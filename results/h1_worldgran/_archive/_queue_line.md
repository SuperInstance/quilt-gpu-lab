
- [x] **H1-WORLDGRAN — H1 re-derived at WORLD granularity** (CPU ~1m, 0 Wh, spawned by H5-REPAIR's hand-off
  2026-10-01 17:2x): H5 proved the D2 determinacy measure is distribution-relative → re-derive H1 where the
  conditioning is explicit (n=60 paired worlds, each world's own distribution). Prereg
  proposals/runs/H1-world-granular.md (power FIRST: n=60 detectable |ρ|=0.355 two-sided / 0.318 one-sided at
  80% power; the −0.30 bar ≈ 76% power one-sided). Reuses h5_repair.py + d2_v1 traces/twins wholesale.
  — 2026-10-01 17:3x **DONE (results/h1_worldgran/, wall 59.5 s, 0 Wh).** Primary = `policy.action` (only
  H5-stable per-world measure, def-spread 0.081): **ρ_W = −0.0898 CI95 [−0.4056,+0.1838] incl 0** ⇒ **G-W1
  DEATH** → books *"No world-level relationship either — the determinacy→transfer story is dead at every
  granularity."* Variance-exists PASS (det std 0.1464, 44 distinct) — not a zero-variance artefact; the null
  is real AND floor-confounded (the measure-valid socket's transfer gap is ≈0: +0.003 ± 0.024). 6-socket ×
  world ρ is **not sign-stable**: world.surprise **+0.439 [+0.186,+0.671] (significant REVERSAL)** ·
  sensors.vision −0.325 · memory.semantic −0.466 (both would clear −0.30 but FAIL H5 stability, def-spread
  0.45/0.36) · episodic −0.190 · reflex std==0 (INCONCLUSIVE-by-construction). Post-hoc: per-world gap is
  reliably measured (between/within 2–66×, seed-mean reliability 0.86–0.99) ⇒ null ≠ gap noise. Next: give a
  measure-valid socket a real gap — H5-stable determinacy on sensors.vision, or a transfer stressor on
  policy.action; ρ ≤ −0.30 CI-excl-0 there resurrects H1, else the booking stands. Artifacts:
  results/h1_worldgran/. NOT COMMITTED.
