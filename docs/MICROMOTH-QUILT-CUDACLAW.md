# MQC — Micromoth-Quilt-Cudaclaw: A Hilbert-Space Substrate for Relational-Intelligence Cellular Graphs

Status: DESIGN (falsifiable spec, no code). Date: 2026-09-27. Owner: architecture lane.
Inputs: micromoth (pure-Python statevector sim), D3 GPU executor (n=27 complex64, KEEP),
D2 ternary kernels (byte-exact parity + speedup vs fp16), eos-seed/exoj (2-bit packed
ternary fabric + gate), D1 look-again result (ceiling-lift from independent reach, not
vote count), fleet doctrine (Relational-Intelligence Cellular Graph).

## 0. Thesis

A quilt cell should not store a feature vector. It should store a **quantum state** —
2^n complex amplitudes whose information lives in interference structure, not in
per-dimension semantics. This single change converts the cellular graph from "many
embeddings voting" into "many partial views of one logical object," because a
statevector is mathematically a **relational** object: its basis states index
combinations of qubits, so any fact encoded in it is encoded *as a correlation between
parts*, never as a property of one part. Partial readout is then not lossy compression
but physics: tracing out qubits is literally the "view from a hidden angle." The whole
fleet doctrine — multi-view reconstruction of the un-seen side — falls out of linear
algebra we can already execute byte-exactly on the 4050.

## 1. The substrate: |ψ⟩ as the cell's relational knowledge

**Definition.** A cell's memory is an n-qubit statevector |ψ⟩ ∈ C^(2^n) (LSB-first,
micromoth gate semantics: x, h, rx, rz, cx, crx, swap — exactly what D3 executes).
Capacity ledger on 6GB: one cell at n=27 costs ~1 GiB (complex64); n=20 costs 8 MiB,
so ~40 cells at n=20–22 coexist with headroom for kernels. **Cells are n≤24 by
default; n=27 is the demonstrated ceiling, reserved for the fleet-level joint state.**

**Why this is relational knowledge, not a vector.** In an embedding, dimension k means
something alone. In |ψ⟩, amplitude α_x lives on basis index x = b₀b₁…b_{n−1}, a bit
*combination*. Bind each qubit region to a relation slot (an entity, a causal edge, a
story fact). Then every amplitude is a statement about a *conjunction*, and the only
cheap observables — qubit marginals, few-qubit correlations — are projections onto
sub-conjunctions. A cell physically cannot reveal "what it knows" wholesale; it can
only emit marginals. Partial views are enforced by the math, not by policy.

**Write path.** Incoming messages are compiled to gate sequences (Section 3) and
applied in place. A message is thus a *rotation* of existing knowledge — new evidence
interferes with old hypotheses instead of overwriting them. Superposed competing
hypotheses are the natural steady state; commitment = measurement of a chosen register.

