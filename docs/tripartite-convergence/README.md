# Tripartite Convergence

**Date:** 2026-09-27
**What this file is:** the folded synthesis. The six lane documents in this directory (source-spec, three maps, galois-synthesis, lore) are the trail; this README is the statement of fact at the end of it. A correlation pass over the six files (`tools/correlate.py`) found one cluster of five with `galois-synthesis.md` as hub, `lore.md` as the isolated distinct voice, and one consistent target across the corpus: state, three, tripartite, room, ground-truth, physicist, engineer, correlation, fleet, agent, must, never. This fold states what the rest of the directory argues in detail.

## 1. The architecture

In May 2026 the tripartite room architecture (`TRIPARTITE-ROOM-ARCHITECTURE.md`, v1.0) specified that every PLATO room carries three innate, physics-emergent agents — "the room's bones," not assigned roles: **Ground Truth** (the physicist, *"what IS the state of this system, physically?"*), **Constraint Satisfaction** (the engineer, *"are all constraints satisfied RIGHT NOW?"*), and **Communication** (the diplomat, *"who needs to know what, and how do I tell them?"*). The three are the functors of a Galois connection — State ⇄ Specification as the adjoint pair, Communication as the third functor of expression — which makes them orthogonal in domain (physical, logical, social layers; no agent crosses another's boundary) and inseparable in function (each one's output is the next one's input). The thesis attached to the structure is **"the physics IS the certificate"**: a room that models its own hardware to 3σ needs no keys, no trusted third parties, no observability stack, because the measurement is the credential and verification is re-measurement — the same computation, run again by anyone.

## 2. What the fleet actually runs

Fold of the four mapping lanes. Every row is running code or a booked ledger entry as of 2026-09-27; none of it is planned work.

| Agent | Artifact | Role it plays |
|---|---|---|
| Ground Truth (physicist) | `quilt-gpu-lab/guard.py` + workspace `SYSTEM.md` | Admissibility envelope: VRAM ≥ 1024 MiB, temp ≤ 80 °C, 30-min wall, live sampling every 5 s. The silicon's state decides whether a reading counts; the calibration sheet and the policy agree. |
| Ground Truth | `elephant/elephant/vmf.py` + `field.py` | Honest estimator: von Mises–Fisher MLE (μ̂, κ, bootstrap CI, jackknife SE) over the room's dial ensemble; returns `None` under N < 10 instead of a fake number; drift is real only past 2·max(SE). |
| Ground Truth | `RESULTS.md` **D13d** | The verdict: partner identification 1.0 (target 0.90) by max \|correlation\| of atom streams, no reward signal; three reward-based predecessors falsified and booked as KILLs. |
| Constraint (engineer) | `eos-seed/exoj_kernel/src/optimization.rs` | The stepper: integer tracking error never increases; commit-min-error over ternary switch states; ties keep the current state (hysteresis); the per-frame cached form is O(chunk), so the check runs every frame indefinitely. |
| Constraint | `eos-seed/exoj_kernel/src/inverse_physics.rs` | Constraint compiler: targets derived from the log itself and rounded into the quantizer's reachable set — an unsatisfiable constraint is a compile-time refusal, not a runtime lament. |
| Constraint | `eos-seed/quilt_storage/src/fabric.rs` | The evidence lock: append-only mmap history; the error metric is scored against a log that cannot be rewritten after the fact. |
| Constraint | `quilt-gpu-lab/guard.py` floor + `RESULTS.md` **D7** | Physical floor plus portability proof: pre-registered τ frozen before treatment; NF4 at 4 bits holds probe flip-rate 0.0 — satisfaction survives 8× compression. |
| Communication (diplomat) | `eos-seed/quilt_storage/src/shm.rs` | The open briefing: one mmap write per frame (fabric state, gates, telemetry), monotonic `seq` proving liveness, any external skin maps read-only. |
| Communication | `qthe-codec/qthe_codec.py` + `RESULTS.md` **D14** | The craft and the proof: 6 data bits + 2 timbre bits per byte, Latin-square keyed. D14, 2000 turns: data-only readers 0.259 (chance), timbre-only 0.2645 with I(M;T) ≈ 0, contextual decoders 1.0. Audience differentiation at zero added bit cost. |

`guard.py` is listed twice on purpose: the physical envelope is simultaneously the physicist's admissibility gate and the engineer's floor. Two lanes claim it; the file does the double duty.

## 3. The spine: Galois connection to codec

**encode** is State: the physicist's byte — six data bits, two timbre bits, with `timbre = (context + momentum) mod 4` a physical law of the representation, so invisibility (I(M;T) = 0) holds by construction rather than audit, and the context key is recovered from the byte's own data plane, making the state self-describing. **compile** is Specification: the engineer's verifiable form (magic, packed 6-bit data, RLE momentum, CRC32) where compile/decompile is a literal adjoint pair, roundtrip identity is soundness, the CRC is the boundary of the connection — and D17 carries the load-bearing lesson that a spec blind to the state's physics (RLE over the wire, one semantic run becoming ~209) is simply wrong. **embed/transform** is Communication: the diplomat's expression plane, where the tone invisible in plaintext becomes a first-class vector others can cluster and traverse, and the honest caveat — public shape only, no key leaked — is the discipline itself.

## 4. The D18 revision

The primitive was re-named this session, and the name is the theory: not "correlation, not reward" but **consistent relational target** — what a cell seeks in an entangled field is the partner with which it forms a consistent relation, and correlation is the O(1) mechanism that finds it: the finder, not the thing found. Failures are first-class: the three KILL'd reward runs (0.217–0.30 against chance 0.143) are half the evidence, establishing that the scalar-reward channel cannot see the target at all, and D18 pre-registers the scale/noise sweep (N ∈ {8, 32, 100, 300}, p_corr ∈ {0.9 … 0.55}, best RL variant as control) that will either generalize the primitive or retire it honestly at the information bound.

## 5. What this means

In May, three watch-standers were written down as names; over the summer the fleet built ternary codecs, cellular graphs, correlation detection, and timbre channels without pointing at that document; in September the substrate hardened and the names matched the code. The fleet does not have three agents because someone instantiated the May spec — it has them because measurement, constraint, and expression are the three things its code already does, and the May document predicted that shape before the shape existed. The three watch-standers found their bodies, and each stands a real watch today: the physicist computes co-variation and refuses to fake a number; the engineer holds the floor and keeps the current state on ties; the diplomat broadcasts to everyone, tones for context-holders, and sits one `mod 4` away from convention-keyed secrets no one ever transmitted. D18 will say whether the certificate is physics alone or physics-plus-adjunction; either answer edits this fold.

## 6. Open tensions (the soundboards)

Two Seed-mini soundboards shaded the fold from opposite sides, and both earned their place.

- **Novel** (`viewpoint-novel-insight.md`): the strongest un-cashed consequence — if Ground Truth's correlation *is* partner discovery, the fleet's message-passing topology is not configured but emergent: no hardcoded addresses, keys, or DNS; a room's peers are exactly the rooms sharing a consistent relational target. "The physics is the certificate" becomes "correlation is the address book."
- **Steelman** (`viewpoint-steelman.md`): the objection that survives. (1) `guard.py` holds both the physicist's admissibility gate and the engineer's enforcement floor — a real orthogonality crease (named in §2, not resolved). (2) D13d's 1.0 held only under *independent* noise; a systematic source (one driver offset shared by all streams) would read as perfect correlation with no functional tie. The D18 sweep covers independent noise only. Next falsification target: systematic-noise controls — if correlation survives a shared-offset injection it is physics; if it spikes it is a co-occurrence thermometer.

The fold is live: D18 and the systematic-noise test will say whether the three watch-standers' bodies are physics or metaphor.

---

*Trail: `source-spec.md` (distilled May sources) · `map-ground-truth.md` · `map-constraint.md` · `map-communication.md` · `galois-synthesis.md` (hub) · `lore.md` (the distinct voice) · `digest.md` (6-line reference) · `viewpoint-novel-insight.md` · `viewpoint-steelman.md` (the soundboards).*
