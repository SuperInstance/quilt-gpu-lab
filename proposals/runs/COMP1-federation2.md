# COMP1 — federation v2: blurred multi-regime, capacity-starved, item-level bootstrap

**Pre-registered 2026-10-01 15:21 AKDT, BEFORE any COMP1 build or run.**
Lane COMPOSITE-1, second decompositional-growth probe. Re-runs COMP0's
federation thesis where it can actually be judged, per the COMPOSITE-1 spec
booked at the end of COMP0's RESULTS entry (keeper fold 15:2x).

## What COMP0 could not test (and why)

- 66-item held-out board: integer granularity 1/66 = 0.0152; FED pinned
  0.8182 on all seeds → across-seed std==0 → INCONCLUSIVE by law.
- Router saturated (1.0/1.0, top1−top2 gap 0.49): the D13d correlation
  router never faced ambiguity, so "routing happens between cells" was
  untested, not supported.
- Semantic regime saturated for every arm → full-board margins compressed.
- LA's second choice reused the same featurization (same cells) — not the
  independent reach D1b's design requires.

## Amendment A1 (2026-10-01 15:29 AKDT — BEFORE any run/arm trained)

Pre-fire corpus validation on CPU (no GPU run, no arms trained, no board
outcome seen; corpus is deterministic so the checked artifact IS the run
corpus): the original grammar's regime-native evidence templates were too
disjoint — **router held-out top-1 = 0.9919, top1−top2 gap 0.171 →
saturated**, the exact COMP0 disease the band exists to catch. Amendment:
**evidence style-mixing** — evidence rendered by a shared 4-style renderer
(manifest / prose / passive / logbook), native style w.p. 0.5 else uniform
over styles that preserve the regime's label rule (counting restricted to
styles carrying the count param). Styles now cross regimes; claims keep
per-regime native templates; append-overlays O1–O4 unchanged at β=0.35.
Measured after amendment: **router held-out 0.7356** (train 0.7514),
top1−top2 gap **0.0412**, per-regime routing 0.61–0.89, n=590 held-out
(141/139/148/162 per kind), canon frac 0.4831 — all validity gates pass,
router in band. **Grammar frozen here.** One calibration step, fully
disclosed; gates untouched.

## Corpus (frozen — NEW generation, seed 2718, content-addressed, hash-split)

New foundry `experiments/comp1_federation2.py::gen_corpus`, seed 2718,
deterministic (mulberry-style LCG, no python `hash()`). Target **N=2400**
raw items, ~equal across **K=4 regimes**, ~50/50 canon/distortion per
regime, sha256-per-item content addressing, dedup on sha256, hash-split
(first nibble ≥ 0xC → held-out, same law as D5/COMP0).

Regimes (label rule frozen; distortion = near-miss, not trivial):

| kind | canon rule | distortion |
|---|---|---|
| `semantic` | claim entities (cargo+dock) == evidence entities (paraphrase) | cargo OR dock swapped within pool |
| `counting-address` | count word in claim == count in manifest evidence | adjacent count word (near-miss) |
| `negation-scope` | claim polarity == evidence polarity (assert/deny) | polarity flip (not/no vs assert) |
| `agent-role` | agent+theme in claim == agent+theme in passive evidence | agent swapped within pool |

