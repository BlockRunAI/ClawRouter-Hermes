---
name: clawrouter
description: Hosted-gateway LLM router — save 87% on inference costs. A local proxy that forwards each request to the blockrun.ai gateway, which routes to the cheapest capable model across <!-- br:models.chatVisible -->76<!-- /br:models.chatVisible --> models from OpenAI, Anthropic, Google, DeepSeek, xAI, NVIDIA, and more. <!-- br:models.free -->7<!-- /br:models.free --> free models included. Also exposes realtime market data (global stocks, crypto, FX, commodities), Twitter/X intelligence, and prediction-market data across Polymarket, Kalshi, Limitless, Opinion, Predict.Fun, dFlow + UMA oracle resolution + wallet identity & clustering as built-in agent tools. Not a local-inference tool — prompts are sent to the blockrun.ai gateway.
triggers:
  - "clawrouter"
  - "claw router"
  - "@blockrun/clawrouter"
  - "blockrun gateway"
  - "blockrun llm router"
  - "blockrun ai gateway"
  - "blockrun.ai inference"
  - "save on llm costs blockrun"
  - "cheapest model blockrun"
  - "free nvidia models blockrun"
  - "x402 llm payment"
  - "usdc llm gateway"
  - "openrouter alternative"
homepage: https://blockrun.ai/clawrouter.md
repository: https://github.com/BlockRunAI/ClawRouter
license: MIT
metadata:
  {
    "openclaw":
      {
        "emoji": "🦀",
        "requires": { "config": ["models.providers.blockrun"] },
        "install":
          [
            {
              "id": "node",
              "kind": "node",
              "package": "@blockrun/clawrouter",
              "bins": ["clawrouter"],
              "label": "Install ClawRouter (npm)",
            },
          ],
      },
  }
---

# ClawRouter (Hermes)

## Quick Start (Hermes plugin)

Recommended:

```bash
curl -fsSL https://raw.githubusercontent.com/BlockRunAI/ClawRouter-Hermes/main/scripts/install.sh | bash
```

Manual install, if you know Hermes' Python venv path:

```bash
~/.hermes/hermes-agent/venv/bin/python -m pip install -U hermes-plugin-clawrouter
hermes plugins enable clawrouter
hermes clawrouter setup       # installs the model-provider plugin + verifies wallet
hermes clawrouter doctor      # green = ready
```

If plain `pip install hermes-plugin-clawrouter` fails with Debian/Ubuntu's
`externally-managed-environment`, do not use `--break-system-packages`; install
into Hermes' venv or use the one-command installer. The installer also checks
for Python, pip/venv support, `pipx`, and Node/npm/npx, and installs missing
basics through common OS package managers when available.

Then in a Hermes chat session:

- Pick model `blockrun/auto` for smart routing across <!-- br:models.chatVisible -->76<!-- /br:models.chatVisible --> models.
- `/clawrouter account` — which rail you're paying on (wallet or API key)
- `/clawrouter wallet` — show address + USDC balance (Solana and Base)
- `/clawrouter stats` — proxy usage
- `/clawrouter status` — proxy health
- `/clawrouter route <eco|auto|premium>` — switch routing profile
- `/clawrouter logout` — drop the API key, go back to the wallet
- Tools: `clawrouter_image_generate`, `clawrouter_video_generate`, `clawrouter_web_search`

## Two ways to pay

Same catalog and same model ids either way — what differs is the credential and the host.

| | Wallet (x402) | API key (account credit) |
|---|---|---|
| Set up | `npx @blockrun/clawrouter setup` | Sign in at https://user.blockrun.ai, mint a key |
| Funding | USDC on Solana or Base | Card top-up at /dashboard/credits |
| Gateway | `sol.blockrun.ai/api` · `blockrun.ai/api` | `api.blockrun.ai` |
| Turn on | the default | `hermes-clawrouter login brk_live_…` |

```bash
hermes-clawrouter login brk_live_...   # bill account credit
hermes-clawrouter account              # what's live right now
hermes-clawrouter logout               # back to the x402 wallet
```

A key wins over a wallet whenever both are present, and nothing is deleted — `logout` reverses it.
Needs `@blockrun/clawrouter` >= 0.12.268; older proxies ignore the key and spend the wallet instead.
Key resolution order: `BLOCKRUN_API_KEY` env → `~/.blockrun/.api-key` → `~/.openclaw/blockrun/api-key`.
Type keys in a terminal, never in a chat — `/clawrouter login` refuses for that reason.

