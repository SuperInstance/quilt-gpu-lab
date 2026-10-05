# SCOUT-42 — SuperInstance push sweep 2026-10-05 14:09 UTC (day-conductor, Casey active, read-only)

Window: post-XM-1 / post-SCOUT-41 (2026-10-04 ~0411Z), ~34h. Method: users/SuperInstance/events PushEvent filter + per-repo commits + open PRs. purplepincher/zero + zero-msg-test bursts are outside the org and look like messaging plumbing — skipped (note only). quilt-matrix tip is still 0cb7552 (guard bugfix, covered by SCOUT-41/XM-1).

## HEADLINE — IONQ lane convergence: MicroMoth docs/IONQ-RECON + PRs #43/#44 (rung-1/rung-2 sim pre-flight, opened 01:14Z/02:24Z Oct 5)

Our IONQ-2 (booked 04:1x Oct 5) cleared rung-2 BEFORE their pre-flight PR landed its rungs. Direct read:
- **CORROBORATE (strong)**: their §2 bridge constant `w = sin²(θ/2)` on `crx` (marked SPECULATIVE, calibratable, "rung 2") — our G2 measured transfer = sin²(θ/2) within 1e-9 at EVERY θ on qcell_sim. Their speculative constant is now GROUNDED from our side; IONQ-2's G4 (crx(θ);crx(−θ) → EXACTLY 0.0) is exactly their §3.1 "cancellation circuit" discriminator — the sign their qm\_\* registry algebraically lacks, our substrate expresses. **No CONTRADICT: nothing booked is threatened; IONQ-1's sim-backend-bound list stands.**
- Their rung-3 = leak↔decoherence mapping (qm_tick geometric leak vs basis-dependent exponential decoherence) — hardware-side, not our lane.
- **Fleet-loading note**: IONQ-RECON §provenance cites `quilt-gpu-lab/scratch/dogfood/luau2/brief_r1.txt` as "AUTHORITATIVE SEMANTICS" for the qm\_\* contract — our scratch tree is load-bearing fleet-side. Scratch is not sealed by the manifest (17-file tool/weight seal). Flagging for WQ-1 scope consideration (untracked live-lane precedent says don't touch, but the citation makes that path de-facto canon).
- Spawned **IONQ-3** (CPU ~15m, LOW, coverage census): read PR #43/#44 diffs; list their §4 rung-1/rung-2 discriminators we did NOT exercise in IONQ-2 G1–G4; any uncovered discriminator that is expressible on qcell_sim gets a follow-up gate. No new physics claimed; reconciliation only.

## TOOL/STEAL — fleet-witness (NEW repo, hot Oct 4 21:xx → Oct 5): L2 git anchoring + L3 witness quorum + Ed25519 sig-seam + sibling-seal embedding

- PRs #3–#5 merged (37→45→57 green), #7 (L3 quorum client-side: policy + cosig verification) and #8 OPEN. docs: WITNESSING / L2-DUPCHECK / L3-QUORUM; src: anchor/checkpoint/embedding/tree.
- **This is the strongest reference design yet for RC-4/RC-5**: our receipt-manifest seal has exactly ONE witness (us); their L3 quorum = policy + cosignature verification across witnesses, Ed25519 seam tests, sibling-seal embedding as a second channel. Maps directly onto the reseal-forgery class (3 instances fleet-side) and our single-manifest weakness.
- Spawned **WQ-1** (CPU ~30m, reading+spec, pre-reg before any tool change): (a) enumerate which sealed claims in receipts/ have exactly one witness; (b) spec minimal Ed25519 cosig seam for receipt_manifest.py that leaves existing seals verifiable (no reseal required); gate: spec must state what happens to the 17-file tool/weight seal under a key rotation, in words, before any code.

## CORROBORATE
- **jev-quilt**: PRs #50/#51 R6 live batteries (8 verbatim re-runs + new classes, G1 graft flip, record-only) + wave-69 knowledge package; hourly wipes continue (75th wipe 0 drift booked earlier — QC-JEV untouched). F4 event-fabrication probe design = record-only assertion-naming layer — same doctrine family as our pre-reg + fail-loud anchors. Cite-only.
- **pong-quilt** rounds 92–95 (PRs #114–#117): `--check` adoption gate + abstaining-judge check label — CI-1/RC fail-closed class holding fleet-side in anger. #49 unchanged at 7 comments (Casey day item).
- **quilt-tools** edge #33 VERIFIED (referral-graph booking on-merge) — receipt doctrine corroborated.

## CHECK-CANDIDATE (LOW, reading)
- **rc-20260824-11** breathing-poc-v5: "cross-phase create_question (INHALE+HOLD) flips coverage from −37% drag to +5% pass" and m3 "stable gap test — regime patched good-forever; stable:tighten fires 3/3 boundaries". The "regime patched good-forever" phrase smells like a monitoring gate that stops firing after first patch — FW-1/DEGENERATE class candidate. Spawned **RC-B1** (CPU ~20m, LOW): read the m3 test; if the regime gate is mute-after-patch, add to the DEGENERATE census note. No claim against them unless machine-checked.

## Contradict status
**No CONTRADICT this sweep.** QO2 routing stack, DECIDE-1/2, receipt-manifest doctrine, QG3+QG6 time-law, QG1c swap census, W5a/W5b/W5c — all unthreatened. Closest touch was IONQ convergence, which confirms rather than contradicts.

## [EMBASSY]
- pong-quilt #49: 7 comments, still unresponded (Casey day item, unchanged).
- None new.
