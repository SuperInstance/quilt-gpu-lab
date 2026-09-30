# ST1 — quilt-cell-v0: trained receipt-validity judgment cell

Pre-registered: 2026-09-30 ~10:58 AKDT, BEFORE any run. GPU POC per Casey 10:56
("keep using the gpu to better our systems. think about proof-of-concepts training").

## Question
Can a tiny (17-22M param) transformer fine-tuned on GPU learn to judge EXPERIMENT
RECEIPT VALIDITY — detecting programmatic corruptions of real bookings — and
ABSTAIN out-of-domain? This is the first TRAINED artifact of the self-training
engine (selftrain lane): the cell the router would route to before escalation.

Why this domain: (1) programmatic ground truth at scale — corruption ops are
known-at-generation; (2) real transfer test costs zero human labeling — corrupt
REAL results.json receipts and flag; (3) it IS the CANON cell (graders of our
own bookings) as a trained local model instead of a prompted API call.

## Design
- **Train corpus (synthetic, seeded):** receipts rendered from our real booking
  schema (verdict/mean_rel_improvement/wins/n_pairs/tau/seeds fields + prose
  line), stats drawn from plausible ranges. Corruption ops (p=0.5 applied, 1 op):
  sign flip on improvement, wins>n_pairs, verdict does not match wins ratio,
  tau moved outside pre-registered grid, missing seed line, denominator swap.
  N_train=8000, N_val_synth=1000. Seeds 6611-6615 (5 seeds, report mean/min;
  verdict from seed-MEANS). AMENDMENT (pre-fire): examples rendered in BOTH
  styles — human template AND compact JSON — because real receipts are JSON
  dumps; without the JSON half, gate 2 faces a pure distribution shift.
- **Model arm A (this run):** AMENDED PRE-FIRE: prajjwal1/bert-tiny →
  sentence-transformers/all-MiniLM-L6-v2 (22.7M) — transformers 5.17 on py3.14
  cannot instantiate bert-tiny's legacy WordPiece tokenizer (smoke-fail, fail-loud
  worked); MiniLM is same tiny class, native fast tokenizer, still within the
  17-22M param budget. seq 192, bf16 eval, batch 32, lr 3e-4, 4 epochs, AdamW,
  log-loss (=proper scoring rule, laya-aligned).
  Arm B (from-scratch 4L transformer) reserved for ST1b — do NOT run here.
- **Abstention (laya M1/M2 from birth):** max-softmax threshold calibrated on
  OOD half A at its 90th percentile; GATE 3 evaluated on held-out OOD half B
  (non-circular by construction). Gate output = clean|corrupt|abstained +
  threshold echo. Also recorded: in-domain coverage (share of real-gate rows
  confident enough to judge at all).
- **Real gate set:** every results/**/results.json in the lab (expect ≥15),
  each yielding K=4 corrupted variants (held-out corruption ops not identical
  in mix to train: swap two numbers with each other added). Honest originals
  must NOT be flagged (FPR direction matters more than TPR — a cell that cries
  corruption on honest receipts is worse than useless).

## Frozen gates (pre-registered; KILL honestly if missed)
1. SYN: held-out synthetic AUC ≥ 0.95 (below ⇒ generator/model broken, fix
   harness, never re-roll blind).
2. REAL (the KEEP gate): corrupted-real detection AUC ≥ 0.80 AND honest-receipt
   FPR ≤ 0.10.
3. ABSTAIN: ≥ 90% of OOD inputs abstained (not confidently judged).
4. FAIL-LOUD: real-receipt count < 10 ⇒ run refuses (insufficient real gate set).

## KEEP ⇒ next
Wire as local CANON pre-filter: every RESULTS.md row's receipts pass through
cell-v0 before booking; flag → human/API escalation. KILL ⇒ booked, corpus +
harness remain (training data for ST1b arms).

## Cost
GPU-only, local; all-MiniLM-L6-v2 download ~90MB from HF hub. No API spend.
