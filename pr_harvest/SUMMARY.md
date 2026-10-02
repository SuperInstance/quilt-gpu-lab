# PR-HARVEST / SUMMARY.md

Lane PR-HARVEST · 2026-10-01 · read-only `gh` (as SuperInstance) · **nothing posted**.
Coverage: 33 open PRs across 12 repos (all requested; dependabot skipped).
Artifacts: `CARDS.md` (per-PR), `BUILDERS.md` (per-repo), `REPLIES-draft.md` (10+ drafts), `_raw/` (bodies+diffs).

---

## TOP-10 PROBES — ranked by (learning × cheapness)

Rank = how much a *cheap, seed-2718, RTX-4050* run would change what our lab believes, times how
fast it runs. All probes have a stated pass/fail gate. "REPRO" = the PR already ran on comparable
hardware, so this is independent replication.

| # | Probe | Source | Cost | Gate (pass condition) |
|---|-------|--------|------|------------------------|
| 1 | **Certainty-gated ring attractor + dilution law, in torch** | arcade #6 / chiaroscuro #4,#6 | ~5 min | convergence time within 25% of `mass/gain`; v1 H1/H2 reproduced ±5 pts |
| 2 | **KC sparsification: random-proj → WTA-5% → depression-only readout** | chiaroscuro #6 | ~5 min | sparse top-1 ≥ dense null +5 pts; locality ≤102 rows/update |
| 3 | **HOLD vs CAST two-mode absence policy** | chiaroscuro #5 | ~5 min | degraded acc +≥8 pts; clean acc unchanged ±0.5 pt |
| 4 | **Distinct-board re-evaluation of minimax closure** | pie-minimax #2 | ~2 min | global/composed top-1 on 2,423 distinct boards ≥0.99 (or the drop is the finding) |
| 5 | **Different-path second reader vs silent drift** | fleet-triage #4 | ~2 min | self-consistent reader conf drop ≤5%; different-path agreement drop ≥20% |
| 6 | **Air-gap / worktree-vs-index store-of-record** | quilt-in-git #4 | ~2 min | worktree-style loader diverges ≥1 under 50% drop; index-style digest exact 100% |
| 7 | **Independent re-derivation of ledger row hash (cross-language)** | tidepool #11 | ~2 min | 100% digest agreement + ≥1 flip under key-order perturbation |
| 8 | **Same-run baseline re-measurement** | chiaroscuro #11 | ~2 min | re-measured prior == published prior ≤1% |
| 9 | **Canon (lex-min rotation) invariance + fixed-boundary negative control** | edge-lab #3,#4 | seconds | naive diverges 100%; canon invariant 100% where symmetric, diverges ≥95% where not |
| 10 | **Dispatch-skip compute accounting** | chiaroscuro #1 (Lane A) | ~3 min | saved work ≈ abstain fraction ±10%; dense-equivalent exact when no abstain |

**Probes 1–3 are the same cluster seen three ways** (see map) and would be a good single
"ring-attractor × ternary × sparsification" bench day. Probe 4 is almost free and settles a thesis.
Probe 7 audits our *own* ledger, not the PR — highest internal value per minute.

**Runners-up (do if the ten are done):** seam/mechanics probe of pre-booked custody (arcade #5);
non-seeded-source reproducibility audit of our own experiments (pong #88); `arcsin(rho)` numeric
bound (chiaroscuro #10/#12, seconds).

---

## MECHANISM MAP — shared machinery clusters across the fleet

Five machines recur across repos that never shared code. That recurrence is the harvest's main finding.

### 1. Ring attractors (fruit-fly CX / circKF)
- **Where:** chiaroscuro #4 (theory), #6 `tools/fly_cx.py` (v2 certainty-gated), arcade #6
  (predictive paddle v1–v3, ported 1:1).
- **Shared machinery:** E-PG bump (θ, amplitude) + per-tick ω integration; ternary ψ cue gating
  (Commit/Reject/Abstain); **conflict shortens the belief vector** (Reject shrinks A, moves θ by
  `(1−A)·err`); certainty-gated capture.
- **Evolved variants:** linear error metric with circular coordinate (arcade v3); event-local aging
  clock (arcade v3) after the tick-clock exploded; standing-mass dilution as the binding failure.
- **Status:** the one cluster with a **PASS** (flycx 4/4) and a clean cross-project port. Highest
  transfer value for our boat-brain / reflex layer.

### 2. Kenyon-cell sparsification (mushroom-body readout)
- **Where:** chiaroscuro #6 `kc_layer.py`, #9/#10/#12/#13 (geometric-PN rebuild), #4 (MB = online LDA).
- **Shared machinery:** PN encode → seeded random projection (V→2048, ~10% dense) → WTA top-102 (5%)
  → MBON per-class linear readout, **depression-only plasticity** (`W *= 0.8` on mistake; correct = no
  write), locality pin ≤102 rows/update.
- **Key result:** random expansion **fails class-level locality in discrete (synonym) vocab space**
  (0.26 < dense null 0.40); geometric PN (orthonormal cones) *improved the geometry* (G-gates pass) but
  **did not fix the task** (H1–H4 all FAIL, v4 worse) ⇒ **lane CLOSED**: "new evidence, not new constants."
- **Status:** a fully-receipted negative mechanism. Gold: it tells us *where* sparsification does not
  pay (discrete symbol spaces) before we spend GPU hours there.

### 3. Ternary JEV (Value / Formula / Abstain, ψ ∈ {+1,0,−1})
- **Where:** chiaroscuro #1 (per-cell dispatch skip), #5 (HOLD/CAST split), #6 (ψ over the fly stack),
  arcade #6 (ψ dynamics in cells), quilt-in-git adjacent (JEV-as-gate doc).
- **Shared machinery:** ternary evidence register + neighborhood coherence (von Neumann radius) +
  **one-way upgrade per frame** + **Abstain cells skip work entirely** (prior token stays resident).
- **Evolution:** split monolithic Abstain into **HOLD (dark, wait) vs CAST (odor-off, go look)** —
  measured +10 pts on degraded inputs, clean-set parity preserved.
- **Status:** the fleet's most portable *control* primitive; cheap, explainable, and it maps onto our
  experiment bus (wait vs go-look) directly.

### 4. Receipt chains (fnv1a-64, chained from a GENESIS head)
- **Where (the widest cluster):** quilt-in-git #2/#3/#4 (notes receipts, signed ticks, air-gap
  regeneration), tidepool #11 (WAL rows, genesis `0x16`), quilt-edge-lab #1–#4 (CA rows, chain tails,
  canon-invariance), quilt-tools #34 (referral book rows), pong-quilt #88–#93 (sFit/ledger trails,
  genesis re-derived), chiaroscuro #1/#6 (Moth notary, token streams), arcade #5 (WitnessLog
  PENDING→ENTANGLED→COLLAPSED), AI-Writings #73 (the frozen clock **lied for 25M ops and nothing broke
  — because order lived in the chain, not in time**).
