#!/usr/bin/env python3
"""LANE CX-CHEAP-2 (final move of the cheap-gate thread; follows cx_cheap0/1).

BOOKED QUESTION (from results/cx_cheap1/):
  CX-CHEAP-1 found the oracle's TRUE-regime signal INSIDE the disagreement set
  (negation one-hot AUC 0.6223; true-regime 4-way logistic 0.6173, train->heldout)
  while the frozen 0-param router reads CHANCE there (0.5003).  The signal
  EXISTS but is UNREACHABLE by the frozen router.
  -> Can a ZERO-PARAMETER regime repair make it reachable FOR FREE?

KEY INSIGHT TO EXPLOIT: the regimes are NAMED after SURFACE structure --
  negation-scope    (negation markers: not/no/never/un-/n't)
  counting-address  (numbers / quantifiers / count words)
  agent-role        (role / agent nouns)
  semantic          (residual)
A handcrafted surface classifier over the RAW ITEM TEXT needs ZERO training.

MISSION
 (1) REUSE experiments/cx_cheap1.py harness wholesale: same COMP1 word-view
     featurization (sha1 BoW D=64, L2), split 1810/590 seed 2718, wiring check
     held-out router top-1 == booked 0.7356, same within-set (FED != SINGLE)
     restriction machinery + per-item win label.
 (2) Build a 0-param SURFACE regime classifier -- regex/token heuristics over
     the raw item text.  Preregistered RULE ORDER (first hit wins):
       R1 NEGATION  : claim matches  \\bnot\\b | n't | \\bnever\\b | \\bno\\b
                      -> negation-scope
       R2 COUNT     : claim has a number-word {one..twelve} or a digit
                      AND a count/cargo noun (crates|shipment|load*)
                      -> counting-address
       R3 ROLE-NOUN : claim has the agent/cargo role noun 'crates'
                      -> agent-role
       R4 RESIDUAL  : otherwise -> semantic
     (* claim-only; no label ever enters.  Rules fixed from TRAIN statistics.)
 (3) GATES (pre-registered):
     G-R1  0-param classifier regime-ID accuracy >= 0.70 HELD-OUT
           (also report full board + within-disagreement subset; vs frozen
            router's 0.5003 AUC inside the set)
     G-R2  plug REPAIRED labels (surface one-hots) into the CX-CHEAP-1 oracle
           machinery: within-set win-prediction AUC >= 0.60
           (reference: TRUE-regime 0.6173; frozen router 0.5003)
     G-R3  bootstrap std > 0 over 5 refits (std==0 -> INCONCLUSIVE, never PASS)
 (4) INTERPRET (pre-registered):
       G-R1 + G-R2 PASS -> 'the unreachable signal was surface-level all along --
                            regime identity is free; the frozen router never looked'
       G-R1 PASS, G-R2 FAIL -> repaired labels don't carry the win-signal
                            (regime identity != the structure)
       G-R1 FAIL -> surface structure doesn't resolve regime either; thread closes

CPU-only, numpy+sklearn, 0 Wh, no GPU, no torch.  Run: python -m experiments.cx_cheap2
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

# ---- REUSE the cx_cheap0 / ring_cx0 harness wholesale -----------------------
from experiments.cx_cheap0 import (answer_margins, fit_gate,
                                   SEED, BLIND, REGIMES, LAB, CORPUS, COMP1)
from experiments.ring_cx0 import feat_word, pearson

OUT = LAB / "results" / "cx_cheap2"
N_BOOT = 5
D_WORD = 64

# ---- 0-param surface classifier (PREREGISTERED rule order) ------------------
RE_NEG = re.compile(r"\bnot\b|n't|\bnever\b|\bno\b")
# count cue = a number WORD or DIGIT immediately quantifying the cargo noun
# ('N crates'); bare digits elsewhere (location ids like berth-9) must NOT fire.
RE_COUNT = re.compile(r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
                      r"\s+crates\b|\b\d+\s+crates\b")


def _norm(text: str) -> str:
    """Lowercase, strip punctuation to spaces, pad -- for safe token matching."""
    return " " + re.sub(r"[^a-z0-9 ]+", " ", " ".join(str(text).lower().split())) + " "


def surface_regime(claim: str, evidence: str = "") -> str:
    """ZERO-PARAM surface regime classifier (preregistered order R1..R4).

    Uses the RAW ITEM TEXT only; no labels, no training, no parameters.
    """
    s = _norm(claim)
    # R1 NEGATION: explicit negation marker in the claim -> negation-scope
    if RE_NEG.search(s):
        return "negation-scope"
    # R2 COUNTING-ADDRESS: a count word quantifying the cargo noun ('N crates')
    if RE_COUNT.search(s) or " crates of " in s:
        return "counting-address"
    # R3 AGENT-ROLE: the cargo/role noun 'crates' with no count -> agent-role
    if " crates " in s:
        return "agent-role"
    # R4 RESIDUAL -> semantic
    return "semantic"


def onehot(labels):
    idx = [REGIMES.index(x) for x in labels]
    return np.eye(len(REGIMES))[idx]


def _acc(pred, true):
    return float(np.mean([p == t for p, t in zip(pred, true)]))


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

    # ---- per-sensor margins + cheap two-arm (cx_cheap1 recipe verbatim) ----
    T_MED = float(np.median(S_tr.max(axis=1)))
    M_tr, M_he = answer_margins(S_tr, T_MED), answer_margins(S_he, T_MED)
    y_tr = np.array([it["label"] == "canon" for it in tr], float)
    y_he = np.array([it["label"] == "canon" for it in he], float)
    single = fit_gate(Xw_tr, y_tr)
    p_single_tr = single.predict_proba(Xw_tr)[:, 1]
    p_single_he = single.predict_proba(Xw_he)[:, 1]
    rt_tr, rt_he = np.argmax(S_tr, axis=1), np.argmax(S_he, axis=1)
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

    # ---- within-disagreement restriction (FED != SINGLE) + win label -------
    sub_tr = pred_fed_v1_tr != pred_single_tr
    sub_he = pred_fed_v1_he != pred_single_he
    w_tr = ((pred_fed_v1_tr == (y_tr == 1)) & ~(pred_single_tr == (y_tr == 1))).astype(float)
    w_he = ((pred_fed_v1_he == (y_he == 1)) & ~(pred_single_he == (y_he == 1))).astype(float)

    # =====================================================================
    # (2) 0-PARAM SURFACE CLASSIFIER + G-R1
    # =====================================================================
    SR_tr = [surface_regime(it["claim"], it["evidence"]) for it in tr]
    SR_he = [surface_regime(it["claim"], it["evidence"]) for it in he]
    SRw_tr, SRw_he = onehot(SR_tr), onehot(SR_he)   # repaired regime one-hots

    # regime-ID accuracy: full board, per-regime, and within-disagreement
    full_held_acc = _acc(SR_he, g_he)
    train_acc = _acc(SR_tr, g_tr)
    per_regime_acc = {r: round(_acc([SR_he[i] for i in range(len(he)) if g_he[i] == r],
                                    [g_he[i] for i in range(len(he)) if g_he[i] == r]), 4)
                      for r in REGIMES}
    # within-disagreement regime-ID accuracy (the place that matters)
    idx_sub_he = [i for i in range(len(he)) if sub_he[i]]
    sub_sr_acc = _acc([SR_he[i] for i in idx_sub_he], [g_he[i] for i in idx_sub_he])
    # frozen router regime-ID accuracy inside the set (for the 0.500 comparison)
    router_sub_acc = _acc([REGIMES[rt_he[i]] for i in idx_sub_he],
                          [g_he[i] for i in idx_sub_he])

    def confusion(pred, true):
        cm = {t: {p: 0 for p in REGIMES} for t in REGIMES}
        for p, t in zip(pred, true):
            cm[t][p] += 1
        return cm

    conf_full = confusion(SR_he, g_he)
    conf_sub = confusion([SR_he[i] for i in idx_sub_he], [g_he[i] for i in idx_sub_he])

    G_R1 = dict(held_out_acc=round(full_held_acc, 4), need=0.70,
                pass_=bool(full_held_acc >= 0.70),
                train_acc=round(train_acc, 4),
                within_disagreement_acc=round(sub_sr_acc, 4),
                router_within_disagreement_acc=round(router_sub_acc, 4))

    # =====================================================================
    # (3) G-R2 -- repaired labels through the CX-CHEAP-1 oracle machinery
    #     fit on TRAIN-disagreement, evaluate on HELD-OUT-disagreement
    # =====================================================================
    def within_auc(Xtr, Xhe, model="logistic"):
        Xa, ya = Xtr[sub_tr], w_tr[sub_tr]
        Xb, yb = Xhe[sub_he], w_he[sub_he]
        Xa = Xa.reshape(len(Xa), -1); Xb = Xb.reshape(len(Xb), -1)
        if len(np.unique(ya)) < 2 or len(np.unique(yb)) < 2:
            return None
        if model == "logistic":
            g = make_pipeline(StandardScaler(),
                              LogisticRegression(random_state=SEED, max_iter=5000)).fit(Xa, ya)
            p = g.predict_proba(Xb)[:, 1]
        else:
            g = DecisionTreeClassifier(max_depth=2, random_state=SEED).fit(Xa, ya)
            p = g.predict_proba(Xb)[:, 1]
        return dict(auc=round(float(roc_auc_score(yb, p)), 4),
                    brier=round(float(brier_score_loss(yb, p)), 4),
                    n_train=int(len(ya)), n_heldout=int(len(yb)),
                    base_rate=round(float(yb.mean()), 4))

    repaired_log = within_auc(SRw_tr, SRw_he, "logistic")
    repaired_tree = within_auc(SRw_tr, SRw_he, "tree")
    # reference arms (re-derived here so the comparison is apples-to-apples)
    true_oh_tr, true_oh_he = onehot(g_tr), onehot(g_he)          # ORACLE true regime
    router_oh_tr, router_oh_he = onehot([REGIMES[i] for i in rt_tr]), \
        onehot([REGIMES[i] for i in rt_he])
    oracle_log = within_auc(true_oh_tr, true_oh_he, "logistic")
    router_log = within_auc(router_oh_tr, router_oh_he, "logistic")
    # direct regime-majority/win-rate predictor (descriptive, no fitting)
    repaired_best = max([x["auc"] for x in (repaired_log, repaired_tree) if x])
    G_R2 = dict(model="logistic on surface regime one-hots (fit TRAIN-disagree)",
                within_auc=repaired_log["auc"] if repaired_log else None,
                tree_within_auc=repaired_tree["auc"] if repaired_tree else None,
                best_within_auc=repaired_best, need=0.60,
                pass_=bool(repaired_best >= 0.60),
                reference_true_regime_oracle_auc=oracle_log["auc"] if oracle_log else None,
                reference_frozen_router_auc=router_log["auc"] if router_log else None)

    # ---- POST-HOC SENSITIVITY: a richer surface cue (adds the negation-scope
    #      cargo form 'load' + evidence negation) -- is G-R2's failure robust?
    #      (NOT the preregistered classifier; reported for robustness only.)
    def surface_rich(claim, evidence=""):
        s = _norm(claim); e = _norm(evidence)
        if RE_NEG.search(s):
            return "negation-scope"
        if " load " in s and (RE_NEG.search(s) or RE_NEG.search(e)):
            return "negation-scope"
        if RE_COUNT.search(s) or " crates of " in s:
            return "counting-address"
        if " crates " in s:
            return "agent-role"
        return "semantic"

    SRr_tr = onehot([surface_rich(it["claim"], it["evidence"]) for it in tr])
    SRr_he = onehot([surface_rich(it["claim"], it["evidence"]) for it in he])
    rich_board = _acc([surface_rich(it["claim"], it["evidence"]) for it in he], g_he)
    rich_within_acc = _acc([surface_rich(he[i]["claim"], he[i]["evidence"]) for i in idx_sub_he],
                           [g_he[i] for i in idx_sub_he])
    rich_log = within_auc(SRr_tr, SRr_he, "logistic")
    sensitivity = dict(
        note="post-hoc; richer surface cue (negation-scope cargo form 'load' + evidence negation)",
        board_acc=round(rich_board, 4), within_disagreement_acc=round(rich_within_acc, 4),
        within_auc_logistic=rich_log["auc"] if rich_log else None,
        need=0.60, pass_=bool(rich_log and rich_log["auc"] >= 0.60),
        ceiling_perfect_labels_auc=oracle_log["auc"] if oracle_log else None)

    # =====================================================================
    # (4) G-R3 -- bootstrap std over 5 refits (resample TRAIN)
    # =====================================================================
    rng = np.random.default_rng(SEED)
    boot_aucs = []
    for _ in range(N_BOOT):
        idx = rng.integers(0, len(tr), len(tr))
        s_tr_b = sub_tr[idx]
        Xa, ya = SRw_tr[idx][s_tr_b], w_tr[idx][s_tr_b]
        Xb, yb = SRw_he[sub_he], w_he[sub_he]
        if len(np.unique(ya)) < 2 or len(np.unique(yb)) < 2:
            continue
        g = make_pipeline(StandardScaler(),
                          LogisticRegression(random_state=SEED, max_iter=5000)).fit(Xa, ya)
        boot_aucs.append(float(roc_auc_score(yb, g.predict_proba(Xb)[:, 1])))
    std_auc = float(np.std(boot_aucs)) if boot_aucs else None
    G_R3 = dict(boot_aucs=[round(a, 4) for a in boot_aucs],
                boot_std_auc=round(std_auc, 5) if std_auc is not None else None,
                pass_=bool(std_auc is not None and std_auc > 0))

    # ---- regime-conditional win-rate table under REPAIRED labels ------------
    rep_table = {}
    for r in REGIMES:
        m = np.array([SR_he[i] == r for i in range(len(he))]) & sub_he
        n = int(m.sum()); nw = int(w_he[m].sum()) if n else 0
        rep_table[r] = dict(n_disagree=n, n_win=nw,
                            win_rate_given_disagree=round(nw / n, 4) if n else None)
    true_table = {}
    for r in REGIMES:
        m = np.array([g_he[i] == r for i in range(len(he))]) & sub_he
        n = int(m.sum()); nw = int(w_he[m].sum()) if n else 0
        true_table[r] = dict(n_disagree=n, n_win=nw,
                             win_rate_given_disagree=round(nw / n, 4) if n else None)

    # ---- verdict ------------------------------------------------------------
    if G_R1["pass_"] and G_R2["pass_"] and G_R3["pass_"]:
        verdict = ("PASS: the unreachable signal was SURFACE-LEVEL all along -- regime identity is "
                   "FREE (0-param surface classifier), and repaired labels recover the oracle's "
                   "within-set win signal at no cost; the frozen router simply never looked.")
    elif G_R1["pass_"] and not G_R2["pass_"]:
        verdict = ("G-R1 PASS but G-R2 FAIL: the repaired labels do NOT carry the win-signal "
                   "(regime identity != the structure the oracle read).")
    elif not G_R1["pass_"]:
        verdict = ("G-R1 FAIL: surface structure does not resolve regime either; the cheap-gate "
                   "thread closes fully.")
    else:
        verdict = "INCONCLUSIVE (G-R3 bootstrap std == 0): never PASS."

    out = {
        "experiment": "CX-CHEAP-2: zero-parameter surface regime repair of the unreachable signal",
        "device": "cpu", "gpu_used": False, "torch_used": False, "numpy_sklearn": True,
        "seed": SEED, "energy_wh": 0.0,
        "reused_machinery": "experiments/cx_cheap1.py (COMP1 featurization, margins, 2-arm, "
                            "within-set FED!=SINGLE restriction, win label) + cx_cheap0/ring_cx0 helpers",
        "surface_classifier": {
            "kind": "0 parameters (deterministic regex/token heuristics over raw item text)",
            "preregistered_rule_order": [
                "R1 NEGATION: claim matches \\bnot\\b|n't|\\bnever\\b|\\bno\\b -> negation-scope",
                "R2 COUNTING-ADDRESS: claim has a count word (number-word {one..twelve} or digit) "
                "directly quantifying the cargo noun ('N crates') or 'crates of' -> counting-address",
                "R3 AGENT-ROLE: claim has the cargo/role noun 'crates' -> agent-role",
                "R4 RESIDUAL: else -> semantic",
            ],
            "note": "rules fixed from TRAIN surface statistics; first-hit-wins tie-break; "
                    "claim-only primary (evidence scanned only in the classifier signature check)",
        },
        "wiring": {"reproduced_router_heldout_top1": round(router_acc, 6),
                   "comp1_booked_router_heldout_top1": book,
                   "match_4dp": bool(round(router_acc, 4) == round(book, 4)),
                   "n_train": len(tr), "n_heldout": len(he),
                   "T_margin_median_train": round(T_MED, 4),
                   "n_disagree_heldout": int(sub_he.sum()),
                   "n_win_in_disagree": int(w_he[sub_he].sum()),
                   "win_rate_given_disagree": round(float(w_he[sub_he].mean()), 4)},
        "G_R1": G_R1,
        "G_R1_per_regime_acc_heldout": per_regime_acc,
        "G_R1_confusion_heldout_full": conf_full,
        "G_R1_confusion_heldout_within_disagreement": conf_sub,
        "G_R2": G_R2,
        "G_R2_detail": {"repaired_logistic": repaired_log, "repaired_tree": repaired_tree,
                        "oracle_true_regime_logistic": oracle_log,
                        "frozen_router_logistic": router_log},
        "G_R2_sensitivity_rich_surface_cue": sensitivity,
        "G_R3": G_R3,
        "regime_winrate_table_true": true_table,
        "regime_winrate_table_repaired": rep_table,
        "verdict": verdict,
        "prior": {"cx_cheap1": "oracle TRUE-regime within-set AUC 0.6173; frozen router 0.5003; "
                               "win-rate|disagree negation 0.754 vs 0.40-0.51 elsewhere",
                  "ring_cx2": "cheap trained logistic detects the REGIME (3.26x, prec 0.805)"},
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cx_cheap2_results.json").write_text(json.dumps(out, indent=2))

    print("=== WIRING ===")
    print(f"router held-out top-1 = {router_acc:.6f} (booked {book}) match4dp={out['wiring']['match_4dp']}")
    print(f"n_disagree={int(sub_he.sum())} n_win={int(w_he[sub_he].sum())} "
          f"win_rate|disagree={out['wiring']['win_rate_given_disagree']}")
    print("=== G-R1 0-PARAM SURFACE REGIME ID ===")
    print(f"  held-out acc {full_held_acc:.4f} (need 0.70) -> {'PASS' if G_R1['pass_'] else 'FAIL'}"
          f" | train {train_acc:.4f}")
    print(f"  within-disagreement acc {sub_sr_acc:.4f} | frozen-router within acc {router_sub_acc:.4f}")
    print(f"  per-regime held-out: {per_regime_acc}")
    print("  confusion (rows=true, cols=pred) full held-out:")
    print("     " + " ".join(f"{r[:9]:>10}" for r in REGIMES))
    for t in REGIMES:
        print(f"  {t[:16]:<17}" + " ".join(f"{conf_full[t][p]:>10}" for p in REGIMES))
    print("  confusion within-disagreement:")
    for t in REGIMES:
        print(f"  {t[:16]:<17}" + " ".join(f"{conf_sub[t][p]:>10}" for p in REGIMES))
    print("=== G-R2 REPAIRED-LABEL WITHIN-SET WIN AUC ===")
    print(f"  logistic {G_R2['within_auc']} | tree {G_R2['tree_within_auc']} | best "
          f"{G_R2['best_within_auc']} (need 0.60) -> {'PASS' if G_R2['pass_'] else 'FAIL'}")
    print(f"  refs: true-regime oracle {G_R2['reference_true_regime_oracle_auc']} | "
          f"frozen router {G_R2['reference_frozen_router_auc']}")
    print(f"=== G-R2 SENSITIVITY (richer surface cue, post-hoc) ===")
    print(f"  board {sensitivity['board_acc']} within-acc {sensitivity['within_disagreement_acc']} "
          f"withinAUC {sensitivity['within_auc_logistic']} -> "
          f"{'PASS' if sensitivity['pass_'] else 'FAIL'} (ceiling perfect labels "
          f"{sensitivity['ceiling_perfect_labels_auc']})")
    print(f"=== G-R3 bootstrap ===")
    print(f"  boot aucs {G_R3['boot_aucs']} std {G_R3['boot_std_auc']} "
          f"-> {'PASS' if G_R3['pass_'] else 'INCONCLUSIVE'}")
    print(f"  win-rate|disagree TRUE  : {[(r, true_table[r]['win_rate_given_disagree']) for r in REGIMES]}")
    print(f"  win-rate|disagree REPAIR: {[(r, rep_table[r]['win_rate_given_disagree']) for r in REGIMES]}")
    print(f"=== VERDICT ===\n  {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
