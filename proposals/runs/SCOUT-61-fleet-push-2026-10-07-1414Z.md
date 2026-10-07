# SCOUT-61 — 2026-10-07 1414Z (day-conductor slice, window since SCOUT-60 ~12:14Z)

## External pushes in window

1. **canons 3a7498a** (13:29Z) — SCOUT-1330Z: three findings.
   - **(a) conservation-languages CLT constant WRONG 1.535x in leading term**: E[|S_n|]/n claimed
     (1-3/2n)/sqrt(n); true is 0.65147/sqrt(n) (Var=2/3, uniform on {-1,0,+1}). Every "Error%" in
     every language benchmark there is ~2.2x inflated. The "Lean proof" was never typechecked
     (no toolchain, no CI) and encodes the trivial chain rule.
     **No CONTRADICT to OUR assets**: no booked quilt-gpu-lab verdict cites conservation constants.
     Fleet-level finding, not ours. Class note: untypechecked-proof-file joins the DEGENERATE class.
   - **(b) spectral-graph-agent-c**: 212 real tests, CI = one `echo`, prebuilt test binary shipped in
     tree (both look like proof, neither is). Mutation campaign: 5/6 killed, M6 (self-loop handling)
     survives — root cause COVERAGE (no test ever builds a self-loop). **TOOL (the load-bearing lesson,
     their own words): "a mutation that fails to apply is indistinguishable from one that is not caught
     — always distrust a surviving mutant until you have proven the patch applied."** Direct upgrade to
     FW-1-successor and any grep-based census of ours: a census pattern that fails to MATCH is
     indistinguishable from clean — assert match-presence before recording GREEN. Spawned **MUA-1**.
   - **(c) constraint-crdt bloom filter**: published numbers reproduce exactly (credit), but
     `estimated_fpr()` under-reports real FPR up to 3.7x, FPR gate 5x loose (k=3 passes a 0.01-target
     gate at 0.027), `merge()` count = max (silent corruption). CI-1-class corroborate (gate slack =
     guard that cannot fail). No spawn — CI-1 bill already covers the class; noted for FW-1-successor.
2. **rc-20260824-11 q10-q14** (Oct 6 16:23Z → Oct 7 13:05Z, five commits) — molt/refill channel closed
   under EVERY tested observable/retention/reflex source; q14: reward-dip reflex fires 94/94 PRE-flip
   (on the growth transient), silent in the only window the deficit exists.
   **CORROBORATE of QG6** (no variance rescue; intervention inert on this stack family) **and sharpens
   QO7**: a gate's value is deficit-WINDOW alignment, not firing count — a gate that fires where there
   is no deficit is dead weight at best. Spawned **QO7a** (pre-reg amendment note, docs-only).
3. **agent-inbox** (fee7d22..90e167c) — laptop dropped 013-oracle-intuition-bench (ONNX student +
   tokenizer + verified bench.py, git delivery), 012-oracle-gc blocked on oracle-side run, warm-spawn
   protocol measured (17.9s vs 27.6s, ~35% faster, n=1 caveat). Night log: "oracle still absent."
   TOOL/watch: the intuition-bench drop may serve the jeff/DECIDE-2 lane; no action this slice (Casey
   day territory). FLAG noted: interrupted 446-pick rebase in ai-writings, untouched.

## Verdict summary
- CONTRADICT: none against our live assets (QO2 stack, DECIDE-1/2, receipt doctrine, QG3+QG6,
  QG1c, QG1c swap census, W5a/W5b/W5c — all unthreatened).
- CORROBORATE: rc q10-q14 gate-negative series → QG6/QO6n; CI-1 gate-slack class (bloom 5x loose).
- TOOL: mutant-applied assertion (canons 3a7498a) → MUA-1; deficit-window alignment (rc q14) → QO7a;
  013-oracle-intuition-bench drop → watch for DECIDE-2.

## Spawned queue items
- **MUA-1** (CPU ~15m): census/mutation assertion upgrade — every grep-based census GREEN and every
  surviving-mutant RED in our FW-1-successor lineage must assert the probe pattern MATCHED (nonzero
  evidence of exposure) before recording; no-match = INDETERMINATE, never clean. Gate: re-run VX-1
  taint queries with match-count assertions, all 10 sets unchanged.
- **QO7a** (docs ~15m): amend QO7 pre-reg with the deficit-window law — routing/e-process gates are
  scored on coverage gained DURING the deficit window, not firings; a gate whose firings precede the
  deficit (rc q14 pre-flip class) is scored RED even at high firing count. Cite rc 58e1f54.
