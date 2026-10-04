# superinstance-api — the fleet's growing context brain, with MCP tooling

**LIVE: https://superinstance-api.casey-digennaro.workers.dev** (v0.1.0, deployed 2026-09-29,
D1 `superinstance-db` + Vectorize `superinstance-index` + Workers AI bge-m3).

*Design receipt, 2026-09-29. Directive arc (Casey): rebuild PLATO as a tool →
"design systems for context management... as an automated growing api that all
agents in our ecosystem can use, maybe something quilted and vectorized in
cloudflare" → "internal pincher/exoj/quilt-dba synergy" → "a superinstance-api
with mcp tooling". This unifies plato-cf (absorbed as the tile subsystem) and
extends the live i2i-ledger (already serving /book /near /since on Workers+D1+
Vectorize).*

## The one-liner

One Cloudflare Worker that is the fleet's shared memory: **tiles for knowledge,
vectors for meaning, reflexes for speed, γ/η fields for honesty, stages for
growth** — exposed to every agent (Claude Code, OpenCode, Kimi, MMX, OpenClaw,
GLM subagents) as native **MCP tools**.

## Five layers (the synergy, mapped)

1. **Authority — tiles & rooms (plato-cf absorbed).** D1 tables; every tile
   Lamport-versioned, tiered full→gist→hint; demotion requires a measurement
   receipt (fact_survival / lattice_snap). Nothing deleted, ever.
2. **Meaning — vectorized recall (i2i-ledger pattern, live).** Workers AI
   bge-m3 → Vectorize; /near semantic recall across every booking + tile.
   Provider-tagged index identity (fleet-memory) so embedding models can swap
   without rebuild.
3. **Reflex — the pincher seam.** Intents table + Vectorize near-match:
   known intent → deterministic answer (<50ms, zero LLM); semi-known →
   confirm; unknown → escalate to caller (the thinking layer), and the
   escalated resolution gets compiled back as a new reflex. The cortex
   teaches the spinal cord; the API itself gets faster with use.
4. **Field — the exoj seam.** Every call books γ (compute cost) and η
   (surprise vs. the vector neighborhood); per-cell conservation
   γ+η ≤ 1585 (quilt-dba's log₂3 budget, integer-scaled). Observers =
   functors: cross-family consensus (the measured 3/3 canon chord) reads as
   agreement between observers, not new ontology.
5. **Growth — the quilt-dba seam.** The API is a growing sheet: cells load in
   stages; adding a cell IS advancing a stage (E-D1: R1 GROWTH confirmed at
   eval 299). Context management = the developmental memory of the fleet, not
   a static store.

## MCP surface (Streamable HTTP on the same Worker)

Tools exposed via Model Context Protocol — any MCP-capable client connects
once and gets the fleet brain:

- `book` — append a learning/booking (gist + receipt_url + books_to) → D1 row
  + embedding. Books γ/η of the call.
- `near` — semantic recall (query → k nearest bookings/tiles with scores).
- `since` — timeline since ts (fleet heartbeat sync).
- `tile_file` / `tile_get` / `tile_history` — room-tile CRUD with Lamport
  versions; `tile_demote` (tier downgrade, requires measurement receipt).
- `pinch` — reflex lookup: {intent, context} → known reflex | CONFIRM |
  ESCALATE (and the compile-back path).
- `field_query` — γ/η/conservation state per cell/sheet, surprise timeline.
- `witness_get` — receipt lookup by id/url (the honesty surface).

## Auth

Per-agent bearer tokens (extends the i2i single-token pattern) — bookings
attribute to agents; tokens at `~/.config/superinstance/<agent>.token` locally,
env secret `SI_API_TOKENS` (comma-separated) on the Worker.

## Build order

- [x] Design receipt (this file)
- [x] schema.sql — rooms/tiles/tile_versions (plato-cf) + bookings (i2i) +
      intents/reflexes (pincher) + field columns (exoj) — one database
- [x] worker v1 — merged i2i-ledger endpoints + tile endpoints, one deploy
- [x] MCP endpoint — Streamable HTTP `/mcp` (initialize, tools/list, tools/call)
- [x] reflex layer — intents table + pinch tool + compile-back
      (verified: paraphrase pinch → CONFIRM 0.892, zero LLM)
- [x] γ/η field on every call + conservation view
      (verified: field_budget 49/1585 after smoke)
- [x] per-agent tokens + deploy + smoke (11/11 green)
- [ ] docs page (Pages) + client skills for Claude Code / OpenCode / OpenClaw

*Clients done (`clients/README.md`); skill proposal filed (pending); Pages still open.*

## Operational lessons (banked 2026-09-29)

- **key.txt CF_API_TOKEN fails API verify (6111)** — CF deploys use wrangler's
  stored OAuth (`~/.wrangler/config/default.toml`). Don't set CLOUDFLARE_API_TOKEN.
- `[[ai]]` in wrangler.toml is an array-of-tables and wrangler rejects it — the
  AI binding is `[ai]` (object).
- **Vectorize metadata filters returned empty results even when unfiltered
  queries matched the same vectors** — pinch queries topK=10 unfiltered and
  filters by `kind` in JS. Revisit when the platform behaves.
- Empty-string metadata values get Vectorize upserts silently rejected — omit
  absent fields instead of sending `""`.

## Local reflex layer — lever-runner synergy (Casey 15:36)

[lever-runner](https://github.com/SuperInstance/lever-runner) is the same doctrine
one layer down: *teach once, run forever; the LLM never sees your shell*. Its
three gates (Rust 50µs template → Python 200µs cache → LLM intent-phrase only)
are the pincher thresholds made local.

The join: **fleet pinch ↔ local lever**, via `scripts/lever_bridge.py`:

- fleet `FIRE` → done, zero LLM anywhere
- fleet `ESCALATE` → local lever resolves → **compile back** so every agent inherits it
- `--pull-fleet` teaches fleet reflexes into your shell; `--push-local` shares local levers

Worker additions that make the sync possible: `GET /intents?limit=` (+ `intents_list` MCP tool).

## Connecting agents

`clients/README.md` — ready configs for Claude Code, OpenCode, OpenClaw
(streamable-http), plus curl/REST for everything else.

## Open questions for Casey

- **lever-runner**: no repo by that name found in the 600-repo catalog —
  point me at it (a local tool? a concept?) and it joins the synergy set.
- Name of the deployed worker: `superinstance-api.casey-digennaro.workers.dev`?
