import datetime
import traceback

from flask import Blueprint, jsonify, request

from auth_route import decode_session_token
from history_repo import (
    get_history_detail,
    get_pg,
    list_history,
    record_reading,
    set_pin,
)

history_bp = Blueprint("history", __name__, url_prefix="/history")


def _to_iso_or_now(value):
    if isinstance(value, datetime.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=datetime.timezone.utc)
        return value.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _get_user_from_auth():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, jsonify({"error": "invalid_or_expired_token"}), 401

    token = auth_header.split(" ", 1)[1].strip()
    payload = decode_session_token(token)
    if not payload:
        return None, jsonify({"error": "invalid_or_expired_token"}), 401

    return payload["sub"], None, None


def _count_visible_history(user_id: str) -> int:
    now = datetime.datetime.now(datetime.timezone.utc)
    with get_pg() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) AS total
            FROM readings
            WHERE user_id=%s
              AND (is_pinned = TRUE OR expires_at IS NULL OR expires_at >= %s)
            """,
            (user_id, now),
        )
        row = cur.fetchone() or {}
        return int(row.get("total", 0))


def _to_detail_response(item: dict) -> dict:
    return {
        "reading_id": int(item["id"]),
        "question": item.get("question", ""),
        "hexagram_code": item.get("hexagram_code", ""),
        "changing_lines": item.get("changing_lines") or [],
        "content": item.get("result_full_text", ""),
        "created_at": _to_iso_or_now(item.get("created_at")),
        "is_pinned": bool(item.get("is_pinned", False)),
    }


@history_bp.route("/list", methods=["GET"])
def list_user_history():
    user_id, err_resp, code = _get_user_from_auth()
    if not user_id:
        return err_resp, code

    try:
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return jsonify({"error": "missing_or_invalid_fields"}), 400

    if limit < 1 or limit > 200 or offset < 0:
        return jsonify({"error": "missing_or_invalid_fields"}), 400

    try:
        rows = list_history(user_id, limit=limit, offset=offset, include_expired=False)
        items = [
            {
                "reading_id": int(row["id"]),
                "question": row.get("question", ""),
                "created_at": _to_iso_or_now(row.get("created_at")),
                "is_pinned": bool(row.get("is_pinned", False)),
            }
            for row in rows
        ]
        total = _count_visible_history(user_id)
        return jsonify({"items": items, "total": total})
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "server_error"}), 500


@history_bp.route("/detail/<int:reading_id>", methods=["GET"])
def history_detail(reading_id):
    user_id, err_resp, code = _get_user_from_auth()
    if not user_id:
        return err_resp, code

    try:
        item = get_history_detail(user_id, reading_id)
        if not item:
            return jsonify({"error": "not_found"}), 404
        return jsonify(_to_detail_response(item))
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "server_error"}), 500


@history_bp.route("/pin", methods=["POST"])
def history_pin():
    user_id, err_resp, code = _get_user_from_auth()
    if not user_id:
        return err_resp, code

    data = request.get_json(silent=True) or {}
    reading_id = data.get("reading_id")
    pin_raw = data.get("is_pinned", data.get("pin", True))

    try:
        reading_id = int(reading_id)
    except (TypeError, ValueError):
        return jsonify({"error": "missing_or_invalid_fields"}), 400

    if isinstance(pin_raw, bool):
        pin = pin_raw
    elif isinstance(pin_raw, int) and pin_raw in {0, 1}:
        pin = bool(pin_raw)
    else:
        return jsonify({"error": "missing_or_invalid_fields"}), 400

    try:
        ok = set_pin(user_id, reading_id, pin)
        if not ok:
            return jsonify({"error": "not_found_or_no_permission"}), 404
        return jsonify({"ok": True})
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "server_error"}), 500


@history_bp.route("/sync", methods=["POST"])
def history_sync():
    user_id, err_resp, code = _get_user_from_auth()
    if not user_id:
        return err_resp, code

    data = request.get_json(silent=True) or {}
    records = data.get("records", [])
    if not isinstance(records, list):
        return jsonify({"error": "invalid_records"}), 400

    saved_ids = []
    for rec in records:
        try:
            rid = record_reading(
                user_id=user_id,
                question=rec.get("question", ""),
                hex_code=rec.get("hexagram_code", ""),
                changing_lines_list=rec.get("changing_lines", []),
                full_text=rec.get("result_text", ""),
                derived_from=None,
                is_pinned=False,
            )
            if rid:
                saved_ids.append(rid)
        except Exception:
            traceback.print_exc()

    return jsonify({"ok": True, "saved_count": len(saved_ids), "saved_ids": saved_ids})

