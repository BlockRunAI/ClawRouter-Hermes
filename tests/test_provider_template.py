"""provider_template/ — files must be present and shaped correctly."""

from __future__ import annotations

import ast
import importlib.resources as resources
import json
import sys
import types
from pathlib import Path

import pytest

#: Models the picker leads with, in the order they must appear. Shared by the
#: ordering test and the SKILL.md advertising test: adding a model here is what
#: forces the user-facing docs to name it too.
FEATURED_MODELS = (
    "blockrun/anthropic/claude-fable-5",
    "blockrun/anthropic/claude-opus-5",
    "blockrun/anthropic/claude-opus-4.8",
    "blockrun/anthropic/claude-sonnet-5",
    "blockrun/anthropic/claude-sonnet-4.6",
    "blockrun/openai/gpt-5.6-terra",
    "blockrun/openai/gpt-5.6-sol",
    "blockrun/openai/gpt-5.6-luna",
    "blockrun/openai/gpt-5.5",
    "blockrun/google/gemini-3.1-pro",
    "blockrun/xai/grok-4.5",
    "blockrun/xai/grok-4.3",
    "blockrun/zai/glm-5.2",
    "blockrun/minimax/minimax-m3",
    "blockrun/moonshot/kimi-k3",
    "blockrun/qwen/qwen3.7-max",
    "blockrun/deepseek/deepseek-v4-pro",
    "blockrun/free/nemotron-3.5-lightning",
)


def _template_dir():
    return resources.files("clawrouter_hermes").joinpath("provider_template")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _short_name(model_id: str) -> str:
    return model_id.rsplit("/", 1)[-1]


def _skill_md_advertised_models() -> set[str]:
    """Model short names named in SKILL.md's "Available Models" paragraph.

    Nothing generates that paragraph, so it drifts silently — qwen3.7-max was
    missing from it for a full release. Parsing is deliberately forgiving:
    split the prose on commas and parens, then drop anything with a space,
    which leaves only model identifiers.
    """
    text = (
        resources.files("clawrouter_hermes")
        .joinpath("skills/clawrouter/SKILL.md")
        .read_text(encoding="utf-8")
    )
    _, _, body = text.partition("## Available Models")
    assert body, "SKILL.md is missing its '## Available Models' section"
    paragraph = body.partition("including:")[2].partition("\n##")[0]
    names = set()
    for raw in paragraph.replace("(", ",").replace(")", ",").split(","):
        token = raw.strip().rstrip(".").replace("[vision]", "").strip()
        if token and " " not in token:
            names.add(token)
    return names


def _template_static_fallbacks() -> tuple[str, ...]:
    """Extract the _STATIC_FALLBACKS tuple from the (un-importable) template."""
    source = _template_dir().joinpath("init.py.tmpl").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "_STATIC_FALLBACKS"
            for t in node.targets
        ):
            return tuple(ast.literal_eval(node.value))
    raise AssertionError("_STATIC_FALLBACKS not found in init.py.tmpl")


def test_template_files_present():
    files = {p.name for p in _template_dir().iterdir()}
    assert "plugin.yaml" in files
    assert "init.py.tmpl" in files


def test_provider_plugin_yaml_declares_model_provider():
    text = _template_dir().joinpath("plugin.yaml").read_text(encoding="utf-8")
    assert "kind: model-provider" in text
    assert "clawrouter" in text


def test_provider_init_template_calls_register_provider():
    text = _template_dir().joinpath("init.py.tmpl").read_text(encoding="utf-8")
    assert "register_provider" in text
    assert "ClawRouterProfile" in text
    assert "base_url" in text
    assert "CLAWROUTER_API_KEY" in text


def test_provider_template_uses_curated_picker_catalog_only():
    text = _template_dir().joinpath("init.py.tmpl").read_text(encoding="utf-8")
    assert "models_url" not in text


def test_template_fallbacks_match_chat_models():
    """The materialized provider's fallback_models must stay in sync with the
    curated picker catalog in models.py. The template is copied verbatim (no
    substitution), so the two lists are hand-maintained duplicates and drift
    silently if only one is edited."""
    from clawrouter_hermes import models

    assert _template_static_fallbacks() == tuple(models.chat_models())


