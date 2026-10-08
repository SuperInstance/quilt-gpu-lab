# PARAM-1 — Gate-parameter validation census (spawned by SCOUT-76, canons 2847865)

**Pre-registered 2026-10-08 23:2x UTC (15:2x AKDT), before verdict reliance.**
Class under test (fleet: fastloop-guard confused-deputy — network-supplied threshold=0.0
inverted a similarity gate): a gate whose *parameter sourcing* can neuter or invert it.

## Frozen gates (words, pre-registered before firing)

- **G1 (coverage):** all five named instruments surveyed end-to-end for parameter sourcing:
  eproc.py (sigma/delta), determ1_lattice_snap.py (eps), verdict_gate.py (Gate bounds),
  degrade_gate.py (tolerance), exit_gate_witness.py (verdict-key/timeout/args).
- **G2 (no network params):** zero urllib/requests/http reads in any gate parameter path.
- **G3 (fail-closed defaults):** every defaulted parameter is either REQUIRED-and-refusing
  or its default is the strictest direction (cannot loosen the gate).
- **G4 (no live RED):** no booked verdict's gate accepts a parameter value that inverts or
  vacuous-fies it. LATENT holes (unused code paths) are YELLOW → named fix items, no booked
  result touched.

## Census result (fired same slice; instruments: selftests + grep call-site census)

| Instrument | Param | Sourcing | Verdict |
|---|---|---|---|
| eproc.py | sigma | keyword, REQUIRED, raises on None/<=0/non-finite | GREEN |
| eproc.py | delta | default 0.05 explicit; stricter values caller-supplied | GREEN |
| determ1_lattice_snap.py | eps | positional argv, **unvalidated** — eps<=0 → snap degenerates (div-zero at 0) | **YELLOW** |
| verdict_gate.py | Gate bounds | min/max default None; **boundless Gate passes vacuously** | **YELLOW** |
| degrade_gate.py | --tolerance | default 0.0 = strictest (any rise inverts); negative only tightens | GREEN |
| exit_gate_witness.py | verdict-key/timeout/args | CLI strings; murmur-RED + fail-loud pinned in selftest 4/4 | GREEN |

G1 PASS (5/5 surveyed). G2 PASS (grep: zero network reads in all five). G3 PASS (defaults
are REQUIRED-refuse or strictest-direction). G4 **PASS with 2 YELLOW latent holes** — all
booked `Gate(` call sites (xp_a, xp_a2, reporter_default_audit) carry explicit bounds;
DETERM-1 bookings used eps 1e-2/1e-4 explicitly. No booked result threatened.

Evidence: degrade_gate selftest 13/13; exit_gate_witness selftest 4/4; verdict_gate is a
library (no selftest — noted below).

## Spawned fix items (cheap, non-GPU)

- **PARAM-1a:** verdict_gate refuses `Gate` with both bounds None (fail-loud at construction);
  add selftest module (currently zero pins on this doctrine tool).
- **PARAM-1b:** determ1_lattice_snap validates eps > 0 finite at argv parse.

Verdict: **GREEN (no live RED)** — PARAM-1a/1b hardening queued.
