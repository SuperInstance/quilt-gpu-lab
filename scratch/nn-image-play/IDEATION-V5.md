# IDEATION-V5 — next-wave briefs for the dicebear×cascade image line

Date: 2026-10-03 (post-v3 receipt, mid-v4 wave). Status: IDEATION ONLY — no GPU work, no model calls.
Scope: what runs AFTER v4 verdicts land. Everything below uses only what is on disk:
ASUS AICreator sd1.5 stack (dreamshaper_8, realismByStableYogi_ponyV3VAE, scribble/inpaint/shuffle CNs, LCM LoRA),
HF cache (clip-b32, dinov2-base, ijepa_vith16), ollama (moondream, qwen2.5:3b/7b, qwen3.5:0.8b), typesafe jev-latest.

## Where the line stands (the constraint set every brief inherits)
- v3: prompt steering dead (v2, effect -1.26 wrong way); scribble-CN at 0.6 halved machine_vs_organic bias
  (-4.0 vs base -6.0) but cn09 re-tied base; program-best JEV noul 0.91; edge-IoU SATURATED (~0.95 all arms) — retired.
- v4 running: judge axis (CLIP vs DINOv2), structure-drift metric (differential), anchor-relative targets,
  cross-identity negative control, style-under-structure.
- Instrument law (v5 standing): differential or concentrated measurements only. No saturated overlap metrics,
  no diluted 5-dial soup where a 1-dial delta answers the question.
- Cost anchors (measured): CN-pipe load ≈ 2 min, base ≈ 1.5 min, 6-step img ≈ 3.6 s, perception ≈ 10 s/img wall
  (0 heavy GPU), CLIP/DINOv2 batch ≈ seconds. 6GB law: one heavy model resident at a time.

---

## W5-A — Judge Board of Three (decision-level flip ledger)
- **Claim (falsifiable):** a 3-judge identity board (CLIP-b32 + DINOv2-base + ijepa_vith16) flips ≤ 10% of
  v3+v4 accept/reject decisions vs the CLIP-alone floor of 0.80; and pairwise judge Spearman ≥ 0.80.
- **Mechanism:** embed every archived artifact (v1–v4 candidates + 10 dicebear sources, ~100 PNGs) with all three
  encoders (mean-pooled patches for ijepa), identity = cosine vs own source. Majority vote at the 0.80 floor;
  ledger every decision that changes. Extends E1 (which paired only CLIP×DINOv2) to a board with a third
  self-supervised opinion and decision-level receipts.
- **Gates:** flip_rate ≤ 10% AND min pairwise Spearman ≥ 0.80 → board certified as default gate. Flip rate
  10–25% → CLIP floor retained but flagged "judge-dependent"; >25% → all past acceptances re-litigated in a
  v5.1 re-verdict (the flip ledger IS the receipt).
- **GPU cost:** ~7 min (three light encoders, phased; ijepa ViT-H fp16 ~2.4GB alone-resident). No generation.
- **Instrument lesson:** judge ensemble with flip-rate as the receipt — a differential on *decisions*, not
  another absolute score. Kills the judge-monoculture risk before it contaminates W5-C/F.

## W5-B — Generator Center-of-Gravity Map (bias sheet across ALL past runs)
- **Claim:** DreamShaper's anchor-relative bias vector is a stable generator property: per-dial bias SD across
  arms/subjects/waves ≤ 1.0, and ≥ 3 dials hold sign across all arms (e.g. complexity +, machine − for robots).
- **Mechanism:** re-perceive ALL archived PNGs (v1 smoke, v2, v3, v4 — one consistent moondream→qwen pass,
  replacing the mixed-stack readings) against the v4 anchor targets; regress per-dial bias by (generator,
  arm, subject). Output: BIAS-SHEET.md — the receipted per-generator bias map, DIALS.md field-face style.
- **Gates:** stability gate above → bias becomes a *known correction vector* applied to future targets
  (target' = target − bias(generator, arm)); instability (SD > 1.5 on ≥ 2 dials) → bias is context-bound,
  correction stays per-arm as today.
- **GPU cost:** 0 heavy-GPU min; ~20 min wall perception over ~100 archived imgs.
- **Instrument lesson:** concentrated per-dial measurement on existing artifacts; turns sunk runs into a
  compounding spec. The REUSE-LEDGER move, image edition.

## W5-C — Cross-Generator Bias Census (DreamShaper vs ponyV3VAE)
- **Claim:** the anthropomorphization bias (machine → organic pull on robot subjects) is a DreamShaper prior,
  not universal SD1.5 behavior: ponyVAE arms show |machine bias| differing by ≥ 2.0 dial units, or opposite
  sign, on ≥ 2 subjects.
- **Mechanism:** realismByStableYogi_ponyV3VAE + LCM 6-step through the identical v3 grid shape (lucineer + casey
  × {cn06, base} × seeds 11/22/33, strength 0.7); anchor-relative dial cascade unchanged; bias vectors compared
  paired per subject×arm against the v3 DreamShaper arms already on disk.
- **Gates:** paired per-dial bias delta (this is the census, not an accept gate). Verdict semantics: "generator
  prior" (claim holds) vs "SD1.5-universal" (bias reproduces on both ckpts → the fight moves to CN strength /
  correction vectors, not checkpoint shopping). Honest fail recorded either way.
