"""Featured ClawRouter chat model catalog for Hermes pickers.

The full BlockRun catalog is maintained by the ClawRouter service. This list is
intentionally curated for Telegram/gateway pickers: it prevents Hermes from
rendering ``ClawRouter (0 models)`` without flooding small inline keyboards.
"""

from __future__ import annotations

CHAT_MODELS = (
    "blockrun/auto",
    "blockrun/free",
    "blockrun/eco",
    "blockrun/premium",
    "openai/gpt-5.5",
    "openai/gpt-5.4",
    "openai/gpt-5-mini",
    "anthropic/claude-opus-4.8",
    "anthropic/claude-opus-4.7",
    "anthropic/claude-sonnet-4.6",
    "google/gemini-2.5-pro",
    "google/gemini-2.5-flash",
    "moonshot/kimi-k2.6",
    "deepseek/deepseek-chat",
    "zai/glm-5.1",
    "xai/grok-4-1-fast-reasoning",
    "xai/grok-code-fast-1",
    "minimax/minimax-m2.7",
    "nvidia/gpt-oss-120b",
)

FREE_MODELS = frozenset({
    "blockrun/free",
    "free",
    "nvidia/gpt-oss-120b",
})


def chat_models() -> list[str]:
    """Return a mutable copy of the curated chat model catalog."""
    return list(dict.fromkeys(CHAT_MODELS))


def is_free_model(model_id: str) -> bool:
    """Return True when a picker entry should be marked as free."""
    return model_id in FREE_MODELS


def picker_label(model_id: str) -> str:
    """Return a compact Telegram button label without changing model IDs."""
    short = model_id.split("/")[-1] if "/" in model_id else model_id
    if is_free_model(model_id):
        short = f"[FREE] {short}"
    if len(short) > 38:
        short = short[:35] + "..."
    return short
