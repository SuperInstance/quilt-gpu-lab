# Canon deep-read → GPU-testable ideas

**Date:** 2026-09-29 · **Author:** canons-scan subagent (read-only on the canon)
**Source canon:** `/home/eileen/projects/quilt-research-canons` (README, `research/**`, `projects/**`, `sprints/**`)
**Target lab:** `/home/eileen/projects/quilt-gpu-lab` (RTX 4050 laptop, 6 GB, torch 2.14.0+cu126)

**Assets that already exist and cost nothing to reuse:** HF cache holds I-JEPA ViT-H/16,
DINOv2-base, V-JEPA 2 ViT-L, CLIP ViT-B/32, all-MiniLM-L6-v2, gte-small, Qwen2.5
0.5B/1.5B/3B-Instruct, Cosmos3-Edge; Ollama serves `qwen2.5:0.5b` + `nomic-embed-text`;
`data/c3/real|synth` frames exist; `experiments/d3_statevector_ceiling.py` is a working GPU
statevector executor. Every idea below rides one of those.

---

## 1. What the canons agent is pushing

- **Artifact-first, self-declaring lineage.** Each run leaves a *runnable* witness that
  declares its successor; the roadmap is in the directory, not in memory.
  (`README.md`, `research/SPRINT-LINEAGE.md`)
- **The canon gate is a structural-completeness test, not a quality scale.** One `noul`
  call at `p > 0.7`; the single rung that flips it is adding the *guarantee* statement
  (+0.690), and everything after it (byte-prefix proof, fail-closed, second implementation,
  Lean proof) is inert. Replacement gate = `min(MECHANISM, EXTERNALITY) > 0.7`.
  (`research/jev-gate-experiments-2026-09-29.md`, `research/HANDOFF.md` §4.1)
- **Batching collapses unless the subject is named.** `noul` unnamed = spread 0.01;
  subject-named = 0.57; `choice` batches (read the distribution, not the argmax);
  `score` is a constant generator (2.500/2.485/2.500 for numpy / 1,285-assertion port /
  empty shell). (`research/loop/INDEX.md`, `research/jev-loop-rounds-9-11-2026-09-29.md`,
  `research/jev-kat-result-2026-09-29.md`)
- **Confidence is not deliberation.** Across all three JEV types confidence is
  uncorrelated with correctness; discrimination and rank-stability are different
  properties and the gate depends on the first.
  (`research/jev-kat-result-2026-09-29.md`, `research/HANDOFF.md` §7)
- **Negative-control doctrine.** Every rule needs a control that exercises the rule's own
  failure mode; a passing suite that *cannot fail* is worse than none because it is
  consumed as evidence. Six of seven bugs in one session were of this class (the
  permanently-empty route passed eleven positive tests).
  (`research/HANDOFF.md` §5, `research/growing-pincher.md`, `research/active-ledger.md`,
  `projects/artifact-first/CASEBOOK.md`)
- **Anti-GAN: novelty in process, sameness in product.** Any objective that rewards
  proximity to a target produces proximity in costumes; replace "the best" with
  "preferred when"; many routes to one answer make a system durable, and *where routes
  disagree is the reading*.
  (`research/anti-gan-route-diversity.md`, `research/route-diversity/route_diversity.py`)
- **Grow-with-withdrawal.** A pincher bypasses on *decayed recent* accuracy, not lifetime
  average (lifetime 0.78 / recent 0.98 at the end); a pincher that cannot be wrong is
  wrong; the signature is structural and inspectable, deliberately not a vector store.
  (`research/growing-pincher.md`)
- **The ActiveLedger is a tensor, not a graph.** One event lands in several planes, in
  each listener's units, and *all entries are correct*; a blocked signal sends nothing
  (not a zero); the projection is the interface; every post lands in both books.
  (`research/active-ledger.md`, `research/HANDOFF.md` §6.4–6.6)
- **Locality is one axis, and the fleet is on the losing end.** Cheeger + Ollivier: flat
  structured lattices lose expansion as they grow (torus `h = 4/n`), negatively-curved
  random ones keep it; the instrument understates decay ~30× above n=24; "locality is
  optimised by 0 plugins and taxed by 2".
  (`research/locality/frontier_run.txt`, `research/family/family_run.txt`,
  `research/tradeoff-paradigms.md`)
