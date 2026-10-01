# C1-PLAYTEST — PRE-REGISTRATION (written before any measured match)

- lane: **C1-PLAYTEST** (worklist item `C1 · The Local Playtester`, PoC scope = pong)
- lab: `/home/eileen/projects/quilt-gpu-lab`
- engine under test: `quilt-arcade` (local clone) `games/pong`
- pre-registered at: 2026-10-01, before the first model match
- house laws in force: seed **2718**; fail loud; **no receipt → VOID**; do **not** commit.

## Claim under test (adopted verbatim from `RTX4050-WORKLIST.md` §C1)

> **the derived law beats the local 7B at pong in ≥90% of h2h matches.**

Falsifiable both ways: ≥90% → claim survives; <90% → claim **KILLED**.

## Apparatus (fixed before running)

- **Engine tick**: `quilt-arcade/games/pong` sheet loaded **verbatim** via `buildSheet()`.
  The ONLY substitution is the `ai.track` cell, replaced by a program with a per-side
  control switch. The `law` branch is the shipped derived law character-for-character
  (target = `ball.y`, side speed **left 0.85 / right 0.70** per tick, deadzone **1.5**,
  clamp `y ∈ [6,54]`). The `model` branch spends the **identical movement budget**
  (same side speed, same clamp) on a direction the driver supplies. No other engine or
  game code is touched. ⇒ the two arms differ **only** in which policy picks the direction.
- **"Derived law" letter on a state**: the law's per-tick direction is the sign of
  `(ball.y − ownPaddleY)` outside the 1.5 deadzone → `D` if below, `U` if above, `S` inside.
  (Used for the agreement probe; it is an exact re-expression of the law, not a proxy.)
- **Model**: `qwen2.5:7b-instruct-q4_K_M` via ollama at `http://127.0.0.1:11434/api/chat`.
  `temperature 0.7`, ollama `seed = 2718 + game_index`, `num_ctx 1024`, `num_predict 8`,
  `stop ["\n"]`, `keep_alive 30m`.
- **Prompt** (`compact state summary`): side, own paddle y, ball x/y/vx/vy, both scores,
  own speed and reach, goal line; demand one letter of `U`/`D`/`S`.
- **Action space**: one letter — `U` = −speed, `D` = +speed, `S` = 0 (y grows downward).
  Yields the *same* per-tick displacement the derived law is allowed.

## Match design (fixed before running)

- closure = engine `W4`, first to **7** points; hard cap **3000 ticks** per game.
- **N = 40 matches.** games 0–19: model = **RIGHT** paddle (law = left).
  games 20–39: model = **LEFT** paddle (law = right). Controls the law's speed asymmetry.
- match seed = `2718 + game_index` (engine serve seed). ollama seed = `2718 + game_index`.
- **Draw rule (declared BEFORE running)**: a game that hits 3000 ticks without closure is a
  **DRAW**, recorded as **law-not-winning** — it counts in the denominator of the law
  win-rate and is **not** credited to the law. Rationale: the law failed to close on the
  weak opponent within a cap that generous ⇒ not evidence for the claim.
- **Primary metric**: `law_win_rate = law_wins / 40`.
- **Gate**: claim **KILLED iff `law_win_rate < 0.90`**. (≥0.90 ⇒ survives.)

## Secondary metrics (recorded, non-gating)

- **per-tick action agreement**: over the model's decision ticks, fraction where the
  model's letter equals the derived-law letter for the *identical* `(ball.y, own paddle y)`
  state. (Same trajectory the model is on — that is the only state it acts on.)
- **violations**: `parse_fail` (reply with no `U`/`D`/`S`) → **deterministic random fallback**,
  counted; `illegal_first_alpha`; rate reported.
- **crashes**: ollama transport/HTTP errors, engine errors, harness death (counted, fail loud).
- **energy**: `guard.py` G7 watt receipt over the whole window; Wh booked, not claimed idle.

## Calibration note (pre-run, harness-only, no model)

Law-vs-law (no model in the loop) does **not** close inside 3000 ticks: engine seeds 1–8
finished at 3000 ticks with scores left 3–5, right 0–4 (mean 3000, never `over=true`).
So the 3000 cap is *generous*, and **any draw in this experiment is itself a falsification
signal** (a draw means the model matched the law well enough to keep the match open).

## Amendments

- None. No amendment will be logged after the first measured match begins; anything
  computed afterwards is labelled **exploratory** in `RESULTS-ENTRY.md`.
