# DEL-1 — Sufficiency-by-deletion audit over the QO2 routing stack

Spawned by SCOUT-38 (fleet-triage f173e16 sufficiency-by-deletion on quilt-cell-harness:
`witness_compartment` proved DECORATIVE — cell reports itself alive without passing through it).
Class: RC-1b decorative-path, found DYNAMICALLY. Our FW-1 census (9/9 GREEN) was a
write-site census; DEL-1 is the deletion complement: **does any QO2 component/branch fail to
matter to the verdict it cites?** A decorative component on a citing booking = RED.

## Components under audit (QO2 stack: QO1 oracle + QG3/QG6 triage + QO6 eproc gate + gen-1 router)
- C1 `tools/eproc.py::kill_gate` retraction semantics (QO6 V1-V4 ALL PASS booking)
- C2 `eprocess` mu-mixture (K=8 grid) — vs single-mu ablation
- C3 witness refusal contract (sigma REQUIRED, series length, finiteness) — QO6 V1c pins
- C4 QO1 oracle forecast role (QO3 horizon booking AUC 0.500→0.880→…; QG7 ensemble P1/P2)

## Pre-registered deletion probes (deterministic, CPU, ~5 min)
- **D1 delete-retraction**: patch kill_gate to a non-retractable predicate (once E_max≥bar →
  KILL_CANDIDATE forever, p-value-in-disguise class). PREDICTION: V2 flips KEEP→KILL_CANDIDATE
  (late bloomer wrongly killed), V3/V4 unchanged, V1 pins unaffected. If V2 does NOT flip,
  retraction is decorative in the booked evidence → RED on the QO6 booking.
- **D2 delete-mixture**: replace K=8 mu-grid with single mu=0.2σ and re-run the V1b/V2/V3/V4
  behavioral pins. PREDICTION: verdicts survive (mixture sharpens E magnitude, not direction);
  if any verdict flips, mixture is load-bearing for the booking — record which.
- **D3 delete-sigma-contract**: replace REQUIRED sigma with silent default (std of the series)
  and re-run V1b flat_noise. PREDICTION: a self-referential sigma can flip flat noise toward
  WITNESSED or materially move E_max — refusal contract load-bearing; if flat_noise still
  NOT_WITNESSED with similar E_max, contract guards are formally pinned but not
  outcome-differentiating on the pinned case (record, not RED — V1c pins the refusals directly).
- **D4 oracle-deletion (citation-level, no GPU)**: cite booked numbers — replace oracle scores
  with chance (AUC 0.5): QO3 gen-1 routing signal 0.880→0.500, QG7 P2 frozen-oracle 0.566-0.581
  → 0.5. Verdicts change ⇒ non-decorative by inspection; no new run needed (QG7b repro PASS
  already anchors determinism).

## Gates (frozen before firing)
- Any probe whose booked-verdict outcome is UNCHANGED where the component is claimed
  load-bearing (D1 prediction is a flip; if no flip) → **RED**, spawns an amendment on the
  citing booking (QO6).
- D2/D3 outcomes are recorded as decorative-scope notes (pin-level vs outcome-level) and feed
  FW-1 successor scope; they cannot RED the QO6 booking (mixture/sigma contract are separately
  pinned by V1 parity + V1c).
- GPU: none. Lane stays with the foreign portal process (PW-1).
- Cost: ~5 min CPU, deterministic; results to `results/del1_deletion_audit/`.
