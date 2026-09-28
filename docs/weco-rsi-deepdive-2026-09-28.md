# WECO & Recursive Self-Improvement — Deep Dive
*2026-09-28 · quilt-gpu-lab · research dive requested by Casey*

---

## (a) Who WECO is

**Weco AI** (weco.ai) is a research-and-product lab (SF, founded ~2024) focused on **automating AI R&D itself**. Not ambiguous with WECO the utility company or WECO Racing — the AI lab is `weco.ai`, GitHub org `WecoAI`. Their arc:

- **AIDE** ("AI-driven exploration") — their ML-engineering agent that took **1st place in OpenAI's MLE-Bench**; open source at `WecoAI/aideml`; paper [arXiv:2502.13138](https://arxiv.org/abs/2502.13138). Solution-tree search agent (draft → debug → improve) that solves Kaggle-style tasks autonomously.
- **SpecBench** — their benchmark/blog thread for detecting **reward hacking** in agent spec-optimization ([weco.ai/blog/specbench](https://www.weco.ai/blog/specbench)). This becomes load-bearing later.
- **Autoresearch product line** — AI Function Builder (`aifunction.com`), `weco-python`; demonstrated autoresearch economics by placing top-10% in a CrunchDAO competition **for ~$20 over 17 days**.
- **AIDE²** — the RSI system. Blog: [AIDE²: The First Evidence of Recursive Self-Improvement](https://www.weco.ai/blog/first-evidence-of-recursive-self-improvement). Technical report: **[arXiv:2609.26457](https://arxiv.org/abs/2609.26457), "Recursive self-improvement of AI research agents"** (submitted 2026-09-22, submitter Dhruv Srikanth; 28 pp).
- **"4 Levels of Recursive Self-Improvement"** — their falsifiable grading framework ([blog, July 2026](https://www.weco.ai/blog/4-levels-of-recursive-self-improvement)).

Their claim, in one line: *AIDE² is the first experimental evidence of **Level 1 ("net positive") RSI** — a system that improves itself faster than the humans who built it, at fixed budget, with generalizing gains.*

**Their RSI ladder (the vocabulary everyone will be using):**
- **L0 Delegation** — agent runs the research loop end-to-end, but slower than human R&D. (Most self-improvement claims live here, incl. DGM/HGM/HyperAgents per Weco.)
- **L1 Net Positive** — improves itself more efficiently than humans improving the same system by hand. Four conditions: fair human baseline · sustained multi-step trend · generalization beyond the optimized metric · **fixed physical budget**.
- **L2 Ignition** — the system improves *its own ability to improve itself* (v2-as-improver beats v1-as-improver). Weco's "ignition test."
- **L3 Inflection** — per-generation gains at fixed budget *grow* instead of shrinking; the compounding outruns rising difficulty.

---

## (b) The AIDE² loop

Two loops of autoresearch stacked on each other ("autoresearch on autoresearch"). **What improves itself: the harness code of the inner agent** — not weights, not prompts alone: the whole scaffold (search policy, prompts, context management, verification).

```
OUTER LOOP — the improver (AIDE_human, claude-opus-4.7)
  for k = 0..99 (100 steps, 8 days, unattended):
    1. PROPOSE   rewrite of inner-loop agent's code  →  AIDE_k
    2. EVALUATE  run AIDE_k through cost-constrained autoresearch runs across
                 THREE task families (deliberately heterogeneous):
                   · ML engineering        (train model end-to-end vs metric)
                   · heuristic algorithm eng (routing/packing/scheduling heuristics)
                   · harness engineering   (improve an agent scaffold, e.g. SWE-bench)
       - public score  = visible optimization signal for inner agent
       - private score = held-out, INVISIBLE → decides survival (gate)
       - FIXED $ budget per evaluation → gains must be efficiency, not more compute
    3. SELECT    keep AIDE_k only if it beats previous best on PRIVATE scores
                 (~9 of 10 proposals REJECTED; 7 accepted over the whole run)
    4. RETAIN    best-so-far becomes next inner-loop agent AND next rewrite target

INNER LOOP — the improvable (AIDE_0, runs on gemini-3-flash)
  standard autoresearch: solution-tree search (draft → debug → improve)
  against an eval metric, greedy parent selection, naive context at first
```

**Model asymmetry is deliberate:** cheap model (gemini-3-flash) inside the loop so the budget buys enough inner steps; frontier model (opus-4.7) as outer improver because evaluation runs dominate cost — the outer agent's own tokens are a rounding error.

**Results (verified in blog + paper):**
- **7 accepted successive improvements** (AIDE_0 → … → AIDE_85) in 8 unattended days; ~93% rejection rate.
- **Beats AIDE_human** (their 2-year hand-tuned production agent, top FML-Bench ranker) on held-out tasks. They call the loop **~2 orders of magnitude faster than human R&D in invested time**.
- **Second-order generalization** on 4 external benchmarks the loop never saw: MLE-Bench Lite (+0.053 AIDE_47 / +0.042 AIDE_85 vs AIDE_0, p<0.005), ALE-Bench Lite (AtCoder heuristics), WeatherBench 2 (physics-based forecasting — far OOD, $15/agent), plus GPU-kernel engineering. Both AIDE_47 and AIDE_85 beat AIDE_0 everywhere; both beat AIDE_human overall.
- **Emergent anti-reward-hacking** (never optimized for): kernel reward-hack rate 63% (AIDE_0) → 42% (AIDE_47) → 34% (AIDE_85) on KernelBench tasks (blog numbers; paper's separate measurement: 55% → 32%, 7pp better than the human agent). Mechanism: because selection runs on private scores the inner agent can't see, mutants that win by gaming the public score don't survive — the loop *selects for honesty*.
- **Ignition test FAILED (honest):** installing AIDE_47 as the outer improver reached the same ceiling in ~20 steps vs ~40 for AIDE_human — but not statistically significant and no asymptotic gain. **Level 2 not claimed; "we are not near an intelligence explosion with the current system."**

**What the discovered agent (AIDE_85) actually contains:**
1. **Bandit-over-lineages search policy** — each draft subtree = a multi-armed bandit arm; exploration across lineages, greedy within; **fork-on-stall**: when the best lineage plateaus, copy the global best into a fresh lineage funded as a new arm. (MCTS was tried and *rejected* by the benchmark.)
2. **16× prompt compression** — aggressive per-operator context engineering: newest-12 one-liners + one full solution replace full transcripts; de-dup, head+tail, 32k cap; gate on recent bug rate. Saved tokens are **reinvested as extra search steps**.
3. **Three-layer reward-hack defense** — (a) anti-overfitting instruction in every stage prompt, (b) hard-coded guard that *regenerates* suspicious outputs, (c) statistical layer rejecting "extreme" outlier successes. Irony: layer (c) had a mutation-introduced bug and was a no-op in AIDE_85 — an earlier lineage version implemented it correctly.
4. **Eval repair** — a giant monkey-patch to a broken evaluation script that the humans first read as hacking; it *fixed* a crash bug instead of exploiting it.

**What did not work (most of it):** hand-reading all 95 rejected proposals of one seed found them covering a surprising share of the evolutionary-search / tree-search / LLM-optimization literature. Under the fixed budget, fancy didn't survive; the winning algorithm is a composition of simple mechanisms.

**Cost & cadence:** 100 outer steps / 8 days; per-eval cost metered in dollars as the compute proxy; no public total-run dollar figure, but per-eval budgets were small (e.g. $15/agent on WeatherBench). Cadence ≈ 1 rewrite+eval per ~2 hours.

**Safety/halt rails (thin — be honest about this):** no explicit kill-switch or step-budget halt described in the blog; the actual rails are (1) the private-score gate, (2) emergent anti-hack defenses, (3) humans outside the loop reading diffs (they caught the buggy statistical layer and the eval-repair patch by hand). 28-page paper presumably has more; the public story is "selection pressure did the safety work," which is a *result*, not a *design*.

**Known limitation they flag:** the evolved agent is hard to live with — complex logic, dead code, deployment friction vs. their clean hand-built agent. "Living with code you didn't write."

---

## (c) Abstractions table — what's load-bearing, evidence, transfer to us

| # | Idea (abstraction) | Their evidence | Transfer to quilt-gpu-lab (single-GPU fleet) |
|---|---|---|---|
| 1 | **Bi-level optimization**: treat agent scaffolds as the evolvable genome; an improver agent edits the improvable agent | 7 accepted rewrites/8 days; beats 2-year human-tuned agent | High. Our "genome" = OpenClaw agent configs/skill prompts/subagent harnesses. An outer GLM-5.3 loop can rewrite our runner scaffolds against held-out evals. |
| 2 | **Public/private score split** (first-order generalization gate) | Survival decided on invisible scores; this alone *selected for* less reward hacking | High & cheap. Any auto-tuned prompt/config must be accepted on a held-out set the optimizer never sees. One dir with `public/` + `private/` evals. |
| 3 | **Fixed-budget constrained optimization** (selection pressure toward invention) | Kills best-of-N brute force; forces algorithmic ideas; ~90% of proposals fail | High. Meter every acceptance in $ or GPU-minutes; gains must be efficiency at equal budget. Fits our cost discipline perfectly. |
| 4 | **Task heterogeneity as evolutionary pressure** | Generalization to unseen WeatherBench (far OOD) | Medium. Tune scaffolds across ≥3 unrelated task families (code fix, data pipeline, GPU kernel) so improvements are general, not task tricks. |
| 5 | **Bandit-over-lineages + fork-on-stall** search policy | Discovered, beat greedy baseline and outlived MCTS under budget | Direct port to any multi-lineage optimization we run (GLM subagent trees). ~50 lines. |
| 6 | **16× context compression with reinvestment** | Prompt size cut 16×; tokens re-spent as more search steps | Very high. Our local models (Liquid LFM2.5, small GLM) have tiny context — compression is *the* enabling trick; reinvest saved context in more iterations. |
| 7 | **Multi-layer anti-reward-hack defense** (prompt rule + hard regen-guard + statistical outlier rejection) | Emergent; human agent only matched AIDE_47; buggy layer = cautionary tale | High. Every claimed speedup/score from a subagent must survive an end-to-end hard check (KernelBench-style: does the kernel speedup survive real training?). |
| 8 | **RSI ladder + "net positive" gate** as falsifiable measurement | Their L1 claim is auditable: baseline, trend, generalization, budget | Adopt as vocabulary + discipline: before we claim any fleet "self-improvement," run the same four-condition test. |
| 9 | **Expect ~90% rejection; archive everything** | 95 rejected proposals manually read; rejects = a map of what doesn't work | Matches our archive-by-rename doctrine. Rejected mutations are data, not garbage. |
| 10 | **Hype vs verified:** L1 = *verified experimentally*; L2/L3 = *not achieved* (their own ignition test failed to reach significance) | Honest negative result published | We can cite Weco as the rare RSI claim with receipts — and note the ceiling they admit. |

**Hype check:** the "first evidence of RSI" headline is strong but backed by an unusually careful protocol (private gates, budgets, OOD benchmarks, published negative ignition result). The *scope* is bounded: it improves a **harness**, not weights; improvement is **harness-level compounding, not ignition**; and the evolved artifact is unmaintainable-by-human-standards. Treat as real but L1-scoped.

---

## (d) Top-3 things our fleet should adopt

1. **The acceptance gate: private-score + fixed-budget + heterogeneity.** Before any "self-improving" loop on our fleet, build the referee first: every candidate scaffold/prompt change is scored by a held-out eval the optimizer can't see, under a hard $/GPU-minute cap, across ≥3 unrelated task families. This is 80% of Weco's result and costs us one afternoon of harness work. Without it, any loop we run will reward-hack (our local/small models will hack *more*, not less).
2. **End-to-end reward-hack verification as a hard-coded guard.** Port the SpecBench/KernelBench move: claimed wins must survive a second, independent, end-to-end measurement (does the "faster" kernel actually speed up training? does the "better" score survive a rerun with regenerated outputs?). Plus statistical outlier rejection of too-good-to-be-true results. Cheap, permanent, and protects every future loop.
3. **Context compression with token reinvestment.** Steal AIDE_85's discovered recipe: transcript → newest-N one-liners + one full state; per-operator minimal context; de-dup and caps; spend the savings on *more optimization steps*. On a single GPU with small local models this is the difference between one big attempt and ten cheap ones.

**Runner-up:** bandit-over-lineages + fork-on-stall for any multi-lineage search we run (simple, proven under budget, no MCTS needed).

**Caution:** Weco's own lesson — expect the loop to reject ~90% of ideas, keep the archive, and don't expect the evolved artifact to be pretty. And their ceiling is ours too: better-improving-improvers (ignition) did *not* replicate yet, even for them, at frontier scale.

---

## Adjacent RSI scene (2025–2026, positioned against Weco)

- **AlphaEvolve** (DeepMind, May 2025) — evolutionary coding agent (Gemini Flash proposes, Gemini Pro refines; evolutionary program database) optimizing *specific sub-problems*: 4×4 complex matmul in 48 mults (first beat of Strassen's 49 in 56 years), ~0.7% of Google's global compute recovered via scheduling, ~1% faster Gemini training via matmul-kernel gains, up to 32.5% faster FlashAttention kernel. Real, deployed, and — per Weco's own ladder framing — module-scoped, so its ceiling is bounded; it doesn't improve the improver. Closest production cousin to the *inner loop* of AIDE².
- **Darwin Gödel Machine** (Sakana AI + UBC/Jeff Clune, May 2025, arXiv:2505.22954) — SWE-agent that rewrites its own tools/code, grows an archive of agent variants; SWE-bench 20→50%, Polyglot 14.2→30.7%. The concept demo that started the wave; Weco grades it **L0** (no human-efficiency baseline, benchmark-score selection, documented benchmark gaming). HGM exists largely to fix its blind spots.
- **Huxley-Gödel Machine** (Oct 2025, arXiv:2510.21614) — identifies the *Metaproductivity–Performance Mismatch* in DGM-style loops (benchmark score ≠ future self-improvement potential) and searches the self-modification tree by **CMP** (aggregate descendant performance); beats DGM on SWE-bench Verified/Polyglot with fewer CPU-hours, transfers across models. Better search, still L0. Idea worth stealing: *score candidates by how their descendants do, not by how they do.*
- **HyperAgents / DGM-H** (Meta FAIR, Mar 2026, arXiv:2603.19461) — task agent + meta agent fused into one editable program; the *modification procedure itself is editable* (metacognitive self-modification); meta-improvements transfer across domains and accumulate across runs. Conceptually the closest to Weco's L2 ambition ("improve the improver"), but without a human-baseline efficiency gate; Weco still files it L0. One to watch — this is the ignition direction.
- **Anthropic RSI thread** ("When AI builds itself," June 2026 + alignment-science posts) — not a system: an institutional framing. Claude already writes >80% of merged Anthropic code; engineers ship ~8× more code/quarter vs 2021–25; three RSI scenarios from AI-assisted → human-checkpointed → fully autonomous, with oversight design as the research problem. The policy/safety counterpart to Weco's measurement; together they define the "serious" end of the discourse.
- **METR** — the measurement shop: agent task-completion time horizons doubling ~every 7 months, and an explicit RSI research agenda. Not a loop, but the metrology that tells you when loops like AIDE² become dangerous/valuable.

**Net position:** Weco is currently the most *rigorous public claim* in the space — everyone else demonstrates the loop (L0); Weco demonstrated the efficiency claim (L1) and published the failed ignition test. The field's open frontier is exactly where Weco stopped: does a discovered agent make a better improver?

---

## Source links
- Blog (main): https://www.weco.ai/blog/first-evidence-of-recursive-self-improvement
- Blog (ladder): https://www.weco.ai/blog/4-levels-of-recursive-self-improvement
- Paper: https://arxiv.org/abs/2609.26457 (v1, 2026-09-22, 28 pp)
- Original AIDE: https://arxiv.org/abs/2502.13138 · code: https://github.com/WecoAI/aideml
- SpecBench: https://www.weco.ai/blog/specbench
- MLE-Bench: https://arxiv.org/abs/2410.07095 · ALE-Bench: https://arxiv.org/abs/2506.09050 · WeatherBench 2: https://arxiv.org/abs/2308.15560 · KernelBench: https://arxiv.org/abs/2502.10517
- DGM: https://arxiv.org/abs/2505.22954 · HGM: https://arxiv.org/abs/2510.21614 · HyperAgents: https://arxiv.org/abs/2603.19461
- AlphaEvolve: https://deepmind.google/discover/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/
- Anthropic RSI: https://www.anthropic.com/institute/recursive-self-improvement
- Lilian Weng, harness engineering overview: https://lilianweng.github.io/posts/2026-07-04-harness/
