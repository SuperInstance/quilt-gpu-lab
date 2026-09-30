# RT1 — What makes a route worth adding? (marginal information vs the disagreement dial)

**Pre-registered: 2026-09-29 ~21:10 AKDT, before any run fired.**
**Source canon:** `quilt-research-canons/research/anti-gan-route-diversity.md` —
its own named open problem: *"what makes a fifth route worth adding? Not a score —
the current dial is whether a disagreement turned out to be about something real,
which is retrospective and therefore weak."*
**Canon doctrine under test:** many routes to one answer make a system durable, and
*where routes disagree is the reading*.

## Operationalisation

"Worth adding" := **marginal information** — the AUC a route contributes to an ensemble,
on a held-out label, over what the other routes already carry.

- **Synthetic double-entry books** (known ground truth, no real ledger needed): 4,000 books
  × 20 entries, accounts ∈ {0..4}, signed amounts. Every book is either clean or carries
  exactly one injected defect: *missing entry*, *sign flip*, *rounding drift*,
  *misstated account*. Labels: multi-class (5) + binary (defect present).
- **Five routes**, each a *different view* of the same book, each with a tiny learned
  checker (3-layer MLP, ≤200 params, CUDA, 3 seeds averaged):
  `R1 ℝ-sum` (exact real arithmetic), `R2 Z/2 parity` (entry-count parity),
  `R3 magnitude-only`, `R4 sign-only`, `R5 categorical` (account-code distribution).
- **Metrics:**
  (a) per-route AUC; (b) ensemble AUC (logistic on route logits, grouped CV);
  (c) **leave-one-route-out marginal AUC** = AUC(ensemble) − AUC(ensemble \ route);
  (d) **disagreement rate** per route = mean pairwise label-disagreement with the others;
  (e) Spearman correlation of (c) vs (d) across routes — the retrospective dial vs the
  marginal-information dial.

## Gates (frozen)

- **G1 LEARNABLE:** best single route AUC ≥ 0.70 (the task carries signal; else INVALID).
- **G2 SPREAD:** marginal AUCs are not all equal (max − min ≥ 0.01) — the metric
  discriminates at all.
- **G3 DIAL_TRACKS:** Spearman(marginal AUC, disagreement rate) ≥ 0.5 → the cheap
  retrospective dial **is** a decent proxy for marginal information.
  Else **DIAL_DECORATIVE** — the canon's own suspicion, measured.
- Secondary (reported, not gated): does disagreement *concentrate* on real defects?
  (AUC of disagreement-as-predictor for the true defect label.)

## Honest limits

- Synthetic books with hand-designed route features: this tests the **instrument**
  (marginal information vs disagreement), not the fleet's real ledger.
- Five routes, not a route market; a G3 pass does not mean every future route is covered.
- Tiny checkers on GPU: the GPU is incidental here (the canon is CPU-solvable) — the
  point is the metric, and the same harness can host bigger learned routes later.
