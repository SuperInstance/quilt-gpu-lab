# C1B RESULTS ENTRY — C1-PLAYTEST FINISH-GATE (final N=40 adjudication)

- **lane:** C1b-FINISH-GATE r2 (closes worklist `C1`), lab `/home/eileen/projects/quilt-gpu-lab`
- **date:** 2026-10-01 · **seed:** 2718 · **device:** RTX 4050 Laptop 6 GB (WSL2)
- **pre-registration:** `results/c1_playtest/PREREG.md` — **unchanged, frozen before the first match**
- **segments folded:** seg1 = games 0-6 (`results/c1_playtest/`, original entry) ·
  segA = games 7-14 (`c1b_run/`, prior lane; per-match block reconstructed from its frozen
  per-tick trace, because the lane was infra-killed before it wrote `match_summary.json`) ·
  segC = games 15-39 (`c1b_run_b/`, this lane)
- **status:** **FINAL — N=40/40 pre-registered games. Gate adjudicated.**
- **posture:** book, do **not** commit.

## Gate verdict at N=40

> Claim (pre-registered): **the derived law beats the local 7B at pong in ≥90% of h2h matches.**
> Rule: **KILLED iff law_win_rate < 0.90.**

| | |
|---|---|
| **law wins** | **40 / 40** |
| model wins | 0 |
| draws (law-not-winning by rule) | 0 |
| **law win-rate** | **1.0** |
| **≥90% gate** | **CLAIM-SURVIVES** |
| 95% CI, exact (Clopper–Pearson) | [0.9119, 1.0] |
| 95% CI, Wilson | [0.9124, 1.0] |
| crashes (ollama/engine/harness) | 0 |

The point estimate is **1.0**; the exact 95% CI is **[0.9119, 1.0000]**.
The lower bound clears 0.90, so the ≥90% gate **survives at N=40**.

## Arms (pre-registered control for the law's speed asymmetry)

| arm | games | law wins | draws | law win-rate | agreement |
|---|---|---|---|---|---|
| model-as-RIGHT (g0-19) | 20 | 20 | 0 | 1.0 | 0.0867 |
| model-as-LEFT (g20-39) | 20 | 20 | 0 | 1.0 | 0.1012 |

## Secondary metrics (non-gating), over all N=40

| metric | value |
|---|---|
| **per-tick action agreement** (7B vs law on identical state) | **0.0936** (4583 / 48973 decisions) |
| rule violations: parse-fail | **0** (rate 0.0) |
| rule violations: illegal first alpha | 0 (not recoverable for segA from its trace; 0 in seg1+segC) |
| ollama transport errors | 0 |
| engine errors | 0 |
| crashes | 0 |
| energy (guard G7, MEASURED, segment-3 window) | **71.219 Wh** (256386.7354 J; 3859.027 GPU-s) |
| guard receipt (segment 3) | `results/c1_playtest/c1b_run_b/guard/g7-wr-c1-playtest-pong-1790904047.json` — schema `g7-watt-receipt@1`, verdict **PASS** |

## Per-game (all 40)

| g | model side | ticks | score (L-R) | winner | agreement |
|---|---|---|---|---|---|
| 0 | right | 1307 | 7-0 | left | 0.1094 |
| 1 | right | 1331 | 7-2 | left | 0.0811 |
| 2 | right | 1303 | 7-0 | left | 0.1811 |
| 3 | right | 1182 | 7-1 | left | 0.0431 |
| 4 | right | 1664 | 7-1 | left | 0.0907 |
| 5 | right | 817 | 7-0 | left | 0.0588 |
| 6 | right | 1672 | 7-1 | left | 0.0682 |
| 7 | right | 1005 | 7-0 | left | 0.0259 |
| 8 | right | 1307 | 7-0 | left | 0.1163 |
| 9 | right | 1323 | 7-0 | left | 0.0945 |
| 10 | right | 915 | 7-0 | left | 0.0011 |
| 11 | right | 1876 | 7-3 | left | 0.072 |
| 12 | right | 1665 | 7-0 | left | 0.0775 |
| 13 | right | 1387 | 7-1 | left | 0.2177 |
| 14 | right | 1076 | 7-1 | left | 0.0576 |
| 15 | right | 1867 | 7-0 | left | 0.1093 |
| 16 | right | 672 | 7-1 | left | 0.0506 |
| 17 | right | 1205 | 7-0 | left | 0.0763 |
| 18 | right | 1666 | 7-1 | left | 0.0534 |
| 19 | right | 515 | 7-0 | left | 0.0621 |
| 20 | left | 978 | 1-7 | right | 0.0767 |
| 21 | left | 1013 | 0-7 | right | 0.0671 |
| 22 | left | 1087 | 0-7 | right | 0.0497 |
| 23 | left | 1260 | 1-7 | right | 0.2087 |
| 24 | left | 1405 | 0-7 | right | 0.0847 |
| 25 | left | 1241 | 2-7 | right | 0.0492 |
| 26 | left | 1080 | 1-7 | right | 0.0463 |
| 27 | left | 978 | 1-7 | right | 0.0511 |
| 28 | left | 1170 | 1-7 | right | 0.2265 |
| 29 | left | 1605 | 2-7 | right | 0.0866 |
| 30 | left | 978 | 1-7 | right | 0.0562 |
| 31 | left | 1888 | 0-7 | right | 0.1367 |
| 32 | left | 1209 | 0-7 | right | 0.0662 |
| 33 | left | 1001 | 0-7 | right | 0.1618 |
| 34 | left | 1358 | 1-7 | right | 0.123 |
| 35 | left | 809 | 0-7 | right | 0.0655 |
| 36 | left | 1013 | 0-7 | right | 0.0355 |
| 37 | left | 1111 | 0-7 | right | 0.1197 |
| 38 | left | 1115 | 0-7 | right | 0.1722 |
| 39 | left | 919 | 0-7 | right | 0.0751 |