def test_curated_picker_catalog_contains_free_models():
    from clawrouter_hermes import models

    chat_models = models.chat_models()
    free_models = [model for model in chat_models if models.is_free_model(model)]
    assert "blockrun/free" in free_models
    assert "blockrun/free/nemotron-3.5-lightning" in free_models
    assert any(model.startswith("blockrun/free/") for model in free_models)


def test_curated_picker_catalog_orders_featured_models():
    from clawrouter_hermes import models

    chat_models = models.chat_models()
    positions = {model: idx for idx, model in enumerate(chat_models)}
    assert chat_models[:4] == [
        "blockrun/auto",
        "blockrun/premium",
        "blockrun/eco",
        "blockrun/free",
    ]
    featured_order = list(FEATURED_MODELS)
    assert [positions[model] for model in featured_order] == sorted(
        positions[model] for model in featured_order
    )
    # All per-model free entries sit contiguously at the end of the picker
    # and match the live free tier exactly, in top-models.json order.
    free_tail = [m for m in chat_models if m.startswith("blockrun/free/")]
    assert chat_models[-len(free_tail):] == free_tail
    assert free_tail == [
        "blockrun/free/nemotron-3.5-lightning",
        "blockrun/free/nemotron-3-nano-30b",
        "blockrun/free/laguna-xs-2.1",
        "blockrun/free/north-mini-code",
        "blockrun/free/nemotron-3-nano-omni-30b-a3b-reasoning",
        "blockrun/free/nemotron-3-ultra-550b",
        "blockrun/free/llama-3.2-11b-vision",
    ]
    # Retired models must not reappear in the picker. Append here on every
    # catalog retirement so a bad merge can't resurrect them.
    retired_models = frozenset({
        "blockrun/free/qwen3-coder-480b",  # NVIDIA EOL 2026-06-14
        # EOL'd for good in blockrun's 2026-07-28 free re-probe (ClawRouter
        # v0.12.239 dropped it from top-models.json); alias pins keep the id
        # routable at the gateway but it leaves user-facing surfaces.
        "blockrun/free/mistral-large-3-675b",
        # Never a real SKU: keep the free route ID in the DeepSeek group instead.
        "blockrun/deepseek/deepseek-v4-flash",
        # Dropped from the live BlockRun catalog by 2026-07-17:
        "blockrun/xai/grok-4-1-fast-reasoning",
        "blockrun/xai/grok-4-0709",
        "blockrun/xai/grok-3",
        "blockrun/free/gpt-oss-120b",
        "blockrun/free/gpt-oss-20b",
        "blockrun/free/qwen3.5-122b-a10b",
        "blockrun/free/llama-4-maverick",
        # Died in blockrun's 2026-07-17 re-probe: hidden upstream and
        # server-redirected to gpt-oss-120b, so a picker entry would silently
        # defeat /exclude. ClawRouter's top-models.test.ts asserts the same.
        "blockrun/free/qwen3-next-80b-a3b-instruct",
        # EOL 2026-08-12 (blockrun #367): NVIDIA published 410 Gone, the
        # gateway set hidden:true and server-redirects calls to a healthy
        # free model, and ClawRouter dropped it from the picker, the
        # FREE_MODELS cascade and the router fallbacks. A picker entry
        # would bill nothing but answer from another model, silently
        # defeating /exclude. top-models.test.ts asserts the same.
        "blockrun/free/deepseek-v4-flash",
        # Retired 2026-08-31 sync: no longer in the live BlockRun catalog.
        "blockrun/free/seed-oss-36b",
        "blockrun/free/mistral-nemotron",
        "blockrun/free/step-3.7-flash",
        "blockrun/free/nemotron-nano-9b-v2",
        "blockrun/free/nemotron-nano-12b-v2-vl",
    })
    assert not set(chat_models) & retired_models


#: Curated entries that postdate the ClawRouter top-models.json snapshot:
#: live in the BlockRun catalog (verified against /api/v1/models) but not
#: yet picked up upstream, so they are exempt from the mirror check until
#: ClawRouter ships them. Drop each one from here the moment it lands in
#: top-models.json — a stale entry silences the guard for a real drift.
#: Empty since 2026-08-31: ClawRouter #290 landed all four, so the picker
#: mirrors top-models.json entry for entry again.
POST_TOP_MODELS_ADDITIONS: frozenset = frozenset()

