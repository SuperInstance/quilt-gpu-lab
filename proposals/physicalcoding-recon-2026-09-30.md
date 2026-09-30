# Recon — Physical Coding / HexaAnything (HexaFuture)
Source: github.com/HexaFuture/PhysicalCoding @99afb04 (README + `physical_coding_tech_report.pdf`, 40pp, arXiv 2609.35432, released 2026-09-29).
Method: full PDF text extraction (pdf tool models unavailable — pypdf local), README, figure captions. Reverse-engineered for quilt/SuperInstance components.

## Thesis (in one line)
The physical world lacks the medium software agents work in; **give it one by making task state and execution procedures executable, inspectable, verifiable code** — `Code as World` (what is true) + `Code as Policy` (what to do next), with an **independent verifier** deciding completion from *fresh evidence*, never from the model's claim. Self-evolution = admitted edits to any of (z, e, W, P, H, θ, φ, D, M).

## Mechanism inventory (exact names — these are the stealable artifacts)
- **Code as World**: typed entries — objects, relations, observations, measurements, constraints, progress predicates. Every entry carries **provenance** (which call produced it, when, under what experimental condition). Entries are **updated one at a time, never regenerated** → a contradicting observation stays visible instead of silently overwriting. Predicates over these entries are the task requirement. **When entries don't determine a predicate → `INSUFFICIENT EVIDENCE`, never a guess** (policy must re-observe).
- **Code as Policy**: a program of **typed node kinds** — observation, action, VLA invocation, judging, verification, recovery, branching, sequencing, looping. Typed ⇒ **statically checkable before execution**. Holds what an action chunk cannot: plan, experimental conditions, analysis code, recovery branches.
- **Harness** `H_t = (O_t, T_t, V_t, R_t, M_t, Γ_t)`: observation interface, tool registry, verifier, recovery operator, **provenance-aware memory**, and **Γ = execution contracts, permissions, budgets, safety gates**.
- **Runtime equations**: `n_t = π_θ(z, W_t, P_t, O_≤t, M_t)`; `u_t = Dispatch(n_t, T_t)`; `x_{t+1} ~ E(x_t, u_t)`; `W_{t+1} = UpdateWorld(W_t, O_{t+1}, y_t)`; `q_t = V_t(W_{t+1}, y_t, z)` — **q_t is a typed verdict, not a completion token**.
- **Trace** `ξ = {z, W_0:T, P_0:T, O_0:T, u_0:T, y_0:T, q_0:T, M_0:T}` = **the unit of attribution and of update**. Failure is traced to a predicate / condition / tool / recovery branch, then fixed by editing *that* artifact.
- **Typed verdicts**: `PASS | FAIL | INSUFFICIENT_EVIDENCE | BLOCKED | SAFETY_STOP`. Model "finished" ≠ success; low-level status ≠ evidence. Step-limit = stopping condition, **not** automatically task failure.
- **Execution contracts**: `GoalContract` (raw user text immutable + frozen runtime task + acceptance reference), typed policy repr, `ObservationEnvelope` (provenance classes: VLA output | tool output | harness observation | **official evaluator evidence**), `TrialOutcome` (completion, stop reason, step, reward, **evaluator identity, evidence source**), `ExperimentSpec` (task id, seed set, mode, goal mode, step/round budgets, concurrency, task knowledge at batch creation).
- **Orchestrator**: explicit experiment→round→trial state machine; after each tool call a **monitor–verify–continue/intervene** decision (continue | interrupt tool | retry | re-observe | local recovery edit). **Recovery is fail-closed**: unfinished/ambiguous state is never promoted to success.
- **Admission discipline**: a candidate Harness edit must pass **static checks + regression tests + the official evaluator** before its trace is admitted as data. Verifier changes are tested on a *separate* suite; in-episode verdict vs benchmark-label disagreements are kept as counterexamples. Verifier must be independent of the policy — else it confirms its own errors.
- **Self-evolution tuple**: update any subset of (z task spec, e environment, W world prog, P policy prog, H harness, θ model, φ verifier, D data, M memory). Objective is *not* a scalar score but better future performance **with safety, provenance, reversibility preserved**.
- **Three-stage roadmap**: (1) Harness bootstrap with existing models → (2) model–Harness co-evolution (agent diagnoses failures, revises tools/workflows, validated traces → post-training) → (3) physical deployment. **Multi-timescale architecture**: the model generates/optimizes *verified policies* while a real-time controller or VLA executes them.
- **Why closed-loop beats open-loop (math)**: open-loop success ≈ Π p_i over n transitions; per-step state checks localize a failed transition and act on it instead of carrying it forward.

