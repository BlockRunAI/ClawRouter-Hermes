# hermes-plugin-clawrouter

ClawRouter for [Hermes](https://github.com/NousResearch/hermes-agent) — 55+ LLMs, x402 USDC micropayments, smart routing.

Wraps the existing [ClawRouter](https://github.com/BlockRunAI/ClawRouter) TypeScript proxy as a Hermes plugin. Wallet (BIP-39, Base + Solana), routing (15-dimension scorer), and x402 payment all stay in the canonical TS implementation — this is a thin Python adapter.

## Install

Recommended one-command installer:

```bash
curl -fsSL https://raw.githubusercontent.com/BlockRunAI/ClawRouter-Hermes/main/scripts/install.sh | bash
```

The installer avoids Debian/Ubuntu's `externally-managed-environment` / PEP 668
trap by installing the plugin into Hermes' own Python environment instead of
system Python. It then enables the plugin, runs setup, and prints doctor checks.

Manual install is still fine if you already know where Hermes' Python environment
lives:

```bash
~/.hermes/hermes-agent/venv/bin/python -m pip install -U hermes-plugin-clawrouter
hermes plugins enable clawrouter
hermes-clawrouter setup
hermes-clawrouter doctor
```

If `pip install hermes-plugin-clawrouter` shows `externally-managed-environment`,
do **not** use `--break-system-packages`. Use the installer above, or run pip from
Hermes' venv as shown. If `hermes` says `~/.hermes/hermes-agent/venv/bin/hermes:
No such file or directory`, reinstall/repair Hermes first, then rerun the
ClawRouter installer.

`setup` writes the model-provider plugin to `~/.hermes/plugins/model-providers/clawrouter/`, seeds `CLAWROUTER_API_KEY=clawrouter-local` in `~/.hermes/.env`, and registers ClawRouter in `~/.hermes/config.yaml` so Hermes' `/model` picker can show the provider and curated BlockRun chat models.

`CLAWROUTER_API_KEY` is intentionally a non-secret placeholder. ClawRouter payments use the local wallet/proxy, but Hermes hides API-key-style providers from `/model` unless the configured key env var exists.

`hermes-clawrouter` is provided because some Hermes releases do not add plugin-defined top-level CLI commands before the plugin is enabled. Once the plugin is loaded, `hermes clawrouter <setup|wallet|doctor|route|stats>` may also be available.

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

### Auxiliary vision

Hermes' `vision_analyze` builds a *separate* OpenAI client for the configured
`auxiliary.vision` provider. That path is fragile for remote custom endpoints
([hermes-agent#38679](https://github.com/NousResearch/hermes-agent/issues/38679):
`Connection error`) and for OAuth providers
([#38685](https://github.com/NousResearch/hermes-agent/issues/38685): silent fallback
to `auto`). Routing vision through ClawRouter sidesteps both — it's a single
`api_key` provider on `127.0.0.1`, so there's no OAuth branch to miss and no remote
TLS handshake to mishandle. Add to `~/.hermes/config.yaml`:

```yaml
auxiliary:
  vision:
    provider: clawrouter
    model: blockrun/auto          # or google/gemini-2.5-pro, anthropic/claude-sonnet-4.6
    base_url: http://127.0.0.1:8402/v1
    api_key: clawrouter-local
    timeout: 120
```

`setup` does **not** write this automatically — it would overwrite an existing vision
config — so add it by hand if you want vision through ClawRouter, then
`hermes gateway restart`.

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

## Guides

Troubleshooting and how-to articles for common Hermes provider/vision setups. Each
is a standalone problem→solution walkthrough:

| Guide | When you need it |
|---|---|
| [`vision_analyze` "Connection error" on a custom provider](docs/01-vision-analyze-connection-error-custom-provider.md) | Chat works but `vision_analyze` returns `Connection error` on a custom OpenAI-compatible endpoint ([hermes-agent#38679](https://github.com/NousResearch/hermes-agent/issues/38679)) |
| [Auxiliary vision falls back to "auto" with an OAuth provider](docs/02-oauth-vision-provider-falls-back-to-auto.md) | `auxiliary.vision.provider` (e.g. `minimax-oauth`) logs `unhandled auth_type` and silently degrades ([#38685](https://github.com/NousResearch/hermes-agent/issues/38685)) |
| [Run GPT-5, Claude, Gemini & DeepSeek from one endpoint](docs/03-one-endpoint-gpt-claude-gemini-deepseek.md) | You want many models in Hermes without a separate provider/key block per model |
| [Pay-per-call LLM access — no API keys](docs/04-pay-per-call-llm-no-api-keys-hermes.md) | You'd rather pay per request with USDC than manage and rotate provider API keys |
| [Behind an HTTP proxy/VPN: timeouts, 500s, `Premature close`](docs/05-proxy-vpn-timeouts-premature-close.md) | Small requests work but large agentic requests 500 or time out after payment — your proxy (mihomo/clash/corporate) isn't being used by ClawRouter's upstream traffic |
| [Retry-and-repay loop: `Invalid character in header content ["x-clawrouter-reasoning"]`](docs/06-invalid-character-header-cyrillic-reasoning.md) | Non-English prompts (Cyrillic/CJK) on ClawRouter ≤ 0.12.207 crash response delivery after payment settles; Hermes retries and re-pays the same request |

## How it works

1. `hermes` starts → the entry-point plugin is loaded → `register(ctx)` wires tools, slash commands, CLI, and the skill.
2. `hermes-clawrouter setup` materializes `~/.hermes/plugins/model-providers/clawrouter/{plugin.yaml,__init__.py}` from bundled package data and writes Hermes config/env hints needed by current Hermes provider and gateway model-picker paths.
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
