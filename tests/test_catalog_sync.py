from __future__ import annotations

from pathlib import Path

from clawrouter_hermes import catalog_sync


def _entry(model_id: str, *, categories=("chat",), billing_mode="paid", available=True) -> dict:
    return {
        "id": model_id,
        "object": "model",
        "owned_by": model_id.split("/", 1)[0],
        "name": model_id,
        "categories": list(categories),
        "billing_mode": billing_mode,
        "available": available,
    }


def test_generate_picker_filters_non_chat_and_excluded_models():
    result = catalog_sync.generate_picker([
        _entry("openai/gpt-6-astra"),
        _entry("openai/gpt-5.1"),
        _entry("openai/gpt-5.6-luna"),
        _entry("openai/gpt-5.6-luna-pro"),
        _entry("openai/gpt-5.6-sol"),
        _entry("openai/gpt-5.6-sol-pro"),
        _entry("openai/gpt-5.5-pro"),
        _entry("openai/gpt-6-luna"),
        _entry("openjev", categories=("judgment",)),
        _entry("openai/gpt-image-1", categories=("image",)),
    ], current=[], cap=20)

    assert result.models == [
        "blockrun/auto",
        "blockrun/premium",
        "blockrun/eco",
        "blockrun/free",
        "blockrun/openai/gpt-6-astra",
        "blockrun/openai/gpt-6-luna",
        "blockrun/openai/gpt-5.6-sol",
        "blockrun/openai/gpt-5.6-luna",
    ]
    assert result.excluded["picker_excluded"] == [
        "blockrun/openai/gpt-5.1",
        "blockrun/openai/gpt-5.6-luna-pro",
        "blockrun/openai/gpt-5.6-sol-pro",
        "blockrun/openai/gpt-5.5-pro",
    ]
    assert "blockrun/openjev" in result.excluded["non_chat"]
    assert "blockrun/openai/gpt-image-1" in result.excluded["non_chat"]


def test_provider_ordering_is_deterministic_not_stale_current_order():
    catalog = [
        _entry("xai/grok-4.3"),
        _entry("xai/grok-4.6"),
        _entry("qwen/qwen3.7-max"),
        _entry("qwen/qwen3.8-flash"),
        _entry("minimax/minimax-m2.7"),
        _entry("minimax/minimax-m3"),
        _entry("xiaomi/mimo-v2.5"),
        _entry("xiaomi/mimo-v2.5-pro"),
    ]
    current = [
        "blockrun/xai/grok-4.3",
        "blockrun/qwen/qwen3.7-max",
        "blockrun/minimax/minimax-m2.7",
        "blockrun/xiaomi/mimo-v2.5",
    ]

    result = catalog_sync.generate_picker(catalog, current=current, cap=70)
    models = result.models

    assert models.index("blockrun/xai/grok-4.6") < models.index("blockrun/xai/grok-4.3")
    assert models.index("blockrun/qwen/qwen3.8-flash") < models.index("blockrun/qwen/qwen3.7-max")
    assert models.index("blockrun/minimax/minimax-m3") < models.index("blockrun/minimax/minimax-m2.7")
    assert models.index("blockrun/xiaomi/mimo-v2.5-pro") < models.index("blockrun/xiaomi/mimo-v2.5")


def test_anthropic_family_quotas_do_not_evict_other_families():
    catalog = [
        _entry("anthropic/claude-fable-5.1"),
        _entry("anthropic/claude-fable-5"),
        _entry("anthropic/claude-opus-5.5"),
        _entry("anthropic/claude-opus-5"),
        _entry("anthropic/claude-opus-4.8"),
        _entry("anthropic/claude-opus-4.7"),
        _entry("anthropic/claude-opus-4.5"),
        _entry("anthropic/claude-sonnet-5"),
        _entry("anthropic/claude-sonnet-4.6"),
        _entry("anthropic/claude-sonnet-4.5"),
        _entry("anthropic/claude-haiku-4.5"),
    ]

    result = catalog_sync.generate_picker(catalog, current=[], cap=14)
    anthropic = [model for model in result.models if model.startswith("blockrun/anthropic/")]

    assert anthropic == [
        "blockrun/anthropic/claude-fable-5.1",
        "blockrun/anthropic/claude-fable-5",
        "blockrun/anthropic/claude-opus-5.5",
        "blockrun/anthropic/claude-opus-5",
        "blockrun/anthropic/claude-opus-4.8",
        "blockrun/anthropic/claude-opus-4.7",
        "blockrun/anthropic/claude-sonnet-5",
        "blockrun/anthropic/claude-sonnet-4.6",
        "blockrun/anthropic/claude-sonnet-4.5",
        "blockrun/anthropic/claude-haiku-4.5",
    ]
    assert "blockrun/anthropic/claude-opus-4.5" not in anthropic


def test_backfill_reaches_cap_when_supported_catalog_has_room():
    catalog = []
    for idx in range(1, 25):
        catalog.append(_entry(f"openai/gpt-5.{idx}"))
    for idx in range(1, 20):
        catalog.append(_entry(f"google/gemini-3.{idx}-flash"))
    for idx in range(1, 15):
        catalog.append(_entry(f"zai/glm-5.{idx}"))
    for idx in range(1, 15):
        catalog.append(_entry(f"deepseek/deepseek-v4.{idx}-pro"))
    for idx in range(1, 10):
        catalog.append(_entry(f"nvidia/free-fake-{idx}", billing_mode="free"))

    result = catalog_sync.generate_picker(catalog, current=[], cap=70)

    assert len(result.models) == 70
    assert result.models[:4] == list(catalog_sync.ROUTER_MODELS)
    assert all(model.startswith("blockrun/free/") for model in result.models[-9:])


def test_materialized_provider_roundtrip(tmp_path: Path):
    provider_init = tmp_path / "__init__.py"
    provider_init.write_text('_STATIC_FALLBACKS = ("old",)\n', encoding="utf-8")

    backup = catalog_sync.write_materialized_provider(provider_init, ["blockrun/auto", "blockrun/openai/gpt-6-astra"])

    assert backup.is_file()
    assert catalog_sync.read_materialized_provider(provider_init) == [
        "blockrun/auto",
        "blockrun/openai/gpt-6-astra",
    ]
