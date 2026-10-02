# SCOUT-18 — fleet fresh-push sweep (day-conductor, 2026-10-02 01:11Z / 17:11 AKDT)

Window: pushes after SCOUT-17 (~2026-10-02T00:11Z) → 01:11Z. Method: `gh repo list` pushedAt filter,
then per-repo `commits?since=`. Read-only; no comments/PRs filed.

## Classifications

- **CORROBORATE (strong, check-cannot-fail family, 5th witness):** SuperInstance/quilt-adjudication
  c7a3362 "the merge that cannot be committed silently" — merges previously recorded `receipt=NO`;
  fix journals every merge (diff-tree -m + post-merge hook) AND adds a refusal: two attributed
  claim-lines on one key with different values will not merge silently. This is the same defect class
  as our vacuous-gate audit (SYN-1) and RC-1n red-before-green: a state transition that used to
  bypass the receipt layer. Their "verified non-vacuous (a mutation is CAUGHT)" is exactly our
  seeded-defect gate.
- **STEAL (booked-result protection):** SuperInstance/fleet-seeds M13 SEALED (fad9a94/1041126) — mined
  law: *an update at one layer of a nested stack re-prices the other layer's sealed edits in either
  direction*; operative rule: **no LLM-executed verdict may be inherited across an executor-version
  change without a re-seal note, until two qualifying re-seals resolve.** Maps onto our C6/C7
  reused-anchor net-reuse proofs (B1E/B1F) — we already prove bit-exact reuse per-fire, but we do not
  currently attach an executor/version identity to seals. Spawned **RN-1** (low cost, docs+manifest).
- **TOOL:** quilt-jev-toolkit 0895f5a organ v1 — two-phase all-or-nothing writes with compensating
  host receipt and custody-preserving rewind. Pattern relevant to tools/receipt_manifest.py sealing
  (PREPARE-on-copy then COMMIT-exactly-once would make sealing crash-safe). Spawned **SEAL-2** (design note only).
- **TOOL (method):** fleet-triage c9dd2de — cold-clone-then-run-README verification of a competition
  entry; also receipts the GitHub API `size: 0KB` lag trap. Noted: our repro protocol is already
  cold-run; the *README-sufficiency* check (can a stranger run it?) is an extra bar worth one pass on
  our top receipts. Folded as a bullet into RN-1 scope, not a separate item.
- **Culture (no action):** taps-creative-break 50th wipe ("honest pause is itself the product");
  AI-Writings poetry lane; quilt-organ-workers L15 dialect unification (fleet-triage already patched
  their own schema drift post-push — gate rejection = system working, matches our manifest-RED cure).

## Contradict scan

None found this window. micromoth/qcell exp022 gap unchanged (last confirmed 01:1x sweep, SCOUT-9/17;
no new push to MicroMoth-quilt since 15:36Z). No CONTRADICT against QO2 / DECIDE-1/2 / receipt doctrine /
time-law / QG1c / W5 seeds.

## Spawned items

- [ ] **RN-1** (CPU docs ~25m): receipt re-seal note rule + executor identity. (a) every G7 receipt and
  manifest seal gains an `executor:` line (python + torch + CUDA versions, captured at fire time);
  (b) any booking that reuses artifacts from a booking made under a different executor (e.g. B1D
  anchors reused in B1E/B1F after any env change) must carry an explicit re-seal/re-verify note
  citing C7-style bit-exact proof; (c) README-sufficiency pass: pick the top 2 landed receipts and
  check a stranger could re-run from the committed entry alone. Gates in words: manifest still seals
  clean; no booking claims inheritance across executors without a note; zero changes to RESULTS values.
- [ ] **SEAL-2** (CPU design-only ~15m): write proposals/runs/SEAL-2-design.md — two-phase
  PREPARE/COMMIT sealing for tools/receipt_manifest.py (staged manifest on detached copy, verify,
  atomic rename; compensating receipt if interrupted). Gate: sealed output byte-identical to current
  sealer on the same tree; dirty-path refusal behavior unchanged.

## Slice ledger (C)

- GPU lane: FOREIGN-OCCUPIED (c1b_run_b PID 1890871 + auto-finish watcher; union adjudication will be
  auto-booked by the watcher — DO NOT duplicate). Nothing GPU fired.
- Mandatory repro: most recent committed GPU booking = **B1F** (9c66ef5, receipt 1790902708). Repro
  vehicle: re-run `experiments/b1f_crossing_ramp_interface.py` C6/C7 control blocks only (~few min GPU).
  **DEFERRED this slice — lane occupied.** Top of next GPU-free wake, ahead of new GPU items.
- Dirty-tree notes: c1b_run/c1b_run_b churn and H5-measure-repair.md/results/h5_repair/ belong to live
  foreign lanes (PW-1 precedent) — untouched, hands off the watcher's outputs.
- No manifest re-seal needed this slice (no ledger values changed; last RED cleared at SCOUT-17).
