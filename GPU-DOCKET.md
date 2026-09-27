# GPU-DOCKET — the RTX 4050's standing agenda

A ranked docket of experiments the local agent can actually run on the
fleet's **RTX 4050 Laptop (6 GB GDDR6, Ada AD107, ~2560 CUDA cores)**.
Every item here is chosen because a 6 GB card can *genuinely* run it AND
because the local GPU has an edge a cloud API does not: **no per-call
cost, tight iteration loops, custom kernels, privacy, and reproducible
overnight batch runs.** Each produces a *booked, reusable result* for the
fleet — a benchmark table, a tiny checkpoint, a scaled fold finding, or a
kernel speedup number — logged the same honest way [RESULTS.md](RESULTS.md)
already logs E1–E4.

This is an agenda, not a promise. Verdicts are honest:
**KEEP / KILL / INCONCLUSIVE / ABORTED**, and the ledger keeps all of them.
When the agent starts a docket item it writes a real `experiments/dN_*.py`
module, adds a `QUEUE.md` line (wire it into `runner.EXP_MOD`), and lets the
existing [guard.py](guard.py) watchdog hold the thermal/VRAM floor.

---

## The 4050's real envelope

The [guard](guard.py) refuses to start below **1 GB free** and aborts if
free VRAM drops under 1 GB or the die passes 80 °C. Under WSL2 + the
desktop compositor, plan for a **working budget of ~4.5–5.0 GB**, not the
nameplate 6. Design to that number; the guard is the backstop, not the plan.

**What fits (build here):**

| Workload | Realistic on 4050 (6 GB) |
|---|---|
| QLoRA fine-tune (4-bit NF4 base + LoRA, grad-checkpoint, batch 1, seq ≤1024) | **≤1.5B comfortable (~4 GB); 3B tight (~5 GB)** |
| Quantized inference | 1–3B at 4/8-bit with room to batch; **7B at 4-bit batch-1, short context (~4.5 GB weights + small KV)** |
| Sentence-embedding models (bge-small/gte-small, ~130 MB) | trivial VRAM, **large batches fine** — the fold-reader workhorse |
| Small from-scratch nets (≤ a few M params) | trivial; seconds/epoch on CUDA (see E1) |
| Statevector quantum sim (complex64, in-place gates) | **~26 qubits comfortable, ~28 with care** (2^28·8 B ≈ 2.1 GB); **~30 in fp16** for entropy-grade use |
| Ternary / custom CUDA kernels (CuPy/Triton) | **ideal** — compute-bound, tiny memory, fast to iterate |

**What does NOT fit (do not queue it):**

- Full (non-LoRA) fine-tune of 7B+ (needs tens of GB of optimizer state).
- Training or full fine-tune of FLUX / any diffusion model (tens of GB).
- Large-batch training of anything >3B.
- 13B+ inference even at 4-bit (≥7 GB weights alone).
- Long-context (≥16k) 7B inference — the KV cache blows past 6 GB.
- Statevector ≥31 qubits (≥16 GB). Full-precision >30 is a cloud job.

**Hygiene for every item (see footer):** seed everything (the lab seed is
`2718`), pin a `requirements.txt`, never commit a checkpoint >100 MB (use a
GitHub Release or note the local path in RESULTS), and **never** print,
log, or commit a secret. API keys only ever go to their own service.

---

## The ranked docket

Ranked by (fleet value) × (how uniquely local-GPU wins) × (certainty it
fits 6 GB). D1–D3 are the highest-confidence, highest-leverage bets.

---

### D1 — Look-Again at scale: the fold/oracle reach-bound sweep
**Repo:** jev-quilt (read) → commit artifact to **quilt-gpu-lab** branch `claude/d1-look-again-scale`
**Rank: 1 (do this first).**

**Fleet question it answers.** G21 showed *Look-Again beating best-single*
by **buying a symbolic reader at counting-addresses** (Law 7, the Reach
Bound: a fold can't land a truth no reader's evidence reaches; raise the
ceiling by buying a reader with independent reach). G21 was a small
demonstration. **Does the effect hold — and where does the reach bound
actually bite — at N in the thousands of items and dozens of readers?**
Book the curve: marginal ceiling-lift per bought reader vs reader
independence.

**Why LOCAL GPU uniquely wins.** This is tens of thousands of
embedding + fold evaluations (items × readers × trials). On a cloud API
that is a per-call bill and a rate limit; locally it is a free overnight
batch. A `bge-small-en` / `gte-small` encoder is ~130 MB and runs enormous
batches on the 4050 — the whole sweep is embarrassingly parallel and costs
nothing to re-run when the design changes.

