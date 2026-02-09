"""
Thin HTTP client for calling an OpenAI-compatible chat completion API.

This is intentionally minimal and reads configuration from `config.py`:
- API key:   OPENAI_API_KEY
- API base:  OPENAI_API_BASE (default https://api.openai.com/v1)
- Model:     OPENAI_MODEL    (default gpt-4o-mini)
"""
from __future__ import annotations

from typing import Optional

import requests

from config import get_llm_api_key, get_llm_api_base, get_llm_model


class LLMError(RuntimeError):
    """Raised when the LLM API call fails."""


def ask_llm(prompt: str, system_prompt: Optional[str] = None) -> str:
    """
    Call the LLM with the given prompt and optional system instructions.

    Returns:
        The assistant's reply text.
    """
    api_key = get_llm_api_key()
    if not api_key:
        raise LLMError("LLM API key is not configured. Set OPENAI_API_KEY in .env.")

    base_url = get_llm_api_base()
    model = get_llm_model()

    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
    except requests.RequestException as exc:
        raise LLMError(f"LLM request failed: {exc}") from exc

    if resp.status_code != 200:
        raise LLMError(f"LLM API error {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"Unexpected LLM response format: {data}") from exc

