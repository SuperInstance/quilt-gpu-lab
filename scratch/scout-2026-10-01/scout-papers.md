# Scout Report: How Models GROW (Iterative Self-Improvement Literature)

Compiled 2026-10-01. Focus: mechanisms that let a model improve **over its own prior, iteratively** (a closed loop), not one-shot distillation from humans. "Demonstrated" = published empirical results showing the loop actually compounding across iterations.

---

## Ranked Catalog (strongest demonstrated growth loops first)

### 1. Expert Iteration / ReST-EM — generate, filter by ground truth, retrain on your own winners
- **Papers:**
  - *Thinking Fast and Slow with Deep Learning and Tree Search* (Expert Iteration / EXIT) — Anthony et al., **arXiv:1705.08439** (NeurIPS 2017)
  - *Reinforced Self-Training (ReST) for Language Modeling* — Gulcehre et al. (DeepMind), **arXiv:2308.08998**
  - *Beyond Human Data: Scaling Self-Training for Problem-Solving with Language Models* (ReST-EM) — Singh et al. (DeepMind), **arXiv:2312.06585**
- **Mechanism (growth loop):** sample many solutions from the current policy → keep only those that pass a **verifier** (ground-truth answer, unit tests, reward model) → fine-tune on the filtered self-generated set → the improved policy generates better data next round → repeat. ReST-EM showed three EM iterations beat supervised training on human data (MATH, HumanEval) with **no new human data**.
- **Demonstrated:** ✅ Strongly. AlphaGo Zero's cousin in text form; DeepMind showed self-generated data outperforming human demonstrations after a few rounds.

### 2. STaR / V-STaR — rationale bootstrapping + self-trained verifiers
- **Papers:**
  - *STaR: Bootstrapping Reasoning With Reasoning* — Zelikman et al., **arXiv:2203.14465** (NeurIPS 2022)
  - *V-STaR: Training Verifiers for Self-Taught Reasoners* — Hosseini et al., **arXiv:2402.06457** (COLM 2024)
- **Mechanism:** model generates rationales; keep rationales leading to correct answers ("rationalization" for still-unsolved problems by feeding the answer as a hint); fine-tune on them; repeat. V-STaR adds the key fix: train a **verifier (DPO reranker) on both correct AND incorrect self-generations** so data quality (not just quantity) improves each iteration.
- **Demonstrated:** ✅ Strongly. STaR: GPT-J +loop approached a 40× larger model on CommonsenseQA. V-STaR: Mistral-7B beats training on gold data alone; correct/wrong data both feed the loop.

### 3. Self-play RL with verifiable rewards — SPIN / Absolute Zero / R1 line
- **Papers:**
  - *Self-Play Fine-Tuning Converts Weak Language Models to Strong Language Models* (SPIN) — Chen et al., **arXiv:2401.01335** (ICML 2024)
  - *Absolute Zero: Reinforced Self-play Reasoning with Zero Data* — Zhao et al., **arXiv:2505.03335** (NeurIPS 2025)
  - *DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via RL* — DeepSeek, **arXiv:2501.12948** (also Nature, 2025)
- **Mechanism:** the model's **own outputs become its own training opponent/teacher**. SPIN: train to distinguish self-generated responses from human data until the distribution matches (no extra labels; provably stops at distribution match). Absolute Zero: one model **proposes tasks AND solves them** in a closed loop, scored by a code executor — zero external data, task generator and solver co-improve. R1: pure RL with rule-based rewards (math answer match, code tests) grows long chain-of-thought reasoning from the model alone.
- **Demonstrated:** ✅ Strongly. SPIN: zephyr-7B SFT→beats DPO baselines, no human prefs. AZR: 7B self-play SOTA on math/code vs. models trained on millions of samples. R1: emergent self-verification/reflection at scale.

### 4. Self-Rewarding LMs — the model becomes its own judge, iterated DPO
- **Paper:** *Self-Rewarding Language Models* — Yuan et al. (Meta), **arXiv:2401.10020** (NeurIPS 2024)
- **Mechanism:** each round the model (LLM-as-a-judge prompt) scores its own candidate responses → preferences → **Iterative DPO**. Key empirical finding: reward-model ability **and** instruction-following co-improve across iterations — the first strong evidence the judge itself grows in the loop, not just the policy (⇒ compounding, "super-alignment without humans" trajectory).
- **Demonstrated:** ✅ 3 iterations on Llama-2-70B; beats RLHF/DPO pipelines including systems using an external reward model. Caveat: later work shows the gain saturates without fresh prompts and can drift.

### 5. Multi-turn self-correction training — RISE / SCoRe / PAG
- **Papers:**
  - *Recursive Introspection (RISE): Teaching Language Model Agents How to Self-Improve* — Qu et al. (CMU), **arXiv:2407.18219**
  - *Training Language Models to Self-Correct via Reinforcement Learning* (SCoRe) — Kumar et al. (DeepMind), **arXiv:2409.12917** (ICLR 2025 oral)
  - *PAG: Multi-Turn Reinforced LLM Self-Correction* — Jiang et al., **arXiv:2506.10406**
