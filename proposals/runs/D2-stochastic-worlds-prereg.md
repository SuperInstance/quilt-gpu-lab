# D2-STOCHASTIC — The Cog Thesis under stochastic worlds (pre-registration)

Pre-registered 2026-10-01 ~14:3x AKDT by lane D2-DESIGN (GLM-5.3 flagship, serial).
Written BEFORE any script, any run, any number. Frozen on commit of this file.
`owner: farm` (PREREG-CLAIM-PROTOCOL rule 2: GPU/lane work; main session must not
self-fire; wheel lanes check owner before implementing). Lanes never commit —
Lucineer books.

- **Repo pin:** `SuperInstance/quilt-dba` @ `5bbd99c99ab885fd8009655ddfbd5a3a58742364`
  (2026-10-01 12:07 -0800). `node experiments/smoke.mjs` must print 13/13 before any
  arm fires; a failing smoke = OPEN wiring defect, not a data point.
- **Companion formal side:** `SuperInstance/exoj` (Field/observer formalism). v1
  measures; v2 interprets. exoj contributes no numbers in v1 — recorded so nobody
  later mistakes v1 for the full two-repo thesis test.
- **House laws:** seed root **2718**; fail loud; verdicts KEEP / KILL / INCONCLUSIVE
  only; std==0 → INCONCLUSIVE, never PASS; CPU-reported-as-GPU = fabrication; G7
  watt-receipt@1 per GPU run — **no receipt = VOID** (adoption law, 2026-10-01);
  GPU timing claims need INSTRUMENT-01 ramp receipts (≥0.3 s sustained pre-load).
- **Seat law (XP-C KILL, 64b9269):** byte-identity at fixed seed is a serving-window
  property, not a model property. **v1 uses NO LLM seat** — the `ai`/teacher-consult
  sockets are out of twin scope precisely so D2 never queues for the seat. Any later
  seat arm inherits one-at-a-time serialization without renegotiation.

## 0. The claim, falsifiable

E-D1's own receipted caveat: arms are deterministic, so cross-seed variance is
vacuous by construction — its seeds 101/118/135 produce **identical state hashes**
(`8c8a54a43f10`, `var_A: var_D: 0` in `e_d1_summary.json`). D2 makes the variance
real and then tests the Cog Thesis on top of it.

**Primary claim (H-TRANSFER).** Under *stochastic* worlds, for the cell sockets in
scope, the transfer gap — normalized error of a sim-trained twin minus its
real-trained twin, both evaluated on held-out real traces — is a **decreasing
function of I/O determinacy** (`determinacy(c) = 1 − H(out | fixed in)/log|O|`,
COG-THESIS §3). Concretely: Spearman ρ(determinacy, gap) over sockets is
significantly negative, AND the high-determinacy sockets transfer near-perfectly.

**What each outcome would mean (frozen before measurement):**

- ρ strongly negative + near-1 sockets transfer: I/O structure governs synthetic
  trainability — the fleet gets a principled criterion for which cells can be
  trained on sim. KEEP (thesis supported, this scope).
- ρ ≈ 0 or positive **over a determinacy range ≥ 0.5 wide, with the mismatch
  control passing**: something other than I/O structure governs transfer. KILL
  (thesis wrong, this scope) — the candidate list (simulator fidelity, data volume,
  temporal context outside static I/O) is then the follow-up queue.
- Gap low everywhere: task too easy or holdout leaking. Verify holdout; if clean →
  INCONCLUSIVE.
- Gap high everywhere **including determinacy ≥ 0.8 sockets**: the *determinacy
  measure* is wrong (static I/O misses temporal dependence), not necessarily the
  thesis. Book as its own KEEP-grade finding; thesis formally INCONCLUSIVE.
- Mismatch control fails to widen: INCONCLUSIVE, thesis untested (most likely
  outcome if sim and real distributions were too close).

**Secondary claim (H-GROWTH, the E-D1 continuation).** The JEV gate's R2 result
(gated curriculum grows, unguided never does) survives stochastic worlds: gated
arm grows in ≥ 80% of stochastic worlds, unguided in ≤ 20%. A collapse is not a
disappointment, it is the finding — R2 was seed-vacuous and stochasticity kills it.

