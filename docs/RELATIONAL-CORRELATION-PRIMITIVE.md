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

## The follow-up experiment (falsifiable)

The D13d result is clean but small (8 cells, p_corr=0.9). The principle claims
generality. The falsifiable test:

**Does correlation-discovery scale, and where does it break?** Sweep three axes
on a single seeded harness:
1. **Scale** — N ∈ {8, 32, 100, 300} cells. Claim: identification stays ≥0.95
   at N=100 (correlation is O(N²) pairwise but O(1) per decision).
2. **Noise** — p_corr ∈ {0.9, 0.75, 0.6, 0.55}. Claim: correlation degrades
   gracefully, staying ≥0.9 at p_corr=0.6, and crossing 0.5 (chance) somewhere
   near p_corr=0.55 — i.e., the method dies *at* the information bound, not
   before it.
3. **Reward comparison** — re-run the best RL variant (D13c) at N=32, p_corr=0.9.
   Claim: reward-based concentration *collapses* with N (more receivers per
   cell → sparser reward) while correlation does not.

**The number that decides:** if correlation-discovery holds ≥0.9 at N=100 AND
p_corr=0.6, while REINFORCE falls below 0.3 at N=32, the principle generalizes —
correlation is the primitive, reward is the fallback. If correlation also
collapses at scale or under noise, then D13d was a small-N artifact and the
principle retires to "correlation helps small graphs, learning scales."

Either outcome is a finding. This is the next D-experiment (D18), pure CPU, no
model, minutes to run.
