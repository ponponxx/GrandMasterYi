import os
import uuid
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_pg():
    """Get PostgreSQL connection."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def _table_exists(cur, table_name: str) -> bool:
    cur.execute("SELECT to_regclass(%s) IS NOT NULL AS ok", (f"public.{table_name}",))
    row = cur.fetchone() or {}
    return bool(row.get("ok"))


def _column_exists(cur, table_name: str, column_name: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s AND column_name=%s
        LIMIT 1
        """,
        (table_name, column_name),
    )
    return bool(cur.fetchone())


def _column_data_type(cur, table_name: str, column_name: str) -> str | None:
    cur.execute(
        """
        SELECT data_type
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s AND column_name=%s
        """,
        (table_name, column_name),
    )
    row = cur.fetchone() or {}
    return row.get("data_type")


def _extract_provider_uid(provider: str, legacy_user_id: str) -> str:
    raw = (legacy_user_id or "").strip()
    prefix = f"{provider}:"
    if raw.startswith(prefix):
        return raw[len(prefix) :]
    if ":" in raw:
        return raw.split(":", 1)[1]
    return raw


def _ensure_users_table(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
          id UUID PRIMARY KEY,
          email TEXT,
          display_name TEXT,
          silver_coins INTEGER NOT NULL DEFAULT 0,
          plan TEXT NOT NULL DEFAULT 'free',
          gold INTEGER NOT NULL DEFAULT 0,
          ask_count INTEGER NOT NULL DEFAULT 0,
          subscribed_until TIMESTAMP WITH TIME ZONE NULL,
          last_login_at TIMESTAMP NULL,
          created_at TIMESTAMP NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """
    )
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT;")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name TEXT;")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS silver_coins INTEGER NOT NULL DEFAULT 0;")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS plan TEXT NOT NULL DEFAULT 'free';")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS gold INTEGER NOT NULL DEFAULT 0;")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS ask_count INTEGER NOT NULL DEFAULT 0;")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS subscribed_until TIMESTAMP WITH TIME ZONE NULL;")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP NULL;")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW();")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();")


def _ensure_auth_providers_table(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_providers (
          id SERIAL PRIMARY KEY,
          user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          provider TEXT NOT NULL,
          provider_uid TEXT NOT NULL,
          created_at TIMESTAMP NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
          UNIQUE(provider, provider_uid),
          UNIQUE(user_id, provider)
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_auth_providers_user ON auth_providers (user_id);")


def _migrate_legacy_users_if_needed(cur):
    if not _table_exists(cur, "users"):
        return

    has_provider_col = _column_exists(cur, "users", "provider")
    has_legacy_coins_col = _column_exists(cur, "users", "coins")
    id_data_type = _column_data_type(cur, "users", "id")
    is_uuid_pk = id_data_type == "uuid"
    needs_migration = has_provider_col or has_legacy_coins_col or not is_uuid_pk

    if not needs_migration:
        return

    if not _table_exists(cur, "users_legacy"):
        cur.execute("ALTER TABLE users RENAME TO users_legacy;")

    _ensure_users_table(cur)
    _ensure_auth_providers_table(cur)

    if not _table_exists(cur, "users_legacy"):
        return

    cur.execute("SELECT * FROM users_legacy")
    legacy_rows = cur.fetchall() or []

    user_id_map: dict[str, str] = {}
    now = datetime.now(timezone.utc)

    for row in legacy_rows:
        old_id = str(row.get("id") or "").strip()
        if not old_id:
            continue

        provider = str(row.get("provider") or "google").strip().lower() or "google"
        provider_uid = _extract_provider_uid(provider, old_id)
        if not provider_uid:
            provider_uid = old_id

        # Reuse existing mapping if this provider identity has already been migrated.
        cur.execute(
            """
            SELECT user_id
            FROM auth_providers
            WHERE provider=%s AND provider_uid=%s
            """,
            (provider, provider_uid),
        )
        existing = cur.fetchone()
        if existing and existing.get("user_id"):
            user_id_map[old_id] = str(existing["user_id"])
            continue

        new_user_id = str(uuid.uuid4())
        user_id_map[old_id] = new_user_id

        silver_coins = int(row.get("coins") or 0)
        gold = int(row.get("gold") or 0)
        ask_count = int(row.get("ask_count") or 0)
        plan = str(row.get("plan") or "free")

        cur.execute(
            """
            INSERT INTO users (
              id, email, display_name, silver_coins, plan, gold, ask_count,
              subscribed_until, last_login_at, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                new_user_id,
                row.get("email"),
                row.get("display_name"),
                silver_coins,
                plan,
                gold,
                ask_count,
                row.get("subscribed_until"),
                row.get("last_login_at"),
                row.get("created_at") or now,
                row.get("updated_at") or now,
            ),
        )
        cur.execute(
            """
            INSERT INTO auth_providers (user_id, provider, provider_uid, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            ON CONFLICT (provider, provider_uid)
            DO UPDATE SET updated_at = NOW()
            """,
            (new_user_id, provider, provider_uid),
        )

    migration_targets = ["readings", "ad_events", "usage_quotas", "billing_events"]
    for table_name in migration_targets:
        if not _table_exists(cur, table_name) or not _column_exists(cur, table_name, "user_id"):
            continue
        for old_id, new_id in user_id_map.items():
            cur.execute(f"UPDATE {table_name} SET user_id=%s WHERE user_id=%s", (new_id, old_id))