- **Mechanism:** train the model **in-context** to fix its own previous attempt: SCoRe uses two-stage multi-turn RL with a lock to prevent collapse onto turn-1 behavior; RISE casts it as a weak-to-strong RL problem so the policy, given its own prior output + feedback, outputs something better. Growth shows up **at inference** (each turn improves accuracy) and is learned once.
- **Demonstrated:** ✅ SCoRe: +15.6% self-correction on MATH (Gemma-2-9B), entirely self-generated data. RISE: 7B Llama-2/Mistral improve monotonically over turns, beating self-refine/stronger single-turn.

### 6. Test-time scaling — self-consistency, verifier reranking, o1-style thinking
- **Papers:**
  - *Self-Consistency Improves Chain of Thought Reasoning* — Wang et al., **arXiv:2203.11171** (ICLR 2023)
  - *Let's Verify Step by Step* (process reward models, PRM) — Lightman et al. (OpenAI), **arXiv:2305.20050** (ICLR 2024)
  - OpenAI o1 (*Learning to Reason with LLMs*, 2024, no arXiv) + R1 above as open versions.
- **Mechanism:** spend more inference compute instead of more weights: sample n chains → majority-vote (self-consistency), or score steps with a PRM and search (best-of-n / beam). o1/R1 show you can RL-train the model to *use* this thinking time productively. Growth is in effective capability per parameter, not in the weights themselves per query.
- **Demonstrated:** ✅ Enormously (self-consistency: +~18 points GSM8X; PRM800K: 78% on MATH best-of-n). Notably compute-capped-friendly: works on small local models today.

### 7. RLAIF / Constitutional AI — self-critique replaces human preference labels
- **Paper:** *Constitutional AI: Harmlessness from AI Feedback* — Bai et al. (Anthropic), **arXiv:2212.08073**
- **Mechanism:** model critiques its own outputs **against a written set of principles**, revises them, then trains a preference model on its own AI feedback (RLAIF). Loop = constitution → self-critique → revise → RM → RL → repeat (can re-run critique on the improved model).
- **Demonstrated:** ✅ for alignment/harmlessness (labels-free, RLHF-parity); ❌ not demonstrated as a *capability* growth loop — the loop mostly moves behavior, not frontier skill.

### 8. Data bootstrapping — weak-to-strong, self-distillation, synthetic curriculum
- **Papers:**
  - *Weak-to-Strong Generalization* — Burns et al. (OpenAI), **arXiv:2312.09390**
  - *Self-Distillation Bridges Distribution Gap in LLM Fine-Tuning* (SDFT) — Yang et al., **arXiv:2402.13669**
  - *Textbooks Are All You Need* (Phi-1) — Li et al. (Microsoft), **arXiv:2306.11644**; Orca: **arXiv:2306.02707**; MAmmoTH: **arXiv:2309.05653**; Phi-4 pushes this to ~14B SOTA-on-math with mostly synthetic data (2024/25).
- **Mechanism:** a weak supervisor's noisy signal lets a stronger student exceed it (W2S — generalization gap works for you, not against); self-distillation re-generates the fine-tuning data *in the model's own distribution* before training on it; Phi/Orca show carefully filtered/structured synthetic data from a strong teacher can substitute for web-scale human corpora (one-shot, but "data bootstrapping" when teacher = you + filter, it becomes ReST).
- **Demonstrated:** ✅ W2S: GPT-4 supervised by GPT-2-level teacher recovers most of its strength (NLP tasks). Phi/Orca: yes. As a *closed self-loop*: mostly ❌ (teacher ≠ student).

### 9. Open-endedness — the environment generates the curriculum, forever
- **Papers:**
  - *POET: Paired Open-Ended Trailblazer* — Wang et al., **arXiv:1901.01753** (2019)
  - *Open-Ended Learning Leads to Generally Capable Agents* (XLand) — DeepMind, **arXiv:2111.09888** (Nature 2022); AdA: **arXiv:2301.07608**
  - *OMNI* — Zhang et al., **arXiv:2306.01711**; *OMNI-EPIC* — Faldor et al., **arXiv:2405.15568**
- **Mechanism:** an **environment/task generator co-evolves with the agent**: new tasks are generated at the frontier of difficulty (min-max novelty + learnability), agents that solve them become seeds/teachers, unsolved tasks get mutated. Growth comes from an endless auto-curriculum rather than a fixed dataset. OMNI swaps handcrafted novelty search for an LLM judging "interestingness"; AZR (above) is this idea ported to code tasks.
- **Demonstrated:** ✅ in RL/agents (POET, XLand meta-games, AdA human-timescale adaptation). ❌ not yet for LLM weights directly (except AZR-ish code loops).