- **A spec that does not name the paradigm it TAXES is not finished.** Eight paradigms,
  each structurally blind to something; the finding is that Locality has no owner.
  (`research/tradeoff-paradigms.md`)
- **Legibility/externality is the binding constraint.** 0/10 sealed predictions decidable
  by a stranger (falsifiers, but not substance tests); 85/110 commits carry no
  attributable login and zero carry a signature; no dependency-closed artifact; the
  two-reader rule verifies internal consistency, not external truth.
  (`research/externalisability-audit-2026-09-29.md`,
  `research/attribution-audit-2026-09-29.md`, `research/greater-superinstance-2026-09-29.md`)
- **Artifact before narrative.** Every method that worked fetched an artifact *first*;
  every wrong answer formed a view first. Errors were caught by *internal consistency*
  while external checks passed; timestamps catch order, not sense.
  (`research/atlas/process-atlas.md`, `projects/artifact-first/METHOD.md`)
- **The 6D claim: a cell's encoding is a per-cell decision with its own cost, and the
  decision is transmitted.** glyphcast has a *pyramid* (how much) where the question asks
  for a *menu* (which way, incl. SKIP); no repo in the fleet has one; the L1 aperture is
  the danger case where content-match returns a wrong-but-cheap correspondence.
  (`research/codec-gaps-vs-glyphcast.md`, `research/codec-gaps/delta_limit.py`,
  `research/team/team-lane-u-collision.md`)

---

## 2. GPU-testable ideas (ranked by testability × novelty × cheapness)