Wallet lives at `~/.openclaw/blockrun/mnemonic` (shared with the upstream TS CLI — fund once, use everywhere). Override with `BLOCKRUN_WALLET_KEY` env for headless setups. Set `CLAWROUTER_PROXY_URL` to point at an externally-managed proxy.

---

Hosted-gateway LLM router that saves <!-- br:savings.autoVsBaselinePct -->84<!-- /br:savings.autoVsBaselinePct -->% on inference costs by forwarding each request to the blockrun.ai gateway, which picks the cheapest model capable of handling it across <!-- br:models.chatVisible -->76<!-- /br:models.chatVisible --> models from 12 providers (<!-- br:models.free -->7<!-- /br:models.free --> free models). Billing flows through one credential — a local USDC wallet, or one BlockRun API key from https://user.blockrun.ai. Either way you do not hold provider API keys.

**This is not a local-inference tool.** ClawRouter is a thin local proxy. Your prompts are sent over HTTPS to the blockrun.ai gateway for model execution. If your workload requires inference that never leaves your machine, use a local runtime like Ollama — ClawRouter is not the right tool for that use case.

Source: https://github.com/BlockRunAI/ClawRouter · npm: https://www.npmjs.com/package/@blockrun/clawrouter · License: MIT.

## Data Flow

```
Your app → localhost proxy (ClawRouter) → https://sol.blockrun.ai/api  (wallet, Solana)
                                        → https://blockrun.ai/api      (wallet, Base)
                                        → https://api.blockrun.ai      (API key)
                                              ↓
                                        OpenAI / Anthropic / Google / etc.
                                              ↓
                                        Response → back through proxy → your app
```

**Sent to the gateway on every request:** the model name, the full prompt/messages body, sampling params (temperature, max_tokens, tools, etc.), and one credential — either an `X-PAYMENT` header containing a signed x402 USDC micropayment (wallet rail), or an `Authorization: Bearer brk_…` header (API-key rail). Never both: an x402 header on an API-key request is a payment nobody asked for, and the proxy strips it.

**Not sent:** your wallet private key (only the detached payment signature is sent), any other local files, environment variables, or OpenClaw config beyond what's needed for this request.

**Blockrun's privacy stance:** https://blockrun.ai/privacy. Treat prompts the same way you'd treat prompts sent to any hosted LLM API (OpenAI, Anthropic, etc.) — do not send data you would not share with a third-party API provider.

## Credentials & Local Key Storage

ClawRouter does **not** collect or forward third-party provider API keys. You do not supply OpenAI, Anthropic, Google, DeepSeek, xAI, or NVIDIA credentials — the blockrun.ai gateway owns those relationships.

There is exactly one optional BlockRun credential: a `brk_…` API key, stored `0600` at `~/.blockrun/.api-key` (or supplied via `BLOCKRUN_API_KEY`) and sent as a bearer token to exactly one host, `api.blockrun.ai`. It is never logged in full — status output masks it to head-and-tail. It is optional: with no key configured, ClawRouter signs x402 payments from the local wallet instead and contacts no account service.

**What `models.providers.blockrun` stores (fully enumerated):**

| Field       | Sensitive | Purpose                                                                                                                                                                                                    |
| ----------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `walletKey` | Yes       | EVM private key used to sign USDC micropayments via x402. **Auto-generated locally on first run** — no user input required. Never transmitted over the network; only detached payment signatures are sent. |
| `solanaKey` | Yes       | Solana keypair (BIP-44 `m/44'/501'/0'/0'`). Auto-derived from the same local mnemonic via `@scure/bip32` + `@scure/bip39`.                                                                                 |
| `gateway`   | No        | Gateway URL. Defaults: `https://blockrun.ai/api` (Base) · `https://sol.blockrun.ai/api` (Solana).                                                                                                          |
| `routing`   | No        | Optional override of the default four-tier router.                                                                                                                                                         |

**How and where keys are stored:**

