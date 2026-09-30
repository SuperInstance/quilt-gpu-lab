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
