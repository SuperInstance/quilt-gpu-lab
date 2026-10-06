# SCOUT-50 — SuperInstance push sweep (day conductor, 2026-10-06 06:1xZ / 22:1x AKDT Oct 5)

Window: since 2026-10-04T06:00Z with focus on post-SCOUT-49 (~2026-10-06T04:1xZ). Read-only gh API.
No new issues on quilt-gpu-lab (0 in window). No [EMBASSY] items observed in any swept commit.
No open foreign PRs against our assets. **No CONTRADICT this sweep** — QO2 routing stack, DECIDE-1/2,
receipt-manifest doctrine, QG3+QG6 time-law, QG1c, W5a/W5b/W5c all unthreatened.

## Fleet event (context, not a finding)
- Mass merge wave 21:05–21:09Z Oct 5: ONBOARDING fleet-seed-2026-10-06 + operation-fictions
  branches merged across ~10 repos (MicroMoth-quilt #46/#47 with import-baseline RESEALS,
  quilt-tools #53/#54, pong-quilt #119/#120, doubt-ledger #21/#22, fleet-witness #9/#10,
  constraint-theory-math #3/#4). Branch name says "stand-down 2026-10-06" — fleet-wide doc wave,
  handoff-flavored. Casey day item if action needed; noted, no local action.

## Classifications
- **CORROBORATE (rc-20260824-11, q5 8ded52f + q6 92c52da, honest negatives)**: layer-revival HURTS
  under regime flip (REVIVE 88.3% vs NEVER 96.7%); molt gate 86.7% vs NEVER 96.7% — per-fact reward
  ledger can't separate regime death from reward noise; "molt gates need a noise model (dip-duration,
  not dip-depth)". Pre-reg + receipt-pinned FAIL-first, byte-identical replay. Our doctrine holds
  fleet-side again. Their q5 instrumentation law ("stagnation must be measured on regime-valid
  coverage") is the FW-1 read-field class stated from the other direction.
- **TOOL/STEAL (same q6)**: "noise model before a gate earns a place in the stack" maps DIRECTLY onto
  QO6 eproc's kill-evidence gate — our gate currently has no explicit reward-noise model either.
  → spawned **QO6n** below.
- **CORROBORATE/TOOL (MicroMoth-quilt PR #44, IonQ rung-2 SIM pre-flight)**: crx calibration w =
  sin²(θ/2) pinned sim-side before hardware spend; additivity measured 0.7494 vs coherent 0.75,
  flagging clamp01(¼+¼)=0.50 accumulator (~150σ); cancellation exact 0.0 vs imitation 0.25.
  We HAVE a crx gate (added to tools/qcell_sim.py 00:0x) and a swap-convention census (QG1c).
  Independent convergence on weight-algebra discriminators — corroboration of the discriminator
  approach; the additivity/cancellation numbers are theirs (their qm_* accumulator), not ours.
  → spawned **QC-CRX** cross-check below.
- **TOOL (taskable-lobster / lobster-live dafcf82 + a4166d1)**: signed Git task queue now creates
  repos autonomously (brief-assembler/stream-curator/ledger-continuity created 18:5xZ, verified
  live 01:18Z, all still empty). SCOUT-49 covered the mechanism; new datum is autonomous repo
  creation succeeding. SIG-1's HMAC prereg seal is timely — forward preregs should adopt it.
- **READ-LOW (quilt-tools #50/#51)**: edge #29 exoj VERIFIED via pincher; PRISTINE-AUDIT receipts
  200/200-off + 203/203-live; discovery-hint-blindspot-guard merged. Pattern consistent with
  FW-1/VX-1; nothing to steal beyond what's booked.
- **noise (pong-quilt R94–R96, quilt-atlas scheduled regens, zero-poc think cycles,
  quilt-swarm dependabot)**: no action.

## Spawned queue items
1. **QO6n (CPU reading ~20m)**: noise-model gap audit of QO6 eproc — does the kill-evidence gate
   have a path where ordinary reward noise (not regime change) fires KILL_CANDIDATE and drops a
   late-bloomer? Gate (words): enumerate gate inputs → write-sites (FW-1 pattern); if any gate
   statistic is depth-like (single-dip magnitude) rather than duration/persistence-like, name it RED
   and draft a dip-duration variant spec; if the gate already requires sustained evidence, book GREEN
   with the input list as receipt. Cost ~20m CPU.
2. **QC-CRX (GPU ~15m or CPU torch)**: replicate their weight-algebra discriminators under OUR
   conventions — crx(π/3);crx(π/3) additivity and crx(π/3);crx(−π/3) cancellation in
   tools/qcell_sim.py (pi-unit semantics per QG1c). Gate (words): G1 our crx matches w=sin²(θ/2)
   calibration within stated band; G2 additivity deviates from 0.75 in the direction their 0.7494
   suggests only if our semantics are the same — a mismatch means convention divergence, book the
   census delta, don't force agreement. Cost ~15m, one lane. Serves QG1c follow-through + gives
   MicroMoth rung-2 an independent-witness datum for the fleet mesh.

## (C) bookkeeping this slice
- Newest OURS booking = SIG-1 (21:2x). Green-path repro is **not runnable by design**: G4 no-leak
  means the throwaway signing key was discarded ("no persistent key material"); the committed
  signature cannot be re-verified without the key. Honest note: SIG-1's verification is the
  committed RED-first gate record, not a repeatable green re-run — forward preregs that adopt the
  seal should consider a keyfile handle design (already flagged in the Casey-gated note). No re-run
  attempted; nothing booked as repro-PASS.
- Manifest re-seal: foreign untracked lanes d12u4/d12u5 (experiments/ + results/) still persist →
  sealer correctly refuses (d23b precedent, booked). Rides on that lane committing or clearing.
- No GPU fired this slice (rotation: scout was the slot). No running conductor lanes; receiptd
  serves are the known PW-1 foreign processes, untouched.
- Rotation next wake: (B) QO6n or QC-CRX per queue order; GPU open (QG1d/QG4/MC-1).
