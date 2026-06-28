"""LLM client for the reasoning agents (architecture §7.1).

Thin wrapper over Anthropic Claude that returns parsed JSON for structured agent output.
Mirrors the extraction client: ``anthropic`` is imported lazily and only used when an API key
is configured. When unavailable (no key / offline / error) callers fall back to deterministic
reasoning, and the case is marked ``degraded`` — the system never silently produces output.

Temperature is fixed at 0.0 for deterministic clinical output. The verifier uses a separate
client instance with no view of other agents' chain-of-thought (independent re-check).
"""

from __future__ import annotations

import json
from typing import Any

from app.config import settings


class LLMUnavailable(RuntimeError):
    """Raised when the LLM cannot be reached so the caller can degrade gracefully."""


def is_available() -> bool:
    return bool(settings.anthropic_api_key)


def _extract_json(text: str) -> dict[str, Any]:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise LLMUnavailable("No JSON object in model response")
    return json.loads(text[start : end + 1])


class LLMClient:
    """Synchronous Claude client (called from a worker thread by the async orchestrator)."""

    def __init__(self, model: str | None = None, max_tokens: int | None = None) -> None:
        self.model = model or settings.anthropic_model
        self.max_tokens = max_tokens or settings.anthropic_max_tokens

    def available(self) -> bool:
        return is_available()

    def complete_json(self, system: str, user: str, *, retries: int = 2) -> dict[str, Any]:
        """Return the parsed JSON object from a single-turn completion.

        Raises ``LLMUnavailable`` on missing key or repeated failure so the agent degrades.
        """
        if not is_available():
            raise LLMUnavailable("ANTHROPIC_API_KEY not configured")

        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        last_err: Exception | None = None
        for _ in range(retries + 1):
            try:
                message = client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=0.0,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                text = "".join(b.text for b in message.content if b.type == "text")
                return _extract_json(text)
            except Exception as exc:  # noqa: BLE001 — surfaced to caller as LLMUnavailable
                last_err = exc
        raise LLMUnavailable(str(last_err))
