---
title: "Run GPT-5, Claude, Gemini and DeepSeek in Nous Hermes From One Endpoint"
description: "Stop wiring a separate provider, key and OAuth flow for every model in Hermes Agent. Point Hermes at one OpenAI-compatible gateway and switch between 55+ models from the /model picker."
keywords:
  - hermes multiple llm providers
  - hermes one endpoint all models
  - hermes gpt claude gemini deepseek
  - hermes custom provider setup
  - hermes openai-compatible gateway
canonical: https://blockrun.ai/blog/hermes-one-endpoint-all-models
audience: Nous Hermes Agent users
related_issue: https://github.com/NousResearch/hermes-agent/issues/38679
---

# Run GPT-5, Claude, Gemini and DeepSeek in Nous Hermes From One Endpoint

**Nous Hermes Agent** lets you plug in just about any model — but the *cost* of that
flexibility is configuration sprawl. Each provider wants its own block in
`config.yaml`, its own API key or OAuth flow, its own quirks. And as the issue
tracker shows, several of those per-provider paths are subtly broken:
[custom-provider vision connection errors](https://github.com/NousResearch/hermes-agent/issues/38679),
[OAuth providers silently falling back to `auto`](https://github.com/NousResearch/hermes-agent/issues/38685),
and OpenRouter/Nous error-format mismatches that
[cause infinite reset loops](https://github.com/NousResearch/hermes-agent/issues/38652).

If you just want to *use the best model for each task* without becoming a provider
plumbing expert, the cleanest pattern is: **point Hermes at one OpenAI-compatible
gateway and let it fan out to every model behind a single URL.**

## The problem with one-provider-per-model

A typical multi-model `config.yaml` accretes blocks like this:

```yaml
providers:
  openai:    { key_env: OPENAI_API_KEY, ... }
  anthropic: { key_env: ANTHROPIC_API_KEY, ... }
  google:    { key_env: GOOGLE_API_KEY, ... }
  deepseek:  { key_env: DEEPSEEK_API_KEY, ... }
  minimax:   { provider: minimax-oauth, ... }   # separate OAuth dance
```

Every entry is:

- **A key to obtain, store, rotate, and fund** — five dashboards, five billing
  relationships, five places a leak can happen.
- **A separate code path in Hermes** — and as above, not all of those paths are
  equally well-tested for auxiliary tasks like vision.
- **A switching cost** — changing the model your agent uses can mean editing config
  and restarting, not just picking from a list.

## The fix: one gateway, one credential, many models

An OpenAI-compatible **gateway** sits between Hermes and the upstream providers.
Hermes sees a single provider with one `base_url` and one credential; the gateway
holds the upstream keys and routes each request to the right model.

[ClawRouter](https://github.com/BlockRunAI/ClawRouter) is a gateway purpose-built
for this, and it ships as a Hermes plugin:

```bash
curl -fsSL https://raw.githubusercontent.com/BlockRunAI/ClawRouter-Hermes/main/scripts/install.sh | bash
hermes-clawrouter doctor
```

After `setup`, Hermes' `/model` picker shows a **ClawRouter** provider with a curated
catalog. You switch models from the picker — no config edit per switch:

```
blockrun/auto                 ← smart routing: best model per request
openai/gpt-5.5
anthropic/claude-opus-4.8
anthropic/claude-sonnet-4.6
google/gemini-2.5-pro
deepseek/deepseek-chat
moonshot/kimi-k2.6
xai/grok-4-1-fast-reasoning
minimax/minimax-m3
…55+ total
```

Set the model to `blockrun/auto` and the gateway's router picks a model per request
on a quality/cost curve; or pin a specific model like `anthropic/claude-sonnet-4.6`
when you want determinism.

### Why this also fixes the broken paths

Because Hermes now talks to **one** provider with **`api_key` auth on `127.0.0.1`**:

- No per-provider OAuth → you can't hit the
  [`unhandled auth_type` fallback](https://github.com/NousResearch/hermes-agent/issues/38685).
- Plain-HTTP localhost transport → you dodge the
  [custom-provider vision "Connection error"](https://github.com/NousResearch/hermes-agent/issues/38679).
- One error format from the gateway → no OpenRouter/Nous-style
  [error-parsing reset loop](https://github.com/NousResearch/hermes-agent/issues/38652).

You consolidate five fragile config blocks into one stable one, and several
known-bad code paths simply stop being reachable.

## What about keys and billing?

This is where gateways differ. Some hosted aggregators give you "one API key for
everything," but you're handing your prompts (and a credit-card relationship) to a
middleman. ClawRouter takes a different approach: it runs **locally** and pays
upstream per call using **x402 USDC micropayments** from a wallet you control —
no per-provider subscription, no platform account.

- **Non-custodial** — the wallet lives at `~/.openclaw/blockrun/mnemonic`; the
  plugin only *reads* it.
- **Pay-per-call** — fund a few dollars of USDC on Base or Solana; ~$5 covers
  thousands of requests, and you only pay for what you use.
- **No key sprawl** — Hermes holds one non-secret local placeholder
  (`CLAWROUTER_API_KEY=clawrouter-local`); the actual payment is the on-chain
  micropayment, not a stored API key.

(If you'd rather use a hosted gateway with a conventional key, the *config pattern*
in this article still applies — point Hermes at one `base_url` and switch models from
the picker. The localhost + pay-per-call specifics are ClawRouter's.)

## Minimal working setup

```bash
# 1. Install + enable
curl -fsSL https://raw.githubusercontent.com/BlockRunAI/ClawRouter-Hermes/main/scripts/install.sh | bash

# 2. Verify everything is wired
hermes-clawrouter doctor

# 3. Use smart routing (or open /model to pick a specific one)
hermes --provider clawrouter -m blockrun/auto
```

To also route auxiliary tasks (vision, summarization) through the same endpoint, add:

```yaml
auxiliary:
  vision:
    provider: clawrouter
    model: blockrun/auto
    base_url: http://127.0.0.1:8402/v1
    api_key: clawrouter-local
    timeout: 120
```

## FAQ

**Can I still pin a specific model?**
Yes. Pick any catalog entry (e.g. `openai/gpt-5.5`, `anthropic/claude-sonnet-4.6`)
from `/model`, or pass `-m <model>` on the CLI. `blockrun/auto` is opt-in.

**Does one gateway become a single point of failure?**
The plugin runs a local supervisor with a heartbeat that restarts the proxy on
death, and you can point `CLAWROUTER_PROXY_URL` at an externally-managed instance for
HA. You also still keep first-party providers configured as fallbacks if you want.

**Do I have to use crypto?**
ClawRouter's billing is x402 USDC, which is what makes it keyless and pay-per-call.
If you prefer a traditional key-based aggregator, the same one-endpoint config
pattern works — you just lose the non-custodial/pay-per-use property.

**How many models are available?**
55+ across OpenAI, Anthropic, Google, DeepSeek, Moonshot/Kimi, xAI/Grok, MiniMax,
Z.AI/GLM, NVIDIA-hosted open models, and more — plus a few free tiers.

---

*Last reviewed against Hermes Agent v0.15.x. The single-endpoint pattern is provider-
agnostic; ClawRouter is the implementation that adds non-custodial pay-per-call
billing and 55+ models behind the one URL.*
