# REST-EM-prereg — Frozen Pre-Registration
**Experiment ID:** REST-EM-001
**Registered:** 2026-10-02 00:15 AKDT (before any loop execution; smoke run is engineering validation only)
**Author:** Lucineer (subagent), quilt-gpu-lab
**Status:** FROZEN. No edits after the full run starts; deviations must be logged in-run, never silently applied.

---

## 1. Hypothesis
Rejection-sampled self-generated SFT (ReST-EM style: generate → executable verify → select → QLoRA → repeat,
compounding over rounds from the *current* policy) improves held-out pass@1 on verifiable math tasks for a small
local model, beyond (a) the same base model with no weight updates, and (b) a one-shot oracle-SFT control of
equal training budget on experimenter-authored demonstrations.

## 2. Constraints (hard)
- ZERO metered spend: no DeepInfra / anthropic / deepseek or any paid API. Only local compute + free PyPI/HF downloads.
- Hardware: RTX 4050 Laptop 6 GB, WSL2. Ollama server at http://127.0.0.1:11434 (OpenAI-compat `/v1/chat/completions`).
- GPU seat is shared. **Seat policy:** before any torch training/eval, check free VRAM (`torch.cuda.mem_get_info` /
  nvidia-smi at `/usr/lib/wsl/lib/nvidia-smi`). Need ≥ 2.5 GB free for the 0.5B QLoRA stack; otherwise drop to
  CPU (fp32 LoRA) or wait. Never evict or crash the concurrent run (jev-net self-play has priority; serialize around it).
- The verifier is **code only** (sympy + property tests). No LLM judge anywhere in the accept/reject path.

## 3. Models
- **Policy model (treatment):** `Qwen/Qwen2.5-0.5B-Instruct` HF weights (cached locally). This is what gets trained
  and evaluated; from round ≥1 generation comes from the current policy (HF, LoRA adapter attached).
- **Round-0 / base sampler:** ollama `qwen2.5:0.5b` (q4_K_M twin of the same checkpoint). Round 0 samples the base
  policy, so the ollama twin and HF weights represent the same policy up to quantization.
- **Registered sanity check (parity):** base held-out pass@1 via ollama-q4 vs HF-bf16 must agree within ±12 pp
  (quantization noise); if not, all base sampling moves to HF and this is logged as a deviation.
- **Fallback:** if ollama is saturated by the concurrent run (chat probe > 90 s), round-0 generation falls back to
  the HF base model and the deviation is logged. Registered *before* any run.
- Exploratory-only (no gate claims): `qwen2.5:3b-instruct-q4_K_M` if VRAM ever allows.

## 4. Task set (exact, frozen)
Two families, both machine-generated with frozen seeds. Train pool and held-out sets are disjoint by construction
(different seed streams) plus an explicit string-overlap check (negative control N4).

**Arithmetic** (answer: integer). Generators, uniform per kind:
- `add2`: a+b, a,b ∈ [13, 499]
- `add3`: a+b+c, a,b,c ∈ [5, 99]
- `sub`: a−b, a ∈ [120, 999], b ∈ [11, a−5] (result ≥ 0)
- `mul`: a×b, a ∈ [12, 29], b ∈ [3, 12]
- `mixed`: (a+b)×c, a,b ∈ [5, 99], c ∈ [3, 9]
Prompt: `Compute {expr}.`

**Symbolic simplification** (answer: expression in x). Generators:
- `lin_add`: (a*x + b) + (c*x − d), coeffs ∈ [2, 12], consts ∈ [1, 20]
- `lin_sub`: (a*x + b) − (c*x + d)
- `sq_collect`: a*x**2 + b*x − (c*x**2 − d*x), coeffs ∈ [2, 9]
- `dist`: a*(x + b) + c*x, a,c ∈ [2, 9], b ∈ [2, 15]
Ground truth: `sympy.expand(simplify(expr))`. Canonical target string = `str(...)`.
Prompt: `Simplify the expression: {expr}. Give the result in terms of x.`

