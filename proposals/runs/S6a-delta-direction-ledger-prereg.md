# S6a — law vs geometry on the D-ledger (edge-mine M15 falsifier)

owner: farm
Seeded by: edge-mine Wave 7 (M15 → S6a, SPOOL Wave 6). CPU-only, <30 min.
Runner (to write): `experiments/s6a_delta_direction.py` — torch CPU + stdlib + Ollama HTTP;
subprocess list-form only (fleet red line). Receipt: `results/s6a_delta_direction.json`.

## Question (one)
A contrastive direction in embedded run-space (keep vs kill/discovery vs miss) — does it predict
held-out discovery ABOVE the physics scalars we already own? Wave 0's oldest seed finally gets a
falsifier, on the one corpus nobody else has.

## Corpus (frozen discovery rule)
All D-line receipts in `results/*.json` + RESULTS.md D-line bookings (D12h, D12i, D12j families +
earlier D-rounds). Unit of analysis: one row per (family, W, N, p, T) with label = acc ≥ 0.9.
Expected n ≈ 200–400 rows, correlated within corners — **leave-one-family-out (LOFO) is the declared
guard**. Families with <1 row per class are excluded from folds and reported.

## Arms (frozen)
- **GEOM**: embed each row's receipt fragment (params + gates + runner docstring) with local
  `nomic-embed-text` (Ollama 127.0.0.1:11434, 768-d, cosine). Train folds only:
  u = normalize(mean(keep) − mean(miss)). Held-out score: (x − grand_mean)·u. AUC per held-out family.
- **SCALAR-1**: sufficiency score T·W (the measured product law, no free parameters).
- **SCALAR-2**: T·W / Ĉ(N,p), Ĉ = per-corner median floor estimate from TRAIN folds only (1 free param).
- **CHANCE**: label-permuted GEOM, 1000 draws, same folds.

## Gates (frozen, mechanical)
- **GEOM_WINS**: mean held-out AUC(GEOM) ≥ max(AUC(SCALAR-1), AUC(SCALAR-2)) + 0.05 AND pooled
  permutation p < 0.05. → Geometry carries information the physics law does not. Big if true.
- **BASELINE_CARRIES**: AUC(GEOM) ≤ max(scalars) + 0.05. → The product law IS the whole story;
  booked negative, S6a closes. Equally informative.
- **SPLIT** otherwise → no claim, book the split. No post-hoc folds, no added features, no re-rolls.
