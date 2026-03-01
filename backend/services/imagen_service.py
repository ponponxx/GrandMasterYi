import json
import os
from typing import Any

import requests

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_IMAGEN_MODEL = "imagen-4.0-fast-generate-001"
DEFAULT_GEMINI_IMAGE_MODEL = "gemini-3.1-flash-image-preview"
DEFAULT_IMAGE_ASPECT_RATIO = "9:16"
DEFAULT_GEMINI_IMAGE_SIZE = "1K"
REQUEST_CONNECT_TIMEOUT_SECONDS = 10
REQUEST_READ_TIMEOUT_SECONDS = 180


class ImagenServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


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
    return text[:300] if text else "unknown_error"


def _parse_non_empty_env(var_name: str, default_value: str) -> str:
    raw = (os.getenv(var_name) or "").strip()
    return raw or default_value


def _post_predict(model: str, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
    url = f"{GEMINI_BASE_URL}/{model}:predict"
    try:
        response = requests.post(
            url,
            params={"key": api_key},
            json=payload,
            timeout=(REQUEST_CONNECT_TIMEOUT_SECONDS, REQUEST_READ_TIMEOUT_SECONDS),
        )
    except requests.RequestException as exc:
        raise ImagenServiceError(f"imagen_connection_error:{model}:{exc}", status_code=503) from exc

    if not response.ok:
        message = _extract_error_message(response)
        raise ImagenServiceError(
            f"imagen_upstream_error:{model}:{response.status_code}:{message}",
            status_code=response.status_code if response.status_code else 503,
        )

    try:
        return response.json()
    except ValueError as exc:
        raise ImagenServiceError(f"imagen_invalid_json:{model}", status_code=502) from exc


def _post_generate_content(model: str, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
    url = f"{GEMINI_BASE_URL}/{model}:generateContent"
    try:
        response = requests.post(
            url,
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=(REQUEST_CONNECT_TIMEOUT_SECONDS, REQUEST_READ_TIMEOUT_SECONDS),
        )
    except requests.RequestException as exc:
        raise ImagenServiceError(f"gemini_image_connection_error:{model}:{exc}", status_code=503) from exc

    if not response.ok:
        message = _extract_error_message(response)
        raise ImagenServiceError(
            f"gemini_image_upstream_error:{model}:{response.status_code}:{message}",
            status_code=response.status_code if response.status_code else 503,
        )

    try:
        return response.json()
    except ValueError as exc:
        raise ImagenServiceError(f"gemini_image_invalid_json:{model}", status_code=502) from exc


def _extract_first_image(payload: dict[str, Any]) -> tuple[str, str, str | None]:
    predictions = payload.get("predictions")
    if not isinstance(predictions, list) or not predictions:
        raise ImagenServiceError("imagen_empty_predictions", status_code=502)

    first = predictions[0]
    if not isinstance(first, dict):
        raise ImagenServiceError("imagen_invalid_prediction_item", status_code=502)

    image_b64 = first.get("bytesBase64Encoded")
    mime_type = first.get("mimeType") or "image/png"
    enhanced_prompt = first.get("prompt")

    if not isinstance(image_b64, str) or not image_b64.strip():
        raise ImagenServiceError("imagen_missing_image_bytes", status_code=502)
    if not isinstance(mime_type, str) or not mime_type.strip():
        mime_type = "image/png"
    if not isinstance(enhanced_prompt, str):
        enhanced_prompt = None

    return image_b64.strip(), mime_type.strip(), enhanced_prompt


def _extract_first_gemini_image(payload: dict[str, Any]) -> tuple[str, str]:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        raise ImagenServiceError("gemini_image_missing_candidates", status_code=502)

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content") or {}
        parts = content.get("parts") or []
        for part in parts:
            if not isinstance(part, dict):
                continue
            inline_data = part.get("inlineData") or part.get("inline_data")
            if not isinstance(inline_data, dict):
                continue
            image_b64 = inline_data.get("data")
            mime_type = inline_data.get("mimeType") or inline_data.get("mime_type") or "image/png"
            if isinstance(image_b64, str) and image_b64.strip():
                return image_b64.strip(), str(mime_type).strip()

    raise ImagenServiceError("gemini_image_missing_inline_data", status_code=502)


def _extract_gemini_usage_metadata(payload: dict[str, Any]) -> dict[str, Any] | None:
    usage_meta = payload.get("usageMetadata")
    if not isinstance(usage_meta, dict):
        return None
    if not usage_meta:
        return None
    return usage_meta


def _generate_with_imagen(prompt_text: str, api_key: str, aspect_ratio: str) -> dict[str, Any]:
    model = (os.getenv("IMAGEN_MODEL") or DEFAULT_IMAGEN_MODEL).strip() or DEFAULT_IMAGEN_MODEL
    base_request = {
        "instances": [{"prompt": prompt_text}],
    }
    preferred_payload = {
        **base_request,
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": aspect_ratio,
            "enhancePrompt": False,
        },
    }
    fallback_keep_ratio_payload = {
        **base_request,
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": aspect_ratio,
        },
    }
    fallback_payload = {
        **base_request,
        "parameters": {
            "sampleCount": 1,
        },
    }

    try:
        payload = _post_predict(model, preferred_payload, api_key)
    except ImagenServiceError as exc:
        retryable_bad_request = exc.status_code == 400
        if not retryable_bad_request:
            raise
        try:
            payload = _post_predict(model, fallback_keep_ratio_payload, api_key)
        except ImagenServiceError as ratio_exc:
            retryable_ratio_bad_request = ratio_exc.status_code == 400
            if not retryable_ratio_bad_request:
                raise
            payload = _post_predict(model, fallback_payload, api_key)

    image_b64, mime_type, enhanced_prompt = _extract_first_image(payload)
    return {
        "provider": "imagen4_fast",
        "model": model,
        "mime_type": mime_type,
        "image_b64": image_b64,
        "prompt_used": enhanced_prompt or prompt_text,
    }


