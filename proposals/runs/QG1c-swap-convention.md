# QG1c — swap/wire-order convention: corrected census (2026-09-30, pre-registered)

## Question
QG1-residual (BOOKED 2026-09-30; verdict NAME) localized the 28/1920 anchor misses to
swap/wire-order semantics: on the booking machinery (pi-units, which reproduces the booked
1892/1920 bit-exactly), the failing set enriches on **swap** (Fisher 7.0e-19, n=442) and
secondarily **x** (8.6e-5); every other flag is clean. Which candidate convention, applied to
the census machinery, restores the anchor to >= 0.99?

## Candidate conventions (FROZEN set, evaluated exhaustively in one pass)
- **C0** current: embed1 MSB (q0 = leftmost kron factor); swap = XOR-map on pairs [(a,b),(b,a)];
  cx = [(c,t)]; gates applied in listed order.
- **C1** wire reversal, single-qubit only: q -> 2-q in embed1.
- **C2** wire reversal, multi-qubit indices only: control/target q -> 2-q in perm + crx select.
- **C3** C1 + C2.
- **C4** C0 with the gate list applied in REVERSE order.
- **C5** C0 with "swap" expanded as a SINGLE XOR pair [(a,b)] (i.e. evaluated as CNOT).

No candidate may be added after firing; a widened search is a new pre-registration.

## Machine (frozen)
Machinery imported from experiments/qg1_residual.py (main-guarded, safe to import; booking
machinery = pi-units gate2 + census embed1/perm XOR-map), with candidates as parameterized
variants of the index mapping / pair expansion / application order. Corpus: micromoth-quilt
`receipts/exp022-desert-break/exp022.telemetry.{k3..k7}.jsonl` (read-only), 960 cells x
{train_p, verify_p} = 1920 pairs. Per candidate: exact balance per unique genome (batched GPU
matmul), anchor := fraction of the 1920 pairs within |exact - recorded| <= 0.044; report failing
count + Fisher enrichment of its failing set for all 7 flags.

## Gates (frozen)
- **G-FIX**: some candidate reaches anchor >= 0.99 AND its failing set has no flag enriched at
  Fisher p < 0.001 => verdict **FIXED**: the convention is NAMED (that candidate); corrected
  census booked.
- **G-PARTIAL**: best candidate improves the anchor by >= 0.02 but does not reach 0.99, or
  reaches 0.99 with residual enrichment => verdict **PARTIAL**: improvement named + remaining
  misses decomposed.
- **G-NONE**: no candidate moves the anchor beyond C0 => verdict **NONE**: the mismatch is deeper
  than the frozen set (report best candidate + decomposition).

## Swap-vs-x decomposition (mandatory output)
For the C0 (booking-machinery) 28 misses: joint census {swap present} x {x present}; per-subset
anchor under each candidate. Separates the primary (swap) from the secondary (x) convention.

## Discipline
Analysis-only; no new data; corpus read-only; keys never echoed; no post-hoc candidate expansion;
no retry loops. Fire-time pins (runner sha256, this pre-reg sha256, 5 telemetry sha256s) captured
in the RESULTS entry.
