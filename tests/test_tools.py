"""tools.py — handler contract + error translation."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch


class _Resp:
    def __init__(self, status_code: int, body: Any = None, text: str = ""):
        self.status_code = status_code
        self._body = body
        self.text = text or (json.dumps(body) if body is not None else "")

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self):
        if self._body is None:
            raise ValueError("no json body")
        return self._body


def _fake_status(reachable=True, base_url="http://127.0.0.1:8402/v1", error=None):
    class _S:
        pass

    s = _S()
    s.reachable = reachable
    s.base_url = base_url
    s.error = error
    s.port = 8402
    s.pid = None
    s.managed = False
    return s


def test_missing_prompt_returns_error_json(isolated_home):
    from clawrouter_hermes import tools

    out = json.loads(tools.image_generate({}))
    assert out["ok"] is False
    assert "prompt" in out["error"].lower()


def test_image_generate_happy_path(isolated_home):
    from clawrouter_hermes import tools

    body = {"created": 123, "data": [{"url": "http://127.0.0.1:8402/images/a.png"}]}
    with patch.object(tools.proxy_supervisor, "ensure_running", return_value=_fake_status()), \
         patch.object(tools.httpx, "post", return_value=_Resp(200, body)) as p:
        out = json.loads(tools.image_generate({"prompt": "a cat"}))
        assert out["ok"] is True
        assert out["result"] == body
        assert p.call_args.kwargs["json"] == {"prompt": "a cat"}
        assert p.call_args.args[0].endswith("/images/generations")


def test_video_generate_passes_optional_fields(isolated_home):
    from clawrouter_hermes import tools

    with patch.object(tools.proxy_supervisor, "ensure_running", return_value=_fake_status()), \
         patch.object(tools.httpx, "post", return_value=_Resp(200, {"id": "v1"})) as p:
        tools.video_generate({"prompt": "x", "model": "bytedance/seedance-2.0", "duration": 10})
        sent = p.call_args.kwargs["json"]
        assert sent == {"prompt": "x", "model": "bytedance/seedance-2.0", "duration": 10}


def test_web_search_passes_query_only(isolated_home):
    from clawrouter_hermes import tools

    with patch.object(tools.proxy_supervisor, "ensure_running", return_value=_fake_status()), \
         patch.object(tools.httpx, "post", return_value=_Resp(200, {"results": []})) as p:
        tools.web_search({"query": "foo", "num_results": 3, "include_text": True})
        sent = p.call_args.kwargs["json"]
        assert sent["query"] == "foo"
        assert sent["num_results"] == 3
        assert sent["include_text"] is True
        assert p.call_args.args[0].endswith("/exa/search")


def test_402_surfaces_payment_hint(isolated_home):
    from clawrouter_hermes import tools

    with patch.object(tools.proxy_supervisor, "ensure_running", return_value=_fake_status()), \
         patch.object(tools.httpx, "post", return_value=_Resp(402, text="Payment required")):
        out = json.loads(tools.image_generate({"prompt": "x"}))
        assert out["ok"] is False
        assert out["status"] == 402
        assert "fund" in out["hint"].lower()


def test_proxy_unreachable_surfaces_error(isolated_home):
    from clawrouter_hermes import tools

    bad = _fake_status(reachable=False, error="Node missing")
    with patch.object(tools.proxy_supervisor, "ensure_running", return_value=bad):
        out = json.loads(tools.web_search({"query": "x"}))
        assert out["ok"] is False
        assert "Node missing" in out["error"]
        assert "doctor" in out["hint"]


def test_connect_error_translated(isolated_home):
    import httpx
    from clawrouter_hermes import tools

    with patch.object(tools.proxy_supervisor, "ensure_running", return_value=_fake_status()), \
         patch.object(
             tools.httpx, "post",
             side_effect=httpx.ConnectError("connection refused"),
         ):
        out = json.loads(tools.image_generate({"prompt": "x"}))
        assert out["ok"] is False
        assert "Cannot reach" in out["error"]
        assert "doctor" in out["hint"]
