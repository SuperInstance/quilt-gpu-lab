# quilt-jepa R3L saturation probe — the receipt (2026-09-28)

*Lane note: two flash lanes died on rate limits; the main session ran the probe (clone + code read + diagnosis).*

## The question (edge-scout docket #4)
quilt-jepa's R3L anomaly-strength ladder saturates **bit-exactly** at amplitudes ≥0.9 ("z(1.2) == z(0.9) bit-exact (clamp plateau)" — verdict-v5.md). Characterize: structural or float-emergent (register precision)?

## The answer: STRUCTURAL — an explicit semantic clamp, not numerics.

**The smoking gun** — `probe5.mjs` line 153 (the anomaly injection):
```js
obsNew[(py + dy) * GRID + px + dx] = Math.min(1, obsNew[(py + dy) * GRID + px + dx] + amp);
```
The observation buffer is hard-clamped at **1.0**. Any amplitude that pushes a cell past 1.0 saturates it to exactly 1.0 — so injected frames at amp=1.2 are *pixel-identical* to amp=0.9 wherever cells were ≥ −0.1 (nearly everywhere on the injection path). All downstream statistics (z-concentration, raw ratio, MAD ratio — probe5.mjs lines 220-222 even *assert* the bit-exactness as their "saturation receipt") inherit the identity trivially.

**Diagnosis:** by-construction, documented-in-repo behavior — their verdict frames it as *refuting their own "widen-by-amplitude" lever* (you cannot buy more anomaly margin past the observation floor). The edge scout's "register precision" reading was a misread: no float phenomena involved; a JS `Math.min` on the world model's observation channel.

**Implications for the fleet:**
1. No fix needed — the clamp is the model's semantics (observations are bounded in [0,1]); "unclamping" would change the world model, not a bug.
2. If quilt-jepa ever wants a wider anomaly margin, the lever is *observation resolution* (sub-1.0 amplitude spacing, or a log-scaled observation channel), not amplitude.
3. Docket #4 closed: characterized, structural, one paragraph, $0.

*Probe cost: one clone (depth-1), one code read. The dtype sweep (fp64/int8 etc.) was unnecessary once the clamp was found — JS numbers are all fp64 and the identity happens before any accumulation.*
