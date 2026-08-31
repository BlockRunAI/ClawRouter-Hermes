<div align="center">

<img src="https://raw.githubusercontent.com/BlockRunAI/ClawRouter-Hermes/main/assets/banner.png" alt="ClawRouter for Hermes" width="600">

<h1>ClawRouter for Hermes</h1>

<p>Hermes gives your agent a body. ClawRouter gives it a wallet.<br>
No provider accounts. No API keys. No credit card.<br><br>
<strong>One Hermes provider, <!-- br:models.chatVisible -->76<!-- /br:models.chatVisible --> models from 12 labs, paid per request in USDC.</strong><br><br>
<em><!-- br:models.free -->7<!-- /br:models.free --> models free — no crypto, no balance, no signup required.</em></p>

<br>

<img src="https://img.shields.io/badge/🆓_6_Free_Models-success?style=for-the-badge" alt="6 free models">&nbsp;
<img src="https://img.shields.io/badge/🐍_Hermes_Plugin-black?style=for-the-badge" alt="Hermes plugin">&nbsp;
<img src="https://img.shields.io/badge/🔑_Zero_API_Keys-blue?style=for-the-badge" alt="No API keys">&nbsp;
<img src="https://img.shields.io/badge/⚡_Smart_Routing-yellow?style=for-the-badge" alt="Smart routing">&nbsp;
<img src="https://img.shields.io/badge/💰_x402_USDC-purple?style=for-the-badge" alt="x402 USDC">&nbsp;
<img src="https://img.shields.io/badge/🔓_MIT-green?style=for-the-badge" alt="MIT licensed">

