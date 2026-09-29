# CM1 round 3 — competent GEN meets the gates (frozen addendum)

Date: 2026-09-29 14:0x AKDT. Pushed BEFORE the run. Round-1 plan governs
cells/stimuli/rule/scoring; r2 addendum governs format-first gate + sweep.

## Delta from round 2 (one factor)

GEN cell: local qwen2.5:0.5b -> **DeepInfra ByteDance/Seed-2.0-mini**
(OpenAI-compatible, temperature 0, token at ~/.config/deepinfra/token,
live 14:03). JUDGE (jev-preview), PROJECT, prompts, stimuli, pinch sweep
(0.3/0.5/0.7), format-first gate, verdict bands — ALL frozen as r2.

## Sealed predictions

- Arm A (ungated Seed) scores far above 0 — format compliance expected.
- Jev usage > 0 (drafts parse -> semantic gates finally engage).
- The sweep ENGAGES: path census varies across p (more DRAFT_PASS at 0.3,
  more PINCHED_FALLBACK at 0.7).
- Open question this round answers: with a COMPETENT generative cell, does
  judgment-gating add accuracy (gates catch real errors) or only cost
  (TIE_NOISE while burning Jev tokens)? r1/r2 wins were fallback-carried;
  either result here is a real property of the mesh.

## Cost booked

DI usage tokens (arm A + arm B) + Jev tokens per pinch level + wall time.

## Output

results/cm1/round_003_out.json + append results/cm1/rounds.jsonl.
Script: experiments/cm1_relay_r3.py (imports r1 cells; r2 script frozen).
