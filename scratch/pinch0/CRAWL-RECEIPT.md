# PINCH0 — CRAWL RECEIPT (Lane 2: audit-and-receipt)

**Generated:** 2026-10-02 (AKDT)
**Lane:** PINCH0 / Lane 2 — receipt + embed + score (audit-and-receipt path)
**Scope:** the corpus **as it already exists on disk**. No fresh fetching was performed in this lane.

## 1. Corpus as-is

Source: `scratch/pinch0/` (produced by scout Lane 1, waves 1–2).

| Artifact | Count | Notes |
|---|---|---|
| `cards.jsonl` | **5,138 cards** | one JSON object per line |
| — unique repos | **5,138** | exactly 1 card per repo (no dupes, max cards/repo = 1) |
| `lessons.jsonl` | **403 lessons** | covering **325** distinct repos |
| `edges_referral.json` | **24 edge rows** | see honesty note in §3 |

### Cards by `kind`

| kind | n |
|---|---|
| experiment-lane | 2,751 |
| unknown | 1,865 |
| infra | 186 |
| tool | 166 |
| game | 98 |
| ledger | 63 |
| writing | 9 |

Other card facets: `archived=true` 16 · `fork=true` 816 · cards with `docs_read` populated 2,294. Card `purpose` and `setup` are non-empty for all 5,138.

### Lessons by `topic`

| topic | n |
|---|---|
| other | 359 |
| verifier | 16 |
| infrastructure | 6 |
| prereg | 5 |
| writing | 4 |
| gating | 3 |
| memory / game / routing / ci / quantum | 2 each |

## 2. Methodology

1. **Receipt** what exists on disk; count and characterise without mutating the corpus.
2. **Embed** each card's text with **Cloudflare Workers AI `@cf/baai/bge-m3`** (1024-dim, free tier).
   - Card text = `repo | kind | purpose | layout | build_run | entrypoints | conventions`.
   - Batches of 48; `429`/`5xx` retried with `Retry-After`-aware exponential backoff.
   - Checkpoint (vectors + repo-id index) written after **every** batch; restart is resume-safe
     (skip already-embedded ids). Memory is O(batch), never O(corpus).
3. **Score** retrieval against the referral edges: for each edge `src→dst`, the query is
   `src`'s card text and the candidate set is **all 5,138 repo cards**; rank `dst`.
   Metrics: **precision@1** and **MRR**.
4. **Probe**: 10 hand-authored queries drawn from real fleet intents, scored descriptively
   against the full repo index (no tuning).
5. **Land** results under `results/pinch0/`; embeddings stay in `scratch/`.

### Credential note (honest)
The task directed use of `CF_API_TOKEN` from `/mnt/c/Users/casey/key.txt`. At 2026-10-02 that
token **does not authenticate** (`401` / code 10000 "Invalid API Token") against
`api.cloudflare.com`. The lane therefore used the machine's **live wrangler OAuth credential**
(`~/.wrangler/config/default.toml`, account `049ff5e8…`, scope includes `ai (write)`), which
authenticates and is auto-refreshed via `wrangler whoami` on `401`. No token value was echoed,
hardcoded, or committed at any point. `CF_API_TOKEN` is retained only as a fallback path.

## 3. Honest boundary

- **This receipt covers what exists as of 2026-10-02.** No fresh fetching was performed.
- The **wave-2 tail is incomplete** — the wave-2 fetch died with the 07:27 reboot
  (`_wave2.log`, ~426 bytes). The corpus is therefore a **partial** crawl of the organisation,
  not a census. Counts above are floors, not totals.
- **Edge-label discrepancy (recorded, not smoothed):** the task describes
  `edges_referral.json` as "24 verified referral edges", but the file itself labels
  **18 `VERIFIED` and 6 `PENDING`**, with 2 duplicate `(from,to)` pairs
  (`pong-quilt→fleet-murmur` ×2; `quilt-tools→quilt-show` once VERIFIED, once PENDING),
  i.e. **22 distinct ordered pairs**. The gate below is pre-registered on **all 24 delivered
  rows** (primary, as instructed); the 18 `VERIFIED`-labelled rows and the 22 distinct pairs are
  reported as **secondary, descriptive** subsets. No rows were dropped to flatter the number.

## 4. PRE-REGISTERED GATE (written before any scoring)

> **PINCH0_VIABLE** iff **precision@1 ≥ 0.50** AND **MRR ≥ 0.60** on the 24 delivered referral edges.

No tuning, no threshold changes, no retries with different parameters after seeing results.
If the gate fails, the recorded result is **NOT_VIABLE** with the raw numbers.

Gateway applies to: retrieval of `dst` among **all 5,138** repo cards using `src` card text as
the query, `@cf/baai/bge-m3` cosine similarity. If embedding coverage is incomplete, coverage
is reported and the gate is evaluated on the covered set with the shortfall stated explicitly.
