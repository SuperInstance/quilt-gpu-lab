# GREENHORN — Architecture (ARCH-LADDER lane, 2026-10-01)

Ladder: **L1** JEV-brained decompose-to-intelligent → **L2** decompose+ML fully-local → **L3** tool-bootstrapped skills → **L4** motivated greenhorn. This doc is the build plan for L1, with L2+ gates so levels stay comparable. Hardware: RTX 4050 6GB. Ollama roster: qwen2.5:0.5b, qwen2.5:7b, qwen3.5:0.8b, tev1:4b, tev1:0.8b, nomic-embed-text. JEV = api.typesafe.ai/v1/systemone (verified format in docs/typesafe-judgment-cells.md; key at /mnt/c/Users/casey/key.txt, read at use-time).

Design laws carried in from prior art (violating any of these is a bug, not a preference):
- **COMPOSITE**: one right sensor captures most of the gain; routers can't read oracle headroom; sensor false-positive rate is the wall.
- **RING-CX**: untrained gates are provably *shape gates*. Only trained gates (even 5-param logistic) reach blind regimes.
- **IE3**: dedicated specialist trunks beat joint and sequential models.
- **B1**: width dominates epochs — when in doubt, add cells, not training steps.
- **Anti-GAN**: we're looking for what is PREFERRED WHEN, not "the best" — cells route between ledgers; verdicts are graded, never argmax-winner-take-all.

---

## 1. THE CELL

One runtime object, five instanced kinds. Everything is a cell; the mesh is just cells + typed ledgers + edges.

```json
{
  "cell_id": "skill.physics.archimedes-buoyancy",
  "kind": "skill",                       // trait | skill | judge | world | router
  "model_binding": {"runner": "ollama", "model": "tev1:4b", "temperature": 0.3},
  "prompt": "<evolving prompt text; see §3>",
  "input_ledger": ["msg.user_query", "cell.trait.intent.*"],   // typed topics it reads
  "output_ledger": ["cell.skill.buoyancy.draft"],             // typed topics it writes
  "verdict_slot": {"judge": "cell.judge.relevance", "field": "noul"},
  "confidence_read": "state.jev.verdicts[cell_id].noul",       // filled each tick
  "split_policy": {"threshold": 0.62, "max_depth": 3, "fanout": {"skill": 3, "sensor": 2}},
  "stats": {"n_calls": 41, "noul_ema": 0.71, "split_history": [...], "prompt_version": 12}
}
```

### Taxonomy (local-model sizing for 6GB, one GPU resident set at a time is fine)

| Kind | Model | Role | Count at L1 |
|---|---|---|---|
| **trait** | qwen2.5:0.5b / qwen3.5:0.8b | micro-classifiers: intent, tone, language, topic routing signals. Cheap, fast, one-line outputs | 8–15 |
| **skill** | tev1:4b (heavy) / qwen2.5:3b (alt) | content generators bound to a skill domain; each carries an evolving prompt | 20–60, grows |
| **judge** | **JEV API call** (no local model) | noul / choice / score verdicts: confidence reads, gate checks, integration adjudication, prompt-mutation scoring | 1 config, many calls |
| **world** | nomic-embed + JEPA-latent store (RoomEncoder-analog, ~150k params, E1-proven) | conversation state as embeddings + latent deltas; sensor-view provider ("what changed since last turn") | 2–4 |
| **router** | trait-class output + table | maps topic→skill cells. NOT a learned net at L1 (RING-CX: untrained gates are shape gates — keep routing explicit and inspectable) | 1 |

Judge cells are the only API-touching kind at L1. They are **thin**: one `POST /v1/systemone`, questions as a dict, noul/choice/score with correct criteria shapes (noul→instructions string; choice→criteria dict; score→criteria LIST of ordered levels — gotchas booked).

Ledgers are append-only typed key-values (`msg.*`, `cell.*`, `state.jev.*`) in one JSON-line store per session. Cells communicate **only** through ledgers (Voyager-analog: registry + wiring, qm_bind/qm_link spirit — bind cell → inputs/outputs; wiring is data, editable without code).

