# Quilt+ML intelligence-growth harvest — SuperInstance

Scout: deep read + local test reproduction, 2026-10-01/02.
Source: 22 repos cloned to `/tmp/scout/<name>` (gh repo clone, depth 1).
Read: README + core code of each; **re-ran tests/experiments locally** where possible (marked ▶).

The question for every repo was: **is there a loop that makes a model/agent measurably
smarter over time — or is it store/receipt bookkeeping wearing a growth costume?**

---

## Ranked verdict table

| Tier | Repo | The growth mechanism | Loop? | Runnable now | Evidence |
|---|---|---|---|---|---|
| **A1** | **jev-net** | Hebbian credit-assigned edge weights + threshold excitability; neurons are LLM cells | ✅ real | ⚠️ needs LLM keys (repoint to Ollama) | ▶ receipts: weights moved 0.80→1.00, thresholds 0.12→0.113, judge 9/10 |
| **A2** | **jev-net-worker** | Same net, hosted: learns from every call + **nightly self-play** cron, serves bootable learned state | ✅ real | ✅ live CF worker (needs wrangler+AI) | live deployment + wave-65 run receipts |
| **A3** | **quilt-softjoints** (+storefront) | **Adjustment→cell compiler**: repeated manual fixes compile into permanent cells; freezing test promotes softjoints→lookups | ✅ real | ▶ 26/26 tests, zero network | storefront measured **+2.83 vs bare model at ~1/3 calls** |
| **A4** | **quilt-dba** | Developmental agent: policy improves, then **growth = loading stage-2 cells** when position crosses a bar; JEV-gated curriculum | ✅ semi (growth trigger is scripted) | ▶ 13/13 smoke, e_d1 reproduced | R1 GROWTH CONFIRMED 3/3; β₁ −1→1; byte-identical replay |
| **A5** | **quilt-pincher** | **LLM-as-compiler**: vector miss → compile a new reflex → stored; next identical trigger is a <50ms hit | ✅ real (capability growth) | ▶ 12/12 tests | three-tier engine, veto cell |
| **A6** | **quilt-rl** | Tabular Q-learning *in a quilt sheet*; QRNG-seeded exploration; pinned convergence predicate | ✅ real (converges to known optimum) | ▶ 10/10 tests, zero-dep | T-CONV pin + NC1/NC2 controls |
| **A7** | **quilt-bandit** | Federated bandits; observations as append-only cells; gossip-ring merge; policy = read-time fold | ✅ real | ▶ 17/17 tests | variance collapse 22.36→5.92 measured; headline claims FAILED bars honestly |
| **A8** | **quilt-elf** | Audit loop: score skills → push "improve lowest-scoring skill" tasks → backlog dispatcher runs them when idle/near quota reset | ✅ design complete | ❌ `npm install` 404s a dep | code only, not run |
| **A9** | **quilt-tournament** | Adversarial multi-team competition + rival-idea injection until a champion is found | ✅ process | n/a (docs) | referee scores, R1–R4 rounds |
| **B1** | **quilt-nn** | Neural net as cell graph; weights/grads/SGD-step are cells; per-epoch receipt chain | ✅ standard SGD | ▶ reproduced README tip `f2af70a54b19…` exactly | XOR loss 1.04e-4, verify=true |
| **B2** | **quilt-attention** | One-head self-attention as cell DAG; hand-rolled backprop; fault localized by cell digest | ✅ standard SGD | ▶ 10/10 tests | reverse task; T3 grad check ~1e-10 |
| **B3** | **cellgraph** | Transformer forward pass *as* a cell graph + tensor-level witness/canary; e-process forecast | ✅ (no training loop) | ▶ 16/16 + localization real | perturbation → first-mover cell = consumer, always |
| **B4** | **micrograd-quilt** | Scalar autograd + **genotype/breeder**: tape is the genome, 3-gen evolution smoke harness, exact-arithmetic auditor | ✅ real | ▶ demo A/B/C run | 39/39 teeth; one tooth falls on ill-conditioned graph |
| **B5** | **cot-quilt** | Large model's CoT decomposed into a cell graph by cheaper models; **model judges its own decomposition**, gaps folded back as new cells (graph v2) | ✅ self-extending | ⚠️ needs keys; ▶ lab stubs 6/6+5/5+6/6 pins | first run: judge 6/10 → 5 critique cells |
| **B6** | **cot-quilt-lab** | Smallest runtime where provider/stage/cell are uniform; FAIL-first pins | ✅ infra | ▶ all pins pass (stub providers) | ENOENT-fails-first receipts |
| **C1** | **quilt-ewitness** | Anytime-valid **e-process** for "it learned" claims; retraction built in | ❌ verifier | ▶ 7/7 tests, zero-dep | T1 WITNESSED@324; T3 null never crosses; NC2 retracted |
| **C2** | **quilt-ml-recipes** | 6 receipted+negative-controlled recipes (R2 train, R4 judge calibration, R5 convergence alarm, R6 convergence) | ❌ recipes | ▶ **32/32 LIBRARY CERTIFIED** | R4 Brier 0.212, shuffle gate; R5 flatTail 31 fires / 1 refuses |
| **C3** | **realm-ml** | Evidence-grounded claim verification; mechanical relation evaluator that abstains | ❌ verifier | ⚠️ needs API keys | JEV AUC 0.454 → **allam-2-7b+artifact 0.893**; held-out 8/10 |
| **C4** | **quilt-storefront** | The live storefront app + eval harness (growth measured here) | ❌ app | ⚠️ needs keys | +2.83 blind-judged; freeze-test: **no region froze** (honest non-result) |
| **C5** | **training-throttle** | Load-aware training throttle (4 zones) | ❌ infra | ▶ 41/41 (needs PYTHONPATH) | — |
| **D1** | **model-switching-strategy** | LRU/LFU/priority/specialization/hybrid model eviction | ❌ infra | ❌ tests don't import (`ModelStatus` missing) | "production-ready" claim unverified |
| **D2** | **jev-fusion** | 4 experiments: fusing a discrete judge into a generative loop | ❌ experiments | ⚠️ refuses without a **verified** judge | judge-verification gate is the lesson |

