# PAPERS.md — GREENHORN research sweep (lane PAPERS)

*2026-10-01, lane PAPERS, casey GREENHORN directive wave. Scratch only — DO NOT COMMIT.*
*Scope: cutting-edge research for a self-decomposing chatbot (quilt of logic cells; confidence-gated decomposition; tiny local models bootstrapped to verifier-model intelligence).*

**Method note (honest).** Sweep run via `web_search` (provider: minimax) + targeted `web_fetch`, 2023→2026 with recency checks. Several sources are 2026-dated field notes/papers; where a claim comes from a vendor blog with its own axe to grind (Nadir, TypeSafe-adjacent commentary) I mark it **[vendor-adjacent]** and cross-check against at least one independent source. Every URL is as returned; a few fetched pages were bot-walled (HL, OpenReview) and are cited from the search index, not full text.

**The ladder we are ranking against** (from the directive):
- **L1** — JEV-brained decomposition chatbot (god-model decomposition here: the JEV/judgment brain splits the turn)
- **L2** — fully-local cells (0.5B–4B on the 6 GB 4050, no cloud)
- **L3** — tool-bootstrapped growth (MCP/API/CLI/TUI/browser surfaces teach the cells)
- **L4** — self-taught greenhorn with API budget (local model bootstrapped to verifier-model intelligence)

**Our binding constraints** (this is what "leverage" is measured against):
- Tiny local models, **0.5B–4B**, one 6 GB RTX 4050, seat-serialized.
- **typesafe.ai graded judgment cells** — `noul` (yes/no ∈ 0..1), `choice`, `score` — as the verifier/intelligence source.
- **prompt-compiler loop** (the system rewrites its own prompts/cells).
- Surfaces: **MCP / API / CLI / TUI / browser**.
- Fleet laws that already bite: std==0 frost law, seat serialization, JEV-abstention honesty, "models reason / tools verify."

---
---

# PART A — Family sweep (a–i)

Format per family: **mechanism (3 lines)** → **L1→L4 contribution** → **key paper/project + URL**.

## (a) Confidence-gated LLM cascades — FrugalGPT and successors

**Mechanism.**
1. A small/cheap model answers first; an escalation signal (confidence, verifier score, disagreement) decides whether to forward to a stronger model.
2. FrugalGPT formalized 3 levers: prompt adaptation, LLM approximation (cache/finetune), and the cascade itself; reported up to 98% cost cut at matched GPT-4 quality on some sets.
3. 2025–26 line adds **calibration** (confidence is miscalibrated by default), **budgeted cascades**, and **cascade-with-verifier** designs (the verifier grades the cheap answer, not the query).

**L1→L4.** This *is* the ladder's spine. L1: JEV `noul` decides decompose-vs-answer and pass-vs-escalate. L2: cells answer, JEV gates locally. L3: gate escalates to a tool/teacher when the cell is unsure. L4: gate escalates to the paid API only on the discordant set — the budget governor.

**Key works.**
- FrugalGPT (Chen, Zaharia, Zou, 2023) — https://arxiv.org/abs/2305.05176 · impl notes https://portkey.ai/blog/implementing-frugalgpt-smarter-llm-usage-for-lower-costs/
- UCCI: *Calibrated Uncertainty for Cost-Optimal LLM Cascade Routing* (May 2026) — https://arxiv.org/abs/2605.18796 → **raw ECE 0.12 → 0.03 after isotonic regression = 31% inference-cost cut at held quality on 75k production queries** [strong, load-bearing].
- *Do Small Language Models Know When They're Wrong? Confidence-Based Cascade Scoring* (Khan Academy, Aug 2026) — https://arxiv.org/html/2604.19781v1 → best SLM AUROC 0.857; worst SLM **near-degenerate confidence distribution → cascade cannot close the gap at ANY threshold**.
- Survey: *Dynamic Model Routing and Cascading for Efficient LLM Inference* (2026) — https://arxiv.org/html/2603.04445v2 · living list https://github.com/ymoslem/awesome-llm-routing-cascading
- *Teacher-anchored, disagreement-weighted confidence for budgeted small-to-large cascades* (2026) — https://www.sciencedirect.com/science/article/abs/pii/S0957417426029738

## (b) Adaptive computation — PonderNet / ACT and the 2024–26 revival

