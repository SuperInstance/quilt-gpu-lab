# H1-WORLDGRAN — RESULTS (lane H1-WORLDGRAN, 2026-10-01 17:3x AKDT)

Prereg: `proposals/runs/H1-world-granular.md` (frozen before fire). **CPU-only, 0 Wh, no GPU** (no
guard/watt receipt required). Reuses byte-for-byte `results/d2_v1/d2_v1_traces.json` +
`results/d2_v1/d2_v1_twins_result.json` and the H5-REPAIR estimator (`h5_repair.py`: `det_E3`,
`encode_pair`, SEED 2718, NPERM 120). Wall **59.5 s**. Script `results/h1_worldgran/h1_worldgran.py`.

## The booked question
H5-REPAIR closed with: *"H1 should be re-derived at **world granularity** (60 points) where conditioning
is explicit and the distribution is the world's own."* H1 (corpus-level) was
ρ(per-socket determinacy, per-socket transfer gap) = **−0.371 [−0.600, 0.486]** over n=6 sockets.
Question here: **within a fixed socket, do worlds with higher determinacy transfer better?** — the world's
own empirical distribution *is* the conditioning, so H5's distribution-relativity objection cannot bite.

## 0. Power analysis — reported BEFORE testing (bar justification)
n = 60, Fisher-z (se = 1/√57): **detectable |ρ| = 0.355 (two-sided α=0.05, 80% power) · 0.318
(one-sided — the correct directional test here).** Power *at* the mission bar ρ = −0.30:
**0.756 one-sided / 0.647 two-sided.** → the mission bar **−0.30 sits 0.018 below the one-sided 80%-power
bar**; it is pre-registered as the effect-size gate (task-specified) with the power-bar reading also
reported. No bar movement after seeing ρ.

## 1. PRIMARY — `policy.action` (the ONLY socket whose per-world measure is H5-stable)

`D(w)` = H5-R3 paired-world Δ-determinacy computed **within** world w (E3, operational weight, nperm=120,
seed 2718+w); `G(w)` = booked twin transfer delta = mean over 3 seeds of `nerr_sim − nerr_real` on world w;
both over the **60 held-out worlds** (i = 140..199), out-of-sample.

- **ρ_W = −0.0898, bootstrap 95% CI [−0.4056, +0.1838]** (B=1000 world-resamples, tie-corrected Spearman).
  **CI includes 0.** |ρ| = 0.09 ≪ any bar. Weight-robust-but-null: operational −0.0898 · uniform −0.0594 ·
  degenerate **+0.0167** (sign not even stable across definitions, though all ≈0).
- **Variance-exists check: PASS** — per-world determinacy has real variance (std **0.1464**, 44 distinct
  values, range 0.637, min 0.363, max 1.000). The null is **not** a zero-variance artefact.
- **Mechanism (decisive):** on the one socket whose per-world determinacy is measurable, the **transfer gap
  is itself ≈ 0** — `G` mean **+0.0030**, std **0.0236**, range 0.206 across 60 worlds. There is essentially
  no sim→real transfer penalty on `policy.action` to explain. So the H5 hand-off has a **built-in tension**:
  *measure-validity* (R3 stabilizes only here, def-spread 0.081) and *gap-magnitude* (largest gaps live on
  the measure-unstable sockets) sit on **different** sockets.

## 2. 6-socket × world-level ρ table (exploratory except the primary)

| socket | H5 R3 def-spread (stability) | per-world det std | **ρ_W (op/uni/deg)** | CI95 | CI excl 0 | gap mean±std |
|---|---|---|---|---|---|---|
| reflex.orient | 0.000 (std==0) | **0.0000** | 0.000 / 0.000 / 0.000 | [0,0] | – | −0.017 ± 0.129 |
| world.surprise | 0.663 ✗ | 0.2237 | **+0.439** / +0.413 / +0.248 | [+0.186, +0.671] | **YES (+)** | −0.013 ± 0.191 |
| sensors.vision | 0.450 ✗ | 0.2107 | **−0.325** / −0.426 / −0.279 | [−0.580, −0.057] | YES (−) | +0.062 ± 0.219 |
| **policy.action** | **0.081 ✓** | 0.1464 | **−0.090** / −0.059 / +0.017 | [−0.406, +0.184] | **no** | +0.003 ± 0.024 |
| memory.semantic | 0.355 ✗ | 0.3182 | **−0.466** / −0.463 / −0.445 | [−0.676, −0.231] | YES (−) | +0.008 ± 0.086 |
| memory.episodic | 0.151 ✗ | 0.3924 | −0.190 / +0.005 / −0.168 | [−0.433, +0.060] | no | +0.000 ± 0.085 |

