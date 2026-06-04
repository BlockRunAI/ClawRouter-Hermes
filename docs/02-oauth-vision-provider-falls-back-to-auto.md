---
title: "Hermes Auxiliary Vision Silently Falls Back to “auto” With an OAuth Provider"
description: "Setting auxiliary.vision.provider to an OAuth provider like minimax-oauth in Hermes Agent logs 'unhandled auth_type' and silently degrades to auto. Here's the root cause and how to get reliable vision."
keywords:
  - hermes oauth provider fallback
  - hermes auxiliary vision provider auto
  - hermes minimax-oauth vision
  - unhandled auth_type hermes
  - hermes vision provider not working
canonical: https://blockrun.ai/blog/hermes-oauth-provider-falls-back-to-auto
audience: Nous Hermes Agent users
related_issue: https://github.com/NousResearch/hermes-agent/issues/38685
---

# Hermes Auxiliary Vision Silently Falls Back to “auto” With an OAuth Provider

You set `auxiliary.vision.provider: minimax-oauth` in **Nous Hermes Agent**. The same
OAuth credentials drive your main conversation fine. But vision quietly stops working
and the agent returns a vague *"I'm not able to view images"* after a long delay. The
log shows:

```
WARNING agent.auxiliary_client: resolve_provider_client: unhandled auth_type oauth_minimax for minimax-oauth
WARNING agent.auxiliary_client: Vision provider minimax-oauth unavailable, falling back to auto vision backends
```

This is reproducible, and it isn't specific to MiniMax — **any OAuth provider not on
Hermes' hard-coded allow-list** hits the same wall. Here's the mechanism and how to
get reliable vision without fighting the OAuth path.

## Root cause

When Hermes needs an auxiliary model (vision, summarization, etc.), it builds a client
through `resolve_provider_client()` in `auxiliary_client.py`. That function has a
**hard-coded set of recognized `auth_type`s**. Your main conversation works because
the *main* code path knows how to mint a client from your OAuth token — but the
auxiliary path's switch statement is narrower.

So when it sees `auth_type: oauth_minimax` (or any OAuth variant it wasn't taught
about), it doesn't raise — it logs `unhandled auth_type` and **silently falls back to
`auto`**. The `auto` chain then tries other backends you may not have configured or
funded, and eventually times out into a generic refusal.

The failure is silent and cascading, which is what makes it confusing: nothing says
*"OAuth isn't supported here."* It just degrades. Tracked upstream as
[hermes-agent#38685](https://github.com/NousResearch/hermes-agent/issues/38685), with
the same root cause in related reports
([#36091](https://github.com/NousResearch/hermes-agent/issues/36091),
[#21521](https://github.com/NousResearch/hermes-agent/issues/21521)).

## Fix — Use an `api_key` provider for auxiliary tasks

The auxiliary client *does* reliably handle the plain `api_key` auth type. So rather
than asking the auxiliary path to replay your OAuth login, point auxiliary tasks at a
provider that authenticates with a simple key:

```yaml
auxiliary:
  vision:
    provider: custom
    model: <vision-capable-model>
    base_url: https://<your-endpoint>/v1
    api_key: <key>
    timeout: 120
```

This sidesteps the `unhandled auth_type` branch entirely.

One caveat: a custom HTTPS endpoint can run into a *separate* auxiliary-client
connection bug (see the companion post on the
[`vision_analyze` "Connection error"](./01-vision-analyze-connection-error-custom-provider.md)).
The most robust setup combines both fixes — **use `api_key` auth, and terminate on
`127.0.0.1`** so there's neither an OAuth branch to miss nor a remote TLS handshake to
get wrong:

```yaml
auxiliary:
  vision:
    provider: custom
    model: <vision-capable-model>
    base_url: http://127.0.0.1:<port>/v1
    api_key: <local-or-placeholder>
    timeout: 120
```

A local OpenAI-compatible proxy holds the upstream credentials (including, if you want,
MiniMax) and exposes them to Hermes as a single `api_key` provider — so you keep the
model and drop the broken auth path.

## Verifying

```bash
hermes gateway restart
tail -f ~/.hermes/logs/agent.log
# Upload an image and ask "what's in this picture?"
```

A correct run resolves against your `api_key` provider with no fallback-to-auto
warning and a real description back in seconds, not a 14-second timeout.

## FAQ

**Why does my main chat work with OAuth but vision doesn't?**
The main and auxiliary code paths build clients differently. The main path handles
your OAuth `auth_type`; the auxiliary path's switch statement doesn't include it, so
it logs `unhandled auth_type` and degrades to `auto`.

**Which providers are affected?**
Any OAuth provider not on the auxiliary client's allow-list. `minimax-oauth` is the
common report; the pattern applies to other non-listed OAuth variants too.

**Is switching to an `api_key` provider a downgrade?**
No. You authenticate once with a stable key (or a local proxy that holds the upstream
keys); it still calls the same premium models. You trade a fragile per-provider OAuth
dance for one reliable code path.

**Do I lose MiniMax if I stop using `minimax-oauth`?**
No — a proxy that fronts MiniMax behind an `api_key` keeps the model available while
avoiding the broken OAuth branch.

---

*If you'd rather not assemble and maintain your own proxy,
[ClawRouter](https://github.com/BlockRunAI/ClawRouter) is a ready-made Hermes plugin
that exposes 55+ models (MiniMax included) as a single local `api_key` provider — one
way to implement the robust setup above. The diagnosis holds regardless of which proxy
you use; track the upstream fix in
[hermes-agent#38685](https://github.com/NousResearch/hermes-agent/issues/38685).*

*Last reviewed against Hermes Agent v0.15.x.*