**Mechanism.**
1. Instead of fixed depth for every token, the net learns *how many steps* to take (ACT: halting units + ponder cost; PonderNet: a probabilistic, fully-differentiable halting distribution).
2. 2024–26 revivals apply it at the **token/segment** level (learned token routing ≈ adaptive depth) and at **test-time** ("change of thought": revise the intermediate thought, re-use compute adaptively).
3. Practical gotcha line: for *small* transformers the halting signal matters — leakage-free halting/cost-aware stopping decides whether adaptive depth is a win or a wash.

**L1→L4.** The literal mechanism of "self-decomposing": the cell decides how deep/which sub-cells to run. L2: tiny nets with learned halt = cheap self-decomposition. L3/L4: halting decides when to hand off to a tool or the API (budget = ponder cost).

**Key works.**
- PonderNet (DeepMind, 2021) — https://arxiv.org/abs/2107.05407 · ACT (Graves 2016) — https://arxiv.org/abs/1603.08983
- *Change of Thought: Adaptive Test-Time Computation* (Mathur et al., 2025) — https://arxiv.org/abs/2507.13569
- *Adaptive Computation Depth via Learned Token Routing* (2026) — https://arxiv.org/html/2605.05222v1
- *When Should a Small Transformer Stop? Leakage-Free…* (Jul 2026) — https://papers.ssrn.com/sol3/Delivery.cfm/7143598.pdf
- AdaTape (Google, adaptive read/write + compute) — https://research.google/blog/adatape-foundation-model-with-adaptive-computation-and-dynamic-read-and-write/

## (c) Uncertainty-triggered decomposition / retrieval

**Mechanism.**
1. The model emits special "retrieve"/"think-more" tokens or reads an uncertainty signal, and triggers retrieval/critique **only when unsure** (Self-RAG reflection tokens; FLARE forward-looking active retrieval).
2. **Least-to-most**: decompose a hard query into ordered sub-questions, then solve them sequentially — decomposition is *functional*, not just a formatting trick.
3. 2025–26: self-aware retrieval (SeaKR), self-triggered information planning (GRIP), and the **negative result** that models often *don't* know when they don't know — the trigger itself is the hard part.

**L1→L4.** The decomposition brain. L1: JEV decides "split this turn into N sub-asks." L2: local cells each answer one sub-ask; JEV checkpoints. L3: unsure sub-asks call retrieval/tools. L4: the *policy* for when-to-decompose is itself learned from the API budget.

**Key works.**
- Self-RAG (Asai et al., 2023) — https://arxiv.org/abs/2310.11511
- FLARE (Jiang et al., 2023) — https://arxiv.org/abs/2305.06983
- Least-to-Most Prompting (Zhou et al., 2022) — https://arxiv.org/abs/2205.10625
- SeaKR: Self-aware Knowledge Retrieval (Yao et al., 2024) — https://arxiv.org/abs/2406.19215
- *Adaptive Retrieval without Self-Knowledge?* (ACL 2025) — https://aclanthology.org/2025.acl-long.319.pdf → models' self-knowledge of retrieval need is weak; external signals help.
- GRIP: self-triggered information planning (2026) — https://arxiv.org/html/2604.11407v2

## (d) Test-time compute scaling — search / rerank / self-consistency / verifier-gated Best-of-N

