from flask import Blueprint, request, jsonify
from auth_route import decode_session_token
from billing_repo import grant_ad_coins, DAILY_AD_LIMIT

ads_bp = Blueprint("ads", __name__, url_prefix="/ads")

# =====================
# /ads/complete
# =====================
@ads_bp.route("/complete", methods=["POST"])
def ads_complete():
    """
    使用者看完廣告 → 增加 coins
    前端流程：
      1. 廣告 SDK 成功播放結束後呼叫此 API
      2. Server 驗證 token → 檢查每日上限 → +3 coin
    """
    # ---- 1️⃣ 驗證 JWT ----
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "missing_token"}), 401
    token = auth_header.split(" ")[1]
    payload = decode_session_token(token)
    if not payload:
        return jsonify({"error": "invalid_or_expired_token"}), 401

    user_id = payload["sub"]

    # ---- 2️⃣ 處理廣告領取 ----
    data = request.json or {}
    ad_network = data.get("ad_network", "admob")  # 可擴充不同來源
    ok, result = grant_ad_coins(user_id, ad_network)

    # ---- 3️⃣ 回傳結果 ----
    if not ok:
        # result 會是 "daily_ad_limit_reached"
        return jsonify({
            "ok": False,
            "error": result,
            "message": f"今日觀看次數已達上限 {DAILY_AD_LIMIT} 次，請改用訂閱或隔日再試。",
            "next_step": "store"  # 前端可依此導引到付費頁
        }), 429  # Too Many Requests

    # result 是剩餘 coin 數
    coins_after = result
    return jsonify({
        "ok": True,
        "coins": coins_after,
        "message": f"🎉 廣告完成，獲得 3 枚金幣！今日上限 {DAILY_AD_LIMIT} 次。"
    })
