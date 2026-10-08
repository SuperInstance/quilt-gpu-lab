# SCOUT-76 — fleet push sweep, window 2026-10-08T18:11Z → 2026-10-08T20:14Z (fired 20:14Z)

Conductor: day cron, (A) slot per rotation (last: B ENDO-1c 11:1x; A SCOUT-75 before that).
Sweep: per-repo commits since 18:11Z across the 14 watched repos. One external push in window.

## Window pushes
- **quilt-research-canons 2847865** (19:29Z): SCOUT-2026-10-08T1930Z — fail-open CI taxonomy +
  five repos dissected. Full classification below. No other repo pushed. taskable-lobster still 404
  (renamed/gone — RC-2 census drift note stands).
- Open PRs: dependabot-only trains (quilt-rag #16-#19, quilt-fleet #21-#23, quilt-elf #13,
  quilt-pincher #22-#25). Routine. No new/updated issues in window. [EMBASSY] pong #49 unchanged
  (Casey day item, untouched).

## CLASSIFY: CONTRADICT COUNT: ZERO
QO2 stack, ENDO-1/1b/1c, EXIT-1, HSA-1b, DETERM-1, receipt doctrine, QG3+QG6, W5a/b/c all unthreatened.

## Findings (canons 2847865, five repos + census)

1. **flux-policy-tester — self-audit certified its own fix; the fix is unreachable code.**
   ISHR sign-bit fix guards `val < 0`, but RegisterFile stores `& 0xFFFFFFFF` so the branch can
   never fire (372/672 (value,shift) pairs wrong). Audit doc says 44/44; branch CI red since
   2026-07-20. → **CORROBORATE (FW-1/RC-1b class, self-audit flavor):** an audit that says
   "fixed + tests added" without a mutation check on the fix itself has this shape. Our mandatory
   (C) committed-repro + verdict_gate is the counter-instrument; no booked result of ours is
   audit-by-prose. Note filed for FW-1-successor: add a "fix-reachability" row (guard condition
   vs the type invariant of the storage it reads).

2. **arm-neon-eisenstein-bench — `|| true` CI + tautological NEON test + README-vs-source x3.**
   `norm_neon` dual-dispatches to `norm_scalar` on x86; CI asserts scalar==scalar; the aarch64
   asm is never compiled on the runner. → **CORROBORATE (CI-1/RC-1b).** Steal the generalized
   question for any cross-runtime claim of ours (incl. GPU lanes): **"which architecture does the
   runner actually have?"** — cheap sanity row for INSTRUMENT-01 receipts.

3. **vetcheck — positive control, then CI-laundried.** Found the fleet's `all([])` vacuous-pass
   bug, fixed it, mutation-verified (26/28 mutated → 28/28 restored)… and then `pytest || true`
   converts that known-red-capable suite to unconditional green. → **CORROBORATE + doctrine
   sharpening for CI-1:** the taxonomy (canons finding 6): red-honest badge = information;
   `|| true` badge = anti-information (converts red to green); tautological-green = no signal
   wearing green. A `|| true` is worse than no CI at all. Amend CI-1 receipt with the three-shape
   table (docs-only).

4. **fastloop-guard — network-supplied `threshold`, zero validation → confused-deputy gate.**
   `threshold=0.0` makes the similarity gate return ANOTHER query's cached response for any query;
   NaN accidentally safe. Their own essay calls it "the last line of defense before GPU dispatch."
   → **TOOL, spawned PARAM-1 (CPU ~20m, pre-reg first):** census every numeric parameter feeding a
   gate/verdict branch in OUR instruments (eproc sigma + budget, DETERM-1 eps, verdict_gate
   thresholds, degrade-gate sweep params, exit-gate-witness, proj_lattice dialect table) — for
   each: source (hardcoded/config/env/network-adjacent), validation present?, boundary behavior at
   0.0 / negative / NaN / out-of-domain. Gate = at least one RED-first instance found and fixed
   fail-loud, or explicit all-valid GREEN table. Rationale: our gates are loading parameters from
   result JSONs and CLI args constantly; fastloop-guard shows the inversion shape.

5. **conservation-guardian — surviving boundary mutation (`>` vs `>=` on daily cap, 83/83 GREEN).**
   Only test sits 4 orders of magnitude past the boundary. → **CORROBORATE (assertion-branch
   coverage class, already a FW-1-successor row).** No new item.

6. **Census:** 5,202 repos / 53pp (grew from 5,113); 3,659 unseen. RC-2 drift note only.

## Spawned
- **PARAM-1** (CPU ~20m, pre-reg first) — gate-parameter validation census per finding 4.
- **CI-1-AMEND** (docs-only, fold into next docs landing) — three-shape badge taxonomy +
  fix-reachability row + runner-arch question, citing canons 2847865.

## Cost
~12 min CPU, 0 GPU. No 429s. No running processes; nothing duplicated. Foreign d12 untracked lane
persists (PW-1, untouched).
