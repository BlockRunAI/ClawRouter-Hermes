from __future__ import annotations

import tomllib
from argparse import Namespace
from importlib import metadata
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from clawrouter_hermes import _VERSION, cli

_PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def test_hermes_clawrouter_version(capsys):
    try:
        expected = metadata.version(cli._DIST_NAME)
    except metadata.PackageNotFoundError:
        expected = _VERSION

    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])

    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"hermes-plugin-clawrouter {expected}"


def test_dist_name_matches_pyproject():
    """Guard the name ``cli.main`` hands to ``metadata.version``.

    A typo there is invisible to the test above: it raises
    ``PackageNotFoundError``, falls through to the ``_VERSION`` fallback, and
    prints a correct-looking string for the wrong reason. Comparing against
    ``pyproject.toml`` catches it regardless of what is installed.
    """
    if not _PYPROJECT.is_file():
        pytest.skip("running outside a source checkout")

    project = tomllib.loads(_PYPROJECT.read_text())["project"]
    assert cli._DIST_NAME == project["name"]
    assert _VERSION == project["version"], (
        "clawrouter_hermes._VERSION has drifted from pyproject.toml"
    )


def test_update_upgrades_package_then_runs_setup(monkeypatch, capsys):
    calls = []

    def fake_run(cmd):
        calls.append(cmd)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli.sys, "executable", "/venv/bin/python")
    monkeypatch.setattr(cli, "_package_version", lambda: "0.3.17")

    cli._update(Namespace())

    assert calls == [
        [
            "/venv/bin/python",
            "-I",
            "-m",
            "pip",
            "install",
            "--upgrade",
            "--no-input",
            "hermes-plugin-clawrouter",
        ],
        [
            "/venv/bin/python",
            "-I",
            "-c",
            "from clawrouter_hermes.cli import main; main(['setup'])",
        ],
    ]
    out = capsys.readouterr().out
    assert "Current hermes-plugin-clawrouter: 0.3.17" in out
    assert "Update complete." in out


def test_update_exits_when_package_upgrade_fails(monkeypatch, capsys):
    calls = []

    def fake_run(cmd):
        calls.append(cmd)
        return SimpleNamespace(returncode=7)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli.sys, "executable", "/venv/bin/python")

    with pytest.raises(SystemExit) as exc:
        cli._update(Namespace())

    assert exc.value.code == 7
    assert len(calls) == 1
    assert "pip upgrade failed with exit code 7" in capsys.readouterr().out


def test_update_exits_when_setup_refresh_fails(monkeypatch, capsys):
    calls = []

    def fake_run(cmd):
        calls.append(cmd)
        return SimpleNamespace(returncode=0 if len(calls) == 1 else 5)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli.sys, "executable", "/venv/bin/python")
    monkeypatch.setattr(cli, "_package_version", lambda: "0.3.17")

    with pytest.raises(SystemExit) as exc:
        cli._update(Namespace())

    assert exc.value.code == 5
    assert len(calls) == 2
    assert "setup refresh failed with exit code 5" in capsys.readouterr().out


def test_update_exits_when_pip_is_missing(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(cli.importlib.util, "find_spec", lambda name: None)
    monkeypatch.setattr(cli.subprocess, "run", lambda cmd: calls.append(cmd))

    with pytest.raises(SystemExit) as exc:
        cli._update(Namespace())

    assert exc.value.code == 1
    assert calls == []
    assert "pip is not available" in capsys.readouterr().out


def test_main_dispatches_update(monkeypatch):
    called = []
    monkeypatch.setattr(cli, "_update", lambda args: called.append(args))

    cli.main(["update"])

    assert len(called) == 1


def test_models_sync_write_updates_provider_file_and_config(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    catalog = [
        {
            "id": "openai/gpt-6-astra",
            "categories": ["chat"],
            "billing_mode": "paid",
            "available": True,
        },
        {
            "id": "anthropic/claude-fable-5.1",
            "categories": ["chat"],
            "billing_mode": "paid",
            "available": True,
        },
    ]
    monkeypatch.setattr(cli.catalog_sync, "fetch_catalog", lambda url: catalog)

    cli._models_sync(Namespace(url="https://example.test/models", cap=20, write=True))

    provider_init = tmp_path / ".hermes" / "plugins" / "model-providers" / "clawrouter" / "__init__.py"
    expected = [
        "blockrun/auto",
        "blockrun/premium",
        "blockrun/eco",
        "blockrun/free",
        "blockrun/anthropic/claude-fable-5.1",
        "blockrun/openai/gpt-6-astra",
    ]
    assert cli.catalog_sync.read_materialized_provider(provider_init) == expected

    config = yaml.safe_load((tmp_path / ".hermes" / "config.yaml").read_text(encoding="utf-8"))
    assert config["providers"]["clawrouter"]["models"] == expected