**Forgetting.** Unitaries don't forget, so we add a scheduled decoherence dial:
per-epoch mixing of a chosen qubit region toward maximally mixed (one kernel: partial
amplitude damping on the region's marginals). Memory becomes a resource with a
half-life, which is what makes reconstruction experiments about *growth* rather than
accumulation.

**Read path.** A cell emits a projection: the marginal density matrix of a k-qubit
subset (k ≈ 4–8), summary statistics, or a measured bitstring sampled from the
subregister (D3's QRNG path — seeded, receipt-grade). Emission is cheap (2^k); the
full state never leaves the cell.

## 2. cudaclaw: the cell's physics

Two kernel families, both already proven, cleanly split by role:

- **Statevector kernels (D3 executor, extended):** evolve, interfere, marginalize,
  decohere, measure. This is the cell's *physics* — the only way knowledge inside a
  cell changes. Correctness gate stays as-is: byte/fp-tolerance parity against
  pure-Python micromoth for n ≤ 12 on a circuit battery (H, CX, Bell, GHZ, random
  Clifford) before any run counts.
- **Ternary kernels (D2):** the *passband*. Every signal crossing a cell boundary is
  quantized to the 2-bit packed ternary fabric {−1 Blocked, 0 Muted, +1 Positive},
  integer-scored against memory-mapped history rows (exoj semantics). Two reasons,
  both first-principles: (a) **bandwidth discipline** — cells cannot dump gigabytes of
  amplitude at each other; the ternary gate forces compression to the relational
  essentials, and its integer scorer makes admission decisions reproducible and
  auditable; (b) **uniformity** — one wire format means any model, any cell, any
  (future) cloud participant speaks the same protocol.

QRNG output from D3 supplies the fleet's stochastic source for annealing flips and
exploration noise — deterministic under seed, so every experiment has a receipt.

## 3. exoj: the don-able cortex between models and cells

exoj today is a fabric any LLM can don: model emits, fabric quantizes, integer scorer
flips switches only when tracking error drops. In MQC it becomes the cell's
sensorimotor cortex, and the donning contract is:

1. The model receives the cell's last projection (ternary-quantized marginal + recent
   history rows).
2. The model proposes an *action*: a gate sequence on |ψ⟩ (its hypothesis about what
   this new evidence should do to the cell's knowledge) plus an outgoing message
   (projection request or assertion, ternary).
3. The exoj gate scores the proposal against fabric history; commit if error drops,
   revert if not. **No privileged writes.** A bad proposal from a weak (or strong)
   model costs one anneal cycle, never the state.

This is the swap-and-hunt protocol from MODELS.md lifted to actions: Kev-0.8B, Laya,
and mini-jev each don a cell; swap the model, keep the organ machinery identical,
compare. Model churn is absorbed by the gate — that's the stability story that lets
many small, cheap, occasionally-wrong models share one substrate without any of them
being trusted. Cells with different donned models become *different kinds of
observer*, which is precisely what multi-view reconstruction needs.

## 4. Relational growth: multi-view hidden-state reconstruction

The doctrine, concretized. A hidden target T is prepared by an oracle circuit U_T;
no cell ever sees U_T or |ψ_T⟩ whole. Cell i holds |ψ_i⟩ and receives only projection
P_i(T) — read access to qubit subset S_i through a lossy channel. The {S_i} are chosen
so that (a) their union covers all qubits, (b) no single S_i does, and (c) **critical
facts live in correlations that straddle subset boundaries** (e.g., a fact encoded in
the parity of qubits {3, 11, 19} where no S_i contains two of them). Such facts are
invisible to every isolated cell and recoverable only by combining information across
edges.

Growth loop per round: cells emit projections → donned models propose gate updates +
edge messages (ternary) → exoj gates commit/revert → receivers compile accepted
messages into their own |ψ_i⟩. Relational knowledge has grown when a cell's marginals
contain information about T that was *not* in its own projection but arrived via
edges — directly measurable as mutual information between cell state and hidden
variables, gated on message provenance.

The D1 lesson is load-bearing here: correlated dense votes *lost* to best-single
(−0.076 at k=4) while independent reach bought +0.127. So the graph's reward
structure must price edges by *novel information transferred* (measured MI between
edge traffic and the receiver's unknowns), not by agreement or volume. Redundant
edges are dead weight by construction; the reach-bound curve becomes the graph's
growth telemetry.

## 5. The ground-truth experiment (what the 4050 falsifies)

**Construct.** Hidden targets T from a structured generator with ground truth in
machines: (i) d6_worldgen-style world-states (entity relations, causal edges), (ii)
story manifests with hidden causal facts. Oracle encodes T as U_T|0⟩ on n = 24 qubits
(fits with margin). m = 8–16 cells at n = 20, each with its S_i, each donning a
different small model. ≥300 targets, calibration/eval split, seed bank, receipts —
D1's statistical protocol verbatim (bootstrap CI95, pre-registered thresholds).

**Conditions.**
- **A (isolated + ensemble):** no edges. Each cell reconstructs T̂_i from its own
  projection. Score best-single and the best ensemble of independent guesses
  (weighted vote). This is the "averaging" ceiling.
- **B (relational graph):** same cells, same projections, same total message budget,
  edges live, exoj-gated writes, R rounds. Fleet output T̂_graph assembled from cell
  states.
- **C (traffic control):** identical to B but edge payloads are *permuted among
  receivers*. Bandwidth, timing, and message quantity preserved; only the relational
  targeting is destroyed. This isolates "relational" from "more communication."

**Metrics.** Reconstruction completeness = fraction of hidden facts recovered,
reported split into *within-view facts* (recoverable from one S_i) and
*cross-boundary facts* (recoverable only by combining views). The interesting claim
lives entirely in the cross-boundary split.

**The one measurement.** Δ = completeness(B) − max(completeness(A_best_single),
completeness(A_ensemble)) on cross-boundary facts, with completeness(C) reported as
the noise floor. **Pre-registered verdict: relational growth is doing real work iff
Δ ≥ +0.10 with CI95 non-overlapping against BOTH A conditions, and B ≫ C.** If Δ ≤ 0
or B ≈ C, the mechanism is ensemble averaging in a costume — doctrine falsified,
revised, or bounded, and we say so in RESULTS.md with the same KEEP/KILL discipline
as D1–D3.

## 6. Cloud models: the yang to our yin

Cloud = oracle reach; local = falsifier. Same hidden targets, serialized projections
P_i(T) — a frontier cloud model receives *the identical partial views* (one-shot or
few-shot) and guesses T̂_cloud. Three axes of comparison:

1. **Completeness per view-budget:** cloud single-model vs graph at equal information
   access. If the graph beats a frontier model on cross-boundary facts at equal
   budget, relational structure is buying something scale alone doesn't.
2. **Scaling curves:** cloud accuracy vs number of views shown, against graph
   accuracy vs number of cells/edges. We expect different shapes — saturation vs
   reach-bound — and the crossover point is the honest map of where each wins.
3. **Bootstrap interchange:** cloud models as *roaming cells* that occasionally don a
   cell through the same exoj gate — same ternary wire format, same no-privileged-
   writes rule. Cloud reach feeds the graph; the graph's job is to retain what cloud
   passes through, cheaply and locally. The falsifiable sub-question: does a graph
   that ingested N cloud visits outperform N isolated cloud calls, measured on
   cross-boundary completeness? Retention is the local fleet's entire value
   proposition, so it gets its own number.

Local runs the ablations (A/B/C, hundreds of targets, overnight, seeded, free) that
cloud budgets can't; cloud runs the reach probes local models can't. Budget lane:
DeepInfra is revoked — cloud probes go through Casey-approved channels only (Workers
AI free tier or explicit nod), budgeted per probe, receipted.

## 7. Build order (subordinate to the falsifier)

D10: marginal/decoherence kernels + parity gates (extends D3). D11: exoj–cell don
contract, one model, one cell, commit/revert telemetry. D12: condition A + C on
world-states (no edges needed to falsify the baseline first). D13: condition B, the
Δ measurement, the verdict. Every stage independently KILLable with a number.
