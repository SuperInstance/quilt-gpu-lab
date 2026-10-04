# GREENHORN RECON — decomposing/verifier-gated chatbot POC survey

Lane GH-RECON · 2026-10-01 · scratch/greenhorn/ · **NOT COMMITTED** (per directive)
Target system: *chatbot that learns from judgment/verifier models + decomposes when unconfident.*

Local clones (shallow, main): `QuantumArtHack/`, `dspy/`, `RouteLLM/`, `FrugalGPT/`,
`semantic-router/`, `reflexion/`, `Voyager/`. All line citations below are
`file:line` at those clones' `HEAD`.

---

## 0. HEADLINE FALSIFICATION (read first)

**QuantumArtHack is not a chatbot repo.** It is `moth-quantum/QuantumArtHack`, a
UnitaryHack-2025 fork of `HeidelbergQuantum/ParallelQPIXL` (`README.md:1-3`) — a
**quantum image/audio encoding library** (FRQI/QPIXL embeddings, Qiskit/PennyLane/
cuQuantum backends). It has **zero** chatbot code, **zero** verifier/verdict loops,
**zero** learned selection.

**There are no mothquantum API calls in it.** Exhaustive grep over `*.py` + notebook
code cells for `mothquantum|api|http|requests|retry|seed|token|endpoint|backoff`
returns only literature DOIs (`QPIXL/qiskit/qpixl.py:11` etc.). The *only* remote API
surface is **IBM Quantum Runtime** (`QiskitRuntimeService(channel="ibm_quantum", token="...")`,
`QPIXL_decoherence_audio_fx.ipynb` cell 2) plus a vendored offline noise snapshot
(`noise_models/ibm_brisbane.pkl`, 5.2 MB).

