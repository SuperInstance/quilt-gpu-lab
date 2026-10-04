# W5-C VERDICT — crop-DINO re-score: formal PASSes, but DO NOT ADOPT the crop

**Run:** 2026-10-03 21:0x AKDT · `v5c_crop_dino.py` → `v5c_crop_dino.json` · 0 new generation, 78 stored artifacts re-embedded (DINOv2-base, symmetric center-box crop on artifact+reference, scales 0.5–0.9 + full-frame, crash-resumable checkpointing, ramp receipt logged per INSTRUMENT-01).

## Pre-registered claims (frozen in script header before run)

| # | Claim | Result |
|---|-------|--------|
| H3 | Full-frame recompute reproduces board dino (ρ≥0.99, max\|Δ\|≤0.02) | **PASS** (ρ=0.9999, max\|Δ\|=0.0026) |
| H1 | ∃ crop s + floor t: dino-primary keeps 4/4 morph rejects AND retention > 0.6269 (v5b booked baseline) | **PASS** (s=0.8 @0.60 → 0.6716; also s=0.6@0.50→0.6418, s=0.9@0.60→0.6567) |
| H2 | ∃ crop s: gap(median legacy dino − morph-max) > full-frame gap | **PASS** (s=0.5: 0.3673 vs 0.1755; s=0.6: 0.2499) |
| H4 | ∃ (s,t): min-gate(clip_ff, ijepa_ff, dino_crop) keeps 4/4 AND retention ≥ 0.60 | **PASS** (s=0.8 @0.60 → 0.6716, vs full-frame min@0.80 → 0.194) |

## The honest headline: crop LOSES to same-grid full-frame

My frozen grid (0.50–0.90 × 0.05) includes floors v5b's G3 scan never reached. On that grid, **full-frame dino-primary @0.55 = 4/4 morph rejects @ 0.7015 retention** — better than every crop scale's best 4/4 knob:

| scale | morph-max dino | best 4/4 knob | retention @4/4 |
|-------|---------------|---------------|----------------|
| 0.5 | 0.2887 | dp@0.50 | 0.5970 |
| 0.6 | 0.4249 | dp@0.50 | 0.6418 |
| 0.7 | 0.6325 ⚠ | dp@0.65 | 0.5970 |
| 0.8 | 0.5894 | dp@0.60 | 0.6716 |
| 0.9 | 0.5726 | dp@0.60 | 0.6567 |
| **1.0 (full)** | **0.5031** | **dp@0.55** | **0.7015** |

At matched 4/4 morph rejection, crop-dino is a **strict retention downgrade**. H1/H4 pass only against the *v5b-booked* baseline (dino@0.60 → 0.6269); the same-grid full-frame optimum beats every crop. **Adopt nothing from the crop family.**

## Mechanism (per-morph receipts)

- s≤0.6 crops crush ALL four morphs to 0.19–0.42 — but legit scores drop in step, so retention falls.
- **s=0.7 INFLATES `xlucineer_caseyedges_s102` to 0.6325** (above full-frame 0.5031 and above the 0.60 floor): the center crop keeps the lucineer-face region and *removes the casey-identity evidence DINO was using to flag the blend*. Mid-scale crops actively help the hardest morph through.
- Gap improvement (H2) is real but doesn't convert: both distributions shift down together.

## Actionable byproduct

**Full-frame dino-primary @0.55 (4/4, ret 0.7015, +7.5pts over booked 0.6269)** is now on the table — it was inside my frozen grid, computed over the same pool, first observed here. Tradeoff: morph-max headroom shrinks 0.097→0.047 (morph-max 0.5031). Policy call for Casey: retention vs margin. No re-roll performed; no claim was adjusted post-hoc.

**Bottom line:** W5-C = negative result for the crop hypothesis (formal PASSes are baseline-relative artifacts), one positive full-frame observation (0.55 floor) for the portal gate discussion. Gate stays **DINOv2-primary full-frame + JEV mandatory**; floor 0.60 vs 0.55 is Casey's call.
