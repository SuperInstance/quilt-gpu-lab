# RESULTS-ENTRY — grader blind spots + repair (GRADER-BLINDSPOT, r11 follow-up)

**Lane:** GRADER-BLINDSPOT · **Subject:** `SuperInstance/MicroMoth-quilt`
`exp015/selfplay-d1` mutation battery · **HEAD:** `37c0608` ·
**Mode:** local analysis in `scratch/grader_blindspots/repo` — **no
upstream commit, no push, no branch, no deletion** (SuperInstance red lines).

## 1. Blind-spot map (reproduced)

Re-ran `tools/selfplay.py --rounds-per-shape 5 --canaries 12` on a fresh
clone: **overall 0.72 (52/72)**, canaries 9/12 — identical overall rate to
the booked `experiments/selfplay/SUMMARY.md`, with three shapes at
**exactly 0.00**:

| shape | rounds | caught | catch_rate |
|---|---|---|---|
| `phase_sign_flip` | 6 | 0 | **0.00** |
| `noise_mixing_swap` | 6 | 0 | **0.00** |
| `comparison_flip` | 6 | 0 | **0.00** |

The other nine shapes: eight at 1.00, `literal_rewrite` at 0.67.

## 2. Per-shape root cause (each CONFIRMED by minimal repro)

Minimal repro: `scratch/grader_blindspots/repro_blindspots.py` (loads
pristine + synthesized-mutant kernels side by side). Evidence in
`blindspot_map.json` → `blind_spots[].minimal_repro_evidence`.

- **`phase_sign_flip`** — *phase-insensitive observables.* The mutation
  conjugates the `|0>` branch of `phaseturn`, degrading rz's **relative**
  phase to a global one on `|0>`. Repro: statevector differs
  (`[cos, -sin]` → `[cos, +sin]`) but `probabilities_dict`, counts and
  Bell+rz counts are **byte-identical** (seed 42, 4096 shots). Every
  battery pin is a magnitude observable; no statevector pin exercises rz.
- **`noise_mixing_swap`** — *symmetric statistics.* Swapping the two
  mixing weights is **exactly** a per-qubit re-labelling of the result bit
  (`probs[b0] <-> probs[b1]`). Repro: asymmetric `rx(0.6)` distribution
  flips (`0.8301/0.1699` → `0.1699/0.8301`) and equals the exact relabel,
  but the Bell-state noise distribution is invariant — and the battery's
  only noise pin (`test_collapse_ledger`) runs the Bell state.
- **`comparison_flip`** — *unreachable boundary.* `r<cumu` → `r<=cumu`
  differs only on a measure-zero draw. Repro: counts identical over 40
  seeds; but injecting a draw **exactly equal** to the cumulative partial
  sum flips the sample `11` → `00`. The battery never injects that draw.

## 3. Repair prototype (local only) + new catch table

Patch: **add `tests/test_grader_blindspots.py`** (3 pins, one per shape)
→ `results/grader_blindspots/repair.diff` (PR-ready, new file, 131 lines).

FAIL-first verification (`verify_repair.py`, `verify_repair.json`):
pristine **GREEN (3 passed)**; each mutant **RED on its own pin only** —
clean 1:1 catch map.

Full battery re-run with the repair, same schedule:

| shape | before | after |
|---|---|---|
| `phase_sign_flip` | 0.00 | **1.00** |
| `noise_mixing_swap` | 0.00 | **1.00** |
| `comparison_flip` | 0.00 | **1.00** |
| **overall** | **0.72 (52/72)** | **0.97 (70/72)** |
| canaries | 9/12 | **12/12** |

**Regression check:** overall **+0.25** (target was ≥0, no −0.02
regression); **zero shapes regressed**; baseline failure set unchanged
(only the pre-existing `test_import_baseline` RED); the only remaining
misses are `literal_rewrite` 2/6 — untouched by this repair, carried as
the instrument's standing honest negative.

## 4. Seal-RED root cause

`tests/test_import_baseline.py` is RED: manifest **487 sealed** vs **497
tracked** (498 incl. the self-excluded manifest). Drift = **10
tracked-but-unsealed files** + `AUDIT.md` digest change, all landing
**after** the 2026-09-30 03:23 UTC seal: PR #28 (`2c03e1f`, 8 `exp022`
files), PR #29 (`8bdae01`, `test_lab_home_citation.py` + AUDIT edit),
then the 2026-10-01 `37c0608` overnight auto-push. Silent because the pin
is passive, **CI never runs the Python battery** (`.github/workflows/build.yml`
is a release-only C#/NuGet job), the auto-push writer never re-seals, and
re-seal is manual. Full analysis + the 10-file list + re-seal procedure:
`results/grader_blindspots/seal_red_analysis.md`.

Re-seal (drafted, **not run**): `python3 tools/import_manifest.py`
(expect *"sealed: 497 tracked files"*) → `pytest tests/test_import_baseline.py -q`
green → commit `receipts/import-baseline.json` with the change. Schema
stays `micromoth-quilt/import-baseline@v1`; only `generated_at` +
`baseline_commit` advance. Prevention: a pre-push hook / 1-line CI job
running the pin so a non-resealing writer can't drift silently again.

## Verdict

Both r11 findings are reproduced, root-caused to phenomena (not noise),
and the grader blind spots are repaired with a FAIL-first, regression-free
patch. Everything is staged as PR-ready artifacts. **Nothing posted or
committed upstream — keeper-gated.**

## Artifacts

`results/grader_blindspots/`: `blindspot_map.json`, `repair.diff`,
`seal_red_analysis.md`, `RESULTS-ENTRY.md` (+ `support/` raw receipts).
Draft issues: `pr_harvest/ISSUES-draft.md` (2 issues).
