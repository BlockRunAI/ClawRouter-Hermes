from unittest.mock import Mock


def test_spawn_preserves_explicit_twzrd_flags(isolated_home, monkeypatch):
    from clawrouter_hermes import proxy_supervisor as supervisor
    monkeypatch.setenv("TWZRD_AUTO_GATE", "1")
    monkeypatch.setenv("TWZRD_FAIL_OPEN", "false")
    monkeypatch.setattr(supervisor, "_spawn_cmd", lambda port: (["fake-proxy"], None))
    popen = Mock()
    monkeypatch.setattr(supervisor.subprocess, "Popen", popen)
    supervisor._spawn(8402)
    env = popen.call_args.kwargs["env"]
    assert env["TWZRD_AUTO_GATE"] == "1"
    assert env["TWZRD_FAIL_OPEN"] == "false"


def test_unset_flags_remain_unset(isolated_home, monkeypatch):
    from clawrouter_hermes import proxy_supervisor as supervisor
    monkeypatch.delenv("TWZRD_AUTO_GATE", raising=False)
    monkeypatch.delenv("TWZRD_FAIL_OPEN", raising=False)
    env = supervisor._build_env()
    assert "TWZRD_AUTO_GATE" not in env
    assert "TWZRD_FAIL_OPEN" not in env


def test_bundled_skill_registration():
    from clawrouter_hermes import _register_twzrd_skill
    ctx = Mock()
    _register_twzrd_skill(ctx)
    args = ctx.register_skill.call_args.kwargs
    assert args["name"] == "twzrd-before-sign"
    assert "clawrouter_hermes.twzrd" in args["path"].read_text()