Legend: **A** = actually grows intelligence (learns/adapts/grows over time) · **B** = trains/learns but standard or partial · **C** = instrument/bookkeeping that makes growth trustworthy · **D** = aspirational / broken as shipped.

---

## The A-tier mechanisms in full

### A1/A2 — jev-net & jev-net-worker: hebbian credit assignment over LLM cells
The only repo where the *learning rule is the headline artifact*, not the store.

**Technique.** Neurons are LLM calls. Each fired cell emits a JEV packet = judgment
(confidence 0–1) + typed extractions (salience 0–1) + verdict (`route|spawn|answer|halt`).
The transfer function is `activation(B) += salience × confidence × edge.weight`. Weights
are the learned parameters; `spawn` injects new components at the next hop (the net iterates).

**Growth loop (step by step).**
1. Forward: prompt → input decomposes → prism projection routes extractions along
   `accepts`-filtered edges → cells fire iff `activation ≥ threshold`.
2. Synth: contributions projected along the cells' out-edges into `synth` (learnable).
3. **Judge**: `deepseek-v4-pro` labels every cell `pivotal(+2)/useful(+1)/neutral(0)/noise(−1)`
   + overall score + named gaps.
4. **Hebbian update**, per edge that *actually delivered* into a credited cell (share ∝ weight):
   `w += η · share · delta/2`, η=0.12, clamp [0.05, 1.0]. No delivery ⇒ no phantom credit.
5. **Threshold excitability**: a +2 cell fires easier next pass (×0.97); a noise cell harder (×1.03).
6. Save `jev-net-state@1` delta → any other quilt **boots from the grown weights**
   (`default.json + state.json == the grown net, anywhere`).
