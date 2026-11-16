"""Bring-your-own-LLM client.

Two wire formats cover almost every provider:

* ``openai``    — any OpenAI-compatible Chat Completions endpoint: OpenAI, Groq,
                  OpenRouter, Together, DeepSeek, Mistral, Google Gemini
                  (OpenAI-compatible endpoint), LM Studio and Ollama (``/v1``).
* ``anthropic`` — Claude via the Anthropic Messages API.

The active provider is stored (API key encrypted) via the Settings page or the
``configure_llm`` MCP tool.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import httpx

from . import db

PRESETS: dict[str, dict[str, str]] = {
    "openai": {"format": "openai", "base_url": "https://api.openai.com/v1", "model": "gpt-4.1-mini"},
    "anthropic": {"format": "anthropic", "base_url": "https://api.anthropic.com/v1", "model": "claude-sonnet-5-5"},
    "gemini": {
        "format": "openai",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-2.5-flash",
    },
    "groq": {"format": "openai", "base_url": "https://api.groq.com/openai/v1", "model": "llama-3.3-70b-versatile"},
    "openrouter": {"format": "openai", "base_url": "https://openrouter.ai/api/v1", "model": "openai/gpt-4.1-mini"},
    "deepseek": {"format": "openai", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
    "ollama": {"format": "openai", "base_url": "http://localhost:11434/v1", "model": "llama3.1"},
    "custom": {"format": "openai", "base_url": "", "model": ""},
}


@dataclass
class LLMConfig:
    provider: str = "openai"
    format: str = "openai"
    base_url: str = PRESETS["openai"]["base_url"]
    model: str = PRESETS["openai"]["model"]
    api_key: str = ""
    temperature: float = 0.8

    def public(self) -> dict:
        d = asdict(self)
        d["api_key"] = ("•" * 8 + self.api_key[-4:]) if self.api_key else ""
        return d


class LLMError(RuntimeError):
    pass


def load_config() -> LLMConfig:
    data = db.get_value("llm_config")
    if not data:
        return LLMConfig()
    return LLMConfig(**data)


def save_config(provider: str, model: str = "", api_key: str = "", base_url: str = "", temperature: float = 0.8) -> LLMConfig:
    preset = PRESETS.get(provider, PRESETS["custom"])
    current = load_config()
    cfg = LLMConfig(
        provider=provider,
        format=preset["format"],
        base_url=(base_url or preset["base_url"]).rstrip("/"),
        model=model or preset["model"],
        # Keep the existing key when the form leaves it blank.
        api_key=api_key or (current.api_key if current.provider == provider else ""),
        temperature=temperature,
    )
    db.set_value("llm_config", asdict(cfg), secret=True)
    return cfg


def complete(system: str, user: str, *, max_tokens: int = 1800, cfg: LLMConfig | None = None) -> str:
    cfg = cfg or load_config()
    if not cfg.base_url or not cfg.model:
        raise LLMError("No LLM configured. Open Settings and connect a model provider.")
    if cfg.provider not in ("ollama",) and not cfg.api_key and "localhost" not in cfg.base_url:
        raise LLMError(f"Missing API key for provider '{cfg.provider}'.")

    try:
        if cfg.format == "anthropic":
            r = httpx.post(
                f"{cfg.base_url}/messages",
                headers={
                    "x-api-key": cfg.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": cfg.model,
                    "max_tokens": max_tokens,
                    "temperature": cfg.temperature,
                    "system": system,
                    "messages": [{"role": "user", "content": user}],
                },
                timeout=120,
            )
            r.raise_for_status()
            return "".join(b.get("text", "") for b in r.json().get("content", [])).strip()

        headers = {"content-type": "application/json"}
        if cfg.api_key:
            headers["authorization"] = f"Bearer {cfg.api_key}"
        r = httpx.post(
            f"{cfg.base_url}/chat/completions",
            headers=headers,
            json={
                "model": cfg.model,
                "temperature": cfg.temperature,
                "max_tokens": max_tokens,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            },
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except httpx.HTTPStatusError as e:  # surface provider error text
        raise LLMError(f"{cfg.provider} returned {e.response.status_code}: {e.response.text[:400]}") from e
    except httpx.HTTPError as e:
        raise LLMError(f"Could not reach {cfg.base_url}: {e}") from e
