---
name: twzrd-before-sign
description: Opt-in wash screening before signing payments in an explicitly wired Python x402 client.
---

# TWZRD before signing

Use Python 3.11+ and install `hermes-plugin-clawrouter[twzrd]` in the payment
script's environment. Preserve the operator's wallet authority and spend policy.
Never put wallet keys in prompts. Register on the actual async payment client:

```python
from clawrouter_hermes.twzrd import create_before_sign_hook

client.on_before_payment_creation(create_before_sign_hook())
```

The client must already have its signer and local spending policy configured.
This hook queries the free TWZRD merchant card for the selected payTo. Flagged,
unknown, partial, stale, or unavailable wash evidence aborts before signing.
Full negative wash evidence permits continuation; it does not certify merchant
safety. Base and Solana challenges are supported. Intel receives the payee and
connection metadata; no attribution identifiers are added.

Skill registration alone does not intercept payments. Other clients, MPP,
arbitrary tools, and direct wallet calls remain outside this hook.

## Node inference proxy (separate boundary)

Set `TWZRD_AUTO_GATE=1` and `TWZRD_FAIL_OPEN=false` before launching the plugin.
The supervisor inherits these into newly spawned proxies. A reused or external
proxy must be configured and restarted by its operator. Environment forwarding
alone does not prove AutoGate activation: the Node proxy needs a compatible
ClawRouter and resolvable gate package. Verify its loaded version and activation.
The Python hook does not change the Node proxy or protect API-key billing.