- Keys live in the OpenClaw user config file — typically `~/.config/openclaw/config.json` on Linux, `~/Library/Application Support/openclaw/config.json` on macOS, `%APPDATA%\openclaw\config.json` on Windows — under the `models.providers.blockrun` path.
- Written by OpenClaw's standard config writer with `0600` permissions on POSIX systems (owner read/write only).
- **Stored in plaintext**, the same way every OpenClaw provider's API key is stored. ClawRouter does not add an extra encryption layer; your filesystem permissions are the security boundary. If you require an encrypted keystore, run OpenClaw on an encrypted volume (FileVault, LUKS, BitLocker) or use a dedicated burner wallet funded only with what you intend to spend.
- Auto-generation uses `@scure/bip39` to produce a 24-word mnemonic, then BIP-44 derivation for both chains. Source: [`src/wallet.ts`](https://github.com/BlockRunAI/ClawRouter/blob/main/src/wallet.ts).

**Operational guidance:** treat the wallet as a spending account with a small top-up, not a long-term store of value. Fund it with what you expect to spend on LLM calls. If the host machine is compromised, the wallet key is compromised — rotate and refund.

## Supply-Chain Integrity

- Every release is tagged on GitHub: https://github.com/BlockRunAI/ClawRouter/releases
- Every release publishes to npm with a matching version: https://www.npmjs.com/package/@blockrun/clawrouter?activeTab=versions
- The `skills/release/SKILL.md` mandatory checklist enforces: same version in `package.json`, matching git tag, matching GitHub release, and matching npm publish.
- To verify locally: `npm pack @blockrun/clawrouter@<version>` and compare the tarball contents to the tagged commit.

## Install

```bash
openclaw plugins install @blockrun/clawrouter
```

The structured `install` block above tells OpenClaw to install the auditable npm package `@blockrun/clawrouter`. Source for every version is on GitHub; every release is tagged.

## Setup

```bash
# Enable smart routing (auto-picks cheapest model per request)
openclaw models set blockrun/auto

# Or pin a specific model
openclaw models set openai/gpt-4o
```

## How Routing Works

ClawRouter classifies each request into one of four tiers:

- **SIMPLE** — factual lookups, greetings, translations → gemini-2.5-flash ($0.30/$2.50)
- **MEDIUM** — summaries, explanations, data extraction → kimi-k2.7 ($0.95/$4.00)
- **COMPLEX** — code generation, multi-step analysis → gemini-3.1-pro ($2/$12)
- **REASONING** — proofs, formal logic, multi-step math → grok-4-1-fast-reasoning ($0.20/$0.50)

Prices are per 1M input/output tokens, on the default `auto` profile. Per-tier
savings percentages are deliberately not quoted: the published figure is blended
across a stated workload mix, and a per-tier number invites comparison against a
baseline nobody wrote down. See
[savings-mix.json](https://github.com/BlockRunAI/blockrun/blob/main/src/brand/savings-mix.json).

Rules handle ~80% of requests in <1ms. Only ambiguous queries hit the LLM classifier (~$0.00003 per classification).

## Available Models

<!-- br:models.chatVisible -->76<!-- /br:models.chatVisible --> models including: claude-fable-5, claude-opus-5, claude-opus-4.8, claude-opus-4.7, claude-sonnet-5, claude-sonnet-4.6, gpt-5.6-sol, gpt-5.6-terra, gpt-5.6-luna, gpt-5.5, gpt-5.4, gemini-3.1-pro, gemini-3.5-flash, grok-4.5, grok-4.3, grok-build-0.1, deepseek-v4-pro, deepseek-v4-flash-vision-exp [vision], deepseek-chat, glm-5.2, kimi-k3, minimax-m3, qwen3.7-max, and the curated free models (nemotron-3.5-lightning, nemotron-3-nano-30b, laguna-xs-2.1, north-mini-code, nemotron-3-nano-omni-30b-a3b-reasoning [vision], nemotron-3-ultra-550b, llama-3.2-11b-vision [vision]).

## Built-in Agent Tools

In addition to LLM routing, ClawRouter exposes BlockRun's x402-gated data APIs as ready-to-use OpenClaw tools. Every tool is paid from the same USDC wallet — no extra setup, no extra API keys.

### Market Data

Realtime prices and historical OHLC across every asset class. The agent should call these directly instead of scraping finance sites.

| Tool                       | Coverage                                                                        | Price         |
| -------------------------- | ------------------------------------------------------------------------------- | ------------- |
| `blockrun_stock_price`     | 12 global markets: US (NYSE/Nasdaq), HK, JP, KR, UK, DE, FR, NL, IE, LU, CN, CA | $0.001 / call |
| `blockrun_stock_history`   | OHLC bars at 1/5/15/60/240-min or D/W/M resolution                              | $0.001 / call |
| `blockrun_stock_list`      | Ticker lookup / company-name search per market                                  | Free          |
| `blockrun_crypto_price`    | BTC-USD, ETH-USD, SOL-USD, and more                                             | Free          |
| `blockrun_fx_price`        | EUR-USD, GBP-USD, JPY-USD, and more                                             | Free          |
| `blockrun_commodity_price` | XAU-USD (gold), XAG-USD (silver), XPT-USD (platinum)                            | Free          |

### Image & Video Generation

| Tool                        | Purpose                                                                     | Price                |
| --------------------------- | --------------------------------------------------------------------------- | -------------------- |
| `blockrun_image_generation` | 8 image models — GPT Image 1/2, Nano Banana / Pro, Seedream 5 Pro, Grok Imagine / Pro, CogView-4 | $0.015–$0.15 / image |
| `blockrun_image_edit`       | Edit / inpaint existing image (openai/gpt-image-1)                          | $0.02–$0.04 / image  |
| `blockrun_video_generation` | Grok Imagine + ByteDance Seedance (1.5-pro / 2.0-fast / 2.0) + Sora 2, 5–10s | $0.03–$0.30 / second |

### Prediction Markets (Predexon)

Full prediction-market toolbox spanning **Polymarket, Kalshi, Limitless, Opinion, Predict.Fun, dFlow** + Binance for crypto candles. **57 endpoints (Predexon v2) exposed as 9 agent tools** (8 named ergonomic wrappers + 1 catch-all):

- **Markets & trading** — events, markets list per venue, cross-venue search (`markets/search`), orderbooks, candlesticks (per-market and per-token), trades, positions, volume charts.
- **Leaderboard & smart money** — global + per-market leaderboards, smart-money positioning, top holders, smart-activity feed.
- **Wallet analytics** — full wallet profile, P&L time series, per-market breakdown, similar-wallet discovery, batch profiles, AND/OR filters.
- **UMA oracle + wallet identity** — UMA optimistic-oracle resolution status (`uma/markets`, `uma/market/{conditionId}`); wallet identity labels (ENS / Lens / exchange / risk tags), bulk identity, on-chain cluster discovery.

| Tool                                 | Coverage                                                                                                                                                                                                                                                                             | Price                  |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------- |
| `blockrun_predexon_events`           | Live Polymarket events with current odds                                                                                                                                                                                                                                             | $0.001 / call          |
| `blockrun_predexon_markets`          | Search Polymarket markets by keyword                                                                                                                                                                                                                                                 | $0.001 / call          |
| `blockrun_predexon_leaderboard`      | Top Polymarket traders ranked by profit                                                                                                                                                                                                                                              | $0.001 / call          |
| `blockrun_predexon_smart_money`      | Smart-money positions on a specific market                                                                                                                                                                                                                                           | $0.005 / call          |
| `blockrun_predexon_smart_activity`   | Markets where smart money is currently active                                                                                                                                                                                                                                        | $0.005 / call          |
| `blockrun_predexon_wallet`           | Polymarket wallet profile (PnL, winrate, positions)                                                                                                                                                                                                                                  | $0.005 / call          |
| `blockrun_predexon_wallet_pnl`       | Wallet P&L time series                                                                                                                                                                                                                                                               | $0.005 / call          |
| `blockrun_predexon_matching_markets` | Polymarket ↔ Kalshi market pairs (arb compare)                                                                                                                                                                                                                                       | $0.005 / call          |
| `blockrun_predexon_endpoint_call`    | Catch-all for the remaining 49 endpoints — orderbooks, candlesticks, top-holders, UMA oracle, wallet identity/cluster, Kalshi/Limitless/Opinion/Predict.Fun, dFlow, Binance Futures, cross-venue search, sports, canonical markets. Takes `path` + optional `method`/`query`/`body`. | $0.001 / $0.005 / call |

Pricing: `$0.001` per market-data call, `$0.005` per analytics / search / wallet call. See the `predexon` skill for the full endpoint reference.

## Example Output

```
[ClawRouter] google/gemini-2.5-flash (SIMPLE, rules, confidence=0.92)
             Cost: $0.0025 | Baseline: $0.308 | Saved: 99.2%
```
