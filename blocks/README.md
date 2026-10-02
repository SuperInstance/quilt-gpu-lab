# blocks/ — the composition map

Harvested, self-tested, CPU-only pieces of proven machinery from booked
experiments. A block earns its directory by three things: a `block.py` that
runs STANDALONE (no repo-internal imports), a `BLOCK.md` (what it is / exact
interface / the booked receipt it came from / how it composes / self-test),
and a self-test that finishes in seconds on CPU and prints exactly one JSON
verdict line as its final stdout line. Provenance lives in
[RESULTS.md](../RESULTS.md) (one line per block below says which entry);
nothing here is stronger than its receipt.

## The blocks (one line each)

| block | what it is | booked from | interface (in → out) |
|---|---|---|---|
| **port_harness** | dual-implementation equivalence harness: proves a PORT of a numeric engine agrees with its REFERENCE before anything downstream trusts it; law = per-side paired rows, never mixed-side | B1-DISTILL (2026-10-01, RESULTS.md L4452–4479): JS↔torch port ≤ 7.2e-07 | `PairedCaseSpec` → `generate_paired_cases` → two runners (numpy ref / JS port child) → `compare` → `ComparatorReport` → `FrozenToleranceGate(1e-6).adjudicate` → PASS/KILL |
| **envelope_guard** | strict validation core for the pure `z_in -> z_out` cell envelope: refuses malformed anything (dup keys, NaN, trailing content) and binds the envelope to its dispatch (digest/cell_id/provider/seed) — a receipt, not decoration | XP-C (2026-10-01, RESULTS.md L4221–4348): 20/20 malformed refused, 3 provider arms | `Dispatch` + raw provider text → `Guard.validate_output` → envelope dict or structured `Refusal(code,...)`; `validate_input(Cell)`; FNV-1a-64 digests |
| **format_first_gate** | judge-answer gating: one batched call, N named questions; strict parse BEFORE any trust (format-first), retry-once, pinch-to-fallback honestly booked, flow-state receipt with token ledger | CM1 r3/r4/r5 (2026-09-29/30, RESULTS.md): rule-rich batch 12/12 DRAFT_PASS, 25x wall / 4.5x token cut | frozen `questions` + injected `JudgeClient` + `state` → `GateReceipt` (answers/flow/counts/tokens/wall) or `GateError`; `mean_agreement(gold, answers)` |
| **exact_minimax_labels** | exact SET-VALUED ground truth for game states: full memoized NxN tic-tac-toe minimax, M(b) = the set of optimal moves, both COMPOSED partitions, chance/floor baselines, FNV-parity-safe board keys | A1-PIE (2026-10-01, RESULTS.md L4105–4220): 180,361 path rows / 2,423 boards; MLP 0.9494 board-disjoint kills the "local rules can't compose" prediction | `solve(n)` → `LabelSet` (`.rows()`, `.labels(board)`, `.stats()`, `.chance()`); `to_key(board)` for hash splits |
| **ternary_transition_kernel** | relational transition kernel: maps continuous pair-state to the {-1,0,+1} ternary codec (`sign` + deadband) and proves it predicts field transitions as well as the continuous oracle — ternarization is ~free | D19 + D20 (2026-09-27, RESULTS.md L831–871): ternary 0.01012 vs markov1 0.01786, shuffled control collapses; linear is sufficient | `FieldWorld.step()` records + `KernelArm` list → `run_arms` receipt (MSEs/gates) → `judge()` KEEP/KILL; `ternary_corr(a,b)` is the standalone codec |
| **pinch_fallback** | graded-confidence safety net: `min(noul) < threshold` → one complaint-carrying retry → PINCH to a DETERMINISTIC known-answer path; every pinch a first-class flow state, zero-engagement thresholds INCONCLUSIVE | CM1 r1/r2/r3 (2026-09-29) + RING-CX-2 (2026-10-01): broken cell rescued 11/12 by the keyword router; p0.7 {11 RETRY, 1 PINCHED}, accuracy held 12/12 | `PinchFallback(primary, grader, fallback, threshold)` → `run`/`run_corpus` → flow receipts + counts; `sweep` applies the frost law; `pinch_threshold_for_rate` (τ doctrine) |
| **ie3_dedicated_trunks** | the dedicated-specialist ARM LAYOUT in closed form: one shared rank-m trunk dilutes two orthogonal rank-k tasks under BOTH joint and sequential training; two dedicated width-k trunks do not | IE3 (2026-09-29) DILUTION_CONFIRMS: C-split 0.987/0.984 @ density 32; COMP0/COMP1 texture — FED>SINGLE only on negation (+0.126, CI excl. 0) | `make_dataset(seed, d)` → `arm_A_joint`/`arm_B_sequential`/`arm_C_split` → r² per task; ordering gate @ density 32 over 5 seeds, std==0 ⇒ INCONCLUSIVE |
| **d13d_correlation_keys** | between-cell routing keys by CORRELATION, not reward: atom-stream partner discovery at 1.0 with zero parameters and zero reward (pair polarity = the shared key), plus the COMP0/COMP1 0-param centroid-Pearson router | D13d KEEP (2026-09-27; D13/b/c RL all KILL) + D18 (floor ~0.25, "consistent relational target is the primitive") + COMP0/COMP1 routing | `make_atom_world` → `key_matrix`/`discover_partners`/`key_margin`; `build_centroid_keys` + `route` for feature-space routing |
| **g7_watt_wrapper** | the G7 seal as an importable context manager: preflight gate (VRAM/thermal), watt-sampled energy window, ALWAYS a `g7-watt-receipt@1` — PASS / KILL (breach/exception, traceback booked) / VOID (fail-closed unmeasured) — digest-bound summary, append-only ledger, tamper-evident | G7 watt-receipt instrumentation KEEP (2026-10-01, RESULTS.md L3637) + E6 receipt-drift KEEP: "no receipt → run VOID"; 67.7 W × 21.493 s live proof | `with watt_window(task_id, probe=...) as g:` → sealed receipt; `G7Wrapper.run_window(fn)`; `verify_integrity(path)`; `FakePowerProbe` for tests |
| **est_freeze_interface** | six determinacy estimators behind ONE validated interface plus the frozen C1–C5 battery; measure pair frozen E3 primary / E0 reserve; FROZEN-V1 = NONE reproduced (the spread is input-distribution sensitivity, not estimator bias) | EST-FREEZE (2026-10-01, RESULTS.md L4763–4818): the ENCODER, not the formula, was the D2 blocker; H6 0.648 with declared encoders | `score(records, spec, est, weight, seed, nperm) -> [0,1]` (frozen signature); `synthetic_atoms` / `noisy_channels` / `stationary_control` / `sensitivity_socket` / `frozen_v1` |

