# The Self-Improvement Audit + the Breakthrough-Finder Design

*Casey (2026-09-28 15:28): "improve our self-improvement systems throughout our account on github… we want to make breakthroughs we have to make a system to find them."*

## Part 1 — What the fleet's self-improvement machinery actually is (the inventory)

| System | What it does | Proof it works | The gap |
|---|---|---|---|
| **The nursery speedrun loop** (autoclaw lineage) | agents mutate `train.py`, 5-min GPU increments, val_bpb gate, keep improvements | D1→D3 receipts: free-delta found, killed honestly, fixed, replicated (−0.029 bpb × 2 seeds) | never *proposes its own next mutation* — I dispatch D1, D2, D3 by judgment |
| **The SPOOL** (3 waves, 40+ pre-registered experiments) | the standing backlog with gates spelled out before scripts exist | every wave fed days of fires; nothing fired unregistered | ranking is manual; no automatic refresh from the outside edge |
| **The lane machine** (flash subagents + GPU serialization) | dispatch → build → FAIL-first → fire → book → push → report | ~30 lanes today; receipts landed all day | dispatch is me; no standing trigger when the queue thins |
| **The falsifier discipline** | pre-registered gates, FAIL-first checks, honest INCONCLUSIVE | the X-campaign: X1 LICENSE · X3/X6 KILL · X2/X9 — the elephant thesis dismantled cleanly | applied ad-hoc to our own claims, not systematically to *external* ideas |
| **Memory** (MEMORY.md, dailies, wiki) | continuity across sessions | survived compaction all day | doesn't feed the scouts — the wiki knows what we've tried; scouts never ask it |
| **The crons** (gpu-lab-tick, superinstance-watch, research lanes) | periodic ticks | runner fires QUEUE; watch scans the org | ticks execute but don't *discover* — no scout cadence, no gem routing |

**The one-line diagnosis:** every organ exists and works; the nervous system connecting them is me. The fleet can improve what it's given; it cannot yet *find what to improve*.

## Part 2 — The Breakthrough-Finder (the system that finds them)

A standing loop with five stations. Not a new lane — a circuit between the existing organs.

### Station 1 — MINE (the scouts, standing)
A recurring scout cadence (daily, cron-driven, rotating focus): papers/arXiv hot, GitHub trending, the RSI/self-improvement scene (WECO et al.), adjacent-field abstractions. Each run extracts **deeper abstractions** (not results) with citations, and writes them to a running `GEMS.md` ledger.

### Station 2 — CROSS-REFERENCE (the assayer)
For each abstraction: score it against the **asset inventory** (every receipt in RESULTS.md is an asset: the difference-operator transformer, the glyph-domain corpus, the falsifier method, chiaroscuro's renderer, the nursery, the cellular loop). Output: the **gem potential** — abstraction × asset → a falsifiable question only OUR hardware/positioning can answer cheaply. The scoring rubric: (novelty to the field) × (uniqueness of local advantage: free GPU iterations, private data, first-mover slots) × (falsifiability in ≤1 day).

### Station 3 — SEED (the SPOOL entry)
Each passing gem becomes a SPOOL entry with a pre-registered gate — same format as wave 1-3. Nothing fires unregistered; the falsifier discipline is non-negotiable.

### Station 4 — FIRE (the existing machine)
The lane machine + runner take it from there. No changes needed — this station already works.

### Station 5 — FEEDBACK (the part that makes it self-improving)
Every verdict feeds back two signals: (a) *which scout sources produced KEEPs* → the next scout's query weights tilt toward those sources; (b) *which abstraction families produced gems* → the assayer's priors update. The finder tunes itself on its own hit rate. That's RSI applied to discovery — the same verifier-gated loop the nursery runs on models, pointed at experiments.

## Part 3 — The build plan (wiring, in order)

1. **GEMS.md** — the ledger file in quilt-gpu-lab (format: date / abstraction / sources / asset-synergy / gem-question / status). First entries: the weco-rsi + edge-gems harvests (landing now).
2. **The assayer prompt** — a flash-lane spec that turns an abstraction list into scored SPOOL entries (reusable, versioned in docs/).
3. **The mine cron** — a daily `edge-mine` cron (isolated agentTurn, flash): run the scout spec, append to GEMS.md, dispatch the assayer on new entries. Replaces one-off scouts.
4. **The feedback hook** — when a gem-sourced experiment books a verdict, append its source-abstraction to a `gem-hits.md` counter-file the mine cron reads to re-weight queries.
5. **(Later) the mutation proposer** — the nursery's missing organ: a lane that reads the D-receipts + GEMS.md and proposes the next mutation with a gate. That's when the speedrun loop stops needing me.

*The loop's own metric: gems discovered → fired → booked per week, and the KEEP-rate of gem-sourced experiments vs baseline. If the finder can't outperform my judgment inside a month, that's a finding too.*
