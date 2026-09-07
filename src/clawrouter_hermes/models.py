"""Featured ClawRouter chat model catalog for Hermes pickers.

The full BlockRun catalog is maintained by the ClawRouter service. This list is
intentionally curated for Telegram/gateway pickers: it prevents Hermes from
rendering ``ClawRouter (0 models)`` without flooding small inline keyboards.
"""

from __future__ import annotations

# Curated, provider-grouped picker order. Keep this list in lockstep with the
# materialized provider template below.
CHAT_MODELS = (
    "blockrun/auto",
    "blockrun/premium",
    "blockrun/eco",
    "blockrun/free",
    "blockrun/anthropic/claude-fable-5",
    "blockrun/anthropic/claude-opus-5",
    "blockrun/anthropic/claude-opus-4.8",
    "blockrun/anthropic/claude-opus-4.7",
    "blockrun/anthropic/claude-sonnet-5",
    "blockrun/anthropic/claude-sonnet-4.6",
    "blockrun/anthropic/claude-haiku-4.5",
    "blockrun/openai/gpt-5.6-terra",
    "blockrun/openai/gpt-5.6-sol",
    "blockrun/openai/gpt-5.6-luna",
    "blockrun/openai/gpt-5.5",
    "blockrun/openai/gpt-5.5-pro",
    "blockrun/openai/gpt-5.4-pro",
    "blockrun/openai/gpt-5.4",
    "blockrun/openai/gpt-5.4-mini",
    "blockrun/openai/gpt-5.4-nano",
    "blockrun/openai/gpt-5.3-codex",
    "blockrun/google/gemini-3.1-pro",
    "blockrun/google/gemini-3.8-flash",
    "blockrun/google/gemini-3.6-flash",
    "blockrun/google/gemini-3.5-flash",
    "blockrun/google/gemini-3.5-flash-lite",
    "blockrun/google/gemini-3.1-flash-lite",
    "blockrun/google/gemini-3-flash-preview",
    "blockrun/xai/grok-4.5",
    "blockrun/xai/grok-4.3",
    "blockrun/xai/grok-build-0.1",
    "blockrun/zai/glm-5.3",
    "blockrun/zai/glm-5.3-flash",
    "blockrun/zai/glm-5.2",
    "blockrun/zai/glm-5.1",
    "blockrun/zai/glm-5-turbo",
    "blockrun/zai/glm-5",
    "blockrun/xiaomi/mimo-v2.5",
    "blockrun/xiaomi/mimo-v2.5-pro",
    "blockrun/minimax/minimax-m3",
    "blockrun/minimax/minimax-m2.7",
    "blockrun/moonshot/kimi-k3",
    "blockrun/qwen/qwen3.7-max",
    "blockrun/qwen/qwen3.8-flash",
    "blockrun/tencent/hy3",
    "blockrun/deepseek/deepseek-v4-flash-vision-exp",
    "blockrun/deepseek/deepseek-v4-pro",
    "blockrun/deepseek/deepseek-chat",
    "blockrun/deepseek/deepseek-reasoner",
    "blockrun/free/nemotron-3.5-lightning",
    "blockrun/free/nemotron-3-nano-30b",
    "blockrun/free/laguna-xs-2.1",
    "blockrun/free/north-mini-code",
    "blockrun/free/nemotron-3-nano-omni-30b-a3b-reasoning",
    "blockrun/free/nemotron-3-ultra-550b",
    "blockrun/free/llama-3.2-11b-vision",
)

def chat_models() -> list[str]:
    """Return a mutable copy of the curated chat model catalog."""
    return list(dict.fromkeys(CHAT_MODELS))


def is_free_model(model_id: str) -> bool:
    """Return True when a picker entry should be marked as free."""
    return model_id == "blockrun/free" or model_id.startswith("blockrun/free/")


def picker_label(model_id: str) -> str:
    """Return a compact Telegram button label without changing model IDs."""
    short = model_id.split("/")[-1] if "/" in model_id else model_id
    if is_free_model(model_id):
        short = f"[FREE] {short}"
    if len(short) > 38:
        short = short[:35] + "..."
    return short
