---
name: superinstance-api
description: The fleet's shared context brain on Cloudflare — MCP tools (book/near/since/tiles/pinch/field_query/witness_get) over D1+Vectorize. Use when any agent needs to book learning, recall semantically, or share reflexes fleet-wide.
---

# superinstance-api — the fleet brain

One Worker, five layers: **tiles** for knowledge (Lamport versions, full→gist→hint
tiers, demotion needs a measurement receipt), **vectors** for meaning (bge-m3 →
Vectorize), **reflexes** for speed (pinch: known intent → deterministic answer,
zero LLM), **γ/η fields** for honesty (cost + surprise booked per call,
conservation γ+η ≤ 1585), **stages** for growth (adding a cell advances a stage).

**LIVE:** https://superinstance-api.casey-digennaro.workers.dev

## Connect (any MCP client)

Streamable HTTP at `/mcp` (initialize → tools/list → tools/call).
Ready-made configs: `clients/README.md` in the repo (Claude Code, OpenCode,
OpenClaw streamable-http, curl/REST).

## Tools

- `book` — append a learning (gist + receipt_url + books_to) → D1 row + embedding
- `near` — semantic recall (query → k nearest bookings/tiles + scores)
- `since` — timeline since ts (fleet heartbeat sync)
- `tile_file` / `tile_get` / `tile_history` — room-tile CRUD, Lamport versions
- `tile_demote` — tier downgrade, REQUIRES a measurement receipt
- `pinch` — {intent, context} → known reflex (FIRE) | CONFIRM | ESCALATE;
  escalations compile back so the API gets faster with use
- `intents_list` / `GET /intents` — reflex inventory
- `field_query` — γ/η/conservation per cell/sheet
- `witness_get` — receipt lookup (the honesty surface)

## Auth

Per-agent bearer tokens: local `~/.config/superinstance/<agent>.token` (read at
use-time, never echo, never commit); Worker side env `SI_API_TOKENS`
(comma-separated). Bookings attribute to the calling agent.

## Gotchas (banked the hard way)

- `CF_API_TOKEN` from key.txt FAILS API verify (6111). Deploys use wrangler's
  stored OAuth (`~/.wrangler/config/default.toml`). Do NOT set
  CLOUDFLARE_API_TOKEN.
- wrangler.toml: the AI binding is `[ai]` (object) — `[[ai]]` array-of-tables
  is REJECTED.
- Vectorize metadata filters return empty even when unfiltered queries match —
  pinch queries topK=10 unfiltered and filters by `kind` in JS. Keep doing that.
- Empty-string metadata values get Vectorize upserts SILENTLY REJECTED — omit
  absent fields, never send `""`.
- Local reflex join: `scripts/lever_bridge.py --pull-fleet | --push-local`
  syncs fleet pinch ↔ local lever-runner reflexes. ESCALATE → local lever
  resolves → compile back → every agent inherits it.

## Neighbors

i2i-ledger (the booking pattern this extends) · lever-runner (local reflex
twin) · quilt-dba (stages; the 1585 budget is its log₂3 scaled) · exoj
(γ/η field seam) · plato-cf (absorbed tile layer).
