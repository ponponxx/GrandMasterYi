import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_MODEL = "gemini-2.5-pro"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def _extract_text(payload: dict) -> str:
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


def generate_divination(system_prompt, user_prompt):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY in environment.")

    url = f"{GEMINI_BASE_URL}/{GEMINI_MODEL}:streamGenerateContent"
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt or ""}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt or ""}]}],
        "generationConfig": {"maxOutputTokens": 1500},
    }

    with requests.post(
        url,
        params={"alt": "sse", "key": api_key},
        json=payload,
        stream=True,
        timeout=90,
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            line = line.strip()
            if not line.startswith("data:"):
                continue
            data_str = line[5:].strip()
            if not data_str or data_str == "[DONE]":
                continue
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                continue
            text = _extract_text(data)
            if text:
                yield text

