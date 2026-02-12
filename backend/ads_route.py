from flask import Blueprint, jsonify, request

from auth_route import decode_session_token
from billing_repo import FREE_AD_COINS, grant_ad_coins

ads_bp = Blueprint("ads", __name__, url_prefix="/ads")


@ads_bp.route("/complete", methods=["POST"])
def ads_complete():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "invalid_ad_proof"}), 401

    token = auth_header.split(" ", 1)[1].strip()
    payload = decode_session_token(token)
    if not payload:
        return jsonify({"error": "invalid_ad_proof"}), 401

    data = request.get_json(silent=True) or {}
    provider = data.get("provider")
    ad_proof = data.get("ad_proof")

    if provider not in {"admob", "unknown"}:
        return jsonify({"error": "invalid_request"}), 400

    if not isinstance(ad_proof, str) or not ad_proof.strip():
        return jsonify({"error": "invalid_request"}), 400

    ok, result = grant_ad_coins(payload["sub"], provider)
    if not ok:
        if result == "daily_ad_limit_reached":
            return jsonify({"error": "rate_limited"}), 429
        return jsonify({"error": "server_error"}), 500

    return jsonify(
        {
            "reward_type": "silver",
            "silver_granted": FREE_AD_COINS,
            "new_silver_balance": int(result),
        }
    )

