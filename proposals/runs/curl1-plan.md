# CURL-1 — JEV↔JEPA curl mesh (quilt arrangement experiment)

**Status:** pre-registered, frozen before fire. Push-before-fire: this file must be committed+pushed before the run executes.
**Date:** 2026-09-30 ~21:30 AKDT. Lane: Casey 21:17 — "experiment with your quilt arrangement of different cells and how jepa and jev and others relate." Builds on 20:32 (JEV connected to a curl of state, monitor deltas on future curls).

## What this is

A six-cell quilt arrangement, run as a real mesh on real data, where the RELATION between cell types is the experiment. Not a simulation of the idea — actual typesafe JEV calls making actual routing decisions over an actual online predictor.

## The cells (quilt-record/v1 addresses)

| addr | kind | role | dials |
|---|---|---|---|
| `curl1.enc1` | perception | frame(64×64 gray) → 16×16 → seeded random projection → 64-d unit-norm latent z | seed=7, proj 256→64 |
| `curl1.jepa1` | prediction | online ridge z_t → ẑ_{t+1}; predicted CURL Δẑ = ẑ−z_t; refit every step from gated buffer | λ=1e-3, warmup 24 |
| `curl1.persist1` | baseline | zero curl: ẑ=z_t (deterministic known-answer path) | — |
| `curl1.jev1` | judgment | typesafe `jev-latest` noul per 10-step window: "is jepa adding value over persist?" | θ=0.6, ~13 calls budget |
| `curl1.router1` | pinch | 2 bad windows → PINCH jepa (route=persist, buffer frozen); 2 consecutive good → re-admit | window=10, hysteresis 2/2 |
| `curl1.led1` | receipt | every routing decision, raw JEV responses, curl traces → results/curl1/ | append-only |

Links: enc→{jepa, persist, jev, router}; jepa→jev; persist→jev; jev→router; router→jepa (gate: serving AND learning); all→led.

## Data

141 consecutive frames of hero.mp4 (data/curl1/f_0001.png…f_0141.png, 64×64 gray, extracted before this pre-reg). No sampled-pair reuse from AV1 (those aren't consecutive; curl needs t→t+1).

## The pre-registered injection (the point of the experiment)

**Broken phase: steps 81–100 (1-indexed frame numbers).** During injection, `enc1` feeds `jepa1` scrambled latents (seeded noise, seed=13) — a sick predictor cell. JEV/router does NOT know the schedule. This is the CM1 r2/r3 question ported from generation to prediction: **does JEV-gating catch a predictor that goes bad mid-stream, or does gating only cost and never help a competent cell?**

While pinched: serving routes to persist AND jepa's training buffer freezes (quarantine — a sick cell doesn't get to keep learning). Pre-registered here.

## Metrics

Per step t (post-warmup): e_jepa = 1−cos(ẑ, z_{t+1}), e_persist = 1−cos(z_t, z_{t+1}).
- hit-rate = frac(e_jepa < e_persist) on CLEAN steps (post-warmup, non-injection)
- routed error = mesh's actual serving error (routed path per router state)
- JEV agreement = frac(JEV verdict sign matches local arithmetic sign) per window
- curl trace = per-window mean errors, both cells (the "deltas on future curls" monitor)

## Frozen hypotheses & verdict bars

- **H1 (jepa learns the curl):** clean hit-rate ≥ 0.55 → KEEP else KILL.
- **H2 (gating is free when competent):** routed mean error ≤ always-jepa mean error over full post-warmup span (incl. broken phase) → KEEP else KILL.
- **H3 (gate catches the sick cell):** (a) pinch fires during steps 81–100 or within 1 window after onset, AND routed error in 81–100 ≤ 1.1 × persist error over same span; (b) re-admission ≤ 2 windows after heal (step 101+) → KEEP else KILL.

Honest predictions (pre-data): H1 ~0.65 (hero.mp4 has real motion; ridge on random-projection latents should beat zero-curl), H3a likely KEEP (a sick cell's errors are enormous), H2 is the genuinely uncertain one — if JEV is slow to react, routed ≈ always-jepa, not better.

## Controls & receipts

- Ablations computed in-run, no extra JEV calls: always-persist (floor), always-jepa (ungated).
- JEV budget: ≤ 16 calls total (11 windows + smoke + spares); raw responses stored, not paraphrased.
- Everything seeds fixed: enc=7, injection=13. No rerolling: one run, verdicts as they land.
- Results → results/curl1/curl1-results.json + curl1-trace.png + cells.csv/links.csv (the arrangement as a portable quilt record). RESULTS.md entry after verdicts.
