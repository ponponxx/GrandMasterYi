import json
import os
import sqlite3
import traceback

from flask import Blueprint, Response, jsonify, request

from auth_route import decode_session_token
from billing_repo import can_consume_ask
from history_repo import record_reading
from services.llm_service import LLMServiceError, generate_divination
from users_repo import get_user_by_id

ask_bp = Blueprint("ask", __name__)

SYSTEM_PROMPT = (
    "You are an I Ching divination Master. "
    "Use only the provided hexagram/judgment/line-text context from database as primary evidence. "
    "Write in Traditional Chinese, practical and specific, and avoid inventing missing classics text."
)

ICHING_DB_PATH = os.path.join(os.path.dirname(__file__), "iching.db")
TOKEN_USAGE_MARKER = "\n[[[TOKEN_USAGE]]]"
TRIGRAM_MAP_TOP_DOWN = {
    "111": ("乾", "天"),
    "110": ("巽", "風"),
    "101": ("離", "火"),
    "100": ("艮", "山"),
    "011": ("兌", "澤"),
    "010": ("坎", "水"),
    "001": ("震", "雷"),
    "000": ("坤", "地"),
}


def _get_user_id_from_bearer():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ", 1)[1].strip()
    payload = decode_session_token(token)
    if not payload:
        return None
    return payload.get("sub")


def _parse_request_payload(data):
    if not isinstance(data, dict):
        return None

    question = data.get("question")
    throws = data.get("throws")
    user_name = data.get("user_name")
    client_context = data.get("client_context")

    if not isinstance(question, str):
        return None
    question = question.strip()
    if not question or len(question) > 500:
        return None

    if not isinstance(throws, list) or len(throws) != 6:
        return None

    normalized_throws = []
    for value in throws:
        if isinstance(value, bool) or not isinstance(value, int) or value not in {6, 7, 8, 9}:
            return None
        normalized_throws.append(value)

    if user_name is not None:
        if not isinstance(user_name, str):
            return None
        user_name = user_name.strip()
        if len(user_name) > 50:
            return None
        if not user_name:
            user_name = None

    if client_context is not None:
        if not isinstance(client_context, dict):
            return None
        app_name = client_context.get("app")
        if app_name is not None and app_name not in {"web", "ios", "android"}:
            return None
        version = client_context.get("version")
        if version is not None and not isinstance(version, str):
            return None

    return {
        "question": question,
        "throws": normalized_throws,
        "user_name": user_name,
        "client_context": client_context,
    }


def _parse_throws_payload(data):
    if not isinstance(data, dict):
        return None

    throws = data.get("throws")
    if not isinstance(throws, list) or len(throws) != 6:
        return None

    normalized_throws = []
    for value in throws:
        if isinstance(value, bool) or not isinstance(value, int) or value not in {6, 7, 8, 9}:
            return None
        normalized_throws.append(value)

    return normalized_throws


def _line_name_from_throw(position_num, throw_value):
    if throw_value not in {6, 7, 8, 9}:
        return f"line-{position_num}"

    yao = "九" if throw_value in {7, 9} else "六"
    if position_num == 1:
        return f"初{yao}"
    if position_num == 6:
        return f"上{yao}"

    middle_labels = {2: "二", 3: "三", 4: "四", 5: "五"}
    return f"{yao}{middle_labels.get(position_num, str(position_num))}"


