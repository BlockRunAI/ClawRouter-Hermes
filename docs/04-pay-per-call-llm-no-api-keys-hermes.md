---
title: "Pay-Per-Call LLM Access for Hermes Agents — No API Keys, No Subscriptions"
description: "Funding and rotating an API key for every model your Hermes agent uses is a chore and a liability. Here's how to give Hermes keyless, pay-per-call access to 55+ models with USDC micropayments from a wallet you control."
keywords:
  - hermes no api key llm
  - hermes pay per use llm
  - x402 micropayments llm
  - hermes usdc llm access
  - keyless llm gateway hermes
canonical: https://blockrun.ai/blog/hermes-pay-per-call-llm-no-api-keys
audience: Nous Hermes Agent users
related_issue: https://github.com/NousResearch/hermes-agent/issues/38638
---

# Pay-Per-Call LLM Access for Hermes Agents — No API Keys, No Subscriptions

Most guides for **Nous Hermes Agent** assume the same first step: *go get an API key.*
Then another for the next provider. Then fund each one, rotate them on a schedule,
and hope none of them leak from `config.yaml`, your shell history, or a screenshot.

For an autonomous agent that runs cron jobs, answers Telegram messages, and spins up
sub-agents, that key-management surface is both a chore and a security liability. The
Hermes tracker is full of credential-handling edge cases —
[fail-open auth policies](https://github.com/NousResearch/hermes-agent/issues/38638),
[OAuth providers degrading silently](https://github.com/NousResearch/hermes-agent/issues/38685) —
precisely because keys and OAuth flows are hard to get right at scale.

There's a different model: **keyless, pay-per-call access** where each request is
paid for at the moment it's made, from a wallet you control, with no stored
provider credential at all.

## What "pay-per-call" means here

Instead of `OPENAI_API_KEY=sk-...` sitting in your environment, the agent pays for
each model call with an **x402 micropayment** — a tiny USDC settlement attached to
the HTTP request itself. The
[x402 standard](https://github.com/coinbase/x402) turns the HTTP `402 Payment
Required` status into a working payment handshake: the server quotes a price, the
client pays from its wallet, the request proceeds.

Applied to LLM access, that means:

- **No API key to store or rotate.** There is no long-lived secret that can leak.
- **You pay for exactly what you use.** No monthly minimum, no idle subscription, no
  per-provider account.
- **The wallet is yours.** Funds are non-custodial; nobody can spend them but you.

## Setting it up in Hermes

[ClawRouter](https://github.com/BlockRunAI/ClawRouter) implements this for Hermes. It
runs a local OpenAI-compatible gateway that signs an x402 payment for each upstream
call and routes to 55+ models:

```bash
curl -fsSL https://raw.githubusercontent.com/BlockRunAI/ClawRouter-Hermes/main/scripts/install.sh | bash
```

That installer puts the plugin into Hermes' own Python environment, avoiding the
Debian/Ubuntu `externally-managed-environment` error from system `pip`. If you
prefer manual install, run pip from Hermes' venv instead:

```bash
~/.hermes/hermes-agent/venv/bin/python -m pip install -U hermes-plugin-clawrouter
hermes plugins enable clawrouter
hermes-clawrouter setup
```

The plugin **reads** a BIP-39 wallet at `~/.openclaw/blockrun/mnemonic` (mode
`0o600`). To create or import one:

```bash
npx @blockrun/clawrouter setup
```

Then fund a few dollars of USDC on **Base** or **Solana** — about **$5 covers
thousands of requests**. Check your balance any time:

```bash
hermes-clawrouter wallet
```

From here, Hermes uses ClawRouter like any provider:

```bash
hermes --provider clawrouter -m blockrun/auto
```

Notice what's *missing*: there's no real API key anywhere. The only key in your
config is a deliberate non-secret placeholder (`CLAWROUTER_API_KEY=clawrouter-local`)
that exists solely so Hermes' model picker will display the provider. Payment is the
on-chain micropayment, not a stored credential.

## Why this fits autonomous agents specifically

Hermes isn't a one-shot chat client — it runs unattended. That changes the
calculus:

- **Cron and sub-agents** spawn model calls you didn't individually authorize. With
  pay-per-call, each one settles a known micro-amount; you cap exposure by how much
  USDC you fund, not by trusting every code path to handle a powerful key correctly.
- **Multi-channel gateways** (Telegram, WhatsApp, email, Discord) each touch the
  model. One funded wallet covers them all instead of one key per integration.
- **Cost visibility** is per-request by construction. `hermes-clawrouter stats`
  shows proxy usage; spend tracks calls, not calendar months.

## Keeping spend under control

```bash
# See address + USDC balance on Base and Solana
hermes-clawrouter wallet

# Proxy usage stats
hermes-clawrouter stats

# Pick a routing profile to bias cost vs quality
hermes-clawrouter route eco       # cheaper models
hermes-clawrouter route auto      # balanced (default)
hermes-clawrouter route premium   # best models
```

Because the wallet is the budget, the simplest spend cap is the oldest one: **only
fund what you're willing to spend.** Top up $5, and that's your ceiling until you
choose to add more.

## Is this safe?

- **Non-custodial:** your mnemonic controls the funds; the plugin only reads it and
  never writes to the wallet. Back up the 24-word phrase.
- **Local signing:** payments are signed by the local proxy on `127.0.0.1`, not by a
  remote service holding your key.
- **Small blast radius:** a leaked *placeholder* key (`clawrouter-local`) is
  worthless — it isn't what pays for calls.

The one responsibility that's genuinely yours: **guard the mnemonic** like any
crypto wallet seed. That's the trade for never managing a provider API key again.

## FAQ

**Do I need to understand crypto to use this?**
Minimally. You run one `setup` command, fund a wallet with USDC once, and back up a
seed phrase. Day-to-day, you just use Hermes normally.

**What if I'd rather use a normal API key?**
Then a traditional provider or hosted aggregator is fine — this approach is for
people who specifically want to *stop* managing keys and pay per use instead.

**Which chains and tokens?**
USDC on **Base** or **Solana**. Pick whichever you already hold.

**What happens if the wallet runs out of USDC?**
Calls that require payment stop succeeding until you top up — a natural, hard spend
cap. Free-tier models (e.g. `blockrun/free`) remain available.

**How does this relate to the Hermes auth bugs?**
Keyless, single-credential access means you simply don't traverse the fragile
per-provider OAuth/key code paths behind reports like
[#38685](https://github.com/NousResearch/hermes-agent/issues/38685) and
[#38638](https://github.com/NousResearch/hermes-agent/issues/38638).

---

*Last reviewed against Hermes Agent v0.15.x. Pay-per-call billing uses the open
[x402](https://github.com/coinbase/x402) standard; ClawRouter is the gateway that
brings it to Hermes with non-custodial USDC settlement.*
