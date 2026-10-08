# SCOUT-74 — fleet push sweep, window 2026-10-08T14:15Z → 2026-10-08T17:11Z (fired 17:15Z)

Conductor: day cron, (A) slot per rotation (last: B 08:2x HSA-1b epoch snapshot fired; C repro re-verified this slice).

## Window pushes (gh api per-repo commits since 14:10Z, read-only)
- **rc-20260824-11** 9d041d9 17:06Z — **q21 anticipation-horizon sweep PASS**: H∈{3,5,8,12,16}, savings
  monotone 8.5%→58.0%, coverage drops ALL ≤1.0pp (noise); mechanism = larger H arms earlier + the
  resume-on-coverage-break clause (not the horizon) protects the ~85% re-armed-without-flip dwells
  (q17 recall 0.150); real bound is DWELL. exo contrast at H=16 arms 0 times — "anticipation free only
  when the universe answers back" reproduced. Opens q22: H→DWELL limit case, saturate or invert?
- **quilt-research-canons** 76020e4 16:33Z — scout 1625Z gems:
  1. **quilt-murmur ★ the find**: 28 experiments, receipt/FNV chain CI properly RED under chain mutation,
     BUT 9/28 experiments (incl. e17 gossip-trust, the interesting claims) have NO hard-fail exit —
     Hedge `eta*r→0` mutation inverted the scientific verdict (SOURCE_BEATS_ECHO 23/24 → ECHO_STEALS_TRUST
     0/24) and E17 still exited 0. "The tree of experiments is *measurement*, not *gate*."
  2. Census re-derived: **5,202 public repos** (821 forks), 47 prior scouts leave 1,824 unexamined
     (brief's 5,113 stale) — RC-2 counting-base note.
  3. `charCodeAt` FNV cannot reproduce the fleet canary — AL-1 dialect-table corroboration (3rd instance).
- All other watched repos: quiet. No open PRs anywhere swept. No new issues in window.
- [EMBASSY] pong #49 still open / 7 comments (SCOUT-73's "appears resolved" was premature — title/lead
  unchanged; stays Casey day-item).

## FINDINGS + CLASSIFY (CONTRADICT COUNT: ZERO)
### 1. rc q21 — CORROBORATE + TOOL → spawned **ENDO-1c**
The anticipation-horizon is the load-bearing parameter of any plateau-anticipation gate; q18's fixed H=5
left 4.7× savings on the table, and the protective mechanism is the observable resume clause, not the
window length. Maps directly onto ENDO-1/ENDO-1b (probe-derived thresholds, graceful-degradation gate)
and our QO7 cost matrix.
**ENDO-1c** (docs amendment to proposals/runs/ENDO-1-endogenous-flip-prereg-amendment.md, CPU ~10m):
add a horizon-sensitivity row to QO7's future pre-reg — any anticipation/dwell gate MUST (a) sweep the
arming window H and report savings-vs-coverage monotonicity, (b) declare the resume/un-arm clause as a
first-class gate component, (c) report the H→DWELL limit case (q22 watch). Gate in words: PASS if the
law holds at every H within noise; RED if savings invert before H=DWELL (that would mean the clause is
hiding cost, not anticipation). No booked result of ours threatened.

### 2. quilt-murmur inverted-science-ungated — CORROBORATE (CI-1/RC-1b class, measurement-not-gate) → spawned **EXIT-1**
Strongest fleet instance yet of the DEGENERATE class: chain verification genuinely fails-closed while the
experiments themselves exit 0 under verdict-inverting mutations. Our CI-1 workflow gates pytest fail-closed,
but we have never verified that every BOOKING script exits nonzero on its own verdict-FAIL branch.
**EXIT-1** (CPU ~20m, pre-reg first): census every booked-verdict-producing script in this repo; for each,
inspect/execute the fail branch (or a minimal mutation-harness dry check where a full run is too costly —
declare method per script); RED = a script that prints a FAIL verdict but exits 0, or has no exercised
fail branch. Known-good candidates: DECIDE-1 G2 FAIL booked with explicit STOP (check its exit path),
QO6t RED, DETERM-1 G2 FAIL. If all GREEN, the finding becomes a doctrine line: "verdicts book failures
as data; exit codes stay for harness death" — but that must be shown, not assumed.

No CONTRADICT: QO2 routing stack, DECIDE-1/2, receipt-manifest doctrine, QG3+QG6 time-law, QG1c,
W5a/W5b/W5c, ENDO-1 rows all unthreatened.