def _load_iching_context(throws):
    reversed_throws = list(reversed(throws))
    top_down_bits = ["1" if value in {7, 9} else "0" for value in reversed_throws]
    hexagram_code = "".join(top_down_bits)

    upper_bits = hexagram_code[:3]
    lower_bits = hexagram_code[3:]
    upper_name, upper_element = TRIGRAM_MAP_TOP_DOWN.get(upper_bits, ("未知", "未知"))
    lower_name, lower_element = TRIGRAM_MAP_TOP_DOWN.get(lower_bits, ("未知", "未知"))

    changing_positions = [idx + 1 for idx, value in enumerate(throws) if value in {6, 9}]
    changing_line_names = [_line_name_from_throw(pos, throws[pos - 1]) for pos in changing_positions]

    with sqlite3.connect(ICHING_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute(
            """
            SELECT id, name, binary_code, judgment
            FROM hexagrams
            WHERE binary_code = ?
            """,
            (hexagram_code,),
        )
        hexagram = cur.fetchone()
        if not hexagram:
            raise ValueError(f"hexagram_not_found_for_code:{hexagram_code}")

        line_rows = []
        if changing_positions:
            placeholders = ",".join(["?"] * len(changing_positions))
            cur.execute(
                f"""
                SELECT position, position_num, text
                FROM lines
                WHERE hexagram_id = ?
                  AND position_num IN ({placeholders})
                ORDER BY position_num
                """,
                [hexagram["id"], *changing_positions],
            )
            line_rows = [dict(row) for row in cur.fetchall()]

    top_down_yinyang = ["陽" if bit == "1" else "陰" for bit in top_down_bits]

    return {
        "hexagram_id": int(hexagram["id"]),
        "hexagram_name": hexagram["name"],
        "hexagram_code": hexagram["binary_code"],
        "judgment": hexagram["judgment"],
        "original_throws": throws,
        "reversed_throws": reversed_throws,
        "top_down_yinyang": top_down_yinyang,
        "upper_trigram": {"name": upper_name, "element": upper_element, "bits": upper_bits},
        "lower_trigram": {"name": lower_name, "element": lower_element, "bits": lower_bits},
        "changing_positions": changing_positions,
        "changing_line_names": changing_line_names,
        "changing_line_rows": line_rows,
    }


def _build_user_prompt(question, context, user_name, client_context):
    upper = context["upper_trigram"]
    lower = context["lower_trigram"]

    top = context["top_down_yinyang"]
    yinyang_summary = f"{' '.join(top[:3])} {' '.join(top[3:])}"

    parts = [
        f"Question: {question}",
        f"Throws(original from frontend): {context['original_throws']}",
        f"Reversed throws(for lookup): {context['reversed_throws']}",
        f"Top-down yin/yang: {yinyang_summary}",
        f"Upper trigram: {upper['name']}({upper['element']}) bits={upper['bits']}",
        f"Lower trigram: {lower['name']}({lower['element']}) bits={lower['bits']}",
        f"Hexagram: {context['hexagram_name']}",
        f"Hexagram code: {context['hexagram_code']}",
        f"Judgment: {context['judgment']}",
    ]

    if context["changing_positions"]:
        parts.append(f"Changing line positions: {context['changing_positions']}")
        parts.append(f"Changing line names(from throws): {context['changing_line_names']}")
        if context["changing_line_rows"]:
            parts.append("Changing line texts from DB:")
            for row in context["changing_line_rows"]:
                parts.append(f"- {row['position']}: {row['text']}")
        else:
            parts.append("Changing line texts from DB: none found")
    else:
        parts.append("Changing lines: none")

    if user_name:
        parts.append(f"User name: {user_name}")

    if client_context:
        parts.append(f"Client context: {client_context}")

    parts.append("Please provide: overall reading, key risks, and 3 actionable suggestions.")
    return "\n".join(parts)


def _save_reading(user_id, question, hexagram_code, changing_lines, content):
    try:
        return record_reading(
            user_id=user_id,
            question=question,
            hex_code=hexagram_code,
            changing_lines_list=changing_lines,
            full_text=content,
            derived_from=None,
            is_pinned=False,
        )
    except Exception:
        traceback.print_exc()
        return None


def _format_context_response(context):
    raw_name = (context.get("hexagram_name") or "").strip()
    name_parts = raw_name.split()
    display_name = name_parts[0] if name_parts else raw_name
    trigram_title = " ".join(name_parts[1:]).strip()

    line_texts = []
    for row in context.get("changing_line_rows", []):
        position = (row.get("position") or "").strip()
        text = (row.get("text") or "").strip()
        if position and text:
            line_texts.append(f"{position}，{text}")
        elif text:
            line_texts.append(text)

    return {
        "hexagram_id": context["hexagram_id"],
        "hexagram_code": context["hexagram_code"],
        "hexagram_name": raw_name,
        "display_name": display_name,
        "trigram_title": trigram_title,
        "judgment": context["judgment"],
        "changing_lines": context["changing_positions"],
        "changing_line_texts": line_texts,
    }


@ask_bp.route("/context", methods=["POST"])
def ask_context():
    user_id = _get_user_id_from_bearer()
    if not user_id:
        return jsonify({"error": "invalid_or_expired_token"}), 401

    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "invalid_or_expired_token"}), 401

    throws = _parse_throws_payload(request.get_json(silent=True) or {})
    if not throws:
        return jsonify({"error": "missing_or_invalid_fields"}), 400

    try:
        context = _load_iching_context(throws)
        return jsonify(_format_context_response(context))
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": "server_error", "details": f"iching_lookup_failed:{exc}"}), 500


