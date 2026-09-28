#!/usr/bin/env python3
"""D18 — correlation-discovery scaling: does the D13d primitive generalize?

D13d (KEEP) cracked partner discovery with max |correlation| of atom streams —
1.0 accuracy, NO reward signal — but at N=8 cells, p_corr=0.9. The principle
(docs/RELATIONAL-CORRELATION-PRIMITIVE.md, follow-up section) claims
generality. This experiment tries to falsify that claim on one seeded harness:

  1. Scale  — N in {8, 32, 100, 300} at p_corr=0.9. Claim: identification
     stays >=0.95 at N=100 (correlation is O(N^2) pairwise, O(1) per decision).
  2. Noise  — p_corr in {0.9, 0.75, 0.6, 0.55} across the same N grid.
     Claim: >=0.9 at p_corr=0.6, degrading toward chance near p_corr=0.55 —
     the method dies AT the information bound, not before it.
  3. Reward — re-run the best RL variant (D13c: REINFORCE with learned
     baseline) at N=32, p_corr=0.9, per-edge update budget MATCHED to its
     N=8 run (~32 updates/edge). Claim: concentration collapses <0.3
     (chance 1/31 = 0.032) while correlation does not collapse.

Pre-registered, the number that decides (task spec):
  KEEP  iff correlation accuracy >= 0.9 at (N=100, p_corr=0.9) AND >= 0.9 at
        (N=8, p_corr=0.6) — the strict joint cell (N=100, p_corr=0.6) is also
        reported — AND REINFORCE concentration < 0.3 at N=32.
  KILL  iff correlation collapses at scale or under noise => D13d was a
        small-N artifact; the principle retires to "correlation helps small
        graphs, learning scales".
  INCONCLUSIVE otherwise (e.g. correlation holds but REINFORCE does not
        collapse: the contrast half of the claim fails).

RL adaptations (documented, kept minimal): disjoint partner pairs so RL and
correlation share the SAME ground truth; p_corr gates the partner link
(D13c's true-partner reward was deterministic 1.0, i.e. p_corr=1.0; a broken
link pays coin-flip to every receiver — no signal); senders run round-robin
so the per-edge update budget is identical at every N; softmax stabilized by
max-subtraction (numerical only, no semantic change).

Pure CPU. No model, no torch, no CUDA. numpy only. Minutes.
"""
from __future__ import annotations

import json
import math
import random

import numpy as np

SEED = 2718
N_GRID = (8, 32, 100, 300)
P_GRID = (0.9, 0.75, 0.6, 0.55)
T_OBS = 200        # observation steps — SAME budget at every N (correlation arm)
REPS = 5           # independent reps per grid cell, seeds derived from SEED

CORR_TARGET = 0.90
CORR_SCALE_CELL = (100, 0.9)     # scale claim (doc said 0.95; criterion is 0.9)
CORR_NOISE_CELL = (8, 0.6)       # noise claim at the D13d reference scale
STRICT_JOINT_CELL = (100, 0.6)   # strictest intersection of both claims

RL_P_CORR = 0.9
RL_NS = (8, 32)
RL_REPS = 3
RL_EPOCHS = 30
RL_LR = 0.5
RL_QUBITS = 4
RL_UPDATES_PER_EDGE = 32     # D13c's N=8 budget (~32 updates/edge)
RL_COLLAPSE_TARGET = 0.30    # claim: concentration < 0.3 at N=32


def derived_seed(*parts: int) -> int:
    s = SEED
    for p in parts:
        s = (s * 1_000_003 + int(p) * 7 + 11) % (2**31 - 1)
    return s


def partner_map(n: int) -> np.ndarray:
    """Disjoint pairs (0,1),(2,3),... — the D13d pairing. Cyclic pairing was
    D13d's booked bug: a cell in two pairs gets double-appended, scrambled
    streams."""
    pm = np.arange(n)
    pm[0::2] = np.arange(1, n, 2)
    pm[1::2] = np.arange(0, n, 2)
    return pm


