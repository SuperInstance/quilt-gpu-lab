# QG2 — the desert-break law at scale (2026-09-30, pre-registered before firing)

## Question
exp021/exp022 measured the desert-break rate on N=8 salted streams (3/8 cross; 5/8 never birth a break).
QG2 turns the anecdote into a law: P(stream crosses bar 0.45 in 12 gens), its break-time distribution, and a
noise-vs-landscape ablation — at N=4096 fresh-rng streams.

## Lane (semantics-faithful reimplementation; honestly NOT stream-identical)
qcell.search source is not on disk (qcells repo not public) — the lane is rebuilt from exp020/exp021's
documented loop: champion-local, pop 16, 12 gens, skeleton [h0,cx01], budget 6, restrict {replace, indel},
tie_sample=True (uniform among exact-fitness ties at gen-max), verify gate (promote iff best_verify >=
champion_verify), seeds 31000+k. Physics = QG1-calibrated conventions (balance = min(p000,p111), angles in
pi-units, q0=MSB) via tools/qcell_sim.py. Gate vocabulary mined from telemetry: h,x,rx,rz,cx,crx,swap with
angles in {0.25,0.5,0.75,1.0}. Mutation class drawn uniform; replace = random pos -> fresh random gate;
indel = insert (if len<6) or delete (if len>1) at random position; invalid draws resampled.
FRESH RNG, not the original stream — declared, not hidden.

## Arms
- ARM-SHOT (the law): train/verify = 512-shot multinomial estimates, exactly the original's noise.
- ARM-EXACT (ablation): fitness = exact balance, gen-max promotion (verify gate trivially passes) — pure
  noiseless hill-climbing. Splits the 5/8 non-crossing into SHOT-NOISE vs LANDSCAPE-TRAP.

## Scale
4096 streams x 12 gens x 16 cells = 786k genome-evals per arm. GPU-batched: 63-gate library precomputed once;
genomes as id-sequences; unitaries = 6-step bmm chain over [65k, 8, 8]; shots via batched multinomial.

## Gates (frozen before firing)
- ANCHOR-VEC: vectorized evaluator must match tools/qcell_sim.py exact balance to 1e-9 on >=50 random genomes.
- ANCHOR-8: the 8-stream shot arm (seeds 31000..31007) must produce the exp021 CLASSES qualitatively
  (>=1 crosser, >=1 stuck-at-~0 stream, near-miss(es) in [0.35,0.45)); NOT required to match per-seed outcomes
  (fresh rng) — reported side-by-side, labeled honestly.
- G1 DESERT-SHAPE: across all gens and cells of ARM-SHOT, <1% of shot-estimated balances fall in [0.30, 0.43).
- G2 THE LAW: P(cross) at N=4096 with Clopper-Pearson 95% CI; report whether 3/8 lies inside; break-time
  histogram (first gen champion verify >= 0.45).
- G3 NOISE-VS-LANDSCAPE: report P_exact(cross) - P_shot(cross). Pre-registered prediction: exact arm crosses
  substantially more (noise is a major jailer). If the exact arm ALSO fails broadly, the desert is a landscape
  property — the deeper finding.
- EXPLORATORY (labeled): loneliness gap distribution; champion genome-length dynamics; per-gate frequency drift
  in crossers vs stuck streams.

## PROVENANCE CITATION AMENDMENT (2026-09-30 02:2x, docs-only — per MicroMoth-quilt PR #29)
The reimplemented lane follows the qcells lab's documented loop; the lab's canonical home is
**SuperInstance/micrograd-quilt** (labs/qcells tree; sealed receipts exp018–exp022 mirrored as
PRs #5–#7). Note: "qcells repo not public" above was true at pre-reg time; the labs/qcells tree
is now mirrored in the org repo. Local workspace paths are quoted history, not the citation.
No data or gates changed.
