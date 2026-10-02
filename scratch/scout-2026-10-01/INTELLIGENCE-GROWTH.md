# Intelligence-Growth Sweep — 2026-10-01/02

Casey's directive (msg 27099): play with quilt+ml growth techniques + have scouts sweep
SuperInstance, the wider repo landscape, and papers. This is the synthesis.

## The unifying loop (everything that compounds reduces to this)

```
generate -> verify (external, EXACT) -> select -> update weights -> repeat
```

The single most important cross-cutting finding (from papers scout, confirmed by quilt
receipts): **loops with self-judges drift; loops with executable/ground-truth verifiers
compound.** A judge that counts only when it survives a truth-shuffle (quilt-ml-recipes R4)
or a verifier that is `sympy`/unit-tests (ReST-EM, Absolute Zero) is what separates growth
from drift. jev-net's "no phantom credit" (only credit edges whose accepts overlap what was
actually delivered) is the same discipline in Hebbian form.

## Ranked catalog

### A-tier — actually grows (learns/adapts/grows over time)
| Technique | Repo/paper | Mechanism | Evidence |
|---|---|---|---|
| Hebbian credit assignment over LLM cells | jev-net / jev-net-worker | judge labels each cell pivotal/useful/neutral/noise; `w += η·share·δ/2` on edges that delivered; thresholds adapt; bootable state.json; worker self-plays nightly | weights 0.80→1.00; **reproduced offline on local Ollama (this session)** |
| Adjustment→cell compiler | quilt-softjoints + storefront | same manual fix twice → permanent cell; freezingTest demotes stable softjoints→lookups | 26/26 tests; app +2.83 over bare model at ~1/3 calls |
| Developmental cell addition | quilt-dba | JEV-gated curriculum; position advances only while surprise declines; stage-2 cells load at pos≥1000 (β₁ −1→1) | R1 GROWTH 3/3; R5 byte-identical replay (reproduced) |
| LLM-as-compiler reflex engine | quilt-pincher | vector miss → compile new reflex → store; next trigger <50ms | 12/12; three-tier + veto cell |
| Self-extending CoT graph | cot-quilt | large model judges its own decomposition; gaps fold back as `origin="critique"` cells → graph v2 | judge 6/10 → 5 critique cells (first run) |
| Skill-library / iterative prompting | Voyager (MineDojo) | auto-curriculum → write code → env verifies → store passing program in vector library; compounds w/o weight updates | DEMO, 3.3× more items; **best fit for 6GB (no fine-tune)** |
| Expert iteration / ReST-EM | DeepMind ReST-EM (2312.06585) | generate → filter by ground truth → retrain on own winners | beat human-data training, zero new human data |
| STaR / V-STaR rationale bootstrapping | Zelikman (2203.14465) / V-STaR (2402.06457) | keep correct rationales + train verifier on BOTH correct AND incorrect self-gen | beats gold SFT at 7B |
| Self-play w/ verifiable rewards | SPIN (2401.01335), Absolute Zero (2505.03335), R1 (2501.12948) | model proposes tasks AND solves them, scored by code execution; zero external data | AZR 7B SOTA math/code |
| RL that converges, certified | quilt-rl | tabular Q-learning in a sheet; QRNG-seeded ε-anneal; T-CONV shape predicate + NC controls | 10/10 (reproduced) |
| Federated bandit as honest experiment | quilt-bandit | observation cells, commutative merge, read-time fold | variance collapse 22.36→5.92; headline claims failed bars honestly |

### B-tier — trains, but standard SGD (or partial)
quilt-nn (NN as cell graph, 16/16), quilt-attention (attention DAG + fault localization, 10/10),
cellgraph (transformer forward = cell graph, 16/16), micrograd-quilt (exact-arithmetic auditor + breeder).

### C-tier — instruments (don't grow; stop you lying about growth)
quilt-ewitness (e-process with retraction, 7/7), quilt-ml-recipes (32/32 certified, negative
controls), realm-ml (JEV canon gate = 0.454 AUC coin-flip vs artifact+7B = 0.893).

### D-tier — aspirational/broken as shipped
model-switching-strategy (tests can't import), quilt-elf (npm 404), jev-fusion (refuses
without verified judge — the refusal IS the lesson).

## Hands-on play (this session): jev-net self-play, fully offline

Repointed jev-net's cell ladder + judge to local Ollama (qwen2.5:3b cells, qwen2.5:7b judge).
3 self-play rounds, zero metered calls. The net's synaptic weights adapted to the judge's
per-cell feedback:

| edge | initial | final | Δ | n_updates |
|---|---|---|---|---|
| input→mechanism | 0.80 | 1.00 | +0.20 | 6 |
| mechanism→builder | 0.75 | 0.93 | +0.18 | 6 |
| input→skeptic | 0.70 | 0.88 | +0.18 | 5 |
| input→builder | 0.60 | 0.74 | +0.14 | 6 |
| skeptic→builder | 0.70 | 0.70 | 0.00 | 0 |
| builder→skeptic | 0.50 | 0.50 | 0.00 | 0 |

The two zero-move edges are CORRECT: no delivered extraction type overlapped their `accepts`,
so no phantom credit was applied. The discipline works. Full receipt:
`scratch/scout-2026-10-01/jev-net-selfplay-receipt.md`. State: `/tmp/jev-play/nets/state.json`.

## Next experiments (pre-register candidates, 6GB-tractable)

1. **jev-net self-play harness as a standing lane** — run N rounds unattended, track weight
   trajectory + judge-score curve, verify "scores rise as weights saturate the load-bearing
   edges." The local Ollama repoint makes this a zero-cost standing experiment.
2. **ReST-EM / Absolute-Zero at small scale** — QLoRA a 1–3B local model; verifier = sympy +
   unit tests (exact, free, no reward model in VRAM). This is the papers scout's top pick and
   the most-replicated growth loop in the literature.
3. **quilt-softjoints adjustment→cell compiler on a live domain** — wire runJoint to Ollama,
   watch a domain grind from softjoints to lookup tables (CPU-only, already +2.83 measured).
4. **Voyager skill-library loop** — external vector-indexed code library + self-verification;
   grows capability with zero weight updates (most tractable per landscape scout).
