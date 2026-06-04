---
title: "Diagnosing Hermes `vision_analyze` “Connection error” on a Custom Provider"
description: "Hermes Agent's vision_analyze returns 'Connection error' on a custom OpenAI-compatible provider even though chat works. Here's the root cause and how to fix it."
keywords:
  - hermes vision_analyze connection error
  - hermes custom provider vision
  - hermes auxiliary vision provider
  - nous hermes agent vision fails
  - openai-compatible vision endpoint hermes
canonical: https://blockrun.ai/blog/hermes-vision-analyze-connection-error
audience: Nous Hermes Agent users
related_issue: https://github.com/NousResearch/hermes-agent/issues/38679
---

# Diagnosing Hermes `vision_analyze` “Connection error” on a Custom Provider

If you wired a custom, OpenAI-compatible model into **Nous Hermes Agent** and chat
works perfectly — but `vision_analyze` returns `Error analyzing image: Connection
error.` — you are not misconfiguring anything. This is a known gap in how Hermes
builds its **auxiliary vision client**, and it affects many custom
OpenAI-compatible endpoints.

This post walks through the symptom, the actual root cause, and the fixes — in order
of how little you have to change.

## The symptom

Your `~/.hermes/config.yaml` looks reasonable:

```yaml
model:
  default: my-chat-model
  provider: custom
  base_url: https://my-endpoint.example.com/v1
  api_key: <valid-key>

auxiliary:
  vision:
    provider: custom
    model: my-vision-model
    base_url: https://my-endpoint.example.com/v1
    api_key: <same-valid-key>
    timeout: 120
```

Chat completions work. But the moment a skill or user triggers `vision_analyze`, the
agent log shows:

```
Auxiliary vision (async): connection error on custom (Connection error.), trying fallback
Auxiliary vision (async): connection error on custom and all fallbacks exhausted
```

…and the user gets a generic *"I can't see the image"* response.

The tell-tale detail: **the same endpoint, same key, and same image succeed** when
you call them directly with `curl` or Python `httpx`. The endpoint is healthy — the
problem is on the Hermes client side. This is tracked upstream in
[hermes-agent#38679](https://github.com/NousResearch/hermes-agent/issues/38679).

## Root cause

Hermes does **not** reuse your main chat client for vision. It builds a *separate*
OpenAI SDK client through `resolve_vision_provider_client()` (in
`auxiliary_client.py`), and that client is constructed with different
connection-pool, timeout, and TLS settings than the main chat client. On many custom
HTTPS endpoints the second client fails to establish a connection where the first one
succeeds, and the failure surfaces as the opaque `Connection error.` string from the
OpenAI SDK.

In short: **chat and vision take two different code paths to the same URL, and only
the chat path is well-exercised for custom providers.** The vision path inherits
proxy/TLS/keep-alive assumptions that hold for first-party providers but not for
arbitrary custom endpoints.

## Fix 1 — Remove every difference between the chat and vision config

Because the bug lives in *how the vision client is built*, the lowest-effort
workaround is to eliminate any difference between your chat and vision provider
config, then restart so the clients rebuild identically:

1. Use the **exact same** `base_url`, `api_key`, and `timeout` for `auxiliary.vision`
   as for `model`. Watch for trailing-slash differences and alternate hostnames.
2. If your endpoint sits behind a corporate proxy, confirm `HTTPS_PROXY` / `NO_PROXY`
   are exported in the **gateway's** environment, not just your interactive shell —
   the auxiliary client reads the gateway process env.
3. Restart cleanly: `hermes gateway restart`.

This resolves it in many setups. If the second client still can't negotiate TLS the
way `curl` does, continue to Fix 2.

## Fix 2 — Terminate the auxiliary client on localhost

The remaining failures all share one trait: a remote HTTPS handshake that the
auxiliary client gets wrong. You can remove that variable entirely by pointing
auxiliary tasks at a **local** OpenAI-compatible endpoint on `127.0.0.1`. The
auxiliary client then speaks plain HTTP to localhost — no TLS handshake, no proxy
env, no second-client SSL mismatch — and a local process forwards to your real
upstream model.

Any local OpenAI-compatible proxy works for this; the important part is *terminate
Hermes' auxiliary client on `127.0.0.1` over plain HTTP*. Configure it the same way:

```yaml
auxiliary:
  vision:
    provider: custom
    model: <vision-capable-model>
    base_url: http://127.0.0.1:<port>/v1
    api_key: <local-or-placeholder>
    timeout: 120
```

## Verifying

```bash
# Local endpoint answers:
curl -s http://127.0.0.1:<port>/v1/models | head

# Restart and watch the log while triggering vision:
hermes gateway restart
tail -f ~/.hermes/logs/agent.log
```

A healthy run shows the vision request resolving against the configured provider with
no `connection error … trying fallback` cascade.

## FAQ

**Why does chat work but vision fail on the same URL?**
Hermes builds a *separate* OpenAI client for auxiliary vision via
`resolve_vision_provider_client()`, with different TLS/pool settings than the chat
client. The remote endpoint is fine; the second client can't connect.

**Is this a Hermes bug or my endpoint's bug?**
Hermes. The endpoint returns 200 to `curl`/`httpx` with the same key and image.
Tracked in [hermes-agent#38679](https://github.com/NousResearch/hermes-agent/issues/38679);
once it's fixed upstream, Fix 1 becomes sufficient on its own.

**Does a local proxy slow vision down?**
No meaningfully — the localhost hop is sub-millisecond; the upstream model call
dominates latency exactly as before.

---

*If you'd rather not run and maintain your own local proxy, a ready-made option is
[ClawRouter](https://github.com/BlockRunAI/ClawRouter) — a one-command Hermes plugin
that serves a local OpenAI-compatible endpoint and gives you 55+ vision-capable
models behind it. It's one way to implement Fix 2; the diagnosis above stands
regardless of which proxy you use.*

*Last reviewed against Hermes Agent v0.15.x.*
