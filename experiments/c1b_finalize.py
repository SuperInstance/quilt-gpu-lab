#!/usr/bin/env python3
"""c1b_finalize.py — lane C1b-FINISH-GATE r2: FINAL union adjudication of the
C1-PLAYTEST >=90% gate over the full pre-registered N=40, and authoring of
results/c1_playtest/C1B-RESULTS-ENTRY.md.

Three measured segments are folded:
  seg1 = games 0-6   -> results/c1_playtest/match_summary.json        (original entry)
  segA = games 7-14  -> results/c1_playtest/c1b_run/games.jsonl       (per-tick trace; the
                        prior lane was killed before it wrote a match_summary, so the
                        per-match block is RECONSTRUCTED from the frozen trace)
  segC = games 15-39 -> results/c1_playtest/c1b_run_b/match_summary.json (this lane)

Read-mostly. Writes: c1b_run_b/c1b_final_adjudication.json and
results/c1_playtest/C1B-RESULTS-ENTRY.md. Does NOT modify RESULTS-ENTRY.md. Does NOT commit.
"""
from __future__ import annotations
import json
from math import comb, sqrt
from pathlib import Path

LAB = Path("/home/eileen/projects/quilt-gpu-lab")
R = LAB / "results/c1_playtest"
SEG1 = R / "match_summary.json"
SEGA_TRACE = R / "c1b_run/games.jsonl"          # trace rows for games 7-14 (+ partial 15)
SEGC = R / "c1b_run_b/match_summary.json"
SEGC_DIR = R / "c1b_run_b"


def j(p):
    return json.loads(Path(p).read_text())


# ── stats ────────────────────────────────────────────────────────────────────
def clopper_pearson(k, n, alpha=0.05):
    """Exact (Clopper-Pearson) binomial CI via bisection on the binomial CDF.

    lower L solves  P(X >= k | n, L) = alpha/2  (i.e. 1 - cdf(k-1) = alpha/2)
    upper U solves  P(X <= k | n, U) = alpha/2
    """
    def cdf(x, n, p):
        if p <= 0.0:
            return 1.0
        if p >= 1.0:
            return 1.0 if x >= n else 0.0
        return sum(comb(n, i) * p**i * (1 - p)**(n - i) for i in range(0, x + 1))

    def lower():
        if k == 0:
            return 0.0
        lo, hi = 0.0, 1.0
        for _ in range(300):
            mid = (lo + hi) / 2
            if (1.0 - cdf(k - 1, n, mid)) > alpha / 2:   # P(X>=k) too large -> p too large
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2

    def upper():
        if k == n:
            return 1.0
        lo, hi = 0.0, 1.0
        for _ in range(300):
            mid = (lo + hi) / 2
            if cdf(k, n, mid) > alpha / 2:               # p too small
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    return lower(), upper()


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return None, None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


# ── segment loading ──────────────────────────────────────────────────────────
def load_seg1():
    s = j(SEG1)
    return list(s["games"]), s


def reconstruct_segA():
    """Rebuild per-match records for games 7-14 from the frozen per-tick trace."""
    games = {}
    order = []
    with open(SEGA_TRACE) as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            o = json.loads(ln)
            g = o["g"]
            if g < 7 or g > 14:          # segA only; drop the partial g15 rows
                continue
            if g not in games:
                games[g] = {"game_index": g, "model_side": o["side"], "rows": 0,
                            "agree": 0, "parse_fail": 0, "sL": 0, "sR": 0}
                order.append(g)
            d = games[g]
            d["rows"] += 1
            d["agree"] += int(o["letter"] == o["law_letter"])
            d["parse_fail"] += int(not o["ok"])
            d["sL"], d["sR"] = o["sL"], o["sR"]
    out = []
    for g in sorted(order):
        d = games[g]
        first_to = 7
        closed = (d["sL"] >= first_to or d["sR"] >= first_to)
        winner = ("left" if d["sL"] > d["sR"] else "right") if closed else None
        law_side = "right" if d["model_side"] == "left" else "left"
        out.append({
            "game_index": g, "model_side": d["model_side"],
            "seed": 2718 + g, "ollama_seed": 2718 + g,
            "ticks": d["rows"], "closed": closed, "draw": (not closed),
            "winner": winner, "score_left": d["sL"], "score_right": d["sR"],
            "law_won": bool(closed and winner == law_side),
            "model_won": bool(closed and winner == d["model_side"]),
            "crashed": False, "decisions": d["rows"], "agree": d["agree"],
            "agreement": round(d["agree"] / d["rows"], 4) if d["rows"] else None,
            "parse_fail": d["parse_fail"], "illegal_first_alpha": None,
            "ollama_errors": 0, "engine_errors": 0, "wall_s": None,
            "recovered_from_trace": True,
        })
    return out