**Concrete steps.**
1. `pip install sentence-transformers torch --index-url ...` (CUDA build); pin versions.
2. Build a reader bank: (a) 2–3 **dense** readers = different local embedding
   models (`bge-small-en-v1.5`, `gte-small`, `all-MiniLM-L6-v2`), each folding
   content-addressed evidence under its **own** weights (Law 6); (b) 1+
   **symbolic** reader = the G21 counting-address reader (exact, orthogonal
   reach — reaches truths the dense readers structurally cannot).
3. Assemble an item set of ≥2,000 (claim, evidence, gold) triples — reuse
   jev-quilt vectors (`vectors/g20*_reader_vectors.json`) and/or generate
   with D5's dataset. Encode all evidence once on GPU (cache the tensor).
4. For each subset of readers, compute the fold verdict (the oracle *chord* —
   agreement/resonance, not a single witness) and score vs gold. Sweep:
   best-single vs Look-Again ensemble; ablate the symbolic reader in/out;
   plot **ceiling-lift vs number of independent readers bought**.
5. Bootstrap CIs over items (seed 2718). An honest null (buying a
   *correlated* reader gives ~0 lift) is a crown jewel — book it.

**VRAM / time.** <2 GB (encoders + cached evidence tensors). Full sweep of
2k items × ~5 readers: minutes to low tens of minutes on the 4050; fits the
30-min guard budget per configuration.

**Artifact.** `experiments/d1_look_again_scale.py` + a results block:
a table (best-single / Look-Again / +symbolic) with CIs, and a
`reach_bound_curve.json` (lift vs readers). Commit code + JSON to
`claude/d1-look-again-scale`; append the verdict to RESULTS.md.

**DONE check.** RESULTS entry with a reproducible JSON result and a verdict.
**KEEP** iff Look-Again beats best-single beyond overlapping CIs AND buying
the independent symbolic reader lifts the ceiling more than buying a
correlated dense one. Otherwise KILL/INCONCLUSIVE with the booked reason.

---

### D2 — qthe ternary matmul kernel: the honest speedup number
**Repo:** qthe (read-only reference) → commit kernel + bench to **quilt-gpu-lab** branch `claude/d2-ternary-kernel`
**Rank: 2.** *(Do not edit qthe — read `qthe.mjs`/`SPEC.md` as the oracle.)*

**Fleet question it answers.** qthe's whole premise is *data-is-geometry,
control-is-physics* with a ternary operator `Ψ(τ) ∈ {0,+1,−1,i}` and the
split-channel pass `y_j = Σ_k Ψ(τ(w))·d(w)·x_k`. SPEC Layer 2 leaves the
performance claims (C1) **open and priced**. **Is there a real, measurable
throughput win from ternary (add/sub/skip) matmul over an fp16 baseline on
this GPU — and is our kernel byte-exact against the reference on Layer 0
integer arithmetic?** Book the speedup, or book the honest null.

**Why LOCAL GPU uniquely wins.** Custom-kernel iteration is exactly what a
cloud text API cannot do at all, cheaply or otherwise. Ternary GEMM is
compute-bound and tiny in memory — the 4050 is *ideal*: you can write,
profile, and re-tune a CuPy `RawKernel` / Triton kernel in a fast local
loop, dozens of times a night, for free.

**Concrete steps.**
1. `pip install cupy-cuda12x` (or Triton). Pin versions.
2. Reimplement the qthe split-channel pass as a GPU kernel: pack weights as
   ternary `{−1,0,+1}` (τ=1/2/0) with the τ=3 Abstain path handled per SPEC;
   real channel = Σ(τ=1)d·x − Σ(τ=2)d·x, imag = Σ(τ=3)d·x.
3. **Parity gate first (Law 0 of the house — determinism or it didn't
   happen):** run the *integer* Layer-0 pass on random inputs and assert
   **byte-exact** equality against the `qthe.mjs` reference (shell out to
   `node qthe.mjs` on the same vectors, or port the reference check). No
   speedup claim is valid until parity is green.
4. Benchmark ternary kernel vs an fp16 cuBLAS `matmul` baseline across
   sizes that fit (e.g. 1024², 2048², 4096²), warmup + `cuda.Event` timing,
   report median of ≥50 runs, seed 2718. Pre-register the floor: ternary
   must beat fp16 by a stated margin to count as a win.

**VRAM / time.** <1.5 GB even at 4096². Whole benchmark: minutes.

