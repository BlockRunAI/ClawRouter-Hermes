"""Starter ClawRouter chat model catalog for Hermes pickers.

The full BlockRun catalog is maintained by the ClawRouter service. This list is
intentionally small: it prevents Hermes gateway pickers from rendering
``ClawRouter (0 models)`` while avoiding a stale copy of the complete catalog.
"""

from __future__ import annotations

CHAT_MODELS = (
    "blockrun/auto",
    "auto",
    "free",
    "eco",
    "premium",
    "openai/gpt-5.5",
    "anthropic/claude-opus-4.7",
    "google/gemini-2.5-pro",
    "moonshot/kimi-k2.6",
    "nvidia/deepseek-v4-flash",
    "deepseek/deepseek-chat",
    "minimax/minimax-m2.7",
)


def chat_models() -> list[str]:
    """Return a mutable copy of the curated chat model catalog."""
    return list(CHAT_MODELS)
