# The Relational-Correlation Primitive

*A finding from the D12/D13 arc, restated as a principle.*

## The result, precisely

The substrate falsification arc asked: can a graph of cells discover *whom to
message* — the addressing that lets them reconstruct facts no single cell can
see — and by what mechanism?

- **D12 (KEEP):** with *perfect* addressing, the relational graph reconstructs
  cross-boundary facts at 1.0 (vs isolated 0.558, traffic-permuted 0.508). The
  structure is reachable; the wiring is load-bearing.
- **D13 (KILL):** naive Hebbian reward → no convergence (concentration 0.233).
- **D13b (KILL):** confidence-weighted reward → stronger signal, still no
  convergence (0.30).
- **D13c (KILL):** REINFORCE with learned baseline → no convergence (0.217).
- **D13d (KEEP):** correlation detection — a cell finds its partner by the
  max |correlation| of atom streams over time — **identifies the true partner
  at 1.0**, with *no reward signal at all*.

Three reinforcement-learning variants plateaued at 0.2–0.3 concentration (chance
0.143); correlation hit 1.0. That is not a tuning gap. It is a category error.

## Why correlation wins

Reward-based credit assignment learns by propagating a scalar *backward* through
a sparse reward: a cell samples a receiver, gets a noisy 1/0, and must climb a
gradient where the true-partner signal (reward 1.0) is buried under the wrong-
partner coin-flip (reward 0.5 ± noise) across only ~32 updates per edge. The
signal-to-noise is structurally poor: you are trying to learn an *identity* by
repeatedly sampling a *value*.

Correlation sidesteps this entirely. Two cells that are truly related have
atoms that **co-vary**. Detecting that is O(1) shared-key discovery, not a
gradient: collect the streams, compute the covariance, read its direction.
There is no reward to propagate because there is no credit to assign — the
relationship *is* the mutual information between the two streams. A cell asks
not "who rewarded me" but "who moves with me." The latter is answered directly;
the former is answered only asymptotically.

The same noise that buries the reward signal *is* the correlation signal when
you read it pairwise instead of sequentially.

## The elephant connection

This is the same primitive as elephant's vmf room-sense. Elephant does not
reward an agent for being in a warm room; it **fits a von Mises–Fisher
distribution to the field and reads the direction** (μ̂, κ). Warmth, charisma,
pull — these are all *covariation readings*: how much does this room's state
co-move with that agent's presence. The D13d cells do exactly the same thing
one level down: fit a correlation to the atom streams and read which peer it
points at.

So the substrate's "relational intelligence" and elephant's "room temperature"
are the same verb — *compute the co-variation and read its direction* — applied
to different fields. That is not a coincidence to exploit; it is the primitive
surfacing in two independent builds, which is exactly what a real primitive does.

## The follow-up experiment (D18 — run, and it corrected the doc)

The falsifiable test was run (D18, 2026-09-27, seed 2718, pure CPU): sweep
N ∈ {8, 32, 100, 300} × p_corr ∈ {0.9, 0.75, 0.6, 0.55}, plus a REINFORCE re-run
at N=32, p_corr=0.9. Two findings, one of which retires a claim above.

**Finding 1 — correlation scales (CONFIRMED, stronger than claimed).** Partner
identification held at 1.0 on the *entire* grid, including the strict joint cell
(N=100, p_corr=0.6) and the whole p_corr=0.55 row. The doc's "crossing 0.5 near
p_corr=0.55" was pessimistic: at T=200 observations the per-decision SNR is still
~5–8σ at p_corr=0.55, and the real floor sits far lower (~0.25 by SNR math). The
primitive generalizes.

**Finding 2 — the "reward vs correlation" contrast was CONFOUNDED (FALSIFIED).**
Re-running D13c REINFORCE on *disjoint consistent partners* (not the original's
scattered per-fact partners) reaches concentration **1.0** at both N=8 and N=32 —
NOT the claimed collapse below 0.3. D13c's published 0.217 was measured with one
per-sender policy chasing ~7 conflicting targets, whose argmax metric has a
structural ceiling near ~1/7. On the *same partner-consistent ground truth* that
D13d's correlation read, REINFORCE learns the addressing at 1.0 even at N=32.

So the claim "reward is structurally poor" was wrong as stated. The real
primitive is **consistent relational target**, and correlation is the O(1) way to
*find* that target — but once the target is consistent, reward learns it too.
This does not demote correlation; it corrects *why* it wins. Correlation wins
because it *discovers the consistent target* in O(1), not because gradient credit
assignment is inherently incapable.

**What stays true:** the harness is sound (verbatim D13c reproduction = 0.217;
negative control — reward wired to a shifted partner → conc 0.0). The elephant
connection stands. The next open question is no longer "correlation vs reward"
but "how does a cell *find* a consistent target in a field where partners are
entangled, not pre-paired" — the scattered-partner regime is the honest frontier.
