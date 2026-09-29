# C2 attempt-3 — degenerate-output fix (frozen delta from attempt-2)

**Pre-registered 2026-09-29 11:41 AKDT, before any v3 GPU run.** Delta only —
everything not listed below is frozen from `C2-world-smoke-plan.md` /
attempt-2 (`experiments/c2_world_smoke.py`,
`results/c2_world_smoke.attempt2-degenerate.json`).

## Diagnosis (evidence from the model snapshot)

Attempt-2 "passed" its gate with degenerate text: V-task `"6. 6. 6. …"`,
I-task `"_what is most likely to happen_"` ×9. Three findings:

1. **Greedy contradicts the shipped runtime default.** Snapshot
   `generation_config.json` is exactly:
   `{"_from_model_config": true, "bos_token_id": 1, "do_sample": true,
   "eos_token_id": 11, "pad_token_id": 0, "transformers_version": "4.57.1"}`.
   The model's own default is **sampling** (`do_sample: true`).
   **`temperature`, `top_p`, `top_k`, `repetition_penalty` are ABSENT from
   the file** — the config delegates them to library defaults. Attempt-2
   forced `do_sample=False` (greedy); on this MoT reasoner greedy loops.
   Prime suspect.
2. **Custom prompt broke the repo's own example pairing.** Snapshot
   `assets/example_reasoning_prompt.json` pairs
   `example_reasoning_input.png` with:
   `"The task is to put flower into the red bottle. Generate a plan
   consisting of subtasks for accomplish the task."` (`max_tokens: 4096`).
   The README documents this exact pairing producing coherent CoT + plan.
   Attempt-2's custom anticipation prompt was off-pairing, and the I-task
   degeneracy was a literal echo of our own prompt tail — classic
   prompt-echo under greedy decoding. Second suspect.
3. **Chat-template kwargs.** `chat_template.jinja` defaults
   `enable_thinking=True`; the generation prompt emits
   `<|im_start|>assistant\n<think>\n`. The README's reference vLLM example
   relies on that default ("Thinking is enabled by default") and only passes
   `enable_thinking: False` to disable. Attempt-2 already got the default —
   v3 pins it **explicitly** so template drift can't silently flip it.
   Corollary: with thinking on, 64 new tokens truncates mid-CoT (README
   recommends `max_tokens=4096`); the gate can still clear on CoT text, but
   a truncating cap invites another degenerate-looking receipt.

## Frozen delta (exact values, vs attempt-2)

1. **Generation params** (both tasks):
   `do_sample=True, temperature=1.0, top_p=1.0, top_k=50,
   repetition_penalty=1.0`. Rationale: `do_sample=true` is the only sampling
   directive in `generation_config.json`; the four numeric values are absent
   there, so they are pinned explicitly to the transformers `GenerationConfig`
   defaults (1.0 / 1.0 / 50 / 1.0) to make the run reproducible regardless of
   library-version drift. No invented repetition penalty — stay on the
   model's shipped distribution. `torch.manual_seed(0)` before each task so
   the sampled run is reproducible.
2. **I-task prompt source:** loaded verbatim at runtime from snapshot
   `assets/example_reasoning_prompt.json` (`["prompt"]` — the flower/bottle
   planning prompt above). The JSON's `max_tokens: 4096` is recorded but
   capped per item 4.
3. **Chat template:** `apply_chat_template(..., add_generation_prompt=True,
   enable_thinking=True)` — explicit pin of the reference default.
4. **`MAX_NEW`: 64 → 256.** Budget-checked: V-task worst case
   256 / 2.98 tok/s ≈ 86 s; load (~42 s) + both tasks ≪ 1800 s guard wall.
5. **V-task prompt UNCHANGED** ("Watch this clip. What is happening, and
   what is most likely to happen next?"). No repo example prompt exists for
   video *reasoning* — the AV clips are documented only as inverse-dynamics
   generator inputs — so the lab's anticipation question stands; sampling is
   the only change on that task.

**Frozen from attempt-2:** NF4 loader (bnb, double-quant, bf16 compute,
device_map auto), ffmpeg `fps=1,scale=640:-2` 8-frame grab (list-form
subprocess — no shell strings, house law), defensive processor path
`videos=[frames]` → `images=frames`, guard.py two-stage wrapper (1 GB free
floor, 80 °C ceiling, 1800 s), output schema + throughput booking.

## Gate (unchanged from attempt-2)

**KEEP** iff ≥ 1 of 2 tasks completes with **≥ 24 new tokens of
scene-relevant** text (relevance judged in the booking, verbatim text kept).
**KILL** = both tasks fail/crash. Throughput numbers book regardless.

## Artifacts

`experiments/c2_world_smoke_v3.py` · `results/c2_world_smoke_v3.json` ·
this plan. No GPU execution during authoring; the bridge commits centrally.