**Full-run sizes (frozen):** train pool 96 (48/48), held-out 96 (48/48), seeds 20261002 (train) / 20261003 (held-out).
**Smoke-run sizes (engineering, NOT gate evidence):** pool 24 (12/12), held-out 16 (8/8), same seeds.
Prompting: identical 2-shot chat prompt for generation, selection, SFT, and eval (frozen in `rest_em_loop.py`).

## 5. Verifier (executable, frozen)
1. **Extraction:** last regex match `(?is)answer\s*[:\-]\s*([^\n]+)` in the reply; strip trailing `.` and spaces.
   No match → format failure (counts as wrong).
2. **Arithmetic:** strict integer equality after `,` removal. Floats (`132.0`) are REJECTED (format is taught in prompt).
3. **Symbolic:** parse with `sympy.parsing.sympy_parser.parse_expr`, `local_dict={'x': x}`, standard transformations +
   convert_xor; input strings containing `__`, `lambda`, `;`, `import`, or free symbols outside {x} are rejected.
   Accept iff **either** (a) `simplify(parsed − target) == 0`, **or** (b) property test: numeric substitution at 5
   seeded rational points (−7/3, −1/2, 1/5, 2, 13/4) agrees within 1e-9. Both are executable checks; no LLM.
4. **Verifier self-test (negative control N1):** fixed suite of right answers (must ACCEPT 100%) and wrong answers —
   ±1 off, mangled coefficients, wrong variable, no-Answer-format, garbage (must REJECT 100%). The suite runs at the
   top of every run; any failure aborts the run before generation.
5. **Shuffle-label probe (negative control N2):** SFT for 30 steps on verifier-*rejected* samples → held-out pass@1
   must not improve ≥ +5 pp vs base. Run once in the full run (optional in smoke; skipped smoke — logged).

## 6. Arms
- **T (treatment, ReST-EM):** loop rounds k = 0..K−1 (K=3 full run; smoke K=2). Round 0 samples base policy
  (ollama twin, fallback HF); rounds ≥1 sample the current policy (HF + adapter). Each round: generate N=8
  candidates/task (full run; smoke N=4), T=0.8, top_p=0.95, max 200 new tokens → verify → select → QLoRA on winners →
  held-out pass@1 (greedy, HF current policy).
- **C1 (no-finetune control):** identical generation/verify/select bookkeeping each round, **no weight updates**;
  held-out pass@1 evaluated on the unchanged base each round. Measures selection drift/eval noise.
- **C2 (oracle-SFT control):** one-shot SFT on 48 experimenter-authored correct demonstrations (same format),
  matched training budget (steps, batch, LR) to one treatment round. NOTE (honesty): "oracle" = written by the
  experimenter-agent directly, NOT sampled from the policy; it is a strong-SFT ceiling probe, not human data.

## 7. Selection & training (frozen)
- Selection: verified-correct only; dedupe by (task, normalized answer); keep ≤ 2 per task, prefer shorter completions;
  uniform order otherwise.
- QLoRA: NF4, compute bf16, double quant; LoRA r=8, α=16, dropout 0.05, targets q/k/v_proj; lr 1e-4, AdamW,
  cosine schedule w/ 10-step warmup, batch 4 × grad-accum 2, max 150 steps/round (full) / 80 (smoke), epochs ≤ 2,
  grad clip 1.0, loss on completion tokens only. Fallbacks in order: peft-fp32 LoRA (CPU) → hand-rolled LoRA
  (same hyperparams). Adapter saved per round under `results/rest_em_adapter_r{k}/`.
- Same seed discipline: torch/numpy/random seeded (20261002) at start; ollama sampling is unseeded (logged as such).

## 8. Primary endpoint & frozen gate (full run only)
- Endpoint: held-out pass@1, greedy decoding (T=0), max 200 new tokens, current policy, frozen prompt.
- **GATE:** after K=3 rounds, treatment held-out pass@1 improves by ≥ **+10 pp absolute** vs its round-0 base score,
  AND C1 (no-finetune) improves < **+5 pp** over the same rounds, AND paired bootstrap 95% CI (10k resamples,
  per-item pairing) of (treatment_final − treatment_base) excludes 0.
