import datetime
from flask import Blueprint, request, jsonify
from auth_route import decode_session_token
from users_repo import get_user_by_id, update_user_subscription, add_user_coins
from billing_repo import record_billing_event

store_bp = Blueprint("store", __name__, url_prefix="/store")

# =====================
# /store/verify - 驗證金流交易 (Google / Apple)
# =====================
@store_bp.route("/verify", methods=["POST"])
def verify_purchase():
    """
    前端付款成功後呼叫：
      POST /store/verify
      Authorization: Bearer <JWT>

      {
        "platform": "google" | "apple",
        "purchase_token": "xxxxx",
        "product_id": "com.grandmasteryi.monthly"
      }

    後端負責驗證此交易是否合法，
    驗證通過後更新使用者方案（plan / subscribed_until）。
    """
    # 1️⃣ 驗證 JWT
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "missing_token"}), 401
    token = auth_header.split(" ")[1]
    payload = decode_session_token(token)
    if not payload:
        return jsonify({"error": "invalid_or_expired_token"}), 401
    user_id = payload["sub"]

    # 2️⃣ 取得參數
    data = request.json or {}
    platform = data.get("platform")
    purchase_token = data.get("purchase_token")
    product_id = data.get("product_id")

    if not all([platform, purchase_token, product_id]):
        return jsonify({"error": "missing_fields"}), 400

    # 3️⃣ 模擬金流驗證（正式上線時這裡要連 Google/Apple API）
    # =======================================================
    # TODO: 後續你可以改成實際呼叫 Google/Apple API 驗證收據：
    #   - Google: https://developers.google.com/android-publisher/api-ref/rest/v3/purchases.subscriptions
    #   - Apple: https://developer.apple.com/documentation/appstoreserverapi/verifyreceipt
    # =======================================================
    verified = True
    purchase_type = "subscription_monthly" if "month" in product_id else "subscription_yearly"
    days = 30 if "month" in product_id else 365

    if not verified:
        return jsonify({"ok": False, "error": "payment_verification_failed"}), 403

    # 4️⃣ 更新使用者方案
    subscribed_until = datetime.datetime.utcnow() + datetime.timedelta(days=days)
    update_user_subscription(user_id, plan="subscriber", until=subscribed_until)

    # 5️⃣ 寫入 billing log
    record_billing_event(
        user_id=user_id,
        platform=platform,
        product_id=product_id,
        purchase_token=purchase_token,
        event_type=purchase_type
    )

    return jsonify({
        "ok": True,
        "plan": "subscriber",
        "subscribed_until": subscribed_until.isoformat() + "Z",
        "message": f"✅ 已啟用 {days}-天訂閱方案"
    })


# =====================
# /store/status - 查詢目前訂閱狀態
# =====================
@store_bp.route("/status", methods=["GET"])
def get_subscription_status():
    """回傳目前使用者的訂閱與 coin 狀態"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "missing_token"}), 401
    token = auth_header.split(" ")[1]
    payload = decode_session_token(token)
    if not payload:
        return jsonify({"error": "invalid_or_expired_token"}), 401

    user_id = payload["sub"]
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "user_not_found"}), 404

    return jsonify({
        "plan": user.get("plan", "free"),
        "coins": user.get("coins", 0),
        "subscribed_until": user.get("subscribed_until")
    })


# =====================
# /store/coins - 購買金幣 (非訂閱型)
# =====================
@store_bp.route("/coins", methods=["POST"])
def purchase_coins():
    """
    直接購買金幣：
      POST /store/coins
      {
        "platform": "google",
        "purchase_token": "xxxx",
        "amount": 50
      }
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "missing_token"}), 401
    token = auth_header.split(" ")[1]
    payload = decode_session_token(token)
    if not payload:
        return jsonify({"error": "invalid_or_expired_token"}), 401
    user_id = payload["sub"]

    data = request.json or {}
    platform = data.get("platform")
    purchase_token = data.get("purchase_token")
    amount = data.get("amount", 0)

    if not all([platform, purchase_token]) or amount <= 0:
        return jsonify({"error": "missing_or_invalid_fields"}), 400

    # 模擬驗證購幣成功
    verified = True
    if not verified:
        return jsonify({"ok": False, "error": "payment_verification_failed"}), 403

    # 增加金幣
    new_balance = add_user_coins(user_id, amount)

    # 寫入 billing 紀錄
    record_billing_event(
        user_id=user_id,
        platform=platform,
        product_id="coins_pack",
        purchase_token=purchase_token,
        event_type="purchase_coins",
        amount=amount
    )

    return jsonify({
        "ok": True,
        "coins": new_balance,
        "message": f"💰 已成功購買 {amount} 枚金幣"
    })