- **GPU cost:** ~8 min (2 pipe loads + 12 imgs + perception).
- **Instrument lesson:** differential paired design (same grid, two generators); concentrated on the ONE dial
  (machine_vs_organic) the whole line has been fighting since v1.

## W5-D — Conditioning-Map Ablation (map hardness, not new CNs)
- **Claim:** at fixed cn_scale 0.6, hardening the conditioning map (soft FIND_EDGES → binarized → dilated
  thick-line) monotonically cuts structure-drift (≥ 20% step-down soft→binary) without breaching the identity
  floor; lllyasviel_shuffle as contrast arm does NOT reduce drift (content-shuffle ≠ geometry pin).
- **Mechanism:** one scribble-CN pipe, four map preprocessors of the same dicebear source (soft / binary t=100 /
  dilate-3px / autocontrast-bis), lucineer + jev × 3 seeds (24 imgs) + 6 shuffle-CN imgs (second load).
  Note: no canny/mlsd CN on disk — the ablation runs on the MAP side of the conditioning, which is the knob
  we actually control for free.
- **Gates:** paired drift ladder per map type + identity floor 0.80 + anchor-relative machine bias per rung.
  Verdict = which map rung is the v6 default (a monotone ladder) or "map hardness is a dead knob" (flat —
  also useful: concentrates future effort on cn_scale alone).
- **GPU cost:** ~12 min (2 loads, 30 imgs).
- **Instrument lesson:** structure-drift (differential change fraction) replaces the retired saturated IoU;
  each rung is a concentrated paired comparison.

## W5-E — Identity-vs-Style Pareto Cliff (strength sweep under CN)
- **Claim:** identity vs strength has a measurable cliff s* (largest strength with mean identity ≥ 0.80), and
  CN06's cliff sits ≥ 0.1 above base's — i.e., structure constraint literally purchases style headroom,
  quantified.
- **Mechanism:** strength {0.5, 0.6, 0.7, 0.8, 0.9} × {cn06, base} × lucineer × seeds {101, 102} (20 imgs,
  2 loads). Style prompt held constant (watercolor). Cliff located per arm; headroom = Δs*; secondary read:
  dial movement per 0.1 strength = style-dial miles-per-gallon.
- **Gates:** cliff exists for both arms (monotone-ish decline, else "no cliff within range" verdict) AND
  Δs* ≥ 0.1 for the CN-buys-headroom claim. Fail = headroom ≤ 0 → v6 style work runs at base with no CN tax.
- **GPU cost:** ~9 min (2 loads, 20 imgs).
- **Instrument lesson:** single-axis concentrated sweep (one variable, one metric per arm); extends v4-E4's
  binary style test into a graded frontier instead of another accept/reject coin.

## W5-F — Crew Widening (all 10 fleet faces, accepted-set gallery)
- **Claim:** under the frozen best arm (from v4 verdicts), ≥ 6 of 10 fleet faces yield ≥ 1 accepted candidate
  (identity ≥ 0.80, corrected-L1 ≤ 5.0 anchor-relative, JEV noul ≥ 0.6 subject-matched); acceptance rate per
  face becomes the generator spec-sheet row.
- **Mechanism:** all 10 dicebear PNGs (casey, fable, glm, jev, kimicode, lucineer, mmx, opencode, wesley,
  zeroclaw) through best-config × 3 seeds (30 imgs, 1 load); full cascade; JEV only on survivors; montage of
  the accepted set = the receipted artifact (fleet gallery).
- **Gates:** count gate above; per-face verdict rows (accept / identity-only-fail / dial-fail / JEV-fail)
  localize WHERE each face breaks — a failure map, not just a pass rate.
