# COMPOSITE-2 — federation v3: VIEW as the manipulated variable, difficulty-WIRED, three-strikes law

**Pre-registered 2026-10-01 17:2x AKDT, BEFORE any COMPOSITE-2 build or run.**
Lane COMPOSITE-2 (the SYNTH-0 top bet, MOVE 1). **AUTHORING ONLY** — this file is the
prereg; no corpus generated, no arm trained, no run fired, no commit (keeper commits;
COMP0/COMP1 law). Design inputs are BOOKED results; nothing here re-runs them.

## Lineage honored (booked, not re-derived)

- **COMP0** (INCONCLUSIVE, strike 1): 66-item granularity, FED pinned 0.8182 → std==0
  law caught the dead metric; router saturated 1.0/1.0.
- **COMP1** (INCONCLUSIVE full-board, strike 2): G1R-negation **PASS** — FED−SINGLE
  @negation-scope **+0.1261 CI[+0.0338,+0.2185]**; FED−JOINT +0.1306 CI[+0.0405,+0.2230];
  monoliths BELOW regime chance (JOINT 0.4234 / SINGLE 0.4279 vs 0.50). Federation
  rescues exactly where the BoW monolith is structurally blind (polarity = word order).
  Floor effect: all arms 0.5469–0.5621 on 0.5169 chance → mid-band difficulty is the C2
  prerequisite. COMP1 FED boards (cheap-bracket targets, `results/comp1/comp1_results.json`,
  sha256 5ed3c50becbb1653…): **full 0.5605 · semantic 0.5816 · counting-address 0.5731 ·
  negation-scope 0.5541 · agent-role 0.5370**. Frozen corpus artifact
  `results/comp1/corpus.jsonl` sha256 c195e558f49c98c8… (re-verified + full hash recorded
  at bracket time, W5).
- **CX-CHEAP-0/1** (MLP NOT retired): the 325p logistic two-arm matches 4228p FED on 4/5
  regimes but fails the frozen gate (negation Δ+0.054 over; regime-conditioned v2 recovers
  counting-flatness −0.0048 but DESTROYS the negation win → −0.0068). The 4228p MLP's one
  unmatchable property = **regime-symmetry AND the negation win simultaneously**.
  CX-CHEAP-1's regime-resolution finding: the frozen 0-param router is CHANCE within
  disagreement (0.5003) while TRUE-regime carries the win-signal (logistic 0.6173;
  win-rate|disagree negation 0.754 vs 0.400/0.500/0.510) — **routing must resolve the
  regime where the disagreement lives.** RING-CX-2: a 5-param trained linear readout on
  untrained margins reaches the blind regime (ratio 3.26, prec 0.805) — cheapness lives
  in the gate once it is trained.
- **SYNTH-0 bookings** (this prereg executes them): difficulty calibration promoted to a
  **WIRING GATE** (0.65–0.85 linear probe BEFORE arms; three strikes = federation thesis
  retired); the honest MLP-retirement re-test with a sensor-picking router; **per-item
  predictions persisted in every artifact** (CX-CHEAP-0 had to re-derive them); full-board
  aggregate structurally dead — secondary forever.

## Thesis under test (v3)

