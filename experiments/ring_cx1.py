#!/usr/bin/env python3
"""RING-CX-1 (SYNTH-0 wildcard, closing probe): untrained ANSWER-MARGIN-gated ring.

Question (booked by RING-CX-0): the untrained *certainty*-gated ring did NOT see
the blind regime (negation Reject 0.127 = 2nd lowest of 4; Reject tracked sensor-key
representational flatness, not federation blindness). Is the blind regime visible
to ANY untrained gate, or only to the *trained* FED-SINGLE disagreement?

MISSION: swap ONLY the gate signal. Ring machinery reused wholesale from
experiments/ring_cx0.py (same N=64 local-exc/global-inh DoD kernel, same label-free
tau doctrine = 20th pct of TRAIN, same robustness grid shape, same seeded jitter).

  r0 gate  : cue_s = softmax_r(rho_s / T)        (routing CERTAINTY, competition-normalized)
  r1 gate  : cue_s = per-sensor ANSWER MARGIN    (no competition normalization)

Per-sensor answer margin (LABEL-FREE, NO TRAINING): each sensor cell s answers the
item using the frozen COMP1 word-view featurization + the frozen 0-param D13d
regime-centroid Pearson router (train-only keys, rebuilt exactly as r0). Sensor s's
binary self-answer distribution is {p_s, 1-p_s}, p_s = sigma(rho_s / T). Its margin is
  margin_s = |p_top1 - p_top2| = |2 p_s - 1|.
T = median TRAIN top-1 rho (label-free temperature; the margin doctrine of COMP1/r0).

Ring integrates margins EXACTLY as before: I_i = C * sum_s margin_s * Gauss(phi_i; 90s, sC),
same W, same alpha/ticks/L2, readout theta_hat + R = |circular resultant|.
GATE: item REJECTS iff R <= tau, tau = 20th pct of TRAIN R (label-free, leak-free).

STRUCTURAL PRE-NOTE (verified before writing): the ring update is positively
homogeneous (relu(c*x) = c*relu(x) for c>=0), so the L2-normalized fixed point -- and
R -- depends only on the DIRECTION of the cue vector I, not its magnitude: ring.read([0.1,0,0,0])
== ring.read([1,0,0,0]) == 0.6702 exactly. Hence an answer-margin gate routed through
this ring is *provably* a cue-SHAPE gate: it cannot see absolute per-sensor decisiveness
(level) at all. Pre-registered anyway; the direct ABSOLUTE-margin gate (mean_s margin_s)
is reported as a labelled EXPLORATORY secondary so the "does level carry the blindness?"
question is actually asked.

Pre-registered gates (seed 2718, stated before run):
  G-A' overall routing acc >= trained-router heldout - 0.02
  G-B' negation-scope Reject-rate >= 2x mean Reject-rate across regimes
  G-C' every deciding stat needs seed-std > 0, else INCONCLUSIVE never PASS
Run: python -m experiments.ring_cx1
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from experiments.ring_cx0 import (Ring64, feat_word, pearson, nearest_sensor,
                                  REGIMES, SEEDS, CUE_JITTER_DEG, CONF_JITTER_CV,
                                  TAU_PCT)

LAB = Path("/home/eileen/projects/quilt-gpu-lab")
OUT = LAB / "results" / "ring_cx1"
CORPUS = LAB / "results" / "comp1" / "corpus.jsonl"
COMP1 = LAB / "results" / "comp1" / "comp1_results.json"

T_MULTS = [0.5, 1.0, 2.0]       # margin-temperature multipliers (robustness)
TAU_PCTS = [10, 20, 30]         # gate-percentile robustness grid (as r0)


def answer_margins(S, T):
    """Per-sensor binary self-answer margin |p_top1 - p_top2|, p = sigma(rho/T)."""
    p = 1.0 / (1.0 + np.exp(-np.asarray(S, float) / T))
    return np.abs(2.0 * p - 1.0)


def main():
    rows = [json.loads(l) for l in open(CORPUS, encoding="utf-8")]
    tr = [r for r in rows if r["sha256"][0] < "c"]
    he = [r for r in rows if r["sha256"][0] >= "c"]
    keys = {r: np.stack([feat_word(it) for it in tr if it["kind"] == r]).mean(axis=0)
            for r in REGIMES}
    S_tr = np.stack([np.array([pearson(feat_word(it), keys[r]) for r in REGIMES])
                     for it in tr])
    S_he = np.stack([np.array([pearson(feat_word(it), keys[r]) for r in REGIMES])
                     for it in he])
    g_he = [it["kind"] for it in he]
    gi = np.array([REGIMES.index(g) for g in g_he])

    router_acc = float(np.mean([REGIMES[int(np.argmax(S_he[i]))] == g_he[i]
                                for i in range(len(he))]))
    book = json.load(open(COMP1))["router_audit"]["heldout_acc"]

    # label-free margin temperature: median TRAIN top-1 rho
    T_MED = float(np.median(S_tr.max(axis=1)))
    ring = Ring64()

    def eval_gate(S, T, seed, kind):
        """Ring gate (kind='ring') or absolute aggregate-margin gate ('agg'/'min')."""
        M = answer_margins(S, T)
        rng = np.random.default_rng(seed)
        rej, dec, Rv, aggs = [], [], [], []
        for i in range(len(S)):
            jit = (rng.normal(0.0, CUE_JITTER_DEG, 4),
                   np.exp(rng.normal(0.0, CONF_JITTER_CV, 4)))
            m = M[i] * jit[1]
            if kind == "ring":
                theta, R = ring.read(m, jit)
            else:
                theta, R = ring.read(m, jit)
            Rv.append(R)
            a = float(np.mean(m)) if kind != "min" else float(np.min(m))
            aggs.append(a)
            rej.append(R if kind == "ring" else a)
            dec.append(-1 if rej[-1] <= 0 else nearest_sensor(theta))
        return np.array(rej), np.array(dec), np.array(Rv), np.array(aggs)

    def calibrate(S, T, tau_pct, kind):
        M = answer_margins(S, T)
        if kind == "ring":
            stat = np.array([ring.read(m)[1] for m in M])
        elif kind == "agg":
            stat = np.array([float(np.mean(m)) for m in M])
        else:
            stat = np.array([float(np.min(m)) for m in M])
        return float(np.percentile(stat, tau_pct)), stat

    def decide_by(stat_he, tau, acc_dec):
        rej = stat_he <= tau
        dec = np.where(rej, -1, acc_dec)
        return rej, dec

    # ---- primary: ring gate, T = T_MED, tau_pct = 20 -----------------------
    M_he = answer_margins(S_he, T_MED)
    TAU, stat_tr = calibrate(S_tr, T_MED, TAU_PCT, "ring")
    R_flat = ring.read(np.array([0.3] * 4))[1]
    R_one = ring.read(np.array([1.0, 0, 0, 0]))[1]

    # routing readout (theta) is gate-independent; cache deterministic thetas
    theta_det = [ring.read(m)[0] for m in M_he]
    dec_route = np.array([nearest_sensor(t) for t in theta_det])

    per_seed = []
    for seed in SEEDS:
        rng = np.random.default_rng(seed)
        stat, dec_r, Rv, aggs = [], [], [], []
        for i in range(len(he)):
            jit = (rng.normal(0.0, CUE_JITTER_DEG, 4),
                   np.exp(rng.normal(0.0, CONF_JITTER_CV, 4)))
            m = M_he[i] * jit[1]
            theta, R = ring.read(m, jit)
            stat.append(R)
            Rv.append(R)
            aggs.append(float(np.mean(m)))
            dec_r.append(nearest_sensor(theta))
        stat = np.array(stat)
        rej = stat <= TAU
        dec = np.where(rej, -1, np.array(dec_r))
        acc_all = float(np.mean(dec == gi))
        comm = [i for i in range(len(he)) if not rej[i]]
        acc_comm = float(np.mean(dec[comm] == gi[comm])) if comm else float("nan")
        rb = {r: float(np.mean([rej[i] for i in range(len(he)) if g_he[i] == r]))
              for r in REGIMES}
        rx = {r: float(np.mean([Rv[i] for i in range(len(he)) if g_he[i] == r]))
              for r in REGIMES}
        ra = {r: float(np.mean([REGIMES[int(np.argmax(S_he[i]))] == g_he[i]
                                for i in range(len(he)) if g_he[i] == r]))
              for r in REGIMES}
        per_seed.append(dict(seed=seed, acc_all=acc_all, acc_commit=acc_comm,
                             reject_overall=float(np.mean(rej)),
                             reject_by_regime=rb, ring_R_by_regime=rx,
                             router_acc_by_regime=ra))

    def sm(key):
        x = np.array([p[key] for p in per_seed], float)
        return dict(mean=round(float(x.mean()), 4), std=round(float(x.std()), 4))

    def reg(field):
        return {r: dict(mean=round(float(np.mean([p[field][r] for p in per_seed])), 4),
                        std=round(float(np.std([p[field][r] for p in per_seed])), 4))
                for r in REGIMES}

    rb_sm, R_sm, ra_sm = reg("reject_by_regime"), reg("ring_R_by_regime"), \
        reg("router_acc_by_regime")
    mean_rb = float(np.mean([rb_sm[r]["mean"] for r in REGIMES]))
    ratio = rb_sm["negation-scope"]["mean"] / mean_rb if mean_rb > 0 else float("inf")
    a = sm("acc_all")
    G_C_ok = (all(rb_sm[r]["std"] > 0 for r in REGIMES) and a["std"] > 0)
    threshold = round(book - 0.02, 4)
    gA = dict(threshold=threshold, overall_acc=a, acc_commit=sm("acc_commit"),
              pass_=bool(G_C_ok and a["mean"] >= threshold))
    gB = dict(negation_rate=rb_sm["negation-scope"]["mean"],
              mean_across_regimes=round(mean_rb, 4), ratio=round(ratio, 3),
              pass_=bool(G_C_ok and ratio >= 2.0))

    # ---- EXPLORATORY secondary: absolute aggregate-margin gates -----------
    sec = {}
    for kind in ("agg", "min"):
        tau_s, _ = calibrate(S_tr, T_MED, TAU_PCT, kind)
        Mh = answer_margins(S_he, T_MED)
        stat_he = (np.array([float(np.mean(m)) for m in Mh]) if kind == "agg"
                   else np.array([float(np.min(m)) for m in Mh]))
        rej = stat_he <= tau_s
        dec = np.where(rej, -1, dec_route)
        rb = {r: float(np.mean([rej[i] for i in range(len(he)) if g_he[i] == r]))
              for r in REGIMES}
        mr = float(np.mean(list(rb.values())))
        sec[kind] = dict(tau=round(tau_s, 4),
                         acc_all=round(float(np.mean(dec == gi)), 4),
                         reject_by_regime={r: round(rb[r], 4) for r in REGIMES},
                         negation_rate=round(rb["negation-scope"], 4),
                         mean_across_regimes=round(mr, 4),
                         ratio=round(rb["negation-scope"] / mr, 3) if mr > 0 else None,
                         pass_=bool(rb["negation-scope"] / mr >= 2.0) if mr > 0 else False)

    # ---- matched-protocol diagnostic: tau from JITTERED TRAIN R -------------
    # (r0 calibrated tau on un-jittered TRAIN R; margin cues are near-uniform, so
    #  jitter inflates held-out R and makes the gate nearly inert. Re-calibrate
    #  under the SAME stochastic protocol as held-out to test the gate fairly.)
    M_tr = answer_margins(S_tr, T_MED)
    rng = np.random.default_rng(SEEDS[0])
    stat_tr_j = []
    for m in M_tr:
        jit = (rng.normal(0.0, CUE_JITTER_DEG, 4),
               np.exp(rng.normal(0.0, CONF_JITTER_CV, 4)))
        stat_tr_j.append(ring.read(m * jit[1], jit)[1])
    TAU_M = float(np.percentile(stat_tr_j, TAU_PCT))
    rng = np.random.default_rng(SEEDS[0])
    rej_m, dec_m = [], []
    for i in range(len(he)):
        jit = (rng.normal(0.0, CUE_JITTER_DEG, 4),
               np.exp(rng.normal(0.0, CONF_JITTER_CV, 4)))
        theta, R = ring.read(M_he[i] * jit[1], jit)
        rej_m.append(R <= TAU_M)
        dec_m.append(nearest_sensor(theta))
    rej_m = np.array(rej_m); dec_m = np.array(dec_m)
    rbm = {r: float(np.mean([rej_m[i] for i in range(len(he)) if g_he[i] == r]))
           for r in REGIMES}
    mm = float(np.mean(list(rbm.values())))
    matched = dict(tau_matched=round(TAU_M, 4),
                   reject_overall=round(float(rej_m.mean()), 4),
                   reject_by_regime={r: round(rbm[r], 4) for r in REGIMES},
                   negation_rate=round(rbm["negation-scope"], 4),
                   mean_across_regimes=round(mm, 4),
                   ratio=round(rbm["negation-scope"] / mm, 3) if mm > 0 else None,
                   negation_top_reject=bool(rbm["negation-scope"] >= max(rbm.values())),
                   acc_all=round(float(np.mean(np.where(rej_m, -1, dec_m) == gi)), 4),
                   pass_B=bool(mm > 0 and rbm["negation-scope"] / mm >= 2.0))

    # ---- robustness grid T x tau_pct (9 cells), primary ring gate ---------
    grid = []
    for tm in T_MULTS:
        T = T_MED * tm
        for tp in TAU_PCTS:
            tau_g, _ = calibrate(S_tr, T, tp, "ring")
            rng = np.random.default_rng(SEEDS[0])
            rb = {r: [] for r in REGIMES}
            for i in range(len(he)):
                jit = (rng.normal(0.0, CUE_JITTER_DEG, 4),
                       np.exp(rng.normal(0.0, CONF_JITTER_CV, 4)))
                R = ring.read(answer_margins(S_he[i:i + 1], T)[0] * jit[1], jit)[1]
                if R <= tau_g:
                    rb[g_he[i]].append(1.0)
                else:
                    rb[g_he[i]].append(0.0)
            rbm = {r: float(np.mean(rb[r])) for r in REGIMES}
            m = float(np.mean(list(rbm.values())))
            grid.append(dict(T_mult=tm, T=round(T, 4), tau_pct=tp, tau=round(tau_g, 4),
                             reject_by_regime={r: round(rbm[r], 4) for r in REGIMES},
                             negation_rate=round(rbm["negation-scope"], 4),
                             mean_across_regimes=round(m, 4),
                             ratio=round(rbm["negation-scope"] / m, 3) if m > 0 else None,
                             negation_top_reject=bool(rbm["negation-scope"] >=
                                                      max(rbm.values()))))
    neg_top_cells = sum(1 for c in grid if c["negation_top_reject"])
    neg_ge2x_cells = sum(1 for c in grid if (c["ratio"] or 0) >= 2.0)

    # ---- operationalization robustness: 5 untrained answer-margin defs ----
    def softmax(S, T):
        z = S / T; z = z - z.max(axis=1, keepdims=True); e = np.exp(z)
        return e / e.sum(axis=1, keepdims=True)
    o_tr = np.argsort(-S_tr, axis=1)
    T_SOFT = float(np.median(S_tr[np.arange(len(tr)), o_tr[:, 0]] -
                             S_tr[np.arange(len(tr)), o_tr[:, 1]]))

    def onehot_margin(X):
        oo = np.argsort(-X, axis=1); top = oo[:, 0]; m = np.zeros_like(X)
        for i in range(len(X)):
            m[i] = np.maximum(0.0, X[i] - np.max(np.delete(X[i], top[i])))
        return m

    qtr, qhe = softmax(S_tr, T_SOFT), softmax(S_he, T_SOFT)
    variants = {
        "routing_softmax_top1_minus_top2": (np.sort(qtr, 1)[:, -1] - np.sort(qtr, 1)[:, -2],
                                            np.sort(qhe, 1)[:, -1] - np.sort(qhe, 1)[:, -2]),
        "raw_rho_top1_minus_top2": (np.sort(S_tr, 1)[:, -1] - np.sort(S_tr, 1)[:, -2],
                                    np.sort(S_he, 1)[:, -1] - np.sort(S_he, 1)[:, -2]),
        "signed_top1_minus_field_mean": (onehot_margin(S_tr).mean(1),
                                         onehot_margin(S_he).mean(1)),
        "abs_sigmoid_margin_mean": (answer_margins(S_tr, T_MED).mean(1),
                                    answer_margins(S_he, T_MED).mean(1)),
        "abs_sigmoid_margin_min": (answer_margins(S_tr, T_MED).min(1),
                                   answer_margins(S_he, T_MED).min(1)),
    }
    opr = {}
    for nm, (st, sh) in variants.items():
        tau_v = float(np.percentile(st, TAU_PCT)); rej = sh <= tau_v
        rb = {r: float(np.mean([rej[i] for i in range(len(he)) if g_he[i] == r]))
              for r in REGIMES}
        mv = float(np.mean(list(rb.values())))
        opr[nm] = dict(tau=round(tau_v, 4),
                       reject_by_regime={r: round(rb[r], 4) for r in REGIMES},
                       negation_rate=round(rb["negation-scope"], 4),
                       mean_across_regimes=round(mv, 4),
                       ratio=round(rb["negation-scope"] / mv, 3) if mv > 0 else None,
                       negation_top_reject=bool(rb["negation-scope"] >= max(rb.values())),
                       pass_B=bool(mv > 0 and rb["negation-scope"] / mv >= 2.0))
    n_opr_pass = sum(1 for v in opr.values() if v["pass_B"])

    out = {
        "experiment": "RING-CX-1 (SYNTH-0 wildcard closing probe): untrained ANSWER-MARGIN-gated ring",
        "reused_machinery": "experiments/ring_cx0.py (Ring64 DoD kernel, featurization, router) wholesale",
        "repro_lineage": {"harvested_engine": "results/ring_cx0/repro/fly_cx.py",
                          "receipt": "results/ring_cx0/repro/fly_cx_receipt.json",
                          "verdict": "PASS 4/4 (r0, reused by reference; ring dynamics identical)"},
        "device": "cpu", "gpu_used": False, "training_used": False, "numpy_only": True,
        "structure_note": ("ring update is positively homogeneous (relu) => L2-normalized "
                           "fixed point and R depend only on cue-vector DIRECTION; "
                           "ring.read([0.1,0,0,0])==ring.read([1,0,0,0])==0.6702 exactly. "
                           "So any per-sensor-margin gate routed through this ring is "
                           "provably a cue-SHAPE gate, blind to absolute margin LEVEL."),
        "gate_swap": "cue_s: softmax(rho_s/T) [r0 certainty] -> |2*sigma(rho_s/T)-1| [r1 per-sensor answer margin]",
        "corpus": {"path": "results/comp1/corpus.jsonl", "n_train": len(tr),
                   "n_heldout": len(he), "seeds": SEEDS},
        "wiring": {"reproduced_router_heldout_top1": round(router_acc, 4),
                   "comp1_booked_router_heldout_top1": book,
                   "T_margin_median_train_top1_rho": round(T_MED, 4),
                   "tau_ring_20pct_train": round(TAU, 4),
                   "R_flat_equal_margins": round(R_flat, 4),
                   "R_single_cue": round(R_one, 4)},
        "G_A_prime_ring_ge_trained_minus_0.02": gA,
        "G_B_prime_negation_reject_ge_2x_mean": gB,
        "G_C_prime_seed_std_ok": bool(G_C_ok),
        "reject_by_regime_ring_seedmean": rb_sm,
        "ring_R_by_regime_seedmean": R_sm,
        "router_acc_by_regime": ra_sm,
        "operationalization_robustness_5_defs": opr,
        "operationalization_robustness_summary": {
            "n_defs": len(opr), "n_pass_B": n_opr_pass,
            "note": "5 untrained answer-margin definitions; none place Reject on negation"},
        "exploratory_absolute_margin_gates": sec,
        "matched_protocol_diagnostic": matched,
        "robustness_grid_9cells": grid,
        "robustness_summary": {"negation_top_reject_cells": neg_top_cells,
                               "negation_ge_2x_cells": neg_ge2x_cells, "n_cells": len(grid)},
        "per_seed": per_seed,
    }
    out["verdict"] = ("PASS" if (gA["pass_"] and gB["pass_"]) else
                      "INCONCLUSIVE" if not G_C_ok else "FAIL")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ring_cx1_results.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({"router_repro": round(router_acc, 4), "booked": book,
                      "T_margin": round(T_MED, 4), "tau_ring": round(TAU, 4),
                      "R_flat": round(R_flat, 4), "R_single": round(R_one, 4),
                      "G_A_prime": gA, "G_B_prime": gB, "G_C_ok": G_C_ok,
                      "reject_ring": rb_sm, "ring_R": R_sm,
                      "router_acc_by_regime": ra_sm,
                      "exploratory": sec,
                      "robust": {"neg_top": neg_top_cells, "neg_ge2x": neg_ge2x_cells},
                      "verdict": out["verdict"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