### 10. Continual learning — accumulate without catastrophic forgetting (the *memory* half of growth)
- **Papers:**
  - *O-LoRA: Orthogonal Subspace Learning for LM Continual Learning* — Wang et al., **arXiv:2310.14152** (EMNLP Findings 2023)
  - *Mitigating Catastrophic Forgetting in LLMs with Self-Synthesized Rehearsal* — Sun et al. (ACL 2024; the model rewrites its own rehearsal data)
  - *An Empirical Study of Catastrophic Forgetting in LLMs During Continual Fine-Tuning* — **arXiv:2308.08747**; survey: ACM Computing Surveys 2025 *Lifelong Learning of LLMs*
- **Mechanism:** keep old skills while adding new ones via orthogonal LoRA subspaces, replay buffers (self-synthesized = no stored private data), MoE adapters, or regularized optimization. This doesn't create improvement by itself — it's what lets a growth loop **bank** its gains instead of thrashing.
- **Demonstrated:** ✅ mature tooling; the constraint is it's an *enabler*, not a driver.

### 11. Recursive self-improvement proper — theory, and 2026 first empirical attempts
- **Papers:**
  - *Gödel Machines: Self-Referential Universal Problem Solvers* — Schmidhuber, **arXiv:cs/0309048** (2003; theory only — provably optimal self-rewrites via proof search; unimplementable)
  - Hutter's line (AIXI as the optimal-but-uncomputable agent; his later argument that "self-improvement is just learning the environment including the machine itself" — theory papers, not empirical RSI systems)
  - *Recursive Self-Improvement in AI* (survey/taxonomy) — Chen et al., **arXiv:2607.07663** (2026)
  - *Recursive Self-Improvement of AI Research Agents* — Srikanth et al., **arXiv:2609.26457** (2026): the agent's **own code is the object of optimization** — each accepted rewrite becomes the agent that edits the next round (empirical, small scale)
  - *The Last AI Built by Humans: Toward Genuine Recursive Self-Improvement* — Duan et al., **arXiv:2609.11873** (2026): roadmap from improvement-execution autonomy → strategy → experience-acquisition → environment adaptation → recursive meta-improvement; HCI "headroom-closed index" diagnostic; **preliminary empirical evidence only**
- **Demonstrated:** ❌ at the full generality level (Gödel machine = pure theory). ⚠️ narrow empirical versions exist (self-modifying coding agents, improving the improver in limited domains); 2026 papers are position/roadmap + small-scale demos. This is the frontier, not the toolkit.

---

## Cross-cutting lesson

Every demonstrated growth loop has the same skeleton:

```
generate (on-policy samples) → verify (ground truth / executor / self-judge / verifier model)
→ select/distill the good ones → update weights → repeat
```

What differs is (a) the **verifier** (external checker = most reliable; self-judge = works but drifts; none = collapses into model collapse) and (b) whether the update touches **weights** (real growth) or only **context** (borrowed growth). Loops with external verifiable signals (math answers, code execution) are the only ones empirically shown to compound for many rounds without humans in the loop.

---

## Top 3 mechanisms for growing a small local model on a 6GB GPU

(6GB ⇒ 1–3B base model, QLoRA fine-tunes, quantized 4-bit inference, no external API.)

1. **ReST-EM / expert iteration with an executable verifier (Family 1).** Generate k solutions per task, keep those passing a free checker (unit tests for code, exact-answer match for math — `sympy`/checker script), SFT on winners, repeat. Needs only generation + a LoRA update per round; no reward model to fit in VRAM. This is the exact loop of ReST-EM, V-STaR, and AZR (all demonstrated at 7B; the components run fine at 1–3B with QLoRA).
2. **STaR/V-STaR with a tiny self-trained verifier (Family 2).** Same loop plus a small DPO-style verifier trained on the model's own correct-vs-incorrect pairs; V-STaR showed this beats gold-data SFT at 7B and the verifier can be a 1B-scale model you already have. Data for the loop is 100% self-generated.
3. **Iterated self-rewarding DPO (Family 4).** LLM-as-judge on own outputs → preference pairs → DPO with the base model as reference (no separate RM process; ref weights already resident). Demonstrated to co-lift judging + following; cheapest RAM-wise of all (DPO needs no sampling-time reward model, just the ref you already loaded). Risk: drift — anchor every few rounds with the executable verifier from #1.

**Single most tractable: #1 — ReST-EM/expert-iteration with code+unit-test verification on a ~1–3B model (QLoRA, ~4-bit, `peft`/`trl`).** The verifier is exact and free, the loop has no moving parts beyond generate-filter-finetune, it's the most replicated growth mechanism in the literature (ReST-EM, V-STaR, Absolute Zero, R1-style RL all reduce to it at small scale), and every round is resumable from checkpointed data. Start domain: small self-generated Python functions with property-based tests (AZR's TRR++ recipe) — it sidesteps the judge entirely and the environment, not the model, supplies truth.