---

## 2. THE DECOMPOSITION LOOP

**Confidence = JEV noul on a cell's proposed answer**, asked as: state = {query, cell draft, ledger excerpt}, question `{"type":"noul","question":"Does this draft answer the user's need?","instructions":"Answer true only if the draft is complete, correct, and grounded in the ledger evidence present."}`. Graded noul ∈ [0,1] is the pinch gate — tunable per cell (docs/typesafe-judgment-cells.md: "pinch thresholds adjustable").

```
tick():
  1. TRAIT SWEEP     trait cells classify msg.* → routing signals (local, ~0.5B, fast)
  2. ROUTE           router table picks 1 primary skill cell + k=2 alternates (dedicated
                     trunks — IE3 law; no joint skill model)
  3. DRAFT           primary skill cell writes cell.<skill>.draft to its output ledger
  4. CONFIDENCE      judge cell reads draft → noul c
  5. SPLIT if c < threshold:
        a. DECOMPOSER: tev1:4b runs a decomposition prompt → 2–4 sub-QUESTIONS,
           each a typed claim ("what is X", "is Y true given ledger", "what does the
           user actually want")
        b. For each sub-question: either
             - fan into an EXISTING skill cell (router hit), or
             - SPAWN a fresh cell with a cold-start prompt + sub-question (width over
               epochs — B1 law; new cells are cheap, training is expensive)
        c. EVIDENCE CHECK: judge cell scores each sub-question `{"type":"choice"}`:
           {answerable_from_ledger, needs_world_view, needs_tool, unanswerable}
             needs_world_view → world cell runs a SENSOR-VIEW pass (embedding drift /
               JEPA latent delta = "what changed") and writes a view topic. COMPOSITE
               law: the ONE right sensor does most of the work — prefer buying one
               good sensor-view over three fuzzy draft revisions.
             unanswerable → write gap topic; integration handles honesty
        d. depth++, goto 3 (budget: max_depth 3, max_cells 12, max ticks 8)
  6. ITERATE          mesh message passing (mechanism verdict below)
  7. INTEGRATE        see below
```

**Split fan-out taxonomy (what a split produces):** sub-question cells (fresh skills), sensor-view cells (world reads — only when decomposition reveals missing *evidence*, not missing words), decomposition prompts themselves (archived into the split template library for §3 compilation). A split that only rephrases is a failed split — the decomposer is scored on whether children's aggregated noul exceeds parent's (booked in split_history).

### ITERATION MECHANISM — VERDICT: round-robin tick with JEV-adjudicated merge for L1; distrust-percolation BP deferred to L2

The RING-CX theorem decides this: **untrained gates are provably shape gates.** Signed-trit loopy BP over edges whose weights we have no training signal for is exactly an untrained-gate network — it will propagate *shape* (message length, topic keyword overlap), not *evidence*, into blind regimes. Worse, loopy BP's failure mode is confident wrong marginals on cyclic meshes, and our mesh is loopy by construction. We have no sensor for edge-trust at L1.

So L1 runs **serial round-robin** (deterministic cell order = registry order, one ledger write per cell per tick, judge cell stamps noul on every draft it reads). Reasons:
1. **Debuggable**: a single linear trace shows exactly which cell wrote which topic when — we can diff two runs. Loopy BP marginals are not attributable.
2. **Ring-CX-safe**: the only "gate" is the JEV noul stamp, which is *trained-by-vendor* (calibrated), not untrained-local. We borrow calibration instead of pretending we have it.
3. **Fleet precedent**: CM1's pain point was sensor false-positive rates — round-robin with explicit judge stamps makes every false positive visible in the trace; BP would average it into a smooth wrong answer.

**Convergence criterion** (cheap, no extra API): stop when (a) every active draft's noul has moved < ε=0.05 across two consecutive ticks (stability), OR (b) budget hit (8 ticks / 12 cells / depth 3). Divergence detector: if any noul oscillates with period 2 across 3+ ticks, freeze that cell's prompt (oscillation = the cycle detector from the distrust-percolation idea, promoted to a per-cell rule) and exclude it from integration.