7. Worker-only: the nightly cron does steps 1–5 unattended (generate question → forward →
   self-judge → learn), so the net improves while nobody calls it.

**Runnable/evidence.** `jev-net` needs DeepSeek/DeepInfra keys; ▶ I confirmed the local
receipts (`nets/state.json`): `input→mechanism 0.80 → 1.00 (n_updates 2)`, thresholds
adapted. `jev-net-worker` is deployed live with a D1 ledger and a `scheduled()` self-play.
**Verdict: real growth, small net, honest ledger.** Caveat: judging models are unreliable
narrators (they echo/truncate cell names — fuzzy subsequence matching recovers them).

### A3 — quilt-softjoints / storefront: the adjustment→cell compiler
The most *transferable* growth loop in the set, because it improves behaviour, not tensors.

**Technique.** Decompose a domain into `lookup` tables where possible, `softjoint` cells
where a small model must read the "moment as a named vector", and `greeter` cells that are
never decomposed. Then two compile loops:

**Growth loop (step by step).**
1. Run. Whenever state must be fixed by hand, record an *adjustment*
   `{target, before, after, why:{trigger,hypothesis,evidence}, generalizes}`.
2. `compileAdjustments()`: union-find clusters adjustments by (target cell, shared hypothesis
   words); when a generalizable pattern repeats ≥ 2×, emit a `compiled_cell` — a lookup if the
   adjustments were input-keyed, else a formula guard — with provenance `compiled_from: run@seq`.
3. The sheet *gains* cells; history is never rewritten. **Future runs hit those paths natively.**
4. Separately, `freezingTest()` buckets observed moment-vectors; when one region maps to one
   output ≥ 3×, it proposes freezing that region into a lookup row. The model surface
   **shrinks** to what is genuinely dynamic.

**Runnable/evidence.** ▶ `npm test` 26/26, no network. Storefront: blind-judged
**+2.83 mean over the bare small model**, holding 9.0 across waves while the bare model drifted,
at ~1/3 the model calls. The freeze test returned an honest **non-result** (no region froze
across 7 live refunder observations — a fact the emotional vector cannot see), and refused to
freeze a non-deterministic region. That refusal *is* the discipline working.

### A4 — quilt-dba: developmental growth as cell addition
**Technique.** A 12-cell seed sheet with a conservation law `γ+η ≤ C = log₂3` (γ=compute cost,
η=surprise). The agent's policy only advances `state.position` while **surprise declines** —
a JEV-gated curriculum keeps it in the zone where surprise falls.

**Growth loop.** evals run → surprise computed via a JEPA momentum predictor → `policy.action`
greedy+curiosity → when `position ≥ 1000`, `loadSheet(buildSheet(2))` **literally adds cells**
(`sensors.language`, `growth.stage`), restores snapshot values, and logs the addition with the
parent hash. Adding cells IS advancing stages; β₁ (first Betti number of the live cell graph)
moves −1 → 1.

**Runnable/evidence.** ▶ `node experiments/smoke.mjs` 13/13; ▶ `e_d1_stages.mjs` reproduced
the exact README result: **R1 growth CONFIRMED (3/3 seeds, growthAt=299), R2 gate CONFIRMED
(unguided arm never grows: position 10 vs 24500), R5 replay BYTE-IDENTICAL.** R3 (the law)
came back an honest **NEVER-BOUND** at these parameters. Caveat flagged in-repo: arms are
deterministic, so cross-seed variance is vacuous — stochastic worlds are next-wave work.
So the "growth" is a *scripted cell-add at a learned threshold*, not self-authored architecture.

### A5 — quilt-pincher: LLM-as-compiler reflex engine
Trigger → embed → vector match. Hit ≥0.80 → execute in <50ms. 0.55–0.80 → confirm. <0.55 or
miss → **call the LLM to compile a brand-new reflex**, store it, execute. The database of
reflexes grows with use; repeated triggers stop costing a model call. ▶ 12/12 tests.