- **GPU cost:** ~12 min (1 load, 30 imgs, ~10 survivors' perception + JEV).
- **Instrument lesson:** anchor-relative targets per face (hand-picked targets stay out of the loop);
  acceptance-rate is the concentrated spec metric. Run AFTER A/B/C settle so the spec sheet isn't misprinted.

## W5-G — LCM 4-Step Proxy Certificate (fast seed-search engine)
- **Claim:** 4-step LCM decisions agree with archived 6-step outputs on ≥ 80% of (identity ≥ 0.80 floor) calls
  and dial deltas within ± 1.0 on ≥ 4/5 dials — certifying 4-step as the seed-search engine (~2.5 s/img).
- **Mechanism:** replay 20 archived (subject, arm, seed) tuples at 4 steps (same pipe config), compare identity
  cosines and anchor-relative dials against the v3/v4 PNGs already on disk. Pure A/B on existing coordinates.
- **Gates:** agreement ≥ 80% AND dial delta bound → 4-step certified for search-only (finalists re-run 6-step,
  written into the protocol); < 80% → proxy rejected, 6-step stays mandatory (2 LCM steps carry real info —
  a receipted negative).
- **GPU cost:** ~4 min (1 load, 20 imgs).
- **Instrument lesson:** differential same-tuple replay — the proxy is judged on decision agreement, not
  absolute scores; every divergence logged as the receipt.

## W5-H — Inpaint Dial-Locality (fix ONE dial, don't move the rest)
- **Claim:** masking a single facial region (eye band / mouth band, PIL ellipse from the edge map) and
  inpainting at strength 0.35 moves its associated dial(s) while collateral movement on other dials stays
  ≤ 1.0 — vs img2img at the same strength moving ≥ 2.0 collateral.
- **Mechanism:** lllyasviel_inpaint CN (on disk) + StableDiffusionControlNetInpaint pipeline, 2 regions ×
  lucineer + casey × 3 seeds (12 imgs, 1 load) + 6 img2img controls; anchor-relative dial deltas before/after.
  Region→dial ownership table is the artifact (eyes→mood/warmth? mouth→warmth?).
- **Gates:** locality ratio (target-dial delta ÷ max collateral delta) ≥ 2.0 per region → dial-targeted
  correction is real; < 1.0 → dials are global properties of the whole face, correction must stay whole-image.
  Either verdict upgrades the model of what dials ARE.
- **GPU cost:** ~7 min (2 loads, 18 imgs).
- **Instrument lesson:** the concentrated single-dial experiment — measures dial *locality*, a mechanism fact
  no 5-dial soup run can produce.

## W5-I — Palette Bones (deterministic LUT dial, dial-lib style)
- **Claim:** a 5-stop palette bone (k-means k=5 on 512px, hex+weights) separates accepted from rejected
  candidates: accepted-vs-source palette distance stays below rejected-vs-source distance with ≥ 0.75 AUC
  across v3+v4 artifacts.
- **Mechanism:** pure numpy/PIL over all archived PNGs + 10 sources; palette distance = weight-matched RGB
  L1. Writes FACE-BONES.md (bone per face, dial-lib ruler-face format) + separation stats. Zero generation.
- **Gates:** AUC ≥ 0.75 → palette becomes a free deterministic dial in the gate stack (pre-CLIP killer);
  0.5–0.75 → diagnostic-only; < 0.5 → palette is style noise, journaled as a failed dial (still a learned dial
  per library law).
- **GPU cost:** 0 heavy-GPU min; ~4 min CPU.
- **Instrument lesson:** DIALS.md ruler face — deterministic extractor beats a judgment call wherever it can;
  every accepted face's bone compounds the library (REUSE-LEDGER image edition).

## W5-J — Quantizer Audit (judge the dial judge at the source)
- **Claim:** swapping the dial quantizer (qwen2.5:3b → qwen3.5:0.8b) on the SAME archived moondream
  descriptions reproduces dials with Spearman ≥ 0.85 per dial and ≤ 10% corrected-L1 verdict flips.
- **Mechanism:** zero generation — replay both quantizers over every stored desc in v3/v4 receipts; per-dial
  agreement + verdict-level flip ledger; also re-run temp0 ×3 stability on 5 faces (CASCADE-V0 Q1, never
  formally booked for the image line).
- **Gates:** claim holds → 0.8b certified as the cheap default quantizer (frees 3b for JEV-question duty);
  fails → quantizer frozen at 3b, sensitivity journaled as the instrument's error bar.
- **GPU cost:** 0 heavy-GPU min; ~3 min wall (CPU ollama).
- **Instrument lesson:** instrument calibration precedes instrument use — an error bar on the dial ruler
  itself, before v5 spends any GPU minutes on dial-delta claims.

---

## Ranking — information per minute (GPU-bound resource; wall time breaks ties)

| # | Brief | GPU min | Why it ranks here |
|---|-------|---------|-------------------|
| 1 | W5-A Judge board | 7 | Every acceptance ever made depends on the judge; flip ledger re-prices the entire line's receipts at once. |
| 2 | W5-J Quantizer audit | 0 | Error bars on the other half of every gate; ~free, must precede dial-delta claims. |
| 3 | W5-B Bias CoG map | 0 | Converts ~100 sunk artifacts into a reusable generator spec + correction vector. |
| 4 | W5-I Palette bones | 0 | New deterministic dial + library compounding for CPU-minutes. |
| 5 | W5-C PonyVAE census | 8 | Settles DreamShaper-prior vs SD1.5-universal — redirects all future bias-fight spending. |
| 6 | W5-G 4-step proxy | 4 | Certifies a 1.4× accelerator for every future search wave; cheap A/B on archived coords. |
| 7 | W5-H Inpaint locality | 7 | New capability class (dial surgery) + a mechanism fact about what dials are. |
| 8 | W5-E Pareto cliff | 9 | Quantifies the CN tax/refund; grades E4's binary result into a frontier. |
| 9 | W5-D Map ablation | 12 | Knob refinement; only matters after C says the fight stays in CN-space. |
| 10 | W5-F Crew widening | 12 | Census + gallery — highest artifact value, lowest mechanism info; run last with a certified stack. |

Sequencing note: A+J+I+B are a same-day "instrument day" (≈0 GPU). C, G can run as wave v5a; H, E, D as v5b;
F closes the wave once the stack is certified. Total heavy-GPU budget for all ten: ≈ 50 min.
