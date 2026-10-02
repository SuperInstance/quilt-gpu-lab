# port_harness

## WHAT IT DOES

A standalone dual-implementation equivalence harness: it proves that a PORT of a
numeric engine agrees with its REFERENCE before any downstream gate trusts the
port. Harvested from the B1-DISTILL lane, where this machinery verified the
JS↔torch engine port behaviorally equivalent (max abs diff ≤ 7.2e-07) before the
distillation gates ran — the gates then KILLed the distillation claim itself,
but the port harness was proven and is harvested here.

The harness's central law comes from a booked defect: the FIRST port control ran
MIXED-SIDE rows (row i from JS paired against row j from torch), measured
0.162 agreement, and produced a phantom bug / false FAIL. The fix — PER-SIDE
rows, each implementation computing BOTH sides of the same symmetric comparison,
rows compared side-by-side — is baked into the generator, the runner protocol,
and the comparator: **align inputs per-side, per-row, with the pairing explicit,
or the harness measures shuffle noise.**

Environment: python 3.14 + numpy (reference side), node v22 (port side), stdlib
otherwise. No torch, no GPU. The node child is spawned list-form; `shell=True`
is never used.

## INTERFACE

Inputs / outputs / contract:

- **Paired-row spec** — `PairedCaseSpec(input_ranges: dict[name -> (lo, hi)],
  sides: tuple)`. `generate_paired_cases(spec, n, seed=2718)` emits `n` seeded
  `PairedCase(row_id, state, sides)` rows. Each row carries the SHARED state and
  BOTH sides of the symmetric comparison; the pairing is explicit in the row.
- **Runner protocol** — a runner takes the same paired rows and returns
  `{(row_id, side): float}`, keyed, never positionally aligned. Two shipped
  runners:
  - `NumpyPongRunner` — reference implementation of the pong derived law,
    vectorised numpy, float64 end to end.
  - `JsPongPortRunner(js_path, bug=None)` — the JS port in a persistent node
    child (JSON-lines protocol, one `{cmd: eval, cases: [...]}` in / keyed
    results out; `{cmd: quit}` to close). Any other engine port can plug in by
    implementing the same two methods (`run`, `metadata`).
- **Comparator report** — `compare(reference, port)` aligns by `(row_id, side)`
  key, never by list order; key-set mismatch fails loud (that IS the mixed-side
  defect class). Returns `ComparatorReport`: `n_rows`, `n_points`,
  `max_abs_diff`, `mean_abs_diff`, `exact_match_rate`, and
  `first_divergent = {row_id, side, reference, port, abs_diff} | None`.
- **Frozen-tolerance gate** — `FrozenToleranceGate(tol=1e-6)`; the bar is fixed
  at construction, before any output is seen, and `tol=None` fails loud.
  `adjudicate(report)` → `PASS` iff `max_abs_diff ≤ tol`, else `KILL`.
  `multi_seed_stats(per_seed_max_abs_diff)` applies the house law to the port's
  per-seed gate stats: **std == 0 across repeats → INCONCLUSIVE**, never PASS.
- **Honest booking** — `run_metadata(...)` records runner versions/digests when
  cheap: sha256 of the JS artifact, `node --version`, numpy/python versions,
  seed, spec, and the frozen tol.
- **Final verdict** — the consumer prints exactly one JSON object on the final
  stdout line with exactly one top-level field, `"verdict"`, and exits 0 iff
  PASS.

**Precision contract.** Both sides compute in IEEE-754 double (float64); the JS
port uses plain `Math.*` doubles (`Math.fround`-free) and the numpy side stays
float64, so an honest port agrees exactly (0.0). The original JS↔torch receipt
was 7.2e-07-class only because the torch side evaluated the net in float32
while the JS side used doubles — the `tol` parameter exists for exactly this
mixed-precision class; set it deliberately (1e-6 default) and freeze it before
the run. Do not narrow it after seeing output.

**House contracts baked in:** seed 2718 default · single JSON verdict line ·
fail loud (missing tol, misaligned keys, dead child) · list-form subprocess
only, never `shell=True` · std==0 across repeats → INCONCLUSIVE (multi-seed
gate stats) · no secrets are read, printed, or copied.

## THE RECEIPT

- Cite: **RESULTS.md B1-DISTILL entry (2026-10-01)** (lines 4452–4479);
  full entry `results/b1_distill/RESULTS-ENTRY.md`; code
  `experiments/b1_distill.py`, `experiments/b1_pong_law_engine.mjs`.
- `js_vs_torch_port_max_abs_diff = [7.15e-07, 6.28e-07]` (≤ 7.2e-07, gate bar
  1e-6) — the engine port was verified behaviorally equivalent before any gate
  ran; the distillation itself KILLed its separate 1e-3 gate and is NOT what
  this block harvests.
- Law equivalence control: pristine-vs-switch `max_abs_diff = 0.0`
  (0/4000 states differ, bit-identical).
- Booked defect → this block's central law: the first port control ran
  mixed-side rows → false FAIL at 0.162 agreement (a phantom bug); fixed to
  per-side rows → ≤ 7.2e-07.
- Artifacts: `results/b1_distill/controls.json` (both the defective attempt and
  the per-side fix, `defect_1` narrative),
  `results/b1_distill/port_control_rerun.json` (the clean per-side rerun).

## COMPOSITION

Upstream of any distill/train block that ports an engine between languages: a
b1-style policy distillation consumes a VERIFIED port (run this harness first;
book its max_abs_diff next to the port, as b1 booked controls.json). The
paired-row generator feeds both runners; the comparator's report and the frozen
gate slot into board_disjoint_cv-style frozen gates (bar fixed before the run,
fail loud on missing bar); the run metadata books runner digests the way the
G7 watt receipt (via `g7_watt_wrapper`) books energy — receipt-or-VOID discipline
applies to anything downstream that consumes the port. Contracts the consumer
must honor: pass identical paired rows to both runners; never realign by list
order; freeze `tol` before firing; treat a std==0 multi-seed port stat as
INCONCLUSIVE, not evidence of perfection.

## SELF-TEST

Command (from the lab root, CPU-only, <10 s including node startup):

```
python3 blocks/port_harness/block.py
```

Checks booked in the `HARNESS {...}` line:

- reference vs correct JS port, 2000 seeded paired rows (4000 (row, side)
  points), frozen tol 1e-6 → gate `PASS` (expected max_abs_diff 0.0 — both
  sides are float64);
- comparator order-invariance: shuffling the port's dict insertion order leaves
  the report unchanged (the mixed-side lesson, asserted);
- multi-seed gate stats over 3 input seeds → std == 0 → verdict `INCONCLUSIVE`
  (house law demonstrated on an exact port);
- reference vs deliberately-bugged port (deadzone halved to 0.75) → harness
  detects it, names the first-divergent (row, side) with both values, and the
  buggy-port gate verdict is `KILL`; `harness_detected_buggy_port: true`.

Expected verdict: **PASS** (the harness itself is the unit under test — the
buggy port's KILL is the asserted proof of detection), final stdout line
exactly `{"verdict": "PASS"}`, exit 0.
