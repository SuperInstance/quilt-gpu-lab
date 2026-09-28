# SuperInstance Vision Scout — 2026-09-28

Scout lane for Casey's cellular-decomposition vision. Read-only reconnaissance:
local clones in `~/projects/`, GitHub READMEs where no clone exists, and the
quilt-gpu-lab ledger as the ground truth of what has actually RUN.

---

## 1. The vision, restated

A superinstance starts as one big model plus a routine to use it for a task.
As the task is understood, the model doesn't just do the task — it **makes a
cellular logic that does the task**: big cells break work into smaller tasks
passed between cells; the biggest cells decompose further; as cells shrink,
the LLM becomes unnecessary and **small models run the holistic workflow**.
As data accumulates, the big model **simulates inputs/outputs to test whether
the decomposed system still handles everything the super-cell would have**.
Next time a similar task arrives, a **JEV decides the decomposed workflow's
answer is similar enough, and the cloud model call becomes a CHECK**. If the
check fails, the model decomposes the failing part and routes new edges.

This is the Crystallization Curve (`superinstance/ARCHITECTURE.md`) said in
cellular form: γ + η = C — crystallized intelligence (cells, bytecode,
ternary kernels) trades against live intelligence (LLM calls) at fixed C.
Every repo below is one organ of this loop. The lab's own results already
prove load-bearing pieces of it: D1b Look-Again (decomposed reader field
0.857 beats best-single 0.688), D15b (a tiny tuned adapter reads the tone
channel at 0.94 where the base model reads 0.08), D13d (correlation, not
reward, cracks shared keys).

---

## 2. Repo → vision map

| Loop piece | Repo(s) | State on our hardware |
|---|---|---|
| **Cells + opcodes** (the substrate) | `quilt` (engine), `quilt-rust`, `quilt-verilog` (5+1 opcodes, formally proven), `quilt-esp32` | `quilt-verilog` proofs ran in CI; no local silicon run |
| **Receipts** (claims you can challenge) | `quilt-arcade` (fnv1a-64 chains from GENESIS), `quilt-stone` (42/42 chains verified), `git-agent` | stone verifier ran in lanes; arcade chains never re-derived locally |
| **Decomposition** (big cell → small cells) | `ai-forest` (canopy→understory→floor→mycelium→seed-bank ecology), `pasture-ai` (Collie routes intent to LoRA species; Night School breeds), `pincher` (vector DB as runtime, LLM as compiler), `terrain`/`mud2scummvm` (prose → deterministic geometry/interaction graphs) | `terrain` has 255 passing tests; `pasture-ai` Rust never built locally; `pincher` unexplored locally |
| **Small models doing the workflow** | `ternary-trees` (ternary decision forests on {-1,0,+1}), `qthe` (8-bit ternary embeddings), D2 ternary matmul kernel (lab: **KEEP**) | ternary-trees: **zero runs anywhere local**; D2 ran and passed |
| **JEV gating — "the cloud call becomes a CHECK"** | `substrate-llm-client` (multi-provider client w/ JEV gating), `jev-quilt` (cellular decision substrate; D1/D1b ran here), `jeviter` (oracle UI), `jev-garden` (**born today** — trains JEVs from quilt judgments), `quilt-arcade` judge slot | jev-quilt exercised by D1/D1b (KEEP); substrate-llm-client never run locally; arcade judge slot is a **null interface** |
| **Checks & failure → re-decompose** | `quilt-arcade` slots (judge/jester/quantum/predictor — "interfaces now, implementations later"), `coev` (adversarial champion auditing, extracted from pong-quilt C1) | slots all return null by design; coev never run locally |
| **Simulation tests the decomposed system** | `quilt-gpu-lab` itself (the docket IS the simulation program), `quilt-silicon` (SIMT warp emulator, 8/8 schedule-invariance), `quilt-raw`/`quilt-arch` (Q32 bit-exact conformance) | 40+ experiments booked on the 4050; the super-cell-vs-cells equivalence test has **never been run as such** |
| **Cells on silicon** (dispatch) | `cudaclaw` (Rust+CUDA persistent kernel, lock-free unified-memory queue, <1 μs dispatch, warp-level agent parallelism) | never cloned/built locally; `cudaclaws/claw-00` (cell selftest) and `claw-01` (correlate CUDA port) are Python stand-ins — **claw-01's CUDA never compiled** |
| **Shared state that converges** | `SmartCRDT` (G/PN counters, OR-Set, LWW, RGA + ChromaDB + observability; γ+η=C as merge semantics) | never run locally (Docker/pnpm stack) |
| **Human-readable surfaces** (the cousins) | `scummvm-arcade` (WASM ScummVM + MUD twins), `terrain` (MUD → Three.js), `mud2scummvm` (Rust bidirectional bridge) | terrain tested; arcade deployed on Pages; all already-running code |

