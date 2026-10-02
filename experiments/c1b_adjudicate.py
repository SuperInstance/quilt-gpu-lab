#!/usr/bin/env python3
"""c1b_adjudicate.py — lane C1b FINISH-GATE: union adjudication of the C1-PLAYTEST
>=90% gate over the FULL pre-registered N=40 (games 0-6 from segment 1, games 7-39
from segment 2). Read-only over both match_summary.json artifacts; writes nothing.

Exact binomial (Clopper-Pearson) + Wilson CI for the law win-rate; per-arm split;
agreement, violations, energy. House law: seed 2718; receipt or VOID.
"""
from __future__ import annotations
import json
from pathlib import Path
from math import comb, sqrt

LAB = Path("/home/eileen/projects/quilt-gpu-lab")
SEG1 = LAB / "results/c1_playtest/match_summary.json"            # games 0-6
SEG2 = LAB / "results/c1_playtest/c1b_run/match_summary.json"    # games 7-39


def clopper_pearson(k, n, alpha=0.05):
    """Exact binomial CI by bisection on the Beta quantile (no scipy)."""
    def binom_cdf(x, n, p):
        return sum(comb(n, i) * p**i * (1 - p)**(n - i) for i in range(0, x + 1))

    def lower():
        if k == 0:
            return 0.0
        lo, hi = 0.0, 1.0
        for _ in range(200):
            mid = (lo + hi) / 2
            if binom_cdf(k - 1, n, mid) > alpha / 2:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    def upper():
        if k == n:
            return 1.0
        lo, hi = 0.0, 1.0
        for _ in range(200):
            mid = (lo + hi) / 2
            if binom_cdf(k, n, mid) < 1 - alpha / 2:
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


def load(p):
    return json.loads(p.read_text())


def main():
    s1, s2 = load(SEG1), load(SEG2)
    games = list(s1["games"]) + list(s2["games"])
    games.sort(key=lambda m: m["game_index"])
    n = len(games)
    law_wins = sum(1 for m in games if m.get("law_won"))
    draws = sum(1 for m in games if m.get("draw"))
    model_wins = sum(1 for m in games if m.get("model_won"))
    crashes = sum(1 for m in games if m.get("crashed"))
    decisions = sum(m.get("decisions", 0) for m in games)
    agree = sum(m.get("agree", 0) for m in games)
    pf = sum(m.get("parse_fail", 0) for m in games)
    ill = sum(m.get("illegal_first_alpha", 0) for m in games)
    oe = sum(m.get("ollama_errors", 0) for m in games)
    ee = sum(m.get("engine_errors", 0) for m in games)
    rate = law_wins / n if n else None

    def arm(lo, hi):
        a = [m for m in games if lo <= m["game_index"] < hi]
        w = sum(1 for m in a if m.get("law_won"))
        d = sum(1 for m in a if m.get("draw"))
        dec = sum(m.get("decisions", 0) for m in a)
        ag = sum(m.get("agree", 0) for m in a)
        return {"games": len(a), "law_wins": w, "draws": d,
                "law_win_rate": round(w / len(a), 4) if a else None,
                "agreement": round(ag / dec, 4) if dec else None,
                "decisions": dec}

    cp = clopper_pearson(law_wins, n) if n else (None, None)
    wl = wilson(law_wins, n) if n else (None, None)
    complete = (n == 40 and s2.get("status") == "RUN")
    killed = (rate is not None and rate < 0.90)
    out = {
        "lane": "C1b-FINISH-GATE",
        "claim": "derived law beats the local 7B at pong in >=90% of h2h matches",
        "N": n, "N_prereg": 40,
        "complete": complete,
        "gate_rule": "KILLED iff law_win_rate < 0.90 (over pre-registered N=40)",
        "law_wins": law_wins, "model_wins": model_wins, "draws": draws,
        "law_win_rate": round(rate, 4) if rate is not None else None,
        "gate_outcome": (("CLAIM-KILLED" if killed else "CLAIM-SURVIVES")
                         if complete else "NOT-ADJUDICATED-PARTIAL"),
        "cp95_ci_exact": [round(cp[0], 4), round(cp[1], 4)] if n else None,
        "wilson95_ci": [round(wl[0], 4), round(wl[1], 4)] if n else None,
        "ci_note": ("law_win_rate = %s/40 = %.4f; exact 95%% CI [%.4f, %.4f] excludes 0.90 "
                    "if the lower bound > 0.90" % (law_wins, rate or 0, cp[0], cp[1])) if n else None,
        "agreement_rate": round(agree / decisions, 4) if decisions else None,
        "decisions": decisions, "agree": agree,
        "parse_fail": pf, "parse_fail_rate": round(pf / decisions, 4) if decisions else None,
        "illegal_first_alpha": ill, "ollama_errors": oe, "engine_errors": ee,
        "crashes": crashes,
        "arm_model_right_g0_19": arm(0, 20),
        "arm_model_left_g20_39": arm(20, 40),
        "seg1_status": s1.get("status"), "seg2_status": s2.get("status"),
        "seg2_elapsed_s": s2.get("elapsed_s"),
        "per_game": [{"g": m["game_index"], "side": m["model_side"], "ticks": m.get("ticks"),
                      "score": f'{m.get("score_left")}-{m.get("score_right")}',
                      "winner": m.get("winner"), "law_won": m.get("law_won"),
                      "draw": m.get("draw"), "agreement": m.get("agreement")} for m in games],
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