def sample_streams(n: int, p_corr: float, t_obs: int, rng: random.Random) -> np.ndarray:
    """(n, t_obs) +-1 atom streams. Exact D13d generative process: per
    observation step, a partner pair shares its fresh base value w.p. p_corr,
    otherwise both atoms are independent coin flips."""
    s = np.empty((n, t_obs), np.float32)
    for a in range(0, n, 2):
        for t in range(t_obs):
            if rng.random() < p_corr:
                v = 1.0 if rng.random() < 0.5 else -1.0
                s[a, t] = v
                s[a + 1, t] = v
            else:
                s[a, t] = 1.0 if rng.random() < 0.5 else -1.0
                s[a + 1, t] = 1.0 if rng.random() < 0.5 else -1.0
    return s


def corr_identify_acc(n: int, p_corr: float, rep: int) -> float:
    """D13d readout at scale: each cell picks argmax_c |corr(stream_a, stream_c)|,
    c != a. Accuracy = fraction naming their true partner."""
    rng = random.Random(derived_seed(rep, n, round(p_corr * 100)))
    pm = partner_map(n)
    s = sample_streams(n, p_corr, T_OBS, rng)
    c = np.abs(s @ s.T) / T_OBS        # |mean product| = D13d's correlation
    np.fill_diagonal(c, -1.0)          # a cell never nominates itself
    return float((c.argmax(axis=1) == pm).mean())


def run_reinforce(n: int, rep: int, reward_partner_shift: int = 0) -> dict:
    """D13c verbatim mechanism (logit policy per sender, learned baseline,
    REINFORCE update), scaled to n cells with the documented adaptations.
    reward_partner_shift != 0 wires the REWARD to a shifted partner while
    concentration is still scored against the TRUE partner — a built-in
    negative control (shifted wiring must score ~0, else the arm leaks)."""
    rng = random.Random(derived_seed(909, n, rep))
    pm = partner_map(n).tolist()
    cells = [[1 if rng.random() < 0.5 else -1 for _ in range(RL_QUBITS)]
             for _ in range(n)]
    # round-robin senders: equal presentations per sender, so per-edge update
    # budget (RL_UPDATES_PER_EDGE) is identical at every N
    per_sender_epoch = math.ceil(RL_UPDATES_PER_EDGE * (n - 1) / RL_EPOCHS)
    facts = {}   # (a, fact_idx) -> (qa, qb, b, truth)
    for a in range(n):
        b = pm[(a + reward_partner_shift) % n]
        for k in range(per_sender_epoch):
            qa, qb = rng.randrange(RL_QUBITS), rng.randrange(RL_QUBITS)
            facts[(a, k)] = (qa, qb, b, 1 if cells[a][qa] == cells[b][qb] else 0)

    logit = [[0.0] * n for _ in range(n)]
    baseline = [0.5] * n
    others = [[r for r in range(n) if r != a] for a in range(n)]

    def softmax(logits: list[float], row_others: list[int]) -> list[float]:
        m = max(logits[r] for r in row_others)   # numerical stability only
        e = [math.exp(logits[r] - m) for r in row_others]
        s = sum(e)
        return [x / s for x in e]

    acc_history = []
    for _ in range(RL_EPOCHS):
        correct = 0
        total = 0
        for a in range(n):
            row_others = others[a]
            for k in range(per_sender_epoch):
                qa, qb, b, truth = facts[(a, k)]
                probs = softmax(logit[a], row_others)
                r = rng.choices(row_others, weights=probs, k=1)[0]
                link_ok = rng.random() < RL_P_CORR
                if link_ok and r == b:
                    recon = truth          # intact partner link reveals truth
                else:
                    recon = 1 if rng.random() < 0.5 else 0
                reward = 1.0 if recon == truth else 0.0
                # REINFORCE: grad of log-prob, scaled by (reward - baseline)
                for j, rr in enumerate(row_others):
                    grad = (1.0 - probs[j]) if rr == r else (-probs[j])
                    logit[a][rr] += RL_LR * (reward - baseline[a]) * grad
                baseline[a] = 0.9 * baseline[a] + 0.1 * reward
                correct += 1 if recon == truth else 0
                total += 1
        acc_history.append(round(correct / total, 3))

    concentrated = 0
    for a in range(n):
        b = pm[a]
        best = max(others[a], key=lambda r: logit[a][r])
        concentrated += 1 if best == b else 0
    return {
        "conc": concentrated / n,
        "final_acc": acc_history[-1],
        "updates_per_edge": per_sender_epoch * RL_EPOCHS / (n - 1),
    }