def _generate_with_gemini_image(prompt_text: str, api_key: str, aspect_ratio: str) -> dict[str, Any]:
    model = (os.getenv("GEMINI_IMAGE_MODEL") or DEFAULT_GEMINI_IMAGE_MODEL).strip() or DEFAULT_GEMINI_IMAGE_MODEL
    image_size = _parse_non_empty_env("GEMINI_IMAGE_SIZE", DEFAULT_GEMINI_IMAGE_SIZE)
    base_payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt_text}]}],
    }
    text_image_payload = {
        **base_payload,
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {
                "aspectRatio": aspect_ratio,
                "imageSize": image_size,
            },
        },
    }
    image_only_payload = {
        **base_payload,
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {
                "aspectRatio": aspect_ratio,
                "imageSize": image_size,
            },
        },
    }
    minimal_payload = {
        **base_payload,
        "generationConfig": {
            "imageConfig": {
                "aspectRatio": aspect_ratio,
                "imageSize": image_size,
            },
        },
    }

    size_mode = "text_and_image"
    try:
        response_payload = _post_generate_content(model, text_image_payload, api_key)
    except ImagenServiceError as exc:
        if exc.status_code != 400:
            raise
        print(
            f"[gemini_image_config_fallback] model={model} mode=text_and_image->image_only",
            flush=True,
        )
        size_mode = "image_only"
        try:
            response_payload = _post_generate_content(model, image_only_payload, api_key)
        except ImagenServiceError as fallback_exc:
            if fallback_exc.status_code != 400:
                raise
            print(
                f"[gemini_image_config_fallback] model={model} mode=image_only->minimal",
                flush=True,
            )
            size_mode = "minimal"
            response_payload = _post_generate_content(model, minimal_payload, api_key)

    image_b64, mime_type = _extract_first_gemini_image(response_payload)
    usage_metadata = _extract_gemini_usage_metadata(response_payload)
    if usage_metadata:
        print(
            f"[gemini_image_usage] model={model} usage={json.dumps(usage_metadata, ensure_ascii=False)}",
            flush=True,
        )
    return {
        "provider": "gemini31_flash_image_preview",
        "model": model,
        "mime_type": mime_type,
        "image_b64": image_b64,
        "prompt_used": prompt_text,
        "token_usage": usage_metadata,
        "image_size": image_size,
        "aspect_ratio": aspect_ratio,
        "size_mode": size_mode,
    }


def generate_ad_image(
    prompt: str,
    aspect_ratio: str = DEFAULT_IMAGE_ASPECT_RATIO,
    model_selector: str = "imagen4_fast",
) -> dict[str, Any]:
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key:
        raise ImagenServiceError("missing_gemini_api_key", status_code=500)

    prompt_text = (prompt or "").strip()
    if not prompt_text:
        raise ImagenServiceError("empty_prompt", status_code=400)

    selector = (model_selector or "").strip().lower()
    if selector == "gemini31_flash_image_preview":
        return _generate_with_gemini_image(prompt_text, api_key, aspect_ratio)
    if selector == "imagen4_fast":
        return _generate_with_imagen(prompt_text, api_key, aspect_ratio)

    raise ImagenServiceError(f"unsupported_model_selector:{selector}", status_code=400)
