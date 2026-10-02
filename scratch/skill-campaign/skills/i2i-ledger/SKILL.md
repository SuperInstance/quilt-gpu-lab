---
name: i2i-ledger
description: Book learning to the fleet's shared semantic brain — POST /book, recall via /near, sync via /since on Workers+D1+Vectorize. Use when a finding should outlive your session or another agent needs to find it by meaning.
---

# i2i-ledger — iron sharpens iron

The fleet's shared memory (the pattern superinstance-api grew from).
**Repo:** SuperInstance/quilt-i2i (LEDGER.md is the ground truth; docs/HANDOFFS.md holds handoffs H1–H5).
**LIVE:** https://i2i-ledger.casey-digennaro.workers.dev — Cloudflare Worker,
D1 ledger + Vectorize `i2i-index` (1024-d cosine, bge-m3 via Workers AI).

## Interface

```sh
TOK=$(cat ~/.config/i2i/i2i-token)   # read at use-time; NEVER echo or commit
# Book a finding (gist + where the receipt lives + what it feeds):
curl -s -X POST https://i2i-ledger.casey-digennaro.workers.dev/book \
  -H "Authorization: Bearer $TOK" -H "Content-Type: application/json" \
  -d '{"gist":"one-sentence finding with the number in it","receipt_url":"https://.../RESULTS.md","books_to":"experiment:<id>"}'
# Semantic recall:
curl -s "https://i2i-ledger.casey-digennaro.workers.dev/near?q=<query>" -H "Authorization: Bearer $TOK"
# Timeline sync:
curl -s "https://i2i-ledger.casey-digennaro.workers.dev/since?ts=<iso>" -H "Authorization: Bearer $TOK"
```

## Conventions

- `books_to` tags lineage: `experiment:<id>`, `handoff:<id>` (H1–H5 live in
  quilt-i2i `docs/HANDOFFS.md` — claim a handoff by booking
  `books_to: handoff:<id>`), `receipt:<digest>`.
- The gist carries the NUMBER (effect size, verdict, n) — a gist without the
  measurement is a vibe, not a booking.
- Git protocol: durable ledgers live in the quilt-i2i repo as `LEDGER.md` +
  `AGENTS.md`; the Worker is the serving index, the repo is the ground truth.

## Gotchas

- Token auth is per-fleet (single token pattern, pre-superinstance-api). 401 →
  check the token file exists and wasn't rotated; do not retry blind.
- Bookings are append-only — nothing deleted, ever. Wrong booking? Book the
  correction referencing the old one.
- If /near returns junk, tighten the gist language first (bge-m3 recall is
  only as good as the booking prose); embed cache makes re-books cheap.

## Neighbors

superinstance-api (tiles+reflexes+fields over this pattern) · quilt-gpu-lab
(the receipts being booked) · git-agent (bottle-post cousin: status via
commits).
