import json
import os
import time
from typing import Callable

import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"
#DEFAULT_GEMINI_MODEL = "gemini-2.5-Pro"
DEFAULT_FALLBACK_MODELS = ("gemini-2.5-flash", "gemini-3-flash-preview")
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 2
REQUEST_CONNECT_TIMEOUT_SECONDS = 10
REQUEST_READ_TIMEOUT_SECONDS = 300
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_OUTPUT_TOKENS = 2048


class LLMServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 503, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


def _resolve_models():
    primary_model = (os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL).strip()
    fallback_raw = (os.getenv("GEMINI_FALLBACK_MODELS") or "").strip()
    fallback_models = [
        model.strip()
        for model in (fallback_raw.split(",") if fallback_raw else DEFAULT_FALLBACK_MODELS)
        if model.strip()
    ]

    models = []
    for model in [primary_model, *fallback_models]:
        if model and model not in models:
            models.append(model)
    return models


def _parse_float_env(var_name: str, default_value: float) -> float:
    raw = (os.getenv(var_name) or "").strip()
    if not raw:
        return default_value
    try:
        return float(raw)
    except ValueError:
        return default_value


def _parse_int_env(var_name: str, default_value: int) -> int:
    raw = (os.getenv(var_name) or "").strip()
    if not raw:
        return default_value
    try:
        return int(raw)
    except ValueError:
        return default_value


def _resolve_generation_config() -> dict:
    temperature = _parse_float_env("GEMINI_TEMPERATURE", DEFAULT_TEMPERATURE)
    max_output_tokens = _parse_int_env("GEMINI_MAX_OUTPUT_TOKENS", DEFAULT_MAX_OUTPUT_TOKENS)

    config = {
        "temperature": temperature,
        "maxOutputTokens": max_output_tokens,
    }

    stop_sequences_raw = (os.getenv("GEMINI_STOP_SEQUENCES") or "").strip()
    if stop_sequences_raw:
        stop_sequences = [s.strip() for s in stop_sequences_raw.split(",") if s.strip()]
        if stop_sequences:
            config["stopSequences"] = stop_sequences[:5]

    return config


def _extract_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
        error = payload.get("error") or {}
        message = error.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
    except ValueError:
        pass

    text = (response.text or "").strip()
    if not text:
        return "unknown_error"
    return text[:300]


def _request_stream(model: str, payload: dict, api_key: str) -> requests.Response:
    url = f"{GEMINI_BASE_URL}/{model}:streamGenerateContent"
    last_error = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.post(
                url,
                params={"alt": "sse", "key": api_key},
                json=payload,
                stream=True,
                timeout=(REQUEST_CONNECT_TIMEOUT_SECONDS, REQUEST_READ_TIMEOUT_SECONDS),
            )
        except requests.RequestException as exc:
            last_error = LLMServiceError(
                f"gemini_connection_error:{model}:{exc}",
                status_code=503,
                retryable=True,
            )
            if attempt < MAX_RETRIES:
                time.sleep(0.5 * (2**attempt))
                continue
            raise last_error from exc

        if response.ok:
            return response

        status_code = response.status_code
        error_message = _extract_error_message(response)
        retryable = status_code in RETRYABLE_STATUS_CODES
        response.close()
        last_error = LLMServiceError(
            f"gemini_upstream_error:{model}:{status_code}:{error_message}",
            status_code=status_code,
            retryable=retryable,
        )
        if not retryable or attempt >= MAX_RETRIES:
            raise last_error
        time.sleep(0.5 * (2**attempt))

    if last_error:
        raise last_error
    raise LLMServiceError("gemini_unknown_error", status_code=503, retryable=True)


def _extract_text(payload: dict) -> str:
    if not isinstance(payload, dict):
        return ""
    candidates = payload.get("candidates") or []
    chunks = []
    for candidate in candidates:
        content = candidate.get("content") or {}
        parts = content.get("parts") or []
        for part in parts:
            text = part.get("text")
            if text:
                chunks.append(text)
    return "".join(chunks)


def _extract_usage(payload: dict) -> dict | None:
    if not isinstance(payload, dict):
        return None
    usage_meta = payload.get("usageMetadata") or {}
    if not isinstance(usage_meta, dict):
        return None

    input_tokens = usage_meta.get("promptTokenCount")
    cached_tokens = usage_meta.get("cachedContentTokenCount")
    thoughts_tokens = usage_meta.get("thoughtsTokenCount")
    output_tokens = usage_meta.get("candidatesTokenCount")
    total_tokens = usage_meta.get("totalTokenCount")

    if (
        input_tokens is None
        and cached_tokens is None
        and thoughts_tokens is None
        and output_tokens is None
        and total_tokens is None
    ):
        return None

    return {
        "input_tokens": int(input_tokens or 0),
        "cached_tokens": int(cached_tokens or 0),
        "thoughts_tokens": int(thoughts_tokens or 0),
        "output_tokens": int(output_tokens or 0),
        "total_tokens": int(total_tokens or 0),
    }


def _extract_finish_reason(payload: dict) -> str | None:
    if not isinstance(payload, dict):
        return None
    candidates = payload.get("candidates") or []
    for candidate in candidates:
        finish_reason = candidate.get("finishReason")
        if isinstance(finish_reason, str) and finish_reason.strip():
            return finish_reason.strip()
    return None


def _iter_sse_data(response: requests.Response):
    data_lines = []
    for raw_line in response.iter_lines(decode_unicode=False):
        if raw_line is None:
            continue

        line = raw_line.decode("utf-8", errors="replace")
        if line == "":
            if data_lines:
                yield "\n".join(data_lines)
                data_lines = []
            continue

        if line.startswith(":"):
            continue

        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())

    if data_lines:
        yield "\n".join(data_lines)


def generate_divination(system_prompt, user_prompt, usage_callback: Callable[[dict], None] | None = None):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY in environment.")

    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt or ""}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt or ""}]}],
        "generationConfig": _resolve_generation_config(),
    }

    errors = []
    models = _resolve_models()
    for index, model in enumerate(models):
        latest_usage = None
        latest_finish_reason = None
        try:
            response = _request_stream(model, payload, api_key)
        except LLMServiceError as exc:
            errors.append(str(exc))
            has_next_model = index < len(models) - 1
            if has_next_model and (exc.retryable or exc.status_code == 404):
                continue
            raise

        with response:
            # Gemini SSE payload is UTF-8; force explicit decoding to avoid mojibake.
            response.encoding = "utf-8"
            try:
                for data_str in _iter_sse_data(response):
                    if not data_str or data_str == "[DONE]":
                        continue
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    payload_items = data if isinstance(data, list) else [data]
                    for item in payload_items:
                        text = _extract_text(item)
                        if text:
                            yield text
                        usage = _extract_usage(item)
                        if usage:
                            latest_usage = usage
                        finish_reason = _extract_finish_reason(item)
                        if finish_reason:
                            latest_finish_reason = finish_reason
            except requests.RequestException as exc:
                raise LLMServiceError(
                    f"gemini_stream_error:{model}:{exc}",
                    status_code=503,
                    retryable=True,
                ) from exc
        if usage_callback and (latest_usage or latest_finish_reason):
            usage_payload = dict(latest_usage or {})
            if latest_finish_reason:
                usage_payload["finish_reason"] = latest_finish_reason
            usage_payload["model"] = model
            usage_callback(usage_payload)
        return

    error_message = " | ".join(errors) if errors else "gemini_no_models_available"
    raise LLMServiceError(error_message, status_code=503, retryable=True)
