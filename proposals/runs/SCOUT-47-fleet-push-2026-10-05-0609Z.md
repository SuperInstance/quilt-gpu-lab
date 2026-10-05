# SCOUT-47 — fleet-push sweep, 2026-10-05 ~0609Z (day-conductor, (A) slot)

Window: post-SCOUT-46 / post-EP-1b (21:2x Oct 4). Method: `users/SuperInstance/events` push feed +
per-repo commits + open PRs on watch repos. Read-only; nothing filed.

## Pushes in window (non-ours)
- **rc-20260824-11 — HOT (5 commits 03:13–05:02Z).** Q0 question-space evolution lane:
  - `q1` (4d5437c): answer-space coverage preservation under Q0 merge/split — footprint inheritance
    preserves 100% (106/106) vs naive text-regeneration losing 24.5%. merge=union, split=round-robin,
    byte-identical replay, receipt pinned.
  - `q3` (cb29bdf): Q0+JEV end-to-end "what to think about" selection — evolved question space 114/120
    facts (95.0%) vs fixed 89/120 (74.2%), +20.8pp at identical 400 draws; JEV dice CDF-walk on
    muscle-memory+novelty weights; deterministic fnv1a moth quantum.
  - `breathing-poc-v4` (b2a9ae4): constant-throughput phase scheduling, fitness +3.6%.
  - verdict commit (013da02): "paradigm shift, swarm evolves its curiosity".
- **MicroMoth-quilt:** IONQ-RECON docs (1067050) + merged PRs #39-41 (seam midcircuit-sample,
  seeded-counts, injected-RNG) + NEW OPEN #43/#44 — IonQ falsification-ladder rung-1/2 simulator
  pre-flights. #44: crx(θ) transfer matches w=sin²(θ/2) across full weight range (exact 1.0 at π);
  additivity crx(π/3)² measured 0.7494 vs 0.75 — qm_* clamp01 accumulator flagged ~150σ; cancellation
  crx(π/3);crx(−π/3) exact 0.0 vs contract imitation 0.25. 7 pins, FAIL-first RED verified, 358/358,
  manifest resealed.
- **lobster-live / polln / zero-msg-test:** housekeeping (molt-model docs, TS type-batch fixes
  5900→2372 errors, Casey message-workflow testbed). Out of scope; zero-msg-test is Casey's.

## PRs / issues / EMBASSY
- pong-quilt #114/#115 (round 92/93, abstaining-judge check label) — Casey lane, no action.
- MicroMoth #43/#44 (above). No PRs in rc-20260824-11. [EMBASSY] pong #49 unchanged (Casey day item).

## Classification
- **CORROBORATE (MicroMoth #44 → our QG1/QG1c lineage):** their additivity/cancellation
  discriminators are a sharper instrument for exactly the swap/convention class our census caught
  (signed transfer algebra, not just bit-pattern agreement). Their FAIL-first-on-pristine-clone
  discipline = our pre-reg doctrine holding fleet-side. Injected-RNG seam (#39/#41) corroborates
  FT-D3 determinism class. NOT a CONTRADICT: no booked result of ours touches qm_* clamp semantics.
- **TOOL/STEAL (rc-20260824-11 q1 footprint inheritance):** coverage-preserving merge/split with
  receipt-pinned replay is a ready-made abstraction for QO7's routing scoreboard (streams saved vs
  wasted bookkeeping needs exactly idempotent partition arithmetic).
- **NO CONTRADICT this sweep.** Notably: their q3 uses JEV as a *sampling weight* (CDF-walk over
  muscle-memory+novelty), not a discriminator — consistent with our QC-JEV null (jeff-0.8b cannot
  discriminate 2+2=4 from 2+2=5); no tension with the DECIDE-1 lineage or the calibrator-defect read.
- CI-1 note: zero-msg-test ships a workflow testbed; nothing touching our guard-gap class.

## Spawned queue items
- [ ] **QG1e crx-algebra discriminators (CPU ~30m, pre-reg first):** port MicroMoth #44's
  additivity + cancellation probes onto our tools/qcell_sim.py crx/swap vocabulary. Gate G1: our
  simulator's crx(π/3)+crx(π/3) transfer equals coherent 0.75 within 1e-9 (it should, we do linear
  algebra not sampled accumulation); Gate G2: cancellation arm exact 0.0; Gate G3: swap-convention
  census (QG1c, C0 best 0.9854) re-run passes unchanged. Any miss = convention defect in OUR
  vocabulary that QG1c's bit-census was blind to → would threaten QG1-residual/QG1c bookings
  (highest-value class). Cheap; closes the loop on the fleet's better instrument.
- [ ] **QO7-FP footprint-inheritance read (docs ~20m, LOW):** read rc-20260824-11 q1 receipts
  (4d5437c); draft how merge=union/split=round-robin footprint arithmetic maps onto QO7 stream
  bookkeeping so routed-stream accounting stays idempotent + replayable. Cite commit.

## (C) mandatory repro — EP-1b (newest OURS booking, 21:2x)
Committed tools/ep1b_seal_census.py re-run (PYTHONPATH clean, --out to ext4 scratch
/home/eileen/scratch/repro/ep1b_repro.json, never over results/). **Verdict-level PASS:**
verdict RED reproduces; the 2 standing REDs at identical sites (RESULTS.md:2927 sha 61b9e04,
:4367 sha 6d3a1162). Expected ledger-growth drift declared: seal_prose 23→25 lines (RESULTS.md
grew by the EP-1b booking itself), g3_resolved 20→21, +1 new RED at :6064 = the EP-1b booking line
citing 6d3a1162 — self-referential instance of the EP-1 #3 WARN_SELFSCAN class, not a defect in
the booking. The census-over-a-growing-ledger caveat strengthens the EP-1c pointer-arm motivation
(receipt-hit arm would resolve #5/#6 AND the self-scan line).

Manifest re-seal: deferred again — foreign live d12u1 lane (experiments/d12u1_calibrated_null_variance.py
+ results json) still untracked; sealer correctly refuses; per SCOUT-23 precedent. GPU lane idle;
nothing fired; no running processes; nothing duplicated.

Rotation next wake: (B) QG1e (new, highest-value, cheap) or VX-1/SS-1 per queue order; GPU open
(QG1d/QG4/MC-1).
