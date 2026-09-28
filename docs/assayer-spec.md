# The Assayer — the reusable spec that turns abstractions into gated gems

*Breakthrough-finder station 2. Version 1 (2026-09-28). Run as a flash lane whenever the ledger gains MINED entries.*

## Input
- `GEMS.md` entries with status MINED (or a fresh scout's abstraction list passed inline).
- The asset inventory: `RESULTS.md` (every receipt is an asset), the training corpora (`training/`), the methods (falsifier discipline, FAIL-first, pre-registered gates), the repos (chiaroscuro-embedding's renderer, the nursery skeleton, quilt-jepa, pincher/lever-runner).

## Process (per abstraction)
1. **Name the essence** in one line (what it replaces or unifies — not the result).
2. **Cross-reference the assets**: which receipt/corpus/method does it multiply? Be specific (cite the experiment ID or file).
3. **Score** three axes, each 1-5:
   - *novelty*: how new to the field (5 = the field hasn't tried it, 3 = emerging, 1 = settled)
   - *local-uniqueness*: why OUR position answers it cheaply (5 = only a free-iteration 6GB GPU + our private corpora can, 1 = anyone with an API key can)
   - *falsifiability*: can a pre-registered gate decide it in ≤1 day on the 4050? (5 = hours and clean, 1 = weeks or muddy)
4. **Gem-potential = novelty × local-uniqueness × falsifiability** (product, not average — a 1 anywhere kills it).
5. Score ≥ 27 → draft the **gem-question** (one falsifiable sentence) + the gate (KEEP iff / KILL iff) + rough cost. Update GEMS.md: MINED → ASSAYED (or SEEDED once the SPOOL entry exists).

## Output contract
- Updated `GEMS.md` rows (pathspec-scoped commit).
- For SEEDED items: the SPOOL-entry text in the established format (## ID — title / Q / claim / gate / feasibility), appended to SPOOL.md's next wave.
- Never loosen a gate to make something pass. The falsifier discipline outranks the gem-hunger.

## Self-check (the assayer grades itself)
After each run: how many MINED→ASSAYED, how many ≥27, and one line on whether the scoring rubric needs recalibration (e.g., everything scoring 27+ = the novelty axis is inflated).
