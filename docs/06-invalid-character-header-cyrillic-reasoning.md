---
title: "Hermes Retries (and Re-Pays) in a Loop: Invalid character in header content [\"x-clawrouter-reasoning\"]"
description: "Non-English prompts (Russian, Chinese, Japanese…) through ClawRouter ≤0.12.207 crashed response delivery with ERR_INVALID_CHAR after the x402 payment settled, so Hermes retried — and paid — the same request repeatedly. Fixed in 0.12.208; how to verify, work around, and audit the duplicate charges."
keywords:
  - clawrouter invalid character in header content
  - x-clawrouter-reasoning error
  - clawrouter ERR_INVALID_CHAR cyrillic
  - hermes clawrouter retry loop payment
  - clawrouter russian prompts crash
  - x402 duplicate charges retry
canonical: https://blockrun.ai/blog/clawrouter-invalid-header-cyrillic-reasoning
audience: Hermes Agent users prompting in non-English languages (Cyrillic, CJK) through ClawRouter ≤ 0.12.207
---

# Hermes Retries (and Re-Pays) in a Loop: `Invalid character in header content ["x-clawrouter-reasoning"]`

If you prompt Hermes in Russian (or Chinese, Japanese, …) through ClawRouter and
see this pattern:

- Every request reaches the upstream model and completes — but Hermes never
  receives the response body.
- The proxy log shows, right after each successful upstream call:
  `Error: Invalid character in header content ["x-clawrouter-reasoning"]`
- Hermes retries the same request, and **each retry signs a new x402 payment**.
  Basescan shows repeated `transferWithAuthorization` charges seconds apart for
  what was a single message.

…you are hitting a bug fixed in **ClawRouter v0.12.208**.

## Root cause: routing keywords leaked into an HTTP header

ClawRouter's smart router scores each prompt against multilingual keyword lists
(English, Russian, Chinese, Japanese, …). The keywords your prompt *matched* are
embedded into a human-readable routing explanation, and that explanation is
returned in an `x-clawrouter-reasoning` debug response header — which is **on by
default**.

For a Russian prompt the matched keywords are Cyrillic (`функция`, `класс`,
`импорт`, …). Node.js only allows Latin-1 in header values, so writing the
response headers threw `ERR_INVALID_CHAR` — *after* the upstream LLM had
completed and the gateway had settled the payment. The body was never delivered,
the client retried, and every retry paid again. (It was not your model's
reasoning text — the leak was ClawRouter's own router metadata.)

## Fix: upgrade to ClawRouter ≥ 0.12.208

Hermes spawns the proxy via `npx -y @blockrun/clawrouter` (unpinned), so simply
**restart the proxy** and npx picks up the fixed version:

```bash
npx -y @blockrun/clawrouter --version   # should print 0.12.208 or later
```

Since 0.12.208 the header value is percent-encoded (decode it with
`decodeURIComponent` if you read it for debugging), and even a hypothetically
invalid header can no longer destroy a delivered response — the proxy sanitizes
and still ships the paid body.

## Workarounds on older versions

- Per request: send `x-clawrouter-debug: false` as a request header.
- Globally (0.12.208+): `export CLAWROUTER_DEBUG_HEADERS=off`.
- Env vars like `BLOCKRUN_DISABLE_REASONING_HEADER` or `CLAWROUTER_REASONING`
  do **not** exist — they have no effect.

## Auditing the duplicate charges

The retry loop produces an unmistakable signature in your payment history:
clusters of charges with **identical input token counts seconds apart**
(typically ×3, matching the client's retry limit). Compare your Basescan
`transferWithAuthorization` entries against the messages you actually sent; one
charge per distinct request is legitimate, the rest are retry duplicates. If you
were affected, contact BlockRun with your wallet address — charges are settled
on-chain and visible in the gateway ledger, so duplicates are straightforward to
verify.