def main():
    # --- correlation arm: full N x p_corr grid, same T_OBS budget everywhere
    corr_acc = {}
    for n in N_GRID:
        corr_acc[n] = {}
        for p in P_GRID:
            vals = [corr_identify_acc(n, p, rep) for rep in range(REPS)]
            corr_acc[n][p] = round(sum(vals) / len(vals), 4)

    # --- reward arm: D13c REINFORCE, N=8 control vs N=32 claim, p_corr=0.9
    # sanity first: negative control — reward wired to a shifted partner must
    # NOT concentrate on the true partner (guards against wiring leakage)
    wrong = run_reinforce(32, 0, reward_partner_shift=2)
    rl = {}
    for n in RL_NS:
        reps = [run_reinforce(n, rep) for rep in range(RL_REPS)]
        rl[n] = {
            "p_corr": RL_P_CORR,
            "conc_mean": round(sum(r["conc"] for r in reps) / len(reps), 4),
            "conc_reps": [round(r["conc"], 4) for r in reps],
            "final_acc_reps": [round(r["final_acc"], 3) for r in reps],
            "updates_per_edge": round(reps[0]["updates_per_edge"], 1),
            "chance": round(1.0 / (n - 1), 4),
        }
    rl["sanity_wrong_partner_wiring_conc"] = round(wrong["conc"], 4)

    # --- pre-registered verdict
    scale_ok = corr_acc[100][0.9] >= CORR_TARGET
    noise_ok = corr_acc[8][0.6] >= CORR_TARGET
    strict_joint_ok = corr_acc[100][0.6] >= CORR_TARGET
    rl_collapses = rl[32]["conc_mean"] < RL_COLLAPSE_TARGET
    corr_ok = scale_ok and noise_ok

    if corr_ok and rl_collapses:
        verdict = "KEEP"
    elif not corr_ok:
        verdict = "KILL"
    else:
        verdict = "INCONCLUSIVE"

    p055_row = ", ".join(f"N={n}:{corr_acc[n][0.55]:.3f}" for n in N_GRID)
    note = (
        "Correlation matrix = mean partner-identification accuracy over "
        f"{REPS} reps at T_OBS={T_OBS} (chance 1/(N-1)). Deciding cells: "
        f"(N=100,p=0.9)={corr_acc[100][0.9]} (target >=0.9; doc claim 0.95), "
        f"(N=8,p=0.6)={corr_acc[8][0.6]}, strict joint (N=100,p=0.6)="
        f"{corr_acc[100][0.6]}. p_corr=0.55 row: {p055_row} (doc predicted "
        "crossing 0.5 near here). RL arm = D13c REINFORCE-with-baseline, "
        "disjoint partners, ~32 updates/edge at every N: conc at N=8 = "
        f"{rl[8]['conc_mean']} (chance {rl[8]['chance']}; D13c's published "
        f"N=8 value 0.217), conc at N=32 = {rl[32]['conc_mean']} (chance "
        f"{rl[32]['chance']}; claim <0.3). Verdict per pre-registered rule: "
        + (
            "the D13d principle GENERALIZES — correlation survives scale and "
            "noise where reward-based credit assignment collapses."
            if verdict == "KEEP"
            else "D13d was a small-N artifact — correlation also collapses at "
            "scale/under noise; principle retires."
            if verdict == "KILL"
            else "correlation held but the contrast half failed — REINFORCE "
            "did not collapse below 0.3 at N=32."
        )
    )

    result = {
        "experiment": "D18 correlation-discovery scaling (does the D13d primitive generalize?)",
        "seed": SEED,
        "corr": {
            "observations": T_OBS,
            "reps": REPS,
            "matrix_acc": corr_acc,
            "chance_acc": {n: round(1.0 / (n - 1), 4) for n in N_GRID},
        },
        "rl_reinforce_d13c": rl,
        "criteria": {
            "corr_scale_ok_N100_p090": scale_ok,
            "corr_noise_ok_N8_p060": noise_ok,
            "strict_joint_ok_N100_p060": strict_joint_ok,
            "reinforce_collapses_N32": rl_collapses,
        },
        "verdict": verdict,
        "note": note,
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
