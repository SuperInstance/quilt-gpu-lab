# PATH-1c — horizon-probe over the FIXED-POINT-AT-FINE knobs (spawned by SCOUT-107 / rc q37)

Pre-registered BEFORE fire. Question: does widening the observation/aggregation window over
gate inputs produce distinct payload digests at fine targets, or do PATH-1b's byte-identical
bands persist (quantization confirmed)? q37 showed their target-lock was a HORIZON artifact;
our PATH-1b caveat ("consistent with payload quantization") names exactly the alternative
hypothesis this probe makes testable-in-principle.

## Scope
Knobs: the two PATH-1b FIXED-POINT-AT-FINE rows only — degrade_gate tolerance {0.5, 0.625,
0.75} and verdict_gate minimum {0.875, 0.895, 0.90}. eproc sigma excluded (already STEERABLE).
Payload emitters = PATH-1b's, verbatim (pinned inputs).

## Aggregation variants (the horizon move)
- V0 single — baseline, byte-anchor to PATH-1b.
- V1 n2x — gate input window doubled (verdict_gate: StatMeta n 32→64; degrade_gate: sweep
  entries duplicated — same marginal evidence, 2x window).
- V2 n4x — window x4 (verdict n→128; degrade sweep ×4).
Same underlying signal; only the observation window widens. If response digests stay identical
across targets under all variants, the gates are quantized, not horizon-limited.

## Gates (frozen words)
- G1 (anchor): V0 reproduces PATH-1b's digests per knob — all 3 fine targets byte-identical
  per knob, and the RAMP rung-count anchors match (degrade 2, verdict 2). G1 FAIL ⇒ premise
  void, STOP, no interpretation.
- G2: at least one variant yields >=2 distinct target digests on at least one knob ⇒
  horizon-limited ⇒ downgrade the FIXED-POINT wording on that row's receipt (AMENDMENT).
- G3: all variants identical on both knobs ⇒ quantization CONFIRMED ⇒ upgrade the PATH-1b
  caveat from "consistent with" to "evidenced by" (AMENDMENT, docs-only).
- G4: cost <= 15 min CPU, no GPU; rerun digests byte-identical (determinism pin).
Either outcome sharpens receipts; no booked verdict ever relied on fine-grained
discrimination ⇒ RED is impossible for G2/G3. VEXIT-1 contract: final `VERDICT:` line;
exit 0 GREEN (G1 pass + G2-or-G3 attained + G4 determinism) / 1 RED (G1 void or determinism
fail) / 3 refuse-overwrite.
