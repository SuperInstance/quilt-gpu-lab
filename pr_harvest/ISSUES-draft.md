# ISSUES-draft — MicroMoth-quilt (GRADER-BLINDSPOT, r11 follow-up)

DRAFT ONLY. DO NOT POST. Keeper-gated. Two issues, both from the r11
scout findings; each carries its own evidence, root cause, and remedy.

---

## ISSUE 1 (draft) — exp015 mutation battery has three structural blind spots (0.00 catch shapes)

**Labels:** `experiment`, `qcells`, `honest-negative`
**Evidence:** `experiments/selfplay/SUMMARY.md` (`phase_sign_flip 0.00`,
`noise_mixing_swap 0.00`, `comparison_flip 0.00`, overall 0.72);
reproduced at HEAD `37c0608`; per-shape repro + repair in the
GRADER-BLINDSPOT lane artifacts (`blindspot_map.json`, `repair.diff`).

### What
The self-play instrument (`tools/selfplay.py`) injects 12 mutation shapes
into `micromoth.py` and measures the `tests/` battery's catch rate. Overall
0.72, but **exactly 0.00** on three shapes. The 0.00s are real defects the
battery cannot see, each for a different structural reason.

### Root causes (each CONFIRMED by minimal repro)
1. **`phase_sign_flip` — phase-insensitive observables.** The mutation
   conjugates the `|0>` branch of `phaseturn`, turning rz's relative phase
   into a global one on `|0>`. `probabilities_dict`, counts and Bell+rz
   counts are byte-identical (seed 42, 4096 shots); only the complex
   statevector moves — and no statevector pin exercises rz.
2. **`noise_mixing_swap` — symmetric statistics.** Swapping the mixing
   weights is exactly a per-qubit readout **re-labelling**
   (`probs[b0] <-> probs[b1]`). The battery's only noise pin runs a **Bell**
   state, whose distribution is invariant under the relabel.
3. **`comparison_flip` — unreachable boundary.** `r<cumu` → `r<=cumu`
   differs only when the draw equals a cumulative boundary (probability
   zero for a continuous RNG). Counts identical over 40 seeds; injecting
   the exact boundary draw flips the sample `11` → `00`.

### Remedy (proposed patch, in-lane)
Add `tests/test_grader_blindspots.py`: three FAIL-first pins (exact
imaginary sign of rz on `|0>`; an **asymmetric** noisy distribution
asserted against `(1-p)p0 + p*p1`; a boundary draw read live from
`probabilities_dict` and required to fall through under strict `<`).
Re-run with the patch: three shapes **0.00 → 1.00**, overall **0.72 →
0.97**, canaries **9/12 → 12/12**, zero shapes regressed, baseline
failure set unchanged.

### Honest limits
`literal_rewrite` stays 0.67 (2/6 misses) — a fixed-point float mutation
invisible to tolerant comparisons; carried as the instrument's standing
honest negative. Repair is local/prototype; not pushed.

---

## ISSUE 2 (draft) — import-baseline seal drifted silently (487 sealed vs 497 tracked); re-seal + guardrail

**Labels:** `bug`, `manifest`, `ci`
**Evidence:** `tests/test_import_baseline.py::BaselineSealed::test_manifest_exists_and_matches`
RED at HEAD `37c0608`; full analysis in `seal_red_analysis.md`.

### What
`receipts/import-baseline.json` (schema `micromoth-quilt/import-baseline@v1`)
sealed 487 files at `generated_at 2026-09-30T03:23:25Z` (naming
`baseline_commit 5106a14`). HEAD tracks 497 (498 incl. the self-excluded
manifest). Drift = **10 tracked-but-unsealed files** + `AUDIT.md` digest
change:

1. `receipts/exp022-desert-break.json`
2. `receipts/exp022-desert-break/exp022.results.json`
3. `receipts/exp022-desert-break/exp022.telemetry.k3.jsonl`
4. `receipts/exp022-desert-break/exp022.telemetry.k4.jsonl`
5. `receipts/exp022-desert-break/exp022.telemetry.k5.jsonl`
6. `receipts/exp022-desert-break/exp022.telemetry.k6.jsonl`
7. `receipts/exp022-desert-break/exp022.telemetry.k7.jsonl`
8. `receipts/exp022-desert-break/exp022_crossing_stream_census.py`
9. `tests/test_exp022_receipt.py`
10. `tests/test_lab_home_citation.py`

All introduced **after** the seal: PR #28 (`2c03e1f`), PR #29 (`8bdae01`,
plus the `AUDIT.md` edit), then the `37c0608` overnight auto-push.

### Root cause (why silent)
The pin is **passive** (only trips when someone runs pytest); **CI never
runs the Python battery** (`.github/workflows/build.yml` is a
release-only C#/NuGet job); the **auto-push writer never re-seals**; and
re-seal is **manual**, so PRs #28/#29 shipped file adds with the manifest
untouched.

### Remedy
Re-seal with the declared tool (never hand-edit): `python3 tools/import_manifest.py`
(expect *"sealed: 497 tracked files @ <HEAD12>"*) → `python3 -m pytest
tests/test_import_baseline.py -q` **GREEN** → commit `receipts/import-baseline.json`
together with the change. Schema version unchanged (`@v1`); only
`generated_at` + `baseline_commit` advance. **Prevention:** add a
pre-push hook or a 1-line CI job running the import-baseline pin (stdlib,
<1s) so a non-resealing writer cannot drift `main` silently again; the
auto-push agent must re-seal before committing local artifacts. Note: the
re-seal also retires exp015's one pre-existing baseline RED — update
`tools/selfplay.py`'s honest-negative note in the same change-set.
