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
    "google/gemini-3.1-pro",
    "google/gemini-3.5-flash",
    "moonshot/kimi-k2.6",
    "deepseek/deepseek-v4-pro",
    "deepseek/deepseek-chat",
    "zai/glm-5.1",
    "xai/grok-4.3",
    "xai/grok-build-0.1",
    "minimax/minimax-m3",
    "free/gpt-oss-120b",
    "free/gpt-oss-20b",
    "free/mistral-large-3-675b",
    "free/qwen3.5-122b-a10b",
    "free/llama-4-maverick",
    "free/qwen3-coder-480b",
    "free/nemotron-3-nano-omni-30b-a3b-reasoning",
)

FREE_MODELS = frozenset({
    "blockrun/free",
    "free/gpt-oss-120b",
    "free/gpt-oss-20b",
    "free/mistral-large-3-675b",
    "free/qwen3.5-122b-a10b",
    "free/llama-4-maverick",
    "free/qwen3-coder-480b",
    "free/nemotron-3-nano-omni-30b-a3b-reasoning",
})


def chat_models() -> list[str]:
    """Return a mutable copy of the curated chat model catalog."""
    return list(dict.fromkeys(CHAT_MODELS))


def is_free_model(model_id: str) -> bool:
    """Return True when a picker entry should be marked as free."""
    return (
        model_id == "blockrun/free"
        or model_id.startswith("free/")
        or model_id in FREE_MODELS
    )


def picker_label(model_id: str) -> str:
    """Return a compact Telegram button label without changing model IDs."""
    short = model_id.split("/")[-1] if "/" in model_id else model_id
    if is_free_model(model_id):
        short = f"[FREE] {short}"
    if len(short) > 38:
        short = short[:35] + "..."
    return short
