"""Opt-in TWZRD wash guard for an official async Python x402 client.

Register on the payment client used by the Hermes skill, before making requests.
No wallet access, telemetry identifiers, paid requests, or global monkeypatches.
"""
import asyncio
from urllib.parse import quote

import httpx
import sys


def create_before_sign_hook(*, timeout_seconds=2.0, transport=None):
    """Fail closed on flagged, incomplete, stale, or unavailable wash evidence.

    transport is an httpx transport for offline tests. The production origin is
    fixed; no challenge-supplied URL can redirect intelligence requests.
    """
    if sys.version_info < (3, 11):
        raise RuntimeError("The TWZRD hook requires Python 3.11+ and the twzrd extra")
    from x402.schemas import AbortResult, PaymentCreationContext

    if not 0 < timeout_seconds <= 30:
        raise ValueError("timeout_seconds must be between 0 and 30")

    async def hook(context: PaymentCreationContext):
        requirements = context.selected_requirements
        if not requirements.pay_to or not (
            requirements.network == "eip155:8453"
            or requirements.network.startswith("solana:")
        ):
            return AbortResult(reason="twzrd_unsupported_payment")
        try:
            async with asyncio.timeout(timeout_seconds):
                async with httpx.AsyncClient(
                    transport=transport, timeout=timeout_seconds,
                    follow_redirects=False, trust_env=False,
                ) as http:
                    response = await http.get(
                        "https://intel.twzrd.xyz/v1/intel/merchant_card/"
                        + quote(requirements.pay_to, safe=""),
                    )
                    response.raise_for_status()
                    card = response.json()
                    if not isinstance(card, dict):
                        return AbortResult(reason="twzrd_wash_unknown")
                    if card.get("wash_flagged") is True:
                        return AbortResult(reason="twzrd_wash_detected")
                    if not (
                        card.get("wash_flagged") is False
                        and str(card.get("wash_confidence", "")).strip().lower() == "full"
                        and card.get("ring_evaluated") is not False
                        and card.get("wash_stale") is not True
                        and card.get("stale") is not True
                    ):
                        return AbortResult(reason="twzrd_wash_unknown")
        except (httpx.HTTPError, ValueError, TimeoutError):
            return AbortResult(reason="twzrd_intel_unavailable")
        return None

    return hook