The r2 harvest list named a `d19_ternary_kernel` piece; that machinery was
already landed as **ternary_transition_kernel** above (D19 + D20, self-test
re-verified during this harvest: KEEP, booked numbers reproduced at source
scale) — no duplicate node was created.

Pending harvest (code-only dirs, no BLOCK.md yet — interfaces usable but
unbooked here): `board_disjoint_cv` (hash-based disjoint k-fold splitter —
the FNV high-32 scheme), `provider_seam` (provider interface over
envelope_guard), `parity_harness` (cross-implementation conformance),
`look_again`. (The r1 stubs `dedicated_trunks` and `g7_wrapper` were
landed by the r2 harvest as `ie3_dedicated_trunks` and `g7_watt_wrapper`
and the stub dirs removed.)

## How they combine

Roles, in one line each:

- **port_harness WRAPS ANY ENGINE** — port a numeric engine between
  languages/stacks and this harness verifies behavioral equivalence FIRST;
  nothing downstream consumes an unverified port.
- **envelope_guard BRACKETS A RUN** — every provider cell that enters or
  leaves a run passes the guard; the dispatch binding makes envelopes
  receipts, so a run's provenance is checkable after the fact.
- **format_first_gate PARSES GEN OUTPUT BEFORE JUDGMENT** — a judge's
  batched answers are trusted only after a strict named-question parse;
  retries and pinches are booked, never silently absorbed.
- **ternary_transition_kernel MAPS CONTINUOUS STATE TO {-1,0,+1}** — the
  ternary codec (`ternary_corr`) plus the world/arms/judge harness that
  proves the 3-symbol abstraction loses ~nothing on relational transitions.
- **exact_minimax_labels GIVES GROUND TRUTH FOR GAME STATES** — exact
  optimal-move sets (both COMPOSED partitions, chance baselines) that any
  learner or judge is scored against.
- **pinch_fallback SAFETY-NETS ANY GRADED PATH** — graded noul below
  threshold routes to a deterministic known-answer path after one
  complaint retry; the pinch is booked, the blind spots are declared, and
  a threshold that never engages is INCONCLUSIVE evidence.
- **ie3_dedicated_trunks WIRES DEDICATED CAPACITY** — the arm layout:
  one cell one job; a shared trunk dilutes two specialists under joint
  AND sequential training (the COMP0/COMP1 federation lanes inherit it).
- **d13d_correlation_keys ROUTES BETWEEN CELLS** — partner discovery and
  item routing by correlation with zero parameters and zero reward (the
  missing half of every federation lane: which dedicated cell sees this).
- **g7_watt_wrapper SEALS GPU RUNS** — `with watt_window(...):` and the
  run cannot end receiptless: PASS measured clean, KILL booked with
  traceback, VOID fail-closed when unmeasurable; no receipt → run VOID.
- **est_freeze_interface MEASURES DETERMINACY** — one frozen signature,
  six estimators, E3 primary / E0 reserve; declare the encoder or the
  number is an artifact, not a measurement.

The natural spine of a lane is:

