# The Relational Transition Kernel

*2026-09-27 — the tool the research synthesis pointed at, built and harnessed.*

## What the tool is

`tools/transition_kernel.py` — the "Transitional JEPA" primitive.

Three threads converge on it:

1. **D13d / D18** — the relational target is found by *correlation*, not
   reward; the ternary codec `{-1, 0, +1}` is the fleet's native alphabet
   (D14 timbre, D17 compression).
2. **Elephant / JEPA** — perception is a *room's* temperature sense: a field,
   not a stream; the unit is the field-*edge* (before → after).
3. **SuperInstance old→new survey** — the elephant's room-temperature sense
   and the quilt cell-ledger's transaction imbalance are the *same currency*
   (`imbalance ≡ d_mu` = field-edge delta). Perception **is** the ledger.

The kernel makes that operational: **predict the field-after a transition
from the field-before plus the acting edge's ternary correlation** — the
relational "who pulled whom" signal — with persistent per-agent identity.

## Where to harness it

- **Falsification** — `experiments/d19_transitional_jepa.py` runs it under
  the honest-ledger harness (Markov-1 floor + continuous-diff oracle +
  shuffled-correlation negative control).
- **The bridge** — the kernel is the unit that lives on the elephant↔quilt
  boundary: every cell-ledger transaction edge IS a field-edge, and every
  field-edge is a prediction the kernel can make. The fleet's perception and
  its substrate ledger become one object.
- **The loop** — whatever D19 teaches (does ternary correlation carry
  transition signal, and at what information cost?), D20 builds on it: add
  persistent-identity embeddings and the A-JEPA "action-conditioned"
  identifiability discipline from the cutting-edge sweep.

## Falsifiable claim (D19)

> Ternary correlation of the acting edge carries predictive signal for the
> next field-state, beyond Markov-1.

Measured as held-out MSE: `markov1 > jepa < oracle`, with the shuffled
negative control confirming the win is the signal, not capacity. The gap
`jepa - oracle` is the **information cost of ternarization** — how much
predictive power the 3-state codec gives up versus the continuous identity
difference. That number is the deliverable.