- Gate is evaluated ONCE. No hyperparameter retries against held-out; tuning signal during the run is train-pool
  verified-rate only. Sign consistency across both task families is reported (arith Δ and symbolic Δ separately).

## 9. Honesty rules
- All reported numbers come from logged runs; no post-hoc exclusions; smoke numbers labeled as smoke numbers.
- Deviations (ollama fallback, device drops, OOM aborts) logged in-run and reported in the results JSON `honest_notes`.
- If the gate fails, it fails — negative results get the same writeup as positive ones.
- Known confound, declared up front: ollama-q4 vs HF-bf16 quantization gap at round 0 (mitigated by parity check §3).

## 10. Stopping rules
- Abort + report honestly: OOM twice in a round; verifier self-test failure; < 3 distinct winners in any round
  (nothing to train on); held-out contamination detected (N4).
- GPU seat: if concurrent run's VRAM footprint grows so free < 2.5 GB, pause (retry loop, max 10 min) then drop to CPU.

## 11. Deliverables
- `proposals/runs/REST-EM-prereg.md` (this file, frozen)
- `experiments/rest_em_loop.py` (harness; `python -m py_compile` clean)
- `results/rest_em_smoke.log` (≥ 2 full cycles of arm T, mini C1/C2 code paths, verifier suite)
- `results/rest_em_smoke.json` (honest smoke numbers + honest_notes)
- Full run (separate, later): `results/rest_em_full.json` — the only numbers the gate applies to.
- NO git commits — the keeper folds + commits.

---

## Post-smoke annotation (2026-10-02 00:40 AKDT — added AFTER the smoke run, BEFORE the full run)
**This is an annotation, not an amendment. The frozen spec above is unchanged.** Observations from the
engineering smoke (24-task pool / 16-task held-out / N=4 / 2 rounds — NOT gate evidence):

1. **Ceiling-effect risk (the big one):** base held-out pass@1 was already **0.8125** (arith 0.875, symb 0.75)
   under the registered 2-shot prompt. The registered +10 pp absolute gate has only ~19 pp of headroom; a
   harder task distribution (e.g. 3-digit × 2-digit mul, nested parens, mixed-variable symbolic) would give
   the loop room to show gains. Decision deferred to the keeper: either accept the ceiling risk as registered,
   or log a dated amendment raising difficulty BEFORE the full run launches. Do not tune after seeing full-run data.
2. **Controls must run as separate processes/arms in the full run.** In the single-process smoke, C1's and
   C2's evals unavoidably saw the treatment-trained adapter (their eval numbers are contaminated; only their
   gen/selection stats are valid). The full run must instantiate each arm fresh (treatment / C1 / C2 separately).
3. **Round-0 generation fell back to HF** by the registered parity rule (|ollama−hf| = 0.125 > 0.12 at n=8;
   one-task noise at that n). Registered tolerance should be evaluated at the full held-out n, or round 0
   should just use HF directly — the HF bf16 base is the exact twin of the trained checkpoint (cleaner
   internal validity); ollama remains useful as an independent sampler/parity check.
4. **Smoke outcome (honest):** 2 full cycles executed; held-out 0.8125 → 0.875 → 0.8125 (net Δ 0.0, one task
   flipping at n=16); on-pool verified rate rose 60.4% → 65.6%. Verifier suite 8/8 accepts + 12/12 rejects.
   QLoRA NF4 (peft), 737,280 trainable params, only 6 optimizer steps/round at smoke scale — under the frozen
   budget, winner volume scales with pool size in the full run.
5. **Seat contention is real:** co-tenant ollama run drove vram_free to 0.00 GB mid-run; training survived
   inside the pre-reserved allocator pool, but the full run should re-check free VRAM before each train step
   batch and pause per §10 when possible.