**Blurred boundaries (the router stress):** shared vocabulary pools across
ALL regimes (docks, cargos, subjects, verbs, count words), PLUS per-item
overlay applied with probability **β=0.35** (seeded), chosen from:
O1 append to evidence an irrelevant count clause ("side note: {k} other
shipments were logged"); O2 append to claim an irrelevant count clause;
O3 prepend evidence style marker ("per the harbor log,"); O4 append to
evidence an irrelevant other-dock clause ("no discrepancies were reported
for {other_dock}"). Overlays NEVER change the label rule. Effect: count
words, manifest-ish style and second docks appear off-regime → centroid
correlation must separate genuinely overlapping surfaces.

**Corpus validity gates (computed, not assumed; else INCONCLUSIVE_CORPUS,
never PASS):**
- n_heldout ≥ 200 AND n_train ≥ 600 AND per-regime heldout ≥ 80.
- |canon fraction − 0.5| ≤ 0.06 on full board and per regime board.
- **Router band: held-out top-1 routing accuracy ∈ [0.40, 0.95]** (chance
  0.25). ≥0.95 → blur construction failed (saturated, COMP0's disease);
  <0.40 → corpus broken. Either → INCONCLUSIVE_CORPUS.
- Majority-class chance baselines COMPUTED per board (full + per regime),
  reported. Sanity readout: FED full board > chance.

## Featurization (frozen, TWO views)

- **Primary (word view):** lowercase word-count BoW, sha1-hashed to D=64,
  L2-normalized (COMP0 verbatim). claim + " " + evidence.
- **LA twin view (char view):** char-trigram count BoW (lowercase, spaces
  kept), sha1-hashed to D=64, L2-normalized. Different sensor, same items.

## Arms (matched doctrine; params stated, not hidden)

Cell = MLP 64→16→1 (1057p). Twin = MLP 64→8→1 (529p).

| arm | what | params |
|---|---|---|
| JOINT | 64→64→1 on ALL train, word view | 4225 |
| SINGLE | one cell 64→16→1 on ALL train, word view | 1057 |
| FED | K=4 cells, each on its regime slice only, word view; D13d centroid-correlation router (0 params) picks answering cell | 4×1057 = 4228 |
| FED+LA-v2 | FED + per-regime CHAR-view twin cells; on routed item, if routed cell margin \|p−.5\| < τ → twin of the SAME regime re-reads, wins iff its margin is larger | 4228+4×529 = 6344 |
| JOINT+LA-v2 (CONTROL, ungated) | JOINT + same twin bank + same τ rule (twin chosen by router) | 4225+2116 = 6341 |

Budget note stated now: JOINT vs FED matched within 3 params (0.07%).
SINGLE is cell-size by COMP0's frozen doctrine ("one dedicated cell tries
to be general"). **FED+LA-v2 carries a +50% capacity premium over FED —
this is the D1b purchase; the JOINT+LA-v2 control arm exists to price it:
if (FED+LA−FED) ≤ (JOINT+LA−JOINT) the LA win is capacity, not reach.**
Capacity-starvation: cells and joint are narrow (16/64 hidden) on a
4-regime blurred corpus — IE3's dilution regime, deliberately.

Router: parameter-free per-regime L2-centroid of TRAIN word-view features;
score = Pearson(item, centroid); order by score. τ = 20th percentile of
routed-cell margin on TRAIN items (no leakage).

## Training (frozen)

Adam lr 1e-3, BCE, batch 16, 300 epochs, fp32 CUDA (RTX 4050 beside the
resident 7B seat; tiny nets, <100 MB). INSTRUMENT-01 ramp receipt ≥0.6 s
sustained synced burn before readout. Seeds **2718, 2719, 2720** (hash-split
fixed by sha256; seeds vary init/batching only).

## Statistics (frozen — the measurement-first fix)

Per item i and arm A: correctness indicator per seed; **seed-mean accuracy
vector per item** a(i) = mean over seeds. Item-level **paired bootstrap**:
resample held-out items with replacement, B=2000, percentile 95% CI of
mean(a(i)−b(i)). Point estimate = mean over items of the seed-mean diff.

- CI_low > 0 AND diff > 0 → gate PASS on that comparison.
- **Degeneracy law retained:** across-seed std == 0.0 of any arm in a
  deciding pair → that gate INCONCLUSIVE, never PASS (std==0 on seed-mean
  still binds). Truncated seeds → INCONCLUSIVE (TRUNC-B).
- Bootstrap replaces granularity as the CI mechanism (items are the unit);
  BOTH reported (per-seed boards + across-seed std AND bootstrap CIs).

## Frozen gates (stated now)

Contested regimes declared BY CONSTRUCTION (BoW-weakest rules):
**`counting-address`** and **`negation-scope`**. (`semantic`/`agent-role`
expected closer to saturation; reported, not gated.)

- **G1 (primary, full board):** FED − SINGLE: diff > 0 AND bootstrap CI
  excludes 0.
- **G1R (primary, per-regime):** FED − SINGLE on BOTH contested regimes:
  each diff > 0 AND CI excludes 0.
- **G2 (primary):** FED+LA-v2 − FED: diff > 0 AND CI excludes 0 (full board).
- **G3 (secondary, dilution):** FED − JOINT: diff > 0 AND CI excludes 0
  (full board; per-regime reported).
- **G2C (control, reported):** (FED+LA−FED) − (JOINT+LA−JOINT) > 0 — the
  LA premium must buy more inside the federation.
- Router out of band, corpus validity fail, any deciding-arm std==0,
  truncation → INCONCLUSIVE-class, never PASS.

**Verdict lattice:** KEEP iff G1 ∧ G1R(both) ∧ G2 PASS. Exactly G1+G1R
without G2 → SPLIT_KEEP_G1. Other partials → SPLIT_KEEP_(names), honest.
KILL iff G1 CI_high < 0 (federation reliably worse than single). Else
INCONCLUSIVE.

## GPU protocol

guard.py Guard, task_id `COMP1-federation2`, receipt_dir
`results/comp1/guard`. Preflight: free VRAM < 1 GB → retry once after
60 s → refused twice = book NOT-RUN + VOID receipt, do not force. G7 watt
receipt REQUIRED — no receipt → run VOID. Guard timeout 2700 s.

## Artifacts & booking

`results/comp1/` — comp1_results.json (per-seed boards, per-regime boards,
bootstrap CIs, router audit incl. top1−top2 gap, LA trigger/flip counts,
τ, ramp receipt, guard summary), corpus.jsonl (content-addressed), guard
receipts. RESULTS.md entry + QUEUE.md line. **No commit** (lane does not
commit; keeper does).

## Re-fire addendum r2 (2026-10-01 15:51 AKDT)

r1 fired 15:31 and was killed ~15:45 — guard breach "free VRAM 1018 MiB <
1024" (resident 7B seat drifted 6 MiB over floor mid-run) → inner exit −15;
G7 receipt g7-wr-comp1-federation2-1790897485 self-declared VOID, evidence
preserved at `results/comp1/r1-void-1545/` (corpus.jsonl + guard/). No arm
results were produced. r2 re-fires the SAME frozen script, same seed, same
gates — zero spec changes. Determinism check passed pre-fire: regenerated
corpus sha256-sequence == r1 artifact (True); n_train=1810, n_heldout=590,
per-kind 141/139/148/162, canon 0.4831. Margins above remain frozen.
