# Recon — Jeff (firelex/jeff) — local judgment cells for the fleet
Source: github.com/firelex/jeff (README 18.7KB, `src/jeff/*`, tests, docs, examples/chess). Licence: code MIT (fork of AutoJev, MIT), **weights Apache 2.0**. v1.1 released **2026-09-29** — same day as the PhysicalCoding report. Checkpoint downloading to `/home/eileen/scratch/external/jeff-checkpoints/jeff-0.8b` (1.7 GB).

## What it is
Fine-tunes of **Qwen3.5-0.8B / 2B** and **Gemma4-E2B** for **zero-shot classification with the same request format as Jev**. You describe a situation and list options in plain words; Jeff returns a **calibrated probability per option from a single forward pass**. No generated text, no parsing. Modalities: `choice` (up to 254 options in v1.1), `noul` (yes/no as probability), `score` (point on a described scale). Several independent questions per request.
**This is the same cell contract as our typesafe/Jev judgment primitive** (`api.typesafe.ai`: noul/choice/score) — but **local, free, offline, 22–28 ms**, weights Apache-2.0.

## The recipe (why it matters — it's cheap and reproducible)
- **Full-weight fine-tune, one epoch, batch 256, cross-entropy over the option letters, then one fitted temperature for calibration** (v1.1 uses end-of-epoch checkpoint; dev-loss selection cost 1–2 pts).
- Training data: **public data + synthetic written by an open model (Qwen3.8-Flash-Next)** + a leak filter; at least half of each family copies the eval **layout conventions (formats only — no eval item is ever trained on)**.
- Built entirely on local hardware: 0.8B trains in **~2 h**, 2B in **~3.5 h** on one RTX PRO 6000. Our venv already matches their pins exactly: **torch 2.14.0, transformers 5.17.0, huggingface_hub**.
- Fine-tune scale evidence: chess (600k Lichess positions labeled by Stockfish, 3.5 h) → puzzles 6.2% untrained, 15.5% zero-shot, **55.8% tuned**; voice-navigation app fine-tune (~11k examples, **half an hour**) → 31.7% → **95.8%**.

## Numbers
| | Qwen3.5-0.8B base | Jeff-0.8B | 2B base | Jeff-2B | Gemma4-E2B base | Jeff-Gemma4 | Jev (published) |
|---|---|---|---|---|---|---|---|
| Overall (5 benchmarks) | 45.3 | 79.1 | 46.5 | 82.0 | 62.5 | 81.6 | **83.0** |
| Financial PhraseBank | 36.0 | **95.7** | 53.4 | 94.7 | 86.0 | 96.1 | 77.0 |
| RAGTruth | 49.1 | 85.6 | 35.9 | 87.7 | 63.8 | 87.4 | 77.3 |
| BBH (reasoning) | 39.5 | 64.9 | 46.0 | 68.7 | 51.3 | 66.4 | **94.3** |
| JevBench hard | 36.2 | 46.7 | 45.7 | 57.1 | 41.0 | 48.6 | **73.3** |
Latency/decision: 0.8B **22 ms** (RTX PRO 6000), 28 ms (M4 Max MLX), 463 ms (32-thread CPU); 1.7 GB fp16.
Games (zero-shot, options state *consequences*, never the right move): Jeff-0.8B = **6.55 Doom kills** (hand-coded bot 6.55, untrained 5.0), **10.3 Frogger crossings** (bot 10.25), **57/98 Pac-Man pellets** (bot 94.1, untrained 25.8). 2B plays *worse* despite scoring higher. It **matches a hand-coded rule bot zero-shot** on two of three games — that is the "nudge ML to be way better than random" Casey meant.

## Caveats (as published, and the traps they name)
- Small models **don't reason**: 0.8B–2B is a calibrated *chooser*, not a planner; forecasting ("a car arrives in 2 turns") is ~random.
- **Wording sensitivity is enormous**: making Frogger's goal option use the same words as every forward option took an episode from 15 → 23 crossings. Options must state consequences, not bare IDs.
- Reason-heavy benchmarks (BBH/JudgeBench/JevBench) stay far below large models — use it for classification/grounding, not multi-step thought.
- English, text only. Long-list behaviour only reliable for the v1.1 Qwen models (Gemma still caps at 26).
- Benchmark score ≠ game skill (Gemma wins benchmarks, plays worst).

