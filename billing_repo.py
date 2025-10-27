# billing_repo.py
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone
import os

DATABASE_URL = os.getenv("DATABASE_URL")

def get_pg():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


# =====================
# 建立表格（初始化）
# =====================
def init_billing_schema():
    ddl = """
    CREATE TABLE IF NOT EXISTS ad_events (
      id SERIAL PRIMARY KEY,
      user_id TEXT NOT NULL,
      ad_network TEXT,
      earned_coins INTEGER NOT NULL,
      created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS usage_quotas (
      id SERIAL PRIMARY KEY,
      user_id TEXT NOT NULL,
      usage_date DATE NOT NULL,
      used_count INTEGER NOT NULL DEFAULT 0,
      UNIQUE(user_id, usage_date)
    );
    """
    with get_pg() as conn, conn.cursor() as cur:
        cur.execute(ddl)
    print("✅ billing tables ready.")


# =====================
# 常數設定（之後可搬去 limits.py）
# =====================
FREE_AD_COINS = 3          # 看一次廣告送 3 coin
DAILY_AD_LIMIT = 5         # 每天最多 5 次
SUBSCRIBER_MONTHLY_QUOTA = 1000  # 每月 1000 次占卜上限


# =====================
# 廣告送幣
# =====================
def grant_ad_coins(user_id: str, ad_network: str = "admob"):
    """使用者看完廣告 → 檢查每日上限 → 增加 coins"""
    today = datetime.now(timezone.utc).date()
    with get_pg() as conn, conn.cursor() as cur:
        # 檢查今日廣告次數
        cur.execute("""
            SELECT COUNT(*) AS cnt FROM ad_events
            WHERE user_id=%s AND DATE(created_at)=%s
        """, (user_id, today))
        cnt = cur.fetchone()["cnt"]
        if cnt >= DAILY_AD_LIMIT:
            return False, "daily_ad_limit_reached"

        # 新增 ad event
        cur.execute("""
            INSERT INTO ad_events (user_id, ad_network, earned_coins)
            VALUES (%s, %s, %s)
        """, (user_id, ad_network, FREE_AD_COINS))

        # 加幣
        cur.execute("""
            UPDATE users
            SET coins = coins + %s,
                updated_at = NOW()
            WHERE id=%s
            RETURNING coins;
        """, (FREE_AD_COINS, user_id))
        coins = cur.fetchone()["coins"]
        conn.commit()
        return True, coins


# =====================
# 占卜次數 / coin 扣除
# =====================
def can_consume_ask(user_row: dict) -> tuple[bool, str]:
    """檢查用戶是否可以占卜，並視情況扣除 coin 或記錄用量"""
    user_id = user_row["id"]
    now = datetime.now(timezone.utc)
    today = now.date()

    # 付費訂閱者（有到期日且未過期）
    sub_until = user_row.get("subscribed_until")
    if sub_until and sub_until >= now:
        # 月度限制 1000 次
        with get_pg() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT used_count FROM usage_quotas
                WHERE user_id=%s AND usage_date=%s
            """, (user_id, today))
            row = cur.fetchone()
            used = row["used_count"] if row else 0
            if used >= 1000 // 30:  # 約每日 33 次（分攤月配額）
                return False, "daily_quota_reached"
            if row:
                cur.execute("""
                    UPDATE usage_quotas SET used_count = used_count + 1
                    WHERE user_id=%s AND usage_date=%s
                """, (user_id, today))
            else:
                cur.execute("""
                    INSERT INTO usage_quotas (user_id, usage_date, used_count)
                    VALUES (%s, %s, 1)
                """, (user_id, today))
            conn.commit()
            return True, "ok"

    # 一般用戶：需要消耗 1 coin
    coins = user_row.get("coins", 0)
    if coins <= 0:
        return False, "no_coins"

    with get_pg() as conn, conn.cursor() as cur:
        cur.execute("""
            UPDATE users
            SET coins = coins - 1,
                updated_at = NOW()
            WHERE id=%s
            RETURNING coins;
        """, (user_id,))
        conn.commit()
        return True, "ok"
