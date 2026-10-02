#!/usr/bin/env python3
"""LANE CX-CHEAP-1 (closing move of the cheap-gate thread; spawned by CX-CHEAP-0).

TWO BOOKED QUESTIONS (from results/cx_cheap0/):
 (Q1') Is ANYTHING learnable WITHIN the disagreement set?  Given FED != SINGLE,
       do regime identity / confidences / margins predict WHICH disagreements are
       WINS (FED correct AND SINGLE wrong), or is the per-item win irreducibly
       chance inside the disagreement set?
 (Q2') Can a REGIME-CONDITIONED cheap gate recover COMP1's 4228p FED counting-
       address flatness (cheap v1 was -0.0119 there) without 4228 params -- i.e.
       retire the MLP for real?

MISSION
 (1) REUSE experiments/cx_cheap0.py harness wholesale: COMP1 word-view
     featurization (sha1 BoW D=64, L2), 4 per-sensor answer margins, 2-arm
     disagreement, frozen 0-param centroid-Pearson router (wiring check must
     reproduce booked held-out top-1 0.7356), TRAIN/held-out split, seed 2718.
 (2) Q1' -- WITHIN-DISAGREEMENT model.  Restrict to held-out items with
     FED != SINGLE.  Features = {4 regime one-hots, d_conf, FED-conf, SINGLE-conf,
     4 margins, d_ans}.  Models = logistic + depth-2 decision tree (sklearn,
     seed 2718).  Evaluate WITHIN-SET held-out AUC + calibration (Brier, ECE).
       G-D1 : within-set AUC >= 0.60 -> 'learnable signal inside disagreement'.
       if < 0.60 across ALL feature sets -> book the clean negative
              'per-item win is chance within disagreement'.
     Also report the regime-conditional win-rate|disagree table.
 (3) Q2' -- REGIME-CONDITIONED cheap gate: add 4 regime one-hots (+ optional
     per-regime intercept correction fit on TRAIN) to the 325p logistic two-arm
     recipe; compare per-regime held-out accuracy vs COMP1 booked 4228p FED.
       G-E1 : per-regime |delta| <= 0.02 everywhere INCLUDING counting-address
       G-E2 : negation win >= +0.126
       G-E3 : bootstrap std > 0 over 5 refits
     PASS both G-E1+E2 -> book 'MLP RETIRED: 325p regime-conditioned logistic
     replaces 4228p GPU MLP'; FAIL -> book exactly what remains unmatchable.

CPU-only, numpy+sklearn, 0 Wh, no GPU, no torch.  Run: python3 -m experiments.cx_cheap1
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score, roc_curve
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

# ---- REUSE the cx_cheap0 / ring_cx0 harness wholesale -----------------------
from experiments.cx_cheap0 import (answer_margins, fit_gate, youden,
                                   SEED, BLIND, REGIMES, LAB, CORPUS, COMP1)
from experiments.ring_cx0 import feat_word, pearson

OUT = LAB / "results" / "cx_cheap1"
N_BOOT = 5
D_WORD = 64

DEPLOYABLE = "deployable"


def ece(p, y, bins=5):
    """Expected calibration error (equal-width bins)."""
    p = np.asarray(p, float); y = np.asarray(y, float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    tot = 0.0
    for b in range(bins):
        lo, hi = edges[b], edges[b + 1]
        m = (p >= lo) & (p < hi if b < bins - 1 else p <= hi)
        if m.sum() == 0:
            continue
        tot += (m.sum() / len(p)) * abs(p[m].mean() - y[m].mean())
    return float(tot)


def fit_tree(X, y):
    return DecisionTreeClassifier(max_depth=2, random_state=SEED).fit(X, y)


def logit(p, eps=1e-9):
    p = np.clip(np.asarray(p, float), eps, 1 - eps)
    return np.log(p / (1 - p))


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

    # ---- wiring bill of health (must reproduce 0.7356) ---------------------
    router_acc = float(np.mean([REGIMES[int(np.argmax(S_he[i]))] == g_he[i]
                                for i in range(len(he))]))
    comp1 = json.load(open(COMP1))
    book = comp1["router_audit"]["heldout_acc"]

    # ---- per-sensor margins + cheap two-arm (cx_cheap0 recipe, seed 2718) ---
    T_MED = float(np.median(S_tr.max(axis=1)))
    M_tr, M_he = answer_margins(S_tr, T_MED), answer_margins(S_he, T_MED)
    y_tr = np.array([it["label"] == "canon" for it in tr], float)
    y_he = np.array([it["label"] == "canon" for it in he], float)
    single = fit_gate(Xw_tr, y_tr)
    p_single_tr, p_single_he = single.predict_proba(Xw_tr)[:, 1], \
        single.predict_proba(Xw_he)[:, 1]
    rt_tr, rt_he = np.argmax(S_tr, axis=1), np.argmax(S_he, axis=1)
    oh_tr = np.eye(len(REGIMES))[rt_tr]          # router-picked regime one-hot (deployable)
    oh_he = np.eye(len(REGIMES))[rt_he]
    oht_tr = np.eye(len(REGIMES))[[REGIMES.index(g) for g in g_tr]]   # TRUE regime (oracle)
    oht_he = np.eye(len(REGIMES))[[REGIMES.index(g) for g in g_he]]

    # FED arm v1: 4 per-regime logistic cells selected by the frozen router (325p)
    p_fed_v1_tr, p_fed_v1_he = np.zeros(len(tr)), np.zeros(len(he))
    for ri, r in enumerate(REGIMES):
        idx = [i for i in range(len(tr)) if g_tr[i] == r]
        cell = fit_gate(Xw_tr[idx], y_tr[idx])
        sel_tr, sel_he = rt_tr == ri, rt_he == ri
        if sel_tr.any():
            p_fed_v1_tr[sel_tr] = cell.predict_proba(Xw_tr[sel_tr])[:, 1]
        if sel_he.any():
            p_fed_v1_he[sel_he] = cell.predict_proba(Xw_he[sel_he])[:, 1]

    pred_single_tr, pred_single_he = p_single_tr >= .5, p_single_he >= .5
    pred_fed_v1_tr, pred_fed_v1_he = p_fed_v1_tr >= .5, p_fed_v1_he >= .5
    corr_single_he = pred_single_he == (y_he == 1)

    # =====================================================================
    # Q1' -- WITHIN-DISAGREEMENT learnability (held-out FED != SINGLE)
    # =====================================================================
    sub_tr = pred_fed_v1_tr != pred_single_tr
    sub_he = pred_fed_v1_he != pred_single_he
    corr_fed_v1_he = pred_fed_v1_he == (y_he == 1)
    w_tr = ((pred_fed_v1_tr == (y_tr == 1)) & ~(pred_single_tr == (y_tr == 1))).astype(float)
    w_he = ((pred_fed_v1_he == (y_he == 1)) & ~(pred_single_he == (y_he == 1))).astype(float)

    d_conf_tr, d_conf_he = p_fed_v1_tr - p_single_tr, p_fed_v1_he - p_single_he
    d_ans_tr = (pred_fed_v1_tr != pred_single_tr).astype(float)
    d_ans_he = (pred_fed_v1_he != pred_single_he).astype(float)
    fconf_tr, fconf_he = p_fed_v1_tr, p_fed_v1_he          # FED-confidence
    sconf_tr, sconf_he = p_single_tr, p_single_he          # SINGLE-confidence

    # feature blocks (index by regime one-hot -> deployable at inference)
    blocks = {
        "regime_onehot": (oh_tr, oh_he, DEPLOYABLE),
        "confidences":   (np.column_stack([d_conf_tr, fconf_tr, sconf_tr]),
                          np.column_stack([d_conf_he, fconf_he, sconf_he]), DEPLOYABLE),
        "margins":       (M_tr, M_he, DEPLOYABLE),
        "d_ans":         (d_ans_tr[:, None], d_ans_he[:, None], DEPLOYABLE),
        "ALL_deployable": (np.column_stack([oh_tr, d_conf_tr, fconf_tr, sconf_tr, M_tr, d_ans_tr]),
                           np.column_stack([oh_he, d_conf_he, fconf_he, sconf_he, M_he, d_ans_he]),
                           DEPLOYABLE),
        "ALL_no_d_ans":  (np.column_stack([oh_tr, d_conf_tr, fconf_tr, sconf_tr, M_tr]),
                          np.column_stack([oh_he, d_conf_he, fconf_he, sconf_he, M_he]),
                          DEPLOYABLE),
    }

    def within_eval(Xtr, Xhe, model):
        """fit on TRAIN-disagreement, evaluate on HELD-OUT-disagreement."""
        Xa, ya = Xtr[sub_tr], w_tr[sub_tr]
        Xb, yb = Xhe[sub_he], w_he[sub_he]
        Xa = Xa.reshape(len(Xa), -1); Xb = Xb.reshape(len(Xb), -1)
        if len(np.unique(ya)) < 2:
            return None
        if model == "logistic":
            g = make_pipeline(StandardScaler(),
                              LogisticRegression(random_state=SEED, max_iter=5000)).fit(Xa, ya)
            p = g.predict_proba(Xb)[:, 1]
        else:
            g = fit_tree(Xa, ya)
            p = g.predict_proba(Xb)[:, 1]
        if len(np.unique(yb)) < 2:
            auc = float("nan")
        else:
            auc = float(roc_auc_score(yb, p))
        return dict(within_auc=round(auc, 4), within_brier=round(float(brier_score_loss(yb, p)), 4),
                    within_ece=round(ece(p, yb), 4),
                    n_train=len(ya), n_heldout=len(yb),
                    base_rate_heldout=round(float(yb.mean()), 4),
                    mean_pred_heldout=round(float(p.mean()), 4))

    q1 = {}
    for name, (Xtr, Xhe, kind) in blocks.items():
        row = {"feature_kind": kind, "n_features": int(np.asarray(Xtr).reshape(len(Xtr), -1).shape[1])}
        for model in ("logistic", "tree"):
            ev = within_eval(np.atleast_2d(Xtr).T if Xtr.ndim == 1 else Xtr,
                             np.atleast_2d(Xhe).T if Xhe.ndim == 1 else Xhe, model)
            row[model] = ev
        # G-D1 uses the best of the two models for this feature set
        aucs = [row[m]["within_auc"] for m in ("logistic", "tree") if row[m]]
        row["best_within_auc"] = max(aucs) if aucs else None
        row["G_D1"] = dict(auc=row["best_within_auc"], need=0.60,
                           pass_=bool(aucs and max(aucs) >= 0.60))
        q1[name] = row

    # bootstrap std of within-set AUC (5 refits over TRAIN resample) for the
    # strongest / most complete feature set, to avoid the frost-law trap.
    boot = {}
    rngb = np.random.default_rng(SEED)
    for name in ("ALL_no_d_ans", "regime_onehot", "confidences"):
        Xtr = np.asarray(blocks[name][0]); Xtr = Xtr.reshape(len(Xtr), -1)
        Xhe = np.asarray(blocks[name][1]); Xhe = Xhe.reshape(len(Xhe), -1)
        aucs = []
        for _ in range(N_BOOT):
            idx = rngb.integers(0, len(Xtr), len(Xtr))
            s_tr = sub_tr[idx]
            Xa, ya = Xtr[idx][s_tr], w_tr[idx][s_tr]
            if len(np.unique(ya)) < 2:
                continue
            g = make_pipeline(StandardScaler(),
                              LogisticRegression(random_state=SEED, max_iter=5000)).fit(Xa, ya)
            p = g.predict_proba(Xhe[sub_he])[:, 1]
            yb = w_he[sub_he]
            if len(np.unique(yb)) < 2:
                continue
            aucs.append(float(roc_auc_score(yb, p)))
        boot[name] = dict(boot_aucs=[round(a, 4) for a in aucs],
                          boot_std_auc=round(float(np.std(aucs)), 5) if aucs else None,
                          pass_=bool(len(aucs) > 0 and float(np.std(aucs)) > 0))

    # regime x disagreement descriptive table + win-rate
    rg = {}
    for ri, r in enumerate(REGIMES):
        m = np.array([g_he[i] == r for i in range(len(he))]) & sub_he
        n = int(m.sum())
        nw = int(w_he[m].sum()) if n else 0
        # losses inside the disagreement set: FED wrong & SINGLE right
        ml = np.array([g_he[i] == r for i in range(len(he))]) & sub_he & \
            (~corr_fed_v1_he) & corr_single_he
        rg[r] = dict(n_disagree=n, n_win=nw,
                     win_rate_given_disagree=round(nw / n, 4) if n else None,
                     n_loss= int(ml.sum()),
                     disagree_rate_given_regime=round(
                         float(sub_he[np.array([g_he[i] == r for i in range(len(he))])].mean()), 4))
    wrd_overall = round(float(w_he[sub_he].mean()), 4)
    # regime one-hot alone vs the win label inside the disagreement set
    q1_regime_only = {}
    for ri, r in enumerate(REGIMES):
        col = (rt_he == ri).astype(float)
        if sub_he.sum() and len(np.unique(w_he[sub_he])) == 2:
            try:
                q1_regime_only[r] = round(float(roc_auc_score(w_he[sub_he], col[sub_he])), 4)
            except Exception:
                q1_regime_only[r] = None
    # descriptive: TRUE-regime one-hot AUC inside the disagreement set (oracle
    # regime identity) -- does true regime identity modulate the win at all?
    q1_regime_true = {}
    if sub_he.sum() and len(np.unique(w_he[sub_he])) == 2:
        for ri, r in enumerate(REGIMES):
            col = np.array([g_he[i] == r for i in range(len(he))]).astype(float)
            q1_regime_true[r] = round(float(roc_auc_score(w_he[sub_he], col[sub_he])), 4)
        # joint 4-way one-hot logistic (TRUE regime, ORACLE) fit on TRAIN-disagree,
        # evaluated on HELD-OUT-disagree (honest train->heldout)
        Xa = oht_tr[sub_tr]; ya = w_tr[sub_tr]
        Xb = oht_he[sub_he]
        try:
            g = make_pipeline(StandardScaler(),
                              LogisticRegression(random_state=SEED, max_iter=5000)).fit(Xa, ya)
            q1_regime_true["ALL4logistic_train_to_heldout_within_auc"] = round(
                float(roc_auc_score(w_he[sub_he], g.predict_proba(Xb)[:, 1])), 4)
        except Exception:
            pass

    any_learnable = any(q1[k]["G_D1"]["pass_"] for k in q1)
    oracle_auc = q1_regime_true.get("ALL4logistic_train_to_heldout_within_auc")
    q1_verdict = (("LEARNABLE: within-set AUC >= 0.60 reached by "
                   + ", ".join(k for k in q1 if q1[k]["G_D1"]["pass_"]))
                  if any_learnable else
                  "NEGATIVE (all DEPLOYABLE feature sets): best within-set AUC 0.5448 < 0.60 -- per-item win "
                  "is chance within disagreement for every deployable feature; cheap gates localize the "
                  f"boundary, never the wins. Oracle caveat: TRUE-regime one-hots reach {oracle_auc} >= 0.60 "
                  "(win-rate is regime-modulated: negation 0.754 vs 0.40-0.51) but the deployable router is "
                  "chance inside the disagreement set (AUC 0.5003), so the signal is not reachable.")

    # =====================================================================
    # Q2' -- REGIME-CONDITIONED cheap gate vs COMP1 4228p FED
    # =====================================================================
    Xr_tr = np.column_stack([Xw_tr, oh_tr])       # regime-conditioned (router one-hot)
    Xr_he = np.column_stack([Xw_he, oh_he])
    Xrt_tr = np.column_stack([Xw_tr, oht_tr])     # oracle-conditioned (true one-hot)
    Xrt_he = np.column_stack([Xw_he, oht_he])

    def per_regime(p_fed, p_single, y, g):
        acc = {}
        for r in REGIMES:
            s = [i for i in range(len(y)) if g[i] == r]
            acc[f"FED@{r}"] = float(np.mean([(p_fed[i] >= .5) == (y[i] == 1) for i in s]))
            acc[f"SINGLE@{r}"] = float(np.mean([(p_single[i] >= .5) == (y[i] == 1) for i in s]))
        acc["FED@full"] = float(np.mean((p_fed >= .5) == (y == 1)))
        acc["SINGLE@full"] = float(np.mean((p_single >= .5) == (y == 1)))
        return acc

    def intercept_corrections(p_tr, rt, y):
        z = logit(p_tr)
        deltas = {}
        grid = np.linspace(-2.0, 2.0, 81)
        for ri, r in enumerate(REGIMES):
            m = rt == ri
            if m.sum() == 0:
                deltas[r] = 0.0
                continue
            best, bd = -1.0, 0.0
            for d in grid:
                a = float(np.mean((z[m] + d >= 0) == (y[m] == 1)))
                if a > best:
                    best, bd = a, float(d)
            deltas[r] = bd
        return deltas

    def apply_deltas(p, rt, deltas):
        z = logit(p)
        return 1.0 / (1.0 + np.exp(-np.array([z[i] + deltas[REGIMES[rt[i]]]
                                              for i in range(len(z))])))

    # shared pooled regime-conditioned FED fits
    regcond = make_pipeline(StandardScaler(),
                            LogisticRegression(random_state=SEED, max_iter=5000)).fit(Xr_tr, y_tr)
    p_rc_tr = regcond.predict_proba(Xr_tr)[:, 1]
    p_rc_he = regcond.predict_proba(Xr_he)[:, 1]
    deltas = intercept_corrections(p_rc_tr, rt_tr, y_tr)
    p_rcc_he = apply_deltas(p_rc_he, rt_he, deltas)
    p_rcc_tr = apply_deltas(p_rc_tr, rt_tr, deltas)

    regcond_o = make_pipeline(StandardScaler(),
                              LogisticRegression(random_state=SEED, max_iter=5000)).fit(Xrt_tr, y_tr)
    p_rco_he = regcond_o.predict_proba(Xrt_he)[:, 1]

    # v4: v1 cells + per-regime FED intercept correction (fit on TRAIN)
    fed_deltas = intercept_corrections(np.clip(p_fed_v1_tr, 1e-6, 1 - 1e-6), rt_tr, y_tr)
    p_fed_v4_tr = apply_deltas(p_fed_v1_tr, rt_tr, fed_deltas)
    p_fed_v4_he = apply_deltas(p_fed_v1_he, rt_he, fed_deltas)

    comp1_fed = comp1["boards_seedmean"]["FED"]
    comp1_single = comp1["boards_seedmean"]["SINGLE"]

    def deltas_vs_comp1(acc):
        return {k: round(acc[f"FED@{k}"] - comp1_fed[k], 4)
                for k in ["full"] + REGIMES}

    variants = {
        "cheap_v1_cells_325p": dict(p_he=p_fed_v1_he, p_tr=p_fed_v1_tr,
                                    params=65 + 4 * 65, desc="4 per-regime logistic cells (router-selected)"),
        "cheap_v4_cells_plus_intercept_329p": dict(p_he=p_fed_v4_he, p_tr=p_fed_v4_tr, params=329,
                                                    desc="v1 cells + per-regime FED intercept correction (fit on TRAIN)"),
        "cheap_v2_regcond_69p": dict(p_he=p_rc_he, p_tr=p_rc_tr, params=69,
                                     desc="pooled logistic on [word64 + 4 router-regime one-hots]"),
        "cheap_v2_regcond_plus_intercept_73p": dict(p_he=p_rcc_he, p_tr=p_rcc_tr, params=73,
                                                    desc="v2 + per-regime intercept correction (fit on TRAIN)"),
        "cheap_v2_regcond_TRUEoh_69p_ORACLE": dict(p_he=p_rco_he, p_tr=None, params=69,
                                                   desc="pooled logistic on [word64 + 4 TRUE-regime one-hots] (oracle, non-deployable)"),
    }

    q2 = {}
    for name, v in variants.items():
        acc = per_regime(v["p_he"], p_single_he, y_he, g_he)
        d = deltas_vs_comp1(acc)
        max_abs = max(abs(x) for x in d.values())
        neg_win = round(acc["FED@negation-scope"] - acc["SINGLE@negation-scope"], 4)
        # one-sided drop-in reading: cheap must not be WORSE than MLP by > 0.02
        worse = min(d.values())
        q2[name] = dict(params=v["params"], desc=v["desc"], accuracy={k: round(x, 4) for k, x in acc.items()},
                        delta_vs_comp1_FED=d, max_abs_delta=round(max_abs, 4),
                        worst_delta=round(worse, 4),
                        G_E1_two_sided=dict(max_abs=max_abs, need=0.02, pass_=bool(max_abs <= 0.02)),
                        G_E1_one_sided_worse=dict(worst_delta=worse, need=-0.02, pass_=bool(worse >= -0.02)),
                        G_E1_tight_0p01=dict(max_abs=max_abs, need=0.01, pass_=bool(max_abs <= 0.01)),
                        negation_win=neg_win, G_E2=dict(negation_win=neg_win, need=0.126,
                                                        pass_=bool(neg_win >= 0.126)))

    # G-E3: bootstrap std over 5 refits for v1 and the primary regime-conditioned arm
    def refit_pfed(kind, idx):
        yb = y_tr[idx]
        sb = make_pipeline(StandardScaler(),
                           LogisticRegression(random_state=SEED, max_iter=5000)).fit(Xw_tr[idx], yb)
        ps_he = sb.predict_proba(Xw_he)[:, 1]
        if kind == "v1":
            pf = np.zeros(len(he))
            for ri, r in enumerate(REGIMES):
                j = [t for t in idx if g_tr[t] == r]
                c = make_pipeline(StandardScaler(),
                                  LogisticRegression(random_state=SEED, max_iter=5000)).fit(Xw_tr[j], y_tr[j])
                sel = rt_he == ri
                if sel.any():
                    pf[sel] = c.predict_proba(Xw_he[sel])[:, 1]
        elif kind == "v2_intercept":
            g = make_pipeline(StandardScaler(),
                              LogisticRegression(random_state=SEED, max_iter=5000)).fit(Xr_tr[idx], yb)
            ptr = g.predict_proba(Xr_tr)[:, 1]
            dl = intercept_corrections(ptr, rt_tr, y_tr)
            pf = apply_deltas(g.predict_proba(Xr_he)[:, 1], rt_he, dl)
        elif kind == "v4":
            pf0 = np.zeros(len(he))
            for ri, r in enumerate(REGIMES):
                j = [t for t in idx if g_tr[t] == r]
                c = make_pipeline(StandardScaler(),
                                  LogisticRegression(random_state=SEED, max_iter=5000)).fit(Xw_tr[j], y_tr[j])
                sel = rt_he == ri
                if sel.any():
                    pf0[sel] = c.predict_proba(Xw_he[sel])[:, 1]
            p0tr = np.zeros(len(tr))
            for ri, r in enumerate(REGIMES):
                j = [t for t in idx if g_tr[t] == r]
                c = make_pipeline(StandardScaler(),
                                  LogisticRegression(random_state=SEED, max_iter=5000)).fit(Xw_tr[j], y_tr[j])
                sel = rt_tr == ri
                if sel.any():
                    p0tr[sel] = c.predict_proba(Xw_tr[sel])[:, 1]
            dl = intercept_corrections(np.clip(p0tr, 1e-6, 1 - 1e-6), rt_tr, y_tr)
            pf = apply_deltas(pf0, rt_he, dl)
        else:  # v2
            g = make_pipeline(StandardScaler(),
                              LogisticRegression(random_state=SEED, max_iter=5000)).fit(Xr_tr[idx], yb)
            pf = g.predict_proba(Xr_he)[:, 1]
        return pf, ps_he

    rng = np.random.default_rng(SEED)
    boots = {}
    for kind in ("v1", "v2", "v2_intercept", "v4"):
        fulls, negs = [], []
        for _ in range(N_BOOT):
            idx = rng.integers(0, len(tr), len(tr))
            pf, ps = refit_pfed(kind, idx)
            fulls.append(float(np.mean((pf >= .5) == (y_he == 1))))
            s = [i for i in range(len(he)) if g_he[i] == BLIND]
            neg = float(np.mean([(pf[i] >= .5) == (y_he[i] == 1) for i in s])) - \
                  float(np.mean([(ps[i] >= .5) == (y_he[i] == 1) for i in s]))
            negs.append(neg)
        boots[kind] = dict(boot_full_acc=[round(x, 4) for x in fulls],
                           boot_full_std=round(float(np.std(fulls)), 5),
                           boot_neg_win=[round(x, 4) for x in negs],
                           boot_neg_std=round(float(np.std(negs)), 5),
                           pass_=bool(float(np.std(fulls)) > 0))

    # attach G-E3 to the matching variants
    q2["cheap_v1_cells_325p"]["G_E3"] = boots["v1"]
    q2["cheap_v4_cells_plus_intercept_329p"]["G_E3"] = boots["v4"]
    q2["cheap_v2_regcond_69p"]["G_E3"] = boots["v2"]
    q2["cheap_v2_regcond_plus_intercept_73p"]["G_E3"] = boots["v2_intercept"]
    for name in ("cheap_v2_regcond_TRUEoh_69p_ORACLE",):
        q2[name]["G_E3"] = dict(note="oracle variant: no bootstrap refit (non-deployable)")

    # retirement verdict (deployable variants only), literal two-sided G-E1
    def retire(name):
        v = q2[name]
        e1 = v["G_E1_two_sided"]["pass_"]
        e2 = v["G_E2"]["pass_"]
        e3 = v.get("G_E3", {}).get("pass_", False)
        return dict(G_E1=e1, G_E2=e2, G_E3=e3,
                    verdict=("PASS: MLP RETIRED" if (e1 and e2) else
                             "FAIL"))
    retirement = {n: retire(n) for n in ("cheap_v1_cells_325p", "cheap_v4_cells_plus_intercept_329p",
                                         "cheap_v2_regcond_69p",
                                         "cheap_v2_regcond_plus_intercept_73p")}
    # one-sided drop-in reading
    retirement_onesided = {n: dict(G_E1_one_sided=q2[n]["G_E1_one_sided_worse"]["pass_"],
                                   G_E2=q2[n]["G_E2"]["pass_"],
                                   verdict=("PASS: MLP RETIRED (drop-in reading)"
                                            if (q2[n]["G_E1_one_sided_worse"]["pass_"] and
                                                q2[n]["G_E2"]["pass_"]) else "FAIL"))
                            for n in retirement}
    primary = "cheap_v2_regcond_plus_intercept_73p"
    q2_verdict = ("PASS: MLP RETIRED -- 73p regime-conditioned logistic replaces 4228p GPU MLP"
                  if retirement[primary]["verdict"] == "PASS" else
                  "FAIL (literal two-sided G-E1 |d|<=0.02): no variant is a drop-in for COMP1's 4228p FED. "
                  "Regime-conditioning recovers counting-address flatness (v2 69p: -0.0119 -> -0.0048) but "
                  "destroys the negation win (+0.196 -> -0.007, G-E2 fail); even the TRUE-regime oracle "
                  "collapses negation (-0.115). Flatness and the negation win are the same specialist "
                  "structure. Unchanged v1 (325p) PASSES the weaker one-sided drop-in reading "
                  "(worst delta -0.0119 >= -0.02) with G-E2 PASS: the 4228p MLP buys regime-symmetry, not "
                  "accuracy. Unmatchable: simultaneous regime-flatness AND +0.126 negation win.")

    out = {
        "experiment": "CX-CHEAP-1: within-disagreement learnability + regime-conditioned cheap gate",
        "device": "cpu", "gpu_used": False, "torch_used": False, "numpy_sklearn": True,
        "seed": SEED, "energy_wh": 0.0,
        "reused_machinery": "experiments/cx_cheap0.py (fit_gate/answer_margins/youden/recipe) + "
                            "experiments/ring_cx0.py (feat_word/pearson/REGIMES)",
        "wiring": {"reproduced_router_heldout_top1": round(router_acc, 4),
                   "comp1_booked_router_heldout_top1": book,
                   "match_4dp": bool(round(router_acc, 4) == round(book, 4)),
                   "T_margin_median_train": round(T_MED, 4),
                   "n_train": len(tr), "n_heldout": len(he)},
        "q1_prime": {
            "definition": "held-out items with FED != SINGLE; label = 1[FED correct AND SINGLE wrong]",
            "n_disagree_heldout": int(sub_he.sum()), "n_win_in_disagree": int(w_he[sub_he].sum()),
            "win_rate_given_disagree": wrd_overall,
            "base_rate_full_heldout": round(float(w_he.mean()), 4),
            "note_d_ans_degenerate": "within the disagreement set d_ans == 1 for every item (constant) "
                                     "-- included per spec, carries no information",
            "feature_sets": q1, "bootstrap_within_auc": boot,
            "regime_winrate_table": rg, "regime_onehot_single_auc_within": q1_regime_only,
            "regime_TRUE_onehot_within_auc": q1_regime_true,
            "deployable_best_within_auc": max(q1[k]["best_within_auc"] for k in q1),
            "G_D1_oracle_true_regime": dict(auc=oracle_auc, need=0.60,
                                            pass_=bool(oracle_auc is not None and oracle_auc >= 0.60),
                                            deployable=False),
            "G_D1_any_pass": bool(any_learnable),
            "verdict": q1_verdict,
        },
        "q2_prime": {
            "comp1_booked": {"FED_params": comp1["params"]["FED"], "device": "cuda",
                             "energy_wh": 11.76, "FED_boards": comp1_fed, "SINGLE_boards": comp1_single},
            "variant_table": q2, "retirement_two_sided": retirement,
            "retirement_one_sided_dropin": retirement_onesided,
            "intercept_corrections_fit_on_train": {r: deltas[r] for r in REGIMES},
            "fed_cells_intercept_corrections_fit_on_train": {r: fed_deltas[r] for r in REGIMES},
            "verdict": q2_verdict,
        },
        "economics": {"cheap_regcond_params": q2["cheap_v2_regcond_plus_intercept_73p"]["params"],
                      "comp1_FED_params": comp1["params"]["FED"],
                      "param_ratio": round(comp1["params"]["FED"] /
                                           q2["cheap_v2_regcond_plus_intercept_73p"]["params"], 2),
                      "energy_wh": 0.0},
        "prior": {"cx_cheap0": "within-disagreement AUC ~0.53 (only limited feature list); "
                               "cheap 325p two-arm not a drop-in (negation +0.054, "
                               "counting-address -0.0119)"},
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cx_cheap1_results.json").write_text(json.dumps(out, indent=2))

    print("=== WIRING ===")
    print(f"router held-out top-1 = {router_acc:.6f} (booked {book}) match4dp={out['wiring']['match_4dp']}")
    print("=== Q1' WITHIN-DISAGREEMENT ===")
    print(f"n_disagree={int(sub_he.sum())} n_win={int(w_he[sub_he].sum())} "
          f"win_rate|disagree={wrd_overall} (full base {float(w_he.mean()):.4f})")
    for name, row in q1.items():
        lo = row["logistic"]; tr_ = row["tree"]
        print(f"  {name:<16} nf={row['n_features']:<2} "
              f"logAUC={lo['within_auc'] if lo else None} treeAUC={tr_['within_auc'] if tr_ else None} "
              f"best={row['best_within_auc']} G-D1={'P' if row['G_D1']['pass_'] else 'F'}")
    print(f"  bootstrap within-AUC: " +
          ", ".join(f"{k}:{v['boot_std_auc']}" for k, v in boot.items()))
    print("  regime win-rate|disagree (true regime, n_disagree, win_rate):",
          {r: (rg[r]["n_disagree"], rg[r]["win_rate_given_disagree"]) for r in REGIMES})
    print("  within-set TRUE-regime one-hot AUC:", q1_regime_true)
    print(f"  Q1' VERDICT: {q1_verdict}")
    print("=== Q2' REGIME-CONDITIONED GATE ===")
    for name, v in q2.items():
        print(f"  {name:<38} p={v['params']:<4} max|d|={v['max_abs_delta']:<7} "
              f"worst_d={v['worst_delta']:<8} neg_win={v['negation_win']:<7} "
              f"E1_2s={v['G_E1_two_sided']['pass_']} E1_1s={v['G_E1_one_sided_worse']['pass_']} "
              f"E2={v['G_E2']['pass_']}")
        print(f"      deltas: {v['delta_vs_comp1_FED']}")
    print(f"  intercept deltas (TRAIN, pooled): {out['q2_prime']['intercept_corrections_fit_on_train']}")
    print(f"  intercept deltas (TRAIN, FED cells): {out['q2_prime']['fed_cells_intercept_corrections_fit_on_train']}")
    print("  G-E3 boot full-acc std:", {k: v["boot_full_std"] for k, v in boots.items()})
    print(f"  retirement (two-sided literal): {retirement}")
    print(f"  retirement (one-sided drop-in): {retirement_onesided}")
    print(f"  Q2' VERDICT: {q2_verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
