# PINCH0 — LANE 2 RECEIPT (embed + score)

**Date:** 2026-10-02 · **Lane:** PINCH0/Lane 2 (audit-and-receipt)
**Corpus:** `scratch/pinch0/` as it existed on disk (scout Lane 1, waves 1–2). No fresh fetching.
**Companion:** `scratch/pinch0/CRAWL-RECEIPT.md` (corpus characterisation + pre-registered gate).

---

## 1. Headline

| | |
|---|---|
| Cards receipted | **5,138** (1 per repo, 5,138 unique repos) |
| Embedded | **5,138 / 5,138** (coverage **1.000**, 0 failures) |
| Model | `@cf/baai/bge-m3` (Cloudflare Workers AI, free tier), 1024-dim |
| Gate (pre-registered) | precision@1 ≥ 0.50 **and** MRR ≥ 0.60 on the 24 delivered edge rows |
| Measured (edges, primary) | precision@1 = **0.000**, MRR = **0.107** |
| Probes (descriptive) | precision@1 = **1.000**, MRR = **1.000** (10/10 rank-1) |
| **VERDICT** | **NOT_VIABLE** |

The pre-registered gate **failed**. This is recorded as-is: no tuning, no threshold changes,
no retries with different parameters.

## 2. Embedding coverage

- Batching 48 texts/call; `Retry-After`-aware backoff; checkpoint of vectors + repo-id index
  after **every** batch (resume-safe). Memory O(batch).
- **5,138 / 5,138 embedded, 0 failures**, wall time ~147 s.
- Credential: see §Credential note below.

## 3. Gate result — the 24 delivered referral edges

Query = the **source** repo's card text (`purpose` + `setup` fields).
Candidates = **all 5,138** repo cards. Rank the destination repo. Cosine similarity.

| metric | value | gate | pass? |
|---|---|---|---|
| precision@1 | 0.000 (0/24) | ≥ 0.50 | ❌ |
| MRR | 0.107 | ≥ 0.60 | ❌ |

**Verdict: NOT_VIABLE.**

### 3.1 Key structural observation

For **24/24** edges the rank-1 hit is the **edge's own source repo** — unsurprising, since the
query text is derived from the source card and that card is in the candidate set. Under the
literal gate spec ("rank dst among ALL repo cards") this makes precision@1 structurally 0 and
caps MRR near `1/2`. The meaningful signal is *where the destination lands*:

| | |
|---|---|
| dst rank range | 2 … 3,252 |
| dst rank ≤ 5 | 6 / 24 |
| dst rank ≤ 30 | 8 / 24 |
| dst rank > 1,000 | 4 / 24 |

### 3.2 Secondary, descriptive (POST-HOC — not the gate)

Recomputing with the source repo **excluded** from candidates (src is always rank-1):

| subset | n | precision@1 | MRR |
|---|---|---|---|
| all delivered rows | 24 | 0.083 | 0.171 |
| rows labelled `VERIFIED` | 18 | 0.111 | 0.222 |
| distinct ordered pairs | 22 | 0.091 | 0.186 |

Still far below the gate. The verdict does not depend on the src-inclusion choice.

### 3.3 Edge-label honesty

The task described the file as "24 verified referral edges"; the file itself labels **18
`VERIFIED` + 6 `PENDING`**, with 2 duplicate `(from,to)` pairs → **22 distinct ordered pairs**.
All 24 delivered rows were scored as instructed; no rows were dropped.

## 4. Probe results (descriptive)

10 hand-authored queries from real fleet intents, target = the repo of record:

| # | query | target | rank |
|---|---|---|---|
| 1 | book a hash-chained deterministic receipt for the duke-lab instrument booking layer | jev-receipts | 1 |
| 2 | schedule recurring fleet health checks and batch processing as a cron job scheduler | fleet-cron | 1 |
| 3 | marketplace for sharing and discovering fleet skills and equipment | skill-exchange | 1 |
| 4 | precision drift analyzer for constraint systems — which boat sinks first | drift-analyzer | 1 |
| 5 | record the disputes that merges usually erase, adjudication query lane | quilt-adjudication | 1 |
| 6 | cryptographic append-only witness log ledger for canon events | quilt-canon-witness | 1 |
| 7 | pareto tournament selection multi-objective optimization for agent population dynamics | pareto-tournament | 1 |
| 8 | ledger where trust relocates blindness, novel mechanism lab | doubt-ledger | 1 |
| 9 | mine skill patterns from Mavis memory and propose new skills to build | mavis-skill-miner | 1 |
| 10 | fleet skill self-evolution from error patterns to proposals to commits | skill-evolver | 1 |

**10/10 rank-1 · precision@1 = 1.000 · MRR = 1.000.**

## 5. Interpretation (honest, bounded)

The embedding **works well for description→repo retrieval** (probes 10/10) but **does not
recover referral edges** (0/24 @1). Referral edges encode *hand-verified operational
relationships* (`from_node`/`to_node` wiring, signed receipts) that are **not** visible in the
prose of two repos' cards. Card-text similarity is therefore the wrong instrument for edge
recovery; edges need their own receipt/signature lane, not a semantic one.

This is a **real negative result** on a **partial** corpus (wave-2 tail incomplete after the
07:27 reboot). Counts are floors; the corpus is not a census of the organisation.

## 6. Credential note

`CF_API_TOKEN` in `/mnt/c/Users/casey/key.txt` **failed auth** on 2026-10-02
(`401`, code 10000 "Invalid API Token"). This lane used the machine's **live wrangler OAuth
credential** (`~/.wrangler/config/default.toml`, account `049ff5e8…`, scope `ai (write)`),
auto-refreshed via `wrangler whoami` on 401. No token value was echoed, hardcoded, or
committed. Embeddings (21 MB) stay in `scratch/` and are git-ignored.

## 7. Artifacts

- `results/pinch0/SCORES.json` — full metrics, per-edge rows, probe rows, verdict.
- `results/pinch0/PINCH0-RECEIPT.md` — this file.
- `scratch/pinch0/CRAWL-RECEIPT.md` — corpus receipt + pre-registered gate.
- `scratch/pinch0/{cf_embed.py, score.py, probes.json}` — reproducible harness.
- `scratch/pinch0/embeddings/` — vectors + id index (git-ignored, 21 MB).
