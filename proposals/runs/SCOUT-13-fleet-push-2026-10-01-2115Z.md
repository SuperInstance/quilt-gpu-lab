# SCOUT-13 — SuperInstance push sweep (day-conductor, 2026-10-01 21:15Z)

Sweep: 16 repos by recency, commits since 2026-09-30 + open PRs. Read-only, no comments/PRs filed.
State delta vs SCOUT-12 (12:1x, ~6h ago): fleet-triage megapush, quilt-tools edges #16/#17,
jev-quilt round 49, pong PRs #89-#92, canons vacuous-gates scout. GPU lane occupied by a foreign
local run (si-arena kimi/poc run_poc.py, elephant-gpu python, PID 1740249 from 13:09 local) — no
GPU item this slice per serial-lane law.

## Classifications

1. **CORROBORATE — fleet-triage experiments/synergy (b42c5dc, 20:35Z).** Their results.json:
   "detection_power originally returned the base rate, not recall" (recall_mean 0.0 as measured),
   fail-open harness 11/13 sharing one bug → one-rule fix → recall 1.0, grouped-vs-random split
   memorisation gap 0.225 (real experiment gap 0.454), n_eff/k 0.128. This is the THIRD independent
   instance of the DEGENERATE-gate / vacuous-statistic class (murmuration std==0 rule; F1 G1
   degenerate pass; W5a saturation; now their base-rate-as-recall). Their fail-open→fail-closed
   one-rule fix is exactly our RC-3/DEGENERATE ask. Also: grouped-split gap quantifies the
   stream-vs-lane stratification concern QO9 pre-registers.
2. **TOOL — fleet-triage BOARD + D1 (14af90b/8adc5c5/b4c76fc).** 38 reports unified by a dependency
   graph; 44 edge databases read directly (467 tables, 26 non-empty, 18 inaccessible); the resolver
   census is being turned into fleet infrastructure. We should CONSUME the BOARD instead of re-sweeping
   raw pushes, and check whether quilt-gpu-lab's receipts appear in their D1 census (RC-2 completeness
   fields would make us machine-readable to it).
3. **CHECK — canons SCOUT-1942Z "vacuous gates + canary repo teaches the trap" (ac27cbb).** Need the
   full read, but the title lands on our DEGENERATE-gate-verdict item (still open). If their trap
   class matches, that item's priority RAISES; if they propose a gate form, it feeds the spec.
4. **RAISE — jev-quilt round 49 (bf27bce, 21:05Z): q10 0.86, 3rd round ≥0.85, q14 damped.** The
   round-to-round drift flagged at SCOUT-12 is now a 3-round pattern. Our QC-JEV pin (p_true
   0.9606/0.0243) is a single-round draw. **QC-JEV3 (drift re-probe of jeff-0.8b, CPU ~10m) priority
   RAISED** — cheap, and it protects the QC-JEV booking that DECIDE-2's premise stands on.
5. **CORROBORATE — quilt-tools PR#34 (edges #16+#17, resolver census pair VERIFIED)** — the referral
   resolver is becoming load-bearing; RP-1 (bare-basename lint over our receipt citations) unchanged,
   still open.
6. **Quiet:** micrograd-quilt (zero commits since 09-30), MicroMoth (overnight artifact sync only),
   percept-plugs/xruntime/murmuration/delta-shape/syzygy/subleq/ewitness (no new pushes since last
   sweep), pong #89-#92 (Casey-lane rounds; #92 open with honesty pins — their scaling-trajectory tool
   is a possible steal for QG4's phase-diagram output format, noted, no new item).
7. **FICTION-COMPACTION.md (f7d6071)** — a narrative instrument about what an agent loses when tools
   become invisible ("the diff is the worst possible surviving artifact: complete about what, empty
   about why"). Not a measurement; classify as CULTURE/DOCTRINE. The actionable kernel for us: our
   receipts carry verdicts and gates but rarely the *question behind the number* — one sentence of
   "why this gate" per pre-reg is cheap insurance. Folded into ST-STEEL's spec (no new item).

## Queue items spawned

- [ ] **SYN-1** (CPU ~30m, spawned by synergy results): gate-statistic base-rate audit — for every
  committed gate function in our experiments (QO6 V1-V4, QG7 P1/P2, W5b gates, FT-A1 P1/P2), assert
  the statistic is NOT recoverable from the class base rate alone (their "detection_power returned
  the base rate" instance). Pre-register the audit list before running; any gate found vacuous →
  mark the booking it supports for re-read (CONTRADICT-class finding against that booking, not silent
  amend).
- [ ] **D1-CENSUS** (CPU ~15m): pull fleet-triage D1's table census; find quilt-gpu-lab rows; if our
  receipts are absent/unreadable → RC-2 completeness fields become the fix and priority raises; if
  present, note what they ingest and stop duplicating raw sweeps (BOARD-consume path).
- [RAISED, existing] **QC-JEV3** (CPU ~10m): drift re-probe — run the QC-JEV 4-probe battery on 3
  fresh rounds against jeff-0.8b; gate: p_true spread < 0.05 across rounds keeps QC-JEV booking
  intact; wider spread → flag the booking and freeze DECIDE-2 until characterized.
- [FOLDED] ST-STEEL spec += "pre-regs carry one sentence naming the question behind each gate".