**Artifact.** `experiments/d2_ternary_kernel.py` + `ternary_kernel.cu`/kernel
source + a `ternary_bench.json` table (size → fp16 ms, ternary ms, speedup)
and a `parity: PASS/FAIL` field. Commit to `claude/d2-ternary-kernel`.

**DONE check.** RESULTS entry: parity **PASS** (mandatory) + the speedup
table. **KEEP** iff parity holds and ternary beats fp16 past the
pre-registered margin at ≥1 size. A parity PASS with *no* speedup is still a
KEEP-worthy booked null (prices C1 honestly). Parity FAIL → KILL the kernel,
book the bug.

---

### D3 — Push the qubit ceiling: a GPU statevector executor for micromoth
**Repo:** micromoth-quilt (read) → commit executor + table to **quilt-gpu-lab** branch `claude/d3-statevector-ceiling`
**Rank: 3.**

**Fleet question it answers.** Statevector sim is exponential in qubits, and
the real Moth QRNG has hard limits (no-CORS, qpu-zero extractable bytes) — so
a strong **local simulated quantum layer** is genuinely valuable for the
fleet's quantum-wow / QRNG-sim work. micromoth is pure-Python and chokes well
before the interesting regime. **How many qubits can the 4050 actually
simulate, and how much faster than CPU — and can we emit entropy-grade
QRNG bytes from a simulated Bell/Hadamard circuit at that scale?**

**Why LOCAL GPU uniquely wins.** The bottleneck is memory bandwidth over an
exponential state, not tokens — a GPU is the right tool and a text API is
useless here. Overnight, free, reproducible, and it raises a *ceiling the
whole fleet inherits*.

**Concrete steps.**
1. Write a GPU statevector executor that consumes a micromoth `QuantumCircuit`
   (read `micromoth.py` for the gate set) and applies gates **in place** on a
   `torch`/`cupy` `complex64` state — apply single/two-qubit gates by index
   math (stride gather/scatter), no full-state copy per gate.
2. **Correctness gate:** for n ≤ 12, assert the GPU statevector matches
   micromoth's own simulator to fp tolerance on a battery of circuits
   (H, CX, Bell, GHZ, random Clifford). Determinism: same seed → same state
   hash.
3. Sweep n upward under the guard until it aborts; record the **max n** that
   completes within budget for complex64, then repeat in **fp16** (~+1–2
   qubits, entropy-grade only). Time each n; compute GPU-vs-CPU speedup.
4. QRNG deliverable: from an n-qubit all-H (or Bell-chain) circuit, sample
   measurements → bytes; run a cheap entropy sanity check (byte histogram,
   monobit/χ²). This is the *local* answer to the Moth QRNG byte limit.

**VRAM / time.** The point is to use the budget: complex64 at 2^28 ≈ 2.1 GB;
target **~26 qubits comfortable, ~28 with care**, ~30 fp16. Per-n run seconds
to a few minutes.

**Artifact.** `experiments/d3_statevector_ceiling.py` (reusable GPU executor)
+ `qubit_ceiling.json` (n → dtype, ms, GPU/CPU speedup, max-n-reached) +
a small QRNG entropy report. Commit to `claude/d3-statevector-ceiling`.

**DONE check.** RESULTS entry with the correctness gate (n≤12 matches
micromoth) + the ceiling table. **KEEP** iff correctness holds and max-n
materially exceeds pure-Python micromoth with a booked speedup. The executor
is the reusable win regardless of the headline number.

---

### D4 — QLoRA a local Fleet-Radio / canon reader
**Repo:** jev-quilt (probe battery + doctrine) → adapter to Release, eval to **quilt-gpu-lab** branch `claude/d4-canon-lora`
**Rank: 4.**

**Fleet question it answers.** `jev_oracle.py` runs its canon/distortion
probe battery through a paid cloud backend (TypeSafe/DeepSeek). **Can a
QLoRA-tuned ≤1.5–3B model run the same doctrinal read *locally* — free,
private, offline — closely enough to be the fleet's first-pass gatekeeper**,
reserving the paid oracle for the hard chord?

**Why LOCAL GPU uniquely wins.** QLoRA of a ≤3B model is *the* canonical
≤6 GB training job — 4-bit NF4 base + small LoRA adapters + grad
checkpointing fits with room to spare. Cloud fine-tuning is expensive and
slow to iterate; here you tune, eval, and retune in one overnight loop at
zero marginal cost, and the model/data never leave the laptop (privacy).

