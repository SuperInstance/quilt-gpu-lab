#!/usr/bin/env python3
"""RING-CX-2 (SYNTH-0 wildcard trilogy, FINAL probe): CHEAP TRAINED gate.

Booked by RING-CX-1 (thread closed negative): only the *trained* FED-SINGLE
disagreement sees the blind regime; every untrained gate is a corpus-geometry
function (wrong axis); the ring's relu homogeneity makes any margin gate through
it provably a SHAPE gate (scale-invariant, blind to margin LEVEL).

OPEN QUESTION (booked): is the blindness reachable by a CHEAP TRAINED gate --
does cheapness live in the GATE, not the geometry?

MISSION
 (1) REUSE experiments/ring_cx1.py harness: COMP1 word-view featurization
     (sha1 BoW D=64, L2) + frozen 0-param regime-centroid Pearson router
     (held-out top-1 must reproduce 0.7356) + regime labels.
 (2) TRAIN three tiny gates (sklearn LogisticRegression + StandardScaler,
     seed 2718, TRAIN split only).  Gate target = BLINDNESS ALERT
     (1 iff held item's regime == the blind regime, negation-scope).  Features:
       (a) a_margins  : the 4 per-sensor answer margins |2 sigma(rho_s/T)-1|
       (b) b_disagree : the 2-arm FED-SINGLE disagreement feature (per item)
       (c) c_both     : margins + disagreement (5 features)
 (3) PRE-REGISTERED GATES (seed 2718, stated before run):
       G-T1 negation alert-rate >= 2x regime-mean alert-rate   (== G-B/G-B' headline)
       G-T2 alert precision on negation >= 0.5
       G-T3 train -> held-out AUC degradation <= 0.10 absolute (no overfit mirage)
       G-T4 std > 0 over 5 bootstrap refits (frost law: else INCONCLUSIVE never PASS)
 (4) REPORT which feature set carries the signal + winner param count.

CHEAP TWO-ARM BUILD (all CPU, sklearn logistic, TRAIN-only, seed 2718)
  SINGLE arm : one binary logistic on the 64-dim COMP1 word view -> P(canon).
  FED arm    : 4 per-regime binary logistic "cells" (each fit on that regime's
               TRAIN items) selected per item by the SAME frozen 0-param
               centroid-Pearson router.  FED read = selected cell's P(canon).
  Disagreement (primary) d_ans = 1[FED answer != SINGLE answer];
    sensitivities d_conf = p_fed - p_single; d_corr = 1[FED correct] - 1[SINGLE correct].
  Whole 2-arm bank = 325 params (65 + 4*65) vs COMP1's FED 4228p / GPU.
CONTROL: 0-param router-argmax baseline ("router's top sensor == negation sensor").

CPU-only, numpy+sklearn, 0 Wh, no GPU, no torch.  Run: python -m experiments.ring_cx2
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from experiments.ring_cx0 import feat_word, pearson, REGIMES

LAB = Path("/home/eileen/projects/quilt-gpu-lab")
OUT = LAB / "results" / "ring_cx2"
CORPUS = LAB / "results" / "comp1" / "corpus.jsonl"
COMP1 = LAB / "results" / "comp1" / "comp1_results.json"

SEED = 2718
BLIND = "negation-scope"


def answer_margins(S, T):
    p = 1.0 / (1.0 + np.exp(-np.asarray(S, float) / T))
    return np.abs(2.0 * p - 1.0)


def fit_gate(X, y):
    return make_pipeline(StandardScaler(),
                         LogisticRegression(random_state=SEED, max_iter=5000)).fit(X, y)


def main():
    rows = [json.loads(l) for l in open(CORPUS, encoding="utf-8")]
    tr = [r for r in rows if r["sha256"][0] < "c"]
    he = [r for r in rows if r["sha256"][0] >= "c"]
    keys = {r: np.stack([feat_word(it) for it in tr if it["kind"] == r]).mean(axis=0)
            for r in REGIMES}
    Xw_tr = np.stack([feat_word(it) for it in tr])
    Xw_he = np.stack([feat_word(it) for it in he])
    S_tr = np.stack([np.array([pearson(Xw_tr[i], keys[r]) for r in REGIMES])
                     for i in range(len(tr))])
    S_he = np.stack([np.array([pearson(Xw_he[i], keys[r]) for r in REGIMES])
                     for i in range(len(he))])
    g_tr = [it["kind"] for it in tr]
    g_he = [it["kind"] for it in he]

    # wiring bill of health: reproduce COMP1's booked router held-out top-1
    router_acc = float(np.mean([REGIMES[int(np.argmax(S_he[i]))] == g_he[i]
                                for i in range(len(he))]))
    book = json.load(open(COMP1))["router_audit"]["heldout_acc"]

    # ---- COMP1 word-view margins (ring_cx1 doctrine, label-free T) ----------
    T_MED = float(np.median(S_tr.max(axis=1)))
    M_tr, M_he = answer_margins(S_tr, T_MED), answer_margins(S_he, T_MED)

    # ---- CHEAP TWO-ARM BUILD (TRAIN-only, seed 2718) ------------------------
    y_tr = np.array([it["label"] == "canon" for it in tr], float)
    y_he = np.array([it["label"] == "canon" for it in he], float)
    single = fit_gate(Xw_tr, y_tr)
    p_single_tr, p_single_he = single.predict_proba(Xw_tr)[:, 1], \
        single.predict_proba(Xw_he)[:, 1]
    rt_tr, rt_he = np.argmax(S_tr, axis=1), np.argmax(S_he, axis=1)
    p_fed_tr, p_fed_he = np.zeros(len(tr)), np.zeros(len(he))
    for ri, r in enumerate(REGIMES):
        idx = [i for i in range(len(tr)) if g_tr[i] == r]
        cell = fit_gate(Xw_tr[idx], y_tr[idx])
        sel_tr, sel_he = rt_tr == ri, rt_he == ri
        if sel_tr.any():
            p_fed_tr[sel_tr] = cell.predict_proba(Xw_tr[sel_tr])[:, 1]
        if sel_he.any():
            p_fed_he[sel_he] = cell.predict_proba(Xw_he[sel_he])[:, 1]
    two_arm_params = 65 + 4 * 65

    def disagree(pf, ps, y):
        return {"d_ans": ((pf >= .5) != (ps >= .5)).astype(float),
                "d_conf": pf - ps,
                "d_corr": ((pf >= .5) == (y == 1)).astype(float)
                          - ((ps >= .5) == (y == 1)).astype(float)}
    D_tr = disagree(p_fed_tr, p_single_tr, y_tr)
    D_he = disagree(p_fed_he, p_single_he, y_he)

    arm = {"SINGLE_acc_heldout": round(float(np.mean((p_single_he >= .5) == (y_he == 1))), 4),
           "FED_acc_heldout": round(float(np.mean((p_fed_he >= .5) == (y_he == 1))), 4)}
    for r in REGIMES:
        s = [i for i in range(len(he)) if g_he[i] == r]
        arm[f"SINGLE_acc@{r}"] = round(float(np.mean([(p_single_he[i] >= .5) == (y_he[i] == 1)
                                                      for i in s])), 4)
        arm[f"FED_acc@{r}"] = round(float(np.mean([(p_fed_he[i] >= .5) == (y_he[i] == 1)
                                                   for i in s])), 4)

    # ---- gate target: blindness alert ---------------------------------------
    t_tr = np.array([g == BLIND for g in g_tr], float)
    t_he = np.array([g == BLIND for g in g_he], float)

    FEATS = {"a_margins": (M_tr, M_he),
             "b_disagree": (D_tr["d_ans"][:, None], D_he["d_ans"][:, None]),
             "c_both": (np.column_stack([M_tr, D_tr["d_ans"]]),
                        np.column_stack([M_he, D_he["d_ans"]]))}
    PARAMS = {k: int(v[0].shape[1] + 1) for k, v in FEATS.items()}

    def evaluate(Xtr, Xhe, boot=False, rng=None):
        if boot:
            idx = rng.integers(0, len(Xtr), len(Xtr))
            Xtr, ytr_b, ttr_b = Xtr[idx], y_tr[idx], t_tr[idx]
        else:
            ytr_b, ttr_b = y_tr, t_tr
        g = fit_gate(Xtr, ttr_b)
        p_he = g.predict_proba(Xhe)[:, 1]
        p_tr = g.predict_proba(Xtr)[:, 1]
        alert = p_he >= 0.5
        rates = {r: float(np.mean([alert[i] for i in range(len(he)) if g_he[i] == r]))
                 for r in REGIMES}
        mean_rate = float(np.mean(list(rates.values())))
        tp = int(np.sum(alert & (t_he == 1)))
        fp = int(np.sum(alert & (t_he == 0)))
        prec = tp / (tp + fp) if (tp + fp) > 0 else float("nan")
        ratio = rates[BLIND] / mean_rate if mean_rate > 0 else float("nan")
        auc_he = float(roc_auc_score(t_he, p_he))
        auc_tr = float(roc_auc_score(ttr_b, p_tr))
        return dict(alert_by_regime={r: round(rates[r], 4) for r in REGIMES},
                    negation_rate=round(rates[BLIND], 4), mean_rate=round(mean_rate, 4),
                    ratio=round(ratio, 3) if mean_rate > 0 else None,
                    n_alerts=int(alert.sum()),
                    precision_negation=round(prec, 4) if (tp + fp) > 0 else None,
                    auc_heldout=round(auc_he, 4), auc_train=round(auc_tr, 4),
                    degradation=round(auc_tr - auc_he, 4))

    gates = {}
    for name, (Xtr, Xhe) in FEATS.items():
        ev = evaluate(Xtr, Xhe)
        rng = np.random.default_rng(SEED)
        bs = [evaluate(Xtr, Xhe, boot=True, rng=rng) for _ in range(5)]
        std_neg = float(np.std([b["negation_rate"] for b in bs]))
        std_ratio = float(np.std([b["ratio"] for b in bs if b["ratio"] is not None]))
        std_auc = float(np.std([b["auc_heldout"] for b in bs]))
        G1 = bool(ev["ratio"] is not None and ev["ratio"] >= 2.0)
        G2 = bool(ev["precision_negation"] is not None and ev["precision_negation"] >= 0.5)
        G3 = bool(ev["degradation"] <= 0.10)
        G4 = bool(std_neg > 0 and std_auc > 0 and (std_ratio > 0 or not bs))
        gates[name] = dict(n_features=int(Xtr.shape[1]), n_params=PARAMS[name], **ev,
                           G_T1=dict(negation_rate=ev["negation_rate"],
                                     mean_rate=ev["mean_rate"], ratio=ev["ratio"], pass_=G1),
                           G_T2=dict(precision_negation=ev["precision_negation"], pass_=G2),
                           G_T3=dict(auc_train=ev["auc_train"], auc_heldout=ev["auc_heldout"],
                                     degradation=ev["degradation"], pass_=G3),
                           G_T4=dict(boot_std_negation_rate=round(std_neg, 4),
                                     boot_std_ratio=round(std_ratio, 4),
                                     boot_std_auc=round(std_auc, 4),
                                     boot_negation_rates=[b["negation_rate"] for b in bs],
                                     pass_=G4),
                           verdict=("PASS" if (G1 and G2 and G3 and G4)
                                    else "INCONCLUSIVE" if not G4 else "FAIL"))
        print(f"{name}: {gates[name]['verdict']} "
              f"T1(ratio={ev['ratio']},{G1}) T2(prec={ev['precision_negation']},{G2}) "
              f"T3(deg={ev['degradation']},{G3}) T4(std={round(std_neg, 4)},{G4})")

    # ---- secondary protocol: prevalence-matched threshold (house tau doctrine) --
    # alert iff held p >= TRAIN quantile at the TRAIN positive rate (label-free
    # w.r.t. held-out; COMP1's tau = pct-of-TRAIN doctrine).  Fixes the degenerate
    # 0.5-threshold calibration of weak features so EVERY feature set gets alerted.
    q = float(np.mean(t_tr))
    pmatch = {}
    for name, (Xtr, Xhe) in FEATS.items():
        g = fit_gate(Xtr, t_tr)
        thr = float(np.quantile(g.predict_proba(Xtr)[:, 1], 1.0 - q))
        alert = g.predict_proba(Xhe)[:, 1] >= thr
        rates = {r: float(np.mean([alert[i] for i in range(len(he)) if g_he[i] == r]))
                 for r in REGIMES}
        m = float(np.mean(list(rates.values())))
        tp = int(np.sum(alert & (t_he == 1))); fp = int(np.sum(alert & (t_he == 0)))
        pmatch[name] = dict(threshold=round(thr, 4), alert_rate=round(float(alert.mean()), 4),
                            alert_by_regime={r: round(rates[r], 4) for r in REGIMES},
                            negation_rate=round(rates[BLIND], 4), mean_rate=round(m, 4),
                            ratio=round(rates[BLIND] / m, 3) if m > 0 else None,
                            precision_negation=(round(tp / (tp + fp), 4)
                                                if (tp + fp) > 0 else None),
                            pass_T1_T2=bool(m > 0 and rates[BLIND] / m >= 2.0 and
                                            (tp + fp) > 0 and tp / (tp + fp) >= 0.5))

    # ---- 0-param control: router-argmax == negation sensor ------------------
    ra = rt_he == REGIMES.index(BLIND)
    rr = {r: float(np.mean([ra[i] for i in range(len(he)) if g_he[i] == r]))
          for r in REGIMES}
    mrr = float(np.mean(list(rr.values())))
    tp = int(np.sum(ra & (t_he == 1))); fp = int(np.sum(ra & (t_he == 0)))
    baseline = dict(alert_by_regime={r: round(rr[r], 4) for r in REGIMES},
                    negation_rate=round(rr[BLIND], 4), mean_rate=round(mrr, 4),
                    ratio=round(rr[BLIND] / mrr, 3) if mrr > 0 else None,
                    precision_negation=round(tp / (tp + fp), 4))
    print("router-argmax baseline:", baseline)

    # ---- disagreement-definition sensitivity + correlation w/ blindness -----
    sens, corr = {}, {}
    for dname in ("d_ans", "d_conf", "d_corr"):
        g = fit_gate(D_tr[dname][:, None], t_tr)
        alert = g.predict_proba(D_he[dname][:, None])[:, 1] >= 0.5
        rates = {r: float(np.mean([alert[i] for i in range(len(he)) if g_he[i] == r]))
                 for r in REGIMES}
        m = float(np.mean(list(rates.values())))
        sens[dname] = dict(negation_rate=round(rates[BLIND], 4), mean_rate=round(m, 4),
                           ratio=round(rates[BLIND] / m, 3) if m > 0 else None,
                           auc_heldout=round(float(roc_auc_score(t_he, g.predict_proba(
                               D_he[dname][:, None])[:, 1])), 4))
        corr[dname] = round(float(np.corrcoef(D_he[dname], t_he)[0, 1]), 4)
    corr["a_margins_mean"] = round(float(np.corrcoef(M_he.mean(1), t_he)[0, 1]), 4)
    corr["a_margins_max"] = round(float(np.corrcoef(M_he.max(1), t_he)[0, 1]), 4)
    dis_by_regime = {dname: {r: round(float(D_he[dname][[i for i in range(len(he))
                                                             if g_he[i] == r]].mean()), 4)
                             for r in REGIMES} for dname in ("d_ans", "d_corr")}

    winner = min((k for k, v in gates.items() if v["verdict"] == "PASS"),
                 key=lambda k: gates[k]["n_params"], default=None)
    n_pass = sum(1 for v in gates.values() if v["verdict"] == "PASS")
    out = {
        "experiment": "RING-CX-2 (SYNTH-0 wildcard trilogy, FINAL): cheap TRAINED gate on COMP1 corpus",
        "reused_machinery": "experiments/ring_cx0.py (featurization/router) + ring_cx1 answer-margin doctrine",
        "device": "cpu", "gpu_used": False, "torch_used": False, "numpy_sklearn": True,
        "seed": SEED, "blind_regime": BLIND,
        "corpus": {"path": "results/comp1/corpus.jsonl", "n_train": len(tr),
                   "n_heldout": len(he), "negation_heldout": int(t_he.sum()),
                   "negation_frac_heldout": round(float(t_he.mean()), 4)},
        "wiring": {"reproduced_router_heldout_top1": round(router_acc, 4),
                   "comp1_booked_router_heldout_top1": book,
                   "match": bool(abs(router_acc - book) < 1e-9),
                   "T_margin_median_train_top1_rho": round(T_MED, 4)},
        "cheap_two_arm": {"SINGLE": "1 logistic on 64-dim word view",
                          "FED": "4 per-regime logistic cells + frozen 0-param router",
                          "two_arm_params": two_arm_params, "accuracy": arm},
        "gate_target": f"blindness alert = 1 iff regime == {BLIND}",
        "params": PARAMS, "gates": gates,
        "prevalence_matched_protocol": pmatch,
        "control_router_argmax_baseline": baseline,
        "disagreement_definition_sensitivity": sens,
        "disagreement_by_regime": dis_by_regime,
        "feature_corr_with_blindness_heldout": corr,
        "which_feature_set_carries_signal": {k: gates[k]["verdict"] for k in gates},
        "winner_cheapest_pass": winner,
        "prior": {"ring_cx0": "untrained certainty gate FAIL (neg Reject 0.127)",
                  "ring_cx1": "untrained margin gate FAIL (ratio 0.789); ring relu-homogeneous"},
    }
    out["verdict"] = ("PASS" if n_pass >= 1 else
                      "INCONCLUSIVE" if not all(gates[k]["G_T4"]["pass_"] for k in gates)
                      else "FAIL")
    out["summary"] = {"n_gate_feature_sets": len(gates), "n_pass": n_pass,
                      "headline": ("cheap trained gate reaches the blind regime"
                                   if n_pass >= 1 else
                                   "no cheap trained gate reaches the blind regime")}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ring_cx2_results.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({"router_repro": round(router_acc, 4), "booked": book,
                      "two_arm_params": two_arm_params, "verdict": out["verdict"],
                      "winner": winner, "params": PARAMS,
                      "verdicts": {k: gates[k]["verdict"] for k in gates},
                      "baseline": baseline, "corr": corr,
                      "two_arm_negation": {k: v for k, v in arm.items()
                                           if "negation" in k}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
