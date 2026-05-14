"""provider_template/ — files must be present and shaped correctly."""

from __future__ import annotations

import importlib.resources as resources


def _template_dir():
    return resources.files("clawrouter_hermes").joinpath("provider_template")


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
    # User's chosen default is preserved.
    assert config["model"]["default"] == "anthropic/claude-opus-4.7"
    assert config["model"]["provider"] == "anthropic"
    # And the base_url is NOT injected (would otherwise point Anthropic
    # calls at the local ClawRouter proxy).
    assert "base_url" not in config["model"]
    # Unrelated keys preserved.
    assert config["unrelated"] == {"key": "value"}
    # ClawRouter provider entry still registered for the picker.
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
