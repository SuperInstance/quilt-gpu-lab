# TC4/TC5/TC6 — the five-face tile queue (pre-registered 2026-09-29, pushed before firing)

Follows TC1 (TIE), TC2 (RETRIEVAL_OBJECTIVE_WINS), TC3 (FRONTIER_CROSSES). Same corpus
(mine_tiles() over our real docs), same embedder (gte-small CUDA), same query=is-question,
index=is-tile-representation evaluation. Gates frozen below; no re-rolling; every arm reported.

## TC6 — the two-face split sweep (closes the trilogy)
Fixed 384-byte tile. Menu face = UTF-8-safe word-boundary truncated question+answer text, M bytes.
Meaning face = InfoNCE retrieval code (TC2/TC3 recipe: Linear(384,d)+Tanh, Adam 2e-3, 1500 ep,
temp 0.07), d = meaning_bytes/4. Splits (menu/meaning): 384/0, 288/96, 192/192, 96/288, 0/384.
Metrics: menu_top1 (embed of truncated menu vs question queries), meaning_top1, their sum.
- G1 MEANING_HOLDS: meaning_top1 at 96B meaning >= 0.85
- G2 MENU_SURVIVES: menu_top1 at 288B menu >= 0.68
- G3 TWO_FACE_WINS: sum at 96/288 >= 1.50 (pure-menu reference sum = 2 x 0.7174 = 1.4348)
Verdict: TWO_FACE if G1&G2&G3; else best split reported as measured.

## TC4 — prefix locality + the 12-bit budget (geohash idea done right, dodecet as budget)
Meaning code z (96-d, TC2 recipe). Flat k-means codebooks: 256 (8b), 4096 (12b), 16384 (14b).
Hierarchical 32-ary prefix tree depth 3 (chars = 5/10/15 bits). Metrics: CONTAINMENT = P(true
cosine top-1 tile lies in query's cell/prefix); candidate-set size; hybrid = prefix@2 candidates
reranked by z-cosine -> top-1.
- G1 DISCRETE_12B: flat 4096-cell containment >= 0.50
- G2 PREFIX: prefix@2 containment >= 0.45 AND prefix@3 containment >= 0.70
- G3 HYBRID: prefix@2 + z-rerank top-1 >= 0.85
Verdict: GREPPABLE if G2&G3; DISCRETE_VIABLE if G1&G3; else book the containment numbers.

## TC5 — rooms are priors (delta-encode promoted to semantics)
Rooms = real source groups (tile domain field). Arm R: per-room anchor (mean embedding) + PCA-24
on deltas + int8 -> reconstruct anchor+delta. Arm G (control): global PCA-24 + int8. Equal 24B/tile
payload (anchor amortized, cost booked separately). Query = question embedding.
- G1 ROOMS_ARE_REAL: R top-1 >= G top-1 + 0.02
- TIE zone: |R - G| < 0.02; else NOT_STATISTICAL.
Both arms' top-1/top-5 reported regardless of verdict.

## Ordering
Serial on the 4050: TC6 -> TC4 -> TC5. Book each to RESULTS.md with receipts
(results/tc6|tc4|tc5/*.json). Failures diagnosed, never re-rolled blind.
