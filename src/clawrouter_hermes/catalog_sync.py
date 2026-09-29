"""Live BlockRun catalog sync for the Hermes ClawRouter picker."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil
import time
import ast
from urllib.error import URLError
from urllib.request import urlopen

from . import models

CATALOG_URL = "https://blockrun.ai/api/v1/models"
ROUTER_MODELS = ("blockrun/auto", "blockrun/premium", "blockrun/eco", "blockrun/free")
MAX_PICKER_MODELS = 70
EXCLUDED_PICKER_MODELS = {
    "blockrun/openai/gpt-5.1",
}

PROVIDER_ORDER = (
    "anthropic",
    "openai",
    "google",
    "xai",
    "zai",
    "xiaomi",
    "minimax",
    "moonshot",
    "qwen",
    "tencent",
    "deepseek",
)

PROVIDER_LIMITS = {
    "anthropic": 10,
    "openai": 14,
    "google": 8,
    "xai": 4,
    "zai": 6,
    "xiaomi": 2,
    "minimax": 2,
    "moonshot": 2,
    "qwen": 3,
    "tencent": 2,
    "deepseek": 4,
}

ANTHROPIC_FAMILY_ORDER = {"fable": 0, "opus": 1, "sonnet": 2, "haiku": 3}
ANTHROPIC_FAMILY_LIMITS = {"fable": 2, "opus": 4, "sonnet": 3, "haiku": 1}
OPENAI_FAMILY_ORDER = {"astra": 0, "terra": 1, "sol": 2, "luna": 3}
OPENAI_SIZE_ORDER = {"pro": 0, "": 1, "mini": 2, "nano": 3}
GOOGLE_TIER_ORDER = {"pro": 0, "flash": 1, "flash-lite": 2, "lite": 3}
QWEN_TIER_ORDER = {"max": 0, "plus": 1, "flash": 2}
DEEPSEEK_TIER_ORDER = {"pro": 0, "reasoner": 1, "chat": 2, "flash": 3}


def _version_parts(model_id: str) -> tuple[int, ...]:
    match = re.search(r"(\d+(?:\.\d+)*)", model_id)
    if not match:
        return ()
    return tuple(int(part) for part in match.group(1).split("."))


def _desc_version_key(model_id: str) -> tuple[int, ...]:
    parts = _version_parts(model_id)
    padded = parts + (0,) * max(0, 4 - len(parts))
    return tuple(-part for part in padded[:4])


def _anthropic_family(model_id: str) -> str:
    lowered = model_id.lower()
    return next((name for name in ANTHROPIC_FAMILY_ORDER if name in lowered), "")


def _anthropic_sort_key(model_id: str) -> tuple:
    family = _anthropic_family(model_id)
    return (ANTHROPIC_FAMILY_ORDER.get(family, len(ANTHROPIC_FAMILY_ORDER)), _desc_version_key(model_id), model_id)


def _split_anthropic_family_quota(provider_models: list[str]) -> tuple[list[str], list[str]]:
    selected: list[str] = []
    overflow: list[str] = []
    by_family: dict[str, list[str]] = {family: [] for family in ANTHROPIC_FAMILY_ORDER}
    other: list[str] = []
    for model_id in provider_models:
        family = _anthropic_family(model_id)
        if family in by_family:
            by_family[family].append(model_id)
        else:
            other.append(model_id)
    for family in ANTHROPIC_FAMILY_ORDER:
        limit = ANTHROPIC_FAMILY_LIMITS.get(family, len(by_family[family]))
        selected.extend(by_family[family][:limit])
        overflow.extend(by_family[family][limit:])
    overflow.extend(other)
    return selected, overflow


def _openai_sort_key(model_id: str) -> tuple:
    lowered = model_id.lower()
    if "chat-latest" in lowered:
        return ((-5, -5, 0, 1), len(OPENAI_FAMILY_ORDER), OPENAI_SIZE_ORDER[""], model_id)
    family = next((name for name in OPENAI_FAMILY_ORDER if name in lowered), "")
    size = next((name for name in ("pro", "mini", "nano") if name in lowered), "")
    return (_desc_version_key(model_id), OPENAI_FAMILY_ORDER.get(family, len(OPENAI_FAMILY_ORDER)),
            OPENAI_SIZE_ORDER.get(size, OPENAI_SIZE_ORDER[""]), model_id)


def _google_sort_key(model_id: str) -> tuple:
    lowered = model_id.lower()
    tier = ""
    for candidate in ("flash-lite", "pro", "flash", "lite"):
        if candidate in lowered:
            tier = candidate
            break
    preview_penalty = 1 if "preview" in lowered else 0
    return (_desc_version_key(model_id), GOOGLE_TIER_ORDER.get(tier, len(GOOGLE_TIER_ORDER)), preview_penalty, model_id)


def _qwen_sort_key(model_id: str) -> tuple:
    lowered = model_id.lower()
    tier = ""
    for candidate in ("max", "plus", "flash"):
        if candidate in lowered:
            tier = candidate
            break
    return (_desc_version_key(model_id), QWEN_TIER_ORDER.get(tier, len(QWEN_TIER_ORDER)), model_id)


def _xiaomi_sort_key(model_id: str) -> tuple:
    return (_desc_version_key(model_id), 0 if "pro" in model_id.lower() else 1, model_id)


def _deepseek_sort_key(model_id: str) -> tuple:
    lowered = model_id.lower()
    tier = next((name for name in DEEPSEEK_TIER_ORDER if name in lowered), "")
    return (_desc_version_key(model_id), DEEPSEEK_TIER_ORDER.get(tier, len(DEEPSEEK_TIER_ORDER)), model_id)


def _version_first_sort_key(model_id: str) -> tuple:
    return (_desc_version_key(model_id), model_id)


def _provider_sort_key(provider: str, model_id: str, current_set: set[str], current_positions: dict[str, int],
                       current_len: int, live_position: int) -> tuple:
    if provider == "anthropic":
        return _anthropic_sort_key(model_id)
    if provider == "openai":
        return _openai_sort_key(model_id)
    if provider == "google":
        return _google_sort_key(model_id)
    if provider == "qwen":
        return _qwen_sort_key(model_id)
    if provider == "xiaomi":
        return _xiaomi_sort_key(model_id)
    if provider == "deepseek":
        return _deepseek_sort_key(model_id)
    if provider in {"xai", "zai", "minimax", "moonshot", "tencent"}:
        return _version_first_sort_key(model_id)
    return _version_first_sort_key(model_id)


@dataclass(frozen=True)
class SyncResult:
    models: list[str]
    added: list[str]
    removed: list[str]
    kept: list[str]
    excluded: dict[str, list[str]]


def fetch_catalog(url: str = CATALOG_URL, *, timeout: float = 10.0) -> list[dict]:
    """Fetch the live BlockRun model catalog."""
    try:
        with urlopen(url, timeout=timeout) as response:  # nosec B310 - fixed public catalog URL by default.
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"failed to fetch BlockRun catalog from {url}: {exc}") from exc
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        raise RuntimeError(f"BlockRun catalog response from {url} did not contain a data list")
    return [entry for entry in data if isinstance(entry, dict)]


def generate_picker(
    catalog: list[dict],
    *,
    current: list[str] | None = None,
    cap: int = MAX_PICKER_MODELS,
) -> SyncResult:
    """Generate a curated Hermes picker from the live BlockRun catalog."""
    current = list(current or models.chat_models())
    current_set = set(current)
    current_positions = {model_id: idx for idx, model_id in enumerate(current)}
    excluded: dict[str, list[str]] = {}
    paid_by_provider: dict[str, list[str]] = {provider: [] for provider in PROVIDER_ORDER}
    free: list[str] = []

    def exclude(reason: str, model_id: str) -> None:
        excluded.setdefault(reason, []).append(model_id)

    for entry in catalog:
        raw_id = str(entry.get("id") or "").strip()
        if not raw_id:
            continue
        model_id = f"blockrun/{raw_id}"
        categories = set(entry.get("categories") or [])
        if "chat" not in categories:
            exclude("non_chat", model_id)
            continue
        provider = raw_id.split("/", 1)[0] if "/" in raw_id else raw_id
        billing_mode = entry.get("billing_mode")
        if billing_mode == "free" or raw_id.startswith("free/"):
            slug = raw_id.split("/", 1)[1] if "/" in raw_id else raw_id
            free.append(f"blockrun/free/{slug}")
            continue
        if entry.get("available") is False:
            exclude("unavailable_paid", model_id)
            continue
        if provider not in paid_by_provider:
            exclude("provider_not_in_picker_order", model_id)
            continue
        if model_id in EXCLUDED_PICKER_MODELS or (provider == "openai" and raw_id.endswith("-pro")):
            exclude("picker_excluded", model_id)
            continue
        paid_by_provider[provider].append(model_id)

    paid: list[str] = []
    overflow_by_provider: dict[str, list[str]] = {}
    for provider in PROVIDER_ORDER:
        limit = PROVIDER_LIMITS.get(provider, len(paid_by_provider[provider]))
        provider_models = list(dict.fromkeys(paid_by_provider[provider]))
        live_positions = {model_id: idx for idx, model_id in enumerate(provider_models)}
        provider_models.sort(
            key=lambda model_id: _provider_sort_key(
                provider, model_id, current_set, current_positions, len(current), live_positions[model_id]
            )
        )
        if provider == "anthropic":
            selected, provider_overflow = _split_anthropic_family_quota(provider_models)
            paid.extend(selected[:limit])
            overflow_by_provider[provider] = [*selected[limit:], *provider_overflow]
        else:
            paid.extend(provider_models[:limit])
            overflow_by_provider[provider] = provider_models[limit:]

    free = list(dict.fromkeys(free))
    free.sort(key=_version_first_sort_key)
    if cap < len(ROUTER_MODELS) + len(free):
        free = free[: max(0, cap - len(ROUTER_MODELS))]
    paid_cap = max(0, cap - len(ROUTER_MODELS) - len(free))
    overflow: list[str] = []
    while any(overflow_by_provider.values()):
        for provider in PROVIDER_ORDER:
            if overflow_by_provider[provider]:
                overflow.append(overflow_by_provider[provider].pop(0))
    paid = list(dict.fromkeys([*paid, *overflow]))
    generated = list(ROUTER_MODELS) + paid[:paid_cap] + free
    generated = list(dict.fromkeys(generated))

    generated_set = set(generated)
    return SyncResult(
        models=generated,
        added=[model_id for model_id in generated if model_id not in current_set],
        removed=[model_id for model_id in current if model_id not in generated_set],
        kept=[model_id for model_id in generated if model_id in current_set],
        excluded=excluded,
    )


def result_summary(result: SyncResult) -> str:
    """Render a human-readable dry-run summary."""
    lines = [
        f"Final picker count: {len(result.models)}",
        f"Added: {len(result.added)}",
    ]
    lines.extend(f"  + {model_id}" for model_id in result.added)
    lines.append(f"Removed: {len(result.removed)}")
    lines.extend(f"  - {model_id}" for model_id in result.removed)
    lines.append("Provider groups:")
    for provider in ("router",) + PROVIDER_ORDER + ("free",):
        if provider == "router":
            group = [model_id for model_id in result.models if model_id in ROUTER_MODELS]
        elif provider == "free":
            group = [model_id for model_id in result.models if model_id.startswith("blockrun/free/")]
        else:
            prefix = f"blockrun/{provider}/"
            group = [model_id for model_id in result.models if model_id.startswith(prefix)]
        if group:
            lines.append(f"  {provider}: {len(group)}")
            lines.extend(f"    {model_id}" for model_id in group)
    return "\n".join(lines)


def render_static_fallbacks(model_ids: list[str]) -> str:
    lines = ["_STATIC_FALLBACKS = (\n"]
    lines.extend(f'    "{model_id}",\n' for model_id in model_ids)
    lines.append(")")
    return "".join(lines)


def replace_static_fallbacks(source: str, model_ids: list[str]) -> str:
    """Replace the materialized provider's static fallback tuple."""
    pattern = re.compile(r"_STATIC_FALLBACKS\s*=\s*\(.*?\)\n", re.DOTALL)
    replacement = render_static_fallbacks(model_ids) + "\n"
    updated, count = pattern.subn(replacement, source, count=1)
    if count != 1:
        raise RuntimeError("_STATIC_FALLBACKS tuple not found in materialized provider")
    return updated


def extract_static_fallbacks(source: str) -> list[str]:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "_STATIC_FALLBACKS"
            for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            return [str(model_id) for model_id in value]
    raise RuntimeError("_STATIC_FALLBACKS tuple not found in materialized provider")


def read_materialized_provider(provider_init: Path) -> list[str]:
    return extract_static_fallbacks(provider_init.read_text(encoding="utf-8"))


def write_materialized_provider(provider_init: Path, model_ids: list[str]) -> Path:
    """Back up and update a materialized Hermes ClawRouter provider file."""
    source = provider_init.read_text(encoding="utf-8")
    updated = replace_static_fallbacks(source, model_ids)
    backup = provider_init.with_suffix(
        provider_init.suffix + f".before-catalog-sync-{time.strftime('%Y%m%d-%H%M%S')}-{time.time_ns()}"
    )
    shutil.copy2(provider_init, backup)
    provider_init.write_text(updated, encoding="utf-8")
    return backup
