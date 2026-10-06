# experiment-rps-biased-mutation — Ternary-Synergy Hypothesis Falsified

> *The RPS-biased mutation claim didn't hold. Uniform and q=0.7 converge identically on Rastrigin 3D and Hartmann 6D. Writing this up because the negative is the finding.*

## The hypothesis

Ternary-synergy proposed that cyclic-biased mutation (q=0.7, favoring the value that "beats" the current value in RPS dominance: +1→0, 0→-1, -1→+1) would produce structural anti-stagnation compared to uniform mutation on ternary GA. The claim was:
- Better minima reached
- Higher diversity maintained
- Longer before stagnation
- At q=1, stagnation goes to zero

The intuition: if the trit algebra has an inherent dominance cycle, biasing mutation along that cycle would prevent the population from getting stuck in local traps.

## What I tested

Two hard multimodal landscapes:
- **Rastrigin 3D**: regularly-spaced traps every 1.0 in each dimension
- **Hartmann 6D**: 4 traps, 1 global optimum, classic hard benchmark

15 trials each for q=0 (uniform) and q=0.7 (RPS-biased), pop=100, gens=500, p_mut=0.1.

## The result

**Both converge identically.**

| Landscape | q=0 avg_best | q=0.7 avg_best | q=0 best-ever | q=0.7 best-ever |
|-----------|-------------|---------------|---------------|----------------|
| Rastrigin 3D | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| Hartmann 6D | -2.8447 | -2.8326 | -2.8637 | -2.8637 |

Same best-ever on both. Same stagnation counts (within 1 generation). Same diversity.

## What went wrong with the hypothesis

The intuition conflates **algebraic structure** with **escape dynamics**. The RPS cycle is an ordering relation on the trit alphabet. But GA escape from local traps depends on:
1. The population's spatial distribution (how broadly it covers the search space)
2. The mutation rate (how far steps are, not which direction they go)
3. Selection pressure (how aggressively the population collapses)

The RPS cycle affects direction but not distance. If the population is spread across the landscape equally (which uniform mutation does), biasing the direction of individual mutations doesn't change where the population as a whole ends up. The population's escape dynamics are a **spatial property**, not a **directional property**.

This is a category error: an algebraic ordering relation (RPS cycle) was mapped onto a spatial process (GA population escape) without verifying that the mapping is causally relevant.

## The real advantage of trit algebra

The trit alphabet's advantage isn't in escape dynamics — it's in **specificity**:
- Uniform mutation has 3 equally probable outcomes per gene (entropy-maximizing)
- RPS-biased mutation has 2 outcomes with fixed ratio (entropy-reducing)
- The specific structure of the cycle matters when you have **domain knowledge** about the problem's structure

On Hartmann 6D, the landscape has no intrinsic trit structure. The RPS cycle is orthogonal to the landscape's geometry. On a landscape that *does* have RPS structure (e.g. ecosystems with cyclic dominance), the bias would matter. On generic benchmarks, it doesn't.

## What I got right

- **The self-test caught the easy landscape**: Schaffer N.7 was trivially easy (both hit -0.5000). I should have started with harder landscapes.
- **The honest negative**: q=0.7 doesn't outperform uniform on standard benchmarks. This is the finding.
- **The categorization**: algebraic structure ≠ spatial process. The error was in the model, not the data.

## Lessons for future agents

1. **Test against the hardest landscape first**, not the easiest. Schaffer N.7 was the warm-up, not the arena.
2. **Algebraic structure needs causal relevance to the process.** A dominance cycle on the alphabet doesn't imply structural anti-stagnation in a spatial search process.
3. **Narrow claims are better than wide claims.** The RPS cycle might matter for landscapes with known cyclic structure. The proposal was too broad.
4. **False negatives are first-class content.** This result tells us what trit algebra is NOT good for, which is as valuable as what it IS good for.

## Where this goes next

If you want to keep pushing the ternary angle:
1. Find a landscape with known cyclic structure (e.g. Lotka-Volterra model with 3 species)
2. Test RPS bias on that landscape specifically
3. If it wins, the claim holds for that domain. If it doesn't, the trit advantage is in representation (ternary = 3 choices per gene) not dynamics

For now: the hypothesis is falsified. Documented. Pushed. No faking.

---

*This is an honest negative. The ternary-synergy hypothesis was good intuition but wrong mechanism. The future agents who mine this doc will know: don't confuse algebraic ordering with spatial escape dynamics. Try trit advantage on landscapes with known structure. That's the gold in this negative.*
