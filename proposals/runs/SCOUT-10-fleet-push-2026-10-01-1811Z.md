# SCOUT-10 — SuperInstance fleet-push sweep — 2026-10-01 1811Z (day-conductor)

Window covered: since SCOUT-9 (~10:05Z-ish, commit fae2fd0) → 18:08Z. Method: `/users/SuperInstance/events`
(user account, not org) + per-repo commits + open PRs across 14 repos. Read-only, nothing filed.

## State changes seen (last 48h window, notable since last scout)

1. **fleet-seeds wave-63: jev calibration ledger v1 (97187b8, 17:15Z)** — seeded, aggregation rules
   pre-registered. Class: **TOOL/CORROBORATE** for the QC-JEV lineage. Our QC-JEV booking (jeff-0.8b
   DISCRIMINATING, d_ptrue 0.936, murmuration null does not transfer) is exactly the kind of per-checkpoint
   datum their ledger wants to aggregate. No threat; opportunity to make our numbers ledger-shaped.
   → spawned **JC-1** (local formatting only; we file nothing).
   Also notable from their run-7 commit (2bc52a5, yesterday): M12 SEALED with a registered falsifiable
   prediction ("first-campaign self-improvement gains concentrate in measurement/transport repair, not
   strategy") and a live anti-cherry-pick QRNG override of the priors' own pick — pre-reg discipline
   corroborated at the fleet level. Watch: E6 re-registration can REFUTE M12; if it fires, it touches
   nothing of ours directly but is the fleet's biggest falsifier in flight.

2. **fleet-triage GPU-EXPERIMENTS Exp 3 "unblocked-but-redirected" (f3cce13, 16:49Z)** — Exp 3 (4×4
   composition test) is blocked-on-data pending a C bitboard solver; the redirect is a wave-63 partition
   re-derivation on 4×4. **No change to our held items** (MMX-1, FT-D1 unaffected). Class: **CORROBORATE**.
   Their framing — "once a lookup table is impossible, you no longer know whether your model is reasoning
   or memorising" — is the same regime-scope honesty we pinned on W5b2 (KEEP claims "reproducible in OUR
   regime", one corpus, one architecture). No spawn.

3. **quilt-research-canons PR #4 (open scout report)** — census paged to exhaustion (52 pages, 5110 repos,
   overlap assertion passed). Three items touch our assets:
   - **quilt-cell-bridges: 44/63 bridges hardcode `/workspace` output paths and die on the final write in
     a clean clone.** Class: **CONTRADICT-CANDIDATE → resolved as CORROBORATE-of-defect-class**: this is
     EXACTLY our 4-instance hardcoded-output-path defect (W5a — first attempt partially overwrote the
     committed artifact; qc_jev_control — did overwrite; w5b2; ST1v2). Their fleet-wide count confirms the
     class is systemic, not local: **RC-1 priority RAISED.**
   - **logtensor: 88 tests pass, but zeroing the proportional-navigation homing term keeps all 88 green —
     the term is never executed by any test.** Class: **TOOL / CONTRADICT-CANDIDATE against any booking
     whose gate arithmetic lives in a branch no test exercises.** Our nearest instances: the QG1c census
     script that "never produced its own 1892 booking" (radians bug lived in exactly such an untested
     branch), and the 10:1x seal-that-pinned-an-untracked-artifact. A booked gate whose code path is never
     executed by any committed check is a check that cannot fail. → spawned **RC-1b** (dead-branch census).
   - Fleet canary in **1 of 5110 repos** (vs 558 hits for the bare FNV constant) — our repo already flagged
     as canary-less; unchanged, Casey-scale decision.

4. **pong-quilt PRs #88–#92** (C1 lane, daily cadence): #92 = C1 scaling study v0 — 7 arms, honest
   descriptive read: **seed variance dominates at 40 gens; horizon, not population, is the axis that
   moves.** Class: **CORROBORATE** of our QG3/QG6 time-law (trapping is a TIME problem; width inert).
   Independent substrate, same law-shape — convergent-law candidate, not a threat. Their honesty
   architecture ("printed, never believed" marker pinned in source; study never touches the canonical
   checkpoint) is a steal-shaped pattern for W5b-style allocation studies: pin the no-claim marker in the
   runner source, not just the pre-reg. Noted for RC-1b's spec.

5. **reverse-actualization wave-73b (17:15Z): NEGATIVE ladder walked, rungs −1..−10, registered prediction
   CONFIRMED both halves; wave-79: iterative re-anchoring FAILS honestly** — same-model loop keeps its
   attractor; lexical and semantic channels independent. Class: **CORROBORATE** of pre-reg + honest-fail
   doctrine; no contact with our assets. No spawn.

6. **Projectionist / quilt-arcade / taps-creative-break / qthe / crab-traps** — game publishing, judge
   refreshes, wipe-rounds, hermetic-chain receipts. No contact with quilt-gpu-lab assets. qthe/crab-traps
   two-reader rule (8/8 agree, tamper localization) further corroborates RC-1b's direction (independent
   readers over shared trust). No action.

7. **[EMBASSY] pong-quilt #49** — now shows **7 comments** (previously logged unresponded). Status changed
   since SCOUT-6; embassy lane appears to have moved. Casey-scale item, likely retired — flagged, not acted.

## SPAWNED QUEUE ITEMS (concrete)

- **[ ] RC-1b dead-branch census** (CPU ~45m): over `tools/` + `experiments/`, for every runner whose
  output a booked verdict depends on, assert the gate-computation branches are exercised by at least one
  committed test or by the verified reproduction run (logtensor homing-term class; QG1c radians was a
  live instance). Gate: census produces a table runner → branches → covered-by; any UNCOVERED gate branch
  on a BOOKED result is RED until covered or the booking is re-flagged. Fold-in: pong #92-style
  no-claim marker pinned in runner source for exploratory outputs.
- **[ ] JC-1 jev-calibration-ledger formatting** (CPU ~10m, LOW): reformat QC-JEV (+QC-JEV2 if it fires)
  numbers into fleet-seeds wave-63 ledger shape, staged locally, ready for Casey to push. No filing.
- **[no-spawn note]** RC-1 (differential receipt harness) priority RAISED by canons PR #4's
  quilt-cell-bridges finding (44/63 bridges, same defect class, fleet-wide). Keep atop the CPU queue.

Rotation bookkeeping: this was an (A) scout slice, non-GPU. GPU lane free; no GPU item fired; no repro due
(SCOUT slice — last GPU landing D12j already reproduced bit-exact 06:2x).
