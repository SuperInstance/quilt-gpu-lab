# SCOUT: How Machine Intelligence GROWS Over Time
### Open-source landscape sweep — beyond SuperInstance
Compiled 2026-10-01 by research subagent. Scope: **demonstrated** self-growth loops (not just proposed).
Local target: RTX 4050 **6 GB VRAM** + CPU, small local models (LFM2.5, 0.5–3B), no big-cluster assume.

Legend for **Status**: `DEMO` = reproduced by third parties / shipping code exists · `PAPER` = authors' result, code sometimes released · `THEORY` = mostly argument, weak/absent reproduction.

Local-feasibility scale: 🟢 runs on 6 GB as-is · 🟡 feasible with 0.5–3B models / QLoRA / offline passes · 🔴 needs cluster-scale compute to be meaningful.

---

## RANKED CATALOG (most → least tractable/valuable for us)

### 1. Skill-library / iterative-prompting growth (in-context lifelong learning)
- **Mechanism (the growth loop):** Agent proposes a task (auto-curriculum) → writes executable code to attempt it → environment returns errors/success → LLM revises the program until self-verification passes → the **passing program is stored as a reusable skill in a growing library**, indexed by embedding and retrieved as a building block for the next, harder task. Capability compounds *without weight updates* — growth lives in an external artifact (the library).
- **Named example:** **Voyager** (MineDojo, `github.com/MineDojo/Voyager`, arXiv 2305.16291). Three parts: automatic curriculum + ever-growing skill library of executable code + iterative prompting with self-verification. 3.3× more unique items, 2.3× longer travel, up to 15.3× faster tech-tree progress than prior SOTA; skill library transfers to a **new world** and solves novel tasks from scratch. Learned skill libraries shipped in the repo.
- **Status:** `DEMO`. Third-party reproductions, active forks, plays on real Minecraft.
- **Local 6 GB:** 🟢 **Best fit.** The "brain" is a small/local or API LLM (LFM2.5-2.6B is explicitly agentic — planning + tool calling). Growth artifact is a vector-indexed code library; no fine-tuning, no VRAM pressure. **This is the single most tractable growth mechanism for this box.**

### 2. Self-play fine-tuning from own outputs (SPIN) & self-play preference optimization
- **Mechanism:** Two-player game on one model — the *current* model generates candidate responses; a copy of the *previous* model is trained to distinguish its own old (worse) outputs from the human/reference data. Iterating drives the model's output distribution toward the target distribution **without any new human data**; each round the "previous model" is the improved one. Weak→strong purely by self-comparison.
- **Named examples:** **SPIN** (arXiv 2401.01335, `uclaml.github.io/SPIN`, UCLA ML) — "Self-Play Fine-Tuning Converts Weak Language Models to Strong Language Models," beats DPO on several benchmarks. **SPIN-Diffusion** extends to text-to-image.
- **Status:** `DEMO` (widely reproduced for LLMs; needs only SFT data + compute).
- **Local 6 GB:** 🟡 Feasible at 0.5–3B with QLoRA + a DPO/SPIN loop; the real constraint is rollouts/rounds, not VRAM. Slower but genuinely runs.

### 3. Expert iteration / STaR family — self-taught reasoning by bootstrapping rationales
- **Mechanism:** Sample many rationales per problem → keep only those that reach the correct answer (or use "rationalization": give the model the answer and ask it to invent a plausible chain) → fine-tune on the kept chains → repeat. Each round the generator is the previous round's model. **The model manufactures its own training set and re-consumes it.**
- **Named examples:**
  - **STaR** (Zelikman et al., "Bootstrapping Reasoning With Reasoning").
  - **Quiet-STaR** (arXiv 2403.09629): generalize STaR so the LM learns to emit a *rationale at every token* to explain the upcoming text; improves zero-shot reasoning on a fixed dataset without task-specific rationales.
  - **ReST / ReST-EM** (arXiv 2308.08998, DeepMind): offline Generate→Improve→Fit loop; data reused across iterations, cheaper than online RLHF. **ReST-RL** (`github.com/THUDM/ReST-RL`) is a two-stage open reimplementation.
  - **V-STaR**: train a verifier on both correct *and* incorrect self-generated solutions to filter the next round.