### A6 — quilt-rl: convergence you can pin
Tabular Q-learning where the MDP *is* the sheet (sensors, reward formula, legal-move router,
listener are all cells). ε anneal pinned (1→0 by ep 600), QRNG-seeded. The crown is the
**T-CONV predicate**: converged iff trailing-100 mean ≥ 0.95·optimal **AND** `flatTail(100, 0.01)` —
with NC1 (ε≡0 provably stalls in a 2-cycle) and NC2 (refuses non-converging series) as live
controls. ▶ 10/10. Real RL, but it climbs to a *known* optimum — a template, not open-ended growth.

### A7 — quilt-bandit: federation as an experiment you can lose
Observation cells (not Q-cells) → merges are commutative/idempotent by inheritance → policy is
a read-time fold. Gossip-ring sync (K merges/sync, propagates in K−1 syncs). ▶ 17/17.
The receipted finding is the value: **federation's real effect is variance collapse
(22.36 → 5.92 spread), not "better"** — and both headline claims *failed* their pre-registered
bars. A model for how to run growth experiments honestly.

---

## B-tier: trains, but the "intelligence growth" is standard SGD (or partial)

- **quilt-nn** — weights/gradients/SGD-step as cells; analytic grads (not finite-diff); LCG
  determinism; sha256 receipt chain with a *portable tagged-string preimage* so Python and Node
  agree byte-for-byte. ▶ **I reproduced the README's exact tip** `f2af70a54b19…`, XOR 1.04e-4.
- **quilt-attention** — one-head self-attention DAG, hand-rolled backprop (checked vs central
  differences), per-epoch receipts, **fault localization** by perturbing one weight cell and
  asserting the changed digest set equals the downstream topological slice. ▶ 10/10.
- **cellgraph** — the proof that a transformer forward pass *is* a cell graph: perturbation →
  first-mover cell is always the consumer; `Wq` moves 14 cells, `Wlog` moves exactly 2. Also
  carries the best honest lesson in the fleet: `tensor_digest` cast float64→float32 and a
  9.8e-10 change became invisible — *"a witness log that cannot see a change is worse than one
  that does not exist."* Forecast → witness → e-process (`max log E = 7.690` vs Ville 2.996). ▶ 16/16.
- **micrograd-quilt** — micrograd + (1) exact-arithmetic stochastic auditor, (2) hash-chained
  op tape (`BIND/LINK/EFFECT/VIEW/TICK/FORGET`), (3) **genotype/breeder**: the tape IS the genome,
  viability floor is binary (one wrong leaf grad → score 0). ▶ demo_c shows a small negative-space
  map archive. The in-repo evolution is an explicit **smoke harness only**; the real GAN lives elsewhere.
- **cot-quilt** — a large model's CoT is decomposed into typed steps by cheap models, wired by
  typesafe JEV load-scores, merged across 3 lenses (cross-seed agreement = weight, divergence =
  alternate routes), then **the large model judges its own decomposition** and the named gaps are
  folded back as `origin="critique"` cells → graph v2. This is a real **self-extending** loop.
  ▶ First run receipt: judge 6/10 → 5 critique cells. Needs keys; local `cot-quilt-lab` skeleton
  pins all pass (6/6 + 5/5 + 6/6).

---

## C-tier: instruments (they don't grow intelligence — they stop you lying about it)

- **quilt-ewitness** ▶ 7/7. Anytime-valid e-process, pre-registered σ required, Ville bar 1/δ,
  **retraction** demonstrated (NC2 V-shape witnessed then retracted). The cleanest "does it
  actually learn?" detector in the set.