**Headline: the world-level relationship is not sign-stable across sockets.** One socket is significantly
**POSITIVE** (`world.surprise`, +0.44 — the H1 direction *reverses*), two are significantly negative but
on **measure-unstable** sockets (`sensors.vision` −0.325, `memory.semantic` −0.466 — both would clear the
−0.30 bar, but both fail the H5 stability gate, def-spread 0.45/0.36), one is **zero-variance by
construction** (`reflex.orient`, det ≡ 1.000 in all 60 worlds — the reflex target is a pure function of the
input channel, so a world-level correlation can never exist there), and the **one measure-valid** socket
(`policy.action`) is **null**. No single world-level law.

## 3. POST-HOC descriptive (not gate-affecting) — is the per-world GAP itself trustworthy?

The mirror of H5's decompose-the-measure move, on the y-axis: variance of the per-world gap **between**
worlds vs **within** world across the 3 seeds (seed-mean reliability = between/(between+within/3)):

| socket | gap between-world var | within-world (seed) var | ratio | seed-mean reliability |
|---|---|---|---|---|
| reflex.orient | 0.01665 | 0.00025 | 66.5× | 0.995 |
| world.surprise | 0.03660 | 0.01510 | 2.42× | 0.879 |
| sensors.vision | 0.04773 | 0.01402 | 3.40× | 0.911 |
| policy.action | 0.00055 | 0.00027 | 2.09× | 0.863 |
| memory.semantic | 0.00736 | 0.00238 | 3.09× | 0.903 |
| memory.episodic | 0.00728 | 0.00276 | 2.63× | 0.888 |

**The per-world gap is reliably measured** (between/within 2–3×; seed-mean reliability ≈ 0.86–0.91), so the
primary null is **not** gap-measurement noise. It is real on `policy.action` — and it is *confounded by the
near-zero gap there* (§1 mechanism). The confound is a property of the design, not of the statistic.

## 4. VERDICT (frozen tree, G-W1)

Primary: ρ_W = −0.0898 with CI **[−0.4056, +0.1838] incl 0**, |ρ| < 0.30, det std 0.1464 ≠ 0 (not
INCONCLUSIVE). Power-bar reading also not met. → **G-W1 = DEATH**. Booked sentence:

> **"No world-level relationship either — the determinacy→transfer story is dead at every granularity."**

Continuity: the corpus-level ρ (−0.371) and H5's R3 corpus ρ (−0.257) do not lift to per-world signal on the
measure-valid socket; across sockets the sign is not even consistent (one significant **+**), so the original
H1 is not a world-level law.

**Honest caveats recorded (do NOT resurrect the thesis on these):** (a) the two exploratory sockets that
clear −0.30 (`sensors.vision`, `memory.semantic`) use per-world scalars that **fail the H5 stability
gate** — chasing them means chasing an un-repaired measure; (b) `world.surprise` shows a *significant
reversal*, i.e. the world-level sign is socket-dependent; (c) the measure-valid socket has a ~zero gap, so
its null is partly a **floor artefact** — this lane therefore cannot fully separate "no relationship" from
"no room for a relationship".

## 5. Repro / artifacts
`results/h1_worldgran/{h1_worldgran.py, h1_worldgran_result.json, h1_worldgran_run.out, RESULTS-ENTRY.md}`.
Prereg `proposals/runs/H1-world-granular.md`. CPU-only 0 Wh, wall 59.5 s, no GPU. **NOT COMMITTED.**

## 6. Next question
The y-axis is the weak leg: the measure-valid socket is precisely the one with **no transfer gap**, so H1-W
cannot be tested where H1 is testable. Next: **give a measure-valid socket a real gap** — either (i) build a
per-world determinacy measure that is H5-stable on `sensors.vision` (the only socket with both large gap
+0.062 ± 0.219 *and* a significant −0.33 signal), or (ii) engineer a transfer stressor on `policy.action`
(where the measure IS stable) by widening the sim→real distribution shift until `G` leaves the floor.
Testable prediction: if determinacy buys transfer, ρ on vision (or on stressed action) should be ≤ −0.30
with CI excluding 0 — otherwise the "dead at every granularity" booking stands.
