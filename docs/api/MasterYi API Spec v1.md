# MasterYi API Spec v1

Base URL (dev): http://localhost:5000
All endpoints are under /api

## Auth

### POST /api/auth/login
使用第三方登入（Google / Apple）。前端把 provider 的 id_token 傳給後端，由後端驗證並簽發 session JWT。

Headers:
- Content-Type: application/json


Request:
{
  "provider": "google" | "apple",
  "id_token": "string"
}

Response 200:
{
  "token": "string",              // session JWT
  "user": {
    "id": "string",
    "email": "string|null",
    "display_name": "string|null",
    "coins": 0,
    "history_limit": 100
  }
}

Errors:
- 400 invalid_request
- 401 invalid_id_token
- 500 server_error


### POST /api/auth/verify
驗證 session JWT 是否有效（或用於 refresh 前檢查）。

Headers:
- Authorization: Bearer <session_jwt>

Response 200:
{ "valid": true }

Errors:
- 401 invalid_or_expired_token


### GET /api/auth/me
取得目前登入者資訊。

Headers:
- Authorization: Bearer <session_jwt>

Response 200:
{
  "id": "user_123",
  "email": "xxx@gmail.com",
  "display_name": "PC",

  "subscription": {
    "plan": "free | pro",
    "expires_at": "2026-03-10T00:00:00Z",
    "quota": 30,
    "remaining_gold": 12,
    "next_refill_at": "2026-03-10T00:00:00Z"
  },

  "wallet": {
    "silver": 5
  },

  "history_limit": 100
}

Errors:
- 401 invalid_or_expired_token


### POST /api/auth/fake_login  (dev only)
開發用，回傳一個假 token（正式環境建議移除或鎖住）。

Request:
{ "user_id": "string" }

Response 200:
{ "token": "string" }


## Ads

### POST /api/ads/complete
使用者完成一次廣告觀看後呼叫。後端驗證 ad_proof 後，簽發短效 ad_session_token（JWT）。
此 token 用於「允許一次 divination」或「在短時間內允許一次 divination」。

Headers:
- Content-Type: application/json
- Authorization: Bearer <session_jwt>   (optional；登入者可用廣告解鎖，不登入者也可用)

Request:
{
  "provider": "admob" | "unknown",
  "ad_proof": "string"              // 由前端 SDK 取得的 proof / payload（你後端會做驗證）
}

Response 200:
登入用戶:
{
  "reward_type": "silver",
  "silver_granted": 1,
  "new_silver_balance": 6
}
未登入用戶:
{
  "reward_type": "unlock",
  "ad_session_token": "jwt_token",
  "expires_in": 60
}

Errors:
- 400 invalid_request
- 401 invalid_ad_proof
- 500 server_error


## Divination

### POST /api/divination
執行占卜。支援 Streaming（預設/推薦）與 JSON（fallback）。

Headers:
- Content-Type: application/json
- Accept: text/plain | application/json   (optional; default: text/plain)
- Authorization: Bearer <session_jwt>     (optional; 若登入且 coin 足夠可直接占卜)
- X-Ad-Session: <ad_session_jwt>          (optional; 若無登入或無 coin，可用廣告 token)

Request:
{
  "question": "string",
  "throws": [6,7,8,9,7,8],
  "user_name": "string|null",
  "client_context": {
    "app": "web" | "ios" | "android",
    "version": "string|null"
  }
}

Rules:
- 未登入：必須帶有效 ad_session_token 才允許占卜；不寫入 DB history（前端自行存 local）。
- 已登入：若 coin 足夠 → 允許，占卜結果寫入 history（並受 history_limit 控制）。
- 已登入：若 coin 不足 → 必須帶有效 ad_session_token 才允許，占卜結果仍寫入 history（同樣受上限控制）。
- ad_session_token 建議設計為短效且可用一次（jti + server-side consume 記錄；或先做短效、之後再加一次性消耗機制）。

Response 200 (Streaming):
- Content-Type: text/plain
- Transfer-Encoding: chunked
Body: 逐段文字串流（UTF-8）

Response 200 (JSON):
{
  "reading_id": 123|null,
  "hexagram_code": "string",
  "changing_lines": [1,3],
  "content": "string",
  "saved_to_history": true|false
}

Errors:
- 400 missing_or_invalid_fields
- 401 invalid_or_expired_token (session 或 ad_session)
- 402 insufficient_coins (若你選擇在登入 coin 不足且未帶 ad token 時回此碼)
- 429 rate_limited
- 500 server_error


## Store

### POST /api/store/verify
（保留）驗證購買/訂閱收據（App Store / Google Play）。

### GET /api/store/status
（保留）回傳訂閱狀態與 coin 狀態。

### POST /api/store/coins
（保留）調整 coin（購買或管理後台操作）。


## History (login only)

### GET /api/history/list
Headers:
- Authorization: Bearer <session_jwt>

Query:
- limit: number (optional)
- offset: number (optional)

Response 200:
{
  "items": [
    {
      "reading_id": 123,
      "question": "string",
      "created_at": "ISO8601",
      "is_pinned": false
    }
  ],
  "total": 999
}

### GET /api/history/detail/{reading_id}
Headers:
- Authorization: Bearer <session_jwt>

Response 200:
{
  "reading_id": 123,
  "question": "string",
  "hexagram_code": "string",
  "changing_lines": [2,5],
  "content": "string",
  "created_at": "ISO8601",
  "is_pinned": false
}

### POST /api/history/pin
Headers:
- Authorization: Bearer <session_jwt>
Request:
{ "reading_id": 123, "is_pinned": true }

Response 200:
{ "ok": true }

### POST /api/history/sync
（保留）把前端 local 的匿名歷史同步到登入帳號（若你要做這功能）。