Repos named in the task that **404 on GitHub**: `ai-pasture`, `error-forest`,
`cocapn-curriculum-forest`. `pasture-ai` absorbed the pasture; `ai-forest`
evolved from it ("evolved from flat pasture" — its own README). The cocapn
lineage survives as `cocapn-health` / `cocapn-plato` and `THE_DIARY_OF_COCAPN.md`.
`lau-terrain` exists but is a shell README (the `lau-*` ecosystem is 77+
crates bridging to cudaclaw via `lau-cudaclaw-bridge`, status unknown).

---

## 3. The gap — top 5 built-but-never-run assets

Casey: *"a huge amount of progress in code has been made without taking the
time to actually try it."* Verified against the lab ledger and local tree:

1. **claw-01 CUDA correlate kernel** (`quilt-gpu-lab/cudaclaws/claw-01/`) —
   full kernel decomposition documented, CPU reference proven **byte-identical**
   (MD5-matched on seed 2718), and the DESIGN.md confesses: *"No actual CUDA
   kernel compilation or GPU execution was performed in this sandbox
   environment due to missing toolchain."* The box still has no `nvcc` —
   only the WSL2 driver passthrough (`/usr/lib/wsl/lib/libcuda.so`).
2. **`SuperInstance/cudaclaw` itself** — the persistent GPU dispatch kernel
   (the literal "cells on silicon" layer). Never cloned to `~/projects/`.
   The local `cudaclaws/` are re-implementations of the idea, not the repo.
3. **quilt-arcade slots + a local `run_all.mjs`** — six games are headless-
   runnable in one command (Node 22 is installed; README timings ≈ 2.3 min
   total), but the ALL GREEN receipt was earned in the z.ai lane, not on
   fleet hardware — and the judge (JEV), predictor (JEPA), and quantum slots
   are interfaces that "implementations come later" for. The CHECK in
   Casey's loop is the one part of the arcade that has never executed.
4. **SmartCRDT** — seven CRDT types, merge observability, convergence
   dashboards: zero local runs. The state backbone that would let fleet
   cells share state offline has never merged two replicas on this machine.
5. **ternary-trees + pasture-ai** — two Rust decomposers, zero local runs
   between them. ternary-trees is the natural *distilled JEV* primitive
   (ternary verdicts: promote/abstain/reject); pasture-ai's Collie is the
   intent→small-model router. Both are `cargo run`-sized efforts.

Born-today repos not even cloned yet: `jev-garden`, `quilt-jepa`.

---

## 4. Prioritized experiments — RTX 4050 (6 GB) runnable

Doctrine: prefer RUNNING existing code over writing new code. Environment
verified: `~/venvs/elephant-gpu/bin/python` → torch 2.14.0+cu126, CUDA on,
RTX 4050 Laptop; Node v22.23.3; **no nvcc** (blocking items 3–4 until the
CUDA toolkit lands in WSL2 — one `apt`/runfile install, ~30 min).

