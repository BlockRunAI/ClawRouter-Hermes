"""provider_template/ — files must be present and shaped correctly."""

from __future__ import annotations

import ast
import importlib.resources as resources


def _template_dir():
    return resources.files("clawrouter_hermes").joinpath("provider_template")


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
    assert any(model.startswith("blockrun/free/") for model in free_models)


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