## The convergence (PhysicalCoding × jeff × what we already run)
Three of our lanes meet here:
1. **Our judgment cell** (typesafe/Jev: noul/choice/score, the "pincher/filter primitive as a tunable API gate") = exactly Jeff's interface. Jeff is a **local, offline, Apache-2.0 drop-in for metered Jev calls** — and offline is the hard requirement for the boat brain (no cloud offshore).
2. **PhysicalCoding's verifier** needs a calibrated, independent decision with an `INSUFFICIENT_EVIDENCE` outcome. **A calibrated `noul` probability + threshold τ *is* that gate.** Architecture (report) + primitive (jeff) fit together exactly.
3. **Our pincher/reflex doctrine** ("route known answers in <50 ms with zero LLM; escalate the unknown") needs a decider that is *fast, free, and calibrated*. Jeff-0.8B is that decider, and its fine-tune turns domain-specific routing from ~30% → ~95% in half an hour.

## Why this can work on *our* hardware
0.8B fp16 = 1.7 GB (fits the 6 GB 4050 with room for KV cache); 2B fp16 = 4.2 GB (fits tightly). Their *training* used a datacenter GPU, but **our GPU already holds what this needs**, and Casey's hardware is idle at night. Their own fine-tune benchmarks are ~30 min (11k examples, 1 epoch) at small scale — within one night on a 4050 with a reduced batch.

## Concrete plan (spawned queue items)
- **JEFF-1 (GPU, tonight)**: feasibility probe — load Jeff-Qwen3.5-0.8B on the 4050, run a handful of `choice`/`noul` prompts, measure latency + VRAM + whether our judgment-cell contract is honoured. Deliverable: `tools/jeff_probe.py` + receipt. Cheap, decisive, and it unlocks everything else.
- **JEFF-2**: **quilt-specific fine-tune** (Casey's ask). Dataset: (situation = room/tile/query context) → (options = candidate cells/routes/answers) with labels from **our own exact evaluators** (qcell-sim exact balance; plato room truth; i2i near-matches) — i.e. **we supply the Stockfish role ourselves**. One epoch, fitted temperature, report calibration error.
- **JEFF-3**: wire a **local Jeff backend into superinstance-api `/pinch`** so the reflex layer stops needing a cloud judgment call (keeps the MCP tool surface identical).
- **JEFF-4**: **verdict gate** — `noul < τ → INSUFFICIENT_EVIDENCE` instead of a coin-flip answer (pairs with PC-2/QG5 in the qcells lane).
- **JEFF-5**: train the **qcell-oracle** as a Jeff-style chooser (spool already wants it): options = mutation classes, labels = exact-simulator crossing, consequences stated in words (the report's wording lesson).

## Relationship to Jev/typesafe
Independent project, same request format, **not affiliated with TypeSafe**. Their `test_jevbench.py` + `src/jeff/jevbench.py` give us a **public hard-tier harness** to score our own local decider against Jev's published 73.3 — a ready-made benchmark for the fleet's judgment-cell work.

---
## Addendum (00:35) — the published checkpoint, read in the clear
`decision_config.json` + `readout.safetensors` give the whole inference contract:
- **`codes`**: A…Z then two-letter codes to 254 options (note: BQ, CJ, EJ, GH-ish gaps — the code list is not a naive A…Z×A…Z product; worth a census, it looks deliberately curated). **`token_ids`**: the pinned vocab id of each code (A=32 … ASCII letters) — needed because the codes appear *as text* in the prompt.
- **`temperature` = 1.1289476733993191** — the fitted calibration constant, published rather than baked into weights.
- **`prompt_layout` = "state-first"**; `max_options` = 254; `format_version` = 1.
- **`readout.safetensors`** = single `weight` tensor **(255, 1024) bf16** = trained linear head over the base model's hidden state (1024), one class per option code + 1 extra.
- **Provenance block**: `run`, `git_commit`, plus **sha256 of every source file and uv.lock**, and `step`. Their artifact carries a receipt of the code that made it — the same discipline as our sha256 tool receipts, applied to model artifacts. **Adopt this for our own trained artifacts.**
- Base: Qwen3.5-0.8B, hybrid linear attention (3 linear : 1 full per 4 layers), attn_output_gate, hidden 1024, head_dim 256, VL-capable, bf16.

**Consequence for the fleet**: the expensive-looking part of jeff (full-weight fine-tune) is *optional*. The readout is a linear probe we can fit in minutes against **exact-simulator labels** — see DECIDE-1 G4.
