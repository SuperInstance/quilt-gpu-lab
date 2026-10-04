# GREENHORN — master ideation fold (keeper synthesis target)

Casey directive 2026-10-01 19:15: self-decomposing chatbot as a quilt of logic.
JEV (typesafe.ai) = intelligence source; local cells bootstrap via decomposition + prompt self-engineering.
Ladder: L1 JEV-brained decomposition chatbot → L2 fully-local cells (tev1+micros) → L3 tool-bootstrapped growth → L4 motivated greenhorn (API-budgeted self-teaching).
Surfaces: MCP/API (agents-first) · CLI (agents) · TUI (balanced) · browser (human-first).

## Lane inputs (all landed 2026-10-01 19:1x-19:2x)
- [x] RECON-POC.md — QuantumArtHack is a QPIXL quantum-codec fork, NOT a chatbot; zero mothquantum API calls (real surface = undocumented Atlas Platform API, OPEN follow-up). Steals: FrugalGPT verdict loop (llmcascade.py:121-142), RouteLLM budget→quantile threshold (calibrate_threshold.py:55), QPIXL rank-threshold compression knob (qpixl.py:30-36, coupled pruning). ⚠️ RouteLLM SWRanking needs hosted embeddings — use local BERT/MF.
- [x] PAPERS.md — calibration is the gate: UCCI isotonic 31% cost cut; verifier CANNOT grade blind — reference-assisted only (0.961 vs 0.776 AUROC); text-JEPA live: LLM-JEPA 2509.14252 + Agentic-JEPA; top-3 = calibrated cascade / uncertainty-triggered decomposition / verifier-gated BoN w/ tool self-verification; DEAD ENDS: zero-shot routing (beaten by len()), tiny-model self-correction loops
- [x] ARCHITECTURE.md — round-robin L1 w/ JEV-noul stamps; BP earned at L2 after 1e3 verdict pairs; five-kind taxonomy; L1 gate +0.4/0.5b & +0.15/7b @<=1.2k JEV tok, p50<=8s; push-back: evidence-driven split, not count-driven

## Design laws we already own (constraints on any design)
- C2-IL: sensor FP rates are the wall; routers can't read oracle headroom → L2's "as good as JEV" = engineer the CELLS' false-positive behavior, not the router.
- IE3: dedicated trunks beat joint → cells are specialists; routing happens BETWEEN cells.
- RING-CX: untrained gates are shape gates → every gate in the mesh must be TRAINED (even 5-param logistic) or JEV-graded.
- B1: width dominates epochs → tiny cells need the right width, more epochs won't save them.
- typesafe cells: graded noul 0..1 = the confidence read AND the verdict channel (same call serves both).
- Anti-GAN: "preferred when, not best" — the mesh's value is which cell answers WHEN, not a global best answer.
- Distrust-percolation (journal 18:28): signed-trit edges + loopy BP = candidate iteration/convergence mechanism; oscillation = free cycle detector.

## Synthesis (keeper fold, 2026-10-01 20:4x heartbeat)

**Position: L1 as architected, with three cross-lane amendments.** ARCHITECTURE.md is the build plan; PAPERS confirms its load-bearing choices; RECON supplies loop shapes.

1. **Calibration amendment (PAPERS → §2/§4).** Raw JEV noul is used directly as the split gate; papers say confidence must be isotonic-calibrated first (31% cost cut is the headroom). Add a **calibration canary** to day 1: log (draft, noul) pairs from day-1 traffic, fit a 1-D isotonic map, replace raw noul with calibrated noul before tuning any threshold. Cheap (CPU, no new API calls), directly attacks risk #1 (judge circularity) too.
2. **Verdict loop shape (RECON → §2 step 5).** Adopt FrugalGPT's literal loop for the escalation decision: `while budget and score < 1-threshold: escalate` — make the split gate a *verdict-against-threshold* loop with the calibrated noul, not an if. RouteLLM's `quantile(q=1-strong_pct)` mapping becomes how per-cell thresholds are set from a token budget instead of hand-tuned 0.62s.
3. **Confidence knob as runtime (RECON → L2 prep).** QPIXL's rank-threshold compression = one continuous knob that zeroes the least-significant components with pruning coupled through. This is the natural mechanism for C2-IL's "engineer the cells' false-positive behavior": a per-cell *effort knob* (context rank kept) that tightens when calibrated confidence is high. Park for L2; note it now so L1 keeps confidence and effort as separate reads.

**Cross-lane dead ends (both lanes, confirmed):** zero-shot routing (loses to len()); tiny-model-as-own-judge self-correction (reward hacking). Don't revisit.

**Doctrine locked:** decomposition is EVIDENCE-driven — a split's best product can be one question to the user (§6 pond example). Round-robin + vendor-calibrated judge stamps now; trained edge gates + distilled local judges earned at L2 from ~1e3 verdict pairs. Anti-GAN throughout: preferred-WHEN selection, never argmax.

**Build order (unchanged, day 1):** cellrunner.py minimal loop → baselines (0.5b, 7b bare) BEFORE tuning → greenhorn_eval harness (120 prompts, 20% human spot-check load-bearing) → day-1 traffic feeds the calibration canary. Day 2: integration + MCP + phrasing-sensitivity experiment (3 noul phrasings, spread >0.15 → pin template set) + order-shuffle check. Day 3: prompt mutation loop + TUI.

**Open follow-ups:** mothquantum Atlas API recon (RECON); JEV phrasing sensitivity (ARCH assumption #1); order-neutrality check (ARCH assumption #2).
