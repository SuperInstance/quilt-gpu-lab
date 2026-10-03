# SCOUT-26 — SuperInstance sweep, 2026-10-03 04:39Z (day-conductor slice, ~20m)

Sweep basis: users/SuperInstance repos sort=pushed (100 newest, window since 2026-10-01T04:39Z), commit tips
of 14 lane repos, open PRs (only new: fleet-triage #5 docs edge-watch), open issues in pong-quilt
(#102 round-80 PR, #49 embassy unchanged). Local tree == remote (no fleet pushes into quilt-gpu-lab).
Primary source: canons SCOUT-2026-10-03T0440Z (59th-wipe, fabricated benchmarks) + follow-ups on 6 lane repos.

## HEADLINE — holonomy-consensus: a published "validation" built from hardcoded literals, with the
## producing suite never executed by any test or CI run (32 green runs prove nothing it claims)

- Baselines are literals (`avg = 412.0`), the "PBFT" control sleeps 412 MICROseconds (1000x sign of
  magnitude error, self-contradictory struct fields), ML comparator admitted `0.0 // TODO` in source but
  reported ✅ VALIDATED in docs, "100% detection" = one deterministic call printed 1000x.
- Structural: `grep benchmark tests/ | wc -l` == 0. CI runs `cargo test` and exercises NONE of the code
  that produced the published numbers. Mutation testing is structurally impossible — you cannot turn red a
  suite that is never called.

### Classification vs our live assets
- **CORROBORATE (class, not instance)** — the never-executed-producer class is the exact target of our
  RC-1 mandatory-repro rule and RC-1b dead-branch census (QG1c radians was our live instance). Our defenses
  held: every RESULTS booking since 2026-09-30 has a committed-script repro (newest: W5B2-REPRO, graded
  REPRO-SOFT honestly). No booked quilt-gpu-lab verdict is produced by an uncalled suite.
- **TOOL (raise priority)** — CI-1 (SCOUT-25 spawn, still open) is the direct hole-closer: quilt-gpu-lab
  has NO workflows at all; if our suite were ever to stop calling the booking scripts, nothing would go
  red. **CI-1 priority RAISED.** Fold in: (a) witness-complex dead-`.gitignore` byte-check (`git check-ignore`
  probe — literal `\n` rule matched nothing, 378 tracked build artifacts, 3rd fleet instance); (b) canons
  failopen-CI census class (81 test-runner failopen).
- **spawned HB-1 hardcoded-literal / degenerate-statistic sweep** (CPU ~20m): for every BOOKED verdict's
  producing script, grep numeric literals equal to the booked headline value or any expected-outcome
  constant; separately flag any booked gate statistic that is saturated/degenerate-by-construction
  (∞ ratio, detector always-firing, tautological identity) counted toward a PASS. Gates pre-registered in
  the run doc before firing. Threat named: a 412.0-style literal in one of OUR booking scripts would be a
  fabricated receipt under our own seal.
- **CORROBORATE (beta-test-elena, the fleet's only published falsification — 2/5 laws pass)**: Law 4
  "population > individual" is a TAUTOLOGY (sum of individual fitnesses); Law 2 passes only degenerately
  (∞ avoidance ratio from zero engagement). Maps 1:1 onto our DEGENERATE gate verdict item (murmmuration
  steal): a claim satisfied by a degenerate case has not been demonstrated. Uncomfortable footnote: that
  repo's own CI is RED (fmt/test/clippy failing) — the fleet's best falsification is its least maintained.

## Other state changes (window since SCOUT-25)
- **CORROBORATE**: dungeon-jev v2 — seal-before-run (9bf60d01) + honest P1 FAIL (JEV seat never fired
  in-budget, receipted per-tick); pre-reg doctrine holding fleet-side. jev-quilt 57th wipe: 0 drift
  alarms → QC-JEV booking untouched. receiptd 12ccb2c twin notary (i2i second witness) — RC-4 spec
  amendment (already spawned by SCOUT-25) unchanged, no new ask. quilt-jepa round-11 registration sealed
  PRE-RUN with pre-run correction disclosed (label fix only) — seal-integrity discipline, mirrors our
  pre-reg convention; nothing to steal beyond what RC-4 covers.
- **TOOL**: fleet-triage 0537439 REAL-PROBE — "the real rasterizer, running headless, agrees with the
  reimplementation" — same shape as our W5B2-REPRO (reimplementation validated against the real producer
  before any claim rides on it). No new instrument.
- PRs: only NEW = fleet-triage #5 (docs: edge-watch, mavis-workspace synergy). [EMBASSY] none new;
  pong-quilt #49 still unresponded (Casey day item, unchanged).

## CONTRADICT
- **None this sweep.** QO2 routing stack (QO1 oracle + QG3/QG6 triage + QO6 eproc), DECIDE-1 post-mortem
  and DECIDE-2, receipt-manifest doctrine, QG3+QG6 time-law, QG1c swap-convention census, edge-mine seeds
  W5a/W5b/W5c — all unthreatened. Nearest miss: holonomy's class would have implicated our pre-RC-1
  bookings had we not found QG1c's radians when we did.

## Spawned / raised
- [spawned by SCOUT-26] **HB-1** (CPU ~20m): hardcoded-literal + degenerate-statistic sweep over booked
  verdicts (see above). Scope: all RESULTS.md bookings with committed scripts (RC-1 list), 4-recent-first.
- CI-1 **priority RAISED** (3rd witness of the ungated-repo class; scope amended with check-ignore probe).
- No new GPU items; GPU free for QG4/QG1d/MC-1 next wake.
