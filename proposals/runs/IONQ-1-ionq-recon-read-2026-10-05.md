# IONQ-1 — MicroMoth IonQ recon read vs our booked assets (2026-10-05, ~02:1x AKDT)

Scope: read-only. Sources — SuperInstance/MicroMoth-quilt docs/IONQ-RECON.md (sealed RECON 2026-10-04),
PR #43 (rung-1 sim pre-flight, PREFLIGHT-PASS, 351/351) and PR #44 (rung-2 weight-algebra discriminators,
358/358), both OPEN, stacked. Spawned by SCOUT-42 (01:09 slice). No comments filed, no PRs touched.

## What they shipped
- **Rung 1** (2q): forbidden-sum discriminator P(01)+P(10) — classical clamped accumulator forbids it
  (0.0), coherent quantum gives 0.50. Sim pre-flight PASS at 6σ/200k shots. Elitzur–Vaidman structure
  noted (link exists with zero effect delivered — the qm_* registry has no such channel).
- **Rung 2** (2q): crx(θ) calibration sweep pins the bridge w = sin²(θ/2) across the full [0,1] weight
  range (exact 1.0 at π); additivity discriminator crx(π/3);crx(π/3) measured **0.7494** vs the
  qm_* accumulator's clamp01(¼+¼)=0.50 (~150σ apart); cancellation discriminator crx(π/3);crx(−π/3)
  measured **exact 0.0** vs the contract's best imitation 0.25 — "the algebraic hole made physical."
- Rung 3 (4–7q) is gated on rungs 1–2 and is the spend rung (wsum-vs-correlator, leak-vs-decoherence).

## Gate 1 — which of OUR booked results are simulator-backend-bound vs substrate-portable
**Simulator-backend-bound (pinned to qcell_sim conventions / torch statevector backend):**
- QG1c swap-convention census — the entire result is a statement ABOUT our simulator's convention
  (pi-units, b01↔b10 swap). A second native gate set (IonQ GPI/GPI2/ZZ, where swap is a decomposition,
  not a native) re-opens the question; the census method transfers, the verdict does not.
- QG1/QG2/QG3/QG6/QG7/QO1/QO3/QO5 — all measured on qcell_sim rollouts with its gate vocabulary and
  fitness = min(p000,p111). Portable in METHOD (oracle + eproc + rerun-ensemble doctrine), pinned in
  NUMBERS. Any hardware-era port must re-pin, per our own RT-D1 real-vs-repro doctrine.
- D12h/i/j weight law (W·T product) — likely structural (selection dynamics, not gate semantics) but
  measured under our mutation/fitness conventions; treat as convention-conditional until re-pinned.

**Substrate-portable (method/procedure results, not gate-semantics results):**
- Receipt-manifest doctrine + RC-3/RC-5/EP-1 seal census + VX-1 verdict index — conventions of
  bookkeeping, not physics.
- QO6 eproc retraction gate, QG7 ensemble law (subpopulation verdicts need ≥4 reruns), mur-muration
  DEGENERATE gate — procedural, substrate-independent.
- DECIDE-1 lineage / representation-locked argmin — different model entirely (jeff-0.8b), untouched.

## Gate 2 — can their weight-algebra discriminators stress our convention census?
**Yes, and cheaply.** Their rung-2 discriminators run on OUR side in seconds:
- qcell_sim has crx with angles in pi-units. θ ∈ {π/6, π/3, π/2, 2π/3, π} → their bridge predicts
  transfer sin²(θ/2) (i.e. sin²(θ·π/360) under our pi-unit convention — exactly the kind of unit
  mismatch QG1-residual caught in the census script). A qcell_sim run of the sweep is a second,
  independent check that OUR crx transfer convention matches the fleet-pinned bridge.
- Additivity (0.75) and cancellation (exact 0.0) are sharper still: cancellation is a bit-level
  amplitude-annihilation check — any statevector-convention error (ordering, endianness, sign) shows
  up as nonzero transfer, i.e. a QG1c-class witness for the crx line specifically (QG1c cleared
  swap-only; crx semantics were never independently stressed).
- The QG1c census METHOD (residual-miss Fisher vs convention variants) also extends: under IonQ-native
  ZZ decompositions, swap is synthesized, not native — a second-native-gate-set census would test
  whether the 28-miss convention story is our-simulator-specific or a deeper wire-order class.

## Verdict
- No CONTRADICT. Their sim pre-flights corroborate the falsification-first discipline and give us a
  free convention stressor. IONQ-RECON's EFFECT/HARDWARE-vs-SEALED receipt distinction (§3.3) is the
  RT-D1 real-probe doctrine re-derived independently — 2nd converging witness, note filed.
- Spawned **IONQ-2** (GPU-cheap, ~15m, pre-reg first): run the rung-2 discriminator battery on
  tools/qcell_sim.py — calibration sweep θ ∈ {π/6,π/3,π/2,2π/3,π} (gate: transfer = sin²(θ/2) within
  the fleet 6σ band at each point), additivity (gate: 0.75), cancellation (gate: EXACTLY 0 — any
  nonzero = new QG1c-class crx convention finding, book RED honestly). Anchors: qcell_sim balance
  convention = min(p000,p111), angles in pi-units, k4 champion 0.4268 selftest must hold.
- Routing note: IONQ-2 is a GPU-cheap CPU-class lane (small statevectors); can slot ahead of
  QG1d/QG4 in the GPU queue per the "stressor before new construction" ordering.
- [EMBASSY] none new this read. Hardware credits: not our lane, Casey day item if ever pursued.