```
[engine]--verified-by--> port_harness
[data/labels]--ground-truth-from--> exact_minimax_labels (boards ARE {-1,0,+1} vectors)
[perception]--ternary-encode-via--> ternary_corr (ternary_transition_kernel)
[discovered partners]--drive--> FieldWorld(edge_source=...)   (d13d_correlation_keys -> ternary_transition_kernel)
[dedicated cells]--laid-out-by--> ie3_dedicated_trunks
[items]--routed-between-cells-by--> d13d_correlation_keys (build_centroid_keys + route)
[GEN/judge text]--parsed-by--> format_first_gate
[graded noul]--doubted-and-pinched-by--> pinch_fallback (fallback may BE exact_minimax_labels)
[provider cells]--bracketed-by--> envelope_guard
[cell determinacy]--measured-by--> est_freeze_interface (declare the encoder!)
[everything]--receipted-to--> RESULTS.md (+ g7_watt_wrapper for watt receipts; no receipt → run VOID)
```

Shared vocabulary that makes them composable: seed 2718 everywhere; single
JSON verdict line on final stdout (PASS/KEEP vs KILL vs INCONCLUSIVE);
fail-loud structured errors; std==0 across repeats ⇒ INCONCLUSIVE, never
PASS; list-form subprocess only, never `shell=True`; no secrets read,
printed, or copied.

**Loading convention.** Every block is a self-contained `block.py` (same
filename by design — the directory is the namespace):

```python
import importlib.util
def load_block(name):
    spec = importlib.util.spec_from_file_location(f"block_{name}", f"blocks/{name}/block.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)   # module docstring + BLOCK.md carry the contract
    return mod
```

(`envelope_guard`'s downstream `provider_seam` instead inserts the block dir
into `sys.path` and imports `block` — equivalent; pick one and stay
consistent within a lane.)

## Worked example — adjudicated minimax policy run (wires 4 blocks)

A lane that trains a small game policy, then has a model judge adjudicate
the run, and books everything. CPU end-to-end.

```python
load = load_block  # loader above
port_h   = load("port_harness")            # 1. only if the engine was ported
minimax  = load("exact_minimax_labels")    # 2. ground truth
gate     = load("format_first_gate")       # 3. judge gating
env_g    = load("envelope_guard")          # 4. provenance bracket

# 1. PORT (skip if no engine port is involved): verify before anything trusts it.
#    PairedCaseSpec -> generate_paired_cases(spec, n, seed=2718) -> both runners
#    -> compare -> FrozenToleranceGate(1e-6).adjudicate -> require PASS.

# 2. LABELS: exact, set-valued, with the corpus receipt in one call.
ls = minimax.solve(3)
stats = ls.stats()          # books 180361 path rows / 2423 boards / both partitions
train_boards, test_boards = ...   # split via minimax.to_key(b) under the
                                  # board_disjoint_cv high-32 FNV scheme
                                  # (raw fnv1a64 % 10 VOIDS — all boards hash odd)
for b, opt in ls.rows():
    ...  # train: L = -log sum_{m in opt} softmax(z)_m  (SET-valued, never tie-broken)
chance = ls.chance(test_boards)     # headroom denominator, from the same block

# 3. JUDGE: interrogate the run with named questions; trust content only
#    after the strict parse; pinches land in the receipt, not under the rug.
g = gate.Gate({
    "acc_vs_chance": {"type": "noul", "question": "test top-1 normalized above chance?",
                      "instructions": "answer in [0,1]"},
    "composed_held": {"type": "bool", "question": "no COMPOSED collapse (imm partition)?",
                      "instructions": "true/false"},
}, fallback=lambda q: 0.0, judge=my_typesafe_adapter)   # injected transport, seed 2718
receipt = g.run(state={"run_stats": stats, "rule_canon": RULE_TEXT})  # r4 lesson: canon IN state
if receipt.counts["PINCHED_FALLBACK"]:
    ...  # booked as declared provenance, never a clean pass

# 4. PROVENANCE: if the judge was a provider cell, bracket it.
guard = env_g.Guard()
env = guard.validate_output(raw_provider_text,
                            env_g.Dispatch(cell_id="judge_c0", z_in=state_text,
                                           provider="glm-5.3-flash", seed=2718))
# z_in_digest binds the envelope to the EXACT judged state — the receipt,
# not decoration. Fold stats + receipt.to_dict() + env into the lane's
# RESULTS.md entry (g7_watt_wrapper if a watt receipt is owed).
```

Alternate wiring for perception lanes: `exact_minimax_labels` boards are
already ternary vectors; `ternary_transition_kernel.ternary_corr` encodes
any continuous pair-state into the same alphabet,
and its `FieldWorld(edge_source=...)` hook lets a discovered-edge upstream
replace the random pair stream without touching the generator, arms, or
frozen judge.

## Booked results pointer

Every block cites its entry; the receipts live in RESULTS.md (and per-lane
artifact dirs): B1-DISTILL (L4452–4479), XP-C (L4221–4348), CM1 r1/r2/r3
(2026-09-29) + RING-CX-2 (L5028–5055), A1-PIE (L4105–4220), D19 + D20
(L831–871), IE3 (L2596) + COMP0 (L4661) / COMP1 (L4872), D13d + D18
(L591–620 / L718–739), G7 watt-receipt instrumentation (L3637), EST-FREEZE
(L4763–4818). Run any block's self-test from
the lab root — `python3 blocks/<name>/block.py` — and it re-proves its own
receipt on CPU in seconds.
