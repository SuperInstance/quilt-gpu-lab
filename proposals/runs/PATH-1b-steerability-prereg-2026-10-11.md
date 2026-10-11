# PATH-1b — Steerability gate for CONTINUOUS upgrades (pre-registration)

Spawned by SCOUT-106 (rc q36, 0fb9e2a): rc's closed-loop fine-granularity s-dial converges to a
FIXED-POINT orbit that is TARGET-INSENSITIVE — byte-identical traces at all five targets. q36
exposes a hole in PATH-1's G4: "RAMP endpoint == DIRECT endpoint ⇒ upgrade CONTINUOUS
unconditional" — identical endpoints could be fixed-point convergence, not knob-independence.

This prereg is COMMITTED before any PATH-1b verdict is relied upon. Commit hash pins the gates.

## Question

For the three deterministic knobs PATH-1 graded PATH-INDEPENDENT (eproc sigma, degrade_gate
tolerance, verdict_gate minimum): is the payload emitter STEERABLE at the finest censused
resolution — do distinct nearby targets produce distinct payloads — or is there a fine-resolution
plateau of the q36 FIXED-POINT shape?

determ1 eps is EXCLUDED (nondeterministic torch backend; PATH-1 SOFT class; spawn scoped ≤3 knobs).

## Targets (frozen)

Per knob, four settings: two adjacent ladder rungs + one inserted midpoint FINER than the ladder:
- eproc sigma: 0.5, 0.55 (midpoint), 0.75
- degrade_gate tolerance: 0.5, 0.625 (midpoint), 0.75
- verdict_gate minimum: 0.875, 0.895 (midpoint), 0.90

Payload emitters are PATH-1's, verbatim (pinned THRESH-2 series; same finalize/Gate calls).

## Gates (frozen in words)

- G1 ANCHOR: fresh RAMP-arm rung digests reproduce PATH-1's grade shapes — eproc 5 distinct rung
  digests; degrade 2; verdict 2 (cite PATH-1 census digest 00f2082a… committed; exact-equality
  not required for stateless emitters, count-of-distinct is the anchor).
- G2 LIVENESS: all emitters run clean (rc 0 / no exception) at every target, every knob.
- G3 STEERABILITY (per knob): at least one fine pair among {adjacent rungs, midpoint-vs-rung}
  yields a DISTINCT payload digest ⇒ steerable at finest resolution; the CONTINUOUS upgrade
  from PATH-1 G4 STANDS for that knob.
- G4 FIXED-POINT row (per knob): ALL targets byte-identical payload digest ⇒ FIXED-POINT-AT-FINE
  (q36 shape) ⇒ RED row: annotate the owning THRESH-2/PATH-1 receipt with a steerability caveat
  and BLOCK the unconditional CONTINUOUS upgrade for that knob. No re-roll, no re-tune of targets.

## Verdict

GREEN iff zero FIXED-POINT rows and G1+G2 hold. RED rows name the knob and the blocked upgrade.

## Cost

CPU only, ~5-10 min. No GPU. Tools: tools/path1b_steerability.py (refuse-overwrite --out, exit 3;
VERDICT anchor line + exit-code contract per VEXIT-1).
