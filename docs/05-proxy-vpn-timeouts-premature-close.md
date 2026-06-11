---
title: "Running Hermes + ClawRouter Behind an HTTP Proxy or VPN (Timeouts, 500s, Premature close)"
description: "Large agentic requests through ClawRouter time out or 500 while small curl tests work — the classic symptom of upstream traffic bypassing your local proxy. How to route ClawRouter through mihomo/clash/v2ray correctly."
keywords:
  - clawrouter proxy timeout
  - hermes clawrouter premature close
  - clawrouter mihomo clash vpn
  - clawrouter HTTPS_PROXY BLOCKRUN_UPSTREAM_PROXY
  - clawrouter request timed out 300000ms
  - blockrun free tier 500
canonical: https://blockrun.ai/blog/clawrouter-proxy-vpn-timeouts
audience: Hermes Agent users running ClawRouter behind a local proxy (mihomo, clash, v2ray, corporate proxies) or in regions with throttled routes
---

# Running Hermes + ClawRouter Behind an HTTP Proxy or VPN

If you route your machine's traffic through a local HTTP proxy (mihomo, clash,
v2ray, a corporate proxy) and see this pattern with Hermes + ClawRouter:

- Small requests work — `curl` to `/v1/chat/completions` with `"hi"` answers instantly,
  `/health` and `/v1/models` return 200.
- Large agentic requests (full system prompt + dozens of tools) fail:
  - **Free models**: immediate `HTTP 500` on every model.
  - **Paid models**: payment signs, then `Request timed out after 300000ms`
    (or `180000ms` for reasoning models), intermittently succeeding.
  - Logs show `Premature close` or `socket not writable, dropping bytes`.

…then your proxy is almost certainly **not being used by ClawRouter at all**.

## Root cause: Node's fetch ignores `HTTP_PROXY`/`HTTPS_PROXY`

`curl`, Python `requests`, and most CLI tools honor the standard proxy
environment variables. **Node's built-in `fetch` (undici) does not.** So when
your shell exports `https_proxy=http://127.0.0.1:7890`:

- your `curl` test goes **through the proxy** → clean exit route → works;
- ClawRouter's upstream calls to `blockrun.ai` go **direct from your machine**.

On a clean network the direct route also works, so nobody notices. On a
throttled or DPI-filtered route (e.g. direct connections from some regions to
Google-hosted infrastructure), the direct path drops **large request bodies**
and **long-lived responses** while letting small packets through. That is
exactly why `"hi"` succeeds and a 300 KB agentic payload dies:

| Symptom | What actually happened |
|---|---|
| Free tier: instant 500 on every model | The upload was reset in transit; ClawRouter wraps any upstream network error as HTTP 500 and the fallback chain exhausts in seconds |
| Paid: "payment signs, then timeout" | x402 signing is **purely local** (it proves nothing about connectivity); the request then stalled on the direct route until ClawRouter's per-model (60s/180s) or global (300s) timer fired |
| `Premature close` | The connection was reset mid-response — by the network path, not by BlockRun |
| Intermittent success | Throttling is probabilistic; some connections slip through |

## Fix

**ClawRouter ≥ 0.12.207** honors the standard env vars automatically. Make sure
the proxy variables are exported in the environment that launches Hermes (the
plugin passes its environment to the spawned ClawRouter):

```bash
export HTTPS_PROXY=http://127.0.0.1:7890   # your mihomo/clash mixed port
export HTTP_PROXY=http://127.0.0.1:7890
hermes
```

On startup you should see:

```
[ClawRouter] Upstream proxy: http://127.0.0.1:7890
```

Notes:

- `BLOCKRUN_UPSTREAM_PROXY` still takes precedence when set, and is the only
  way to use a **SOCKS** proxy (`BLOCKRUN_UPSTREAM_PROXY=socks5://127.0.0.1:1080`) —
  SOCKS URLs found in the standard env vars are deliberately not auto-applied.
- `NO_PROXY` is honored, and loopback (`localhost`, `127.0.0.1`, `::1`) is
  always excluded so the Hermes ↔ ClawRouter hop on `127.0.0.1:8402` stays direct.
- On **older ClawRouter versions** (< 0.12.207), set the explicit variable:
  `BLOCKRUN_UPSTREAM_PROXY=http://127.0.0.1:7890`.
- If you run your proxy in **TUN mode** (system-wide transparent routing),
  none of this is needed — all TCP already flows through the tunnel.

## Verifying the route

1. Start Hermes, send one large agentic message.
2. Check your proxy's connection log — you should see `CONNECT blockrun.ai:443`
   (and `mainnet.base.org:443` for wallet RPC) from the ClawRouter process.
3. If `blockrun.ai` never appears in the proxy log while the request fails,
   ClawRouter is still going direct.

## "I paid — did I lose money on the timed-out request?"

Mostly no. The x402 payment signature (EIP-3009 `transferWithAuthorization`) is
created locally and moves no funds by itself. USDC only leaves your wallet when
the gateway **settles** the payment, which happens *after* the upstream model
finishes. If your request died in transit before reaching the gateway, nothing
was charged — check your wallet's actual USDC transfer history, not the
"payment signed" log lines. The gateway also skips settlement when it detects
the client disconnected before a (non-streaming) response could be delivered.