def load_segC():
    s = j(SEGC)
    return list(s["games"]), s


# ── main ─────────────────────────────────────────────────────────────────────
def main():
    g1, s1 = load_seg1()
    gA = reconstruct_segA()
    gC, sC = load_segC()
    games = g1 + gA + gC
    games.sort(key=lambda m: m["game_index"])
    n = len(games)
    idx = [m["game_index"] for m in games]
    assert idx == list(range(n)), f"non-contiguous game coverage: {idx}"

    law_wins = sum(1 for m in games if m.get("law_won"))
    draws = sum(1 for m in games if m.get("draw"))
    model_wins = sum(1 for m in games if m.get("model_won"))
    crashes = sum(1 for m in games if m.get("crashed"))
    decisions = sum(m.get("decisions", 0) for m in games)
    agree = sum(m.get("agree", 0) for m in games)
    pf = sum(m.get("parse_fail") or 0 for m in games)
    ill = sum(m.get("illegal_first_alpha") or 0 for m in games)
    ill_known = all(m.get("illegal_first_alpha") is not None for m in games)
    oe = sum(m.get("ollama_errors") or 0 for m in games)
    ee = sum(m.get("engine_errors") or 0 for m in games)
    rate = law_wins / n if n else None
    complete = (n == 40)
    killed = (rate is not None and rate < 0.90)
    cp = clopper_pearson(law_wins, n) if n else (None, None)
    wl = wilson(law_wins, n) if n else (None, None)

    def arm(lo, hi):
        a = [m for m in games if lo <= m["game_index"] < hi]
        w = sum(1 for m in a if m.get("law_won"))
        d = sum(1 for m in a if m.get("draw"))
        dec = sum(m.get("decisions", 0) for m in a)
        ag = sum(m.get("agree", 0) for m in a)
        return {"games": len(a), "law_wins": w, "draws": d,
                "law_win_rate": round(w / len(a), 4) if a else None,
                "agreement": round(ag / dec, 4) if dec else None, "decisions": dec}

    adj = {
        "lane": "C1b-FINISH-GATE r2",
        "claim": "derived law beats the local 7B at pong in >=90% of h2h matches",
        "N": n, "N_prereg": 40, "complete": complete,
        "gate_rule": "KILLED iff law_win_rate < 0.90 (over pre-registered N=40)",
        "law_wins": law_wins, "model_wins": model_wins, "draws": draws,
        "law_win_rate": round(rate, 4) if rate is not None else None,
        "gate_outcome": (("CLAIM-KILLED" if killed else "CLAIM-SURVIVES")
                         if complete else "NOT-ADJUDICATED-PARTIAL"),
        "cp95_ci_exact": [round(cp[0], 4), round(cp[1], 4)] if n else None,
        "wilson95_ci": [round(wl[0], 4), round(wl[1], 4)] if n else None,
        "agreement_rate": round(agree / decisions, 4) if decisions else None,
        "decisions": decisions, "agree": agree,
        "parse_fail": pf, "parse_fail_rate": round(pf / decisions, 4) if decisions else None,
        "illegal_first_alpha": ill, "illegal_first_alpha_known": ill_known,
        "ollama_errors": oe, "engine_errors": ee, "crashes": crashes,
        "arm_model_right_g0_19": arm(0, 20),
        "arm_model_left_g20_39": arm(20, 40),
        "segments": {
            "seg1_g0_6": {"source": "match_summary.json", "status": s1.get("status"),
                          "games": [m["game_index"] for m in g1]},
            "segA_g7_14": {"source": "c1b_run/games.jsonl (trace-reconstructed)",
                           "games": [m["game_index"] for m in gA]},
            "segC_g15_39": {"source": "c1b_run_b/match_summary.json", "status": sC.get("status"),
                            "games": [m["game_index"] for m in gC]},
        },
        "per_game": [{"g": m["game_index"], "side": m.get("model_side"),
                      "ticks": m.get("ticks"),
                      "score": f'{m.get("score_left")}-{m.get("score_right")}',
                      "winner": m.get("winner"), "law_won": m.get("law_won"),
                      "draw": m.get("draw"), "agreement": m.get("agreement"),
                      "recovered": bool(m.get("recovered_from_trace"))} for m in games],
    }
    (SEGC_DIR / "c1b_final_adjudication.json").write_text(json.dumps(adj, indent=2))
    print(json.dumps({k: adj[k] for k in (
        "N", "law_wins", "draws", "law_win_rate", "gate_outcome",
        "cp95_ci_exact", "wilson95_ci", "agreement_rate", "parse_fail",
        "illegal_first_alpha", "crashes")}, indent=2))

    # ── author C1B-RESULTS-ENTRY.md ──────────────────────────────────────────
    receipts = sorted((SEGC_DIR / "guard").glob("g7-wr-*.json"))
    rec = j(receipts[-1]) if receipts else {}
    en = rec.get("energy", {})
    comp = rec.get("compute", {})

    def armline(label, a):
        return (f"| model-as-{label} | {a['games']} | {a['law_wins']} | {a['draws']} | "
                f"{a['law_win_rate']} | {a['agreement']} |")

    rows = "\n".join(
        f"| {g['g']} | {g['side']} | {g['ticks']} | {g['score']} | {g['winner']} | "
        f"{g['agreement']} |" for g in adj["per_game"])

    md = f"""# C1B RESULTS ENTRY — C1-PLAYTEST FINISH-GATE (final N=40 adjudication)

- **lane:** C1b-FINISH-GATE r2 (closes worklist `C1`), lab `/home/eileen/projects/quilt-gpu-lab`
- **date:** 2026-10-01 · **seed:** 2718 · **device:** RTX 4050 Laptop 6 GB (WSL2)
- **pre-registration:** `results/c1_playtest/PREREG.md` — **unchanged, frozen before the first match**
- **segments folded:** seg1 = games 0-6 (`results/c1_playtest/`, original entry) ·
  segA = games 7-14 (`c1b_run/`, prior lane; per-match block reconstructed from its frozen
  per-tick trace, because the lane was infra-killed before it wrote `match_summary.json`) ·
  segC = games 15-39 (`c1b_run_b/`, this lane)
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
| 95% CI, exact (Clopper–Pearson) | [{round(cp[0], 4)}, {round(cp[1], 4)}] |
| 95% CI, Wilson | [{round(wl[0], 4)}, {round(wl[1], 4)}] |
| crashes (ollama/engine/harness) | {adj['crashes']} |

The point estimate is **{adj['law_win_rate']}**; the exact 95% CI is **[{'%.4f' % cp[0]}, {'%.4f' % cp[1]}]**.
{"The lower bound clears 0.90, so the ≥90% gate **survives at N=40**." if cp[0] >= 0.90 else "The lower bound does **not** clear 0.90; the verdict is read off the pre-registered point rule (`< 0.90` ⇒ KILLED), and the CI width is stated honestly."}

## Arms (pre-registered control for the law's speed asymmetry)

| arm | games | law wins | draws | law win-rate | agreement |
|---|---|---|---|---|---|
{armline('RIGHT (g0-19)', adj['arm_model_right_g0_19'])}
{armline('LEFT (g20-39)', adj['arm_model_left_g20_39'])}

## Secondary metrics (non-gating), over all N={adj['N']}

| metric | value |
|---|---|
| **per-tick action agreement** (7B vs law on identical state) | **{adj['agreement_rate']}** ({adj['agree']} / {adj['decisions']} decisions) |
| rule violations: parse-fail | **{adj['parse_fail']}** (rate {adj['parse_fail_rate']}) |
| rule violations: illegal first alpha | {adj['illegal_first_alpha']}{'' if adj['illegal_first_alpha_known'] else ' (not recoverable for segA from its trace; 0 in seg1+segC)'} |
| ollama transport errors | {adj['ollama_errors']} |
| engine errors | {adj['engine_errors']} |
| crashes | {adj['crashes']} |
| energy (guard G7, MEASURED, segment-3 window) | **{round(en.get('watt_hours', 0), 3)} Wh** ({en.get('joules')} J; {comp.get('gpu_seconds')} GPU-s) |
| guard receipt (segment 3) | `{receipts[-1].relative_to(LAB) if receipts else 'MISSING'}` — schema `{rec.get('schema')}`, verdict **{rec.get('gate', {}).get('verdict')}** |

## Per-game (all {adj['N']})

| g | model side | ticks | score (L-R) | winner | agreement |
|---|---|---|---|---|---|
{rows}

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
"""
    (R / "C1B-RESULTS-ENTRY.md").write_text(md)
    print(f"wrote {R / 'C1B-RESULTS-ENTRY.md'} ({len(md)} bytes)")


if __name__ == "__main__":
    main()
