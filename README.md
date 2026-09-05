<div align="center">

<img src="https://raw.githubusercontent.com/BlockRunAI/ClawRouter-Hermes/main/assets/banner.png" alt="ClawRouter for Hermes" width="600">

<h1>ClawRouter for Hermes</h1>

<p>Hermes gives your agent a body. ClawRouter gives it a way to pay.<br>
No provider accounts. No per-lab keys. Two rails, one provider block.<br><br>
<strong>One Hermes provider, <!-- br:models.chatVisible -->76<!-- /br:models.chatVisible --> models from 12 labs, paid per request —<br>
USDC from a local wallet, or account credit on one BlockRun key.</strong><br><br>
<em><!-- br:models.free -->7<!-- /br:models.free --> models free — no crypto, no balance, no signup required.</em></p>

<br>

<img src="https://img.shields.io/badge/🆓_<!-- br:models.free -->7<!-- /br:models.free -->_Free_Models-success?style=for-the-badge" alt="free models">&nbsp;
<img src="https://img.shields.io/badge/🐍_Hermes_Plugin-black?style=for-the-badge" alt="Hermes plugin">&nbsp;
<img src="https://img.shields.io/badge/🔑_Wallet_or_API_Key-blue?style=for-the-badge" alt="Wallet or API key">&nbsp;
<img src="https://img.shields.io/badge/⚡_Smart_Routing-yellow?style=for-the-badge" alt="Smart routing">&nbsp;
<img src="https://img.shields.io/badge/💰_x402_USDC-purple?style=for-the-badge" alt="x402 USDC">&nbsp;
<img src="https://img.shields.io/badge/🔓_MIT-green?style=for-the-badge" alt="MIT licensed">

