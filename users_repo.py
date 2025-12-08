import os
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")

def get_pg():
    """建立 PostgreSQL 連線"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


# =====================
# 初始化：建表
# =====================
def init_users_schema():
    ddl = """
    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY,
      provider TEXT NOT NULL,
      email TEXT,
      display_name TEXT,
      plan TEXT NOT NULL DEFAULT 'free',
      coins INTEGER NOT NULL DEFAULT 0,
      subscribed_until TIMESTAMP WITH TIME ZONE NULL,
      last_login_at TIMESTAMP NULL,
      created_at TIMESTAMP NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    );
    """
    with get_pg() as conn, conn.cursor() as cur:
        cur.execute(ddl)
        conn.commit()
    print("✅ users table ready.")


# =====================
# 新增或更新使用者（登入時呼叫）
# =====================
def upsert_user_basic(user_id: str, provider: str, email: str, display_name: str):
    now = datetime.now(timezone.utc)
    sql = """
    INSERT INTO users (id, provider, email, display_name, last_login_at, created_at, updated_at)
    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
    ON CONFLICT (id) DO UPDATE
    SET email = EXCLUDED.email,
        display_name = EXCLUDED.display_name,
        last_login_at = EXCLUDED.last_login_at,
        updated_at = NOW();
    """
    with get_pg() as conn, conn.cursor() as cur:
        cur.execute(sql, (user_id, provider, email or "", display_name or "", now))
        conn.commit()


# =====================
# 查詢使用者
# =====================
def get_user_by_id(user_id: str) -> dict | None:
    with get_pg() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None


# =====================
# 更新 coins
# =====================
def update_user_coins(user_id: str, delta: int):
    sql = """
    UPDATE users
    SET coins = coins + %s,
        updated_at = NOW()
    WHERE id = %s
    RETURNING coins;
    """
    with get_pg() as conn, conn.cursor() as cur:
        cur.execute(sql, (delta, user_id))
        row = cur.fetchone()
        conn.commit()
        return row["coins"] if row else 0


def add_user_coins(user_id: str, amount: int):
    """直接增加金幣數（購幣用）"""
    return update_user_coins(user_id, amount)


# =====================
# 更新訂閱方案 / 到期日
# =====================
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


# =====================
# 是否訂閱中
# =====================
def is_subscriber(user_row: dict) -> bool:
    if not user_row:
        return False
    until = user_row.get("subscribed_until")
    if not until:
        return False
    return until >= datetime.now(timezone.utc)