## Numbers worth keeping
- RoboCasa365 overall: XR-1 VLA 56.6% → +Harness 61.1% → +Harness-trained model 61.7%; Composite-Unseen 34.3 → 38.3 → 39.5.
- Instruction-masking ablation: QwenGR00T trained with instruction masked still succeeds 92.3% vs 96.2% conditioned ⇒ **policies mostly map scenes→trajectories, not instructions.**
- VLAs lose >50% of success under viewpoint/initial-state changes; ~0 when object layout is perturbed; more data/capacity does not fix it.
- PhyBench: Hooke's law relative error 1.3% (Opus 5.5) / 2.3% (GPT-6-Astra) / 4.8% (GPT-5.6-Sol); pendulum 1.0–1.9%; coupled oscillators 0.8–1.7%. Real AgileX dual-arm: 5/7 tabletop tasks fully completed, 2 partial **with recoverable evidence**.
- Their own estimate: coordinated evolution of all four targets remains future work; this report covers Harness, tool revision, first data→model update.

## Mapping onto quilt / SuperInstance (the reverse-engineering payoff)
| PhysicalCoding | We already have | Concrete move |
|---|---|---|
| Code as World typed entries + provenance + one-at-a-time update | plato-cf rooms: Lamport versions, tiers (full/gist/hint), `tile_history`, `tile_demote` receipts; quilt-dba staged rooms | Adopt **explicit provenance fields + "update one entry, never regenerate"** as the room mutation rule; contradiction-visibility is what `tile_history` should surface |
| Code as Policy typed nodes, statically checkable | pincher reflex (`/pinch`, `intents_list`), exoj field | Type the reflex nodes; static-check a route before it runs (we currently free-run) |
| Typed verdicts incl. INSUFFICIENT_EVIDENCE | Jev/typesafe judgment cells (noul 0..1, choice, score) — *our* verifier primitive | **Threshold τ on a calibrated noul = INSUFFICIENT_EVIDENCE gate.** Direct, tiny, testable. |
| Trace ξ as unit of attribution/update | i2i-ledger bookings; edge-ledger receipts; superinstance-api `/book`, `/since`, `witness_get` | **Upgrade the booking schema: add `q_t` typed verdict + evidence-source class to every booking** — then failures localize to predicate/tool/branch by query |
| Harness H=(O,T,V,R,M,Γ) | superinstance-api five seams (tiles/rooms, meaning, reflex, field, growth) + 14 MCP tools + per-agent tokens | Our five seams *are* a Harness split; tokens = Γ. Name them that way in the docs |
| Admission: fail-closed, static + regression + official evaluator before a trace becomes data | our pre-registration, frozen gates, honest booking, "diagnose don't re-roll" | **We're already doing the published standard ad hoc — write it up as our admission protocol and cite this** |
| Multi-timescale (model writes verified policies; real-time controller executes) | boat doctrine: cloud policy generation + local boat brain (LFM2.5/Wesley) executing offline | This is the *citation* for the two-layer boat architecture |
| Multiplicative open-loop failure Πp_i | pincher pinch-to-fallback; CM1 gates catching a broken GEN | Same insight from two directions: **an external verdict beats a self-report** — unifies QG2 (structural desert) with our gate results |

## What to steal, ranked
1. **Typed verdict vocabulary + trace schema** (cheap, immediately adoptable in i2i-ledger/superinstance-api D1 schema).
2. **INSUFFICIENT_EVIDENCE as a first-class outcome** — kills false promotions; directly useful in the QG lane (see QG5 below).
3. **Fail-closed admission with evaluator identity recorded** — formalizes our pre-reg discipline.
4. **Provenance envelope on every observation/tile** (we have halves of this).
5. **The three-stage + multi-timescale roadmap language** for fleet/boat positioning docs.

## What NOT to copy
- Their simulator/benchmark scaffolding (RoboCasa365 harness) — we're not doing manipulation.
- VLA-centric tool surfaces — no arms here.
- Their verifier is task-specific; ours must stay *cell-specific* (qcells/typesafe/edge-ledger).

## Spawned queue items (into night spool)
- **PC-1**: verdict-typed booking schema in i2i-ledger (add q_t ∈ {PASS, FAIL, INSUFFICIENT_EVIDENCE, BLOCKED, SAFETY_STOP} + evidence_source). Pre-reg the schema; migrate without breaking existing rows.
- **PC-2**: QG5 — **verdict-typed promotion in the qcells lane**: promote a mutation only when the promotion *survives a CI separation test*, else record INSUFFICIENT_EVIDENCE and re-measure (more shots) instead of promoting on a noisy point estimate. Directly tests QG2's finding that shot noise ≈ landscape effect.
- **PC-3**: reflex nodes typed + static check before dispatch in superinstance-api `/pinch`.
- **PC-4**: write `docs/admission-protocol.md` in quilt-i2i stating our fail-closed admission rule (static + gate + evaluator identity), citing this report's §4/§5.5.
