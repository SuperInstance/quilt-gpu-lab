# RECEIPT — lane SEAL-PIN: seal pin + selfplay widening (PR#30 follow-ups)

Lane: SEAL-PIN (z.ai GLM lane), 2026-10-01. Scratch clone:
`scratch/grader_blindspots/repo`, branch **`keeper/seal-pin-and-widening`**
(based on `keeper/grader-blindspot-repair` = 191be6e). Local commits only,
NO pushes — keeper applies.

## Booked deliverable 1 — the seal pin

Root cause being pinned (PR#30 finding): the overnight auto-push writer
commits artifacts WITHOUT re-sealing the import manifest; the
drift-catcher (tests/test_import_baseline.py) drifted silently because
nothing ran it (487 sealed vs 497 tracked at 37c0608).

**Design headline: one script mode + one workflow job + one hook installer.**

- `tools/import_manifest.py --check` (new read-only mode): verifies the
  sealed manifest against the live tracked tree; exit 0 clean, exit 1
  drift, exit 2 manifest missing/unreadable/malformed. Fail-loud output
  names every UNSEALED / DRIFTED / ORPHANED file + the remedy. Provably
  write-free (manifest bytes unchanged across a check run).
- `.github/workflows/seal.yml` (new CI job `seal-check`): runs `--check`
  on every push + PR — an unsealed tree cannot merge remotely. This is
  the backstop for clones that never installed the hook.
- `tools/hooks/pre-push` + `tools/install_hooks.sh`: local pin — blocks
  `git push` on drift, so the auto-push writer's push is refused unless
  it re-seals. **Auto-push path coverage:** hooks are not cloned, so the
  writer's clone must run `tools/install_hooks.sh` ONCE (one command;
  idempotent). Keeper action item: run it in the auto-push clone.
  Thereafter the writer either re-seals before committing or the push
  fails loudly. (Chose block over auto-re-seal in the hook: blocking is
  reversible; auto-amend could rewrite history.)

Verified: SEAL OK on sealed tree; deliberate README digest drift → exit 1
with the file named; manifest removed → exit 2; hook rc=1 under drift with
PUSH BLOCKED banner, rc=0 clean; `--check` leaves the manifest byte-identical.

## Booked deliverable 2 — selfplay widening (3 variants)

Extended the instrument (`tools/selfplay.py` SHAPES) + new FAIL-first
pins (`tests/test_widening_pins.py`, house style of
tests/test_grader_blindspots.py):

1. **phase mutation on the |1> branch** — new `phase_sign_flip` variant
   conjugates phaseturn's |1> branch (both `sin(+theta/2)` →
   `sin(-theta/2)`): rz degenerates to a GLOBAL phase. Pin: exact |1>
   amplitude after x·rz(θ), imaginary part +sin(θ/2).
   **FAIL-first: pristine battery BLIND (0 new failures); caught by the
   new pin alone.**
2. **noise mutation on an ASYMMETRIC circuit** — new `noise_mixing_swap`
   variant mis-indexes the noise model (`noise_model[j]` →
   `noise_model[0]`), invisible to uniform noise and to
   re-label-invariant Bell pins. Pin: 2-qubit asymmetric circuit
   (rx 0.6 / rx 1.1), DISTINCT per-qubit error rates [0.05, 0.15],
   analytic 4-outcome assert in kernel order (qubit 0 mixed first).
   **FAIL-first: pristine battery BLIND; caught by the new pin alone.**
3. **boundary-draw canary** — r == cumu equality injected deliberately
   via monkeypatched draw: INTERIOR boundary (after index 1 of the
   asymmetric 2-qubit distribution → must fall to the NEXT outcome) and
   TOTAL boundary (Bell, r = Σprobs → shot must be DROPPED under strict
   r<cumu; r<=cumu accepts at the last index). Boundary coverage of
   comparison_flip widened 1 → 3 (first + interior + total).

## Verification (full battery, local)

- Working tree (sealed, pristine kernel): **256 passed**, incl. 4 new
  widening pins. `--check`: SEAL OK (502 = 502).
- Full instrument re-run (`python3 tools/selfplay.py`, 60 rounds):
  **58/60 caught, rate 0.97** (was 43/60, 0.72). The three formerly-0.00
  shapes → **1.00** (phase_sign_flip, noise_mixing_swap, comparison_flip).
  Canaries 12/12. 0 harness crashes, 0 synthesis failures. The 2 misses
  are `literal_rewrite` (0.60, known partial — 9th-decimal perturbation).
- FAIL-first matrix (staged worlds, delta vs baseline): both new
  mutation variants missed by the pristine-HEAD battery, caught by the
  new pins only; comparison_flip caught by repair pin + both new canaries.

## Bookkeeping

- Commits (branch `keeper/seal-pin-and-widening`, fast-forwardable onto
  PR#30 or openable as follow-up):
  - `7cd5111` seal pin: --check mode + CI seal-check job + pre-push hook
  - `958bc1f` selfplay widening: |1>-phase, per-qubit noise variants +
    boundary-draw canary
- Each commit re-seals `receipts/import-baseline.json` WITH its change
  (declared re-embed protocol; dogfooded the pin mid-flight — the
  manifest pin went RED on the uncommitted widening and forced the seal).
- `keeper/grader-blindspot-repair` restored to 191be6e (untouched).

## Suggested PR#30 description addendum

- The root-cause remedy is now enforceable, not procedural: CI
  `seal-check` job + pre-push hook (install once per clone:
  `tools/install_hooks.sh`). Keeper: install the hook in the auto-push
  writer's clone, or its push will fail loudly on the next unsealed sync.
- Selfplay widening landed: 0.72 → 0.97 overall catch; all three 0.00
  shapes now 1.00 with sibling-path coverage.
- Staged-world honest negative updated: the manifest pin fails
  ENVIRONMENTALLY in temp copies (no .git), always delta-excluded; the
  real tree's seal is owned by test_import_baseline + CI + hook.
