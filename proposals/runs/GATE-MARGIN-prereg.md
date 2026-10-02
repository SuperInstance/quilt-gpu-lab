# GATE-MARGIN — off-by-one / relative-margin audit of committed booking gates (CPU, read-only + 1 recompute)

Spawned by SCOUT-19 (2026-10-02 0711Z): breakthrough-prospector f0034fd booked a false pass from a
relative-margin off-by-one (`x*k` vs `x*(1+k)`). SYN-1 (vacuous gate) folded in per spool note.

## Question
Do any COMMITTED gate expressions behind BOOKED verdicts contain (a) relative-margin arithmetic of the
`x*k` vs `x*(1+k)` class, (b) threshold-direction or boundary-inclusion errors (`>` vs `>=`, wrong
comparison operand), or (c) vacuity — a gate that would pass under its own null (missing control arm,
bar below seed noise)?

## Scope (booked gate sites, from RESULTS.md bookings)
1. `experiments/comp2_itemlocal.py` — `gate()` (line ~168: `>=` bar / `> 0`), G_IL1, G_IL2 (+0.05 bar), G_IL2b; `route_margin` majority rule; chance baseline `+ 0.02` filter.
2. QO1/QO3 oracle scripts — AUC comparisons vs baseline; CP95 interval construction.
3. QG6 — `delta_lb` significance (lower bound vs 0; direction).
4. DECIDE-1..1d — accuracy vs chance bars (0.25/0.125), consistency counts.
5. Grep-all pass: every committed `experiments/` + `tools/` file searched for relative-margin patterns
   (`\*\s*\(?\s*1\s*\+`, `\* k`, `/\s*\(?\s*1\s*[-+]`), boundary operators adjacent to booked bars,
   and any gate lacking a null/control arm in the same script.

## Gates (pre-registered, words)
- G1: every booked gate expression is manually re-read against its prereg wording; verdict per site:
  CLEAN / BUG (with the exact line + what it would have changed in the booked result).
- G2: recompute check — comp2 `gate()` re-derived independently (bootstrap diff CI on committed
  il_results.json predictions subset) reproduces G_IL2 (+0.0022 FAIL) and G_IL2b (+0.1045 PASS)
  verdicts; boundary case `diff == bar` classified exactly as the committed code classifies it.
- G3: vacuity census — each booked gate names the null arm or chance bar it is measured against;
  any gate with no null is RED (SYN-1).
- STOP rule: any G1 BUG that flips a booked verdict -> amend the booking in place (never silently),
  mark affected results, and stop the slice; no re-runs this wake.

## Cost
CPU-only, ~15 min; zero GPU-Wh; read-only except RESULTS/spool/this prereg.
