# Tripartite Architecture — Distilled Source Spec

**Purpose:** Reference document for the quilt-gpu-lab tripartite-convergence work. Other lanes map their implementations against this. Everything here is faithful to the three source documents; where the sources are silent (e.g. an explicit Pathos↔Ground-Truth mapping), that is flagged, not invented.

**Sources (fetched 2026-09-27):**

1. `SuperInstance/tripartite-room` — `TRIPARTITE-ROOM-ARCHITECTURE.md` ("Definitive Architecture — v1.0", Forgemaster ⚒️, Cocapn Fleet, 2026-05-09; based on 18+ hardware profiling experiments, 50+ fleet repos, and the Zero-Crypto temporal security paper). Includes Appendix 0 (Simulation-First Protocol, added 2026-05-13) and Appendices A–C (glossary, real-numbers reference, Galois Unification Principle).
2. `SuperInstance/Tripartite1` — `README.md` (SuperInstance AI / `synesis`, v0.2.0, Rust 1.75+, "Production-Ready Phase 1", last updated 2026-01-07).
3. `SuperInstance/tripartite-rs` — `README.md` (same project as Tripartite1 — identical badges/links, plus an extended "Tripartite Protocol Architecture" section with the consensus math, Aristotle framing, and the Rust crate layout; ends with a `callsign1.jpg` image).

**One-paragraph orientation:** Two bodies of work share one tripartite pattern. The **Tripartite Room** doc defines three *innate, physics-emergent* agents per PLATO room (Ground Truth / Constraint Satisfaction / Communication) grounded in Galois-connection category theory and physics-based temporal security. The **synesis** repos (Tripartite1 / tripartite-rs) define three *consensus* agents (Pathos / Logos / Ethos) that must agree before any user-facing response is emitted, grounded in Aristotle's rhetorical triangle with weighted voting and an Ethos veto. The room doc is the theory/physics pole; synesis is the applied/consensus pole.

---

## 1. The Three Agents — Archetypes and Core Questions (Both Namings)

### 1.1 Tripartite Room naming (source 1)

| Agent | Archetype | Core Question | Motto |
|-------|-----------|---------------|-------|
| **Ground Truth** | The Physicist | "What IS the state of this system, physically?" | "I measure what IS." |
| **Constraint Satisfaction** | The Engineer | "Are all constraints satisfied RIGHT NOW?" | "Every constraint, every time, no exceptions." |
| **Communication** | The Diplomat | "Who needs to know what, and how do I tell them?" | "The right information, to the right recipient, at the right time." |

Key properties (source 1, §2):

- **Innate:** the agents *emerge from the room's physics*, not from assignment or configuration. "They are not bolted on; they are the room's bones." An RTX 4050 room has a different Ground Truth than a Raspberry Pi room; a CUDA room has a different Constraint profile than a WASM room; a Telegram room has a different Communication surface than a WeChat room.
- **Not microservices:** "This is not a microservice pattern. This is not Kubernetes with three pods. This is a room — a PLATO room — with three innate perspectives on reality."
- **Complete cognitive unit:** "The physicist knows what IS. The engineer knows what MUST BE. The diplomat knows what OTHERS need to hear."
- **Failure isolation:** any single agent can fail without catastrophic room failure (GT fails → Constraint falls back to conservative estimates; Constraint fails → GT keeps profiling; Communication fails → room goes silent but stays consistent; all fail → room dead, state preserved in PLATO tiles).

### 1.2 Synesis naming (sources 2 & 3)

| Agent | Faculty | Core Question | Covers (tripartite-rs detail) |
|-------|---------|---------------|-------------------------------|
| **Pathos** | Intent | "What does the user actually want?" | Goal, Context, Nuance, Emotion |
| **Logos** | Logic | "How do we accomplish this?" | Method, Steps, Feasibility, Logic |
| **Ethos** | Truth | "Is this safe, accurate, and feasible?" | Safety, Accuracy, Ethics, Constraints |

Key properties (sources 2 & 3):

