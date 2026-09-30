# QG1-residual — localize the 28/1920 anchor misses (2026-09-30, pre-registered)

## Question
The QG1 exact census (proposals/runs/QG1-exact-census.md, results/qg1_exact_census/) anchored at
1892/1920 = 0.9854, below the pre-registered ≥0.99 bar: 28 recorded values miss the exact balance
min(|s000|²,|s111|²) by more than ±0.044. Two live hypotheses:
(a) **noise tail** — exp022 recorded at 512 shots; ±0.044 is the 95% CI half-width at p=0.5, so a 99%-within-2σ
    bar is internally inconsistent for binomial noise (2σ ⇒ ~95%, not 99%); the 28 are the expected tail;
(b) **missing convention** — a gate-combo subpopulation (e.g. crx semantics, angle units, wire order) deviates
    systematically and the census readout is wrong for it.
This run decides CLOSE vs NAME. It does not fix any simulator.

## Method (frozen before run)
Analysis-only re-read of the SAME corpus
(/home/eileen/projects/micromoth-quilt/receipts/exp022-desert-break/exp022.telemetry.{k3..k7}.jsonl —
the corpus lives in micromoth-quilt; read-only consumption, exactly the path experiments/qg1_exact_census.py
already loads,
960 cells × {train_p, verify_p} = 1920 pairs). Statevector machinery copied verbatim from
experiments/qg1_exact_census.py (balance=min(p000,p111), pi-unit half-angle, q0=MSB, complex128, CUDA batched
unitary chain — GPU only for that matmul). Per pair:
- dev = recorded − exact_bal; fail := |dev| > 0.044 (same threshold as the census).
- k = round(recorded·512) recovers the shot count; exact two-sided binomial p-value of the pair under
  p0 = exact_bal, n = 512 (lgamma pmf, no scipy).
- CENSUS (mandatory output, descriptive): full failing table (stream, gen, observable, recorded, exact, dev,
  gate-name multiset, per-gate presence flags, rx/rz/crx angle values) + signed mean dev of failures.
- ENRICHMENT: Fisher exact (2×2, failing×flag) per gate flag {h,x,rx,rz,crx,cx,swap}; flags present in all or
  no genomes are reported n/a. Threshold per flag p < 0.001.
- CALIBRATION: Benjamini–Hochberg over all 1920 pair p-values at q = 0.01; count rejections.
- RE-BAND (the self-consistent 99% anchor): per-pair band ±2.5758·sqrt(p0(1−p0)/512); report fraction within.

## Gates (frozen)
- G-LOCALIZE (descriptive, must print): the failing table + enrichment table. No pass/fail.
- G-CLOSE: BH rejections == 0 AND no gate flag enriches at Fisher p < 0.001 AND re-band fraction ≥ 0.99
  → verdict **CLOSE**: residual is 512-shot noise; the original bar (99% within the 95% half-width) was
  internally inconsistent; anchor stands corrected at the self-consistent 99% band. No convention missing.
- G-NAME: otherwise → verdict **NAME**: the convention is owed to the strongest-enriching gate flag; the census
  readout is wrong for genomes carrying it. No fix, no re-roll in this run — a corrected census would be a new
  pre-registration.

## Discipline
No new data, no re-rolls, telemetry read-only, keys never echoed. Fire-time pins captured in the RESULTS entry.
Honest prior note: 28 observed is BELOW the ~96 Gaussian expectation at 2σ/1920, and 28 < at-risk-population
binomial expectation — the noise hypothesis was already favored at census time; this run is the pre-registered
arbitration, not a retrofit.