**Concrete steps.**
1. `pip install transformers peft bitsandbytes accelerate datasets` (pin all).
2. Base: a ≤1.5B instruct model (comfortable) or 3B (tight, batch 1). Load
   4-bit NF4 (`BitsAndBytesConfig`), enable gradient checkpointing.
3. Train data: the D5 dataset (canon vs distortion probe → verdict), or seed
   from jev-quilt's doctrines + `PROBES` in `jev_oracle.py`. Format as the
   probe → yes/no + short justification.
4. QLoRA config: `r=16, alpha=32`, target attn/MLP proj, batch 1 +
   grad-accum, seq ≤1024, 1–3 epochs, seed 2718.
5. Eval on a **held-out** probe set vs the base model (and, if a key is
   present, spot-agreement vs the cloud oracle — key stays in its own env,
   never logged).

**VRAM / time.** ~4 GB (1.5B) to ~5 GB (3B, tight). 1–3 epochs on a few
thousand examples: overnight-scale but each eval loop is minutes.

**Artifact.** LoRA adapter (typically <100 MB — if larger, attach to a
GitHub **Release**, do NOT commit the weights) + `experiments/d4_canon_lora.py`
+ `d4_eval.json` (base vs tuned accuracy on held-out probes). Note the local
adapter path in RESULTS. Commit code + eval to `claude/d4-canon-lora`.

**DONE check.** RESULTS entry with base-vs-tuned held-out accuracy. **KEEP**
iff tuned beats base by a pre-registered margin on held-out probes. A tuned
model that fails to beat base is a booked KILL — the fleet keeps paying the
cloud oracle, honestly.

---

### D5 — Overnight dataset foundry: distill a fold-reader training set
**Repo:** feeds D1/D4 → dataset to **quilt-gpu-lab** branch `claude/d5-probe-foundry`
**Rank: 5.**

**Fleet question it answers.** D1 and D4 both need labeled (claim, evidence,
verdict) data at volume. **Can we generate a reproducible, versioned probe
dataset locally** — canon vs distortion pairs grounded in jev-quilt doctrine —
instead of paying per-token to a cloud model for every regeneration?

**Why LOCAL GPU uniquely wins.** Bulk generation is the textbook overnight
batch job: thousands of generations at **zero API cost**, fully private, and
re-runnable byte-for-byte when the recipe changes. A cloud API charges every
time and you can't pin the exact weights.

**Concrete steps.**
1. Load a 7B instruct model at 4-bit (batch-1, short context) **or** a 3B at
   4-bit with light batching — whichever the guard tolerates.
2. Seed prompts from jev-quilt doctrines (`README.md`, `JEV_ORACLE_SPEC.md`)
   and the `jev_oracle.py` PROBES: generate paraphrase-canon (label:canon) and
   adversarial-distortion (label:distortion) pairs, plus counting-address
   items for D1's symbolic reader.
3. Deduplicate (embedding-NN with the D1 encoder), content-address each item
   (sha256), split train/held-out by hash so D4's eval is honest.
4. Version: write `probes.jsonl` + a `recipe.json` (model id, seed, prompts,
   counts) so the set is reproducible.

**VRAM / time.** ~5 GB (7B-4bit batch-1) or ~4 GB (3B). Thousands of items:
a genuine overnight run — exactly what the standing cron loop is for.

**Artifact.** `probes.jsonl` (if >100 MB → Release; else commit) +
`experiments/d5_probe_foundry.py` + `recipe.json`. Commit to
`claude/d5-probe-foundry`.

**DONE check.** RESULTS entry with dataset stats (counts per label, dedup
rate, train/held-out split by hash) and the reproducibility recipe. **KEEP**
iff the set is content-addressed, split cleanly, and D1 or D4 can consume it.

---

### D6 — A tiny "fun" scorer + ranked seed bank for cargo-line-tycoon
**Repo:** cargo-line-tycoon (procgen) → scorer + seed bank to **quilt-gpu-lab** branch `claude/d6-fun-scorer`
**Rank: 6.**

**Fleet question it answers.** cargo-line-tycoon procgens worlds; the game
would ship better if it could **pre-select high-variety, high-"fun" seeds**
instead of rolling blind. **Can a <1M-param from-scratch scorer, trained on a
cheap fun-proxy (route diversity, resource-balance, connectivity entropy),
rank procgen seeds well enough to pre-bake a curated seed bank?**

**Why LOCAL GPU uniquely wins.** Two loops that are free and fast locally and
awkward/expensive on a cloud API: (1) generate + featurize thousands of
procgen worlds, (2) train a tiny net over them in seconds/epoch (cf. E1's
150k-param encoder). Overnight it can score *every* seed in a range.

