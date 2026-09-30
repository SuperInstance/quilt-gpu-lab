# DECIDE-1 (pre-reg, frozen before firing) — the read-sideways decision cell on the 4050
Motivated by: Casey 2026-09-30 (jeff + PhysicalCoding directives). Mechanism source: "A Decision Model Is One Token Position and a Softmax" (Medium, 2026-09). Claim there: a decision model = an LM **stopped at one position and read sideways** — put indexed options in the prompt, end with `choice_index:`, then read the **probability distribution across the option digits at that position** (do not read the generated token). No text out; floats out. `noul` = Bernoulli 0..1; `choice` = confidence + distribution; `score` = rubric position; questions in parallel cost ~1.

## Hypothesis
We can run this cell **locally, zero-shot, un-tuned, on the RTX 4050** with an open 0.8B, and its sideways distribution is **better than random** at picking the simulator-verified best option in our own qcells lane — i.e. a tiny local model nudges ML above random *before* any fine-tune, exactly as Casey framed it.

## Setup
- Model: `mstrasser/Jeff-Qwen3.5-0.8B` (Apache-2.0 weights, 1.7 GB fp16) via local transformers 5.17.0 / torch 2.14.0 (pins already match our venv). No API, no network at inference.
- Cell: `tools/decision_cell.py` — prompt = state + K questions, each ending with `choice_index:`; one forward pass; read logits at each marker position; softmax over the digit-token ids with a fitted temperature; return per-option probabilities, chosen option, confidence.
- Task (auto-labelled, free): qcells-lane **mutation choice**. Champion state recorded from a QG2-style rollout; present 4 candidate mutations with **consequences stated in words** (the report's wording lesson); label = the mutation with the highest **exact** balance from `tools/qcell_sim.py`. 64 questions held out; no training on them.
- Random baseline = 1/4 = 0.25.

## Frozen gates (before firing)
- **G1 MECHANISM SANITY**: on a trivially decidable control set (e.g. "which is larger", 16 items, 2 options), accuracy ≥ 0.75. **If G1 fails, STOP and diagnose the readout (token ids / marker position / template), never re-roll.**
- **G2 BEATS RANDOM (zero-shot)**: on the 64 lane questions, accuracy > 0.25 with a one-sided binomial test p < 0.01, and 95% CI reported. Prediction: 0.35–0.65. Secondary: is the *top-1 probability* calibrated (reliability bins) and does abstention (max-prob < τ) concentrate the errors?
- **G3 FIT ON OUR HARDWARE**: peak VRAM ≤ 6 GB, median latency per decision reported (target: one-pass, well under the 114–212 ms Jev API round-trip); record whether `noul`/`score` render sanely.
- **EXPLORATORY (labelled post-hoc)**: temperature fit; effect of stating consequences vs bare option text (the README says wording is enormous — test it here); parallel-K cost.

## Deliverables
`tools/decision_cell.py` (named, single-file, cell-slot-able per the tool doctrine), `results/decide1/decide1_results.json`, RESULTS.md entry, and — if G2 holds — a local-backend candidate for superinstance-api `/pinch` (JEFF-3).

## Honest caveats to record
Zero-shot accuracy may disappoint (0.8B, reasoning-free). That is still a result: it sets the baseline that a one-epoch fine-tune (Jeff recipe) must beat. The Medium piece also notes "one paper broke" Jev's benchmark — treat every published figure as a hypothesis, ours included.

---
## AMENDMENT 1 (pre-fire, 2026-09-30 00:35 AKDT) — the readout is a *trained linear head*, not just a sideways softmax
Inspecting the published checkpoint (`jeff-0.8b`) before firing:
- `decision_config.json`: `codes` = A…(254 two-letter codes), `token_ids` = their **exact vocab ids** (A=32 … =ASCII letters), **`temperature` = 1.1289476733993191** (the fitted calibration constant, published in the clear), `prompt_layout = "state-first"`, `max_options = 254`, `base_model = Qwen/Qwen3.5-0.8B`, plus a **provenance block of sha256 hashes for every source file** (train.py, model.py, encoder.py, decoder.py, optim.py, evaluate.py, types.py, events.py, uv.lock) and the training `step` (1258).
- `readout.safetensors`: **one tensor, `weight`, shape (255, 1024), bf16.** 1024 = the base model's `hidden_size`; 255 = 254 option codes + 1 extra class.
⇒ The operative mechanism is: run the frozen LM (state-first layout, codes in the prompt) → take the **hidden state at the readout position** → **`softmax(W·h / T)`** with a **trained 255-class linear head** and the **fitted temperature**. The Medium post's "one token position and a softmax" is the *shape* of the interface; jeff's actual edge is that the readout is **fitted** (and that the codes' token ids are pinned exactly).
⇒ Consequence for us, and it is a big one: **the readout can be trained without touching the base model.** With our exact simulators (qcell-sim) as labelers, fitting `W` is logistic regression on frozen 1024-d features — minutes of GPU, not the ≈2 h full-weight fine-tune. Full-weight fine-tuning then improves the *representation*; the readout-only path is the cheap "nudge ML above random" version Casey asked for.
Additional arch notes: base is a **hybrid linear-attention** Qwen3.5 (24 layers, 3 linear : 1 full attention, attn_output_gate, head_dim 256, hidden 1024) and it is a **VL-capable** model (Qwen3VL processor, image/video tokens).

### G4 (added, frozen before firing)
- **G4 READOUT LADDER**: on the same 64 held-out lane questions, compare three readers — (a) **zero-shot sideways softmax** over the pinned code token ids; (b) **fitted temperature only** on (a); (c) **trained 255-class linear readout** on frozen hidden states (fitted on a disjoint set of lane questions, exact-simulator labels). Prediction: (c) > (b) > (a) ≥ random. Any ordering is reportable; (a)≈(c) would mean the base model already exposes the decision linearly, (c)≫(a) reproduces jeff's claimed value of a fitted readout.