1. **quilt-arcade local ALL-GREEN reproduction** — *Q: does the fleet's own
   box re-derive all 67 checks and every fnv1a chain from GENESIS?*
   Exercises: arcade plugin/cell/receipt layer + Node runner. Clone, `npm ci`,
   `node run_all.mjs`. **~3 min**, zero GPU. Book the receipt in the lab style.
2. **claw-01 CUDA compile + byte-identity run** — *Q: does the designed-but-
   never-run kernel produce identical hashes to its CPU reference on real
   silicon?* Install CUDA toolkit, run `correlate_cuda.py`'s CUDA path vs
   `cpu-output.json`. **~30 min setup + minutes run.** Converts the biggest
   never-tried asset into a receipt.
3. **cudaclaw real build** — *Q: is <1 μs persistent-kernel dispatch real on
   Ada consumer silicon, and how many ternary agent cells fit per warp?*
   Clone SuperInstance/cudaclaw, `cargo run --features cuda`, book latency +
   warp-utilization numbers. **~1 h** (Rust toolchain + build).
4. **ternary-trees as distilled JEV** — *Q: can a ternary RandomForest
   reproduce D15b's 0.94 tone-channel read at <10 k params (and how far does
   it generalize where the adapter failed, D15c-style)?* Fit on existing lab
   artifacts (`probes.jsonl`, `results/d15b_eval.json`). CPU, **minutes**.
5. **E27 hidden-angle relational reconstruction** (already spooled) — *Q: can
   many small models, each seeing one low-dim projection, jointly recover the
   unseen side?* This IS the relational seed; it is pre-registered and
   unclaimed. Synthetic data, **~1 h**.
6. **Wire the arcade judge slot to a local judge** — *Q: with a real (even
   tiny) judge behind the JEV slot, do verdicts change, and what fraction of
   moves would a "cloud call as check" have vetoed?* Point the slot at a
   local heuristic or Ollama (`Liquid-LFM2.5-2.6B`, 127.0.0.1:11434).
   **1–2 h.** First living implementation of the CHECK.
7. **SmartCRDT convergence smoke** — *Q: do two replicas that diverge offline
   rejoin to identical state, and what does convergence_time look like on
   fleet receipts as ops?* `pnpm test` + a two-replica divergence script;
   optionally feed quilt receipt chains as CRDT ops. **~30 min setup.**
8. **Cloud-call-becomes-check, measured** — reuse D1b's corpus/readers:
   simulate big-model verdicts on a sample, gate them with the local reader
   field's agreement check, count saved calls vs wrong-accepts. *Q: what
   fraction of super-cell calls pass the JEV check?* **1–2 h GPU.**
9. **pasture-ai Collie routing smoke** — *Q: does breed.md parsing + intent
   routing run on x86/WSL2 without TensorRT?* `cargo build`, route three
   fake intents, book which species fire. **~1 h.**
10. **Super-cell vs cells equivalence test (the vision's capstone)** — take
    a task the fleet already does (e.g. quilt judgment on D5 probe-foundry
    triples), have the big model produce the verdict AND the decomposed
    reader-field verdict, and measure agreement across a held-out sweep.
    *Q: where does the decomposed system stop handling what the super-cell
    handled?* Overnight batch, **free locally**. The failure curve IS the
    map of where to decompose next.

**Build order:** 1 → 2 → 4 → 5 → 6 → 3 → 7 → 8 → 9 → 10.
Items 1, 4, 5, 6, 7, 9 need no new science — they are receipts waiting to
happen on code that already exists.

---

*Scout: subagent lane, 2026-09-28. Sources: local clones (`~/projects/`),
GitHub READMEs (quilt-arcade, cudaclaw, SmartCRDT, pasture-ai, ai-forest,
ternary-trees, lau-terrain), quilt-gpu-lab QUEUE/SPOOL/RESULTS/GPU-DOCKET,
claw-01 DESIGN.md + VALIDATION.md, superinstance ARCHITECTURE.md. No repo
was modified; this file is the only change in its commit.*
