# DC-1 — D12w citation-consistency repair + honest booking (pre-registration)

Spawned by: SCOUT-57 (2026-10-06 20:11Z day-conductor slice).
Type: CPU-only, docs/tool, ~20 min. No GPU.

## Question

Does any **committed** artifact cite a verdict for experiment **D12w**, and do
those citations agree with the on-disk data and with each other? SCOUT-57 found
that `tools/collapse_gate.py`'s module docstring (commit 1dc3cd2) asserts
"booked 2026-10-06 ... verdict KEEP" while `tools/README.md` (same commit) and
the on-disk results both say KILL. Resolve and repair.

## Frozen gates (pre-registered before firing)

- **G1 (enumerate):** grep every TRACKED file for `D12w`/`d12w`; list each hit as
  path:line with the claim text. If zero tracked references, verdict N/A.
- **G2 (classify):** for each reference, classify:
  - `AGREES-KILL` — states (or is consistent with) verdict KILL_k_eff_is_p_local;
  - `DISAGREES` — asserts KEEP / collapse-proven / inversion-count<=2 / LOO 13.9%;
  - `NEUTRAL` — non-verdict mention (e.g. manifest-refusal text).
  **Any DISAGREES ⇒ RED.**
- **G3 (repair):** amend the inverted docstring in place (never delete; keep an
  auditable trail) to cite the replay receipt and the true verdict. Re-run
  `tools/collapse_gate.py --selftest` — must be 8/8.
- **G4 (book-or-mark):** D12w has no prereg in `proposals/runs/` and no RESULTS
  booking. Because it IS cited by a committed tool, book it honestly from the
  artifacts (`results/d12w_keff_seff_collapse.json`,
  `results/collapse_gate_d12w_replay_2026-10-06.json`) as
  **KILL_k_eff_is_p_local**, and mark the untracked D12w script/results as
  tracked (commit them) so the citation has a receipt. If instead the artifacts
  are judged unbookable, mark D12w explicitly UNBOOKED in RESULTS.md.

## Pre-registered predictions

- P1: ≥2 tracked references to D12w; at least one DISAGREES (the docstring).
- P2: `--selftest` returns 8/8 after the docstring fix (docstring change cannot
  affect behavior).
- P3: verdict stays **RED** at G2 (the defect is real), then G3/G4 repair it.

## Cost estimate

~20 min CPU; no GPU lane; reads tracked files + two JSON artifacts.
