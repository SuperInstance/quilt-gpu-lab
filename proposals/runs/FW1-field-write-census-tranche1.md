# FW-1 FIELD-WRITE CENSUS — tranche 1 (QO10, QO6/eproc, QC-JEV)

Pre-registered BEFORE the audit was written down. Spawned by SCOUT-24 (fleet-triage 2353a14
retraction lesson: grep every write to every field a claim depends on BEFORE modelling it).
Uncovered write-path on a booked result = RED. QG1c radians was a live instance of this class.

## Census rule (per booking)
1. Enumerate the state fields the verdict function READS.
2. Grep every write site of those fields in the producing tool + its imports.
3. A write path not exercised by a committed test OR the verified repro run => RED for that booking.
4. Branches of the verdict function uncovered by BOTH test and repro are listed (RC-1b census),
   but only matter if they gate the booked verdict.

## Tranche 1 scope (newest 3 bookings with in-repo producing tools; ~20 min slice)

### QO10 — experiments/qo10_projection_ladder.py (booked 13:5x, repro PASS 14:4x)
- Verdict reads: ladder-arm AUC means, ensemble spread, G1 anchors vs embedded QO3 AUC
  constants, cv/gen-only std-0 degeneracy flags.
- Write sites: all internal (per-arm AUC lists built in-script; embedded anchor constants are
  literals, no external write path). results.json write is the known hardcoded-path defect
  (RC-1, 5th witness) — does not feed the verdict fields.
- Coverage: verdict-level repro PASS (14:4x) exercises the scoring path.
- **GREEN.**

### QO6 — tools/eproc.py kill_gate/witness (booked 05:5x, replicated then booked)
- Verdict reads: E trajectory (E_final/E_max), stop_t, retracted, sigma/delta.
- Write sites: log_acc/cumsum inside eprocess() — internal, DETERMINISTIC (numpy, no RNG).
- Coverage: booking was a deterministic replicate (ALL_PASS identical); sigma-refusal
  (honesty contract) exercised; retraction (KEEP via late evidence E 581) exercised in booking.
- RC-1b census note: the `claim="INCREASES"` arm of witness() is covered by NEITHER a test nor
  any booked run. It does not gate any booked verdict (QO6/QO7 are DECREASES-only) — recorded,
  not RED. Candidate for one test pin.
- **GREEN** (booking verdict path).

### QC-JEV — tools/decision_cell.py 4-probe control (booked 10:2x, repro verdict-level PASS 10:1x)
- Verdict reads: p_true on true/false arithmetic probes (d_ptrue), argmax choice on letter-fixed
  content-swap probes.
- Write sites: logits path internal; the noul-branch scalar bug was fixed in place pre-scoring
  (802bae1, committed). Hardcoded results/ output path (RC-1 class) noted — not verdict-feeding.
- Coverage: verdict + all gates reproduced 10:1x (honest: not byte-exact, _latency_ms varies).
- **GREEN.**

## VERDICT (tranche 1): 3/3 GREEN, zero RED. 1 uncovered-branch census entry (eproc INCREASES arm).
Tranche 2 (next FW-1 wake): D12i, W5b2, QG7 ensemble bookings (harder — GPU nondeterminism,
ensemble gates; the QG7 subpopulation lesson says ensemble reruns are the coverage instrument).
