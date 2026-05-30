"""_patch_telegram_model_labels — wraps the adapter keyboard, relabels only
the model-selection buttons, and degrades gracefully when the adapter has no
keyboard to patch."""

from __future__ import annotations

import sys
import types

import pytest


class _FakeButton:
    def __init__(self, text, callback_data=None):
        self.text = text
        self.callback_data = callback_data


class _FakeMarkup:
    def __init__(self, inline_keyboard):
        self.inline_keyboard = inline_keyboard


def _make_adapter_class(*, with_keyboard: bool):
    """A stand-in TelegramAdapter whose original _build_model_keyboard mirrors
    the real adapter's callback-data scheme (``mm:<idx>`` for model buttons,
    ``mg:``/``mb``/``mx`` for nav)."""

    class TelegramAdapter:
        _MODEL_PAGE_SIZE = 4

        if with_keyboard:

            def _build_model_keyboard(self, model_list, page):
                page_size = self._MODEL_PAGE_SIZE
                start = page * page_size
                end = min(start + page_size, len(model_list))
                rows = [
                    [
                        _FakeButton(str(model_list[i]), callback_data=f"mm:{i}")
                        for i in range(start, end)
                    ],
                    [
                        _FakeButton("◀ Back", callback_data="mb"),
                        _FakeButton("✗ Cancel", callback_data="mx"),
                    ],
                ]
                return _FakeMarkup(rows), f" ({start + 1}–{end})"

    return TelegramAdapter


def _install_fake_gateway(monkeypatch, adapter_cls):
    """Wire a fake ``gateway.platforms.telegram`` into sys.modules."""
    telegram = types.ModuleType("gateway.platforms.telegram")
    telegram.TelegramAdapter = adapter_cls
    telegram.InlineKeyboardButton = _FakeButton
    telegram.InlineKeyboardMarkup = _FakeMarkup

    platforms = types.ModuleType("gateway.platforms")
    platforms.telegram = telegram
    gateway = types.ModuleType("gateway")
    gateway.platforms = platforms

    monkeypatch.setitem(sys.modules, "gateway", gateway)
    monkeypatch.setitem(sys.modules, "gateway.platforms", platforms)
    monkeypatch.setitem(sys.modules, "gateway.platforms.telegram", telegram)
    return telegram


def test_patch_relabels_only_model_buttons(monkeypatch):
    from clawrouter_hermes import _patch_telegram_model_labels

    adapter_cls = _make_adapter_class(with_keyboard=True)
    _install_fake_gateway(monkeypatch, adapter_cls)

    _patch_telegram_model_labels()
    assert adapter_cls._clawrouter_labels_patched is True

    # blockrun/free is free, openai/gpt-5.5 is not.
    models = ["blockrun/free", "openai/gpt-5.5"]
    markup, page_info = adapter_cls._build_model_keyboard(adapter_cls(), models, 0)

    model_row, nav_row = markup.inline_keyboard
    free_btn, paid_btn = model_row

    # Model buttons get compact, free-aware labels; callback data is preserved.
    assert free_btn.text == "[FREE] free"
    assert free_btn.callback_data == "mm:0"
    assert paid_btn.text == "gpt-5.5"
    assert paid_btn.callback_data == "mm:1"

    # Nav/back/cancel buttons pass through untouched.
    assert [b.text for b in nav_row] == ["◀ Back", "✗ Cancel"]
    assert [b.callback_data for b in nav_row] == ["mb", "mx"]

    # page_info is forwarded verbatim from the original method.
    assert page_info == " (1–2)"


def test_patch_is_idempotent(monkeypatch):
    from clawrouter_hermes import _patch_telegram_model_labels

    adapter_cls = _make_adapter_class(with_keyboard=True)
    _install_fake_gateway(monkeypatch, adapter_cls)

    _patch_telegram_model_labels()
    first = adapter_cls._build_model_keyboard
    _patch_telegram_model_labels()  # second call must not re-wrap
    assert adapter_cls._build_model_keyboard is first


def test_patch_noop_when_adapter_lacks_keyboard(monkeypatch):
    from clawrouter_hermes import _patch_telegram_model_labels

    adapter_cls = _make_adapter_class(with_keyboard=False)
    _install_fake_gateway(monkeypatch, adapter_cls)

    _patch_telegram_model_labels()  # must not raise
    assert getattr(adapter_cls, "_clawrouter_labels_patched", False) is False
    assert not hasattr(adapter_cls, "_build_model_keyboard")