def _normalize_user_row(row: dict | None) -> dict | None:
    if not row:
        return None
    user = dict(row)
    user["id"] = str(user.get("id"))
    user["silver_coins"] = int(user.get("silver_coins") or 0)
    user["coins"] = user["silver_coins"]  # backward-compatible alias
    user["gold"] = int(user.get("gold") or 0)
    user["ask_count"] = int(user.get("ask_count") or 0)
    return user


def init_users_schema():
    with get_pg() as conn, conn.cursor() as cur:
        _migrate_legacy_users_if_needed(cur)
        _ensure_users_table(cur)
        _ensure_auth_providers_table(cur)
        conn.commit()
    print("users/auth_providers tables ready.")


def get_or_create_user_by_provider(provider: str, provider_uid: str, email: str, display_name: str) -> dict:
    provider_norm = str(provider or "").strip().lower()
    provider_uid_norm = str(provider_uid or "").strip()
    if not provider_norm or not provider_uid_norm:
        raise ValueError("invalid_provider_identity")

    email_norm = (email or "").strip() or None
    display_name_norm = (display_name or "").strip() or None
    now = datetime.now(timezone.utc)

    for _ in range(2):
        with get_pg() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.*
                FROM auth_providers ap
                JOIN users u ON u.id = ap.user_id
                WHERE ap.provider=%s AND ap.provider_uid=%s
                LIMIT 1
                """,
                (provider_norm, provider_uid_norm),
            )
            existing = cur.fetchone()
            if existing:
                existing_id = str(existing.get("id"))
                cur.execute(
                    """
                    UPDATE users
                    SET email=%s,
                        display_name=%s,
                        last_login_at=%s,
                        updated_at=NOW()
                    WHERE id=%s
                    RETURNING *
                    """,
                    (email_norm, display_name_norm, now, existing_id),
                )
                row = cur.fetchone()
                conn.commit()
                return _normalize_user_row(row) or {}

            new_user_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO users (
                  id, email, display_name, silver_coins, plan, gold, ask_count,
                  subscribed_until, last_login_at, created_at, updated_at
                )
                VALUES (%s, %s, %s, 0, 'free', 0, 0, NULL, %s, NOW(), NOW())
                """,
                (new_user_id, email_norm, display_name_norm, now),
            )
            try:
                cur.execute(
                    """
                    INSERT INTO auth_providers (user_id, provider, provider_uid, created_at, updated_at)
                    VALUES (%s, %s, %s, NOW(), NOW())
                    """,
                    (new_user_id, provider_norm, provider_uid_norm),
                )
            except psycopg2.IntegrityError:
                conn.rollback()
                continue

            cur.execute("SELECT * FROM users WHERE id=%s", (new_user_id,))
            created = cur.fetchone()
            conn.commit()
            return _normalize_user_row(created) or {}

    # Extremely unlikely race fallback.
    with get_pg() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT u.*
            FROM auth_providers ap
            JOIN users u ON u.id = ap.user_id
            WHERE ap.provider=%s AND ap.provider_uid=%s
            LIMIT 1
            """,
            (provider_norm, provider_uid_norm),
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError("failed_to_get_or_create_user")
        return _normalize_user_row(row) or {}


def get_user_by_id(user_id: str) -> dict | None:
    if not isinstance(user_id, str) or not user_id.strip():
        return None
    with get_pg() as conn, conn.cursor() as cur:
        try:
            cur.execute("SELECT * FROM users WHERE id=%s", (user_id.strip(),))
        except Exception:
            return None
        row = cur.fetchone()
        return _normalize_user_row(dict(row)) if row else None


def update_user_coins(user_id: str, delta: int):
    sql = """
    UPDATE users
    SET silver_coins = silver_coins + %s,
        updated_at = NOW()
    WHERE id = %s
    RETURNING silver_coins;
    """
    with get_pg() as conn, conn.cursor() as cur:
        cur.execute(sql, (delta, user_id))
        row = cur.fetchone()
        conn.commit()
        return int(row["silver_coins"]) if row else 0


def update_user_gold(user_id: str, delta: int):
    sql = """
    UPDATE users
    SET gold = gold + %s,
        updated_at = NOW()
    WHERE id = %s
    RETURNING gold;
    """
    with get_pg() as conn, conn.cursor() as cur:
        cur.execute(sql, (delta, user_id))
        row = cur.fetchone()
        conn.commit()
        return int(row["gold"]) if row else 0


def increment_user_ask_count(user_id: str, delta: int = 1):
    sql = """
    UPDATE users
    SET ask_count = ask_count + %s,
        updated_at = NOW()
    WHERE id = %s
    RETURNING ask_count;
    """
    with get_pg() as conn, conn.cursor() as cur:
        cur.execute(sql, (delta, user_id))
        row = cur.fetchone()
        conn.commit()
        return int(row["ask_count"]) if row else 0


def add_user_coins(user_id: str, amount: int):
    return update_user_coins(user_id, amount)


def add_user_gold(user_id: str, amount: int):
    return update_user_gold(user_id, amount)


def update_user_subscription(user_id: str, plan: str = None, until=None):
    fields = []
    values = []
    if plan:
        fields.append("plan = %s")
        values.append(plan)
    if until:
        fields.append("subscribed_until = %s")
        values.append(until)
    if not fields:
        return 0

    sql = f"UPDATE users SET {', '.join(fields)}, updated_at = NOW() WHERE id = %s"
    values.append(user_id)

    with get_pg() as conn, conn.cursor() as cur:
        cur.execute(sql, tuple(values))
        affected = cur.rowcount
        conn.commit()
        return affected


def is_subscriber(user_row: dict) -> bool:
    if not user_row:
        return False
    until = user_row.get("subscribed_until")
    if not until:
        return False
    return until >= datetime.now(timezone.utc)
