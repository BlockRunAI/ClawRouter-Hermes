import importlib.util
from pathlib import Path
import pytest
MODULE=Path(__file__).parents[1]/"src"/"clawrouter_hermes"/"account.py"
def load():
 spec=importlib.util.spec_from_file_location("account_isolated",MODULE);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def test_account_env_is_detected_without_wallet(isolated_home,monkeypatch):
 monkeypatch.setenv("BLOCKRUN_API_KEY","brk_live_hermes_test");assert load().resolve_api_key()["source"]=="env";assert not (Path.home()/".openclaw"/"blockrun"/"mnemonic").exists()
def test_malformed_account_refuses_fallback(isolated_home,monkeypatch):
 monkeypatch.setenv("BLOCKRUN_API_KEY","bad")
 with pytest.raises(ValueError,match="fallback refused"):load().resolve_api_key()