**The real mothquantum API surface is elsewhere.** The `moth-quantum` org exists with
19+ public repos (`gh api orgs/moth-quantum/repos`): `actias-backend` (Svelte quantum
synth v2), `quantum-audio`, `MicroMoth`, `qc-parallelizer` ("optimally combining and
distributing quantum circuits"), `quantum_rng_comet` (C QRNG), `QuantumBlur/Graph/Brush`.
The commercial API is the **"Atlas Platform and API"** (marketed at
`docs.mothquantum.com`, a JS SPA — no static docs payload; not documented in any public
repo). **Verdict: public ✅ / live ✅ / but the repo is quantum-media DSP, not chatbot infra;
its API is not what we'd consume, and we do NOT need it.**

**Consequence for GH:** QuantumArtHack is *raw material for mechanisms*, not a design
template. Two of its ideas (rank-threshold compression; cyclic-multiplex + partial-trace
demux) are genuinely reusable; the rest is signal processing. The design template comes
from §2 (RouteLLM, FrugalGPT).

---

## 1. QuantumArtHack — mechanism table

| Mechanism | Code path | What it does | Repurpose for GREENHORN |
|---|---|---|---|
| **Rank-threshold compression** | `QPIXL/qiskit/qpixl.py:30-36` (also `qpixl_angs.py:45-50`, `parallel_param_qpixl.py:38-43`) | After a Walsh–Hadamard transform, `a_sort_ind = np.argsort(np.abs(a))`; then `cutoff = int((compression/100.0)*n)` zeroes the `cutoff` smallest-|coeff| entries. `compression` ∈ [0,100] is a single knob trading fidelity for circuit size. | **The single most repurposable idea.** Rank *our* cells/claims by |weight| (logprob margin, verifier score, attention mass) and zero the bottom `c%`. One continuous knob maps to "how much of the reasoning do we keep". It is *the* principled form of "compress when confident, keep when not". |
| **Zero-coefficient gate-collapse** | `qpixl.py:38-79` — `if a[i] != 0: circuit.ry(...)`, then inner `while ... a[i]==0` skips runs; CNOT pairs "cancel out" | Dropping a coefficient to 0 removes its rotation *and* the CNOTs that addressed it — the circuit gets **shorter**, not just sparser (pairs cancel; `README.md:96`). Pruning is *coupled*: kill one node and its plumbing evaporates. | Pruning a low-confidence cell should also drop its scaffolding (tool calls, re-derivations, rebuttals). Model our cell-DAG so removing a leaf collapses the plumbing — compute savings super-linear in cells removed. |
| **Run-length skip + deferred parity accumulation** | `qpixl.py:52-79`; `helper.py:156-167` (`countr_zero`), `helper.py:95` (`grayCode`) | `ctrl = grayCode(i)^grayCode(i+1)`; `pc ^= 2**ctrl`; consecutive zero angles are walked in one inner loop while `pc` accumulates, then a single `for j in range(k)` emits the surviving controls. | **Batch coalescing of no-op cells.** Accumulate the "effect" of a run of trivial/deterministic cells as a bitmask and flush once, instead of paying per-cell. Use for cheap deterministic pre-filtering before an expensive verdict pass. |
| **Cyclic index permutation (routing table)** | `helper.py:242-257` (`permute_bits(b,bitlength,shift)`), `qpixl_parallel.py:6-8` (`permutation(j,perm,total)=(j-perm)%total`) | Reversible rotation of an index by `shift`/`perm`; used to interleave N streams into disjoint circuit slices. | An explicit, invertible **lane-routing table** (which cell variant ↔ which slot). Gives collision-free multiplexing of N candidate answers and cheap demux by rotating back. |
| **Parallel multiplex: N streams, one pass, same depth** | `qpixl_parallel.py:91-185` (`cFRQI(data,...)` loops `for ind, arr in enumerate(data)` at every gate; `README.md:120-140`) | Encodes N independent arrays into one circuit at the **same depth** as one, by exploiting that each address qubit is targeted once per layer. Cost is linear in *data*, not in *streams*. | Fan-out/fan-in: run N candidate decompositions/answers in one batched pass at ~1× latency. Basis of a cheap "sample K, verify K" loop. |
| **Partial-trace demux** | `helper.py:259-292` (`decodeParallelQPIXL` → `partial_trace(state, traced_over_qubits)` at `:277`) | To read stream *d*, marginalize out every other stream's qubit, then un-permute. One multiplexed state → each stream recovered exactly. | **Isolate one cell's contribution while marginalizing the rest** — per-cell scoring that ignores cross-talk. Also a concrete API for "read out lane d of K". |
| **Angle readout (atan2) + min-max denorm** | `helper.py:217-240` (`decodeQPIXL`: `pv[i//2]=np.arctan2(state[i+1],state[i])` at `:238`); `helper.py:138-154` (`convertToGrayscale` min-max rescale) | Converts a 2-component complex pair into a **signed phase**, then rescales by data min/max. Bounded (`convertToAngles` uses `π/(2·max)`, `helper.py:116-121`). | A **signed, bounded confidence readout** from two competing scores (e.g. [accept, reject] logits): `atan2` gives a smooth ±angle, invertible, no softmax saturation. Then min-max normalize per-batch so thresholds transfer. |
| **Density-matrix = distributional state** | `QPIXL_decoherence_audio_fx.ipynb` cell 2/cell 4 (`AerSimulator(method='density_matrix')`; `rho = result.data(j)['density_matrix']`; `state_vector = np.real(np.diag(rho))`) | Represents an unresolved/uncertain state as a **probability distribution over outcomes** (diagonal of ρ) rather than a point estimate; handles noise naturally. | Store an "unconfident" cell as a *distribution over candidate outputs*, not a single string. Resolve (collapse) only when the distribution is peaked — literal "decompose while uncertain, commit when sharp." |
| **Calibrated decoherence injection** | nb cell 4 `post(decoherence, dividend, steps)` closure: `delay_ns = int(t1*1e9/dividend)/steps`, applied `decoherence` times per qubit vs per-qubit `T1s` list | Inject **controlled, physically-calibrated degradation** at a tunable level; sweep it to measure where output breaks. | (i) **Robustness/confidence probe:** degrade the model's own context and measure the point where the answer flips → a real uncertainty signal. (ii) **T1 = memory half-life:** a per-fact decay constant for memory freshness — elegant, quantitative. |
| **Job lifecycle: run→await→extract-by-index** | nb cell 4: `job = noisy_simulator.run(batch)`; `result = job.result()`; `result.data(j)['density_matrix']` | Batch submit; block on `job.result()`; index individual results out of the batch by position. | Canonical shape for our submit→verify→resubmit loop; note the **by-index result mapping** so a batch of cells keeps identity through the round-trip. |
| **Idempotent checkpoint guard** | nb cell 4: `if not os.path.exists(metadata_file_path):` wraps the whole compute; `file_name}_metadata_{tag}_c{compression}.txt` names the artifact | Compute is skipped if its named artifact already exists → resumable, restart-safe, cache keyed by (file, tag, compression). | **Free resumability for long eval runs.** Key our verdict cache by `(cell, verifier, config-hash)`; re-runs cost nothing. Nothing in our stack does this yet. |
| **Power-of-2 pad-with-zeros** | `helper.py:196-215` (`pad_0`), `helper.py:70-88` (`nextpow2`); guard `is_power_of_two` | Pad any input to the next power of two; padding is free because zeros vanish in compression. | Pad cell batches to a fixed lane count; empty lanes are free (they compress away). Fixes ragged-batch handling in the multiplex design. |
| **Batch-size-bounded streaming** | nb cell 4 `PROCESS_BATCH_SIZE = 2` + `for i in range(0,len(circuits),PROCESS_BATCH_SIZE)` | Chunked processing to bound memory. | Keep our batch math O(chunk) — matches the workspace `Memory usage must be O(chunk)` rule; a literal precedent to copy. |

---

## 2. Deep-studied projects (the TWO closest to our design)

Design has two halves — **(A) learn from judgment** and **(B) decompose/escalate when
unconfident**. The two closest codebases are the ones that implement those halves as
*runtime architecture*: **RouteLLM** (learned verifier + gate) and **FrugalGPT**
(scorer-gated cascade = literal "escalate when unconfident"). DSPy covers (A) best in
*training*, and is treated in §3.

### 2a. RouteLLM (`lm-sys/RouteLLM`, 3,006 LOC)

| Mechanism | Code path | What it does | Repurpose for GREENHORN |
|---|---|---|---|
| **The gate** | `routellm/routers/routers.py:41-43` | `if calculate_strong_win_rate(prompt) >= threshold: return strong else weak`. One comparison; threshold is caller-supplied. | Our top-level router gate: one float, one comparison, swap the payload. Cleanest possible seam. |
| **Four interchangeable verifiers** | `routers.py:38` (abstract) + impls: CausalLLM `:94-102` (5 special tokens `[[1]]..[[5]]`, returns `1 - binary_prob`), BERT `:117-130` (3-class, `1 - sum(softmax[-2:])`), MatrixFactorization `:238-246` (`pred_win_rate`), SWRanking `:177-236` (Elo MLE over nearest-neighbour arena battles, `compute_elo_mle_with_tie`) | Same interface, radically different cost/quality: LLM-judge, small classifier, learned embeddings, kNN-over-history. All return a **float in [0,1] = P(strong wins)**. | **Plug-in verifier interface.** Ship 3 verifiers behind one `score(prompt_or_cell)->[0,1]`: (a) LLM-judge, (b) local BERT (cheap, fits our GPU), (c) Elo/kNN over our own verdict history. Start with the free local one. |
| **What is learned vs hardcoded** | Learned: classifier weights / MF embeddings / Elo ratings (HF checkpoints, `routers.py:61-73, 200-215`). Hardcoded: the pairwise structure & the *decision rule shape*. | Learning happens **offline**, in the verifier only; the gate is a static comparison. | Keep the gate dead-simple and static; push **all** learning into the scorer. Avoids a hard-to-debug learned policy loop. |
| **Budget → threshold calibration** | `routellm/calibrate_threshold.py:55` | `threshold = win_rates.quantile(q = 1 - strong_model_pct)` — pick the escalation **budget**, get the gate for free from the *empirical distribution* of scores. | **You set cost, math sets the threshold.** No hand-tuning a magic number; as the verifier's score distribution drifts, recalibrate by quantile. Directly applicable to "how many cells get the expensive verifier". |
| **Score-based win-rate labels** | `calibrate_threshold.py:36-46` (`batch_calculate_win_rate`), config `controller.py:11-27` (`GPT_4_AUGMENTED_CONFIG` merges human arena battles + `routellm/gpt4_judge_battles`) | Judgment signal = **human preference battles**, augmented with **GPT-4-as-judge** ("golden label data from GPT-4"). | Our judgment source, concretely: human thumbs + LLM-judge, merged into one labeled set. The `gpt4_judge_battles` pattern is exactly "bootstrap labels with a strong verifier." |
| **Threshold validation** | `controller.py:79-88` | Rejects router-less / out-of-`[0,1]` / unknown-router combinations loudly. | Copy the fail-loud gate validation; a silent misconfigured gate is the worst failure mode in a self-improving loop. |

### 2b. FrugalGPT (`stanford-futuredata/FrugalGPT`, 2,336 LOC)

| Mechanism | Code path | What it does | Repurpose for GREENHORN |
|---|---|---|---|
| **The verdict loop (post-hoc)** | `src/FrugalGPT/llmcascade.py:121-142` | `while(1)`: ask strategy for next `(service_name, score_thres)`; call that model; **score the response text**; `if score > 1 - score_thres: break`; else fall through to the next (stronger) model. | **This is our cell-verdict loop verbatim.** Escalate *only because the produced answer was judged weak* — not because the prompt looked hard. Cheap model first, verified, escalate on failure. The accept condition `score > 1 - thres` is a ready-made contract. |
| **Trained scorer = the verifier** | `src/FrugalGPT/scoring.py:130-212` (`Score.train` fits DistilBERT/BERT/AlBERT/GPT-2 for sequence classification; `get_score` returns `softmax(logits)[1]` = P(quality)) | A **fine-tuned small transformer that predicts the quality of a (query‖answer) string**, trained on ground-truth quality labels. Local, cheap, fast, offline. | Our per-cell verifier, concretely: DistilBERT heads trainable on our own GPU box (RTX 4050; `venvs/elephant-gpu`). Learned from judgment, cheap enough to run on *every* cell. |
| **One scorer per model** | `llmcascade.py:109-118` (`build_scorers` loops `model_perf_train`) + `:186-198` (`_build_scorer`) | Calibrated **per producing model** — the scorer knows model A's failure modes ≠ model B's. | Score cells with a verifier aware of *which model produced them*. Kills the "one global quality number" confound. |
| **Strategy = learned order + per-step thresholds** | `llmchain.py:107-127` (`train`: enumerate `itertools.permutations(service_ids, ell)`, score each chain, keep best) + `optimizer.py:70-133` (`optimize`) | Grid/brute search over (which models, in what order, with what thresholds) under a **cost budget**; objective = `-accuracy`, cost constraint enforced in `f()` (`optimizer.py:74-96`). | **Learn our escalation ladder offline** from logged runs: which cell-types should go to which verifier in which order, under a token/time budget. No hand-designed pipeline. |
| **Quantile-based threshold fitting** | `optimizer.py:100-133` (`quatile2thres_batch`, `scipy.optimize.brute` over quantiles, monotonicity constraint `g()`) | Searches *quantiles* (0..1) rather than raw thresholds, then maps to thresholds via `np.quantile(d_mat, 1-q)` — scale-free, transferable across datasets. | Same trick as RouteLLM but integrated into the ladder search: tune quantiles, not magic numbers. And the monotonicity guard (`if not all(diff(qual)>=0): return 10000`) is a free sanity invariant for our ladder. |
| **Distance = 1 − score** | `optimizer.py:8-10` (`compute_dist(answers, scores) = 1 - scores[-1]`) | Uniform "distance from confident" scalar all downstream logic keys on. | One scalar, one meaning. Adopt as our internal `uncertainty = 1 - verifier_score`. |
| **Cost accounting per call** | `llmcascade.py:122-131` (`cost += MyLLMEngine.get_cost()`); `optimizer.py:53-67` (`C_mat` cumulative cost up the chain) | Every escalation carries its marginal cost; the optimizer sees cumulative cost per position. | Budget-aware decomposition: a cell only buys the expensive verifier if its expected accuracy gain beats its marginal cost. |

### Why these two and not (only) DSPy
RouteLLM and FrugalGPT put the **verdict gate in the runtime hot path** — which is where
our system lives ("decompose *when unconfident*"). RouteLLM gates **before** generation on
a prompt feature; FrugalGPT gates **after** generation on the response. **We need both**:
pre-gate (route cheap/expensive by difficulty) and post-gate (verdict the produced cell).
They are complementary, not competing, and both are ~2-3k LOC = fully auditable.

---

## 3. Survey — the rest (receipts, not vibes)

| Project | Closest mechanism | Receipt | One-line verdict |
|---|---|---|---|
| **dspy** (118k LOC) | Judgment-driven **compilation**: `BootstrapFewShot.compile(student, teacher, trainset)` (`dspy/teleprompt/bootstrap.py:84-95`) runs the teacher at `temperature=1.0` (`:190-191`), keeps only traces the **metric** accepts (`:205-210`), and writes them back as demos (`:223-250`, `_train` `:259-270`); `metric_threshold` turns a scalar metric into a pass/fail gate (`:207-210`). | `bootstrap.py:84,205,223,259` | **The "learn from judgment" engine.** A metric is a verifier; compile = distilled prompt/block from accepted traces. Steal the accept-trace-and-write-back loop. |
| **dspy** — calibration | **Guarded, reversible self-modification**: `reanchor/calibrate.py` fits per-output thresholds/cuts/weights *directly against the metric* with a **5-fold** held-out check, and **restores the original config unless the fitted behaviour wins on held-out folds** (`FOLDS=5`; "restores the original field configuration unless the fitted behavior wins"). | `dspy/teleprompt/reanchor/calibrate.py:1-28, 34-38` | **The safety pattern we most need.** Learn the gate, but only keep the change if it generalizes across folds. Reversible-by-default. |
| **dspy** — reflective evolution | GEPA proposal signature takes `examples_with_feedback` → `improved_instruction` (`teleprompt/gepa/instruction_proposal.py:13,39,45,88`) | same | Verifier *feedback text* (not just a scalar) drives the next prompt. Richer judgment channel than pass/fail. |
| **Voyager** | **Skill library ≈ our blocks**: `add_skill` writes code+LLM-authored description; `retrieve_skills(query)` = `vectordb.similarity_search_with_score(query, k=retrieval_top_k)` (`agents/skill.py:114-127`, `top_k=5` at `:18`). | `skill.py:114-127` | Blocks = embedded, retrievable skills. Vector store IS the block library; `top_k` is the retrieval budget. |
| **Voyager** — verifier | `agents/critic.py:91-114` `ai_check_task_success` = LLM-as-judge returning `{success, critique}`, retried `max_retries=5`; `:79-89` `human_check_task_success` = human y/n + critique. | `critic.py:79-134` | **Two-channel verifier: LLM judge + human.** Critique (not just success) is the learning signal. Retry-on-parse-failure is a robustness detail we'd otherwise forget. |
| **Reflexion** | **Verbal reinforcement, no weights**: `run_reflexion` loops act→execute→(on failure) `gen.self_reflection(impl, feedback)` → **re-issue with `self_reflection` in the prompt** (`programming_runs/reflexion.py:26-91`); `reflections` persisted as a list on the item (`:94`). | `reflexion.py:26,59,94` | Zero-gradient learning-from-judgment: keep a list of self-critiques and prepend them. Cheapest possible "memory of mistakes." |
| **semantic-router** | **Explicit thresholded routing**: `SemanticRouter.__call__` scores query vs route utterances, `passed = total_score >= current_threshold` per route (`routers/base.py:640-655`); threshold from encoder or `_set_score_threshold()` (`:535-546`); empty route-choice when nothing passes (`:700`). | `base.py:640-655, 535-546` | Deterministic, inspectable gate with a **calibrated per-encoder threshold** — the honest fast baseline before any learned router. |

---

## 4. RANKED STEAL-LIST — top 8, adopt in order

1. **FrugalGPT's post-hoc verdict loop** — `llmcascade.py:121-142` (`while(1) … if score > 1-score_thres: break`). *Beats building our own:* it is our exact escalate-when-unconfident contract, already proven, with the accept condition and cost accounting written.
2. **RouteLLM's budget→threshold quantile calibration** — `calibrate_threshold.py:55`. *Beats building our own:* turns a cost budget into a gate with one `np.quantile`, and self-adjusts as the score distribution drifts — no magic number to hand-tune.
3. **DSPy's guarded calibration** — `teleprompt/reanchor/calibrate.py:1-28` + `FOLDS=5` (`:50`, revert unless it wins on held-out folds). *Beats building our own:* gives self-improvement a built-in **reversal path**, which is the hardest part to retrofit and the easiest way to make a self-modifying loop safe.
4. **QPIXL rank-threshold compression** — `qiskit/qpixl.py:30-36`. *Beats building our own:* a single continuous `compression` knob with a principled `argsort(|coeff|)` rank cut, and it comes with the coupled property that pruned items' plumbing collapses too (`:38-79`).
5. **DSPy's accept-trace-and-write-back compile loop** — `teleprompt/bootstrap.py:84-270` (metric-gated traces → demos/blocks). *Beats building our own:* it is a working, cached, retry/round-aware implementation of "keep only judged-good work, then reuse it."
6. **FrugalGPT's per-producer trained scorer** — `scoring.py:130-212` + `llmcascade.py:109-118`. *Beats building our own:* a small local transformer scorer trained on quality labels runs on every cell cheaply on our own GPU, and per-producer scorers remove the biggest confound (model-specific failure modes).
7. **Voyager's embedding skill library** — `agents/skill.py:114-127` (+ `critic.py:91-114` judge). *Beats building our own:* blocks-as-embedded-skills with `top_k` retrieval is a complete, tiny block library + verdict wiring pattern.
8. **QPIXL multiplex + partial-trace demux** — `qpixl_parallel.py:91-185`, `helper.py:259-292`. *Beats building our own:* N candidates in one same-depth pass with an exact, invertible demux is a ready-made "sample K, verify K" fan-out, and `permute_bits` (`helper.py:242`) is the routing table for free.

*Runners-up (not top-8):* reflexion's self-critique list (trivial to add later), semantic-router's per-encoder threshold (use as the honest baseline), QPIXL's `pad_0` free-lane padding (`helper.py:196`).

---

## 5. Assumptions killed / corrections

- **KILLED:** "QuantumArtHack shows a chatbot learning from verifier/judgment models." — It has no chatbot, no verifier, no selection anywhere; it is a quantum image/audio *codec*. (§0)
- **KILLED:** "Extract mothquantum API call patterns (endpoints, seeds, PRF, streams, jobs)." — No mothquantum API calls exist in the repo. The only remote call is IBM Quantum Runtime; the mothquantum commercial surface is the Atlas Platform API, undocumented in public repos. (§0)
- **CORRECTED:** the "submit→verify→resubmit" mapping is a *stretch* for this repo — QPIXL has no verify step. What it honestly offers is `run(batch) → job.result() → result.data(j)` (`nb` cell 4): a **job lifecycle with by-index result identity**, which we reuse purely as plumbing.
- **CONFIRMED:** the genuinely valuable QuantumArtHack mechanisms are the *compression-by-rank-threshold* idea and the *multiplex/partial-trace* idea — architectural, not API-driven.
- **CAUTION:** FrugalGPT is a **research/demo repo** (`setup.py`, `src/service/modelservice.py` 703 LOC of local server shims; `llmcascade.py:87-119` calls `self.savestrategy`/`self.no_scorer_train` before they're set in some paths — `save()` at `:78-85` references `self.no_scorer_train` which `load()` never sets). **Steal the loops, not the plumbing.**
- **CAUTION:** RouteLLM's `SWRankingRouter` computes embeddings via a hosted `OPENAI_CLIENT` (`routers.py:220-236`) — that path needs network + spend; use the local `BERTRouter`/`MF` paths for our box.

## 6. Method / provenance (falsifiable)

- Clones (`git clone --depth 1`, verified via `git -C <dir> remote get-url origin`):
  `moth-quantum/QuantumArtHack`, `stanfordnlp/dspy`, `lm-sys/RouteLLM`,
  `stanford-futuredata/FrugalGPT` (`HEAD=2b23e6a` "update readme"), `aurelio-labs/semantic-router`,
  `noahshinn/reflexion`, `MineDojo/Voyager`.
- QuantumArtHack `HEAD = b54346d` ("Merge pull request #10 from ljcamargo/novel-audio-effect"); 72 files, ~1.6k LOC of Python.
- Line citations verified by `grep -n` against the clones at time of writing; re-run the grep in the repo to falsify.
