# WAVE V4 VERDICT — scored 2026-10-03

**Prereg:** `v4_wave_prereg.json` (sha16 c6e5ee9b1d71de86, frozen pre-run). **Score: 1/7** (E2c derived-PASS; six in-script claims FAIL). Worst scorecard of the line — most informative wave yet. Every FAIL is a finding.

| claim | verdict | measured |
|---|---|---|
| E1a judge agreement ≥0.85 | **FAIL** | Spearman(CLIP,DINOv2) = **0.5633** (37 artifacts) |
| E1b flip rate ≤10% | **FAIL** | **78.4%** (29/37 flip the 0.80/0.75 floors) |
| E2a cn drift < base | **FAIL** | cn drift HIGHER on 3/4 subjects (e.g. lucineer 0.0150 vs 0.0126) — scribble CN *injects* structure, doesn't pin it |
| E2b \|machine bias\| ≤5 pooled | **FAIL** | +7.0 anchor-relative — see ruler-convention note below |
| E3 cross-identity refused | **FAIL** | morphs mean identity **0.8531**, all 4 ≥ 0.80 — **the identity gate failed its negative control** |
| E4 style floor + paired | **FAIL** | split: **neon PASSES** (cn 0.847 > base 0.828, JEV nouls 0.91/0.88 = wave best); **watercolor kills identity** (0.746 < 0.78) |
| E2c ≥3 subjects accepted (derived) | **PASS** | 16 accepted across lucineer + jev + mmx (2 new subjects; casey still 0) |

## The three findings that matter

**1. The identity gate is CLIP-blind to cross-face morphs (E3).** Scribble conditioning from the WRONG face moves drift by the same amount as legit arms, and CLIP cosine stays ≥0.80. JEV caught the casey-direction morphs (noul 0.46/0.38 — refused) but waved the lucineer-direction ones through (0.87/0.88). A control that runs, is satisfied, and gates nothing — now measured in our own gate. Consequence: single-cosine identity floor is retired as a sole gate; the board-of-three (W5-A) + JEV-in-mandatory-path is the replacement, and the E3 morphs join the artifact pool as known-blind positives.

**2. The judge axis collapsed (E1).** CLIP and DINOv2 agree on order (0.56) but disagree on 78% of floor decisions. Every past acceptance was a single-judge verdict. The 0.80 floor is a CLIP-relative claim, not an identity claim.

**3. The anchor moved (E2b + ruler convention).** Anchor-relative targets (measured source readings) replaced hand-picked ones this wave — and the cascade reads the lucineer SOURCE at machine=1/10 (flat vector shading reads organic to moondream), where v2/v3 hand-assumed 10. Candidate readings are ~6-8 machine under BOTH conventions: the stable fact is DreamShaper parks lucineer mid-dial, and "bias" flips sign with the ruler. v3-vs-v4 bias numbers are non-comparable until re-based (W5-B does this post-hoc from stored v3 descs). Lesson: changing the ruler mid-line needs a re-basing pass, same line.

## What held

- Structure-drift metric discriminates arms where IoU saturated (0.007-0.016 range, arm-separated) — the differential-instrument doctrine works.
- Crew widening: jev + mmx accepted first faces (JEV noul 0.87 / 0.80-0.74). casey remains the hard subject (best noul 0.58).
- neon_cn06 = style-freedom point on the identity-style Pareto frontier, with the wave's best JEV verdicts.
- 40/40 generated, receipts chain intact through one SIGKILL (RAM pressure) — phase-resumable design paid off.

## Next (armed)

W5-A judge board of three (ijepa joins; E3 morphs as blind-spot tests) → W5-J quantizer audit (qwen3.5:0.8b vs 3b on stored descs) → W5-B generator CoG map / BIAS-SHEET.md (target-free, re-bases v3).
