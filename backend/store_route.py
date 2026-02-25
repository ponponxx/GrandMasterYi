import datetime

from flask import Blueprint, jsonify, request

from auth_route import decode_session_token
from billing_repo import record_billing_event
from users_repo import add_user_gold, get_user_by_id, update_user_subscription

store_bp = Blueprint("store", __name__, url_prefix="/store")


def _get_user_id():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    payload = decode_session_token(token)
    if not payload:
        return None
    return payload.get("sub")


@store_bp.route("/verify", methods=["POST"])
def verify_purchase():
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "invalid_or_expired_token"}), 401

    data = request.get_json(silent=True) or {}
    platform = data.get("platform")
    purchase_token = data.get("purchase_token")
    product_id = data.get("product_id")
    if not all([platform, purchase_token, product_id]):
        return jsonify({"error": "missing_fields"}), 400

    # TODO: replace with real Google/Apple verification.
    verified = True
    if not verified:
        return jsonify({"ok": False, "error": "payment_verification_failed"}), 403

    days = 30 if "month" in str(product_id).lower() else 365
    purchase_type = "subscription_monthly" if days == 30 else "subscription_yearly"

    subscribed_until = datetime.datetime.utcnow() + datetime.timedelta(days=days)
    update_user_subscription(user_id, plan="subscriber", until=subscribed_until)

    record_billing_event(
        user_id=user_id,
        platform=platform,
        product_id=product_id,
        purchase_token=purchase_token,
        event_type=purchase_type,
    )

    return jsonify(
        {
            "ok": True,
            "plan": "subscriber",
            "subscribed_until": subscribed_until.isoformat() + "Z",
            "message": f"Subscription activated for {days} days.",
        }
    )


@store_bp.route("/status", methods=["GET"])
def get_subscription_status():
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "invalid_or_expired_token"}), 401

    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "user_not_found"}), 404

    gold = int(user.get("gold") or 0)
    silver = int(user.get("coins") or 0)
    return jsonify(
        {
            "plan": user.get("plan", "free"),
            "gold": gold,
            "coins": silver,
            "wallet": {"gold": gold, "silver": silver},
            "subscribed_until": user.get("subscribed_until"),
        }
    )


@store_bp.route("/coins", methods=["POST"])
def purchase_coins():
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "invalid_or_expired_token"}), 401

    data = request.get_json(silent=True) or {}
    platform = data.get("platform")
    purchase_token = data.get("purchase_token")
    amount = data.get("amount", 0)
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        amount = 0

    if not all([platform, purchase_token]) or amount <= 0:
        return jsonify({"error": "missing_or_invalid_fields"}), 400

    # TODO: replace with real platform verification.
    verified = True
    if not verified:
        return jsonify({"ok": False, "error": "payment_verification_failed"}), 403

    new_gold_balance = add_user_gold(user_id, amount)

    record_billing_event(
        user_id=user_id,
        platform=platform,
        product_id="gold_pack",
        purchase_token=purchase_token,
        event_type="purchase_gold",
        amount=amount,
    )

    return jsonify(
        {
            "ok": True,
            "gold": int(new_gold_balance),
            "message": f"Purchased {amount} gold.",
        }
    )