#: Entries whose picker placement deliberately diverges from top-models.json
#: order; membership is still enforced. Empty since 2026-08-31 — its only
#: member, the free DeepSeek V4 Flash route PR #28 grouped with the paid
#: DeepSeek models, was retired when NVIDIA EOL'd it.
CURATED_PLACEMENT_OVERRIDES: frozenset = frozenset()


def test_curated_picker_catalog_mirrors_clawrouter_top_models():
    """Membership + relative order must match ClawRouter's top-models.json.

    The gateway's MODEL_ALIASES table makes phantom IDs smoke-test green:
    blockrun/deepseek/deepseek-v4-flash returned HTTP 200 via a legacy alias
    to deepseek-chat while never being a real SKU (PR #27). Catalog membership
    therefore has to be validated against top-models.json, not the wire.
    Runs only where a sibling ClawRouter checkout exists; CI skips.
    """
    top_models_path = (
        _repo_root().parent / "ClawRouter" / "src" / "top-models.json"
    )
    if not top_models_path.is_file():
        pytest.skip("sibling ClawRouter checkout not available")
    top_models = json.loads(top_models_path.read_text(encoding="utf-8"))

    from clawrouter_hermes import models

    mirrored = [
        model.removeprefix("blockrun/")
        for model in models.chat_models()
        if model not in POST_TOP_MODELS_ADDITIONS
    ]
    unknown = [model for model in mirrored if model not in top_models]
    assert not unknown, f"curated IDs missing from top-models.json: {unknown}"
    positions = {model: idx for idx, model in enumerate(top_models)}
    order = [
        positions[model]
        for model in mirrored
        if "blockrun/" + model not in CURATED_PLACEMENT_OVERRIDES
    ]
    assert order == sorted(order), (
        "curated order diverges from top-models.json"
    )


def test_patch_hermes_model_catalog_uses_curated_clawrouter_only(monkeypatch):
    import clawrouter_hermes.cli as cli_module
    from clawrouter_hermes import models

    clear_calls = []
    hermes_models = types.ModuleType("hermes_cli.models")
    hermes_models._PROVIDER_MODELS = {}

    def provider_model_ids(provider, *_, **__):
        return ["auto", "eco", "openai/gpt-5.6-sol"] if provider == "clawrouter" else ["other"]

    def cached_provider_model_ids(provider, *_, **__):
        return ["auto", "eco", "openai/gpt-5.6-sol"] if provider == "clawrouter" else ["cached-other"]

    def clear_provider_models_cache(provider=None):
        clear_calls.append(provider)

    hermes_models.provider_model_ids = provider_model_ids
    hermes_models.cached_provider_model_ids = cached_provider_model_ids
    hermes_models.clear_provider_models_cache = clear_provider_models_cache

    hermes_cli = types.ModuleType("hermes_cli")
    hermes_cli.models = hermes_models
    monkeypatch.setitem(sys.modules, "hermes_cli", hermes_cli)
    monkeypatch.setitem(sys.modules, "hermes_cli.models", hermes_models)

    cli_module.patch_hermes_model_catalog()

    assert hermes_models._PROVIDER_MODELS["clawrouter"] == models.chat_models()
    assert hermes_models.provider_model_ids("clawrouter") == models.chat_models()
    assert hermes_models.cached_provider_model_ids("blockrun") == models.chat_models()
    assert hermes_models.provider_model_ids("openai") == ["other"]
    assert hermes_models.cached_provider_model_ids("openai") == ["cached-other"]
    assert clear_calls == ["clawrouter"]