### ① The canon gate leaves the oracle — does the step function survive on a local model?
**Claim under test:** the gate is a property of the *claim*, not the oracle ("the gate is a
structural completeness test"). If a 1.5B local model reproduces the step and the
mechanism/externality split, the fleet's promotion mechanism becomes offline and
stranger-reproducible — which is the single biggest open item in the canon. If it does not,
the canon gate is oracle-specific and the fleet's canon is not externally reproducible.
**Source:** `research/jev-gate-experiments-2026-09-29.md` (exp 2/3/4/5, "what I would test
next" → cross-model agreement), `research/HANDOFF.md` §4.1.
**Design:** rebuild the 9-rung monotone evidence ladder + the 2×2 (mechanism × guarantee)
matrix as plain text; elicit `MECHANISM`, `EXTERNALITY`, and composite scores from
`Qwen2.5-1.5B-Instruct` (cached; fp16 ≈ 3 GB) with a fixed rubric prompt, 3 paraphrases per
rung, greedy + T=0.3. Measure: (a) is the level curve monotone with a big step at the
guarantee rung; (b) does `min(axis1,axis2)` separate the 4 evidence states from the
single-number score; (c) run the "bare guarantee" tautology case — a small model should
*fail* it (0.98 on a restatement) and that failure is the finding.
**Cost:** 1.5B fp16 on 6 GB (~3.2 GB VRAM), ~60–100 short generations → **10–20 min
wall-clock**, no training. Pre-empts the same question against `jev-preview` for free.
**Why fruitful/multipliable:** produces a reusable offline gate harness other lanes can run
in CI; any outcome is publishable (either the gate externalizes, or "the gate is a private
instrument" becomes a measured structural failure — and that is a far more useful sentence
than the current assumption). Multiplies: every other claim in the canon that was promoted
by a single API call can be re-scored for free afterwards.

### ② MOTH order/tie preservation under simulated noise — the pre-QPU falsifier
**Claim under test:** "order is preserved; ties are broken; rank readout is ill-defined
exactly where glyph streams live", and the canon's own stated unknown: *"whether order
preservation survives real hardware noise — untested."*
**Source:** `research/moth/moth-qpixl-roundtrip.md`.
**Design:** extend the existing GPU statevector executor (`experiments/d3_statevector_ceiling.py`)
to add a noise channel (depolarizing + amplitude damping) on the angle-encoding circuit;
re-run the canon's own hard cases (2×2 checker, 2×2 ramp, 2×3/2×4 crossing) plus a
repeated-glyph frame, at p ∈ {0, 1e-4, 1e-3, 1e-2}. Metrics: order inversions, tie
variance, nearest-level glyph error. Falsifier: order survives at p=1e-3 noise but ties do
not, or order breaks before ties.
**Cost:** ≤ 12 qubits dense statevector (complex64 ≈ 130 MB), thousands of shot-loops in
torch → **< 10 min**, < 1 GB VRAM.
**Why fruitful/multipliable:** it costs nothing and it *decides whether QPU credits are
worth spending* — that is exactly the "measure the cheap analogue before paying for the
expensive one" discipline the canon preaches. Result feeds the fleet's quantum lane
(`moth`), which currently has no noise model at all.

### ③ Disagreement-as-doubt: does ensemble disagreement predict reader error?
**Claim under test:** the two-reader rule is the fleet's whole verification argument, and
the trade-off ledger already concedes it is miscalibrated *("disagreements are rarer than
the agreement rate suggests, so the true error rate is higher than measured")*. The
testable form: per-sample ensemble disagreement has AUC > 0.5 for per-sample error.
**Source:** `research/tradeoff-paradigms.md` (two-readers row),
`research/greater-superinstance-2026-09-29.md` (§ "verification internalizes trust"),
canon's calibration-ladder framing in `research/HANDOFF.md` §6.2.
**Design:** reuse cached encoders (I-JEPA ViT-H, DINOv2-base, CLIP B/32, V-JEPA 2 ViT-L)
on the existing staged dial bank (`experiments/e12_room_dial_reader.py`, `e15`, `e13b`);
per sample, fit K readers (ridge + LBFGS nonlinear, different folds/seeds), compute
(a) ensemble spread and (b) true squared error against the staged dial; test AUC of spread
ranking error, plus Brier of "spread > τ ⇒ wrong". Cross-encoder disagreement (different
lineages) vs same-encoder different-seed disagreement is the interesting contrast: does
*lineage* diversity buy calibration that seed diversity does not?
**Cost:** all embeddings cached; probes are small → **10–20 min**, ~1–2 GB VRAM.
**Why fruitful/multipliable:** converts a doctrine ("two readers") into a number
(AUC/Brier), and the same harness then audits every probe in the lab (E12/E13/E15/X1/X2/X9)
for free. Directly answers the canon's #2 open item (calibration rung 3) with a cheap
proxy rung.

### ④ The mode menu: is a transmitted per-cell encoding decision worth its bits?
**Claim under test:** "a cell's encoding is a per-cell decision with its own cost, and the
decision itself is transmitted" — and, skeptically, that this beats the *pyramid*
glyphcast already specifies. No repo in the fleet implements it
(`team-lane-u-collision.md` verdict: NO).
**Source:** `research/codec-gaps-vs-glyphcast.md`, `research/team/team-lane-u-collision.md`,
`research/qpixl-ascii/README.md` (per-cell budget is a function, not a width).
**Design:** on `data/c3/real` frames (or freshly ffmpeg-rendered glyph frames), train a
~200k–2M-param tiny policy head over `{literal, delta, skip, coarse}` plus a
coarse-to-fine *pyramid* baseline and fixed 4-bit/8-bit baselines. Rate–distortion at
matched bits: reconstruction error vs transmitted bits, with the mode header charged
explicitly. Falsifier: learned menu ≤ fixed pyramid at equal bits, or the menu's gain
disappears once the header cost is paid (the qthe-codec 17-byte container lesson).
**Cost:** small CNN/MLP, few epochs on crops → **20–40 min**, < 2 GB VRAM.
**Why fruitful/multipliable:** it is the canon's own named gap and the lab already owns the
glyph corpus + tooling; a KEEP gives the lab a *new* architecture axis (per-cell mode
policy) that every future glyph predictor can inherit, and the "charge the header" control
is a reusable discipline.

### ⑤ Where the planes meet: tensor-of-planes vs graph, on frozen embeddings
**Claim under test:** readings live in intersecting planes, a shared event can be present
in one listener's units and *absent* in another's, and *"a grep finds the number but not
that two of three cells consider the event absent"* — i.e. a shared/low-rank model should
**not** explain the data as well as a union-of-planes model.
**Source:** `research/active-ledger.md`; `research/HANDOFF.md` §6.4 (open: "planes but not
where two of them meet").
**Design:** take frozen I-JEPA/DINOv2 embeddings of the staged rooms (already cached) and
K task-specific label sets (the "purposes": mood, volume, presence, plus a deliberately
orthogonal synthetic one). Compare at equal parameter budget: (a) one global probe, (b)
K independent probes, (c) a shared-subspace + per-plane-residual decomposition (low-rank +
sparse). Metric: per-plane error, plus the *absence* phenomenon — fraction of samples where
a per-plane reading is correctably "below threshold" while the global probe reports a value.
**Cost:** linear algebra + tiny probes over cached features → **< 10 min**, < 1 GB VRAM.
**Why fruitful/multipliable:** cheap, and it either builds the missing 4D-addressing
machinery the canon flags as unbuilt, or it honestly demotes the tensor claim to a graph
with labels — both are keeper results. The "absence detection" metric is new and reusable.

### ⑥ The L1 aperture: does a learned displacement beat content matching, or only look cheaper?
**Claim under test:** on a repeating texture, match-anywhere returns *a* perfect match that
is not *the* match (cost comes back ~67 points too low, "the cheap answer is wrong and it
looks right"); a codec avoids this because it transmits a *displacement*, not a search.
**Source:** `research/codec-gaps-vs-glyphcast.md`, `research/codec-gaps/delta_limit.py`.
**Design:** synthetic repeating (checker/periodic-ramp) glyph fields with **known** ground
-truth shift, plus real panning frames from the lab corpus. Compare three deltas:
positional, content-match (canon's matcher), and a *learned* estimate — either a tiny
unsupervised flow net (few 10s of k params, photometric loss, GPU) or a classical
correlation + learned disambiguation. Metric: unmatched-cell rate against the *true* moved
set, not against the matcher's own notion of match.
**Cost:** synthetic data is free; tiny flow net → **15–30 min**, < 2 GB VRAM.
**Why fruitful/multipliable:** the canon already measured the failure on CPU; the GPU
question is whether the *fix* works, which is what decides whether qpixl-ascii can be
shipped. Reusable: the same harness scores any future matcher on the four L1–L4 regimes.

### ⑦ What makes a route worth adding? Marginal information vs retrospective judgement
**Claim under test:** the canon's own named open problem: "what makes a fifth route worth
adding? Not a score — the current dial is whether a disagreement turned out to be about
something real, which is retrospective and therefore weak." Operationalize "worth adding"
as *marginal information about a held-out label set*, and test whether that ordering agrees
with the retrospective one.
**Source:** `research/anti-gan-route-diversity.md` (open problem + self-critique),
`research/route-diversity/route_diversity.py`.
**Design:** generate synthetic double-entry books with a known ground-truth defect (missing
entry, sign error, rounding); instantiate 4–6 routes (ℝ-sum, Z/2 parity, magnitude-only,
sign-only, categorical) as tiny learned checkers over the same features; compute
leave-one-route-out marginal AUC/information of each route; compare with the observed
disagreement matrix. Falsifier: disagreement frequency is uncorrelated with marginal
information (i.e. the instrument is decorative).
**Cost:** 4–6 tiny models on synthetic data → **10–20 min**, < 1 GB VRAM.
**Why fruitful/multipliable:** it closes an explicitly-open canon problem with a cheap
instrument, and the metric ("marginal information of a route") is reusable for the 12
language ports and the two separate cell-kind ecosystems the canon cites as its examples.

### ⑧ Does abstraction-agreement peak at mid temperature? *(rank last: claim needs operationalizing)*
**Claim under test:** the canon's Q4C hunch — "lower T = more conservative, higher T = more
exploratory; canon lives in the middle" — plus the measured claim that a canon-chord is
"same doctrinal position, different metaphoric framing".
**Source:** `research/2026-09-24-novel-problems-report.md` (§Problem 4, Q4A–Q4C),
`sprints/sprint-zai-001.py`.
**Design:** fixed doctrinal prompt, T ∈ {0.3, 0.5, 0.7, 0.9}, 24 samples each from local
Qwen2.5-1.5B; measure (a) surface Jaccard (should fall with T), (b) agreement of a *fixed*
frozen abstraction-labeller (e.g. a MiniLM-embedding kNN over hand-labelled abstraction
axes) — predict an inverted-U in (b).
**Cost:** ~96 short generations → **20–30 min**, ~3 GB VRAM.
**Skeptical flag:** as written, "canon lives in the middle" is **not falsifiable** — there is
no operational definition of canon-status in the source, and Q4A's "0.10–0.30 Jaccard
threshold" is an unfitted guess. Worth running only because it forces that definition into
existence; do not let it become a headline.

---

## 3. Already covered / CPU-sufficient — do not spend GPU here

- **The whole JEV-gate characterisation, the batching collapse, the KAT, the `score`
  collapse.** These are *API-call* experiments (~90 calls, seconds of compute). No GPU.
  Only the portability half (idea ①) is GPU-relevant.
- **`locality/`, `family/`.** Curvature is exact via LPs at n ≤ 70; conductance is an
  analytic/sampled bound, and the asymptotic result (torus `h = 4/n`) is already settled.
  A GPU torch eigensweep at large n would sharpen the *picture* but cannot touch the
  theorem — the canon says so itself. Low value.
- **`projects/`** — `process-signature`, `chain-lint`, `fleet-legend`, `artifact-first`,
  `quilt-widening`, `sunset-run`: all stdlib path/JSON/text analysis. The canon's own
  runners are `python3 <file>.py --self-test`.
- **`research/molt`, `research/sow`, `research/two-views`, `research/reef-spec`,
  `research/growing-pincher`, `research/active-ledger`, `research/tradeoff`,
  `research/atlas`, `research/loop`, `research/jevlab`, `research/qpixl-ascii`,
  `research/codec-gaps/delta_limit.py`.** Dependency-free Python, sub-second demos. GPU
  would add nothing (and `quantumaudio` is not installed here — the MOTH 5-scheme matrix
  cannot be re-run locally at all).
- **`research/team/team-witness-barcode.md`.** Settled as NUMEROLOGY by reading the CEH07
  primary source. It is a proof-shaped result; no compute needed.
- **Latent probes (C1–C4 in this lab).** Already run — and the C3 val AUC was audited as an
  eval bug (41/64 val clips byte-identical to train; 32/32 "real" val clips duplicated).
  Any re-run must use **group-disjoint splits** (`real_t0s()` grid collision). Do not
  re-benchmark the same number; inherit the corrected split.
- **Existing queue overlap to avoid re-inventing:** `QUEUE.md` E15/E22/E25/E26 (dial-read
  robustness), G1/G3 (local seat, quant erosion), and `SPOOL.md` E15/E22; `GEMS.md`
  wave-0/wave-5 mines. Idea ③ *extends* the E12/E15 family with a calibration metric rather
  than duplicating it; ideas ① ② ④ ⑤ ⑥ ⑦ have no counterpart in `QUEUE.md` or `SPOOL.md`.

### Claims flagged as not (yet) falsifiable
- "Canon lives in the middle" at mid temperature — no operational definition
  (`research/2026-09-24-novel-problems-report.md` Q4C).
- Reef "bleaching can destroy OR strengthen the colony" — no measured strengthening path;
  resilience is hardcoded constants (`research/reef-spec/reef.py`).
- "Measurability is the RSI-eligibility criterion" (M11) — a restatement of the gate
  finding, not a distinct prediction (`research/HANDOFF.md` §9).
- "The fleet is at the wrong end of the locality axis" — normative framing; the only
  testable half (expansion decay) is already settled.
- The JEV velocity doctrine "3 N-of-M verdict > single-model gate"
  (`research/jev-velocity.json`) — the file's own data shows `bedrock_B` first stable at
  trial **20** (0.47 → 0.59 drifting upward), so "most stable at trial 1" holds for 4/5
  questions only; the N-of-M claim was never run with N > 1 *models*.
- `research/team/team-exact-calibration` and the SOW judge-unanimity rule: real, cheap,
  and CPU/API-bound — no GPU.

---
*Read-only pass; nothing in the canon was modified. ~163 files / 2.7 MB inspected; 30+
documents read in full.*