- **quilt-ml-recipes** ▶ **32/32 LIBRARY CERTIFIED**. Six recipes, each with RECEIPT +
  NEGATIVE-CONTROL + GROW. R4: a judge counts only if it survives the truth-shuffle (Brier alone
  certifies ignorance). R5: "converged" is a shape claim. R2 reproduces quilt-nn's tip from copied code.
- **realm-ml** — JEV as canon gate scored **AUC 0.454–0.510 (a coin flip)**; a 7B model handed the
  right artifact hit **0.893**; held-out **8/10 (0.750)**, both misses being "the evidence states a
  relation, the claim asserts it" — fixed by *not asking a model*: a mechanical relation evaluator
  that returns `None` when it cannot decide ("a guess arrives with the confidence of a computation").
- **training-throttle** ▶ 41/41 (needs `PYTHONPATH=.`); load-zone batch/worker/GPU scaling. Infra.
- **quilt-storefront** — the app + the eval harness; growth is measured *here* (+2.83).

---

## D-tier: aspirational or broken as shipped

- **model-switching-strategy** — README says "✅ Production-Ready", but `pytest` **cannot collect**:
  tests import `ModelStatus` / `ResourceManager` from `model_switching`, while the package is
  `model_switching_strategy` and exports `ModelSwitcher` etc. Claim > artifact.
- **quilt-elf** — genuinely good design (vibe-driven accelerator: FLUSH_MODE before quota reset,
  `runAudit()` pushes "improve the lowest-scoring skill" + "generate 10 examples" tasks and
  exponentially averages skill scores). But `npm install` **404s a dependency** and `tsx` is
  missing → the loop has never been run from this checkout.
- **jev-fusion** — the *method* is exemplary: exp4 tests whether a fast judge's mask approaches the
  ORACLE selector (not just beats RANDOM), on a surrogate with exact ground truth. But running it
  prints **"JUDGE UNVERLIABLE — refusing to run"** without a live, pre-verified judge. Discipline
  over demo.
- **cot-quilt-lab** — explicit skeleton (stub providers); pins pass, endpoints are stubs.

---

## Top 3 I'd actually PLAY with on a local RTX 4050 6GB / CPU

**1. jev-net hebbian self-play net — the top pick.**
It's the only repo where the *learning rule* is small enough to hold in your head and genuinely
changes behaviour. It's ~700 lines of stdlib Python, zero exotic deps, and the provider ladder is
pluggable (`jevnet/providers.py`) — repoint the cell ladder + judge to a **local Ollama model on
the 4050** (`llama3.1:8b` or `Liquid-LFM2.5-2.6B`, both already on this box) and you have a
self-improving net running fully offline, with a bootable `jev-net-state@1`. Watch the weights,
watch the thresholds, run `selfplay` in a loop, diff five `state.json`s. Play ideas: 3 cells → 8;
judge = a different local model than the cells (self-judge bias); does η=0.12 vs 0.3 change the
weight trajectory? This is the direct answer to "does a model get smarter over time."

**2. quilt-softjoints + storefront adjustment→cell compiler (CPU-only, zero GPU).**
Zero-dep Node, 26/26 tests, and the loop compiles real "run twice → becomes a cell" growth. You
can wire `runJoint` to the same Ollama endpoint and watch a domain grind from softjoints to lookup
tables. Most transferable mechanism to real assistants, and it already has a **+2.83 measured** app.

**3. quilt-dba developmental growth (CPU, zero keys, sub-second).**
`node experiments/e_d1_stages.mjs` reproduces in ~2s and *you can watch a sheet grow a cell at
eval 299*. Perfect sandbox to attack the honest hole the repo itself flags: make the world
stochastic so cross-seed variance is meaningful, and try making the growth trigger *learned*
instead of hard-coded at `position ≥ 1000`.

*(Runners-up for a quick win: `quilt-rl` and `quilt-ml-recipes` — zero-dep, converge in seconds,
and `quilt-ewitness` to certify the "it learned" claim honestly.)*
