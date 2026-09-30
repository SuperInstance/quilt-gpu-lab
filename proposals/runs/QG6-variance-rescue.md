# QG6 — variance rescue: do bigger move-sets beat more generations?

Spawned by QG3 (trap = slow-climb fence, not width wall). P1(refuted in QG3) was budget;
QG6 tests the MOVE-SET instead: are stuck streams gradient-starved (need bigger jumps)
or simply slow (need more rounds)?

## Design
- Same lane as QG3 arm A: W=6, gens=12, S=1024 streams, C=15 children/gen (FIXED total
  children = fixed eval budget), bar=0.45, seed=1234 for k=1 arm (replicate of QG3 A).
- Arms: k=1 (baseline replicate), k=2, k=3 — each child receives k independent
  mutation applications (sub/ins/del each, same op mix) instead of 1.
- Everything else identical (selection, promotion >=, tie-breaking by random key).

## Gates (fail-loud)
- G1 ANCHOR-VEC vs tools/qcell_sim.evaluate on 50 random genomes, max|diff| < 1e-9.
- G2 REPLICATE: k=1 arm crossed rate must fall inside QG3 arm A CP95
  [0.547, 0.609] modulo the lane's known torch-nondeterminism band (+-0.006 absolute);
  if outside, book FAIL and stop.

## Pre-registered predictions
- P1 (variance-rescue): if trapping is a move-set problem, k=2 and/or k=3 crossed rate
  exceeds k=1 by delta lower-bound > +0.05 (CP95, n=1024 each).
- P-null (slow-climb): if trapping is a time problem at fixed budget, all k arms are
  statistically indistinguishable (overlapping CP95s).
- P2 (too-hot): k=3 could UNDERSHOOT k=1 if jumps destroy accumulated fitness
  (non-monotone in k). Any monotone/anti-monotone pattern gets named either way.

## Booking
Results to results/qg6_variance_rescue/{results.json,run.log}; per-k crossed rate + CP95
+ delta lower bounds vs k=1; crossed_gen distribution per arm (does k change WHEN, not
just WHETHER). FAILs booked in place, no re-rolls.

Pinned instruments (fire-time convention): tools/qcell_sim.py @ receipts/manifest.json
current seal; lane code copied verbatim from experiments/qg3_trap_anatomy.py (declared
inheritance), mutation kernel extended by k-parameter.
