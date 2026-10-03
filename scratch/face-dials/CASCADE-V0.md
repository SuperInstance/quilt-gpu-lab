# CASCADE-V0 — JEV judges, dicebear renders, NNs cascade (2026-10-02, Casey directive)

Casey: "jev help the system … maybe dicebear-quilt could be the last-mile image
generator for jev even in a cascading NN."

## The inversion (the core idea)
dicebear makes GENERATION nearly free: deterministic, ~ms, 63 styles × unbounded
seed-space, receipts for free. So the compute budget moves entirely to JUDGMENT.
The cascade is not a generator producing pixels — it is a JUDGE-STACK SEARCHING
SEED-SPACE. (duke-lab's GAN-with-words pattern, faces edition: procedural
generator, neural critic, search = the learning loop. No training required.)

## The cascade (each stage independently falsifiable, receipted)
- S0 PROPOSE — cheap proposer emits (style, seed) candidates: local 0.5b, grammar,
  or seed-grammar like `{role}-{trait}-{n}`. Cost ≈ 0.
- S1 FORMAT GATE — deterministic, free (CM1 r2 lesson: format-first gating catches
  broken proposals at zero judgment cost). Bad seed grammar dies here.
- S2 LOCAL VLM DIALS — moondream measures face-dials (mood/warmth/complexity/
  machine/organic/colorfulness…). Cost ≈ free, fully local. Coarse filter:
  reject anything whose dials are nowhere near the target profile.
- S3 JEV CELLS — typesafe graded judgment on the few survivors ("does this face
  read as trusted-quartermaster?", noul). Semantic judgment, batched, precious.
- S4 ANCHOR — chosen face + the judgments that chose it → tipnotary chain +
  i2i. The SELECTION is receipted, not just the artifact. (dicebear quilt face
  law: the face IS a pure function of its id; the cascade receipt says WHY.)

Rejects at every stage feed back to S0 as guidance (CM1 loop). Every stage is
swappable without retraining anything.

## dicebear as last-mile in a bigger NN cascade
Heavy NN (SD/diffusion, when we want painterly) consumes the CHOSEN face as
img2img identity anchor; a VLM stage judges IDENTITY PRESERVATION (do the
face-dials survive the expansion?); JEV judges the aesthetic. dicebear stays
the deterministic root-of-trust: the NN decorates, the SVG defines identity,
receipts bind both. Decode: NN = texture, dicebear = identity spec, JEV = judge
at every boundary.

## Economics
Judgment spend concentrates only on survivors: S1 kills free, S2 kills at
local-milliseconds, S3 (cloud cells) sees only the residue. The more artists/
characters we do, the cheaper each new one gets — dial-lib's REUSE-LEDGER law,
transplanted to faces: dials and stage-gates are reusable across all targets.

## V0 experiment (this directory)
face_dials_v0.py — is moondream a usable S2 instrument?
Q1 STABILITY: temp0 ×3 same face — identical dials? (deployability)
Q2 SEPARATION: distinct faces → distinct medians? (instrument vs noise)
Q3 CLAIMS: measured dials vs style's authored claim (Law #1, faces edition)
Next: wire S0+S1 (seed grammar proposer + gate) → full local cascade demo →
then S3 with real typesafe cells → S4 anchor receipt.
