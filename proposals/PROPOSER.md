# PROPOSER — the mutation-proposal organ (v0)

*Part of the RSI loop: ledger → propose → review-gate → fire → verdict → ledger.*

## Role in the loop

Today's arc (D1→D3, G1→G4) proved the loop's *evaluation* half: one variable per
mutation, pre-registered gates, honest KILLs, paired replication before stacking.
What was missing is the *proposal* half — mutations so far were proposed by
whatever was in Casey's or the main agent's head at fire time. This organ makes
proposing a **retrieval-and-reason step over the ledger itself**:

```
training/mutations.json   the memory (one record per mutation, verdicts + costs + lessons)
GEMS.md                   the mined abstractions (candidate fuel, with fire-status)
proposals/propose.py      the deterministic scorer (this spec, executable)
        ↓
proposals/proposals-YYYY-MM-DD.json   ranked candidates + pre-registered gates
        ↓
HUMAN REVIEW  ← nothing self-proposed fires without this (the acceptance discipline)
        ↓
RESULTS.md + gem-hits.md  verdicts flow back; the next proposal cycle reads them
```

## v0 discipline (what makes this an honest organ, not a slot machine)

1. **Deterministic.** `propose.py` is stdlib-only Python, no LLM inside. Same
   inputs → same proposals, byte-identical. The *reasoning* lives in the
   candidate spec (each candidate's mutation line, receipts, gem links, and
   falsifiability are authored and reviewed); the *scoring* is arithmetic.
2. **Pre-registered gates.** Every emitted candidate carries KEEP/KILL thresholds
   **before** any code exists (the SPOOL convention). A proposal without a gate
   is not a proposal.
3. **Fixed budget.** Every gate states its budget cap. Gains must be at equal
   budget — the WECO/AIDE² condition that made ~90% of their proposals *honest
   rejections* instead of reward hacks. Expect most proposals to die; the
   archive of dead proposals is data (WECO read all 95 of theirs).
4. **The queue precedes proposals.** QUEUED ledger records (D4, G5) consume their
   IDs and fire first. Candidates that duplicate a queued mutation are
   **suppressed** (listed in the output as suppressed, with the reason); candidates
   that *overlap* a queued mutation (extend rather than duplicate) take a 0.8
   penalty so the loop explores outward, not in circles.
5. **Private-ish eval.** Gates are written against held-out/changed-cell/second-seed
   readings the trainer cannot game (the WECO public/private split, at our scale:
   paired arms + replication before KEEP is believed).

## Scoring rule (v0)

For each candidate:

- **past-outcome similarity** = mean over its ledger refs of
  `outcome_base × polarity`, where

  | verdict | base |
  |---|---|
  | KEEP, REPLICATED | +1.0 |
  | INCONCLUSIVE | +0.25 |
  | QUEUED | 0.0 |
  | KILL | −1.0 |
  | KILL with `diagnostic_validated: true` | +0.5 (the gate died, the lesson lives — G4) |

  `polarity` is +1 when the candidate *builds on* the receipt's mechanism,
  −1 when it deliberately *avoids repeating* the killed form.

- **gem-synergy** = mean over the candidate's gem links of
  `synergy × status_multiplier(GEMS.md status)`: SEEDED 1.0 (unfired fuel),
  ASSAYED 0.75, MINED 0.6, FIRED 0.5 (credit taken), missing 0.5.
  × 0.8 if `queued_overlap`.

- **falsifiability** = authored 0–1: crisp numeric gate + control arm + one-run
  cheapness all push it up; gates needing new infrastructure push it down.

**score = past × gem × falsifiability** (product — a candidate weak on any axis
cannot ride the others).

Output: per domain (bpb, glyph), the ranked top 3, IDs assigned in order
(next free ID = highest prior ID + 1; today that is **D5** for bpb, **G6** for
glyph — D4/G5 belong to the queue).

## What v1 adds (deliberately not in v0)

- An LLM *candidate-writer* that reads RESULTS.md weekly and emits new candidate
  specs into the same scorer (the scorer/harness stays deterministic — that is
  the WECO lesson: selection pressure, not generation, is where the honesty lives).
- gem-hits.md feedback: candidates linked to gems whose fired experiments KEEPed
  get a small multiplier; gems that only KILLed decay. (The hook is written in
  gem-hits.md; v0 reads statuses only.)
- An ignition probe (WECO L2): score the proposer by its *descendants* — did the
  proposals it emitted produce KEEPs — not by its own output quality.

## Limits (stated honestly)

v0's candidate pool is hand-authored by the agent that built it — so today the
*generation* is not yet self-generated; the *selection and gating* are. The loop
closes when verdicts from fired proposals are appended to the ledger and the next
cycle's scores visibly move. That loop-back is the next commit, not this one.