- **Tripartite consensus:** the three agents form a "Tripartite Council." **"No response is emitted until all three agents agree."**
- **Aristotelian origin:** "The tripartite consensus system draws inspiration from Aristotle's rhetorical triangle. Each agent embodies a distinct reasoning modality."
- **Weighted voting with veto:** consensus score `C = (w_P·S_P + w_L·S_L + w_E·S_E) / (w_P + w_L + w_E)` with `w_P = 0.3`, `w_L = 0.4` (logic dominant), `w_E = 0.5` (Ethos has veto). **Veto:** if `S_E < 0.5` (default `threshold_veto`), the response is blocked regardless of other scores — safety-first.
- **Revision rounds:** if `C < 0.90` (default threshold), agents negotiate — round 1 independent, round 2 see each other's assessments, round 3 targeted revision — max 5 rounds (configurable); falls back to the safest partial response if consensus is never reached.
- **Confidence calibration:** `Final Confidence = C_consensus × (1 − decay(t)) × quality_factor`, with `decay(t) = 1 − e^(−λt)`, `λ = 0.001`, `quality = token_precision × source_reliability`.

### 1.3 On the relationship between the two namings

⚠️ **Neither source states an explicit Pathos/Logos/Ethos ↔ Ground Truth/Constraint/Communication mapping.** Both triads are presented above verbatim; the mapping is a convergence-workspace decision, not source-canonical. Structural resonances worth noting (observations, not claims):

- "Ground **Truth**" and "Ethos (**Truth**)" share the truth faculty; Ethos's question ("safe, accurate, **feasible**") is constraint-flavored, matching the Engineer's "MUST BE."
- Pathos's intent-reading is user-facing, resonating with Communication; Logos's "how" is method/feasibility, resonating with the Constraint agent's operational checking.
- The room triad answers IS / MUST BE / WHO-NEEDS-TO-KNOW; the synesis triad answers WANT / HOW / IS-IT-SAFE. Both are "three orthogonal perspectives that must agree before action."

---

## 2. Growth Rates and Domain Boundaries

### 2.1 Growth model (source 1, §2.3)

| Agent | Growth Rate | Growth Mechanism | Domain Layer |
|-------|-------------|------------------|--------------|
| Ground Truth | **Fast (hours)** | Hardware profiling, thermal learning, timing distributions | **Physical** (timing, temperature, hardware) |
| Constraint Satisfaction | **Medium (days)** | Kernel optimization, drift baseline, fallback tuning | **Logical** (constraints, violations, drift) |
| Communication | **Slow (weeks)** | Protocol learning, fleet topology, human preference modeling | **Social** (messages, protocols, fleet coordination) |

Rationale: Ground Truth grows fastest because hardware discovery is immediate and rich (a new GPU yields thousands of timing measurements within minutes). Constraint Satisfaction grows as it calibrates against Ground Truth's models. Communication grows slowest because fleet topology and human preferences change infrequently.

### 2.2 Domain boundaries — orthogonality (source 1, §2.2)

The three agents are "orthogonal in the categorical sense," one per layer:

- **Physical layer → Ground Truth.**
- **Logical layer → Constraint Satisfaction.**
- **Social layer → Communication.**

**Layer crossing is explicit and mediated:** "The Ground Truth agent does not send Telegram messages. The Communication agent does not profile GPUs. Each agent respects its domain boundary."

Interaction invariants (source 1, §6.3) sharpen the boundaries:

1. No direct hardware access from Communication (never reads sensors, never runs kernels).
2. No external communication from Ground Truth (never messages outside the room).
3. Constraint Satisfaction is stateless between checks (idempotent; drift is tracked, checking is independent).
4. Ground Truth is append-only (new measurements refine models, never overwrite).
5. Communication is lossless in translation (every internal state has an unambiguous human-readable representation).

### 2.3 How growth actually happens (source 1, §3.6, §9.4)