> Federation's value is blindness-repair: a bank of HETEROGENEOUS-SENSOR cells whose
> router picks the SENSOR — not just the expert — beats same-view federation and every
> monolith at matched parameters, on a corpus whose difficulty is WIRED to mid-band
> before any arm fires. Pre-declared blind regime: **negation-scope** (continuity with
> COMP1's only passing gate; S4 is the repair sensor).

## 1. Corpus (frozen spec; generated only at run time)

Foundry: extend `experiments/comp1_federation2.py::gen_corpus` (same LCG law — mulberry,
no python `hash()`; sha256 per-item content addressing; dedup on sha256; hash-split first
nibble ≥ 0xC → held-out, COMP1/D5 law). Grammar = COMP1's A1-amended grammar VERBATIM
(4-style renderer, style-mixing w.p. 0.5, claims keep native templates, overlays O1–O4).
**K=4 regimes = COMP1's exact four** (comparability law: the cheap bracket's per-regime
targets are COMP1's boards): `semantic`, `counting-address`, `negation-scope`,
`agent-role`, ~50/50 canon/distortion, blurred boundaries via shared pools + overlays.

**Sizing (power-driven; the ≥500 floor is trivially exceeded and rejected):** target
**N=24,600 raw** (6,150/regime; pools sized for ≥20× combinatorial headroom; post-dedup
floor N=23,000, deterministic LCG regeneration until met). Expected split ≈ 18,450 train /
6,150 held-out (≈1,537/regime held-out).

**Difficulty wiring — the F-GATE (pre-arm, blocking):** logistic linear probe (sklearn
lbfgs, C=1.0, seed 2718, 3 refits 2718/2719/2720) on the frozen S1 word64 view, TRAIN-fit:
- full-board held-out probe ∈ **[0.65, 0.85]** AND every per-regime probe ∈ **[0.60, 0.90]**
  AND refit std > 0 → GATE GREEN, corpus FROZEN (grammar-frozen law; any post-pass change
  = new amendment + full gate re-run, COMP1 A1 precedent).
- FAIL → **arms BLOCKED**, logged `WIRING_VIOLATION` (iteration #, knob values, probe
  boards) to `results/comp2/difficulty_calibration_log.json`. Calibration budget: **≤8
  iterations** over 4 declared knobs in priority order — k1 distortion near-miss distance,
  k2 overlay rate β (start 0.35), k3 vocab-overlap fraction, k4 style-mix probability.
  Three consecutive violations with budget exhausted = **wiring-exhaustion strike** (below).

**Corpus validity gates (computed, not assumed; else INCONCLUSIVE_CORPUS, never PASS):**
n_heldout ≥ 5,600 AND per-regime held-out ≥ 1,350 (power floor); |canon frac − 0.5| ≤ 0.06
full + per-regime; dedup exact-unique; determinism re-gen sha256-sequence identical (W1);
majority-chance COMPUTED per board; router bands (below); FED sanity readout full > chance.

## 2. Sensors (frozen featurizations — VIEW is the manipulated variable)

| id | sensor | definition (deterministic sha1 hashing, L2-normalized, D=64) |
|---|---|---|
| S1 | word BoW | COMP1 primary verbatim: lowercase word-count BoW → D=64 |
| S2 | char-trigram | COMP1 twin view verbatim: lowercase trigrams, spaces kept → D=64 |
| S3 | positional | ordered adjacent bigrams (w_i,w_{i+1}) ⊕ (token, position-bucket ∈ {0–2,3–5,6+}) → D=64 — sees word ORDER (passives, polarity-by-position) |
| S4 | negation-marker-aware | 4 explicit dims (neg-marker ∈ claim, ∈ evidence, XOR, count-word-present) ⊕ word BoW → D=60 → D=64 |

All four on claim + " " + evidence. S3/S4 are the structural-blindness repairs COMP1's
word-view lacked; S1/S2 are continuity controls.

## 3. Arms (matched doctrine; params stated, not hidden)

Cell = MLP 64→16→1 (**1057p**); joint = 64→64→1 (**4225p**); Adam lr 1e-3, BCE, batch 16,
fp32 CUDA. Item-update budgets COMP1-matched: all-train arms/cells 30 ep (543k updates =
COMP1's 300ep×1810); slice cells 30 ep on ~4,600 items (135k = COMP1's per-cell budget).

| arm | what | params |
|---|---|---|
| JOINT | 64→64→1, S1, all train (monolith control) | 4225 |
| SINGLE | one cell, S1, all train (best-single control, COMP0 doctrine) | 1057 |
| FED-WORD | 4 cells per-regime slice, ALL S1, 0-param centroid router (COMP1 arm verbatim — replication + in-corpus 4228p comparator) | 4×1057 = 4228 |
| **FED-HETERO (primary)** | 4 cells = one per SENSOR S1–S4, EACH on ALL train; learned sensor-picking router answers | 4228 + 36 router = 4264 (+0.85%, disclosed) |
| FED-HE-MATCHED | 4 per-regime slice cells with structurally-matched sensor (semantic→S2, counting→S1, negation→S4, agent→S3 — frozen assignment table, declared before calibration); same learned router | 4228 + 36 = 4264 |
| S4-MONO (control, ungated) | SINGLE-arch cell on S4 alone — "just buy the right sensor once" control | 1057 |
| FED+LA | re-read layer on the FED-HETERO bank, **zero premium**: routed-cell margin < τ (20th pct TRAIN, COMP1 law) → 2nd-choice SENSOR cell re-reads, wins iff larger margin | +0 |

Match: JOINT vs FED banks within 41 params (0.97%), stated not hidden. Factorial
decomposition: FED-HE-MATCHED − FED-WORD isolates SENSOR (same partition);
FED-HETERO − FED-HE-MATCHED isolates ROUTED-sensor-choice vs frozen structural matching.

**Learned sensor-picking router (CX-CHEAP-1 law — resolve the regime where disagreement
lives):** multinomial logistic (softmax, CPU, lbfgs, seed 2718), TRAIN-fit on regime
labels (free: corpus is synthetic and cells are regime-exclusive in 2 of 3 banks), 8
frozen deployable features = 4 per-sensor centroid-Pearson scores (0-param geometry,
COMP1) ⊕ 4 per-sensor cheap-logistic margins (TRAIN-fit); output = answering sensor.
No test leakage (features and router TRAIN-only; margins from TRAIN-fit cells).
Router validity (else INCONCLUSIVE_CORPUS): learned router held-out top-1 ∈ **[0.40,
0.95]** (chance 0.25) AND centroid-score top-1 alone ∈ [0.40, 0.95]. Reported (not
gating): within-disagreement routing accuracy, target ≥ 0.60 — CX-CHEAP-1's gap was
0.5003 there.

## 4. Cheap-arm bracket (the honest MLP-retirement test, dual-corpus)

325p-class two-arm, CPU, 0 GPU-Wh: SINGLE-cheap = logistic on S1 (65p); FED-cheap-hetero
= 4 logistic cells (one per sensor S1–S4, 4×65=260p) + the SAME learned router (36p) →
**361p total** (325p-class, +11% vs CX-CHEAP-0's 325p — the router is the purchase).

- **G4a (primary, literal booked endpoint — frozen COMP1 corpus):** run on
  `results/comp1/corpus.jsonl` (sha recorded, W5), 1810/590 split, COMP1 featurization.
  Per-regime |Δ| ≤ 0.02 vs COMP1 booked FED boards (0.5816 / 0.5731 / 0.5541 / 0.5370;
  full 0.5605 reported) **AND** negation FED-cheap − SINGLE-cheap ≥ **+0.126** with CI
  excluding 0. (CX-CHEAP-0 failed exactly this at max|Δ| 0.054; the hypothesis is the
  sensor-picking router supplies regime-flatness without destroying the win.)
- **G4b (co-primary, transfer — C2 corpus):** same two endpoints in-corpus vs C2's own
  4228p FED-WORD seed-mean boards. A retirement claim must hold on both corpora.
- **Verdict:** MLP **RETIRED** iff G4a ∧ G4b. G4a-only → `RETIRED-OLD-CORPUS-ONLY`
  (honest partial; retirement deferred). Else **NOT-RETIRED**.

## 5. Statistics (frozen — COMP1 law + power receipts)

Per item i, arm A: correctness per seed → seed-mean vector a(i). Item-level **paired
bootstrap** over held-out items, B=2000, percentile 95% CI, numpy PCG64 seed 2718 per
gate; point estimate = mean over items of the seed-mean diff. Per-seed boards +
across-seed std reported alongside (both mechanisms, always).

**Power analysis (the sizing receipt):** from COMP1's booked per-regime FED−SINGLE CIs
back out per-regime diff sd ≈ 0.50–0.61 (negation 0.573, counting 0.606, semantic 0.501);
use sd̂=0.60. Required per-regime held-out n = (1.96·sd̂/h)²: h=±0.03 → **1,537**;
h=±0.05 → 554. Achieved half-width by N: 2,400 (COMP1) → ±0.096 (measured 0.092 ✓ model
calibrates) · 9,600 → ±0.048 · 16,800 → ±0.036 · **24,600 → ±0.030 ✓ target**. Mid-band
difficulty raises arm agreement → sd̂ likely smaller → margin. Detectable effects at
n≈1,537: CI-excl-0 for |diff| ≳ 0.03; the P1 bar (+0.08) is 2.7× and the replication bar
(+0.126) 4.2× the half-width. W2 cross-check: |percentile − normal-approx| half-width
≤ 0.005 per primary CI.

**Degeneracy law retained:** across-seed std == 0.0 of any arm in a deciding pair → that
gate INCONCLUSIVE, never PASS. Truncated seeds → INCONCLUSIVE (TRUNC-B).

## 6. Frozen gates (stated now — per-regime primary, full-board SECONDARY forever)

- **P1 (primary, blind regime):** FED-HETERO − SINGLE @negation-scope **≥ +0.08** AND
  CI_low > 0 (SYNTH-0's booked bar) AND both-arm std > 0.
- **P2 (primary, sensor-not-just-expert):** FED-HE-MATCHED − FED-WORD @negation-scope
  > 0 AND CI_low > 0.
- **P3 (primary, LA at zero premium):** FED+LA − FED-HETERO @negation-scope > 0 AND
  CI_low > 0. Secondary: full board + trigger/flip counts per seed.
- **P4 (primary, retirement):** the dual-corpus bracket above.
- **Secondary (reported, NEVER verdict-turning — the booked kill):** ALL full-board
  aggregates (FED-HETERO−SINGLE, FED-HETERO−JOINT, FED+LA−FED-HETERO); G2b
  FED-HETERO−FED-HE-MATCHED; agent-role and remaining per-regime tables; S4-MONO readout.

**Verdict lattice:** federation thesis **KEEP** iff P1 ∧ P2 PASS. P3 PASS → LA doctrine
refined-and-kept (independent reach = a different SENSOR to escape to); P3 FAIL → LA
closed to a D1b footnote regardless of KEEP (booked). Partials → `SPLIT_KEEP_(names)`,
honest. P4 has its own lattice (§4). Wiring/validity/std==0/truncation →
INCONCLUSIVE-class, never PASS.

**Borderline rule (P1):** CI_high ≥ +0.08 but CI_low ≤ 0 → `INCONCLUSIVE_BORDERLINE`;
one pre-declared re-analysis at B=10,000 (nothing else changes). Still spanning → book
INCONCLUSIVE-at-max-power; strike ledger holds at 2 (suspension, not retirement).

## 7. Three-strikes rule (restated from SYNTH-0 booking)

Ledger: **strike 1 = COMP0** (66-item granularity, std==0, metric dead) · **strike 2 =
COMP1** (floor effect, full-board dead, only negation passed). **Strike 3 = this run,
via either path:** (i) **substantive** — wiring green, arms fired, and P1 CI_high <
+0.08 (federation reliably cannot deliver blindness-repair at the sensor-routing level
on a properly-wired mid-band board); or (ii) **wiring exhaustion** — 3 consecutive
WIRING_VIOLATIONs burn the ≤8-iteration calibration budget without a mid-band corpus
(thesis untestable at measurable difficulty). **Consequence: federation thesis RETIRED
from the queue; look-again demoted to a D1b footnote; booked in RESULTS.md + ROADMAP;
no COMP3.** NOT strikes (measurement-scoped, re-fire allowed per COMP1 r2 law, zero spec
changes): post-green-gate std==0 INCONCLUSIVE, TRUNC-B, guard VOID/refused.

## 8. Budget — Wh envelope + GPU/CPU split

- **GPU (only the 6 MLP banks × 3 seeds ≈ 13M item-updates ≈ COMP1×1.3):** est 1,000–1,400 s
  wall, est ~16 Wh, **envelope ≤ 20 Wh**, guard timeout 3,600 s. guard.py Guard, task_id
  `COMPOSITE-2-federation3`, receipt_dir `results/comp2/guard`; preflight free VRAM < 1 GiB
  → retry once 60 s → refused twice = NOT-RUN + VOID receipt, do not force (COMP1 r1/r2
  law). **G7 watt receipt REQUIRED — no receipt → run VOID.** INSTRUMENT-01 ramp receipt
  ≥0.6 s sustained synced burn before readout. Slice-cell banks CPU-trainable as disclosed
  fallback if guard refuses (CX thread: CPU logistics win); all-train banks stay GPU for
  recipe comparability.
- **CPU (0 GPU-Wh):** corpus gen ~2 min; F-gate calibration ≤8 × ~5 s; router fits ~s;
  cheap bracket on BOTH corpora ~2 min; bootstraps (B=2000 × 4 primary gates × boards)
  minutes in numpy.
- **Storage:** ~100–150 MB prediction jsonl (gzip-9) on /home ext4 — **never /mnt/c**.

## 9. Artifacts & the persistence mandate (CX-CHEAP-0 lesson, W4)

`results/comp2/` — comp2_results.json (per-seed + seed-mean boards full/per-regime, all
bootstrap CIs + W2 cross-checks, router audit incl. within-disagreement, LA triggers/
flips, τ, ramp receipt, guard summary, power receipt), corpus.jsonl (content-addressed),
difficulty_calibration_log.json (EVERY F-gate iteration), predictions/*.jsonl —
**every arm scored on any corpus persists per item: {sha256, regime, label, split, p,
correct, margin, routed_sensor/cell, la_trigger, la_flip} (arm × seed × item). An arm
without per-item predictions is UNBOOKABLE.** cheap/ (bracket results + per-item
predictions, both corpora + COMP1-artifact sha provenance W5). guard/ receipts.
RESULTS.md entry + QUEUE.md line by the runner. **Lane does not commit.**

## 10. Risks (declared now)

1. **Mid-band unreachable** with frozen grammar + 4 knobs (probe jumps 0.55→0.9x) →
   budget burn → wiring-exhaustion strike. Mitigation: 4 orthogonal, monotone knobs; A1
   precedent shows sensitivity.
2. **Router re-saturation** as difficulty eases (>0.95) → INCONCLUSIVE_CORPUS. Mitigation:
   router band checked in the SAME calibration loop (k2/k3 blur knobs independent of k1
   difficulty).
3. **Cross-corpus comparability** (G4a): COMP1 numbers are from a floored corpus;
   mitigation is the design itself — G4a runs on the FROZEN COMP1 corpus, G4b transfers.
4. **S4-MONO trivially suffices** (right sensor beats federation): control isolates it;
   booked interpretation rule — if S4-MONO ≥ FED-HETERO − 0.02 on ≥3/4 regimes, P1/P2
   wins re-read as "buy the right sensor once", thesis narrowed honestly, not KEEP.
5. **24k gen collisions/determinism:** pool headroom ≥20×, LCG regen law, W1 sha check.
6. **Param drift (+36p router):** disclosed 0.85%; router-free FED-WORD carries the
   replication; FED-HE-MATCHED shares the router so P2 is matched exactly.
7. **Guard VRAM drift (7B seat, COMP1 r1):** preflight retry law + slice-cell CPU
   fallback + VOID-evidence preservation.
