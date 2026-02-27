import os
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta, timezone
import json
import zlib
from users_repo import get_user_by_id, is_subscriber
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_pg():
    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor
    )

# ---- 壓縮 / 解壓 ----
def _compress(s: str) -> bytes:
    if not s:
        return None
    return zlib.compress(s.encode("utf-8"))

def _decompress(b: bytes) -> str:
    if not b:
        return ""
    try:
        return zlib.decompress(b).decode("utf-8")
    except Exception:
        return ""

def _make_summary(text: str, max_len: int = 220) -> str:
    if not text:
        return ""
    t = text.strip().replace("\r", " ").replace("\n", " ")
    return t if len(t) <= max_len else t[:max_len] + "…"

# =====================
# 初始化建表
# =====================
def init_history_schema():
    ddl = """
    CREATE TABLE IF NOT EXISTS readings (
      id SERIAL PRIMARY KEY,
      user_id TEXT,
      question TEXT NOT NULL,
      hexagram_code TEXT NOT NULL,
      changing_lines JSONB,
      result_summary TEXT,
      result_full BYTEA,
      derived_from INTEGER,
      is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
      expires_at TIMESTAMP NULL,
      created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_readings_user_created
      ON readings (user_id, created_at DESC);

    CREATE INDEX IF NOT EXISTS idx_readings_user_expires
      ON readings (user_id, expires_at);
    """
    with get_pg() as conn, conn.cursor() as cur:
        cur.execute(ddl)
        conn.commit()
    print("✅ readings table ready.")

# =====================
# 寫入占卜紀錄
# =====================
def _normalize_changing_lines(value):
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, bool):
                continue
            try:
                out.append(int(item))
            except (TypeError, ValueError):
                continue
        return out

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return []
        return _normalize_changing_lines(parsed)

    return []


def record_reading(user_id, question, hex_code, changing_lines_list,
                   full_text, derived_from=None, is_pinned=False):
    now = datetime.now(timezone.utc)
    user = get_user_by_id(user_id) if user_id else None
    subscriber = is_subscriber(user) if user else False
    expires_at = now + timedelta(days=30) if subscriber and not is_pinned else None

    summary = _make_summary(full_text)
    compressed = _compress(full_text)
    changing_lines_json = psycopg2.extras.Json(_normalize_changing_lines(changing_lines_list))

    sql = """
    INSERT INTO readings (user_id, question, hexagram_code, changing_lines,
                          result_summary, result_full, derived_from,
                          is_pinned, expires_at)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    RETURNING id;
    """
    with get_pg() as conn, conn.cursor() as cur:
        cur.execute(
            sql,
            (
                user_id,
                question,
                hex_code,
                changing_lines_json,
                summary,
                psycopg2.Binary(compressed) if compressed is not None else None,
                derived_from,
                is_pinned,
                expires_at,
            ),
        )
        row = cur.fetchone()
        conn.commit()
        return row["id"] if row else None

# =====================
# 列出歷史（摘要列表）
# =====================
def list_history(user_id, limit=100, offset=0, include_expired=False):
    now = datetime.now(timezone.utc)
    with get_pg() as conn, conn.cursor() as cur:
        if include_expired:
            cur.execute("""
                SELECT id, question, hexagram_code, changing_lines,
                       result_summary, derived_from, is_pinned,
                       expires_at, created_at
                FROM readings
                WHERE user_id=%s
                ORDER BY is_pinned DESC, created_at DESC
                LIMIT %s OFFSET %s
            """, (user_id, limit, offset))
        else:
            cur.execute("""
                SELECT id, question, hexagram_code, changing_lines,
                       result_summary, derived_from, is_pinned,
                       expires_at, created_at
                FROM readings
                WHERE user_id=%s
                  AND (is_pinned = TRUE OR expires_at IS NULL OR expires_at >= %s)
                ORDER BY is_pinned DESC, created_at DESC
                LIMIT %s OFFSET %s
            """, (user_id, now, limit, offset))
        rows = cur.fetchall()

    out = []
    for r in rows:
        item = dict(r)
        try:
            item["changing_lines"] = _normalize_changing_lines(item.get("changing_lines"))
        except Exception:
            item["changing_lines"] = []
        out.append(item)
    return out

# =====================
# 讀取單筆全文
# =====================
def get_history_detail(user_id, reading_id):
    sql = """
    SELECT * FROM readings WHERE id=%s AND user_id=%s
    """
    with get_pg() as conn, conn.cursor() as cur:
        cur.execute(sql, (reading_id, user_id))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["changing_lines"] = _normalize_changing_lines(d.get("changing_lines"))
        except Exception:
            d["changing_lines"] = []
        d["result_full_text"] = _decompress(d.get("result_full"))
        d.pop("result_full", None)
        return d

# =====================
# Pin / Unpin
# =====================
def set_pin(user_id, reading_id, pin):
    now = datetime.now(timezone.utc)
    user = get_user_by_id(user_id)
    subscriber = is_subscriber(user) if user else False

    with get_pg() as conn, conn.cursor() as cur:
        if pin:
            cur.execute("""
                UPDATE readings
                SET is_pinned=TRUE, expires_at=NULL
                WHERE id=%s AND user_id=%s
                RETURNING id
            """, (reading_id, user_id))
        else:
            new_exp = (now + timedelta(days=30)) if subscriber else None
            cur.execute("""
                UPDATE readings
                SET is_pinned=FALSE, expires_at=%s
                WHERE id=%s AND user_id=%s
                RETURNING id
            """, (new_exp, reading_id, user_id))
        row = cur.fetchone()
        conn.commit()
        return bool(row)


def delete_reading(user_id, reading_id):
    with get_pg() as conn, conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM readings
            WHERE id=%s AND user_id=%s
            RETURNING id
            """,
            (reading_id, user_id),
        )
        row = cur.fetchone()
        conn.commit()
        return bool(row)

# =====================
# 清理過期紀錄
# =====================
def delete_expired(limit=1000):
    now = datetime.now(timezone.utc)
    with get_pg() as conn, conn.cursor() as cur:
        cur.execute("""
            DELETE FROM readings
            WHERE is_pinned = FALSE
              AND expires_at IS NOT NULL
              AND expires_at < %s
            RETURNING id
        """, (now,))
        rows = cur.fetchall() or []
        conn.commit()
        return len(rows)