## 1. Arms

All world simulation on **CPU (node)**, all twin training/eval on **GPU (4050,
device string recorded per receipt)**. World seeds derive from the root:
`world_seed(i) = splitmix32(2718, i)`, i = 0..N−1, derivation committed before
fire. E-D1 replication seeds 101/118/135 are kept verbatim for the control arm.

| arm | worlds | world dynamics | purpose |
|---|---|---|---|
| **W-DET** | 3 (seeds 101/118/135) | unmodified quilt-dba @ pinned commit | wiring check: must reproduce E-D1's hash `8c8a54a43f10` and var=0. Any deviation = wiring bug, run is VOID, no verdict booked |
| **W-STO** | **200 in v1**, growth to 1000 gated (§4) | stochastic patch: env.rng-driven reward-drift timing, respawn delay drawn per event, probabilistic curriculum switching, ±sensor noise; agent logic untouched (patch lives outside cell reach, driver-side like the growth handshake) | the real variance + the operational trace source |
| **W-MIS** | sim-side only (no new worlds) | the *simulator* for twin training deliberately mismatched (input distribution shifted: wrong salience range, wrong task mix) | null control: must WIDEN the gap or nothing was tested |

Stochasticity injection points (receipted from source read): `core.mjs` world tick
(`respawnQ` timing — currently `RESPAWN_DELAY` constant), curriculum switch
probabilities, sensor salience perturbation. The patch must advance `env.rng` in
the world tick only; agent cells keep reading rng-free inputs (their determinacy
is the measured quantity — do not let the patch leak rng into cell internals).

**Sockets in v1 scope (6, chosen for predicted determinacy spread — the prediction
is itself pre-registered):**

| socket | predicted determinacy | why |
|---|---|---|
| `reflex.orient` output | ~0.9 | threshold rule on one scalar: near-total constraint |
| `world.surprise` (integer L1) | ~0.8 | computable from consecutive observations |
| `sensors.vision` (wrapped reading) | ~0.6 | push-based wrapper, bounded alphabet |
| `policy.action` (greedy+curiosity) | ~0.5 | argmax over estimates + occasional exploration |
| `memory.semantic` (decayed estimate) | ~0.3 | history-dependent, wide value space |
| `memory.episodic` (visit ring content) | ~0.1 | carries arbitrary world history — near-free |

The nine `engine/cells/` substrate cells (ai, api, formula, io, listener, program,
router, sensor, value) get a **static contract-extraction pass** in v1 (code vs
header disagreement = datum, per COG-THESIS §4.1) but no twins — v2 if v1 lands.
`ai`-socket twins are v2+ and seat-serialized.

**Trace protocol:** per world, harvest evals 0–999 (growth completes by ~299),
sampled at a seeded stride to 2,048 ticks per socket per world (subsample rng =
splitmix32(2718, world_i)). Split by **world**, not tick: 70% train worlds / 30%
test worlds, disjointness asserted at load (fail loud on overlap — COG-THESIS §6:
a gap against seen data is zero by construction). Twins: identical architecture
(tiny MLP, ≤ 2 hidden layers, ≤ 1 M params — the 6 GB wall gets respect),
identical optimizer/budget/steps, training seeds 2718/2719/2720, per condition
{real, sim, sim-mismatched}. Errors normalized per socket (MSE/variance for
regression, 1−accuracy for discrete) so gaps are comparable.

## 2. Frozen gates (numbers before scripts)

Primary metric: `gap(c) = nerr_sim(c) − nerr_real(c)` on the held-out real test
worlds; ρ = Spearman over the 6 in-scope sockets using operational-distribution
determinacy.

