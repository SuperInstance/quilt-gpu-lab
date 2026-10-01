# A5 parity receipt — quilt-mojo-lab wave-73 runtime #9 (CuPy) on this box

Reproduces `python/cupy_quilt.py` (runtime #9) per `docs/RUNTIME9-PREREG.md` and
the wave-73 protocol in `python/bench.py`; quilt-mojo-lab was used READ-ONLY.
Script: `a5_parity_repro.py`; receipt: `a5_parity_receipt.json`.

## Numbers (10 flow steps, inject (1,1,4.8), best-of-3, sync inside window)

| size | parity_diff | max|Δpot| | cells/s (this box) | cells/s (wave-73c) |
|---|---|---|---|---|
| 16² | 0.0 | 0.0 | 2.24M | 15.7M |
| 512² | 0.0 | 0.0 | 2.07G | 2.83G |
| 1024² | 0.0 | 0.0 | 3.06G | 3.099G |

Device: RTX 4050 Laptop 6GB, driver 616.92, WSL2; CuPy 14.2.0; python 3.14 (elephant-gpu venv).
Reference: their FlatQuilt canon; checksum 0.4000000059604645 at all sizes, matched exactly.

## Verdict vs their receipt

- Bit-parity reproduced exactly: 0.0 at 16²/512²/1024², max|Δpot| = 0.0 —
  stronger than the frozen P1 claim ("0.0 at 16², within 1e-4 at 512²").
- 1024² within 1.3% of their 3.099G; 512²/16² ran slower here (16² is launch-bound;
  a same-hour attempt caught 512² at 1.08G under poisoned clocks — throughput moves, parity doesn't).
- Honesty note on "datacenter silicon": their `docs/RESULTS.md` header records
  wave-73 on "2-core container + RTX 4050 6GB" — 4050-class, not datacenter;
  the table above is therefore 4050-vs-4050.
- INSTRUMENT-01 ramp law re-confirmed: after the 12s idle gap the 16² probe ran
  13× slow (165K cells/s); after the 0.6s sustained synced ramp, 2.2M.
- Methodology deltas, by design: (D1) deliberate 12s idle gap + pre/post-ramp probes;
  (D2) per-size probes + this JSON receipt. Kernels, gate, injection, timing window unchanged.
