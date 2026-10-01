# EST-FREEZE — results

Lane EST-FREEZE, 2026-10-01 ~15:2x–15:5x AKDT. CPU only (no GPU, no guard.py, no twins).
Prereg: `proposals/runs/EST-freeze.md` (frozen before any run). Lanes never commit.

## What this resolves

The D2 v1 blocker: two independent builds of the same prereg disagreed on the determinacy
estimator (A: reflex 1.000 / spread 0.000 / H6 0.715; B: reflex 0.469 / spread 0.50–0.52 /
H6 0.118). Here six independent estimators are run through one shared interface
`score(records, spec, est, weight, seed, nperm) -> [0,1]` on identical material
(`results/d2_build/{mini,fb}_traces.json`, 16 real + 16 sto worlds, both builds).

**Reproduced exactly (E0, different channels):**

| channel | arm | est | booked | reproduced |
|---|---|---|---|---|
| build B `salLevel`→fire (O=2) | real | E0 | 0.445 | **0.4455** |
| build B `salLevel`→fire (O=2) | sto | E0 | 0.469 | **0.4693** |
| build B `salx`→fire (O=2, "fine") | sto | E0 | 0.723 | **0.7227** |
| build B `salx`→fire | real | E0 | 0.970 | **0.9699** |
| build A `(salx, vision-window)`→fire | real | E0 | 1.000 | **1.0000** |

⇒ the two builds ran **identical estimator math**; they differed only in the **input
encoder**. Build A used the socket's declared channel (sensors.vision → reflex.orient);
build B used a lossy, undeclared projection (3-level salience). Fire|full-channel is a
pure function (E0–E3/E5 = 1.000, spread 0.000); fire|salience is not (purity 0.833).

## Estimator × test table (frozen criteria, EST-freeze.md §2–3)

`C1` exact 1.000 on synthetic atoms |O|=2..6 · `C2` seed spread · `bias@O2` = max |est−analytic truth| · `stat` = max spread across 3 input dists on a stationary-truth synthetic (pure estimator instability) · `C3` in-scope sockets ≤0.15 spread (/6) · `C4` reflex−episodic(32) range on frozen full channel.

| est | C1 atoms | C2 seed | bias@O2 | stat-spread | C3 /6 | C4 range | verdict |
|---|---|---|---|---|---|---|---|
| **E0** plug-in H (prereg formula)+MM | 1.000 ✓ | 0.000 ✓ | **0.049 ✓** | **0.065 ✓** | 0/6 ✗ | 0.648 ✓ | passes all but C3 |
| E1 excess mode-agreement | 1.000 ✓ | 5e-4 ✓ | 0.271 ✗ | 0.008 ✓ | 1/6 ✗ | 0.824 ✓ | bias fail |
| E2 effective-alphabet/coverage | 1.000 ✓ | 0.000 ✓ | 0.086 ✓ | 0.094 ✓ | 1/6 ✗ | 0.318 ✗ | C3+C4 fail |
| **E3** permutation-exact norm. MI | 1.000 ✓ | 5e-4 ✓ | **0.049 ✓** | **0.039 ✓** | 0/6 ✗ | 0.693 ✓ | passes all but C3 |
| E4 split-half TV (parity) | 0.998 ✗ | 0.000 ✓ | 0.564 ✗ | 0.239 ✗ | 2/6 ✗ | 0.136 ✗ | disqualified |
| E5 purity Wilson-LB | 1.000 ✓ | 0.000 ✓ | 0.405 ✗ | 0.195 ✗ | 2/6 ✗ | 0.788 ✓ | bias+stat fail |

## The finding (book loudly)

**FROZEN-V1 = NONE by the frozen criterion**, because **C3 is not satisfiable by any of the
six estimators** — every in-scope socket shows spread ≫ 0.15 for every estimator.

But the stationary-truth control separates the causes: on synthetic data whose true
determinacy is **identical across the three input distributions**, the best estimators
contribute ≤0.04 spread (E3 0.003–0.039, E1 ≤0.023, E0 ≤0.065). Therefore the huge real-data
spreads are **genuine socket input-distribution sensitivity, not estimator bias**. The H5
gate as written conflates the two. Consequences for v1:

1. **H6 is fine once the encoder is frozen** — reflex(1.000) − episodic(0.352) = 0.648 ≥ 0.5.
   Build B's H6 FAIL (0.118) was purely the encoder artifact.
2. **H5 must be re-derived** — its "≤0.15 across operational/uniform/degenerate" bar is
   unpassable on real sockets because their true determinacy *is* input-distribution-
   dependent. Recommended v1 revision: report per-socket spread as a **data datum** (with the
   estimator's synthetic floor subtracted), gate on the *operational* distribution, and keep
   the degenerate leg only as a named F4 diagnostic.
3. **Recommendation for v1:** adopt **E3** (permutation-exact bias-corrected normalized MI)
   as the measure — smallest stationary instability (0.000–0.039) and smallest |bias|@O2
   (≤0.049), exact 1.000 atoms, interface-identical; E0 (the incumbent prereg formula) is a
   close second. **Freeze declared encoders** (reflex = full `sal|vision-window`), which is
   the actual blocker fix. Fix the permutation seed (seed=0) so C2 is exactly 0 by construction.

## Files
- `estimators.py` — 6 estimators, one interface.
- `crossval.py` → `est_freeze_crossval.json` — build repro, C1 atoms + bias table, C2, C3, C4, det-arm.
- `analysis2.py` → `est_freeze_pass2.json` — full-channel reflex, in-scope view, stationary-truth control.