**Concrete steps.**
1. Batch-run the cargo-line-tycoon procgen over thousands of seeds; extract
   scalar features per world (path count, avg route length, resource entropy,
   graph connectivity). Define a transparent fun-proxy target from features
   (documented, not magic).
2. Train a tiny MLP (≤1M params) to predict the proxy from raw world tensors,
   seed 2718 — mostly a distillation/consistency check that the net learns
   the proxy from raw structure.
3. Score a large seed range; emit the top-K as a ranked **seed bank**.

**VRAM / time.** Trivial (<1 GB). Procgen batch is CPU/GPU mixed; training is
seconds/epoch. Fits the guard budget easily.

**Artifact.** `experiments/d6_fun_scorer.py` + tiny checkpoint (<100 MB, commit
ok) + `seed_bank.json` (ranked seeds + scores) for the game to ship. Commit
to `claude/d6-fun-scorer`.

**DONE check.** RESULTS entry with held-out rank correlation (predicted vs
proxy) and the seed bank. **KEEP** iff the scorer ranks held-out seeds better
than random AND the top-K are qualitatively more varied. Otherwise book the
KILL — the fun-proxy was the weak link, and that's a finding.

---

### D7 — Quantization-drift probe for the local reader (portability)
**Repo:** extends the queued E5 → drift table to **quilt-gpu-lab** branch `claude/d7-quant-drift`
**Rank: 7.**

**Fleet question it answers.** The lab already has **E5** queued
("int8 vs fp16 embedding drift: does room-sense survive quantization for
portable deployment?"). Generalize it to the fold readers and the D4 model:
**does the *verdict* survive fp16 → int8 → 4-bit quantization**, so the local
reader can deploy on even smaller edge hardware without changing its calls?

**Why LOCAL GPU uniquely wins.** Measuring per-precision drift means running
the same inputs through fp16 / int8 / 4-bit locally and diffing — free,
repeatable, and impossible to do on a black-box cloud endpoint whose
quantization you don't control.

**Concrete steps.**
1. Take the D1 encoder(s) and/or the D4 model; run a fixed held-out probe set
   through fp16, int8 (`bitsandbytes` 8-bit), and 4-bit NF4.
2. Measure embedding drift (cosine to fp16 reference) and, for the reader,
   **verdict-flip rate** (fraction of probes whose KEEP/KILL decision changes).
3. Report the precision → drift / flip-rate curve; find the smallest precision
   whose flip-rate stays under a pre-registered ceiling. Seed 2718.

**VRAM / time.** <2 GB. Minutes per precision.

**Artifact.** `experiments/d7_quant_drift.py` + `quant_drift.json` (precision →
mean cosine drift, verdict-flip rate). Commit to `claude/d7-quant-drift`;
cross-link the closed E5 line.

**DONE check.** RESULTS entry with the drift/flip table. **KEEP** iff some
sub-fp16 precision holds flip-rate under the ceiling (portable deploy is
green). If every quantization flips too many verdicts, that's a booked KILL:
the reader is not portable below fp16, and the fleet ships it at fp16.

---

## Safety / hygiene footer (non-negotiable)

- **Secrets:** never print, log, or commit an API key or any secret value.
  A key only ever travels to *its own* service (e.g. the JEV/TypeSafe key to
  TypeSafe, nowhere else) and only from its own env var — never into a URL,
  header, payload, or results file of an unrelated service. If a probe needs
  the cloud oracle, read the key from env at call time and keep it out of every
  artifact.
- **No large checkpoints in git:** never commit a file >100 MB. LoRA adapters,
  statevector dumps, and datasets that cross the line go to a GitHub **Release**
  (or stay local with the path noted in RESULTS) — never `git add`ed.
- **Reproducible or it didn't happen:** seed everything (lab seed `2718`),
  pin a `requirements.txt` per experiment, and record the exact model ids /
  kernel source / commit in the result JSON. Determinism is the house law.
- **Book every result:** append to [RESULTS.md](RESULTS.md) with an honest
  verdict — KEEP / KILL / INCONCLUSIVE / ABORTED — even (especially) the nulls.
  A claim that dies, dies cheap and honest, with the receipt kept beside the body.
- **Let the guard guard:** run every experiment under [guard.py](guard.py).
  It exists because this laptop has crash-looped before; do not bypass the
  VRAM/thermal floor to squeeze a bigger run. If it aborts, that abort is data.
