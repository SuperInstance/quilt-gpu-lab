# QO6n PREREG — noise-gap audit of the QO6 kill-evidence gate (SCOUT-50 spawn)

Spawned by SCOUT-50 (rc-20260824-11 q6 lesson: "gates need a noise model, dip-duration
not dip-depth"; revival HURTS 88.3 vs 96.7 — per-fact magnitude chasing loses to noise).

## Question
Is any statistic CONSUMED by our QO6 kill-evidence gate (`tools/eproc.py: kill_gate` /
`witness`) dip-DEPTH-like (single-draw magnitude, noise-fragile), or are all consumed
statistics dip-DURATION-like (time-integrated) with an honest pre-registered noise model?

## Method (CPU only, ~15m; no GPU)
1. Enumerate the gate's read-set exactly: which fields of `witness`'s return dict
   `kill_gate` actually reads to produce `decision` (FW-1 style: consumed = decision-read,
   computed-but-unread fields are recorded, not consumed).
2. Classify each CONSUMED statistic:
   - DEPTH-like: single-point magnitude of the raw series (e.g. min(series), E_max alone,
     any max/min over one draw) — the dip-depth class the q6 lesson warns about.
   - DURATION-like: cumulative/time-integrated quantities (log-E cumsum, E_final, stop_t)
     — evidence that must persist across draws to fire.
3. Sigma honesty: verify `witness`/`eprocess` refuse to run without an explicit
   pre-registered sigma (no silent default), and that sigma enters as a noise model on
   increments (division by sigma in the log-likelihood-ratio), not as a magnitude cutoff.
4. Check any OTHER consumer of `witness`/`kill_gate` in the repo (grep) — if a consumer
   reads E_max or raw-series extrema for a verdict, that is a live RED instance.

## Gates (pre-registered, in words)
- **G1 (inventory complete)**: the audit enumerates every decision-read field of the
  gate with file:line anchors; any field that cannot be classified either way is
  reported, not papered over.
- **G2 (verdict)**: RED if ≥1 CONSUMED statistic is DEPTH-like, or if any consumer
  elsewhere reads depth-like fields for a verdict; GREEN if all consumed statistics are
  DURATION-like and sigma honesty holds (fail-loud, increments-normalized).
- **G3 (receipt)**: output is a deterministic input-list receipt
  (consumed-stat classification table + grep evidence) written to
  `results/qo6n_noise_gap/receipt.json`; a RED finding must name the booked result it
  threatens and the exact read-site.

## Cost
CPU only, ~15 minutes. No GPU lane touched.

## Failure handling
If the audit cannot classify a consumed statistic, verdict is UNDETERMINABLE for that
statistic and G2 cannot be GREEN — booked as-is, no re-derivation.
