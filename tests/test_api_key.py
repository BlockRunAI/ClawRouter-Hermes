"""api_key.py — resolution order, validity, masking, and the two money guards.

The validity rule and resolution order are a contract with
``ClawRouter/src/api-key.ts``: the proxy this plugin spawns resolves the key
with that TS code, so a Python answer that disagreed would make every status
line describe an auth mode the proxy is not in.
"""

from __future__ import annotations

import pytest

VALID = "brk_live_" + "a" * 48
OTHER = "brk_live_" + "b" * 48


def test_no_key_configured_is_not_an_error(isolated_home):
    from clawrouter_hermes import api_key

    assert api_key.resolve() is None
    assert api_key.summary()["configured"] is False


def test_env_wins_over_both_files(isolated_home, monkeypatch):
    from clawrouter_hermes import api_key

    api_key.CORE_API_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    api_key.CORE_API_KEY_FILE.write_text(OTHER + "\n")
    monkeypatch.setenv("BLOCKRUN_API_KEY", VALID)

    resolved = api_key.resolve()
    assert resolved.key == VALID
    assert resolved.source == "env"


def test_core_file_wins_over_legacy(isolated_home):
    from clawrouter_hermes import api_key

    api_key.CORE_API_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    api_key.CORE_API_KEY_FILE.write_text(VALID + "\n")
    api_key.LEGACY_API_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    api_key.LEGACY_API_KEY_FILE.write_text(OTHER + "\n")

    resolved = api_key.resolve()
    assert resolved.key == VALID
    assert resolved.source == "core"


def test_legacy_file_is_still_read(isolated_home):
    from clawrouter_hermes import api_key

    api_key.LEGACY_API_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    api_key.LEGACY_API_KEY_FILE.write_text(VALID + "\n")

    resolved = api_key.resolve()
    assert resolved.source == "legacy"


def test_malformed_stored_key_is_skipped_not_sent(isolated_home):
    """A malformed credential is a 401 per request, and an unexplained 401 is
    the hardest failure mode there is to diagnose."""
    from clawrouter_hermes import api_key

    api_key.CORE_API_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    api_key.CORE_API_KEY_FILE.write_text("sk-this-is-an-openai-key\n")

    assert api_key.resolve() is None


def test_malformed_env_key_is_skipped(isolated_home, monkeypatch):
    from clawrouter_hermes import api_key

    monkeypatch.setenv("BLOCKRUN_API_KEY", "not-a-key")
    assert api_key.resolve() is None


@pytest.mark.parametrize(
    "value,expected",
    [
        (VALID, True),
        ("brk_test_" + "a" * 20, True),   # a future prefix must not lock users out
        ("brk_abcdefgh", True),            # loose on the body, by design
        ("brk_short", False),               # 5-char body is under the 8 minimum
        ("brk_", False),
        ("sk-proj-abcdefghijkl", False),
        ("0x" + "a" * 64, False),          # a wallet key must never be stored as one
        ("", False),
        (None, False),
    ],
)
def test_is_valid_matches_the_ts_rule(value, expected):
    from clawrouter_hermes import api_key

    assert api_key.is_valid(value) is expected


def test_mask_head_matches_what_the_portal_labels(isolated_home):
    from clawrouter_hermes import api_key

    masked = api_key.mask(VALID)
    assert masked.startswith(VALID[:14])
    assert masked.endswith(VALID[-4:])
    assert VALID not in masked


def test_save_writes_0600_to_core(isolated_home):
    from clawrouter_hermes import api_key

    path = api_key.save(VALID)
    assert path == api_key.CORE_API_KEY_FILE
    assert path.stat().st_mode & 0o777 == 0o600
    assert api_key.resolve().key == VALID


def test_save_refuses_a_non_blockrun_key(isolated_home):
    from clawrouter_hermes import api_key

    with pytest.raises(ValueError, match="brk_"):
        api_key.save("sk-proj-nope")
    assert not api_key.CORE_API_KEY_FILE.exists()


def test_clear_removes_both_files_and_reports_env(isolated_home, monkeypatch):
    from clawrouter_hermes import api_key

    api_key.save(VALID)
    api_key.LEGACY_API_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    api_key.LEGACY_API_KEY_FILE.write_text(OTHER + "\n")
    monkeypatch.setenv("BLOCKRUN_API_KEY", VALID)

    result = api_key.clear()
    assert len(result["removed"]) == 2
    # Only the user's shell can unset an env var — say so instead of claiming
    # the switch back to the wallet already happened.
    assert result["env_still_set"] is True
    assert not api_key.CORE_API_KEY_FILE.exists()


def test_clear_on_a_clean_machine_is_a_no_op(isolated_home):
    from clawrouter_hermes import api_key

    result = api_key.clear()
    assert result == {"removed": [], "env_still_set": False}


def test_gateway_is_overridable_for_staging(isolated_home, monkeypatch):
    from clawrouter_hermes import api_key

    assert api_key.default_gateway() == "https://api.blockrun.ai"
    monkeypatch.setenv("BLOCKRUN_API_BASE_URL", "https://staging.example/")
    assert api_key.default_gateway() == "https://staging.example"


def test_format_summary_never_prints_the_whole_key(isolated_home):
    from clawrouter_hermes import api_key

    api_key.save(VALID)
    text = api_key.format_summary(api_key.summary())
    assert VALID not in text
    assert api_key.mask(VALID) in text
    assert "dashboard/credits" in text
