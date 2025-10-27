# history_repo.py
import os
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta, timezone
import json
import zlib

from users_repo import get_user_by_id, is_subscriber

DATABASE_URL = os.getenv("DATABASE_URL")

def get_pg():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)

# ---- 壓縮 / 解壓 ----
def _compress(s: str) -> bytes:
    if s is None:
        return None
    return zlib.compress(s.encode("utf-8"))

def _decompress(b: bytes) -> str:
    if b is None:
        return ""
    return zlib.decompress(b).decode("utf-8")

def _make_summary(text: str, max_len: int = 220) -> str:
    if not text:
        return ""
    t = text.strip().replace("\r", " ").replace("\n", " ")
    return t if len(t) <= max_len else t[:max_len] + "…"

# =====================
# 初始化：建表（全文壓縮存於 BYTEA）
# =====================
def init_history_schema():
    ddl = """
    CREATE TABLE IF NOT EXISTS readings (
      id SERIAL PRIMARY KEY,
      user_id TEXT,                                -- 可為 NULL（guest）
      question TEXT NOT NULL,
      hexagram_code TEXT NOT NULL,
      changing_lines JSONB,                        -- 例如 [1,4,6]
      result_summary TEXT,                         -- 列表用摘要
      result_full BYTEA,                           -- 壓縮全文
      derived_from INTEGER,                        -- 延伸占卜父ID
      is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
      expires_at TIMESTAMP NULL,
      created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );

    -- 查列表常用索引
    CREATE INDEX IF NOT EXISTS idx_readings_user_created
      ON readings (user_id, created_at DESC);

    CREATE INDEX IF NOT EXISTS idx_readings_user_expires
      ON readings (user_id, expires_at);
    """
    with get_pg() as conn, conn.cursor() as cur:
        cur.execute(ddl)
    print("✅ readings table ready.")

# =====================
# 寫入占卜紀錄
# =====================
def record_reading(
    user_id: str | None,
    question: str,
    hex_code: str,
    changing_lines_list: list[int] | None,
    full_text: str,
    derived_from: int | None = None,
    is_pinned: bool = False
) -> int:
    """
    - 訂閱者：未 pinned -> 預設 30 天後過期（expires_at）
    - 非訂閱者或 guest：不設 expires_at（可由上層策略決定是否不落盤）
    """
    now = datetime.now(timezone.utc)
    user = get_user_by_id(user_id) if user_id else None
    subscriber = is_subscriber(user) if user else False

    expires_at = None
    if user and subscriber and not is_pinned:
        expires_at = now + timedelta(days=30)

    summary = _make_summary(full_text)
    compressed = _compress(full_text)
    lines_json = json.dumps(changing_lines_list or [])

    sql = """
    INSERT INTO readings (
      user_id, question, hexagram_code, changing_lines,
      result_summary, result_full, derived_from,
      is_pinned, expires_at
    )
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    RETURNING id;
    """
    with get_pg() as conn, conn.cursor() as cur:
        cur.execute(sql, (
            user_id, question, hex_code, lines_json,
            summary, psycopg2.Binary(compressed), derived_from,
            is_pinned, expires_at
        ))
        rid = cur.fetchone()["id"]
        conn.commit()
        return rid

# =====================
# 列出歷史（摘要列表）
# =====================
def list_history(
    user_id: str,
    limit: int = 100,
    offset: int = 0,
    include_expired: bool = False
) -> list[dict]:
    """
    - 預設不含過期（未 pinned 且 expires_at < now）
    - 僅回摘要（result_summary）；全文另用 get_history_detail
    """
    now = datetime.now(timezone.utc)
    with get_pg() as conn, conn.cursor() as cur:
        if include_expired:
            cur.execute("""
                SELECT id, question, hexagram_code, changing_lines,
                       result_summary, derived_from, is_pinned,
                       expires_at, created_at
                FROM readings
                WHERE user_id=%s
                ORDER BY created_at DESC
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
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, (user_id, now, limit, offset))
        rows = cur.fetchall()

    # 轉換 changing_lines JSONB -> Python list
    out = []
    for r in rows:
        item = dict(r)
        try:
            item["changing_lines"] = json.loads(item["changing_lines"]) if item.get("changing_lines") else []
        except Exception:
            item["changing_lines"] = []
        out.append(item)
    return out

# =====================
# 讀取單筆全文
# =====================
def get_history_detail(user_id: str, reading_id: int) -> dict | None:
    sql = """
    SELECT id, user_id, question, hexagram_code, changing_lines,
           result_summary, result_full, derived_from, is_pinned,
           expires_at, created_at
    FROM readings
    WHERE id=%s AND user_id=%s
    """
    with get_pg() as conn, conn.cursor() as cur:
        cur.execute(sql, (reading_id, user_id))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["changing_lines"] = json.loads(d["changing_lines"]) if d.get("changing_lines") else []
        except Exception:
            d["changing_lines"] = []
        d["result_full_text"] = _decompress(d["result_full"]) if d.get("result_full") else ""
        # 不把 bytea 原文丟給前端
        del d["result_full"]
        return d

# =====================
# Pin / Unpin
# =====================
def set_pin(user_id: str, reading_id: int, pin: bool) -> bool:
    now = datetime.now(timezone.utc)
    user = get_user_by_id(user_id)
    subscriber = is_subscriber(user) if user else False

    with get_pg() as conn, conn.cursor() as cur:
        if pin:
            # 釘選 → 永久（清除過期時間）
            cur.execute("""
                UPDATE readings
                SET is_pinned=TRUE, expires_at=NULL
                WHERE id=%s AND user_id=%s
                RETURNING id
            """, (reading_id, user_id))
        else:
            # 取消釘選 → 訂閱者恢復 30 天期限；非訂閱者不設期限（由策略決定）
            new_exp = (now + timedelta(days=30)) if subscriber else None
            cur.execute("""
                UPDATE readings
                SET is_pinned=FALSE, expires_at=%s
                WHERE id=%s AND user_id=%s
                RETURNING id
            """, (new_exp, reading_id, user_id))
        ok = cur.fetchone() is not None
        conn.commit()
        return ok

# =====================
# 可選：清理已過期
# =====================
def delete_expired(limit: int = 1000) -> int:
    """批次刪除過期且未 pinned 的資料（可排程呼叫）"""
    now = datetime.now(timezone.utc)
    with get_pg() as conn, conn.cursor() as cur:
        cur.execute("""
            DELETE FROM readings
            WHERE is_pinned = FALSE
              AND expires_at IS NOT NULL
              AND expires_at < %s
            RETURNING id
        """, (now,))
        rows = cur.fetchall()
        conn.commit()
        return len(rows or [])