| gate | rule | maps to |
|---|---|---|
| **H1 CORRELATION** | ρ ≤ −0.60 AND bootstrap-over-worlds 95% CI upper bound < 0 | necessary for KEEP |
| **H2 NEAR-1 TRANSFER** | sockets with determinacy ≥ 0.80: mean gap ≤ 0.05 | necessary for KEEP |
| **H3 CONTROL WIDENS** | mean gap(sim-mis) ≥ mean gap(sim) + 0.05 | fails ⇒ INCONCLUSIVE regardless of H1/H2 |
| **H4 VARIANCE REAL** | std over W-STO worlds of BOTH {position@1000, growthAt-or-null} > 0; std==0 ⇒ INCONCLUSIVE + suspected unwired seeding (§5 F3) | law, not preference |
| **H5 DETERMINACY STABLE** | per-socket spread across the 3 input distributions (uniform / operational / degenerate) ≤ 0.15; offenders excluded and counted; > 1/3 of sockets unstable ⇒ the measure does not exist ⇒ INCONCLUSIVE (report, never average away) | COG-THESIS §4.2 |
| **H6 RANGE** | max−min determinacy across in-scope sockets ≥ 0.5 | fails ⇒ INCONCLUSIVE (flat-over-narrow is uninformative) |
| **H-GROWTH** | gated arm grown (growthAt ≤ 1000) in ≥ 80% of W-STO worlds AND unguided in ≤ 20% | both hold ⇒ R2 survives (KEEP-grade); gated < 50% ⇒ R2 does not survive stochastic worlds (separate booking, does not veto the thesis measurement) |
| **GPU-SEED LAW** | per-socket training-seed std == 0 ⇒ that socket INCONCLUSIVE (seeds not wired — fail loud, fix, rerun; never book) | house law |

**Verdict assembly (mechanical):** KEEP iff H1 ∧ H2 ∧ H3 ∧ H4 ∧ H5 ∧ H6. KILL iff
H3 ∧ H4 ∧ H5 ∧ H6 hold but ρ ≥ 0 (flat-or-wrong over a real range with a working
control). Everything else INCONCLUSIVE with the failing gates named. H-GROWTH
books independently of the thesis verdict.

## 3. CPU-seeded vs GPU-eval split

- **CPU (deterministic, byte-reproducible):** world generation, trace harvest,
  determinacy entropies (numpy, Miller–Madow small-|O| correction), world splits,
  all receipts/chains (quilt-dba `canonDeep` + fnv1a64, sealChain per run). Every
  world batch ships a chain tip; replay from tip must be byte-identical (E-D1 R5
  discipline).
- **GPU (receipted, not bit-deterministic by claim):** twin training + eval only.
  XP-C taught that byte-identity is a serving-window property — D2 **claims no GPU
  bit-determinism**; it measures seed *variance* instead (GPU-SEED LAW above).
  Timing/speedup claims (if any) require INSTRUMENT-01 ramp receipts (0.6 s
  pre-load, bench standard); accuracy claims do not.
- **Energy:** every GPU run under `guard.py`, one g7-watt-receipt@1 sealed, no
  receipt = VOID. Live calibration exists: tiny-net-class load ≈ 65–70 W mean.

## 4. Right-sizing, growth receipts, budget

The worklist says 1000 worlds. Honest arithmetic: E-D1 wall receipts show
0.2–0.3 s per 5000-eval world — world-gen is nearly free; **the budget is trace
I/O and twins**, and the 4050 is a 6 GB card sharing a box with live lanes.

- **v1 = 200 stochastic worlds** (140 train / 60 test), 6 sockets, 2,048
  ticks/socket/world → ≤ 60 M values/socket-side, tiny by tensor standards but the
  honest first scale. 6 sockets × 3 conditions × 3 seeds = 54 twin trainings,
  ≤ 60 s each on 4050 (tiny nets, no seat contention — tiny-net lanes run beside
  build lanes freely per ROADMAP doctrine 2).
- **Growth to 1000 worlds is itself JEV-gated:** fire the ×5 extension ONLY if v1
  passes H4 AND the bootstrap CI on ρ is wider than 0.40 (underpowered) — the
  extension exists to halve that CI, and its growth receipt states that in one
  line. Extensions without a receipt purpose = VOID.
- **Wall-clock (planning numbers, not receipts):** v1 evening ≈ 3–4 h — world-gen
  ~10 min (parallel), trace harvest ~30 min, determinacy pass ~20 min, twins
  ~1 h GPU, analysis + booking ~1 h. 1000-world extension: +1–2 h harvest, twins
  ×2 data ≈ 1.5 h GPU.
