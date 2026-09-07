---
name: twzrd-before-sign
description: Fail-closed wash screen for a Python x402Client used by a Hermes skill. Does not protect ClawRouter Node-proxy inference payments.
---

# TWZRD before signing (Python tools only)

Two payment boundaries in ClawRouter-Hermes:

1. **LLM inference** goes to `http://127.0.0.1:8402` and is signed by the **Node** proxy. Enable that with `TWZRD_AUTO_GATE=1` in the **Hermes gateway** environment (this plugin already copies `os.environ` into the spawned proxy). That is ClawRouter #357, not this skill.
2. **Python tools** that call `x402Client` themselves do **not** go through 8402. Wire this hook on that client:

```python
from clawrouter_hermes.twzrd_before_sign import create_before_sign_hook

client.on_before_payment_creation(create_before_sign_hook(timeout_seconds=2))
```

Requires `x402[evm,svm]==2.13.1` and `solana==0.36.6` (x402 2.13.1 imports an RPC module missing from solana 0.40.3). Installing this skill does not grant wallet authority.

Wash, missing/partial/stale coverage, timeout, and intel errors abort. `wash_flagged: false` without full coverage is unknown, not clean. Not Path B / not independent adoption.