- **Status:** `DEMO` — canonical, reproduced widely; underpins modern RLVR pipelines.
- **Local 6 GB:** 🟡 QLoRA fine-tune + offline sampling loop at sub-3B. Best run "offline" (generate batch in the day, fit at night). Works because the loop is data-bound, not memory-bound.

### 4. Self-rewarding / self-judging loops (Iterative DPO with LLM-as-judge)
- **Mechanism:** One model plays both actor and judge. It generates candidate answers, then scores them with an LLM-as-a-Judge prompt against a rubric; the pairwise preferences it produces drive DPO; the improved model becomes next round's judge. **Instruction-following AND judging skill rise together.**
- **Named examples:** **Self-Rewarding Language Models** (Yuan et al., arXiv 2401.10020, Meta + NYU; ICML 2024). Follow-ups: **Meta-Rewarding LMs** (adds a meta-judge), **CREAM** (consistency-regularized), **Process-based Self-Rewarding**.
- **Status:** `DEMO`. Third-party reimplementations exist; known failure mode = reward-hacking/judge drift over rounds (needs a ground-truth anchor).
- **Local 6 GB:** 🟡 Same profile as SPIN — QLoRA target + an offline judge pass. Judge can be the *same* small model or a stronger API model.

### 5. Constitutional AI / RLAIF — self-alignment by critique-and-revise
- **Mechanism:** The model critiques and rewrites its own outputs against an explicit written **constitution** (a rule list), producing a self-improved response set → supervised fine-tune on the revisions → then use AI-generated pairwise preferences (RLAIF) instead of human labels for a preference stage. **Human input is compressed into rules, not labels.**
- **Named example:** **Constitutional AI** (Anthropic, arXiv 2212.08073); **RLAIF** (Google, arXiv 2309.00267) shows AI feedback ≈ human feedback for summarization; **Collective Constitutional AI** (public input into the constitution).
- **Status:** `DEMO` — industry-proven and open reimplementations (e.g. `ConstitutionalAI` repos, Anthropic's HH-RLHF pipeline style).
- **Local 6 GB:** 🟡 The critique/revise pass is inference-only (fits easily at 3B Q4); the preference tuning is the 6 GB constraint. Excellent *cheap* first stage for a local box.

### 6. Open-endedness via LLM-as-model-of-interestingness (OMNI / OMNI-EPIC)
- **Mechanism:** A foundation model is used as a "Model of Interestingness" — it *proposes new tasks/environments* scored for learnability (not too easy, not too hard, from the agent's recent performance) and novelty. The agent trains on them; the proposer observes progress and proposes the next frontier. **Environment generation and solution generation co-evolve.**
- **Named examples:** **OMNI** (`github.com/jennyzzt/omni`, Zhang et al., arXiv 2306.01711) — LM-based MoI improves open-ended learning on BabyAI/textworld-style tasks. **OMNI-EPIC** (arXiv 2405.15568) — generates open-ended *code* environments; spawned **Genie 3**-style world-model interest. Predecessor: **POET** (`github.com/uber-research/poet`).
- **Status:** `DEMO` (OMNI/POET have runnable code); OMNI-EPIC is more recent, code/behavior partially reproduced.
- **Local 6 GB:** 🟡 The proposer is prompt-level (any local LLM); the learning agent's environments must be *cheap small tasks* we define. Well-suited to a curriculum engine wrapped around a small policy net.

### 7. POET / Quality-Diversity / novelty search — co-evolving curriculum
- **Mechanism:** Maintain a population of (environment, solution) pairs. Mutate environments; keep those that are *solvable by a slightly-better-than-random agent but not trivially*; solutions transfer between environments. Novelty search / MAP-Elites keep a diverse archive keyed by behavior descriptors. **Growth = expanding archive of qualitatively different competencies.**
- **Named examples:** **POET** (Wang et al., Uber AI, arXiv 1901.01753; 424+ cites), **Enhanced POET** (open-endedness with minimal constraints), **MAP-Elites**, **Novelty Search** (Lehman & Stanley).
- **Status:** `DEMO` — code public (`uber-research/poet`).
- **Local 6 GB:** 🟡 POET's 2-D biped environments were designed for CPU-heavy but small nets; a 6 GB GPU can host the solution nets fine. Great for a "hundred boats" open-ended forge.

### 8. Evolution Strategies / neuroevolution hybrids (EGGROLL) & CMA-ES
- **Mechanism:** Perturb weights with noise, evaluate the population's fitness, move toward the best perturbation (a gradient *estimate* from finite differences). No backprop required → works on non-differentiable rewards and parallelizes trivially. Modern twist: **low-rank perturbations** crush the memory cost so ES can train *large* models.
- **Named examples:** **OpenAI ES** (Salimans et al., 2017, Atari via ES); **EGGROLL** — "Evolution Strategies at the Hyperscale" (arXiv 2511.16652, ICML 2026; `github.com/...`), low-rank ES that can power end-to-end LLM training; tooling: **EvoTorch** (`docs.evotorch.ai`), **CMA-ES** (Hansen), **PyCMA**, JAX-based CMA-ES.
- **Status:** `DEMO` for classic ES/CMA-ES (decades of reproduction); EGGROLL is recent `PAPER`+reference code, independently promising.
- **Local 6 GB:** 🟡🟢 For *small* nets (MLPs, policies, tiny transformers) ES/CMA-ES is the best "no-backprop" growth path and embarrasingly parallel on CPU+GPU. Not for training a 7B model.

### 9. Meta-learning / learning-to-learn (MAML, RL², learned optimizers)
- **Mechanism:** Outer loop optimizes an *initialization* (MAML) or the *learning rule/optimizer itself* across a distribution of tasks; inner loop adapts to each task. Growth = getting faster/better at acquiring new skills, not just accumulating skills.
- **Named examples:** **MAML** (Finn et al., arXiv 1703.03400), **RL²** (arXiv 1611.02779), **MetaGenRL** (learned RL objectives, `louiskirsch.com/metagenrl`), PyTorch-native meta-learning tutorials; **Learned Optimizers** (e.g. learned LR schedulers, VeLO-style).
- **Status:** `DEMO` (MAML/RL² reproduced endlessly); learned large-scale optimizers remain research-stage.
- **Local 6 GB:** 🟡 MAML on small nets is fine (double-backprop memory is the pinch). Good for "make the small model adapt fast," less for raw capability growth.

### 10. Synthetic-data flywheel / instruction bootstrapping (Self-Instruct, ReST-EM, phi-style)
- **Mechanism:** Seed with a handful of hand-written examples → model generates large volumes of new instruction/response pairs → filter/dedupe/verify → fine-tune → the better model generates a better next batch. **Self-amplifying data engine.** Closest thing to "data that grows."
- **Named examples:** **Self-Instruct** (arXiv 2212.10560; bootstraps Alpaca), **Evol-Instruct/WizardLM** (evolve instructions to be harder), **Unnatural Instructions**, **phi-1/phi-2 "Textbooks Are All You Need"** (synthetic textbook data), **CoT-Self-Instruct**.
- **Status:** `DEMO` — the most industrialised of all these loops.
- **Local 6 GB:** 🟢 **Generation is free-ish**; the bottleneck is the *fit* step. Do generation with any local/API model, QLoRA-fit offline. This is the practical "feed the flywheel" engine for a 6 GB box.

### 11. Self-improving coding agents (Darwin Gödel Machine / AlphaEvolve)
- **Mechanism:** An agent is given a benchmark harness and the ability to **rewrite its own source code**; it proposes code edits, runs the benchmark, keeps edits that score higher, and (DGM) maintains an **archive of its own past selves** to branch from (preventing stagnation / enabling stepping-stones). Recursive self-improvement grounded by real evaluation.
- **Named examples:** **Darwin Gödel Machine** (Sakana AI + UBC, arXiv 2505.22954, `sakana.ai/dgm/`) — empirically improved its own coding ability; **AlphaEvolve** (DeepMind, evolutionary coding + verifier) — improved real algorithms (matrix multiply, datacenter scheduling); **Huxley-Gödel Machine** (successor idea).
- **Status:** `DEMO` — DGM's SWE-bench scores improved across generations; code reimplementations exist. Caveat: needs an expensive eval loop and is safety-sensitive (behind sandboxes).
- **Local 6 GB:** 🔴🟡 The *pattern* (bounded agent self-edit + harness + archive) is cheap and runnable locally with small agents; the *demonstrated magnitudes* required large compute. Treat as a blueprint, not a local workload.

### 12. Absolute Zero / R-Zero — self-proposed curriculum with a verifier, zero external data
- **Mechanism:** A single model is split into a **proposer** that invents tasks and a **solver** that answers; a **grounded verifier** (e.g. a code executor) validates both the task and the answer, producing verifiable reward. The curriculum is self-generated *and* self-graded, so no human tasks at all — the model maximizes its own learning progress.
- **Named examples:** **Absolute Zero Reasoner (AZR)** (arXiv 2505.03335, Tsinghua; `andrewzh112.github.io/absolute-zero-reasoner`) — SOTA among zero-data models on coding/math; **R-Zero** (self-evolving reasoning from zero data).
- **Status:** `PAPER`+code, strong results, recent (2025); reproduction community active.
- **Local 6 GB:** 🟡 Only if the verifier domain is cheap & code-based (e.g. generate toy Python problems, execute, grade). Mechanism is elegant and portable; scale is not.

### 13. Network/model growth (Net2Net, progressive growing, MoE growth)
- **Mechanism:** Start small, then *grow the architecture* when capacity saturates: Net2Net copies a trained net into a wider/deeper one (function-preserving init) then continues training; progressive growing adds layers/resolution; MoE adds experts and routes to them. **The model's capacity itself increases over time.**
- **Named examples:** **Net2Net** (Chen et al., arXiv 1511.05641), **Progressive Growing of GANs** (Karras), **Progressive Self-Knowledge Distillation (PS-KD)** (arXiv 2006.12000), MoE-growth / expert-choice routing (Google Research).
- **Status:** `DEMO` for Net2Net, PGGAN, PS-KD; **MoE *growth* specifically is more `PAPER`**.
- **Local 6 GB:** 🟡 Net2Net/PS-KD work at tiny scale and are the honest way to make a small model *literally bigger* over time. MoE growth is hard to keep under 6 GB.

### 14. Self-critique loops (Reflexion, Self-Refine) — inference-time, no weight change
- **Mechanism:** Produce output → critique it against criteria → revise → retry, optionally storing the verbal lesson in an episodic memory so future attempts start wiser. Growth is *in the loop and the memory*, not the weights (or later distilled into weights).
- **Named examples:** **Reflexion** (Shinn et al., arXiv 2303.11366), **Self-Refine** (Madaan et al., arXiv 2303.17651).
- **Status:** `DEMO` broadly; but known limit — self-critique *without* an external oracle can plateau or degrade, so pair with a verifier.
- **Local 6 GB:** 🟢 Trivially runs (pure inference). Weak on its own; powerful as the inner loop of #1/#3.

---

## CROSS-CUTTING VERDICTS

1. **Two families of growth exist:**
   - **(A) Weight-free growth** — capability accumulates in *external artifacts* (skill libraries, curriculum, memory, archives). Cheap, safe, runs on 6 GB today. Voyager is the flagship.
   - **(B) Weight-changing growth** — self-generated data/preferences re-fit into the model (STaR, SPIN, self-rewarding, ReST, Self-Instruct). Stronger signal, needs QLoRA + offline loops on a small box.

2. **The universal prereq is a verifier.** Every *demonstrated* loop that reliably grows (AlphaZero, AZR, DGM, SPIN, STaR, Voyager) has a ground-truth check — game outcome, code executor, held-out benchmark, or human data anchor. Loops without an oracle (pure self-critique, judge-only self-rewarding) drift or plateau. **Design rule for any local growth system: attach the strongest cheap verifier you can find.**

3. **Reward hacking / drift is the named failure mode** across #4, #5, #14, #11. Mitigations seen in the literature: meta-judge (Meta-Rewarding), consistency regularization (CREAM), process rewards, ground-truth anchors, and archive/diversity pressure (DGM, MAP-Elites).

4. **Growth is a rate, not a jump.** Demonstrated systems grow via *many cheap iterations*, which is exactly what a modest always-on local box can do overnight while a big-cluster one-shot can't.

---

## LOCAL STACK THAT ACTUALLY GROWS (RTX 4050 6 GB + CPU)

**Recommended composition, in build order:**

1. **Voyager-style skill library (#1) + Reflexion memory (#14)** — the harness. Local LFM2.5-2.6B (agentic, tool-calling, ~42–67 tok/s) as the policy. Skills = executable functions in a vector-indexed store. 🟢
2. **A verifier layer** — code executor (Python) + small unit tests + cheap held-out checks. This is what turns "loop" into "growth." 🟢
3. **Offline STaR/SPIN/self-rewarding refit (#3/#2/#4)** — nightly QLoRA passes at 0.5–3B on the day's verified traces. 🟡 (the one real VRAM-bound step; run with small batch + gradient checkpointing)
4. **Self-Instruct-style data flywheel (#10)** for breadth; **OMNI/POET-style curriculum (#6/#7)** for deciding *what to learn next*. 🟡
5. **ES/CMA-ES (#8)** for any small differentiable-or-not policy you want to evolve without backprop. 🟡

**Do not attempt locally:** AZR/DGM at demonstrated scale (#11/#12 magnitudes), large-model ES/EGGROLL, learned optimizers. Borrow their *loop shape*, not their compute.

---

## SOURCE INDEX (named examples)
| # | Technique | Repo / Paper |
|---|-----------|--------------|
| 1 | Voyager | github.com/MineDojo/Voyager · arXiv 2305.16291 |
| 2 | SPIN | uclaml.github.io/SPIN · arXiv 2401.01335 |
| 3 | STaR / Quiet-STaR / ReST | arXiv 2203.14465 · 2403.09629 · 2308.08998 · github.com/THUDM/ReST-RL |
| 4 | Self-Rewarding LMs | arXiv 2401.10020 |
| 5 | Constitutional AI / RLAIF | arXiv 2212.08073 · 2309.00267 |
| 6 | OMNI / OMNI-EPIC | github.com/jennyzzt/omni · arXiv 2306.01711 · 2405.15568 |
| 7 | POET | github.com/uber-research/poet · arXiv 1901.01753 |
| 8 | ES / CMA-ES / EGGROLL | docs.evotorch.ai · arXiv 2511.16652 |
| 9 | MAML / RL² | arXiv 1703.03400 · 1611.02779 |
| 10 | Self-Instruct | arXiv 2212.10560 |
| 11 | Darwin Gödel Machine / AlphaEvolve | sakana.ai/dgm · arXiv 2505.22954 |
| 12 | Absolute Zero | arXiv 2505.03335 |
| 13 | Net2Net / PS-KD | arXiv 1511.05641 · 2006.12000 |
| 14 | Reflexion / Self-Refine | arXiv 2303.11366 · 2303.17651 |
