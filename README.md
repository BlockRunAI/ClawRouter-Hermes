# hermes-plugin-clawrouter

ClawRouter for [Hermes](https://github.com/NousResearch/hermes-agent) — 55+ LLMs, x402 USDC micropayments, smart routing.

Wraps the existing [ClawRouter](https://github.com/BlockRunAI/ClawRouter) TypeScript proxy as a Hermes plugin. Wallet (BIP-39, Base + Solana), routing (15-dimension scorer), and x402 payment all stay in the canonical TS implementation — this is a thin Python adapter.

## Install

```bash
pip install hermes-plugin-clawrouter
hermes plugins enable clawrouter
hermes clawrouter setup
hermes clawrouter doctor
```

`setup` writes the model-provider plugin to `~/.hermes/plugins/model-providers/clawrouter/` (Hermes only loads provider plugins from that directory; PyPI entry points can't ship them).

## Usage

In a Hermes chat:

- Set model to `blockrun/auto` to use ClawRouter's smart routing.
- `/clawrouter wallet` — address + USDC balance
- `/clawrouter stats` — proxy usage stats
- `/clawrouter status` — proxy health
- `/clawrouter route <eco|auto|premium>` — switch routing profile

Tools (callable from chat):

- `clawrouter_image_generate` — 55+ models incl. DALL-E 3, Flux, Nano Banana
- `clawrouter_video_generate` — Seedance, Grok Imagine
- `clawrouter_web_search` — Exa-powered

## Wallet

The plugin **reads** the canonical wallet at `~/.openclaw/blockrun/mnemonic` (24-word BIP-39 phrase, mode 0o600). To create one:

```bash
npx @blockrun/clawrouter setup
```

Then fund USDC on Base or Solana — $5 covers thousands of requests, non-custodial. The plugin never writes to the wallet.

### Headless / CI

Set `BLOCKRUN_WALLET_KEY=<0x raw EVM hex>` to bypass the mnemonic file (EVM-only — Solana derivation unavailable).

## Environment variables

| Variable | Effect |
|---|---|
| `CLAWROUTER_PROXY_URL` | Point at an externally-managed proxy (e.g. `https://my-host/v1`). Skips local spawn entirely. |
| `HERMES_CLAWROUTER_AUTOSPAWN=0` | Disable lazy spawn; require `npx @blockrun/clawrouter` to be running already. |
| `BLOCKRUN_WALLET_KEY` | Raw EVM hex private key — overrides the mnemonic file. |
| `CLAWROUTER_ROUTING_PROFILE` | `eco` / `auto` / `premium`. Forwarded to the proxy on spawn. |

## How it works

1. `hermes` starts → the entry-point plugin is loaded → `register(ctx)` wires tools, slash commands, CLI, and the skill.
2. `hermes clawrouter setup` materializes `~/.hermes/plugins/model-providers/clawrouter/{plugin.yaml,__init__.py}` from bundled package data.
3. Hermes' `providers/__init__.py` discovers the materialized directory and registers the `ClawRouterProfile`, pointing `base_url` at `http://127.0.0.1:<port>/v1`.
4. First tool call or chat turn → the supervisor probes `:8402`, spawns `npx -y @blockrun/clawrouter --port <port>` if needed, waits ≤30s for `/v1/models`, then forwards the request.
5. A heartbeat thread restarts the subprocess on death (max 3 restarts/min).

## Distribution

The Python package ships **both** logical plugins:

- **Standalone** plugin (this PyPI entry point): tools, slash commands, CLI, skill.
- **Model-provider** plugin (materialized into `~/.hermes/plugins/model-providers/clawrouter/` by `hermes clawrouter setup`): `ProviderProfile` registration.

This split is required because Hermes' PluginManager (`hermes_cli/plugins.py`) skips `register(ctx)` for `kind: model-provider`, and entry-point plugins always load as `kind: standalone`.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT. © BlockRun.
