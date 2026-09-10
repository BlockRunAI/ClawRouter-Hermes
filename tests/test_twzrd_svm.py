"""Real SVM transaction construction/signing; no RPC or payment broadcast."""
import asyncio
import base64
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

pytest.importorskip("x402")
pytest.importorskip("solders")
from solders.hash import Hash
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from x402 import x402Client
from x402.mechanisms.svm.constants import TOKEN_PROGRAM_ADDRESS
from x402.mechanisms.svm.exact import ExactSvmScheme
from x402.mechanisms.svm.signers import KeypairSigner
from x402.schemas import PaymentAbortedError, PaymentRequired

from clawrouter_hermes.twzrd import create_before_sign_hook


class CountingKeypair:
    def __init__(self):
        self.inner = Keypair()  # Ephemeral and unfunded.
        self.calls = 0

    def pubkey(self):
        return self.inner.pubkey()

    def sign_message(self, message):
        self.calls += 1
        return self.inner.sign_message(message)


@pytest.mark.parametrize("card,reason", [
    ({"wash_flagged": True}, "twzrd_wash_detected"),
    ({"wash_flagged": None}, "twzrd_wash_unknown"),
    ({"wash_flagged": False}, "twzrd_wash_unknown"),
    ({"wash_flagged": False, "wash_confidence": "partial"}, "twzrd_wash_unknown"),
    ({"wash_flagged": False, "wash_confidence": "full", "stale": True}, "twzrd_wash_unknown"),
    ({"wash_flagged": False, "wash_confidence": "full", "ring_evaluated": True}, None),
])
def test_svm_signing_boundary(monkeypatch, card, reason):
    keypair = CountingKeypair()
    scheme = ExactSvmScheme(KeypairSigner(keypair))
    rpc = Mock()
    rpc.get_latest_blockhash.return_value = SimpleNamespace(
        value=SimpleNamespace(blockhash=Hash.default()))
    get_rpc = Mock(return_value=rpc)
    monkeypatch.setattr(scheme, "_get_client", get_rpc)
    metadata = Mock(return_value=SimpleNamespace(
        token_program=Pubkey.from_string(TOKEN_PROGRAM_ADDRESS), decimals=6))
    monkeypatch.setattr(
        "x402.mechanisms.svm.exact.client.get_cached_mint_metadata", metadata)
    network = "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp"
    payee = str(Keypair().pubkey())
    required = PaymentRequired.model_validate({
        "x402Version": 2,
        "resource": {"url": "https://merchant.example/resource"},
        "accepts": [{
            "scheme": "exact", "network": network, "amount": "50000",
            "asset": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "payTo": payee, "maxTimeoutSeconds": 60,
            "extra": {"feePayer": str(Keypair().pubkey())},
        }],
    })
    seen = []

    def intel(request):
        seen.append(request)
        return httpx.Response(200, json=card)

    client = x402Client().register(network, scheme)
    client.on_before_payment_creation(create_before_sign_hook(
        transport=httpx.MockTransport(intel)))
    if reason:
        with pytest.raises(PaymentAbortedError, match=reason):
            asyncio.run(client.create_payment_payload(required))
        assert keypair.calls == 0
        get_rpc.assert_not_called()
        metadata.assert_not_called()
    else:
        payload = asyncio.run(client.create_payment_payload(required))
        tx = VersionedTransaction.from_bytes(base64.b64decode(payload.payload["transaction"]))
        assert keypair.calls == 1
        # Facilitator has not signed; the actual client's signature verifies.
        assert tx.verify_with_results() == [False, True]
        rpc.get_latest_blockhash.assert_called_once()
    assert len(seen) == 1
    assert seen[0].url.path.endswith(payee)