- **Energy (planning):** ~1.5–2.5 h at ~65–70 W GPU ⇒ **~100–175 Wh GPU-side,
  book ≤ 250 Wh with system overhead**; ~$0.02–0.06 at $0.23/kWh. Real numbers via
  G7 receipts; estimates never booked as measurements.

## 5. Failure modes and detections

| # | failure | detection (fail loud) |
|---|---|---|
| F1 | co-tenancy on the GPU skews or OOMs twins | guard.py records device + concurrent CUDA PIDs per run; OOM → checkpoint per socket, rerun; accuracy is co-tenant-safe but OOM is not |
| F2 | seat flakiness contaminates a run | v1 has no seat by design; any v2 seat arm serializes (XP-C law) and probes the seat process before/after |
| F3 | degenerate world seeding (env.rng never advanced → all worlds identical — the exact E-D1 vacuity) | pairwise state-hash uniqueness at eval 100: < 90% unique ⇒ INCONCLUSIVE + wiring bug; W-DET hash equality check is the complementary canary |
| F4 | determinacy estimator bias at small output alphabets (log\|O\| → 0) | per-socket \|O\| reported; log2\|O\| < 1 flagged; Miller–Madow correction; still unstable ⇒ excluded per H5 |
| F5 | train/test leakage across worlds | world-id disjointness assert at data load; violation aborts before training |
| F6 | mismatched simulator accidentally matched (H3 cannot widen) | pre-gate: KS test sim-vs-real input distributions must reject equality (p ≤ 0.05) BEFORE the control is bookable; a non-mismatched mismatch = fix and rerun, never post-hoc reinterpretation |
| F7 | growth collapse starves the operational distribution (traces from a degenerate agent) | H-GROWTH receipts per world; thesis ρ computed on grown worlds only if ≥ 60 grown train worlds exist, else INCONCLUSIVE |
| F8 | patch leaks stochasticity into agent cells (measuring noise, not determinacy) | W-DET hash reproduction + a stochastic-world A/B on the reflex socket: its determinacy may NOT drop below its W-DET value minus 0.05; violation ⇒ patch bug |
| F9 | WSL GPU device-not-ready / 6 GB wall (G9's death) | params ≤ 1 M, batch ≤ 4096, activation-budget assert in the twin script; OOM paths checkpoint |
| F10 | quilt-dba upstream moves under us | commit pin §0 + smoke 13/13 gate; drift ⇒ re-pin explicitly in a new prereg revision, never silently |

## 6. Smallest first build (one evening, the wiring receipt — NOT the thesis verdict)

1. Stochastic patch behind `--stochastic` (driver-side only), smoke 13/13 still green.
2. W-DET check: 3 seeds reproduce `8c8a54a43f10`, var=0. Fail loud.
3. Mini batch: 16 W-STO worlds (12 train / 4 test). F3 uniqueness check; H4 std > 0.
4. Two sockets only — `reflex.orient` (predicted ~0.9) and `memory.episodic`
   (predicted ~0.1), the extremes: determinacy pass (3 distributions), twins ×
   3 conditions × 3 seeds = 18 trainings ≤ 20 min GPU under guard.py, G7 receipt
   sealed. F6 KS pre-gate on the mismatch arm.
5. Book the mini: gates H4 + F-gates only. Mini passes ⇒ v1 (200 worlds, all 6
   sockets) is armed for the next wave per QUEUE. Mini fails ⇒ the failure mode is
   the booking; no thesis language.

## 7. OPEN items (honest)

- exoj integration is v2: v1 cannot claim the two-repo thesis, only the
  quilt-dba-side measurement.
- Nine substrate cells: contract-extraction only in v1 (code-vs-header
  disagreements booked as data); twins v2.
- The 0.05 / 0.15 / 0.60 / 0.80 thresholds are frozen judgment calls at n=6
  sockets — underpowered by construction, which is why the bootstrap CI and the
  growth path to 1000 worlds exist. If v1 lands KEEP at CI width < 0.20, the
  extension does not fire (receipt says so).

— lane D2-DESIGN, 2026-10-01. Do not fire without a committed prereg
(farm_queue_flip refuses otherwise — keep that gate).
