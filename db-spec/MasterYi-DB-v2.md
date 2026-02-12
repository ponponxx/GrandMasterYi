Table: users
-------------------------------------
Column           | Type          | Description
-----------------|---------------|---------------------------------
id               | UUID (PK)     | 使用者唯一 ID（Google sub）
email            | VARCHAR       | 使用者 email（nullable）
display_name     | VARCHAR       | 顯示名稱（nullable）
created_at       | TIMESTAMPTZ   | 建立時間
updated_at       | TIMESTAMPTZ   | 最後更新時間


Table: subscriptions
----------------------------------------------------
Column              | Type          | Description
--------------------|---------------|------------------------------------
id                  | UUID (PK)     | 訂閱唯一 ID
user_id             | UUID (FK)     | 對應 users.id
plan                | TEXT          | free | pro_monthly | pro_yearly
status              | TEXT          | active | canceled | expired
quota               | INTEGER       | 訂閱每月 gold 總量
interval_days       | INTEGER       | (30 or 365)
next_refill_at      | TIMESTAMPTZ
expires_at          | TIMESTAMPTZ
last_verified_at    | TIMESTAMPTZ
created_at          | TIMESTAMPTZ
updated_at          | TIMESTAMPTZ

Indexes:
- user_id (unique)
- next_refill_at


Table: wallets
------------------------------------------------
user_id         |UUID (PK, FK)
gold_balance    |INTEGER DEFAULT 0 | From Pro Plan
silver_balance  |INTEGER DEFAULT 0 | From read AD
updated_at      |TIMESTAMPTZ       | 


Indexes:
- user_id (PK)

Table: ad_sessions
--------------------------------------------------------
Column           | Type         | Description
-----------------|--------------|------------------------------
jti              | UUID (PK)    | JWT unique ID
user_id          | UUID (FK)    | nullable；未登入使用者可為 null
issued_at        | TIMESTAMPTZ  | JWT 發行時間
expires_at       | TIMESTAMPTZ  | JWT 失效時間
consumed_at      | TIMESTAMPTZ  | 被 use 時間（nullable）
created_at       | TIMESTAMPTZ  | 建立時間

Indexes:
- jti (unique)
- user_id
- expires_at

Table: readings
------------------------------------------------------------------
Column           | Type         | Description
-----------------|--------------|--------------------------------------
id               | BIGINT (PK)  | 自動流水 ID
user_id          | UUID (FK)    | 使用者（nullable if ad unlock only）
hexagram_code    | TEXT         | 卦碼（例如 "101001"）
changing_lines   | INT[]        | 變爻陣列
question         | TEXT         | 使用者提問
result_text      | TEXT         | 最終解釋全文
saved_to_history | BOOLEAN      | 是否寫入 history
is_pinned        | BOOLEAN      | 是否置頂
created_at       | TIMESTAMPTZ  | 該次記錄
updated_at       | TIMESTAMPTZ  | 若後續可編輯才會更新

Indexes:
- user_id
- created_at

Table: achievements
-----------------------------------------------------------
Column          | Type          | Description
----------------|---------------|-------------------------------------
user_id         | UUID (PK, FK) | 對應 users.id
hexagrams_seen  | TEXT[]         | 已看過的卦象
lines_seen      | INT[]          | 已看過的變爻號碼
updated_at      | TIMESTAMPTZ    | 最後更新時間

Indexes:
- user_id

Frontend Local Storage:

- local_history
  - key: "local_history"
  - Structure:
    {
      id: string,
      hexagram_code: string,
      changing_lines: number[],
      question: string,
      result_summary: string,
      timestamp: string
    }

- google_client_id
- session_jwt

users.id
   ↳ subscriptions.user_id
   ↳ wallets.user_id
   ↳ ad_sessions.user_id
   ↳ readings.user_id
   ↳ achievements.user_id

users
PRIMARY KEY (id)

subscriptions
FOREIGN KEY (user_id) REFERENCES users(id)
UNIQUE (user_id)

wallets
FOREIGN KEY (user_id) REFERENCES users(id)
PRIMARY KEY (user_id)

ad_sessions
PRIMARY KEY (jti)
FOREIGN KEY (user_id) REFERENCES users(id)

readings
FOREIGN KEY (user_id) REFERENCES users(id)

achievements
PRIMARY KEY (user_id)

Subscription refill logic
if now >= next_refill_at:
    remaining_gold = quota
    next_refill_at += interval (30 days for monthly, 365 days for yearly)

Wallet consume logic
if gold > 0:
    consume 1 gold
elif silver > 0:
    consume 1 silver
elif valid_ad_unlock:
    consume ad_session
else:
    insufficient balance

Ad session logic
if expires_at < now OR consumed_at != null:
    invalid ad_session
else:
    mark consumed_at = now
    allow interpretation

Achievements logic
- hexagram_code first seen: add to hexagrams_seen
- for each changing_line, if not in lines_seen: add