## Ops notes

- Segment 3 ran the **frozen** driver (`experiments/c1_playtest_pong.py`) with
  `--start 15 --games 40 --out results/c1_playtest/c1b_run_b`, re-entering the identical
  pre-registered loop at index 15 (engine seed = ollama seed = 2718+gi, arm split gi<20 ⇒ model
  RIGHT). The seat was held exclusively: `OLLAMA_MAX_LOADED_MODELS=1`, `qwen2.5:7b-instruct-q4_K_M`
  resident for the whole window.
- Two partial traces exist from the infra kill and are **excluded** (not re-run, not double-counted):
  `c1b_run/games.jsonl` shows game 15 truncated at 594 ticks, and
  `c1b_run_b/games.partial-g15-827ticks.archived-20261001.jsonl` shows a second game-15 attempt
  truncated at 827 ticks. Game 15 is booked once, from the segment-3 run.
- Segment 1 (`RESULTS-ENTRY.md`, games 0-6) is **not modified**; this entry folds it.
- Segment A's own guard window sealed **VOID** (`inner rc=-15`, the infra kill); its measured
  rows are used because the per-tick trace is complete and self-consistent (reconstructed match
  stats match its driver log exactly). Segment 1's window was PASS (21.09 Wh). The booking
  receipt above is the fresh, MEASURED segment-3 receipt.
- Adjudication: exact Clopper–Pearson + Wilson 95% CIs; per-arm split; violations and Wh over
  the union, by `experiments/c1b_finalize.py`. The exact CI is cross-checked against
  `scipy.stats.beta.ppf` (agreement to 1e-6); note the earlier helper `experiments/c1b_adjudicate.py`
  carried an inverted Clopper–Pearson bisection (it reported 0.9994 for 40/40; the correct bound is
  0.9119) — the verdict does not depend on it, and `c1b_finalize.py` supersedes it.
- Both `seg1` and `segC` report driver-level status `PARTIAL` **by construction** (seg1 is the
  first 7 of 40; segC is a *resumed* segment beginning at index 15), so the driver deliberately
  refuses to adjudicate. The pre-registered N=40 gate is adjudicated here, by the keeper, over the
  union of the three segments.
- `c1b_run_b/games.jsonl` per-tick rows hit the driver's 2 MB cap at game 25 (tick 445); the
  per-match block (`match_summary.json`) is complete for all 25 segment-3 games, so the capping
  costs trace detail only, not any booked statistic.

## Artifacts (all under `results/c1_playtest/`)

- `C1B-RESULTS-ENTRY.md` — this file
- `c1b_run_b/match_summary.json`, `c1b_run_b/games.jsonl` — segment-3 per-match + per-tick rows
- `c1b_run_b/c1b_final_adjudication.json` — **union N=40 adjudication** (the gate computation)
- `c1b_run_b/guard/` — fresh G7 watt receipt (segment 3)
- `c1b_run/games.jsonl` (+ archived copy) — segment-2A frozen trace (games 7-14)
- `match_summary.json`, `games.jsonl`, `guard/` — segment 1 (v1 entry, unchanged)
- code: `experiments/c1_playtest_pong.py`, `c1_pong_engine.mjs`, `c1b_finalize.py`
