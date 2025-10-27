import os
import datetime
import jwt
from flask import Blueprint, request, jsonify
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from dotenv import load_dotenv

from db import SessionLocal, create_or_get_user, store_jwt

# 讀取環境變數
load_dotenv()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
JWT_SECRET = os.getenv("JWT_SECRET")  # 建議在 .env 中設置安全隨機值
JWT_ALGORITHM = "HS256"

# Flask Blueprint
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# =====================
# Google 驗證
# =====================
def verify_google_token(id_token_str):
    try:
        info = id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
        return info
    except Exception as e:
        print(f"❌ Google token verification failed: {e}")
        return None


# =====================
# JWT 建立與解析
# =====================
def create_session_token(user_id):
    exp = datetime.datetime.utcnow() + datetime.timedelta(days=7)
    payload = {
        "sub": user_id,
        "iat": datetime.datetime.utcnow(),
        "exp": exp
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, exp


def decode_session_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        print("⚠️ JWT expired")
        return None
    except jwt.InvalidTokenError:
        print("⚠️ Invalid JWT")
        return None


# =====================
# 登入 API
# =====================
@auth_bp.route("/login", methods=["POST"])
def auth_login():
    data = request.json or {}
    provider = data.get("provider")
    id_token_str = data.get("id_token")

    if not provider or not id_token_str:
        return jsonify({"error": "missing_fields"}), 400

    # 驗證登入提供者
    if provider == "google":
        user_info = verify_google_token(id_token_str)
    else:
        return jsonify({"error": "unsupported_provider"}), 400

    if not user_info:
        return jsonify({"error": "invalid_token"}), 401

    google_id = user_info["sub"]
    name = user_info.get("name", "")
    email = user_info.get("email", "")

    try:
        # 建立或取得使用者
        with SessionLocal() as db:
            user = create_or_get_user(db, google_id, email, name)

            # 建立 JWT
            session_token, exp = create_session_token(f"google:{google_id}")
            store_jwt(db, user.id, session_token, exp)

        print(f"✅ Login success: {email} ({google_id})")

        return jsonify({
            "status": "ok",
            "user": {
                "id": user.id,
                "display_name": user.name,
                "email": user.email,
                "coins": user.coins
            },
            "session_token": session_token,
            "expires_at": exp.isoformat() + "Z"
        })

    except Exception as e:
        print(f"❌ Login error: {e}")
        return jsonify({"error": "server_error", "details": str(e)}), 500


# =====================
# JWT 驗證 API
# =====================
@auth_bp.route("/verify", methods=["POST"])
def verify_token():
    """驗證前端送來的 JWT 是否仍有效"""
    data = request.json or {}
    token = data.get("token")

    if not token:
        return jsonify({"error": "missing_token"}), 400

    payload = decode_session_token(token)
    if not payload:
        return jsonify({"valid": False, "reason": "invalid_or_expired"}), 401

    return jsonify({"valid": True, "user_id": payload["sub"]})
