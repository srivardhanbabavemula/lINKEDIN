"""Unified local LLM client — Ollama and LM Studio (OpenAI-compatible)."""

from __future__ import annotations

import json
from typing import Any

import requests

import config

PROVIDERS = ("ollama", "lmstudio")


def generate(prompt: str, temperature: float = 0.3) -> str:
    provider = config.LLM_PROVIDER.lower()
    if provider == "lmstudio":
        return _lmstudio_generate(prompt, temperature)
    return _ollama_generate(prompt, temperature)


def _ollama_generate(prompt: str, temperature: float) -> str:
    response = requests.post(
        f"{config.OLLAMA_HOST}/api/generate",
        json={
            "model": config.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        },
        timeout=180,
    )
    response.raise_for_status()
    return response.json().get("response", "").strip()


def _lmstudio_generate(prompt: str, temperature: float) -> str:
    """LM Studio exposes an OpenAI-compatible API on port 1234 by default."""
    response = requests.post(
        f"{config.LMSTUDIO_HOST}/v1/chat/completions",
        json={
            "model": config.LMSTUDIO_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        },
        timeout=180,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def health_check() -> dict[str, Any]:
    provider = config.LLM_PROVIDER.lower()
    try:
        if provider == "lmstudio":
            r = requests.get(f"{config.LMSTUDIO_HOST}/v1/models", timeout=5)
            r.raise_for_status()
            return {"ok": True, "provider": "lmstudio", "host": config.LMSTUDIO_HOST}
        r = requests.get(f"{config.OLLAMA_HOST}/api/tags", timeout=5)
        r.raise_for_status()
        models = [m.get("name") for m in r.json().get("models", [])]
        return {"ok": True, "provider": "ollama", "models": models}
    except Exception as exc:
        return {"ok": False, "provider": provider, "error": str(exc)}