[![PyPI version](https://img.shields.io/pypi/v/hermes-plugin-clawrouter.svg?style=flat-square&color=306998)](https://pypi.org/project/hermes-plugin-clawrouter/)
[![PyPI downloads](https://img.shields.io/pypi/dm/hermes-plugin-clawrouter.svg?style=flat-square&color=blue)](https://pypi.org/project/hermes-plugin-clawrouter/)
[![Python](https://img.shields.io/pypi/pyversions/hermes-plugin-clawrouter?style=flat-square)](https://pypi.org/project/hermes-plugin-clawrouter/)
[![GitHub stars](https://img.shields.io/github/stars/BlockRunAI/ClawRouter-Hermes?style=flat-square&label=GitHub%20stars)](https://github.com/BlockRunAI/ClawRouter-Hermes)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](https://github.com/BlockRunAI/ClawRouter-Hermes/blob/main/LICENSE)

[![Hermes](https://img.shields.io/badge/NousResearch-Hermes-000000?style=flat-square)](https://github.com/NousResearch/hermes-agent)
[![x402 Protocol](https://img.shields.io/badge/x402-Micropayments-purple?style=flat-square)](https://x402.org)
[![Base Network](https://img.shields.io/badge/Base-USDC-0052FF?style=flat-square&logo=coinbase&logoColor=white)](https://base.org)
[![Solana](https://img.shields.io/badge/Solana-USDC-9945FF?style=flat-square&logo=solana&logoColor=white)](https://solana.com)
[![USDC Hackathon Winner](https://img.shields.io/badge/🏆_USDC_Hackathon-Agentic_Commerce_Winner-gold?style=flat-square)](https://x.com/USDC/status/2021625822294216977)
[![Telegram](https://img.shields.io/badge/Telegram-Community-26A5E4?style=flat-square&logo=telegram)](https://t.me/blockrunAI)

</div>

> **hermes-plugin-clawrouter** wires [NousResearch Hermes](https://github.com/NousResearch/hermes-agent) into [ClawRouter](https://github.com/BlockRunAI/ClawRouter), the open-source LLM router built for autonomous agents. One `pip install` gives Hermes <!-- br:models.chatVisible -->76<!-- /br:models.chatVisible --> chat models from OpenAI, Anthropic, Google, xAI, DeepSeek, Moonshot, Z.ai, MiniMax, Qwen, NVIDIA and more — plus image, video and web-search tools — behind a single local provider. Requests are scored across <!-- br:clawrouter.dimensions -->15<!-- /br:clawrouter.dimensions --> dimensions and routed to the cheapest capable model in under 1ms, cutting inference cost by <!-- br:savings.autoVsBaselinePct -->84<!-- /br:savings.autoVsBaselinePct -->% versus pinning Claude Opus 5. Authentication is a wallet signature, billing is USDC over [x402](https://x402.org) on Base or Solana, and <!-- br:models.free -->7<!-- /br:models.free --> models cost nothing at all. MIT licensed.

---

## Why this plugin exists

Stock Hermes wants a **provider block and an API key per lab**. Want Claude *and* GPT *and* Gemini *and* Grok? That's four accounts, four billing relationships, four keys to rotate, and a `config.yaml` that grows every time a new model ships.

Your agent can't do any of that. Agents can't open accounts or type in credit cards — they can only sign transactions.

ClawRouter collapses the whole thing into one provider:

- **Starts at $0** — <!-- br:models.free -->7<!-- /br:models.free --> free models, usable before you ever touch crypto
- **One provider, every lab** — Hermes' `/model` picker shows the full curated catalog, grouped by provider
- **No API keys** — the local wallet signature *is* authentication; you never hold a lab's key
- **No model babysitting** — `blockrun/auto` scores each request across <!-- br:clawrouter.dimensions -->15<!-- /br:clawrouter.dimensions --> dimensions and picks the cheapest model that can actually do the job
- **Pay per request** — USDC via x402 on Base or Solana; $5 covers thousands of calls, non-custodial
- **Same wallet for everything** — image, video and web-search tools bill through it too
- **Fixes Hermes' auxiliary-vision breakage** — a single `api_key` provider on `127.0.0.1` sidesteps [#38679](https://github.com/NousResearch/hermes-agent/issues/38679) and [#38685](https://github.com/NousResearch/hermes-agent/issues/38685) ([how](#auxiliary-vision))

---

## How it compares

|                     | Hermes + lab API keys       | Hermes + OpenRouter | Local Ollama       | **ClawRouter for Hermes**                                             |
| ------------------- | --------------------------- | ------------------- | ------------------ | --------------------------------------------------------------------- |
| **Models**          | One provider block per lab  | Many                | Whatever you host  | **<!-- br:models.chatVisible -->76<!-- /br:models.chatVisible -->, one block**            |
| **Free tier**       | No                          | Rate-limited        | Free but local GPU | **<!-- br:models.free -->7<!-- /br:models.free --> models, no signup** |
| **Auth**            | An API key per lab          | Account + API key   | None               | **Wallet signature**                                                  |
| **Payment**         | Per-lab invoices            | Credit card         | Your electricity   | **USDC per request**                                                  |
| **Model selection** | Manual                      | Manual              | Manual             | **Automatic (<!-- br:clawrouter.dimensions -->15<!-- /br:clawrouter.dimensions -->-dim scoring, <1ms)** |
| **Image / video**   | Another key, another block  | No                  | No                 | **Built-in tools, same wallet**                                       |
| **Frontier models** | Yes                         | Yes                 | No                 | **Yes**                                                               |

---

## Quick Start

> **No wallet? Free models work out of the box.** Install, pick any `blockrun/free/...` model in `/model`, and you're running — no crypto, no balance. Add USDC later when you want frontier models.

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

In a Hermes chat, open `/model` and choose **ClawRouter → `blockrun/auto`** for smart routing — or pin anything from the catalog, e.g. `blockrun/anthropic/claude-opus-5`, `blockrun/openai/gpt-5.6-terra`, `blockrun/free/deepseek-v4-flash`.

### 3. Fund the wallet (optional)

Free models need nothing. For paid models, create and fund the shared wallet:

```bash
npx @blockrun/clawrouter setup     # creates ~/.openclaw/blockrun/mnemonic
```

Send a few USDC on Base or Solana — $5 covers thousands of requests, fully non-custodial. Check it any time with `/clawrouter wallet`.

---

## What you get

### Models

The `/model` picker carries a curated, provider-grouped slice of the catalog (small inline keyboards can't render <!-- br:models.chatVisible -->76<!-- /br:models.chatVisible --> entries); every other model stays routable by full ID.

| Provider          | In the picker                                                                                      |
| ----------------- | -------------------------------------------------------------------------------------------------- |
| **Routing**       | `blockrun/auto` · `blockrun/premium` · `blockrun/eco` · `blockrun/free`                             |
| **Anthropic**     | claude-fable-5 · opus-5 · opus-4.8 · opus-4.7 · sonnet-5 · sonnet-4.6 · haiku-4.5                   |
| **OpenAI**        | gpt-5.6-terra / sol / luna · gpt-5.5 · gpt-5.4-pro / 5.4 / mini / nano · gpt-5.3-codex              |
| **Google**        | gemini-3.1-pro · gemini-3.5-flash · gemini-3.1-flash-lite · gemini-3-flash-preview                  |
| **xAI**           | grok-4.5 · grok-4.3 · grok-build-0.1                                                                |
| **DeepSeek**      | deepseek-v4-pro · deepseek-chat · deepseek-reasoner                                                 |
| **Z.ai**          | glm-5.2 · glm-5.1 · glm-5-turbo · glm-5                                                             |
| **Moonshot / Qwen / MiniMax** | kimi-k3 · qwen3.7-max · minimax-m3 · minimax-m2.7                                       |
| **Free**          | deepseek-v4-flash (1M ctx) · mistral-nemotron · seed-oss-36b · step-3.7-flash · nemotron-3-nano-omni (vision) · nemotron-nano-9b-v2 · nemotron-nano-12b-v2-vl (vision) |

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
| `/clawrouter wallet`                   | Address + USDC balance                   |
| `/clawrouter wallet <base\|solana>`    | Switch payment chain (machine-wide), restarts the proxy |
| `/clawrouter stats`                    | Proxy usage stats                        |
| `/clawrouter status`                   | Proxy health, port, active profile       |
| `/clawrouter route <eco\|auto\|premium>` | Set the routing profile                |
| `/clawrouter help`                     | The list above                           |

### Tools

| Tool                        | Coverage                                                                                  |
| --------------------------- | ----------------------------------------------------------------------------------------- |
| `clawrouter_image_generate` | <!-- br:models.image -->9<!-- /br:models.image --> image models — GPT Image 2, Nano Banana / Pro, Seedream 5 Pro, Grok Imagine, CogView-4 |
| `clawrouter_video_generate` | <!-- br:models.video -->8<!-- /br:models.video --> video models — Seedance 1.5 / 2.0, Grok Imagine, Sora 2 |
| `clawrouter_web_search`     | Exa-powered web search                                                                    |

All three bill from the same wallet — no extra keys, no extra setup.

### CLI

```bash
hermes-clawrouter <setup|update|wallet|doctor|route|stats>
```

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

---

## Wallet

The plugin **reads** the canonical wallet at `~/.openclaw/blockrun/mnemonic` (24-word BIP-39 phrase, mode 0o600) and never writes to it. Create one with:

```bash
npx @blockrun/clawrouter setup
```

Fund USDC on Base or Solana — $5 covers thousands of requests, non-custodial. The same wallet is shared with the upstream TS CLI and every other ClawRouter client on the machine: fund once, use everywhere.

**Headless / CI:** set `BLOCKRUN_WALLET_KEY=<0x raw EVM hex>` to bypass the mnemonic file (EVM-only — Solana derivation unavailable).

---

## Environment variables

| Variable | Effect |
|---|---|
| `CLAWROUTER_PROXY_URL` | Point at an externally-managed proxy (e.g. `https://my-host/v1`). Skips local spawn entirely. |
| `HERMES_CLAWROUTER_AUTOSPAWN=0` | Disable lazy spawn; require `npx @blockrun/clawrouter` to be running already. |
| `BLOCKRUN_WALLET_KEY` | Raw EVM hex private key — overrides the mnemonic file. |
| `CLAWROUTER_ROUTING_PROFILE` | `eco` / `auto` / `premium`. Forwarded to the proxy on spawn. |

`CLAWROUTER_API_KEY` is intentionally a non-secret placeholder (`clawrouter-local`). ClawRouter payments use the local wallet and proxy, but Hermes hides API-key-style providers from `/model` unless the configured key env var exists.

---

## Upgrading

```bash
hermes-clawrouter update      # pip upgrade + refresh the materialized integration
```

A plain `pip install -U` works too: the materialized provider plugin is stamped with the version that wrote it, so the next Hermes start notices an older stamp and rewrites it in place — no `setup --force` needed to pick up newly added models. (Before 0.3.16 that refresh never happened, which is why a bare upgrade could strand you on an old model list.)

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `error: externally-managed-environment` on `pip install` | Do **not** use `--break-system-packages`. Use the one-command installer, or run pip from Hermes' venv (`~/.hermes/hermes-agent/venv/bin/python -m pip install -U hermes-plugin-clawrouter`). |
| `~/.hermes/hermes-agent/venv/bin/hermes: No such file or directory` | Reinstall or repair Hermes first, then re-run the ClawRouter installer. |
| `hermes-clawrouter --version` still shows the old version | Your shell is finding a stale `~/.local/bin/hermes-clawrouter` from a previous `pip --user` install. Re-run the one-command installer; it refreshes that launcher to delegate to Hermes' current venv. |
| `ClawRouter (0 models)` in the picker | Run `hermes-clawrouter setup`, then restart Hermes. |
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
Hermes chat  →  ClawRouter provider (127.0.0.1:8402)  →  blockrun.ai gateway  →  OpenAI / Anthropic / Google / …
                        ↑ spawned + supervised                ↑ x402 USDC micropayment, signed locally
```

1. `hermes` starts → the entry-point plugin loads → `register(ctx)` wires tools, slash commands, CLI, and the skill.
2. `hermes-clawrouter setup` materializes `~/.hermes/plugins/model-providers/clawrouter/{plugin.yaml,__init__.py}` from bundled package data and writes the Hermes config/env hints that current provider and gateway model-picker paths need.
3. Hermes' `providers/__init__.py` discovers the materialized directory and registers `ClawRouterProfile`, pointing `base_url` at `http://127.0.0.1:<port>/v1`.
4. First tool call or chat turn → the supervisor probes `:8402`, spawns `npx -y @blockrun/clawrouter --port <port>` if needed, waits ≤30s for `/v1/models`, then forwards the request.
5. A heartbeat thread restarts the subprocess on death (max 3 restarts/min).

Wallet (BIP-39, Base + Solana), routing (the <!-- br:clawrouter.dimensions -->15<!-- /br:clawrouter.dimensions -->-dimension scorer) and x402 payment all live in the canonical [TypeScript implementation](https://github.com/BlockRunAI/ClawRouter) — this package is a thin Python adapter, not a fork.

**Not a local-inference tool.** Prompts are sent over HTTPS to the blockrun.ai gateway for execution. If you need inference that never leaves your machine, use Ollama.

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

You're here. <!-- br:models.chatVisible -->76<!-- /br:models.chatVisible --> models, smart routing, x402 USDC — native Hermes ergonomics.

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

No. <!-- br:models.free -->7<!-- /br:models.free --> models are free with no wallet, no balance and no signup. Fund USDC only when you want frontier models.

### Where do my keys live?

You have no lab API keys. The only secret is a local BIP-39 mnemonic at `~/.openclaw/blockrun/mnemonic` (mode 0o600), which never leaves the machine — only detached x402 payment signatures are sent. Treat it as a spending account with a small top-up, not a store of value.

### What does it cost to run?

The plugin is MIT and free. You pay per request in USDC, at gateway prices — on `blockrun/auto` that's <!-- br:savings.autoVsBaselinePct -->84<!-- /br:savings.autoVsBaselinePct -->% less than pinning Claude Opus 5 for the same traffic, and <!-- br:savings.ecoVsBaselinePct -->98<!-- /br:savings.ecoVsBaselinePct -->% less on `eco`.

### Can I point it at my own proxy?

Yes — set `CLAWROUTER_PROXY_URL` and the plugin skips the local spawn entirely.

---

<div align="center">

**MIT License** · © [BlockRun](https://blockrun.ai) — agent-native AI infrastructure

⭐ If ClawRouter powers your Hermes agent, consider starring the repo!

</div>
