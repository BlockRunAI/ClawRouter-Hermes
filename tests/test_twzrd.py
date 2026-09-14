import asyncio
import base64

import httpx
import pytest

pytest.importorskip("x402")
from eth_account import Account
from x402 import x402Client
from x402.mechanisms.evm import EthAccountSigner
from x402.mechanisms.evm.exact import ExactEvmScheme
from x402.schemas import PaymentAbortedError, PaymentRequired

from clawrouter_hermes.twzrd import create_before_sign_hook


@pytest.mark.parametrize("guarded", [False, True])
def test_http_challenge_through_real_transport(guarded):
    from x402.http.clients.httpx import PaymentError, x402AsyncTransport
    signer = CountingSigner()
    client = x402Client().register("eip155:8453", ExactEvmScheme(signer))
    if guarded:
        client.on_before_payment_creation(create_before_sign_hook(
            transport=httpx.MockTransport(lambda req: httpx.Response(200, json={"wash_flagged": True})),
        ))
    seen = []
    def merchant(request):
        seen.append(request)
        if request.headers.get("payment-signature"):
            return httpx.Response(200, text="fixture")
        encoded = base64.b64encode(challenge().model_dump_json(by_alias=True).encode()).decode()
        return httpx.Response(402, headers={"payment-required": encoded})
    async def request():
        async with httpx.AsyncClient(transport=x402AsyncTransport(client, httpx.MockTransport(merchant))) as http:
            return await http.get("https://merchant.example/resource")
    if guarded:
        with pytest.raises(PaymentError, match="twzrd_wash_detected") as error:
            asyncio.run(request())
        assert isinstance(error.value.__cause__, PaymentAbortedError)
        assert signer.calls == 0
        assert len(seen) == 1
    else:
        assert asyncio.run(request()).status_code == 200
        assert signer.calls == 1
        assert len(seen) == 2


class CountingSigner(EthAccountSigner):
    def __init__(self):
        super().__init__(Account.create())  # ephemeral, unfunded; never persisted
        self.calls = 0

    def sign_typed_data(self, *args, **kwargs):
        self.calls += 1
        return super().sign_typed_data(*args, **kwargs)


def challenge():
    return PaymentRequired.model_validate({
        "x402Version": 2,
        "resource": {"url": "https://merchant.example/resource"},
        "accepts": [{
            "scheme": "exact", "network": "eip155:8453", "amount": "50000",
            "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "payTo": "0x1111111111111111111111111111111111111111",
            "maxTimeoutSeconds": 60, "extra": {"name": "USD Coin", "version": "2"},
        }],
    })


@pytest.mark.parametrize("card,reason", [
    ({"wash_flagged": True}, "twzrd_wash_detected"),
    ({"wash_flagged": None}, "twzrd_wash_unknown"),
    ({"wash_flagged": False}, "twzrd_wash_unknown"),
    ({"wash_flagged": False, "wash_confidence": "partial"}, "twzrd_wash_unknown"),
    ({"wash_flagged": False, "wash_confidence": "full", "stale": True}, "twzrd_wash_unknown"),
    ([], "twzrd_wash_unknown"),
    ({"wash_flagged": False, "wash_confidence": "full", "ring_evaluated": True}, None),
])
def test_real_client_signing_boundary(card, reason):
    signer = CountingSigner()
    client = x402Client().register("eip155:8453", ExactEvmScheme(signer))
    requests = []

    def intel(request):
        requests.append(request)
        return httpx.Response(200, json=card)

    client.on_before_payment_creation(create_before_sign_hook(transport=httpx.MockTransport(intel)))
    if reason:
        with pytest.raises(PaymentAbortedError, match=reason):
            asyncio.run(client.create_payment_payload(challenge()))
        assert signer.calls == 0
    else:
        payload = asyncio.run(client.create_payment_payload(challenge()))
        assert payload.payload["signature"]
        assert signer.calls == 1
    assert len(requests) == 1
    assert requests[0].url.path.endswith(challenge().accepts[0].pay_to)


@pytest.mark.parametrize("failure", ["timeout", "http", "json", "redirect"])
def test_intel_failure_never_signs(failure):
    signer = CountingSigner()
    client = x402Client().register("eip155:8453", ExactEvmScheme(signer))

    async def intel(request):
        if failure == "timeout":
            await asyncio.sleep(1)
        if failure == "http":
            return httpx.Response(503)
        if failure == "redirect":
            return httpx.Response(302, headers={"location": "https://other.example"})
        return httpx.Response(200, text="not JSON")

    client.on_before_payment_creation(create_before_sign_hook(
        timeout_seconds=0.05, transport=httpx.MockTransport(intel),
    ))
    with pytest.raises(PaymentAbortedError, match="twzrd_intel_unavailable"):
        asyncio.run(client.create_payment_payload(challenge()))
    assert signer.calls == 0
