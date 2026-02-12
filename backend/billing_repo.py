import psycopg2
import psycopg2.extras
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_pg():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


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

    CREATE TABLE IF NOT EXISTS billing_events (
      id SERIAL PRIMARY KEY,
      user_id TEXT NOT NULL,
      platform TEXT,
      product_id TEXT,
      purchase_token TEXT,
      event_type TEXT,
      amount INTEGER,
      created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );
    """
    with get_pg() as conn, conn.cursor() as cur:
        cur.execute(ddl)
        conn.commit()
    print("✅ billing tables ready.")


# =====================
# 常數設定
# =====================
FREE_AD_COINS = 3
DAILY_AD_LIMIT = 5
SUBSCRIBER_MONTHLY_QUOTA = 1000
DAILY_SUBSCRIBER_LIMIT = SUBSCRIBER_MONTHLY_QUOTA // 30


# =====================
# 廣告送幣
# =====================
def grant_ad_coins(user_id: str, ad_network: str = "admob"):
    today = datetime.now(timezone.utc).date()
    with get_pg() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) AS cnt FROM ad_events
            WHERE user_id=%s AND DATE(created_at)=%s
        """, (user_id, today))
        cnt_row = cur.fetchone()
        cnt = cnt_row["cnt"] if cnt_row else 0

        if cnt >= DAILY_AD_LIMIT:
            return False, "daily_ad_limit_reached"

        cur.execute("""
            INSERT INTO ad_events (user_id, ad_network, earned_coins)
            VALUES (%s, %s, %s)
        """, (user_id, ad_network, FREE_AD_COINS))

        cur.execute("""
            UPDATE users
            SET coins = coins + %s,
                updated_at = NOW()
            WHERE id=%s
            RETURNING coins;
        """, (FREE_AD_COINS, user_id))
        row = cur.fetchone()
        coins = row["coins"] if row else 0
        conn.commit()
        return True, coins


# =====================
# 占卜次數 / coin 扣除
# =====================
def can_consume_ask(user_row: dict):
    user_id = user_row["id"]
    now = datetime.now(timezone.utc)
    today = now.date()

    sub_until = user_row.get("subscribed_until")
    if sub_until and sub_until >= now:
        with get_pg() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT used_count FROM usage_quotas
                WHERE user_id=%s AND usage_date=%s
            """, (user_id, today))
            row = cur.fetchone()
            used = row["used_count"] if row else 0

            if used >= DAILY_SUBSCRIBER_LIMIT:
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

    # 一般用戶
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
        row = cur.fetchone()
        new_balance = row["coins"] if row else 0
        conn.commit()
        return True, new_balance


# =====================
# 紀錄金流事件 (for store_route)
# =====================
def record_billing_event(user_id, platform, product_id, purchase_token, event_type, amount=None):
    with get_pg() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO billing_events (user_id, platform, product_id, purchase_token, event_type, amount, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (user_id, platform, product_id, purchase_token, event_type, amount))
        conn.commit()