- **Ground Truth mechanisms:** boot calibration protocol (~1 h: CPU per ISA/precision 10 min, GPU per kernel/precision 15 min, memory 5 min, thermal equilibrium 20 min, 1000+ samples per op 10 min) → initial confidence γ ≈ 0.7; steady-state EMA learning (α = 0.001, ~1000 samples to converge — deliberately conservative: flag anomalies first, absorb confirmed changes slowly); daily re-profile (catches aging, dust, thermal-paste drying).
- **Room growth timeline:** Day 1 γ ≈ 0.9 (3σ detection) → Week 1 γ ≈ 0.95 → Month 1 γ ≈ 0.98 (2.5σ) → Month 3 γ ≈ 0.99 (2σ) → Year 1 γ > 0.99 (subtle drift detection). Fleet-wise: 2–3 rooms Day 1 → 10+ Week 1 (attestation active) → 50+ Month 1 (holonomy consensus) → 100+ Month 3 (fleet anomaly correlation).
- **synesis side (source 3):** growth analog is the revision-round negotiation and confidence decay — per-query maturation rather than a long-horizon learning curve.

---

## 3. The Galois Connection: State ⇄ Specification ⇄ Communication

### 3.1 The core diagram (verbatim structure, source 1, §1 "Why Three?")

```
State ─── F ───▶ Specification
  ▲                  │
  │                  │
  └──── G ◀─────────┘
         │
         ▼
    Communication
```

- **F** (forward functor, abstraction): State → Specification.
- **G** (backward functor, concretization): Specification → State.
- **Communication** hangs off the adjunction as the third functor — what the system must *express*.

The three perspectives are the three functors of the Galois connection framework:

1. **State** — what the system actually is (Ground Truth)
2. **Specification** — what the system must satisfy (Constraint Satisfaction)
3. **Communication** — what the system must express (Communication)

### 3.2 The claim attached to it (source 1)

"The Galois Unification Principle (proved across 6 connections in the fleet) shows that these three perspectives are not independent — they are connected by adjunctions. The Tripartite Room is the physical realization of this mathematical structure."

### 3.3 The six proved connections (source 1, Appendix C)

From `galois-unification` (each proved constructively, with explicit forward and backward functors):

1. **Measurement ↔ Signal** — the folding order (§5 below)
2. **Intent ↔ Holonomy** — trivial holonomy ⟺ idempotent propagation
3. **Specification ↔ Implementation** — abstract constraints map to concrete checks
4. **Local ↔ Global** — room-level state maps to fleet-level consensus
5. **Precision ↔ Throughput** — higher precision maps to lower throughput
6. **Time ↔ Temperature** — thermal effects on timing are monotone

**The Galois Unification Principle:** "All constraint systems in the fleet are connected by Galois connections, and the composition of these connections preserves the invariant that constraint satisfaction is decidable in polynomial time for Eisenstein integer constraints."

### 3.4 The instantiated instance: Measurement lattice ⇄ Signal lattice (source 1, §3.5, §8.8)

The folding order is itself a Galois connection:

```
Measurement ≡ ⟦Raw Timing⟧
    ↕ (Galois connection)
Signal ≡ ⟦Anomaly⟧
```

Forward abstraction α: L₁ → L₂; backward concretization γ: L₂ → L₁ (e.g. `γ(NORMAL) = {m : |fold(m) − E[fold(m)]| ≤ kσ}`). The adjunction property: `α(m) ≥ s ⟺ m ∈ γ(s)`. The composition G∘F is the expectation operator E[ ]. "This is exactly the Galois Unification Principle applied to physical measurement."

---

## 4. "The Physics IS the Certificate"

**The deep claim (source 1, §1):** "Every PLATO room is a self-attesting unit. … No external monitoring. No separate observability stack. The room IS its own monitor, its own auditor, its own certificate authority. **The physics IS the certificate.**"

In three sentences:

1. Each room's Ground Truth agent models its hardware's timing so precisely (per-operation baseline μ₀, thermal coefficient α, load coefficient β, variance σ²) that any deviation beyond 3σ (0.27% false-positive rate) is flagged as anomalous in a single pass, in under 5 ms — "No keys exchanged. No certificates verified. No trusted third party. Just physics."
2. A forger cannot fake this because reproducing a timing measurement requires reproducing the *exact* physical stack — same GPU model, same firmware/microcode, same thermal state, same utilization pattern, and the same manufacturing variance ("silicon lottery," unique per chip) — an estimated 34 bits of entropy per device, ≥34,000 bits for a 1000-device fleet, exceeding AES-256 security by over 100×.
3. Attestation is therefore a physical challenge/response (Room A: "run eisenstein_int8_100M and report timing" → Room B: "4.31 ms at 52 °C" → Room A's model predicts 4.29 ms at 52 °C → within 1σ: PASS; 6.0 ms → 21σ: REJECT), making each room simultaneously the source, the checker, and the certificate authority of its own proof — the room's measured physics *is* the credential.

---

## 5. The Folding Order and the Room Lifecycle

### 5.1 The folding order (source 1, §3.5 / §8)

The Ground Truth agent's core algorithm: a **five-stage information-reduction pipeline** that folds millions of raw timing measurements into a single anomaly signal. Each stage "folds away" one source of variation; each φᵢ is a homomorphism that quotients out nuisance variation while preserving the anomaly signal. Formally "a monoid action on the measurement space."

```
Stage 1: Raw Timing → TSC Cycles
  cycles[op] = wall_clock × TSC_frequency        — strips clock-speed variation
Stage 2: Cycles → Precision-Dependent Throughput
  throughput(p) = N_constraints / cycles(op, p)  — strips instruction-count variation
Stage 3: Throughput → Thermal-Normalized Baseline
  throughput_norm = throughput − α(T − T_ref)    — strips temperature effects
Stage 4: Thermal Baseline → Utilization Fingerprint
  fingerprint = throughput_norm − β(U − U_ref)   — strips load variation
Stage 5: Utilization Fingerprint → Anomaly Signal
  anomaly = |fingerprint − E[fingerprint]| > 3σ  — strips everything; what remains is SIGNAL
```

Composed: `anomaly = φ₅ ∘ φ₄ ∘ φ₃ ∘ φ₂ ∘ φ₁ (raw_measurements)`. Stage 5 is "lossy by design — we WANT to lose everything except the anomaly signal" (surjective homomorphism onto ℤ₂ = {NORMAL, ANOMALOUS}). Threshold k: 3σ standard (0.27% FP), 2σ high-sensitivity (4.55% FP), 4σ low-FP (0.006%). Ground-truth calibration: Eisenstein INT8 on RTX 4050 = 4.3 ms ± 0.08 ms per 100M constraints → anomaly window [4.06, 4.54] ms; detection < 5 ms single-kernel, < 500 ms full 1000-room fleet attestation.

### 5.2 Room lifecycle (source 1, §9)

Five phases plus the alert transition:

1. **Birth — Discovery (~1 hour).** Agents come online *sequentially, in dependency order*: Ground Truth first (must know the hardware before anything else: 0–5 min init, 5–20 min calibration suite), Constraint Satisfaction second (20–35 min, consumes GT's dispatch table, first baseline check), Communication third (35–60 min, discovers fleet topology, announces itself, requests temporal attestation from existing rooms for trust bootstrapping). Operational at ~60 min.
2. **Calibration (~4 hours).** 1000+ samples per operation; drift baselines; timing exchange with 3+ fleet rooms; verify against fleet consensus; confirm zero false violations. Exit criterion: reliable models, γ > 0.9, eligible for fleet temporal attestation.
3. **Operation — Steady State.** A 5-second cycle: sample thermal state → run constraint batch / check drift → broadcast heartbeat → evaluate timing deviations → update drift dashboard → route alerts. Throughput: 10B+ constraints/s (GPU), 1B+/s (CPU); heartbeats every 30 s.
4. **Growth.** Continuous model refinement (γ 0.9 → 0.99+) and fleet-relationship growth (2–3 rooms → 100+ rooms; attestation → holonomy consensus → fleet anomaly correlation).
5. **Alert — Anomaly Detected (timeline).** T+0 ms: GT detects > 3σ deviation → T+5 ms: confirms no physical explanation → T+10 ms: escalates to Communication → T+50 ms: P1 alert to user (Telegram/Discord) → T+100 ms: challenges 3 nearby rooms for attestation → T+500 ms: fleet responds (correlated or isolated?) → T+1 s: correlated ⇒ P0 fleet-wide alert, isolated ⇒ keep monitoring per user → T+60 s: resolved ⇒ log incident, resume.
6. **Death.** *Graceful:* Communication announces offline → Constraint flushes violation buffer → GT serializes temporal models to PLATO tiles → final heartbeat ("state preserved") → terminate. *Unplanned:* heartbeat missed for 2× interval (60 s) → fleet marks room SUSPECT → reappears ⇒ re-enter calibration, restore from PLATO tiles; stays gone ⇒ DEAD, removed from roster.

**Appendix 0 upgrade (simulation-first, 2026-05-13):** every interaction now follows `predict → apply → observe → confirm → supersede if wrong`. Tiles carry lifecycle state — **Active** (current truth), **Superseded** (replaced measurement; excluded from active queries — GT marks these), **Retracted** (withdrawn on sensor error/drift; excluded entirely — Constraint marks these); Communication broadcasts only Active tiles. All three agents share a room-level **Lamport clock** (tick on tile production, merge on arrival) for causal ordering without centralized coordination. Status at time of writing: 12 repos upgraded, 489+ tests passing, ~95% PLATO write reduction.

---

## 6. "Why Three?" — The Categorical Argument

The sources give one explicit argument (source 1, §1), which is worth quoting nearly in full:

> "The number three is not arbitrary. It emerges from the categorical structure of constraint systems:
> 1. **State** — what the system actually is (Ground Truth)
> 2. **Specification** — what the system must satisfy (Constraint Satisfaction)
> 3. **Communication** — what the system must express (Communication)
>
> These correspond to the three functors in our Galois connection framework. … The Galois Unification Principle (proved across 6 connections in the fleet) shows that these three perspectives are not independent — they are connected by adjunctions. The Tripartite Room is the physical realization of this mathematical structure."

Unpacked, the argument runs:

- **Three because the structure is three.** A constraint system minimally requires: an actual state (what IS), a specification (what MUST BE), and an expression surface (what must be SAID about it). These are the three functors State ⇄ Specification (+ Communication) of the Galois connection in §3 — not three chosen roles but the three terms of the adjunction.
- **Three because the layers are orthogonal.** Physical / logical / social (§2.2) partition the room's reality without overlap; each layer gets exactly one agent, and mediated crossing keeps the boundaries clean.
- **Three because the perspectives compose into one unit.** "The physicist knows what IS. The engineer knows what MUST BE. The diplomat knows what OTHERS need to hear. Together, they form a complete cognitive unit." Independence-with-adjunction: each can fail alone (§2.4) yet none is meaningful without the others' outputs (GT's dispatch table feeds Constraint; Constraint's dashboard feeds Communication; Communication's fleet reports feed GT's verification).
- **Corroborated by the six proved connections** (§3.3): the same tripartite structure recurs — Measurement/Signal, Intent/Holonomy, Specification/Implementation, Local/Global, Precision/Throughput, Time/Temperature — which is why the doc calls the Galois Unification Principle "the Forgemaster's North Star. Every architectural decision in this document is justified by one or more of these connections."
- **On the synesis side** the "why three" is Aristotelian rather than categorical: the rhetorical triangle — Pathos/Logos/Ethos — as three reasoning modalities whose agreement is the release condition for action ("No response is emitted until all three agents agree"). Three modalities, one veto (Ethos), weighted 0.3/0.4/0.5.

Both triads thus assert the same meta-principle from different foundations: **action requires three concordant perspectives, and three is forced by the structure of the problem — categorical adjunction in the room doc, rhetorical triad in synesis.**

---

## Provenance & Fidelity Notes

- Source 1 is dated 2026-05-09 (v1.0) with an appendix dated 2026-05-13; its "real numbers" come from the fleet's `constraint-bench-suite` on RTX 4050 (eileen/WSL2), Xeon AVX-512, Pi 5 NEON, and WASM, over 18+ May-2026 profiling sessions (Appendix B).
- Sources 2 and 3 are the same project under two repos: tripartite-rs's README embeds the full Tripartite1 README and extends it with the "Tripartite Protocol Architecture" section (consensus math, Aristotle framing, crate map, hardware manifests). Version v0.2.0; Phase 1 (Local Kernel) complete, Phase 2 (Cloud Mesh: QUIC/mTLS, cloud escalation, billing, Cloudflare Workers) 33% at time of writing.
- ASCII diagrams in §3.1 reproduce the source diagram exactly. All quotes are verbatim from the fetched sources. Nothing outside the sources has been imported except the clearly-labeled correspondence observations in §1.3.
