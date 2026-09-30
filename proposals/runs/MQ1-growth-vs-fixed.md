# MQ1 — Growth-vs-Fixed: do nets that grow into their jobs beat nets born full-size?

**Pre-registered: 2026-09-29 ~20:25 AKDT, before any run fired.**
**Thesis (Casey, 2026-09-29):** the value of quilts is *making them work* —
then optimizing, backtesting, and growing systems into their jobs on the same
hardware. MQ1 is the smallest honest test of the growth half.

## Question

At **equal final parameter count** and **equal training-step budget**, does a
net that starts small and **grafts capacity on plateau** (grown arm) reach
better held-out loss than a net born full-size (fixed arm)?

Sub-question (quilt-native): **does grafting damage the gradient fabric?**
Measured by the stochastic rational auditor (exact-fraction twins) across
every graft point.

## Protocol (frozen)

- **Task:** y = sin(x) + N(0, 0.15), x ∈ [−π, π]; 240 train / 60 held-out
  (dataset fixed at seed 42, shared by all runs; arms vary **init only**).
- **Fixed arm:** micrograd `MLP(1, [8, 8, 1])`, plain SGD, 3,000 steps.
  LR tuned on the fixed arm alone (grid {0.01, 0.05, 0.1} on train loss);
  grown arm inherits the winner — no oracle advantage.
- **Grown arm:** starts `MLP(1, [2, 2, 1])`. Every 50 steps: if relative
  val-loss improvement over the last 200 steps < 2%, graft +1 neuron to
  hidden layer 0 until it reaches width 8, then layer 1. Stops growing at
  [8, 8] — parameter parity with fixed. Same total step budget.
- **Graft init:** fresh random weights (a new cell joins as it is), lr
  unchanged. No re-warming, no surgery on existing weights.
- **Seeds:** 5 per arm (inits). Report ALL seeds — no cherry-picking.
- **Witness (amended pre-fire, 20:35 AKDT):** full-run WAL attach measured
  ~4-5× wall-clock on smoke runs — training runs under `engine.quiet()`;
  the run tape still carries a hash-chained TICK per eval plus graft
  markers (`verify()` at end), and every graft point gets a **full-fidelity
  audit-window tape** (fresh, loud, every op) that the auditor consumes.
  Spirit preserved: the chain witnesses eval-level truth; the auditor sees
  the complete graph exactly where it matters.
- **Auditor (amended pre-fire, 20:40 AKDT — calibration from smoke runs):**
  `_xapply` realizes transcendentals as float snapshots in Fractions
  (`Fraction(math.tanh(float(x)))`), so tanh-heavy nets have a transcendental
  drift FLOOR (measured 0.1–0.5 rel in smoke) that is not graft signal.
  Therefore: every run also audits 3 matched control steps (no graft); the
  gate compares **graft drift vs control drift**, not vs zero.
  GRAFT_DAMAGE only if median(graft drift) > 2 × median(control drift).
  The absolute-CI gate is retired as uninformative for tanh nets.

## Success gates (frozen before firing)

- **GROWN_WINS:** median held-out MSE(grown) < 0.95 × median MSE(fixed)
- **TIE:** within ±5%
- **FIXED_WINS:** grown worse by >5%
- Auditor gate (amended): GRAFT_DAMAGE only if median(graft drift) >
  2 × median(control drift); otherwise FABRIC_INTACT.

## Shadow replication (tensor scale — the RTX 4050)

Same protocol in torch (CUDA, elephant-gpu venv): `MLP(1, [64, 64, 1])`,
grown from [16, 16], Adam 1e-3, 4,000 steps, graft +8 neurons on the same
plateau rule, 5 seeds. Gate: does the scalar-scale verdict **replicate**
(same sign)? Replication across scale is the actual claim — rules that hold
from 100-line scalars to 4050 tensors are rules worth keeping.

## Honest limits

- 1-D toy task; sin is smooth; 5 seeds is small.
- Growth operator is the dumbest one (append + fresh init) — negative result
  here kills THIS operator, not growth itself.
- micrograd is scalar CPU — wall-clock is seconds; the shadow is where the
  GPU earns its heat.