def test_materialize_writes_correct_filenames(tmp_path, monkeypatch):
    """Materializer drops files at $HERMES_HOME/plugins/model-providers/clawrouter/."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    import importlib
    import clawrouter_hermes.cli as cli_module
    importlib.reload(cli_module)

    target = tmp_path / ".hermes" / "plugins" / "model-providers" / "clawrouter"
    cli_module._materialize_provider_plugin(force=False)

    assert (target / "plugin.yaml").is_file()
    assert (target / "__init__.py").is_file()
    assert "register_provider" in (target / "__init__.py").read_text()
    assert "kind: model-provider" in (target / "plugin.yaml").read_text()


def test_install_hermes_compat_writes_provider_env_and_config(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    import importlib
    import yaml
    import clawrouter_hermes.cli as cli_module
    importlib.reload(cli_module)

    cli_module.install_hermes_compat(force_provider=True, set_default=True)

    hermes_home = tmp_path / ".hermes"
    assert (hermes_home / "plugins" / "model-providers" / "clawrouter" / "__init__.py").is_file()
    assert "CLAWROUTER_API_KEY=clawrouter-local" in (hermes_home / ".env").read_text()

    config = yaml.safe_load((hermes_home / "config.yaml").read_text())
    assert config["model"]["provider"] == "clawrouter"
    assert config["model"]["default"] == "blockrun/auto"
    assert config["providers"]["clawrouter"]["key_env"] == "CLAWROUTER_API_KEY"
    assert config["providers"]["clawrouter"]["discover_models"] is False
    assert "blockrun/auto" in config["providers"]["clawrouter"]["models"]



def test_setup_preserves_existing_default_model_without_force(tmp_path, monkeypatch):
    """Without set_default=True, an existing model.default must not be clobbered."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    import importlib
    import yaml
    import clawrouter_hermes.cli as cli_module
    importlib.reload(cli_module)

    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir(parents=True, exist_ok=True)
    (hermes_home / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "model": {"default": "anthropic/claude-opus-4.7", "provider": "anthropic"},
                "unrelated": {"key": "value"},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    cli_module.install_hermes_compat(force_provider=True, set_default=False)

    config = yaml.safe_load((hermes_home / "config.yaml").read_text())
    assert config["model"]["default"] == "anthropic/claude-opus-4.7"
    assert config["model"]["provider"] == "anthropic"
    assert "base_url" not in config["model"]
    assert config["unrelated"] == {"key": "value"}
    assert config["providers"]["clawrouter"]["key_env"] == "CLAWROUTER_API_KEY"


def test_install_hermes_compat_is_idempotent(tmp_path, monkeypatch):
    """Running setup twice produces no diff on the second run."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    import importlib
    import clawrouter_hermes.cli as cli_module
    importlib.reload(cli_module)

    cli_module.install_hermes_compat(force_provider=True, set_default=True)
    hermes_home = tmp_path / ".hermes"
    first_config = (hermes_home / "config.yaml").read_text()
    first_env = (hermes_home / ".env").read_text()

    cli_module.install_hermes_compat(force_provider=False, set_default=True)
    second_config = (hermes_home / "config.yaml").read_text()
    second_env = (hermes_home / ".env").read_text()

    assert first_config == second_config
    assert first_env == second_env


def test_hermes_home_env_var_respected(tmp_path, monkeypatch):
    """When HERMES_HOME is set, materializer writes there (not ~/.hermes)."""
    custom = tmp_path / "custom_hermes_root"
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_HOME", str(custom))
    import importlib
    import clawrouter_hermes.cli as cli_module
    importlib.reload(cli_module)

    cli_module._materialize_provider_plugin(force=False)

    target = custom / "plugins" / "model-providers" / "clawrouter"
    assert (target / "plugin.yaml").is_file()
    assert (target / "__init__.py").is_file()
    # Default ~/.hermes location must NOT have been touched.
    legacy = tmp_path / ".hermes" / "plugins" / "model-providers" / "clawrouter"
    assert not legacy.exists()


# ---------------------------------------------------------------------------
# Upgrade freshness: a materialized plugin carries the version that wrote it,
# so `pip install -U` alone is enough to get a new catalog. Before the stamp,
# install_hermes_compat() only rewrote the plugin when the directory was
# missing or --force was passed, so upgraded users kept the old
# _STATIC_FALLBACKS and never saw newly added models in the picker.
# ---------------------------------------------------------------------------


def test_template_plugin_yaml_declares_a_version_line():
    """The stamp target must exist, or staleness detection never resolves."""
    text = _template_dir().joinpath("plugin.yaml").read_text(encoding="utf-8")
    assert any(line.startswith("version:") for line in text.splitlines())


def test_materialized_plugin_yaml_is_version_stamped(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    import importlib
    import clawrouter_hermes.cli as cli_module
    importlib.reload(cli_module)

    cli_module._materialize_provider_plugin(force=False)

    assert cli_module._materialized_plugin_version() == cli_module._package_version()
    assert not cli_module._provider_plugin_is_stale()


def test_install_hermes_compat_refreshes_stale_provider_plugin(tmp_path, monkeypatch):
    """An upgraded install gets the new catalog without setup --force."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    import importlib
    import clawrouter_hermes.cli as cli_module
    importlib.reload(cli_module)

    cli_module.install_hermes_compat(force_provider=True, set_default=False)
    target = tmp_path / ".hermes" / "plugins" / "model-providers" / "clawrouter"

    # Simulate the state left by a previous version: old stamp, old catalog.
    (target / "plugin.yaml").write_text(
        "name: clawrouter-provider\nkind: model-provider\nversion: 0.0.1\n",
        encoding="utf-8",
    )
    (target / "__init__.py").write_text("_STATIC_FALLBACKS = ()\n", encoding="utf-8")
    sentinel = target / "user-file.txt"
    sentinel.write_text("keep me", encoding="utf-8")

    assert cli_module._provider_plugin_is_stale()

    cli_module.install_hermes_compat(force_provider=False, set_default=False)

    assert cli_module._materialized_plugin_version() == cli_module._package_version()
    assert "register_provider" in (target / "__init__.py").read_text(encoding="utf-8")
    # The unattended refresh rewrites only the two files we own.
    assert sentinel.read_text(encoding="utf-8") == "keep me"


def test_install_hermes_compat_leaves_current_plugin_untouched(tmp_path, monkeypatch):
    """No stamp mismatch means no rewrite — the refresh must not churn."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    import importlib
    import clawrouter_hermes.cli as cli_module
    importlib.reload(cli_module)

    cli_module.install_hermes_compat(force_provider=True, set_default=False)
    target = tmp_path / ".hermes" / "plugins" / "model-providers" / "clawrouter"
    (target / "__init__.py").write_text("# hand-edited\n", encoding="utf-8")

    cli_module.install_hermes_compat(force_provider=False, set_default=False)

    assert (target / "__init__.py").read_text(encoding="utf-8") == "# hand-edited\n"


# ---------------------------------------------------------------------------
# Doc surfaces that carry the catalog but nothing enforced until now.
# ---------------------------------------------------------------------------


def test_skill_md_advertises_every_featured_model():
    """SKILL.md's model list must name each featured model.

    Adding a model to FEATURED_MODELS without updating the shipped skill text
    is exactly how qwen3.7-max shipped unadvertised in 0.3.14.
    """
    advertised = _skill_md_advertised_models()
    missing = [m for m in FEATURED_MODELS if _short_name(m) not in advertised]
    assert not missing, f"SKILL.md does not mention: {missing}"


def test_skill_md_advertises_every_free_model():
    from clawrouter_hermes import models

    advertised = _skill_md_advertised_models()
    free_models = [m for m in models.chat_models() if m.startswith("blockrun/free/")]
    missing = [m for m in free_models if _short_name(m) not in advertised]
    assert not missing, f"SKILL.md does not mention free models: {missing}"


def test_skill_md_names_no_models_outside_the_catalog():
    """Catches renamed/retired ids lingering in the shipped skill text."""
    from clawrouter_hermes import models

    known = {_short_name(m) for m in models.chat_models()}
    unknown = sorted(name for name in _skill_md_advertised_models() if name not in known)
    assert not unknown, f"SKILL.md names models not in the catalog: {unknown}"


def test_docs_curated_entry_count_matches_catalog():
    """The blog doc quotes a live count; it was off by one for a release."""
    from clawrouter_hermes import models

    doc = _repo_root() / "docs" / "03-one-endpoint-gpt-claude-gemini-deepseek.md"
    if not doc.is_file():
        pytest.skip("docs/ is not part of the installed package")
    text = doc.read_text(encoding="utf-8")
    quoted = [
        int(line.strip().lstrip("…").split()[0])
        for line in text.splitlines()
        if line.strip().startswith("…") and "curated entries" in line
    ]
    assert quoted, "docs/03 no longer quotes a curated entry count"
    assert quoted == [len(models.chat_models())] * len(quoted)
