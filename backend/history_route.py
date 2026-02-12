from flask import Blueprint, request, jsonify
from auth_route import decode_session_token
from history_repo import (
    list_history,
    get_history_detail,
    set_pin,
    record_reading,
)
import traceback

history_bp = Blueprint("history", __name__, url_prefix="/history")

# =====================
# JWT 驗證輔助
# =====================
def _get_user_from_auth():
    """驗證 Authorization header 並回傳 user_id"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, jsonify({"error": "missing_token"}), 401

    token = auth_header.split(" ")[1]
    payload = decode_session_token(token)
    if not payload:
        return None, jsonify({"error": "invalid_or_expired_token"}), 401

    return payload["sub"], None, None


# =====================
# /history/list
# =====================
@history_bp.route("/list", methods=["GET"])
def list_user_history():
    """取得使用者占卜摘要列表（預設不含過期）"""
    user_id, err_resp, code = _get_user_from_auth()
    if not user_id:
        return err_resp, code

    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))
    include_expired = request.args.get("include_expired", "false").lower() == "true"

    try:
        rows = list_history(user_id, limit=limit, offset=offset, include_expired=include_expired)
        return jsonify({"ok": True, "count": len(rows), "items": rows})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


# =====================
# /history/detail/<id>
# =====================
@history_bp.route("/detail/<int:reading_id>", methods=["GET"])
def history_detail(reading_id):
    """取得單筆占卜全文"""
    user_id, err_resp, code = _get_user_from_auth()
    if not user_id:
        return err_resp, code

    try:
        item = get_history_detail(user_id, reading_id)
        if not item:
            return jsonify({"ok": False, "error": "not_found"}), 404
        return jsonify({"ok": True, "item": item})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


# =====================
# /history/pin
# =====================
@history_bp.route("/pin", methods=["POST"])
def history_pin():
    """釘選或取消釘選"""
    user_id, err_resp, code = _get_user_from_auth()
    if not user_id:
        return err_resp, code

    data = request.json or {}
    reading_id = data.get("reading_id")
    pin = data.get("pin", True)

    if not reading_id:
        return jsonify({"error": "missing_reading_id"}), 400

    try:
        ok = set_pin(user_id, reading_id, bool(pin))
        if not ok:
            return jsonify({"ok": False, "error": "not_found_or_no_permission"}), 404
        return jsonify({"ok": True, "pinned": pin})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


# =====================
# /history/sync  (可選)
# =====================
@history_bp.route("/sync", methods=["POST"])
def history_sync():
    """
    離線同步：前端上傳本地新占卜紀錄
    結構：
      {
        "records": [
          {
            "question": "我該換工作嗎？",
            "hexagram_code": "101010",
            "changing_lines": [1,4,6],
            "result_text": "占卜內容…",
            "created_at": "2025-10-28T10:00:00Z"
          },
          ...
        ]
      }
    """
    user_id, err_resp, code = _get_user_from_auth()
    if not user_id:
        return err_resp, code

    data = request.json or {}
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
            continue

    return jsonify({
        "ok": True,
        "saved_count": len(saved_ids),
        "saved_ids": saved_ids
    })
