# ENDO-1 / ENDO-1b — Endogenous-flip licensing law (pre-reg amendment for QO7)

Spawned: ENDO-1 by SCOUT-70 (2026-10-08 0620Z), ENDO-1b by SCOUT-72 (1111Z). Landed together
as one amendment by day-conductor slice (B) slot, 2026-10-08 ~04:2x AKDT. Docs-only; no run.

Source: SuperInstance rc-20260824-11 q15–q19 gate arc:
- q15 (3fd3116): reward-dip reflex gate FAIL on cost axis — spends during the growth transient,
  silent in the deficit window (11th consecutive gate negative).
- q16 (9743fcc): question-topology churn carries ZERO anticipatory signal under EXOGENOUS flips.
- q17 (eb5f041, first WIN): flips are ENDOGENOUS in their charter — coverage-dwell rule gives
  plateau-anticipation precision 0.667 vs placebo 0.000.
- q18 (dd46e9b): RELEASE gate on the alert saves 12.25% dice passes at ≤+0.17pp coverage;
  exogenous contrast arm never fires, zero savings. Law: *anticipation is free ONLY when the
  universe answers back.*
- q19 (993336a): win survives capacity scarcity 70→45 with the SAT threshold re-parameterized
  per regime from an observable plateau probe (probe tail-50 mean − 0.05; SAT must sit UNDER
  the plateau as scarcity drags it 0.665→0.552). Gate's fuel is plateau headroom; degrades
  gracefully (fewer, not worse, saves). Deterministic fnv1a, byte-identical replay.

## Amendment (applies when QO7's pre-reg is drafted; QO7 remains a Casey day-item)

QO7's routing/e-process gates (oracle kill/keep thresholds, budget triage, eproc gate) must
add the following rows on top of the QO7a deficit-window law:

1. **Flip-model declaration row (ENDO-1).** Every gate must declare the flip model of the
   universe it consumes evidence from: REACTIVE (endogenous flips — the lane's own dynamics
   carry the signal) or INDIFFERENT (exogenous flips — no observable channel is open).
   Under the rc q17/q18 law, anticipatory gating is licensed ONLY in the reactive regime;
   in the exogenous contrast arm the gate MUST never fire. Our QO6 eproc gate already
   consumes lane-internal evidence — it must declare REACTIVE and carry the contrast arm.

2. **Anti-economizer failure mode (rc q15).** A gate that spends during the growth transient
   is scored via the QO7a deficit-window rule (misaligned firing ⇒ RED dead-weight class).
   Pre-registered here so the failure mode is named before QO7 fires, not after.

3. **Per-regime threshold re-parameterization (ENDO-1b / q19).** Any gate threshold in the
   endogenous-flip lane must be derived from an OBSERVABLE PROBE and re-parameterized per
   regime — never a frozen constant across a regime change. The probe recipe (statistic,
   window, derivation) must be receipted in the pre-reg. Fleet instance of the same
   principle: our fitted-T temperature pin drifting out of range across regimes
   (QC-JEV balance-edit-lane flag) and QG6's nonstationarity handling.

4. **Graceful-degradation sweep gate (q19).** Gate quality criterion = graceful degradation:
   savings shrink monotonically, never invert, across a scarcity/parameter sweep (q19's
   70/60/52/45 ladder as the shape). A gate whose benefit inverts under scarcity is scored
   regime-brittle (honest RED), even if it passes at the nominal point.

5. **Contrast arm at every sweep point (q19 G2).** The exogenous contrast arm runs at EVERY
   sweep point, not just the nominal one: exo never fires ⇒ arms byte-identical ⇒ the
   anticipation law reproduces. Any exo firing anywhere in the sweep falsifies the
   endogenous-source claim.

6. **Horizon-sensitivity sweep row (ENDO-1c, rc q21).** Any anticipation/dwell gate MUST
   (a) sweep the arming window H (q21's {3,5,8,12,16} shape) and report savings-vs-coverage
   monotonicity across it — a single-H win leaves arbitrary savings on the table (q18's fixed
   H=5 vs 58% at H=16); (b) declare the resume/un-arm clause as a FIRST-CLASS gate component
   (q21's protector is the resume-on-coverage-break clause, not the window length); (c) report
   the H→DWELL limit case (q22 watch: saturate or invert).

## Gates in words (pre-registered for any future QO7 instrument fire)

- **G1**: the endogenous-lane probe is observable from lane data alone and its recipe is
  receipted in the pre-reg (statistic + window + derivation, fnv1a-class deterministic).
- **G2**: the scarcity/parameter sweep shows graceful degradation — benefit shrinks,
  never inverts. Inversion at any point ⇒ verdict REGIME-BRITTLE, booked honestly.
- **G3**: exogenous contrast arms are byte-identical to no-gate at every sweep point.
  Any exo firing ⇒ RED on the endogenous-source claim.
- **G5** (ENDO-1c): the law holds at every swept H within coverage noise (≤1.0pp-class); the
  resume clause is receipted as the protective mechanism; H→DWELL limit reported. RED if savings
  INVERT before H=DWELL — that means the clause is hiding cost, not anticipation.
- **G4** (inherited, QO7a): scoring is on aligned coverage gained inside the deficit
  window, never on firing count.

## Mapping to our assets (no booked result threatened)

- QO6/QO6h/QO6s eproc gate: gains the declaration row (REACTIVE) + contrast-arm duty.
- QO7a deficit-window law: rows 2/4/5 compose with it; this file does not supersede it.
- QG6 time-law + QG7 ensemble law: regime-dependence of thresholds is consistent with
  the subpopulation/ensemble lessons; no amendment needed there.
- DIFFPORT-1/RT-D1 doctrine: the contrast-arm duty is a special case of the real-vs-repro
  real-probe arm (the exo arm IS the real-probe for an anticipation claim).

Cite: rc 3fd3116, 9743fcc, eb5f041, dd46e9b, 993336a, 9d041d9 (q21); SCOUT-70 + SCOUT-72 +
SCOUT-74 full notes; proposals/runs/QO7a-deficit-window-prereg-amendment.md.
