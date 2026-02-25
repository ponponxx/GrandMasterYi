import os
import datetime

import jwt
from dotenv import load_dotenv
from flask import Blueprint, jsonify, request
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from users_repo import get_user_by_id, upsert_user_basic

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
JWT_SECRET = (os.getenv("JWT_SECRET") or "").strip()
if not JWT_SECRET:
    raise RuntimeError("Missing JWT_SECRET in environment. Set a value with at least 32 bytes.")
if len(JWT_SECRET.encode("utf-8")) < 32:
    raise RuntimeError("JWT_SECRET must be at least 32 bytes for HS256.")
JWT_ALGORITHM = "HS256"

PRO_PLAN_VALUES = {"pro", "pro_monthly", "pro_yearly", "subscriber"}
DEFAULT_PRO_QUOTA = 1000
DEFAULT_HISTORY_LIMIT = 200

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def verify_google_token(id_token_str: str):
    try:
        return id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except Exception:
        return None


def create_session_token(user_id: str):
    now = datetime.datetime.utcnow()
    exp = now + datetime.timedelta(days=7)
    payload = {"sub": user_id, "iat": now, "exp": exp}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, exp


def decode_session_token(token: str):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def _iso_or_none(dt_value):
    if not dt_value:
        return None
    if isinstance(dt_value, datetime.datetime):
        if dt_value.tzinfo is None:
            dt_value = dt_value.replace(tzinfo=datetime.timezone.utc)
        return dt_value.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    return str(dt_value)


def _to_user_profile(user: dict) -> dict:
    raw_plan = str(user.get("plan") or "free").lower()
    plan = "pro" if raw_plan in PRO_PLAN_VALUES else "free"
    gold = int(user.get("gold") or 0)
    coins = int(user.get("coins") or 0)
    if gold < 0:
        gold = 0
    if coins < 0:
        coins = 0

    return {
        "id": user["id"],
        "email": user.get("email"),
        "display_name": user.get("display_name"),
        "subscription": {
            "plan": plan,
            "expires_at": _iso_or_none(user.get("subscribed_until")),
            "quota": DEFAULT_PRO_QUOTA if plan == "pro" else 0,
            "next_refill_at": None,
        },
        "wallet": {
            "gold": gold,
            "silver": coins,
        },
        "history_limit": DEFAULT_HISTORY_LIMIT,
    }


def _get_token_from_auth_header():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    return auth_header.split(" ", 1)[1].strip()


@auth_bp.route("/login", methods=["POST"])
def auth_login():
    data = request.get_json(silent=True) or {}
    provider = data.get("provider")
    id_token_str = data.get("id_token")

    if provider not in {"google", "apple"} or not isinstance(id_token_str, str) or not id_token_str.strip():
        return jsonify({"error": "invalid_request"}), 400

    if provider == "apple":
        return jsonify({"error": "invalid_request", "message": "apple_login_not_implemented"}), 400

    user_info = verify_google_token(id_token_str)
    if not user_info:
        return jsonify({"error": "invalid_id_token"}), 401

    user_id = f"google:{user_info['sub']}"
    email = user_info.get("email", "")
    name = user_info.get("name", "")

    try:
        upsert_user_basic(user_id, provider, email, name)
        user = get_user_by_id(user_id)
        token, _ = create_session_token(user_id)
        return jsonify({"token": token, "user": _to_user_profile(user)})
    except Exception as exc:
        return jsonify({"error": "server_error", "details": str(exc)}), 500


@auth_bp.route("/fake_login", methods=["POST"])
def fake_login():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not isinstance(user_id, str) or not user_id.strip():
        user_id = "google:test_user_123"
    user_id = user_id.strip()

    upsert_user_basic(
        user_id=user_id,
        provider="google",
        email="test@example.com",
        display_name="TestUser",
    )
    session_token, _ = create_session_token(user_id)
    return jsonify({"token": session_token})


@auth_bp.route("/verify", methods=["POST"])
def verify_token():
    token = _get_token_from_auth_header()
    if not token:
        return jsonify({"valid": False, "error": "invalid_or_expired_token"}), 401

    payload = decode_session_token(token)
    if not payload:
        return jsonify({"valid": False, "error": "invalid_or_expired_token"}), 401

    return jsonify({"valid": True})


@auth_bp.route("/me", methods=["GET"])
def get_me():
    token = _get_token_from_auth_header()
    if not token:
        return jsonify({"error": "invalid_or_expired_token"}), 401

    payload = decode_session_token(token)
    if not payload:
        return jsonify({"error": "invalid_or_expired_token"}), 401

    user = get_user_by_id(payload["sub"])
    if not user:
        return jsonify({"error": "invalid_or_expired_token"}), 401

    return jsonify(_to_user_profile(user))