**Answer integration:** candidate syntheses, not a merge-by-committee. Top-2 drafts (by noul) + the gap topics go to tev1:4b as a synthesis prompt → 2 candidate answers → JEV `score` (criteria list: ["incomplete","partially answers","answers with errors","answers cleanly","answers cleanly and shows insight"]) → pick the higher; if within 0.15, JEV `choice` on {"lead_with_direct_answer","lead_with_caveat"} using tone trait. Anti-GAN: this is preferred-WHEN selection between ledgers, not a single argmax winner.

**The distruct-percolation BP mechanism is not dead** — it is the L2 target: once L1 has accumulated ~10³ (cell-draft, verdict) pairs, edges get 5-param logistic gates trained on that history (RING-CX's own remedy: even tiny trained gates reach blind regimes), trits become meaningful (−1 from verdict disagreement, 0 = cold-start damping on never-observed pairs, oscillation → cycle detector drops the edge), and BP replaces round-robin. Ship order: collect data with the dumb mechanism, earn the smart one.

---

## 3. SELF-IMPROVEMENT

**Where prompt engineering lives: in the cell, as evolvable state.** Every cell owns `prompt` + `prompt_version` + a rolling verdict ledger. The improver is a background (post-reply) loop:

1. **Trigger**: cell's noul_ema drops below its historical median by >0.1 over ≥10 calls.
2. **Mutate**: tev1:4b rewrites the prompt under an edit-op set (add constraint, add 1-shot example from the cell's own best/worst verdict pair, tighten output format — format-first is a known block, blocks/format_first_gate). Produce 2 variants.
3. **Score**: replay the cell's last N=8 failed inputs through each variant; JEV `score` each output; keep the winner only if it beats incumbent by ≥0.2 median (dspy-teleprompter analog, but the metric is JEV noul on real traffic, not a task loss).
4. **Book**: old prompt archived (rename, never delete), prompt_version++.

**What gets compiled, per level:**

| Level | Compiled artifact | Compiler |
|---|---|---|
| L1 | prompt text; split templates (decomposer prompts that produced successful splits); router table entries | verdict-ledger replay |
| L2 | edge gates (5-param logistic per edge); distilled judge students (tev1:0.8b fine-tuned on JEV verdict pairs → local noul); skill-cell LoRAs from best-prompt trajectories | ML on the L1 corpus |
| L3 | new *skills as code*: blocks/ entries (playwright sweep, web-search verify, tiny-vision caption) with their own prompt+gate, self-registered via qm_bind-analog | tool loop + judge acceptance |
| L4 | curriculum choices: which tutor question to spend $ on next (expected eval-delta per dollar) | meta-cell over the eval harness itself |

blocks/ stays the compiled skill library (Voyager-analog); a cell whose prompt stabilizes at high noul across 50+ calls graduates to a block with a frozen interface.

---

## 4. LEVEL GATES (falsifiable, one harness)

**Harness `greenhorn_eval`** (built day 1, never changed without re-baselining): 120 fixed prompts — 30 knowledge QA, 30 reasoning/math-lite, 30 multi-constraint chat (persona + format + content), 15 ambiguous/underspecified (correct behavior = ask or state assumptions), 15 refusal/safety-adjacent. Judge = JEV `score` rubric ["wrong","partially right","mostly right","right, clean","right, insightful"] on (prompt, answer) pairs, blind to system identity; 20% of pairs human-spot-checked by Casey to catch JEV-judge drift. Report: mean score ± CI (bootstrap), latency p50/p95, API tokens, cell count. Every level runs the *same* harness — level changes the engine, not the exam.

| Level | Gate (accept/reject, numeric) | Budget rider |
|---|---|---|
| **L1** | GREENHORN-L1 ≥ **qwen2.5:0.5b bare + 0.4 rubric points** mean score (≈ +2 sub-levels), AND ≥ 0.15 over qwen2.5:7b bare on the 30 multi-constraint subset (decomposition must beat raw scale where it should) | ≤ 1.2k JEV tokens/answer p95; p50 latency ≤ 8s |
| **L2** | fully-local engine (zero typesafe calls) within **0.1 points** of L1's score on the same 120; distilled judge agreement with JEV ≥ 0.85 Spearman on a held-out verdict set | 0 API tokens, p50 ≤ 5s on 4050 |
| **L3** | ≥ **20 self-acquired skills** in blocks/ each with noul_ema ≥ 0.7 on its own acceptance set, acquired with **zero big-API calls**; eval gains ≥ +0.1 on the knowledge/reasoning subsets attributable to new skills (ablation: run with new blocks off) | tool calls logged, no cloud LLM |
| **L4** | **learning velocity ≥ 0.05 eval-points per API-dollar**: over a $10 tutor budget, eval-delta/$ ≥ 0.05 sustained across two consecutive $10 windows; spontaneous curriculum (log shows question selection, not random) | tutor spend logged per question |

L1's bar is deliberately modest (0.5b bare is a weak baseline — beating it proves plumbing, the 7b multi-constraint margin proves the *thesis*).

---

## 5. SURFACES

One core: `engine.tick(session)` returns `{answer, trace, ledgers}`. Surfaces differ in what they expose:

| Surface | Priority | Differs |
|---|---|---|
| **MCP server** | agents-first, day 2 | Tools: `greenhorn_ask(query, {max_depth, budget})`, `greenhorn_trace(session_id)` → full cell graph + noul stamps, `greenhorn_cells(filter)` → registry listing. Returns JSON; the *trace is a first-class product* for agent consumers |
| **CLI** | agents-first, day 1 | `greenhorn "query"` → answer + `--trace` JSON to stdout (pipeable), `--json` machine mode, `--budget`/`--depth` flags |
| **TUI** | balanced, day 3 | chat pane + live cell-mesh view (cells light up per tick, noul badges color-coded), ledger inspector — the debug surface |
| **Browser** | human-first, day 3+ | same engine via local HTTP; adds the worked-trace waterfall UI (decomposition tree with per-cell verdicts), share links for eval review |

Streaming: TUI/browser stream draft tokens from the *primary* skill cell (pre-confidence-stamp, marked "draft"); MCP/CLI return final only (agents want atomic verdict-bearing output). Integration answers never stream (they're post-adjudication).

---

## 6. L1 TRACE — worked example

Query: *"my pond pump moves 800 GPH but the frog statue's spray is weak — is the pump dying or is something else going on?"* (session starts cold)

**Tick 1**
- trait.intent (qwen2.5:0.5b) → `msg.intent = "diagnose"`, `msg.topics = ["pumps","hydraulics","diagnosis"]`
- router → primary `skill.troubleshoot.fluid-systems` (tev1:4b), alternates `skill.physics.fluid-flow`, `skill.chat.clarify`
- skill.troubleshoot draft: "The pump is likely failing due to impeller wear. Replace it." → ledger `cell.troubleshoot.fluid.draft`
- judge.relevance: state={query, draft}, noul question → **noul 0.31** < 0.62 → **SPLIT (depth 1)**

**Tick 2 (split products)**
- decomposer (tev1:4b) → sub-questions: SQ1 "what restricts spray output besides pump health?" SQ2 "what in the ledger says the pump's actual output vs rating?" SQ3 "what would the user need to check first?"
- judge.choice per SQ: SQ1 `answerable_from_ledger`→skill.physics; SQ2 `needs_world_view`; SQ3 `answerable`→skill.troubleshoot (re-prompted narrow)
- world cell sensor-view: no conversation history → writes `view.world.context_missing = "no prior flow data"`. COMPOSITE instinct: the right sensor here would be *ask-the-user-for-one-number* → gap topic `gap.needs_head_estimate`
- skill.physics.fluid-flow (tev1:4b): "Weak spray at rated GPH usually = head loss or line restriction, not pump death — tubing diameter, check valve, clogged fountain head, and vertical lift (head) cut effective flow" → noul **0.83**
- skill.troubleshoot (re-prompted): "Check in order: filter/strainer clog, fountain-head orifice scale, tubing kinks, then impeller" → noul **0.79**

**Tick 3** — noul deltas < 0.05 on both active drafts → **converged** (3 ticks, 5 cells, ~2.1k JEV tokens)

**Integration** — top-2 drafts + `gap.needs_head_estimate` → tev1:4b synthesis ×2 → JEV score: cand-A ["answers cleanly"] 3.4, cand-B ["mostly right"] 2.9 → cand-A:
> "Weak spray with a healthy-rated pump usually isn't a dying pump — it's head loss: scale in the fountain head, a clogged strainer, kinked tubing, or too much vertical lift for the run. Check the orifice and strainer first (5 min), and tell me the height from pump to spray outlet — at 800 GPH even 3–4 ft of head plus a narrowed orifice will look exactly like this. If flow is weak even at zero lift with a clean head, *then* suspect the impeller."

Judge-stamped final noul 0.88. Note the decomposition produced an **evidence gap → one user question** (right-sensor doctrine), not three more paragraphs.

---

## 7. BUILD ORDER + RISKS

**Day 1 — the minimal loop.** `cellrunner.py`: cell registry + ledgers (JSONL per session) + tick loop (trait sweep → route → draft → JEV noul → split-on-low-noul with decomposer prompt → depth cap). 3 trait cells, 4 skill cells, 1 judge wrapper (curl POST, correct question shapes, retry-on-empty), 1 world cell stub (embedding of last 3 msgs). CLI. Run the §6 trace by hand. Start `greenhorn_eval` harness + baseline runs (qwen2.5:0.5b bare, qwen2.5:7b bare) — baselines before any tuning.
**Day 2 — integration + MCP.** Round-robin convergence, synthesis + JEV score adjudication, oscillation freeze. MCP server (3 tools). Run the 120-prompt eval end-to-end; book score vs baselines.
**Day 3 — self-improvement + TUI.** Verdict ledgers, noul_ema, prompt mutation loop (edit-ops + replay scoring), split-template library. TUI mesh view. Re-run eval → measure improvement delta (the first L1→L1' signal).

**Risks**
1. **JEV-judge circularity** — the judge grades drafts its own decomposition produced; systematic judge bias passes every gate. Mitigation: 20% human spot-check is load-bearing, and L2's distilled-student agreement metric independently exposes drift.
2. **Split cascades** — decomposer generates plausible-but-useless sub-questions; mesh burns budget, latency balloons. Mitigation: hard budgets (12 cells / 8 ticks / 3 depth), decomposer scored on child-aggregate-noul-minus-parent (failed splits degrade its template).
3. Latency: serial round-robin + API round-trips → p50 risk. Mitigation: judge batching (multiple questions per systemone call — one POST can carry all sub-question `choice` checks), trait cells at 0.5b are ~fast.

**Two assumptions most likely wrong**
1. *That noul measures answer confidence.* It measures graded judgment on the stated question — phrasing sensitivity means the confidence read may swing on question wording, not answer quality. Day-2 experiment: same draft, 3 noul phrasings; if spread > 0.15, pin a fixed question template set.
2. *That round-robin ordering is order-neutral.* Registry-order evaluation means early writers contaminate later cells' ledgers; the mesh may be silently order-tuned. Cheap check: shuffle order, re-run 20 eval prompts, diff scores.

**Push-back (one thing)**: "DECOMPOSES ITSELF until enough components exist to run ITERATIONS and get an intelligent response" implies **count-driven** decomposition — more cells → smarter answer. Our own COMPOSITE result says the opposite: ONE right sensor captures most of the gain and routers can't read oracle headroom. Decomposition should be **evidence-driven**: split to acquire the missing *view* (world-read, tool result, one user number), not to multiply drafts. The §6 example is the doctrine — the split's best product was a single question to the user. If L1 tuning drifts toward "more cells," it's the wrong hill.

---
*ARCH-LADDER lane, 2026-10-01. Prior art: docs/typesafe-judgment-cells.md, RESULTS.md (E1–COMPOSITE/IE3/RING-CX/B1), blocks/README.md. Not committed — scratch only.*