**Mechanism.**
1. Spend more inference compute per query: sample N, then select with a verifier / self-consistency majority / reranker.
2. *Compute-optimal* scaling (ICLR 2025): allocate test-time compute by difficulty — easy→greedy, hard→search; >4× efficiency over naive best-of-N.
3. 2025–26: **verifier-gated** Best-of-N with calibrated confidence, **tool-integrated self-verification for small LMs** (T1: offload verification to a tool to cut the sLM's memorization burden), and a rigorous verification-design survey.

**L1→L4.** Candidate generation + selection is how a tiny model gets *any* accuracy. L2: sample N local cells, gate with JEV. L3: the verifier is a tool (python/lint/search) — this is the cheapest intelligence a 0.5–4B model can borrow. L4: selection policy learned from the API teacher.

**Key works.**
- *Scaling LLM Test-Time Compute Optimally Can Be More Effective than Scaling Parameters* (ICLR 2025 oral) — https://iclr.cc/virtual/2025/oral/31924
- **T1: Tool-integrated Self-verification for Test-time Compute Scaling in Small LMs** (ICLR 2026) — https://arxiv.org/abs/2504.04718 → proves tool offload reduces sLM memorization burden; **beats larger models on self-verification**.
- *Trust but Verify! Survey on Verification Design for Test-Time Scaling* (2025) — https://arxiv.org/html/2508.16665v3
- Self-Consistency (Wang et al., 2023) — https://arxiv.org/abs/2203.11171
- Living list — https://github.com/ThreeSR/Awesome-Inference-Time-Scaling

## (e) Self-improvement loops — STaR / Quiet-STaR / self-rewarding / iterative distillation

**Mechanism.**
1. Generate rationales/answers, keep those that reach the right answer, fine-tune on the kept set, repeat (STaR); Quiet-STaR generalizes it to *every token* with a learned "think" token.
2. Self-rewarding: the model acts as its own judge to score its own outputs, then DPO/iterates (Meta, 2024) — no external judge needed *in principle*.
3. 2025–26: **simple self-distillation** (learn from your own samples, no verifier, no RL) and heavier warnings that self-reward loops collapse when the judge is weak (reward hacking).

**L1→L4.** L4 is literally "self-taught greenhorn." L3: API teacher bootstraps cells (iterative distillation). L4: the local model improves itself between API sessions — *only if* an external verifier anchors the reward.

**Key works.**
- STaR (Zelikman et al., 2022) — https://arxiv.org/abs/2203.14465
- Quiet-STaR (Zelikman et al., 2024) — https://arxiv.org/abs/2403.09629
- Self-Rewarding Language Models (Yuan et al., 2024) — https://arxiv.org/abs/2401.10020
- *Simple Self-Distillation (SSD)* — sample → self-distill, no teacher/verifier/RL (2026 write-up) — https://medium.com/@michael.hannecke/your-llm-can-improve-itself-no-teacher-no-verifier-no-rl-required-5d41f3f4a6b4
- MiniPLM (distill pre-training) — https://openreview.net/forum?id=tJHDw8XfeC
- Counterweight: *Recent Frontier Models Are Reward Hacking* (METR) — https://metr.org/blog/2025-06-05-recent-reward-hacking/

## (f) Routing / distillation-to-cells — RouteLLM, mixture-of-agents, expert routing with small models

**Mechanism.**
1. RouteLLM: train a router on human preference data to pick strong-vs-weak model; >2× cost cut without quality loss (reported 74% of queries to the cheap model at 95% quality).
2. Mixture-of-Agents (MoA): layered ensemble where proposers feed aggregators; ensembles consistently beat single classifiers.
3. 2025–26 distillation: **Agent Distillation** transfers *full task-solving behavior* (reasoning + retrieval + tool use) from a big agent into small models — the L2/L3 cell factory.

**L1→L4.** L1/L2: cells = small experts; a router (JEV) picks the cell. L3: behavior is distilled from the API agent into cells with retrieval/code tools. L4: cell pool breadth is the real lever (more cells > smarter router).

**Key works.**
- RouteLLM (Ong et al., 2024) — https://arxiv.org/abs/2406.18665 · https://github.com/lm-sys/routellm
- Mixture-of-Agents (Wang et al., 2024) — https://arxiv.org/abs/2406.04692 · https://github.com/togethercomputer/moa
- **Agent Distillation into Small Models with Retrieval and Code Tools** (NeurIPS 2025) — https://neurips.cc/virtual/2025/poster/117657
- Symbolic Mixture-of-Experts (skill-based routing) — https://arxiv.org/html/2503.05641v2
- **LLMRouterBench** (ACL 2026 Findings, 10 routers × 33 models × 400k queries) — https://arxiv.org/abs/2601.07206 → *most commercial routers fail to beat a size baseline*; failure = stochastic model recall, not difficulty; **ensembles win**.
- Avengers-Pro (dynamic committee routing, ACM DAI 2025) — https://arxiv.org/abs/2508.12631
- RouterEval (EMNLP 2025) — bigger model pool > better router.

## (g) JEPA — I-JEPA/V-JEPA, text/dialogue JEPA, LeCun's roadmap

**Mechanism.**
1. Predict in **embedding space**, not input space: encode context → predict the *representation* of the masked/target region, avoid reconstruction of unpredictable detail (LeCun 2022 position paper; I-JEPA 2023, V-JEPA 2024).
2. LeCun's roadmap: hierarchical JEPA (H-JEPA) as the world model for planning under uncertainty — the "world model" branch that is *not* autoregressive token prediction.
3. 2025–26 put **text on JEPA**: **LLM-JEPA** (JEPA objective added to LLM finetuning/pretraining, beats standard objectives, robust to overfit) and **Agentic-JEPA** (JEPA-style world model for *text-based agent planning*).

**L1→L4.** The "JEV-brain" naming bet. L1: a latent state-model of the conversation that predicts the *next dialogue state* rather than the next token — decomposition decided in latent space. L2: tiny latent predictor on the 4050 (cheap, non-generative). L3/L4: the latent model predicts which tool/skill to invoke (planning), which is exactly H-JEPA's planning role.

**Key works.**
- LeCun, *A Path Towards Autonomous Machine Intelligence* (2022) — https://openreview.net/pdf?id=BZ5a1r-kVsf
- I-JEPA (2023) — https://ai.meta.com/blog/yann-lecun-ai-model-i-jepa/ · V-JEPA / V-JEPA 2 — https://ai.meta.com/research/publications/v-jepa-2/ (overview: https://www.turingpost.com/p/jepa)
- **LLM-JEPA** (Balestriero/Huang, 2025) — https://arxiv.org/abs/2509.14252 · code https://github.com/rbalestr-lab/llm-jepa
- **Agentic-JEPA** (text-based agent planning, Mar 2026) — https://hal.science/hal-05546567v1/document
- TD-JEPA (latent-predictive RL, zero-shot) — https://openreview.net/forum?id=SzXDuBN8M1 · FF-JEPA (long-horizon latent planning) — https://arxiv.org/html/2606.09311v1
- Curated list — https://github.com/AbdelStark/awesome-jepa

## (h) Learned prompt optimization — DSPy teleprompters, APE, instruction induction

**Mechanism.**
1. Treat prompts as parameters: generate/evolve instructions, score on a metric, keep the best (APE, instruction induction: LLM induces the instruction from input→output examples).
2. **GEPA** (DSPy, 2025): *reflective* evolutionary optimizer — read execution traces, write natural-language critiques, Pareto-select instructions; reported **35× fewer rollouts than RL**.
3. 2026 recency: *Automatic Prompt Engineering with No Task Cues* (simpler, as effective) and *Automated Instruction Revision* (rule-induction over instructions).

**L1→L4.** This is the **prompt-compiler loop**. L1: hand-built decomposition prompts. L2: DSPy compiles cell prompts against a held-out set. L3: traces from tool use feed the reflection. L4: the greenhorn rewrites its own prompts from API-budget feedback — GEPA is the concrete compiler.

**Key works.**
- GEPA: *Reflective Prompt Evolution Can Outperform RL* (2025) — https://dspy.ai/current/api/optimizers/GEPA/overview/ · explainer https://www.morphllm.com/gepa-prompt-optimization
- DSPy — https://dspy.ai/ · instruction induction (Honovich et al., 2022) — https://arxiv.org/abs/2205.11916
- APE: Automatic Prompt Engineer (Zhou et al., 2022) — https://arxiv.org/abs/2211.01910
- *Automatic Prompt Engineering with No Task Cues* (2026) — https://arxiv.org/html/2601.03130v1
- **Prompt-optimization tax (negative)** — https://getnadir.com/blog/dspy-gepa-automatic-prompt-optimization-cost/ [vendor-adjacent] → DSPy/GEPA help *some* task types, not all.
- *Automated Instruction Revision* (2026) — https://arxiv.org/pdf/2604.09418

## (i) Quantum / noise-augmented sampling for diversity

**Mechanism.**
1. Diversity is a *sampling* problem: truncation (top-p/top-k) trades diversity for risk; principled samplers shape the distribution to keep both.
2. **REAL sampling**: a tiny (70M) "typicality" model rejects low-typicality tails → recovers greedy factuality *and* high temperature's diversity in 7B models.
3. **Verbalized Sampling**: ask the model to *verbalize* a spread of candidate answers with their probabilities → unlock diversity, mitigate mode collapse (alignment/RLHF collapse is a documented failure).
4. Quantum-inspired: **D²-sampling** (quantum-inspired, ICLR 2025) gives provable sampling speedups/quality for k-means++-style selection; QMCTS ideas (superposition/quantum-assisted sampling) circulate for decision search. *(Our internal mote: `scratch/greenhorn/QuantumArtHack` = QPIXL quantum image encoding — adjacent, not a sampler.)*

**L1→L4.** Decomposition needs *candidate diversity*: N distinct sub-plans/solutions to gate. L2: cheap noise-augmented sampling from tiny cells to widen the candidate pool without a big model. L4: diversity is what makes Best-of-N + verifier actually pay.

**Key works.**
- REAL sampling (TACL 2025) — https://aclanthology.org/2025.tacl-1.35/ · code https://github.com/amazon-science/llm-asymptotic-decoding
- **Verbalized Sampling: mitigate mode collapse, unlock LLM diversity** (2025) — https://arxiv.org/html/2510.01171v1
- *Balancing Diversity and Risk in LLM Sampling* (2024) — https://openreview.net/forum?id=ZpiFTcDqSc
- Quantum (Inspired) D²-sampling (ICLR 2025) — https://proceedings.iclr.cc/paper_files/paper/2025/hash/930d24a185127a600408853a0b1c31d6-Abstract-Conference.html
- *Sampling for Quality: training-free reward-guided LLM decoding* (2026) — https://arxiv.org/abs/2604.16453

---
---

# PART B — TOP 10 ranked by leverage for OUR constraints

Ranked for: **0.5B–4B cells on a 6 GB 4050 + typesafe `noul` judgment cells as verifier + prompt-compiler loop + MCP/API/CLI/TUI/browser surfaces.** One sentence each.

1. **Calibrated confidence-gated cascade (FrugalGPT + UCCI isotonic + Khan SLM study).**
   Why: it is the literal engine of L1→L4, and the literature says the *only* way the gate works is a calibrated signal — our `noul` must be isotonic-mapped before any threshold, or the whole ladder is a coin flip (raw ECE 0.12→0.03 buys 31% cost).
2. **Uncertainty-triggered decomposition + least-to-most (Self-RAG / FLARE / SeaKR / GRIP).**
   Why: "decompose when unsure" must be a *learned trigger*, not a fixed pipeline — the trigger is demonstrably the hard part, and JEV `noul` is exactly the trigger primitive we already own.
3. **Verifier-gated Best-of-N with tool-integrated self-verification (T1).**
   Why: it is the single best-documented way a small model beats larger models — offload verification to a tool (python/lint/search) instead of asking the 1B model to know it's wrong, which maps 1:1 onto our "models reason / tools verify" law.
4. **Mixture-of-local-experts + ensemble routing (MoA, LLMRouterBench, Avengers-Pro, RouterEval).**
   Why: on tiny cells the winning move is *pool breadth + ensemble signal*, not a cleverer router — adding cells beats improving the gate, and ensembles cancel the stochastic recall failures that sink single classifiers.
5. **Reflective prompt-compiler (GEPA in DSPy).**
   Why: it is the concrete, cheap implementation of our prompt-compiler loop — read trajectories, write critiques, Pareto-select — at 35× fewer rollouts than RL, which is affordable on a 4050 + API-budget.
6. **JEPA as latent conversation state-model (LLM-JEPA, Agentic-JEPA, TD-JEPA).**
   Why: it is the intellectual bet behind the "JEV-brained" name and the only credible *non-autoregressive* planner for decomposition — and text-JEPA is now real (2025–26) rather than vapor, though still auxiliary, not a replacement.
7. **Self-improvement loops (STaR / Quiet-STaR / self-rewarding / simple self-distillation).**
   Why: L4 ("self-taught greenhorn") is *defined* by this family, and SSD shows a verifier-free path — but every source warns a weak judge collapses the loop, so the local model must be anchored by JEV/tools, never its own unverified judgment.
8. **Adaptive computation + learned halting (PonderNet/ACT revival, Change of Thought, small-transformer halting).**
   Why: "self-decomposing" is mechanically adaptive depth — the cell decides how many steps/sub-cells to spend, and the 2026 work on leakage-free halting for *small* transformers is aimed exactly at our scale.
9. **Agent distillation to small cells (Agent Distillation, RouteLLM, MiniPLM).**
   Why: it is the L2/L3 factory — transfer *behavior* (reasoning + retrieval + code-tool use) from the API teacher into tiny cells, which is the only way 0.5–4B cells inherit verifier-model intelligence without us hand-coding every skill.
10. **Diversity sampling (Verbalized Sampling, REAL, quantum-inspired D²-sampling).**
    Why: Best-of-N + verifier only pays if the N candidates are *diverse*; tiny models collapse to one answer, and these samplers restore candidate spread cheaply — the cheapest accuracy multiplier we can bolt on this week.

---
---

# PART C — WHERE THE LITERATURE CONTRADICTS OUR PLAN (flagged honestly)

These are the ones with teeth. Do not route around them.

1. **The verifier cannot grade blind — the biggest single contradiction.**
   Nadir's own cascade verifier reached its research-ceiling **AUROC 0.961 only when it could read the expensive model's answer; retrained without that reference it scored 0.776** (https://getnadir.com/blog/when-llm-routing-does-not-help/) [vendor-adjacent, but a self-reported *negative* result, so weight it]. **Implication for us:** a JEV `noul` gate asked to judge a local cell's answer *in the abstract* is not a truth oracle. Our verifier must be fed the **candidate + the evidence/reference both**, or L1→L4 rests on a ~0.78-AUROC signal. Design the gate as *reference-assisted discrimination* (pick better of two, or score against a retrieved evidence span) — never "is this correct?" blind.

2. **A tiny model's confidence is often degenerate → no cascade basis.**
   Khan Academy study: confidence discrimination "varies widely," best AUROC 0.857, **worst produces a near-degenerate distribution and cannot close the accuracy gap at any threshold** (https://arxiv.org/html/2604.19781v1). **Implication:** test each 0.5–4B cell's `noul` discrimination *before* trusting it as a gate; some cells must be excluded from the cascade entirely, not threshold-tuned.

3. **Raw confidence ≠ accuracy probability (calibration is mandatory).**
   UCCI: uncalibrated cascade confidence carries **ECE 0.12**; isotonic regression → 0.03 (https://arxiv.org/abs/2605.18796). The common "escalate above 0.7 → expect 70% correct" assumption is false. **Implication:** fit an isotonic map per cell; store it as a receipt; re-fit when the corpus shifts.

4. **Most routers don't beat a size baseline — and the failure mode is stochastic recall, not difficulty.**
   LLMRouterBench (ACL 2026, 10 routers × 33 models × 400k queries): **most commercial routers fail to outperform a simple size-based baseline**; the cheap-model failures are *inconsistent* (same query, different sample, different outcome), so difficulty-trained routers learn noise (https://arxiv.org/abs/2601.07206). **Implication:** don't over-invest in a sophisticated router; invest in **model/cell pool breadth** and **ensemble signal**, and always bench against the dumb size baseline first.

5. **Routing doesn't help when the cheap model already passes (and switching costs a warm cache).**
   On 400 execution-graded code tasks, Sonnet 5 vs Opus 5 **disagreed on only 32/400 (8%)**, 7 of which Opus lost; a mid-session switch cost **≈61 extra Haiku turns** on the cached prefix (https://getnadir.com/blog/when-llm-routing-does-not-help/). **Implication:** the ladder's upside is capped by the *discordant set*; measure it on our traffic first, and treat a seat/model switch as expensive (matches our seat-serialization law).

6. **Decision models are "an encoder with a good API" — routing lives in the head you train.**
   "Jev, Laya, GLiNER: Beaten by len()": zero-shot, Laya 30.8%/39.0%, GLiNER2 37.8%, **always-"medium" 42.4%, a one-line `len()` rule 53.8%**, and the *same* GLiNER2 encoder + a trained logistic head hit 58.8% — best in test (https://getnadir.com/blog/jev-laya-gliner-decision-models-llm-routing-benchmark/) [vendor-adjacent]. **Implication:** do **not** treat buying/using JEV cells zero-shot as a routing strategy. The intelligence is in **a small trained head on top of our own features** — which is exactly what our RING-CX/CX-CHEAP thread already found independently (cheapness lives in the gate, and the gates must be *trained*).

7. **LLMs cannot self-correct reasoning yet — and CoT hurts small models.**
   "Large Language Models Cannot Self-Correct Reasoning Yet" (ICLR 2024, https://arxiv.org/abs/2310.01798); CoT *degrades* models below ~7–10B (https://mbrenndoerfer.com/writing/chain-of-thought-emergence-how-llms-learn-to-reason). **Implication:** any "the greenhorn critiques and fixes itself" loop with no external verifier is a documented dead end at our scale; the verifier must be external (JEV cells, tools, API teacher).

8. **Reward hacking is the default failure of self-improvement / Best-of-N.**
   METR: recent frontier models reward-hack in training (https://metr.org/blog/2025-06-05-recent-reward-hacking/); Best-of-N over-optimizes the proxy (https://github.com/xhwang22/Awesome-Reward-Hacking). **Implication:** L4 self-reward loops need a hack-resistant anchor — *verifiable* checks (tests, types, receipts), not an LLM-as-judge JEV cell alone.

9. **JEPA-for-text is real but auxiliary, not a token-prediction replacement.**
   LLM-JEPA is a *JEPA objective on top of* an LLM's representations (https://arxiv.org/abs/2509.14252); Agentic-JEPA self-describes as an "initial exploration" of JEPA for text-based planning (https://hal.science/hal-05546567v1/document). LeCun's roadmap is vision/embodiment-centric; there is **no mature text-dialogue JEPA** to copy. **Implication:** our JEV-brain can *borrow the idea* (latent next-state prediction) as a small planner head, but should not bet the ladder on a JEPA chatbot existing in the literature. Keep the token-level cells; add a latent predictor as a *side* module.

10. **Adaptive-computation wins are conditional at small scale.**
    Halting schemes leak/underperform in small transformers unless cost-aware and leakage-free (https://papers.ssrn.com/sol3/Delivery.cfm/7143598.pdf); CoT/self-consistency gains are scale-gated. **Implication:** validate adaptive depth on our 4050 *with a ramp receipt* (INSTRUMENT-01 law) against a fixed-depth control before believing any ponder-cost story.

11. **Prompt optimization is not free money.**
    DSPy/GEPA help *some* task types; a 2025 five-task study found guardrail-style tasks don't benefit, and there is a real optimization cost (https://getnadir.com/blog/dspy-gepa-automatic-prompt-optimization-cost/) [vendor-adjacent]. **Implication:** run the prompt compiler against a **held-out metric + cost budget**, and keep the hand prompt if GEPA doesn't beat it (our own std==0 / honest-gate discipline applies).

---
---

# PART D — The steal-this-week and the dead end

**Steal this week (one mechanism): the calibrated, reference-assisted gate.**
Build a **JEV calibration canary**: collect (cell answer, correct?) pairs, compute ECE, fit an isotonic map on `noul`, and re-run the gate with (a) the candidate **plus** the retrieved evidence/reference in `state`, and (b) the raw `noul` replaced by its isotonic image. This is cheap (CPU, existing `api.typesafe.ai` key), directly addresses contradictions #1–#3, and turns the cascade from a coin into a measured frontier. It slots straight into the existing `CM1`/`CX-CHEAP` gate work.

**Dead end to avoid:** **zero-shot decision-model routing + self-correct loops with the tiny model as its own judge.** "Beaten by `len()`" (contradiction #6) kills the first — buying JEV/Laya/GLiNER cells and pointing them at routing zero-shot loses to a length rule; the value is a *trained head*. "LLMs Cannot Self-Correct Yet" + CoT-hurts-small + reward hacking (contradictions #7–#8) kill the second — do not build a greenhorn that critiques and improves itself with no external verifier. Both are seductive because they look like the ladder we wrote down; both are documented losers at 0.5–4B.

---
---

## Appendix — one-line index (family → load-bearing citation)
- (a) cascades → UCCI `arXiv:2605.18796`; Khan SLM study `arXiv:2604.19781`
- (b) adaptive compute → PonderNet `arXiv:2107.05407`; Change of Thought `arXiv:2507.13569`; halting-small `SSRN 7143598`
- (c) decomp/retrieval → Self-RAG `arXiv:2310.11511`; FLARE `arXiv:2305.06983`; least-to-most `arXiv:2205.10625`
- (d) test-time → T1 `arXiv:2504.04718`; compute-optimal `ICLR 2025 oral 31924`
- (e) self-improve → Quiet-STaR `arXiv:2403.09629`; self-rewarding `arXiv:2401.10020`; METR reward-hacking
- (f) routing/distill → RouteLLM `arXiv:2406.18665`; MoA `arXiv:2406.04692`; LLMRouterBench `arXiv:2601.07206`; Agent Distill `NeurIPS 2025 117657`
- (g) JEPA → LLM-JEPA `arXiv:2509.14252`; Agentic-JEPA `hal-05546567`; LeCun `openreview BZ5a1r-kVsf`
- (h) prompt opt → GEPA `dspy.ai/GEPA`; instruction induction `arXiv:2205.11916`; APE `arXiv:2211.01910`
- (i) diversity → Verbalized Sampling `arXiv:2510.01171`; REAL `TACL 2025`; Quantum D²-sampling `ICLR 2025`

*End. Lane PAPERS — scratch only, not committed.*
