#!/usr/bin/env python3
"""LANE CX-CHEAP-0 (follow-through from RING-CX-2 trilogy closure).

TWO BOOKED QUESTIONS:
 (Q1) Can a CHEAP gate predict the PER-ITEM FED-SINGLE accuracy win -- not the
      blind regime, the item-level answer win -- at held-out AUC >= 0.70?
 (Q2) Does the cheap 325-param logistic two-arm (which reproduced the negation
      win +0.196 vs COMP1's +0.126) make COMP1's 4228-param FED MLP unnecessary?

MISSION
 (1) REUSE experiments/ring_cx2.py harness wholesale: COMP1 word-view
     featurization (sha1 BoW D=64, L2), 4 per-sensor answer margins, 2-arm
     disagreement, frozen 0-param centroid-Pearson router (wiring check must
     reproduce booked held-out top-1 0.7356), TRAIN/held-out split discipline,
     seed 2718.
 (2) Q1 -- per-item win prediction.  label = 1[FED correct AND SINGLE wrong]
     per item.  NOTE (honest): COMP1's saved artifacts do NOT persist per-item
     per-arm predictions (comp1_results.json holds only aggregate boards/CI);
     the only derivable path is to rebuild the per-item FED/SINGLE reads from
     the SAME frozen COMP1 featurization + router + split (exactly as ring_cx2
     did).  TRAIN items fit the gate, held-out evaluates.
     Feature sets (small logistic, sklearn, seed 2718):
       f_margins  : {4 per-sensor answer margins}
       f_disagree : {2-arm disagreement d_ans, d_conf}
       f_both     : margins + disagreement
       f_oracle   : + per-sensor correctness indicators (LABEL-DEPENDENT ->
                    leaky/non-deployable; reported as an oracle upper bound)
 (3) GATES (pre-registered): G-C1 best deployable held-out AUC >= 0.70;
     G-C2 precision >= 2x base rate at the Youden point; G-C3 bootstrap std > 0
     over 5 refits (std==0 -> INCONCLUSIVE, never PASS).  Book AUC + Brier/set.
 (4) Q2 -- MLP retirement: compare the cheap 325p two-arm per-regime held-out
     accuracy vs COMP1's booked 4228p FED numbers (results/comp1/).
     Gate = per-regime |delta| <= 0.02 everywhere AND negation win >= +0.126.

CPU-only, numpy+sklearn, 0 Wh, no GPU, no torch.  Run: python -m experiments.cx_cheap0
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score, roc_curve
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from experiments.ring_cx0 import feat_word, pearson, REGIMES

LAB = Path("/home/eileen/projects/quilt-gpu-lab")
OUT = LAB / "results" / "cx_cheap0"
CORPUS = LAB / "results" / "comp1" / "corpus.jsonl"
COMP1 = LAB / "results" / "comp1" / "comp1_results.json"

SEED = 2718
BLIND = "negation-scope"
N_BOOT = 5


def answer_margins(S, T):
    p = 1.0 / (1.0 + np.exp(-np.asarray(S, float) / T))
    return np.abs(2.0 * p - 1.0)


def fit_gate(X, y):
    return make_pipeline(StandardScaler(),
                         LogisticRegression(random_state=SEED, max_iter=5000)).fit(X, y)


def youden(p, y):
    fpr, tpr, thr = roc_curve(y, p)
    j = tpr - fpr
    i = int(np.argmax(j))
    return float(thr[i]), float(tpr[i]), float(fpr[i]), float(j[i])


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

    # ---- wiring bill of health --------------------------------------------
    router_acc = float(np.mean([REGIMES[int(np.argmax(S_he[i]))] == g_he[i]
                                for i in range(len(he))]))
    comp1 = json.load(open(COMP1))
    book = comp1["router_audit"]["heldout_acc"]

    # ---- per-sensor answer margins (label-free T, ring_cx1 doctrine) --------
    T_MED = float(np.median(S_tr.max(axis=1)))
    M_tr, M_he = answer_margins(S_tr, T_MED), answer_margins(S_he, T_MED)

    # ---- cheap two-arm (325p, TRAIN-only, seed 2718) -----------------------
    y_tr = np.array([it["label"] == "canon" for it in tr], float)
    y_he = np.array([it["label"] == "canon" for it in he], float)
    single = fit_gate(Xw_tr, y_tr)
    p_single_tr, p_single_he = single.predict_proba(Xw_tr)[:, 1], \
        single.predict_proba(Xw_he)[:, 1]
    rt_tr, rt_he = np.argmax(S_tr, axis=1), np.argmax(S_he, axis=1)
    p_fed_tr, p_fed_he = np.zeros(len(tr)), np.zeros(len(he))
    # per-sensor cell predictions on ALL items (for indicators / disagreement)
    cell_pred_tr = np.zeros((len(tr), len(REGIMES)))
    cell_pred_he = np.zeros((len(he), len(REGIMES)))
    for ri, r in enumerate(REGIMES):
        idx = [i for i in range(len(tr)) if g_tr[i] == r]
        cell = fit_gate(Xw_tr[idx], y_tr[idx])
        cp_tr = (cell.predict_proba(Xw_tr)[:, 1] >= .5).astype(float)
        cp_he = (cell.predict_proba(Xw_he)[:, 1] >= .5).astype(float)
        cell_pred_tr[:, ri] = cp_tr
        cell_pred_he[:, ri] = cp_he
        sel_tr, sel_he = rt_tr == ri, rt_he == ri
        if sel_tr.any():
            p_fed_tr[sel_tr] = cell.predict_proba(Xw_tr[sel_tr])[:, 1]
        if sel_he.any():
            p_fed_he[sel_he] = cell.predict_proba(Xw_he[sel_he])[:, 1]
    two_arm_params = 65 + 4 * 65

    pred_single_tr, pred_single_he = p_single_tr >= .5, p_single_he >= .5
    pred_fed_tr, pred_fed_he = p_fed_tr >= .5, p_fed_he >= .5
    corr_single_tr, corr_single_he = (pred_single_tr == (y_tr == 1)), (pred_single_he == (y_he == 1))
    corr_fed_tr, corr_fed_he = (pred_fed_tr == (y_tr == 1)), (pred_fed_he == (y_he == 1))

    # ---- per-item win label: FED correct AND SINGLE wrong -------------------
    w_tr = (corr_fed_tr & ~corr_single_tr).astype(float)
    w_he = (corr_fed_he & ~corr_single_he).astype(float)
    base_tr, base_he = float(w_tr.mean()), float(w_he.mean())

    # ---- disagreement features ---------------------------------------------
    d_ans_tr = (pred_fed_tr != pred_single_tr).astype(float)
    d_ans_he = (pred_fed_he != pred_single_he).astype(float)
    d_conf_tr, d_conf_he = p_fed_tr - p_single_tr, p_fed_he - p_single_he

    # per-sensor correctness indicators (ORACLE -- label-dependent, leaky)
    ind_tr = np.column_stack([(cell_pred_tr[:, ri] == (y_tr == 1)).astype(float)
                              for ri in range(len(REGIMES))])
    ind_he = np.column_stack([(cell_pred_he[:, ri] == (y_he == 1)).astype(float)
                              for ri in range(len(REGIMES))])
    # deployable analogue: per-sensor disagreement with SINGLE arm
    indd_tr = np.column_stack([(cell_pred_tr[:, ri] != pred_single_tr).astype(float)
                               for ri in range(len(REGIMES))])
    indd_he = np.column_stack([(cell_pred_he[:, ri] != pred_single_he).astype(float)
                               for ri in range(len(REGIMES))])

    FEATS = {
        "f_margins":  (M_tr, M_he, "deployable"),
        "f_disagree": (np.column_stack([d_ans_tr, d_conf_tr]),
                       np.column_stack([d_ans_he, d_conf_he]), "deployable"),
        "f_both":     (np.column_stack([M_tr, d_ans_tr, d_conf_tr]),
                       np.column_stack([M_he, d_ans_he, d_conf_he]), "deployable"),
        "f_oracle":   (np.column_stack([M_tr, d_ans_tr, d_conf_tr, ind_tr]),
                       np.column_stack([M_he, d_ans_he, d_conf_he, ind_he]),
                       "ORACLE/leaky"),
    }
    probe = {"+per_sensor_disagreement (deployable)":
             (np.column_stack([M_tr, d_ans_tr, d_conf_tr, indd_tr]),
              np.column_stack([M_he, d_ans_he, d_conf_he, indd_he]), "deployable")}

    def evaluate(Xtr, Xhe, ttr=None, the=None):
        ttr = w_tr if ttr is None else ttr
        the = w_he if the is None else the
        g = fit_gate(Xtr, ttr)
        p = g.predict_proba(Xhe)[:, 1]
        auc = float(roc_auc_score(the, p))
        brier = float(brier_score_loss(the, p))
        thr, tpr, fpr, j = youden(p, the)
        alert = p >= thr
        tp = int(np.sum(alert & (the == 1))); fp = int(np.sum(alert & (the == 0)))
        prec = tp / (tp + fp) if (tp + fp) > 0 else float("nan")
        base = float(the.mean())
        return dict(auc_heldout=round(auc, 4), brier_heldout=round(brier, 4),
                    base_rate=round(base, 4),
                    youden_threshold=round(thr, 4), youden_tpr=round(tpr, 4),
                    youden_fpr=round(fpr, 4), youden_j=round(j, 4),
                    precision_at_youden=round(prec, 4) if (tp + fp) > 0 else None,
                    precision_over_base=(round(prec / base, 3) if base > 0 and (tp + fp) > 0 else None),
                    n_alert=int(alert.sum()), n_params=int(Xtr.shape[1] + 1))

    results = {}
    for name, (Xtr, Xhe, kind) in {**FEATS, **probe}.items():
        ev = evaluate(Xtr, Xhe)
        # G-C3: bootstrap std over 5 refits (resample TRAIN)
        rng = np.random.default_rng(SEED)
        b_auc, b_pr = [], []
        for _ in range(N_BOOT):
            idx = rng.integers(0, len(Xtr), len(Xtr))
            g = fit_gate(Xtr[idx], w_tr[idx])
            p = g.predict_proba(Xhe)[:, 1]
            b_auc.append(float(roc_auc_score(w_he, p)))
            thr, *_ = youden(p, w_he)
            al = p >= thr
            tp = int(np.sum(al & (w_he == 1))); fp = int(np.sum(al & (w_he == 0)))
            b_pr.append(tp / (tp + fp) if (tp + fp) > 0 else np.nan)
        std_auc = float(np.std(b_auc))
        GC1 = bool(ev["auc_heldout"] >= 0.70)
        GC2 = bool(ev["precision_over_base"] is not None and ev["precision_over_base"] >= 2.0)
        GC3 = bool(std_auc > 0)
        if not GC3:
            verdict = "INCONCLUSIVE"
        elif GC1 and GC2:
            verdict = "PASS"
        else:
            verdict = "FAIL"
        results[name] = dict(feature_kind=kind, **ev,
                             n_features=int(Xtr.shape[1]),
                             G_C1=dict(auc_heldout=ev["auc_heldout"], need=0.70, pass_=GC1),
                             G_C2=dict(precision_over_base=ev["precision_over_base"], need=2.0,
                                       pass_=GC2),
                             G_C3=dict(boot_std_auc=round(std_auc, 5),
                                       boot_aucs=[round(x, 4) for x in b_auc],
                                       pass_=GC3),
                             verdict=verdict)
        print(f"{name:<42} AUC={ev['auc_heldout']:.4f} Brier={ev['brier_heldout']:.4f} "
              f"base={ev['base_rate']:.4f} prec/base={ev['precision_over_base']} "
              f"std={std_auc:.5f} -> {verdict}")

    # ---- singular feature diagnostics (does a single feature carry it?) -----
    singles = {}
    for i, nm in enumerate(REGIMES):
        a = float(roc_auc_score(w_he, M_he[:, i]))
        singles[f"margin@{nm}"] = round(a, 4)
    singles["margin_mean"] = round(float(roc_auc_score(w_he, M_he.mean(1))), 4)
    singles["margin_max"] = round(float(roc_auc_score(w_he, M_he.max(1))), 4)
    singles["d_ans"] = round(float(roc_auc_score(w_he, d_ans_he)), 4)
    singles["d_conf"] = round(float(roc_auc_score(w_he, d_conf_he)), 4)
    singles["router_is_blind(0-param control)"] = round(
        float(roc_auc_score(w_he, (rt_he == REGIMES.index(BLIND)).astype(float))), 4)

    # ---- separation decomposition: is the win signal structural? ------------
    win = corr_fed_he & ~corr_single_he
    loss = (~corr_fed_he) & corr_single_he
    sub = d_ans_he.astype(bool)
    within = {}
    for nm, f in [("margin_mean", M_he.mean(1)), ("margin_max", M_he.max(1)),
                  ("d_conf", d_conf_he), ("fed_conf|pf-.5|", np.abs(p_fed_he - .5)),
                  ("single_conf|ps-.5|", np.abs(p_single_he - .5))]:
        within[nm] = round(float(roc_auc_score(win[sub], f[sub])), 4)
    sep = {
        "n_win": int(win.sum()), "n_loss_fed_wrong_single_right": int(loss.sum()),
        "n_disagree": int(sub.sum()), "disagree_rate": round(float(sub.mean()), 4),
        "necessary_condition_win_implies_disagree": bool(int((win & ~sub).sum()) == 0),
        "win_rate_given_disagree": round(float(win[sub].mean()), 4),
        "win_rate_given_agree": round(float(win[~sub].mean()), 4) if (~sub).any() else None,
        "within_disagreement_auc": within,
        "note": "all wins imply FED!=SINGLE (necessary condition); NO feature separates win "
                "from loss WITHIN the disagreement set (all within-set AUC ~ chance), so the "
                "high overall AUC is the necessary-condition boundary, not a per-item predictor.",
    }

    # ---- Q2: MLP retirement test -------------------------------------------
    boards = comp1["boards_seedmean"]["FED"]
    boards_single = comp1["boards_seedmean"]["SINGLE"]
    our = {}
    for r in REGIMES:
        s = [i for i in range(len(he)) if g_he[i] == r]
        our[f"FED@{r}"] = round(float(np.mean([(p_fed_he[i] >= .5) == (y_he[i] == 1)
                                               for i in s])), 4)
        our[f"SINGLE@{r}"] = round(float(np.mean([(p_single_he[i] >= .5) == (y_he[i] == 1)
                                                  for i in s])), 4)
    our["FED@full"] = round(float(np.mean(pred_fed_he == (y_he == 1))), 4)
    our["SINGLE@full"] = round(float(np.mean(pred_single_he == (y_he == 1))), 4)

    delta = {}
    for k in ["full"] + REGIMES:
        c = boards[k if k != "full" else "full"]
        delta[k] = round(our[f"FED@{k}"] - c, 4)
    neg_win_ours = round(our["FED@negation-scope"] - our["SINGLE@negation-scope"], 4)
    neg_win_comp1 = round(boards["negation-scope"] - boards_single["negation-scope"], 4)
    max_abs_delta = max(abs(v) for v in delta.values())
    Q2_pass = bool(max_abs_delta <= 0.02 and neg_win_ours >= neg_win_comp1)

    out = {
        "experiment": "CX-CHEAP-0: per-item FED-SINGLE win prediction + MLP retirement test",
        "device": "cpu", "gpu_used": False, "torch_used": False, "numpy_sklearn": True,
        "seed": SEED, "energy_wh": 0.0,
        "reused_machinery": "experiments/ring_cx2.py (COMP1 featurization, margins, disagree, router) "
                            "+ experiments/ring_cx0.py (feat_word/pearson/REGIMES)",
        "honest_note": "COMP1 artifacts do not persist per-item per-arm predictions; per-item "
                       "FED/SINGLE correctness re-derived from the SAME frozen COMP1 featurization "
                       "+ router + split (ring_cx2 recipe), not read from a saved file.",
        "wiring": {"reproduced_router_heldout_top1": round(router_acc, 4),
                   "comp1_booked_router_heldout_top1": book,
                   "match": bool(abs(router_acc - book) < 1e-9),
                   "T_margin_median_train_top1_rho": round(T_MED, 4)},
        "q1_win_definition": "label = 1[FED correct AND SINGLE wrong] (per item)",
        "q1_base_rate": {"train": round(base_tr, 4), "heldout": round(base_he, 4),
                         "n_win_heldout": int(w_he.sum()), "n_heldout": len(he)},
        "q1_feature_sets": results,
        "q1_single_feature_auc_heldout": singles,
        "q1_separation_decomposition": sep,
        "q1_best_deployable": None,
        "q1_verdict": None,
        "q2_mlp_retirement": {
            "comp1_booked": {"FED_params": comp1["params"]["FED"], "device": "cuda",
                             "FED_boards": boards, "SINGLE_boards": boards_single},
            "cheap_two_arm_params": two_arm_params, "device": "cpu",
            "cheap_boards": our, "per_regime_delta_vs_comp1_FED": delta,
            "max_abs_delta": round(max_abs_delta, 4), "delta_gate": 0.02,
            "negation_win_ours": neg_win_ours, "negation_win_comp1": neg_win_comp1,
            "verdict": ("PASS: MLP retired, replacement = logistic two-arm" if Q2_pass
                        else "FAIL: MLP buys something")},
        "economics": {
            "cheap_two_arm": {"params": two_arm_params, "device": "cpu", "energy_wh": 0.0},
            "comp1_FED_MLP": {"params": comp1["params"]["FED"], "device": "cuda",
                              "energy_wh": 11.76, "wall_s": comp1.get("wall_seconds")},
            "param_ratio": round(comp1["params"]["FED"] / two_arm_params, 2)},
        "prior": {"ring_cx2": "cheap gate detects the blind REGIME (3.26x, prec 0.805) but "
                              "NOT the per-item win; d_ans dead (AUC 0.549)"},
    }
    dep = {k: v for k, v in results.items() if v["feature_kind"] == "deployable"}
    best = max(dep, key=lambda k: dep[k]["auc_heldout"])
    out["q1_best_deployable"] = best
    out["q1_verdict"] = ("PASS: cheap gate predicts the per-item win"
                         if dep[best]["verdict"] == "PASS" else
                         "FAIL: no cheap deployable set reaches G-C1/C2")
    out["q1_answer"] = (f"best deployable = {best}, held-out AUC {dep[best]['auc_heldout']}, "
                        f"Brier {dep[best]['brier_heldout']}, prec/base "
                        f"{dep[best]['precision_over_base']} -> {dep[best]['verdict']}")
    out["q2_answer"] = out["q2_mlp_retirement"]["verdict"]

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cx_cheap0_results.json").write_text(json.dumps(out, indent=2))
    print("\n=== SUMMARY ===")
    print(json.dumps({"router_repro": round(router_acc, 4), "booked": book,
                      "base_rate_heldout": round(base_he, 4),
                      "verdicts": {k: v["verdict"] for k, v in results.items()},
                      "singles": singles, "separation": sep, "q2_delta": delta,
                      "q2_neg_win_ours": neg_win_ours, "q2_neg_win_comp1": neg_win_comp1,
                      "q2_verdict": out["q2_mlp_retirement"]["verdict"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
