#!/usr/bin/env python3
"""c1b_book.py — lane C1b FINISH-GATE: author C1B-RESULTS-ENTRY.md from measured
artifacts (segment-1 + segment-2 summaries, union adjudication, fresh G7 receipt).
Idempotent, read-mostly: only writes results/c1_playtest/C1B-RESULTS-ENTRY.md.
Does NOT modify RESULTS-ENTRY.md. Does NOT commit.
"""
from __future__ import annotations
import json
from pathlib import Path

LAB = Path("/home/eileen/projects/quilt-gpu-lab")
R = LAB / "results/c1_playtest"
SEG2 = R / "c1b_run"


def j(p):
    return json.loads(Path(p).read_text())


def main():
    adj = j(SEG2 / "c1b_adjudication.json")
    s1 = j(R / "match_summary.json")
    s2 = j(SEG2 / "match_summary.json")

    receipts = sorted((SEG2 / "guard").glob("g7-wr-*.json"))
    rec = j(receipts[-1]) if receipts else {}
    en = rec.get("energy", {})
    comp = rec.get("compute", {})

    def armline(a):
        return (f"| model-as-{'RIGHT' if a is adj['arm_model_right_g0_19'] else 'LEFT'} "
                f"| {a['games']} | {a['law_wins']} | {a['draws']} | "
                f"{a['law_win_rate']} | {a['agreement']} |")

    rows = "\n".join(
        f"| {g['g']} | {g['side']} | {g['ticks']} | {g['score']} | {g['winner']} | "
        f"{g['agreement']} |" for g in adj["per_game"])

    cp = adj["cp95_ci_exact"]
    wl = adj["wilson95_ci"]
    md = f"""# C1B RESULTS ENTRY — C1-PLAYTEST FINISH-GATE (final N=40 adjudication)

- **lane:** C1b-FINISH-GATE (closes worklist `C1`), lab `/home/eileen/projects/quilt-gpu-lab`
- **date:** 2026-10-01 · **seed:** 2718 · **device:** RTX 4050 Laptop 6 GB (WSL2)
- **pre-registration:** `results/c1_playtest/PREREG.md` — **unchanged, frozen before the first match**
- **segments folded:** segment 1 = games 0-6 (`results/c1_playtest/`, unchanged) ·
  segment 2 = games 7-39 (`results/c1_playtest/c1b_run/`, this lane, resumed at index 7)
- **status:** **FINAL — N={adj['N']}/{adj['N_prereg']} pre-registered games. Gate adjudicated.**
- **posture:** book, do **not** commit.

## Gate verdict at N=40

> Claim (pre-registered): **the derived law beats the local 7B at pong in ≥90% of h2h matches.**
> Rule: **KILLED iff law_win_rate < 0.90.**

| | |
|---|---|
| **law wins** | **{adj['law_wins']} / {adj['N']}** |
| model wins | {adj['model_wins']} |
| draws (law-not-winning by rule) | {adj['draws']} |
| **law win-rate** | **{adj['law_win_rate']}** |
| **≥90% gate** | **{adj['gate_outcome']}** |
| 95% CI, exact (Clopper–Pearson) | [{cp[0]}, {cp[1]}] |
| 95% CI, Wilson | [{wl[0]}, {wl[1]}] |
| crashes (ollama/engine/harness) | {adj['crashes']} |

{"" if adj['gate_outcome'] == 'CLAIM-SURVIVES' else ''}The point estimate is **{adj['law_win_rate']}**; the exact 95% CI is **[{'%.4f' % cp[0]}, {'%.4f' % cp[1]}]**.
{"The lower bound clears 0.90, so the ≥90% gate **survives at N=40**." if cp[0] >= 0.90 else "The lower bound does **not** clear 0.90; the verdict is read off the pre-registered point rule (`< 0.90` ⇒ KILLED), and the CI width is stated honestly."}

## Arms (pre-registered control for the law's speed asymmetry)

| arm | games | law wins | draws | law win-rate | agreement |
|---|---|---|---|---|---|
{armline(adj['arm_model_right_g0_19'])}
{armline(adj['arm_model_left_g20_39'])}

## Secondary metrics (non-gating), over all N={adj['N']}

| metric | value |
|---|---|
| **per-tick action agreement** (7B vs law on identical state) | **{adj['agreement_rate']}** ({adj['agree']} / {adj['decisions']} decisions) |
| rule violations: parse-fail | **{adj['parse_fail']}** (rate {adj['parse_fail_rate']}) |
| rule violations: illegal first alpha | {adj['illegal_first_alpha']} |
| ollama transport errors | {adj['ollama_errors']} |
| engine errors | {adj['engine_errors']} |
| crashes | {adj['crashes']} |
| energy (guard G7, MEASURED, whole window) | **{round(en.get('watt_hours', 0), 3)} Wh** ({en.get('joules')} J; {comp.get('gpu_seconds')} GPU-s) |
| guard receipt | `{receipts[-1].relative_to(LAB) if receipts else 'MISSING'}` — schema `{rec.get('schema')}`, verdict **{rec.get('gate', {}).get('verdict')}** |

## Per-game (all {adj['N']})

| g | model side | ticks | score (L-R) | winner | agreement |
|---|---|---|---|---|---|
{rows}

## Ops notes

- Segment 2 ran the **frozen** driver (`experiments/c1_playtest_pong.py`) with `--start 7 --games 40`,
  re-entering the identical pre-registered loop at index 7 (seeds 2718+gi, arm split gi<20 ⇒ model
  RIGHT). The seat was held exclusively: `OLLAMA_MAX_LOADED_MODELS=1`, `qwen2.5:7b-instruct-q4_K_M`
  resident for the whole window, no concurrent model lane (`/api/ps` single-entry throughout).
- Segment 1 (`RESULTS-ENTRY.md`, games 0-6) is **not modified**; this entry folds it.
- Adjudication is computed over the union of both segments by `experiments/c1b_adjudicate.py`.

## Artifacts (all under `results/c1_playtest/`)

- `C1B-RESULTS-ENTRY.md` — this file
- `c1b_run/match_summary.json`, `c1b_run/games.jsonl` — segment-2 per-match + per-tick rows
- `c1b_run/c1b_adjudication.json` — **union N=40 adjudication** (the gate computation)
- `c1b_run/{dir}guard/` — G7 watt receipt (segment 2)
- `match_summary.json`, `games.jsonl`, `guard/` — segment 1 (v1 entry, unchanged)
- code: `experiments/c1_playtest_pong.py`, `c1_pong_engine.mjs`, `c1b_adjudicate.py`, `c1b_book.py`
"""
    (R / "C1B-RESULTS-ENTRY.md").write_text(md)
    print(f"wrote {R / 'C1B-RESULTS-ENTRY.md'} ({len(md)} bytes)")


if __name__ == "__main__":
    main()
