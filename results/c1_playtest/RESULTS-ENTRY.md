# RESULTS ENTRY — C1-PLAYTEST (the Local Playtester, pong PoC)

- **lane:** C1-PLAYTEST (worklist `C1`), lab `/home/eileen/projects/quilt-gpu-lab`
- **date:** 2026-10-01 · **seed:** 2718 · **device:** RTX 4050 Laptop 6 GB (WSL2)
- **pre-registration:** `results/c1_playtest/PREREG.md` (written before the first match)
- **status:** **PARTIAL — 7/40 pre-registered games. Gate NOT adjudicated.**

## Headline

| metric | value |
|---|---|
| **law win-rate** | **7/7 = 1.000** (directional only — sample is 7/40) |
| **≥90% gate** | **NOT-ADJUDICATED-PARTIAL** (needs the full N=40) |
| draws | 0 (every game closed at 7) |
| model wins | 0 |
| **per-tick action agreement** (7B vs law, identical state) | **0.0917** (851 / 9,276 decisions) |
| rule violations: parse-fail | **0** (rate 0.0000) |
| rule violations: illegal first alpha | 0 |
| crashes: ollama / engine / harness | **0 / 0 / 0** |
| energy (guard G7, MEASURED) | **21.09 Wh** (75,915.2 J; 1110.2 GPU-s) |
| guard receipt | `guard/g7-wr-c1-playtest-pong-1790894210.json` — schema-valid, verdict **PASS** |

Per-game (all seven had the model on the **RIGHT** paddle; law on the left):

| g | ticks | score (L-R) | winner | agreement | wall s |
|---|---|---|---|---|---|
| 0 | 1307 | 7-0 | law | 0.1094 | 206.6 |
| 1 | 1331 | 7-2 | law | 0.0811 | 237.7 |
| 2 | 1303 | 7-0 | law | 0.1811 | 237.6 |
| 3 | 1182 | 7-1 | law | 0.0431 | 254.8 |
| 4 | 1664 | 7-1 | law | 0.0907 | 300.3 |
| 5 |  817 | 7-0 | law | 0.0588 | 140.4 |
| 6 | 1672 | 7-1 | law | 0.0682 | 263.4 |

## What was actually measured

The derived law and qwen2.5:7b-instruct-q4_K_M played head-to-head through the
**real quilt-arcade pong engine** (`games/pong`, `buildSheet()` verbatim). The only
engine substitution is `ai.track`, replaced by a control switch: `law` mode is the
shipped derived law character-for-character (track `ball.y`, side speed 0.85/0.70,
deadzone 1.5, clamp [6,54]); `model` mode spends the **identical movement budget**
on a one-letter (`U`/`D`/`S`) decision from ollama. So both paddles move at the same
speed under the same clamps, and the arms differ only in who picks the direction.

The model is not close to the law: it agrees with the law's own per-tick direction
on **9.2%** of decisions, and loses every game. That is the pre-registered claim's
direction, but **seven games cannot adjudicate a ≥90% gate** (7/7 has a 95% CI of
[0.61, 1.00]); this is recorded as directional, not as a verdict.

**Directional corroboration (exploratory, not part of the pre-registered run):**
two aborted attempts (below) each show the law leading and the same ~0.12 agreement.
Merged with the seven: **9 partial/complete games, law 9/9, agreement ≈ 0.10.**

## Fail-loud ops log — why 7/40 (read this before re-running)

1. **Thrash, attempt 1.** The first launch used `num_ctx=512`. This host runs
   **`OLLAMA_MAX_LOADED_MODELS=1`**, and a concurrent lane (`xp_c_envelope
   --probe-determinism`, model `qwen2.5:3b`) requests a different model/ctx. Every
   model switch forces a **full reload ⇒ ~10 s per tick**. Fix: drop `num_ctx` and
   use the server default so all lanes share one resident runner. The partial artifact
   is archived as `_archive/games.aborted-thrash.jsonl` (g0: 1069 ticks, law 4-0, agree 0.116).
2. **Thrash, attempt 2.** Relaunched; the same lane's probe resumed, alternating
   3b/7b on ollama and re-triggering the reload-per-call. Driver was `SIGSTOP`ped
   ~90 s until the other lane drained, then resumed. Archived
   `_archive/games.aborted-2.jsonl` (g0: 590 ticks, law 2-0, agree 0.134).
3. **Wall-clock economics (the real finding).** Uncontended, one call ≈ **70–230 ms**
   (146-token templated prompt, 2 generated tokens, `-np 1`). A law-vs-7B game needs
   ~1,300–1,700 ticks (points are paced by ball traversal, so ~200 ticks/point), i.e.
   **~235 s per game**. **N=40 at this cadence is ≈ 2.5 hours** — the worklist's ≈50 min
   estimate does not survive contact with per-tick LLM calls. The driver therefore
   carries a `--budget-s` that halts **between games** and finalises cleanly, so the
   run seals a valid PASS receipt instead of a timeout VOID.
4. `scripts/`-level: the receipt was re-validated by `fleet-seeds/scripts/g7_validate.mjs`
   (exit 0). No commit was made.

## Honest limits

- **7/40 games.** Gate not adjudicated. The pre-registered decision rule needs N=40.
- **One arm only.** Games 0–19 are model-as-RIGHT; games 20–39 (model-as-LEFT, which
  controls for the law's 0.85-vs-0.70 speed asymmetry) were never reached.
- Agreement is measured against the law's *own* direction on the model's actual
  trajectory — it is a policy-agreement probe, not a counterfactual replay.
- Contention with other lanes is environmental; a fleet-clean window (or a dedicated
  seat) is required for the full run.

## To finish it

Re-run `python3 experiments/c1_playtest_pong.py` (no budget, or a larger one) in a
window with **no concurrent ollama multi-model lanes**; expect ≈2.5 h. Everything
else (pre-reg, seeds, prompt, gate) is frozen and unchanged.

## Artifacts (all in `results/c1_playtest/`)

- `PREREG.md` — pre-registration (unchanged)
- `match_summary.json` — per-match summaries + aggregates (status PARTIAL)
- `run_config.json` — pinned apparatus (model, temp, seed policy, substituted cell)
- `games.jsonl` — per-tick rows, 1.60 MB (under the 2 MB cap; `capped=false`)
- `guard/g7-wr-c1-playtest-pong-1790894210.json` — G7 watt receipt (PASS, 21.09 Wh)
- `guard/guard_summary.json`, `guard/ledger.jsonl` — guard digest + append-only ledger
- `run.log` — driver log (warm, per-game lines, budget halt, receipt)
- `_archive/games.aborted-thrash.jsonl`, `_archive/games.aborted-2.jsonl` — the two
  contention-aborted partials (exploratory only; not folded into the gate)
- code: `experiments/c1_playtest_pong.py` (driver) + `experiments/c1_pong_engine.mjs`
  (engine harness)