@ask_bp.route("", methods=["POST"])
def ask_main():
    user_id = _get_user_id_from_bearer()
    if not user_id:
        return jsonify({"error": "invalid_or_expired_token"}), 401

    payload = _parse_request_payload(request.get_json(silent=True) or {})
    if not payload:
        return jsonify({"error": "missing_or_invalid_fields"}), 400

    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "invalid_or_expired_token"}), 401

    can_consume, consume_result = can_consume_ask(user)
    has_ad_session = bool((request.headers.get("X-Ad-Session") or "").strip())
    if not can_consume and not (consume_result == "no_coins" and has_ad_session):
        if consume_result == "daily_quota_reached":
            return jsonify({"error": "rate_limited"}), 429
        return jsonify({"error": "insufficient_coins"}), 402

    if not os.getenv("GEMINI_API_KEY"):
        return jsonify({"error": "server_error", "details": "Missing GEMINI_API_KEY"}), 500

    question = payload["question"]
    throws = payload["throws"]
    user_name = payload["user_name"]
    client_context = payload["client_context"]

    try:
        iching_context = _load_iching_context(throws)
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": "server_error", "details": f"iching_lookup_failed:{exc}"}), 500

    hexagram_code = iching_context["hexagram_code"]
    changing_lines = iching_context["changing_positions"]

    llm_user_prompt = _build_user_prompt(
        question,
        iching_context,
        user_name,
        client_context,
    )

    accept_header = (request.headers.get("Accept") or "").lower()
    wants_json = "application/json" in accept_header and "text/plain" not in accept_header

    if wants_json:
        usage_info = {}

        def capture_usage(usage_payload):
            usage_info.clear()
            usage_info.update(usage_payload or {})

        try:
            content = "".join(
                generate_divination(SYSTEM_PROMPT, llm_user_prompt, usage_callback=capture_usage)
            ).strip()
        except LLMServiceError as exc:
            traceback.print_exc()
            status_code = exc.status_code if exc.status_code in {429, 502, 503, 504} else 503
            return jsonify({"error": "server_error", "details": str(exc)}), status_code
        except Exception as exc:
            traceback.print_exc()
            return jsonify({"error": "server_error", "details": str(exc)}), 500

        reading_id = _save_reading(user_id, question, hexagram_code, changing_lines, content)
        return jsonify(
            {
                "reading_id": reading_id,
                "hexagram_code": hexagram_code,
                "changing_lines": changing_lines,
                "content": content,
                "saved_to_history": reading_id is not None,
                "token_usage": usage_info or None,
            }
        )

    def stream_response():
        chunks = []
        usage_info = {}

        def capture_usage(usage_payload):
            usage_info.clear()
            usage_info.update(usage_payload or {})

        try:
            for chunk in generate_divination(SYSTEM_PROMPT, llm_user_prompt, usage_callback=capture_usage):
                chunks.append(chunk)
                yield chunk
            if usage_info:
                yield f"{TOKEN_USAGE_MARKER}{json.dumps(usage_info, ensure_ascii=False)}"
        except LLMServiceError as exc:
            traceback.print_exc()
            yield f"\n[llm_unavailable] {exc}"
        except Exception:
            traceback.print_exc()
            yield "\n[server_error]"
        finally:
            content = "".join(chunks).strip()
            if content:
                _save_reading(user_id, question, hexagram_code, changing_lines, content)

    return Response(stream_response(), mimetype="text/plain")
