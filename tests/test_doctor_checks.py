"""Doctor helper probes added to close the System 2 (config.yaml) gap."""

from __future__ import annotations


def test_provider_config_missing(isolated_home):
    from clawrouter_hermes import cli

    ok, detail = cli._check_provider_config()
    assert ok is False
    assert "missing" in detail


def test_provider_config_after_setup(isolated_home):
    from clawrouter_hermes import cli

    cli._configure_hermes_provider(set_default_force=False)
    ok, detail = cli._check_provider_config()
    assert ok is True
    assert detail.endswith("config.yaml")


def test_provider_config_url_mismatch(isolated_home):
    import yaml

    from clawrouter_hermes import cli

    cli._config_file().parent.mkdir(parents=True, exist_ok=True)
    cli._config_file().write_text(
        yaml.safe_dump(
            {
                "providers": {
                    "clawrouter": {
                        "name": "ClawRouter",
                        "base_url": "http://example.invalid/v1",
                        "transport": "openai_chat",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    ok, detail = cli._check_provider_config()
    assert ok is False
    assert "mismatch" in detail


def test_provider_config_accepts_api_key(isolated_home):
    """PR #2 used the ``api:`` key; Hermes accepts it too, so doctor must."""
    import yaml

    from clawrouter_hermes import cli

    cli._config_file().parent.mkdir(parents=True, exist_ok=True)
    cli._config_file().write_text(
        yaml.safe_dump(
            {
                "providers": {
                    "clawrouter": {
                        "name": "ClawRouter",
                        "api": cli._base_url(),
                        "transport": "openai_chat",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    ok, _ = cli._check_provider_config()
    assert ok is True


def test_api_key_from_env(isolated_home, monkeypatch):
    from clawrouter_hermes import cli

    monkeypatch.setenv("CLAWROUTER_API_KEY", "live-key")
    ok, detail = cli._check_api_key_present()
    assert ok is True
    assert detail == "env"


def test_api_key_from_env_file(isolated_home, monkeypatch):
    from clawrouter_hermes import cli

    monkeypatch.delenv("CLAWROUTER_API_KEY", raising=False)
    cli._ensure_local_api_key()
    # _ensure_local_api_key also sets the process env via setdefault;
    # clear it so we exercise the .env-file branch.
    monkeypatch.delenv("CLAWROUTER_API_KEY", raising=False)
    ok, detail = cli._check_api_key_present()
    assert ok is True
    assert detail.endswith(".env")


def test_api_key_missing(isolated_home, monkeypatch):
    from clawrouter_hermes import cli

    monkeypatch.delenv("CLAWROUTER_API_KEY", raising=False)
    ok, detail = cli._check_api_key_present()
    assert ok is False
    assert "not set" in detail