[![PyPI version](https://img.shields.io/pypi/v/hermes-plugin-clawrouter.svg?style=flat-square&color=306998)](https://pypi.org/project/hermes-plugin-clawrouter/)
[![PyPI downloads](https://img.shields.io/pypi/dm/hermes-plugin-clawrouter.svg?style=flat-square&color=blue)](https://pypi.org/project/hermes-plugin-clawrouter/)
[![Python](https://img.shields.io/pypi/pyversions/hermes-plugin-clawrouter?style=flat-square)](https://pypi.org/project/hermes-plugin-clawrouter/)
[![GitHub stars](https://img.shields.io/github/stars/BlockRunAI/ClawRouter-Hermes?style=flat-square&label=GitHub%20stars)](https://github.com/BlockRunAI/ClawRouter-Hermes)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](https://github.com/BlockRunAI/ClawRouter-Hermes/blob/main/LICENSE)

[![Hermes](https://img.shields.io/badge/NousResearch-Hermes-000000?style=flat-square)](https://github.com/NousResearch/hermes-agent)
[![BlockRun account](https://img.shields.io/badge/Sign_up-user.blockrun.ai-000000?style=flat-square)](https://user.blockrun.ai)
[![x402 Protocol](https://img.shields.io/badge/x402-Micropayments-purple?style=flat-square)](https://x402.org)
[![Solana](https://img.shields.io/badge/Solana-USDC-9945FF?style=flat-square&logo=solana&logoColor=white)](https://solana.com)
[![Base Network](https://img.shields.io/badge/Base-USDC-0052FF?style=flat-square&logo=coinbase&logoColor=white)](https://base.org)
[![USDC Hackathon Winner](https://img.shields.io/badge/🏆_USDC_Hackathon-Agentic_Commerce_Winner-gold?style=flat-square)](https://x.com/USDC/status/2021625822294216977)
[![Telegram](https://img.shields.io/badge/Telegram-Community-26A5E4?style=flat-square&logo=telegram)](https://t.me/blockrunAI)

</div>

> **hermes-plugin-clawrouter** wires [NousResearch Hermes](https://github.com/NousResearch/hermes-agent) into [ClawRouter](https://github.com/BlockRunAI/ClawRouter), the open-source LLM router built for autonomous agents. One `pip install` gives Hermes <!-- br:models.chatVisible -->76<!-- /br:models.chatVisible --> chat models from OpenAI, Anthropic, Google, xAI, DeepSeek, Moonshot, Z.ai, MiniMax, Qwen, NVIDIA and more — plus image, video and web-search tools — behind a single local provider. Requests are scored across <!-- br:clawrouter.dimensions -->15<!-- /br:clawrouter.dimensions --> dimensions and routed to the cheapest capable model in under 1ms, cutting inference cost by <!-- br:savings.autoVsBaselinePct -->84<!-- /br:savings.autoVsBaselinePct -->% versus pinning Claude Opus 5. Pay however suits you: sign a USDC [x402](https://x402.org) micropayment per call from a local wallet on Solana or Base, **or** sign up at [user.blockrun.ai](https://user.blockrun.ai), top up with a card and use one `brk_…` key. <!-- br:models.free -->7<!-- /br:models.free --> models cost nothing on either rail. MIT licensed.

---

## Two ways to pay

Same catalog, same model ids, same OpenAI-compatible shape. The rails differ only in what authenticates the call and where the money comes from.

|                    | 👛 **Wallet** (x402)                                    | 🔑 **API key** (account credit)                                |
| ------------------ | ------------------------------------------------------- | -------------------------------------------------------------- |
| **Who it's for**   | An agent that can sign but can't open accounts           | A person who'd rather pay with a card                          |
| **Set up**         | `npx @blockrun/clawrouter setup` — a local BIP-39 wallet | [Sign in at user.blockrun.ai](https://user.blockrun.ai), mint a key |
| **Sign-up needed** | None, ever                                               | Google sign-in                                                  |
| **Funding**        | Send USDC on Solana or Base                              | Card top-up at [/dashboard/credits](https://user.blockrun.ai/dashboard/credits) |
| **Gateway**        | `sol.blockrun.ai/api` · `blockrun.ai/api`                | `api.blockrun.ai`                                               |
| **Per-call fee**   | BlockRun's `$0.001` transaction fee, on top of list price | None — list price, billed at exact usage                        |
| **Top-up fee**     | None (you just hold USDC)                                | 5.5% + $0.30 per card top-up                                    |
| **Receipts**       | On-chain, plus `/clawrouter stats`                       | Per-request, at [/dashboard/activity](https://user.blockrun.ai/dashboard/activity) |
| **Turn it on**     | The default                                              | `hermes-clawrouter login brk_live_…`                            |

**A key wins over a wallet whenever both are present.** A machine holding a wallet *and* a key you just added means "bill my account", not "keep spending my USDC". Nothing is deleted — `hermes-clawrouter logout` puts you straight back on the wallet, same mnemonic, same balance.

---

## Where to sign up

1. Go to **[user.blockrun.ai](https://user.blockrun.ai)** and sign in with Google.
2. Mint a key at **[/dashboard/keys](https://user.blockrun.ai/dashboard/keys)** — it looks like `brk_live_…`.
3. Add credit at **[/dashboard/credits](https://user.blockrun.ai/dashboard/credits)** (card; 5.5% + $0.30 per top-up).
4. Tell this plugin about it:

```bash
hermes-clawrouter login brk_live_...
hermes-clawrouter account      # confirms the rail, the gateway and the key (masked)
```

Every call then shows up as its own receipt — model, tokens, exact cost, request id — at **[/dashboard/activity](https://user.blockrun.ai/dashboard/activity)**.

> Type the key in a **terminal**, never in a chat. `/clawrouter login` deliberately refuses: a slash command's arguments live in the transcript, and on Telegram that history is not yours to delete.

---

## Why this plugin exists

Stock Hermes wants a **provider block and an API key per lab**. Want Claude *and* GPT *and* Gemini *and* Grok? That's four accounts, four billing relationships, four keys to rotate, and a `config.yaml` that grows every time a new model ships.

ClawRouter collapses the whole thing into one provider:

- **Starts at $0** — <!-- br:models.free -->7<!-- /br:models.free --> free models, usable before you pay anyone anything
- **One provider, every lab** — Hermes' `/model` picker shows the full curated catalog, grouped by provider
- **No lab keys, ever** — you hold at most one BlockRun credential, never OpenAI's or Anthropic's
- **Pay how you like** — a wallet signature *or* one `brk_…` key; the plugin follows whichever is configured
- **No model babysitting** — `blockrun/auto` scores each request across <!-- br:clawrouter.dimensions -->15<!-- /br:clawrouter.dimensions --> dimensions and picks the cheapest model that can actually do the job
- **Same credential for everything** — image, video and web-search tools bill through it too
- **Fixes Hermes' auxiliary-vision breakage** — a single `api_key` provider on `127.0.0.1` sidesteps [#38679](https://github.com/NousResearch/hermes-agent/issues/38679) and [#38685](https://github.com/NousResearch/hermes-agent/issues/38685) ([how](#auxiliary-vision))

---

## How it compares

|                     | Hermes + lab API keys       | Hermes + OpenRouter | Local Ollama       | **ClawRouter for Hermes**                                             |
| ------------------- | --------------------------- | ------------------- | ------------------ | --------------------------------------------------------------------- |
| **Models**          | One provider block per lab  | Many                | Whatever you host  | **<!-- br:models.chatVisible -->76<!-- /br:models.chatVisible -->, one block**            |
| **Free tier**       | No                          | Rate-limited        | Free but local GPU | **<!-- br:models.free -->7<!-- /br:models.free --> models, no signup** |
| **Auth**            | An API key per lab          | Account + API key   | None               | **Wallet signature, or one BlockRun key**                             |
| **Payment**         | Per-lab invoices            | Credit card         | Your electricity   | **USDC per request, or account credit**                               |
| **Model selection** | Manual                      | Manual              | Manual             | **Automatic (<!-- br:clawrouter.dimensions -->15<!-- /br:clawrouter.dimensions -->-dim scoring, <1ms)** |
| **Image / video**   | Another key, another block  | No                  | No                 | **Built-in tools, same credential**                                   |
| **Frontier models** | Yes                         | Yes                 | No                 | **Yes**                                                               |

---

## Quick Start

> **Not sure you want to pay yet? Free models work out of the box.** Install, pick any `blockrun/free/...` model in `/model`, and you're running — no crypto, no account, no balance.

### 1. Install

```bash
curl -fsSL https://raw.githubusercontent.com/BlockRunAI/ClawRouter-Hermes/main/scripts/install.sh | bash
```

The installer checks for Python, pip/venv support, `pipx`, and Node/npm/npx, installs missing basics through common Linux/macOS package managers, avoids Debian/Ubuntu's `externally-managed-environment` (PEP 668) trap by installing into Hermes' own Python environment, enables the plugin, runs setup, and prints doctor checks.

<details>
<summary><strong>Manual install</strong> — if you already know where Hermes' venv lives</summary>

```bash
~/.hermes/hermes-agent/venv/bin/python -m pip install -U hermes-plugin-clawrouter
hermes plugins enable clawrouter
~/.hermes/hermes-agent/venv/bin/hermes-clawrouter setup
~/.hermes/hermes-agent/venv/bin/hermes-clawrouter doctor
```

`setup` writes the model-provider plugin to `~/.hermes/plugins/model-providers/clawrouter/`, seeds `CLAWROUTER_API_KEY=clawrouter-local` in `~/.hermes/.env`, and registers ClawRouter in `~/.hermes/config.yaml` so Hermes' `/model` picker shows the provider and its curated chat models.

</details>

### 2. Pick a model

In a Hermes chat, open `/model` and choose **ClawRouter → `blockrun/auto`** for smart routing — or pin anything from the catalog, e.g. `blockrun/anthropic/claude-opus-5`, `blockrun/openai/gpt-5.6-terra`, `blockrun/free/nemotron-3.5-lightning`.

### 3. Choose how you pay (optional)

Free models need neither. For paid models, pick one:

<table>
<tr><td width="50%" valign="top">

**🔑 Pay by card**

```bash
# 1. Sign in + mint a key at user.blockrun.ai
# 2. Add credit at /dashboard/credits
hermes-clawrouter login brk_live_...
```

Verifies the key against `api.blockrun.ai`, stores it `0600` at `~/.blockrun/.api-key`, and switches the proxy over.

</td><td width="50%" valign="top">

**👛 Pay from a wallet**

```bash
npx @blockrun/clawrouter setup
# creates ~/.openclaw/blockrun/mnemonic
```

Send a few USDC on **Solana** or **Base** — $5 covers thousands of requests, fully non-custodial.

</td></tr>
</table>

Check either with `/clawrouter account` in chat, or `hermes-clawrouter account` in a terminal.

---

## What you get

### Models

The `/model` picker carries a curated, provider-grouped slice of the catalog (small inline keyboards can't render <!-- br:models.chatVisible -->76<!-- /br:models.chatVisible --> entries); every other model stays routable by full ID.

| Provider          | In the picker                                                                                      |
| ----------------- | -------------------------------------------------------------------------------------------------- |
| **Routing**       | `blockrun/auto` · `blockrun/premium` · `blockrun/eco` · `blockrun/free`                             |
| **Anthropic**     | claude-fable-5 · opus-5 · opus-4.8 · opus-4.7 · sonnet-5 · sonnet-4.6 · haiku-4.5                   |
| **OpenAI**        | gpt-5.6-terra / sol / luna · gpt-5.5 · gpt-5.5-pro · gpt-5.4-pro / 5.4 / mini / nano · gpt-5.3-codex |
| **Google**        | gemini-3.1-pro · gemini-3.6-flash · gemini-3.5-flash · gemini-3.5-flash-lite · gemini-3.1-flash-lite · gemini-3-flash-preview |
| **xAI**           | grok-4.5 · grok-4.3 · grok-build-0.1                                                                |
| **DeepSeek**      | deepseek-v4-flash-vision-exp (vision) · deepseek-v4-pro · deepseek-chat · deepseek-reasoner         |
| **Z.ai**          | glm-5.3 · glm-5.3-flash · glm-5.2 · glm-5.1 · glm-5-turbo · glm-5                                   |
| **Xiaomi / Tencent** | mimo-v2.5 (vision) · mimo-v2.5-pro · hy3                                                         |
| **Moonshot / Qwen / MiniMax** | kimi-k3 · qwen3.7-max · qwen3.8-flash · minimax-m3 · minimax-m2.7                       |
| **Free**          | nemotron-3.5-lightning · nemotron-3-nano-30b · laguna-xs-2.1 · north-mini-code · nemotron-3-nano-omni (vision) · nemotron-3-ultra-550b (1M ctx) · llama-3.2-11b-vision (vision) |

### Routing profiles

| Model ID            | Strategy                | Cost vs. pinning Opus 5                                                  | Best for             |
| ------------------- | ----------------------- | ------------------------------------------------------------------------ | -------------------- |
| `blockrun/free`     | Free models only        | **100% cheaper**                                                         | $0 balance, learning |
| `blockrun/eco`      | Cheapest capable        | **<!-- br:savings.ecoVsBaselinePct -->98<!-- /br:savings.ecoVsBaselinePct -->% cheaper** | Maximum savings      |
| `blockrun/auto`     | Balanced (recommended)  | **<!-- br:savings.autoVsBaselinePct -->84<!-- /br:savings.autoVsBaselinePct -->% cheaper** | General use          |
| `blockrun/premium`  | Best model per tier     | Baseline                                                                 | Mission-critical     |

Savings are computed from a published workload mix, not estimated — see [savings-mix.json](https://github.com/BlockRunAI/blockrun/blob/main/src/brand/savings-mix.json). `/clawrouter route <eco|auto|premium>` sets the profile the proxy itself runs with, applied on its next spawn.

### Slash commands

| Command                                | What it does                             |
| -------------------------------------- | ---------------------------------------- |
| `/clawrouter account`                  | Which rail you're paying on, and where to change it |
| `/clawrouter wallet`                   | Address + USDC balance (Solana and Base) |
| `/clawrouter wallet <solana\|base>`    | Switch payment chain (machine-wide), restarts the proxy |
| `/clawrouter stats`                    | Proxy usage stats                        |
| `/clawrouter status`                   | Proxy health, port, active profile, auth mode |
| `/clawrouter route <eco\|auto\|premium>` | Set the routing profile                |
| `/clawrouter logout`                   | Drop the API key, go back to the wallet  |
| `/clawrouter help`                     | The list above                           |

There is no `/clawrouter login` — it refuses on purpose, and points you at the terminal. See [Where to sign up](#where-to-sign-up).

### Tools

| Tool                        | Coverage                                                                                  |
| --------------------------- | ----------------------------------------------------------------------------------------- |
| `clawrouter_image_generate` | <!-- br:models.image -->9<!-- /br:models.image --> image models — GPT Image 2, Nano Banana / Pro, Seedream 5 Pro, Grok Imagine, CogView-4 |
| `clawrouter_video_generate` | <!-- br:models.video -->8<!-- /br:models.video --> video models — Seedance 1.5 / 2.0, Grok Imagine, Sora 2 |
| `clawrouter_web_search`     | Exa-powered web search                                                                    |

All three bill from whichever rail you're on — wallet or account credit — with no extra keys and no extra setup. On the API-key rail they go to `api.blockrun.ai`, which serves the media and search endpoints alongside chat.

### CLI

```bash
hermes-clawrouter <setup|update|login|logout|account|wallet|doctor|route|stats>
```

| Subcommand | What it does |
|---|---|
| `login <brk_…>` | Verify a BlockRun key, store it `0600`, switch this machine to account credit |
| `logout` | Remove stored keys and go back to the x402 wallet |
| `account` | Which rail is live, which gateway, the key masked (`--json` for scripts) |
| `wallet` | Solana + Base addresses and USDC balances (`--json`) |
| `doctor` | Health check — the credential checks follow whichever rail is configured |

`hermes-clawrouter` ships as its own entry point because some Hermes releases don't register plugin-defined top-level CLI commands until the plugin is enabled. Once it's loaded, `hermes clawrouter <sub>` usually works too.

---

## Auxiliary vision

Hermes' `vision_analyze` builds a *separate* OpenAI client for the configured `auxiliary.vision` provider. That path is fragile for remote custom endpoints ([hermes-agent#38679](https://github.com/NousResearch/hermes-agent/issues/38679): `Connection error`) and for OAuth providers ([#38685](https://github.com/NousResearch/hermes-agent/issues/38685): silent fallback to `auto`). Routing vision through ClawRouter sidesteps both — it's a single `api_key` provider on `127.0.0.1`, so there's no OAuth branch to miss and no remote TLS handshake to mishandle. Add to `~/.hermes/config.yaml`:

```yaml
auxiliary:
  vision:
    provider: clawrouter
    model: blockrun/auto          # or google/gemini-2.5-pro, anthropic/claude-sonnet-4.6
    base_url: http://127.0.0.1:8402/v1
    api_key: clawrouter-local
    timeout: 120
```

`setup` does **not** write this automatically — it would overwrite an existing vision config — so add it by hand if you want vision through ClawRouter, then `hermes gateway restart`.

That `api_key: clawrouter-local` is the placeholder, not a credential. See [the env-var note](#environment-variables).

---

## Paying with a BlockRun API key

```bash
hermes-clawrouter login brk_live_...   # bill account credit via api.blockrun.ai
hermes-clawrouter account              # what's live right now
hermes-clawrouter logout               # back to signing x402 payments from the wallet
```

`login` verifies the key against `api.blockrun.ai/v1/models` before storing it, writes it `0600` to `~/.blockrun/.api-key` (shared with every BlockRun product on the machine), and stops any proxy it supervises so the new credential actually takes effect. An unreachable gateway is *not* treated as a rejected key — it saves anyway and tells you to re-run `doctor`.

**Resolution order**, highest first — identical to the upstream TS CLI, because that is the code the proxy itself runs:

1. `BLOCKRUN_API_KEY` environment variable — for CI and containers
2. `~/.blockrun/.api-key` — BlockRun Core, shared across products
3. `~/.openclaw/blockrun/api-key` — legacy ClawRouter location

A file that exists but holds something that isn't a `brk_…` key is logged and skipped rather than sent upstream: a malformed credential is a 401 per request, and an unexplained 401 is the hardest failure mode there is to diagnose.

**What changes inside the proxy is narrower than it sounds.** In API-key mode ClawRouter builds no x402 client, registers no signer, and attaches a bearer token instead of settling a 402. Everything downstream is untouched: the same model ids, the same <!-- br:clawrouter.dimensions -->15<!-- /br:clawrouter.dimensions -->-dimension classifier, the same fallback chains, the same routing profiles, the same OpenAI-compatible surface. The three plugin tools keep working unchanged.

**Requires `@blockrun/clawrouter` ≥ 0.12.268.** Older proxies ignore `BLOCKRUN_API_KEY` *silently* and sign x402 payments from the wallet instead — a configured key would spend USDC you thought was parked. When this plugin sees a stale pre-install alongside a configured key it refuses the fast path and launches `@latest` through `npx` instead; `hermes-clawrouter doctor` reports the version, and `setup` refreshes the pre-install.

**Two proxies never share a port across rails.** They bill different accounts from different hosts, so a wallet proxy already listening on `:8402` is left alone and a matching one is started on the next free port. `doctor` cross-checks the *running* proxy's `/health` against what you configured, because that is the only thing that proves which account is actually being billed.

---

## Wallet

The plugin **reads** the canonical wallet at `~/.openclaw/blockrun/mnemonic` (24-word BIP-39 phrase, mode 0o600) and never writes to it. Create one with:

```bash
npx @blockrun/clawrouter setup
```

Fund USDC on **Solana** or **Base** — $5 covers thousands of requests, non-custodial. The same wallet is shared with the upstream TS CLI and every other ClawRouter client on the machine: fund once, use everywhere. Switch chains with `/clawrouter wallet solana` or `/clawrouter wallet base` (machine-wide, and it restarts the proxy).

**Which chain by default?** Solana. When nothing is recorded, a fresh machine prefers Solana — but a machine that already had a wallet before that preference existed stays on Base, because its USDC is sitting in the Base wallet and pointing it at a Solana gateway would fail every request against an empty balance. `CLAWROUTER_PAYMENT_CHAIN` overrides both. The plugin mirrors the upstream resolution order exactly (env → `~/.blockrun/.chain` → `~/.openclaw/blockrun/payment-chain` → that default) rather than guessing, because the proxy is what actually signs and the plugin only reports what it will do.

**Headless / CI:** set `BLOCKRUN_WALLET_KEY=<0x raw EVM hex>` to bypass the mnemonic file (EVM-only — Solana derivation unavailable).

Configuring an API key does **not** touch any of this. The mnemonic stays where it is, the balance stays where it is, and `logout` returns you to it.

---

## Environment variables

| Variable | Effect |
|---|---|
| `BLOCKRUN_API_KEY` | **A real credential.** A `brk_…` key; makes the proxy bill account credit through `api.blockrun.ai` instead of signing x402 payments. Wins over a wallet. |
| `BLOCKRUN_API_BASE_URL` | Override the API-key gateway (staging deploys). Default `https://api.blockrun.ai`. |
| `CLAWROUTER_PROXY_URL` | Point at an externally-managed proxy (e.g. `https://my-host/v1`). Skips local spawn entirely. |
| `HERMES_CLAWROUTER_AUTOSPAWN=0` | Disable lazy spawn; require `npx @blockrun/clawrouter` to be running already. |
| `BLOCKRUN_WALLET_KEY` | Raw EVM hex private key — overrides the mnemonic file. |
| `CLAWROUTER_PAYMENT_CHAIN` | `solana` / `base`. Wins over both chain files. Wallet rail only — an API key has no chain to sign on. |
| `CLAWROUTER_ROUTING_PROFILE` | `eco` / `auto` / `premium`. Forwarded to the proxy on spawn. |

> **`CLAWROUTER_API_KEY` is not `BLOCKRUN_API_KEY`.** The names sit one word apart and mean opposite things. `CLAWROUTER_API_KEY` is a non-secret placeholder (`clawrouter-local`) that exists only because Hermes hides API-key-style providers from `/model` unless their key env var is set — putting a `brk_…` key there does nothing, since the local proxy replaces the client's `authorization` header on the way upstream. `BLOCKRUN_API_KEY` is the one that spends money.

---

## Upgrading

```bash
hermes-clawrouter update      # pip upgrade + refresh the materialized integration
```

A plain `pip install -U` works too: the materialized provider plugin is stamped with the version that wrote it, so the next Hermes start notices an older stamp and rewrites it in place — no `setup --force` needed to pick up newly added models. (Before 0.3.16 that refresh never happened, which is why a bare upgrade could strand you on an old model list.)

`update` also re-runs `setup`, which reinstalls `@blockrun/clawrouter@latest` — the fastest way to clear the "pre-installed proxy is too old for API-key mode" warning.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `error: externally-managed-environment` on `pip install` | Do **not** use `--break-system-packages`. Use the one-command installer, or run pip from Hermes' venv (`~/.hermes/hermes-agent/venv/bin/python -m pip install -U hermes-plugin-clawrouter`). |
| `~/.hermes/hermes-agent/venv/bin/hermes: No such file or directory` | Reinstall or repair Hermes first, then re-run the ClawRouter installer. |
| `hermes-clawrouter --version` still shows the old version | Your shell is finding a stale `~/.local/bin/hermes-clawrouter` from a previous `pip --user` install. Re-run the one-command installer; it refreshes that launcher to delegate to Hermes' current venv. |
| `ClawRouter (0 models)` in the picker | Run `hermes-clawrouter setup`, then restart Hermes. |
| Set a key but the wallet is still being spent | Your pre-installed proxy predates 0.12.268 and ignores the key. Run `hermes-clawrouter setup` (installs `@latest`), then `doctor`. |
| `401` on every call after `login` | The key is revoked or mistyped. `hermes-clawrouter doctor` says so explicitly; mint a new one at [/dashboard/keys](https://user.blockrun.ai/dashboard/keys). |
| `402 insufficient_quota` on the key rail | Account credit is exhausted — top up at [/dashboard/credits](https://user.blockrun.ai/dashboard/credits). There is no local balance gate, by design: the gateway's books are server-side, and guessing zero would silently downgrade a paying customer. |
| `logout` didn't switch me back | `BLOCKRUN_API_KEY` is still set in your shell — only you can unset that one. `logout` says so when it happens. |
| Anything else | `hermes-clawrouter doctor` |

### Guides

Standalone problem→solution walkthroughs for common Hermes provider/vision setups:

| Guide | When you need it |
|---|---|
| [`vision_analyze` "Connection error" on a custom provider](https://github.com/BlockRunAI/ClawRouter-Hermes/blob/main/docs/01-vision-analyze-connection-error-custom-provider.md) | Chat works but `vision_analyze` returns `Connection error` on a custom OpenAI-compatible endpoint ([hermes-agent#38679](https://github.com/NousResearch/hermes-agent/issues/38679)) |
| [Auxiliary vision falls back to "auto" with an OAuth provider](https://github.com/BlockRunAI/ClawRouter-Hermes/blob/main/docs/02-oauth-vision-provider-falls-back-to-auto.md) | `auxiliary.vision.provider` (e.g. `minimax-oauth`) logs `unhandled auth_type` and silently degrades ([#38685](https://github.com/NousResearch/hermes-agent/issues/38685)) |
| [Run GPT-5, Claude, Gemini & DeepSeek from one endpoint](https://github.com/BlockRunAI/ClawRouter-Hermes/blob/main/docs/03-one-endpoint-gpt-claude-gemini-deepseek.md) | You want many models in Hermes without a separate provider/key block per model |
| [Pay-per-call LLM access — no API keys](https://github.com/BlockRunAI/ClawRouter-Hermes/blob/main/docs/04-pay-per-call-llm-no-api-keys-hermes.md) | You'd rather pay per request with USDC than manage and rotate provider API keys |
| [Behind an HTTP proxy/VPN: timeouts, 500s, `Premature close`](https://github.com/BlockRunAI/ClawRouter-Hermes/blob/main/docs/05-proxy-vpn-timeouts-premature-close.md) | Small requests work but large agentic requests 500 or time out after payment — your proxy (mihomo/clash/corporate) isn't being used by ClawRouter's upstream traffic |
| [Retry-and-repay loop: `Invalid character in header content`](https://github.com/BlockRunAI/ClawRouter-Hermes/blob/main/docs/06-invalid-character-header-cyrillic-reasoning.md) | Non-English prompts (Cyrillic/CJK) on ClawRouter ≤ 0.12.207 crash response delivery after payment settles; Hermes retries and re-pays the same request |

---

## How it works

```
                                                    ┌─ x402 USDC signed locally ─→ sol.blockrun.ai/api
Hermes chat → ClawRouter provider (127.0.0.1:8402) ─┤                              blockrun.ai/api
                    ↑ spawned + supervised          └─ Bearer brk_…            ─→ api.blockrun.ai
                                                                                        ↓
                                                            OpenAI / Anthropic / Google / xAI / …
```

1. `hermes` starts → the entry-point plugin loads → `register(ctx)` wires tools, slash commands, CLI, and the skill.
2. `hermes-clawrouter setup` materializes `~/.hermes/plugins/model-providers/clawrouter/{plugin.yaml,__init__.py}` from bundled package data and writes the Hermes config/env hints that current provider and gateway model-picker paths need.
3. Hermes' `providers/__init__.py` discovers the materialized directory and registers `ClawRouterProfile`, pointing `base_url` at `http://127.0.0.1:<port>/v1`.
4. First tool call or chat turn → the supervisor probes `:8402`, checks the running proxy's `/health` is on the rail you configured, spawns one if not, waits ≤30s for `/v1/models`, then forwards the request.
5. A heartbeat thread restarts the subprocess on death (max 3 restarts/min).

Wallet (BIP-39, Solana + Base), API-key resolution, routing (the <!-- br:clawrouter.dimensions -->15<!-- /br:clawrouter.dimensions -->-dimension scorer) and x402 payment all live in the canonical [TypeScript implementation](https://github.com/BlockRunAI/ClawRouter) — this package is a thin Python adapter, not a fork.

**Not a local-inference tool.** Prompts are sent over HTTPS to a BlockRun gateway for execution. If you need inference that never leaves your machine, use Ollama.

### Distribution

The Python package ships **both** logical plugins:

- **Standalone** plugin (this PyPI entry point): tools, slash commands, CLI, skill.
- **Model-provider** plugin (materialized into `~/.hermes/plugins/model-providers/clawrouter/` by `hermes-clawrouter setup`): `ProviderProfile` registration.

The split is required because Hermes' PluginManager (`hermes_cli/plugins.py`) skips `register(ctx)` for `kind: model-provider`, and entry-point plugins always load as `kind: standalone`.

---

## Development

```bash
git clone https://github.com/BlockRunAI/ClawRouter-Hermes.git
cd ClawRouter-Hermes
pip install -e ".[dev]"
pytest
```

---

## Support

| Channel | Link |
| --- | --- |
| 🔑 Sign up / API keys | [user.blockrun.ai](https://user.blockrun.ai) |
| 💬 Community Telegram | [t.me/blockrunAI](https://t.me/blockrunAI) |
| 🐦 X / Twitter | [x.com/blockrunai](https://x.com/blockrunai) |
| 📅 Schedule a demo | [calendly.com/vickyfu9/30min](https://calendly.com/vickyfu9/30min) |
| ✉️ Email | vicky@blockrun.ai |

---

## From the BlockRun ecosystem

<table>
<tr>
<td width="50%">

### 🐍 ClawRouter-Hermes

**ClawRouter for NousResearch Hermes**

You're here. <!-- br:models.chatVisible -->76<!-- /br:models.chatVisible --> models, smart routing, wallet or API key.

`pip install hermes-plugin-clawrouter`

</td>
<td width="50%">

### ⚡ [ClawRouter](https://github.com/BlockRunAI/ClawRouter)

**The LLM router built for autonomous agents**

The canonical TypeScript proxy this plugin wraps. Works with any OpenAI-compatible client.

`npx @blockrun/clawrouter`

</td>
</tr>
<tr>
<td width="50%">

### 🤖 [BRCC](https://blockrun.ai/brcc.md)

**BlockRun for Claude Code**

Claude Code on <!-- br:models.chatVisible -->76<!-- /br:models.chatVisible --> models — no Anthropic account, no rate limits, pay per request.

`curl -fsSL https://blockrun.ai/brcc-install | bash`

</td>
<td width="50%">

### 📊 [Models & pricing](https://blockrun.ai/models)

**The live catalog**

Every model, every price, updated as the gateway changes.

[blockrun.ai/models](https://blockrun.ai/models)

</td>
</tr>
</table>

---

## FAQ

### Does this replace Hermes' own providers?

No. It adds one more provider. Existing OpenAI/Anthropic/OAuth blocks in `config.yaml` keep working; you can move to ClawRouter model by model.

### Do I need crypto to try it?

No. <!-- br:models.free -->7<!-- /br:models.free --> models are free with no wallet, no balance and no signup. Beyond that you can pay with a card at [user.blockrun.ai](https://user.blockrun.ai) and never touch a wallet at all.

### If I switch to an API key, what happens to my wallet?

Nothing. The key takes precedence while it's configured, and the wallet sits idle — same mnemonic, same USDC balance, same addresses. `hermes-clawrouter logout` removes the stored key and the very next call signs x402 again. `/clawrouter wallet` still shows the balance either way, and still switches the chain the wallet *would* use.

### Do the image, video and search tools work on the API key?

Yes. `api.blockrun.ai` serves `/v1/images/generations`, `/v1/videos/generations` and `/v1/exa/search` alongside chat, and the three plugin tools go through the same local proxy on either rail. If a partner endpoint ever isn't published on that host, the proxy rewrites the gateway's `Unsupported endpoint` 404 into an explanation instead of a bare error.

### Where do my keys live?

On the wallet rail: a local BIP-39 mnemonic at `~/.openclaw/blockrun/mnemonic` (mode 0o600), which never leaves the machine — only detached x402 payment signatures are sent. On the key rail: `~/.blockrun/.api-key` (mode 0o600), sent as a bearer token to exactly one host, `api.blockrun.ai`. Either way you hold no lab API keys — BlockRun owns those relationships.

### What does it cost to run?

The plugin is MIT and free. You pay per request at gateway prices — on `blockrun/auto` that's <!-- br:savings.autoVsBaselinePct -->84<!-- /br:savings.autoVsBaselinePct -->% less than pinning Claude Opus 5 for the same traffic, and <!-- br:savings.ecoVsBaselinePct -->98<!-- /br:savings.ecoVsBaselinePct -->% less on `eco`. The wallet rail adds BlockRun's `$0.001` per-call transaction fee; the key rail has no per-call fee and charges 5.5% + $0.30 once, when you top up.

### Can I see exactly what each call cost?

On the key rail, yes — [user.blockrun.ai/dashboard/activity](https://user.blockrun.ai/dashboard/activity) lists every request with its model, token counts, exact cost and request id. On the wallet rail, `/clawrouter stats` plus the on-chain record.

### Can I point it at my own proxy?

Yes — set `CLAWROUTER_PROXY_URL` and the plugin skips the local spawn entirely.

---

<div align="center">

**MIT License** · © [BlockRun](https://blockrun.ai) — agent-native AI infrastructure

⭐ If ClawRouter powers your Hermes agent, consider starring the repo!

</div>