- **Shared machinery:** `h = fnv1a64(row ‖ prev_h)`; row = `{args,cell,hash,op,prev_hash,seq}`;
  genesis head per family; **the chain is the recovery/audit mechanism** (air-gap rebuild) and the
  *only* ordering primitive that survives a frozen clock.
- **The fleet's two hard-won refinements:** (a) **read the store-of-record, not the worktree** (index
  vs worktree, air-gap/import); (b) **the judge must be independently implemented** (tidepool's
  second canonicalizer; edge-lab's different-runtime rule-150 check; fleet-triage's two-instrument
  agreement).
- **Our gap:** one hash path in RESULTS, unkeyed, unbound to actor/run-id — the single cheapest fix
  available to us.

### 5. Referral graphs + weight law
- **Where:** quilt-tools #34 (the book), fleet-triage #3/#4, quilt-Kuramoto #2, arcade #5.
- **Shared machinery:** nodes + CANDIDATE/VERIFIED edges; **mass upgrades only on an external merge
  event citing the from-node by name**; the `view()` is a **pure function of booked edges** (ranked
  distribution, ties broken by name, from-node-only repos carry no mass).
- **Honest instrumentation:** the census (244 repos, 7,790 citation sites, 513 hard-outcome checks,
  0.0% FP) is a *consume-don't-rival* second reader for the resolver; its stated limits (shallow HEAD,
  49.2% FP advisory) are part of the number, not a footnote.
- **Our gap:** our ledger lets a claim carry its own weight — the fleet's weight law is the fix.

### Cross-cutting (the doctrine, not a machine)
**Pre-registration → sealed → FAIL honestly → R8 kill → close the lane** (chiaroscuro, arcade,
edge-lab, pie-minimax) and its sibling **honesty architecture** (pong's no-claim marker in source+test;
edge-lab's sealed-FAIL-left-sealed; tidepool's never-invent-a-measurement). Every builder in this
harvest uses some form of it; the discipline is fleet-wide and is what makes these FAILs worth reading.

---

## What our project should STEAL (top 5)
1. **Independent second implementation of our ledger hash** (tidepool) + bind rows to actor/run-id
   (quilt-in-git #3). Two days, ends a whole class of silent-corruption risk.
2. **No-claim marker + same-run baseline re-measurement** (pong #92, chiaroscuro #11) — cheap honesty
   architecture for RESULTS.
3. **The ring-attractor + ternary + KC bench day** (probes 1–3) — one mechanism cluster, three
   falsifiable gates, ~15 min of GPU.
4. **Canonicalize rotation-symmetric artifacts before digesting** (edge-lab #3) + **bound every
   invariance on both sides** (edge-lab #4).
5. **Different-path reader for our own drift** (fleet-triage #4) — our GPU-vs-CPU recomputation lane
   already exists; wire it as a re-scan gate.

## What our project should AVOID
1. **Constant churn** — chiaroscuro spent four PRs to close one lane; adopt "third revision requires
   new evidence, not new constants" (R8) as a QUEUE rule.
2. **Bureaucracy exceeding the experiment** — pong-quilt's bookkeeping (order pins, README arithmetic,
   docs-after-suite) is now a second job; keep our doc checks *automated* so they don't become rounds.
3. **Single-bucket "unknown"** — chiaroscuro #5's HOLD/CAST shows absence has two modes; don't collapse
   them.
4. **Hand-maintained currency** — quilt-tools upgrades are asserted in a seed; if we adopt a weight
   law, pin it against the merge SHA.
5. **Hardcoded absolute paths in receipt writers** — chiaroscuro #1 `token_stream.py` writes to
   `/root/...`; our tools must write next to themselves.
