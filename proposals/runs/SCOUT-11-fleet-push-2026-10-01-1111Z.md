# SCOUT-11 — SuperInstance fleet push, 2026-10-01 11:11–11:2x UTC (03:11 AKDT)

Sweep: `/users/SuperInstance/events` (user account, not org) + targeted reads. Window: since SCOUT-10 (~06:11Z).
No live local work duplicated (ps checked: no experiment processes; GPU idle). No repro due (CM1-r5 repro PASS
01:1x; FT-1b analysis-only). CONTRADICT count: **zero** — nothing this sweep threatens a booked result.

## Pushes since 06:11Z (state changes)
- **taps-creative-break** — NEW repo 09:13Z, pushes 10:22Z/11:06Z. Casey-adjacent creative-break loop
  (wipe-durable mirror, Python, session logs). Not our lane, no overlap. Watched, no action.
- **quilt-atlas** 10:56Z — wave-76 MECHANICAL-LEARNING M3 (see FIND #2).
- **quilt-research-canons** 10:30Z — scout report (see FIND #3).
- **chiaroscuro** — PR #10 (09:32Z) + PR #11 (10:25Z) honest-FAIL receipts (see FIND #1).
- Projectionist 03:32Z, quilt-canvas-tui 03:35Z — pre-window/Casey lanes, unchanged.

## FIND #1 — chiaroscuro PRs #10/#11 (CORROBORATE; methodological steal)
Two more honest-FAIL run receipts, sealed-spec-first, v1/v2 FAILs left standing, no goalpost moves.
- PR #10 (kc_geo): G2 FAILED on a **spec math bug** — claimed analytic worst-case 30°, true bound is
  arcsin(ρ)=35.26° at ρ=tan30°; measured 33.76° is inside the TRUE bound. They recorded the spec error
  in the receipt and did NOT silently re-gate. Steal: **analytic-bound reconciliation step** — when a gate
  derives from a claimed analytic bound, re-derive the bound inside the runner (we have no such runner-side
  check; our analog failures were wrong constants in committed scripts, found only on repro).
- PR #11 (CAST v3): verdict **FAIL honestly applied** — the intended feature (L4 vocab expansion) collided
  with the sealed anti-drift gate; v3 NOT merged; decision deferred to a v4 spec with a fresh unseen set.
  Clean handling of "feature works, gate says no" — corroborates our STOP-rule doctrine.
Threats: none (no overlap with our bookings).

## FIND #2 — quilt-atlas wave-76 M3 "evidence-gated commitment" (CORROBORATE + STEAL, highest value)
wave-76: every commitment receipt must CITE its admission evidence (dbar_at_gate, threshold, lattice_max,
delta_frac) and is replay-verifiable. Plus their headline: **R1 registered point was VACUOUS — PASS at a
measurement point where the baseline is trivially 0.0** (eligibility floor already gated it), booked as
"PASS — but vacuous", verdicts re-read at a live tick instead.
- CORROBORATE: vacuous-pass shape = our DEGENERATE gate class (F1 G1 degenerate pass, QO5 g0, W5a saturation)
  and the murmuration std==0 steal. Third independent witness; 4th counting atlas-72k.
- STEAL (concrete): **QO6 kill/keep receipts should embed admission evidence inline** — our eproc gate
  (QO6, lineage 61b9e04/aad90ac5) books verdicts but the evidence tuple {stat, threshold, sigma, n} at
  decision time should ride INSIDE the receipt row, replay-verifiable without re-running. Spawned **QO6-EV**.
- Their R5 shape (gate suppressed 36% of receipts; 1,444-1,466 of blocked would-have-emitted = counterfactual
  accounting) is a nice template for QO7's budget scoreboard (streams saved vs wasted) — note for QO7 spec.

## FIND #3 — canons scout 10:30Z (CONSUME)
Their latest report flags: judge_gate 2/3 mutations with a **truncation blind spot**; quilt-jepa **mtime
seal unverifiable in clone**; erised-mirror 75/75 claimed vs 0/15 runnable; canary canonical source verified.
- Truncation blind spot = the "pipeline ending in tail reports last command's exit code" shape (CONVERGENCE.md
  shape 3 = our 09:1x tmpfs incident). Widened DEGENERATE-gate spec: **a verdict extracted from output must
  assert output completeness** (spawned **TRUNC-B**, folds into the DEGENERATE gate item).
- mtime-seal finding: checked OUR receipt layer — seals are sha256-content-based (manifest digest, 149 exp /
  22 tool files), no mtime dependency; clone-safe. No action.
- Nothing touching quilt-gpu-lab this report; our receipt layer stays green (mutation-verified 3/3 at 04:23Z).

## EMBASSY / Casey day items (unchanged)
- pong-quilt #49 still unresponded (erised-mirror stranger-verification of r37 stone-v1 chain).

## SPAWNED QUEUE ITEMS (concrete)
- **QO6-EV** (CPU ~30m): extend QO6 eproc receipt rows with inline admission evidence
  {stat, threshold, sigma, n, seed} at decision time + a replay-verifier that re-derives each row's
  verdict from its embedded evidence alone (atlas wave-76 R5 receipt shape). Tool/contract change —
  pin gates in the pre-reg: existing QO6 V1-V4 cases must re-derive identical verdicts from evidence-only
  replay; any row lacking evidence is VOID. Improves: QO2 gate, QO7 scoreboard input.
- **TRUNC-B** (CPU ~10m, folds into DEGENERATE-gate spec): completeness assertion pin — any booking whose
  verdict is extracted from produced output (log tail, jsonl append, judge call) must ship a
  completeness/termination marker check; truncated-but-plausible output = INCONCLUSIVE, not PASS.
  Sources: canons judge_gate truncation blind spot; our 09:1x tmpfs tail incident.
- **AB-1** (low, reading ~15m): adopt chiaroscuro PR #10's analytic-bound re-derivation pattern for any
  future gate whose threshold derives from an analytic claim (arcsin-bound class). Note only until one
  of our gates actually has an analytic derivation to re-check.

## Classification summary
CORROBORATE: chiaroscuro honest-FAIL x2, atlas vacuous-pass, canons fail-first findings fleet-wide.
STEAL: QO6-EV evidence-in-receipt; TRUNC-B completeness pin; AB-1 analytic-bound pattern (noted).
CONTRADICT: none. TOOL: taps-creative-break watched, no action. canons mtime finding: verified N/A for us.
