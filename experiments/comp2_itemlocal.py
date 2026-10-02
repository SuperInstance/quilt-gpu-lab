#!/usr/bin/env python3
"""COMPOSITE-2 phase 3 — C2-IL: the ITEM-LOCAL sensor corpus (CPU-only, 0 GPU-Wh).

Pre-registered: proposals/runs/C2-item-local.md (+ AMENDMENT 1, pre-run, disclosed).
Question (COMP2 §10): does a federation premium exist where the CORRECT SENSOR is
ITEM-LOCAL?  Corpus = conjunctive dual-view items: canon iff BOTH the polarity channel
and a second channel agree; every distortion violates EXACTLY ONE channel, the violated
channel drawn i.i.d. PER ITEM, independent of the regime tag (so no regime-level sensor
table can carry the answer).

NO NEW BANKS (prereg §3): the 45 frozen COMP2 banks are scored CPU-side; per-view cheap
logistics are refit CPU-side.  0 GPU-Wh, no guard window.

Modes:  --pilot (disclosed small-N direction-finding, not a booking) | --run (default)
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

LAB = Path(__file__).resolve().parents[1]
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

from experiments.comp1_federation2 import (  # noqa: E402
    SUBJECTS, VERBS, CARGOS, DOCKS, COUNTS, NATIVE_STYLE, _rng, _sha256, _pick,
)
from experiments.comp2_arms import FEAT, SENSORS, REGIMES  # noqa: E402

OUT = LAB / "results" / "comp2_itemlocal"
BANKS = LAB / "results" / "comp2" / "banks"
CORPUS_SEED = 2718
N_TARGET = 12000
PER_REGIME = N_TARGET // len(REGIMES)          # 3,000
SEEDS = [2718, 2719, 2720]
BOOT_B = 2000
BOOT_SEED = 2718
D = 64
H_CELL = 16
H_JOINT = 64
VARIANT = os.environ.get("C2IL_VARIANT", "B")   # A = polarity+count, B = polarity+semantic


# ── C2-IL corpus (prereg §2 + AMENDMENT 1) ──────────────────────────────────
def render_evidence_il(style, subj, verb, cargo, dock, n, deny):
    if style == "manifest":
        if deny:
            return f"manifest: {dock} -> no {n} crates {cargo} listed, signed {subj}."
        return f"manifest: {dock} -> {n} crates {cargo}, signed {subj}."
    if style == "prose":
        if deny:
            return f"{subj} did not {verb} the {n} crates of {cargo} at {dock}."
        return f"{subj} brought a {cargo} shipment of {n} crates to {dock}."
    if style == "passive":
        if deny:
            return f"the {n} {cargo} crates at {dock} were not {verb} by {subj}."
        return f"the {n} {cargo} crates at {dock} were {verb} by {subj}."
    if deny:
        return f"per the harbor log, no {n} crates of {cargo} were {verb} at {dock}."
    return f"per the harbor log, {n} crates of {cargo} were {verb} at {dock} by {subj}."


def gen_item_il(rng, kind: str, i: int, variant: str = "B") -> dict:
    """Prereg §2 draw order verbatim; `variant` = the non-polarity channel (AMENDMENT 1)."""
    subj = _pick(rng, SUBJECTS)
    verb = _pick(rng, VERBS)
    cargo = _pick(rng, CARGOS)
    dock = _pick(rng, DOCKS)
    n = _pick(rng, COUNTS)
    deny = (rng() < 0.5)
    canon = (i % 2 == 0)

    e_subj, e_verb, e_cargo, e_dock, e_n, e_deny = subj, verb, cargo, dock, n, deny
    channel = None
    if not canon:
        if rng() < 0.5:                       # violated channel, i.i.d. per item
            e_deny = not deny
            channel = "polarity"
        elif variant == "A":                  # count channel (prereg as frozen)
            j = COUNTS.index(n)
            e_n = COUNTS[(j + (1 if rng() < 0.5 else -1)) % len(COUNTS)]
            channel = "count"
        elif variant == "C":                  # agent channel
            e_subj = _pick(rng, SUBJECTS, exclude=[subj])
            channel = "agent"
        else:                                 # B: semantic channel (cargo or dock)
            if rng() < 0.5:
                e_cargo = _pick(rng, CARGOS, exclude=[cargo])
                channel = "cargo"
            else:
                e_dock = _pick(rng, DOCKS, exclude=[dock])
                channel = "dock"

    claim = (f"{subj} did not {verb} the {cargo} crates at {dock}." if deny
             else f"{subj} {verb} the {cargo} crates at {dock}.")
    style = NATIVE_STYLE[kind]
    evid = render_evidence_il(style, e_subj, e_verb, e_cargo, e_dock, e_n, e_deny)
    return {"claim": claim, "evidence": evid, "ev_style": style,
            "label": "canon" if canon else "distortion", "kind": kind, "channel": channel}


def gen_corpus_il(per_regime=PER_REGIME, variant=VARIANT):
    rng = _rng(CORPUS_SEED)
    items, seen, regen = [], set(), 0
    for kind in REGIMES:
        made = 0
        while made < per_regime:
            it = gen_item_il(rng, kind, made, variant)
            h = _sha256(it["claim"] + " " + it["evidence"])
            if h in seen:
                regen += 1
                continue
            seen.add(h)
            it["sha256"] = h
            items.append(it)
            made += 1
    train = [it for it in items if int(it["sha256"][0], 16) < 12]
    held = [it for it in items if int(it["sha256"][0], 16) >= 12]
    return train, held, {"n_raw": len(items), "regen_collisions": regen}


def sha_sequence(items):
    return hashlib.sha256("".join(it["sha256"] for it in items).encode()).hexdigest()


def y_of(it):
    return 1 if it["label"] == "canon" else 0


def featurize(items):
    return {s: np.stack([FEAT[s](it) for it in items]).astype(np.float32) for s in SENSORS}


# ── torch bank inference (CPU) ──────────────────────────────────────────────
def load_bank(path, hid):
    import torch
    import torch.nn as nn
    m = nn.Sequential(nn.Linear(D, hid), nn.Tanh(), nn.Linear(hid, 1))
    m.load_state_dict(torch.load(path, map_location="cpu"))
    m.eval()
    return m


def infer(model, X):
    import torch
    with torch.no_grad():
        return torch.sigmoid(model(torch.tensor(X)).squeeze(-1)).numpy().astype(np.float64)


# ── bootstrap + gates (COMP2 law) ───────────────────────────────────────────
def boot_ci(d, b=BOOT_B, seed=BOOT_SEED):
    rng = np.random.default_rng(seed)
    n = len(d)
    draws = np.empty(b)
    for k in range(b):
        draws[k] = d[rng.integers(0, n, n)].mean()
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return {"diff": round(float(d.mean()), 4), "ci95": [round(float(lo), 4), round(float(hi), 4)]}


def gate(correct, a, b, idx=None, bar=None, label=None):
    sel = np.arange(correct[a].shape[1]) if idx is None else idx
    va = correct[a][:, sel].mean(axis=0)
    vb = correct[b][:, sel].mean(axis=0)
    ci = boot_ci(va - vb)
    sa = float(correct[a][:, sel].mean(axis=1).std())
    sb = float(correct[b][:, sel].mean(axis=1).std())
    deg = (sa == 0.0) or (sb == 0.0)
    pt_ok = (ci["diff"] >= bar) if bar is not None else (ci["diff"] > 0)
    verdict = ("INCONCLUSIVE (std==0 law)" if deg else
               ("PASS" if (pt_ok and ci["ci95"][0] > 0) else "FAIL"))
    return {"comparison": label or f"{a} - {b}", "diff": ci["diff"], "ci95": ci["ci95"],
            "bar": bar, "std_a": round(sa, 4), "std_b": round(sb, 4),
            "std0_a": sa == 0.0, "std0_b": sb == 0.0, "verdict": verdict}


def route_minp(P, ss):
    return np.min(np.stack([P[s] for s in ss]), axis=0)


def route_margin(P, ss):
    M = np.stack([P[s] for s in ss])
    k = np.argmax(np.abs(M - 0.5), axis=0)
    return M[k, np.arange(M.shape[1])]


def route_majority(P, ss):
    M = np.stack([P[s] for s in ss])
    v = (M >= 0.5).sum(0)
    half = len(ss) / 2.0
    return np.where(v > half, 1.0, np.where(v < half, 0.0, np.min(M, axis=0) >= 0.5))


def fit_gate(Ptr_cells, y_tr, view_names):
    """Learned item-local router: per-cell p -> multinomial logistic -> best cell.
    Target = the cell whose verdict is correct with the largest margin (TRAIN)."""
    from sklearn.linear_model import LogisticRegression
    X = np.stack([Ptr_cells[s] for s in view_names], axis=1)
    ok = ((X >= 0.5) == (y_tr[:, None] == 1))
    tgt = np.argmax(np.where(ok, np.abs(X - 0.5), -1.0), axis=1)
    clf = LogisticRegression(solver="lbfgs", C=1.0, max_iter=3000,
                             random_state=BOOT_SEED).fit(X, tgt)
    return clf, X.shape[1] * (len(view_names) + 0)


def apply_gate(clf, Phe_cells, view_names):
    X = np.stack([Phe_cells[s] for s in view_names], axis=1)
    pick = clf.predict(X)
    return X[np.arange(len(pick)), pick]


def main(out_dir: Path, pilot: bool = False) -> int:
    import torch  # noqa: F401
    from sklearn.linear_model import LogisticRegression
    t0 = time.time()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "predictions").mkdir(exist_ok=True)

    per_regime = 1000 if pilot else PER_REGIME
    variant = VARIANT
    train, held, gen_stats = gen_corpus_il(per_regime, variant)
    n_tr, n_he = len(train), len(held)
    reg_t = np.array([it["kind"] for it in train])
    reg_h = np.array([it["kind"] for it in held])
    y_tr = np.array([y_of(it) for it in train])
    y_he = np.array([y_of(it) for it in held])
    ch_h = np.array([it["channel"] or "none" for it in held])
    idx = {r: np.array([i for i, rg in enumerate(reg_h) if rg == r]) for r in REGIMES}
    grp = {"canon": np.where(y_he == 1)[0]}
    for c in sorted({c for c in ch_h if c != "none"}):
        grp[f"dist_{c}"] = np.where((y_he == 0) & (ch_h == c))[0]

    # validity + W1
    t2, h2, _ = gen_corpus_il(per_regime, variant)
    determinism = sha_sequence(train + held) == sha_sequence(t2 + h2)
    per_held = {r: int(len(idx[r])) for r in REGIMES}
    per_viol = {}
    for r in REGIMES:
        d = [it for it in held if it["kind"] == r and it["label"] == "distortion"]
        per_viol[r] = round(float(np.mean([it["channel"] == "polarity" for it in d])), 4) if d else None
    validity = {"n_raw": gen_stats["n_raw"],
                "n_unique": len({it["sha256"] for it in train + held}),
                "regen_collisions": gen_stats["regen_collisions"], "n_train": n_tr,
                "n_heldout": n_he, "per_regime_heldout": per_held,
                "canon_frac_heldout": round(float(y_he.mean()), 4),
                "per_regime_canon_frac": {r: round(float(y_he[idx[r]].mean()), 4) for r in REGIMES},
                "per_regime_polarity_frac_of_distortions": per_viol,
                "determinism_w1": bool(determinism)}
    chance = {"full": round(float(max(y_he.mean(), 1 - y_he.mean())), 4)}
    for r in REGIMES:
        yr = y_he[idx[r]]
        chance[r] = round(float(max(yr.mean(), 1 - yr.mean())), 4)

    # ── features ───────────────────────────────────────────────────────────
    F_tr, F_he = featurize(train), featurize(held)

    # frozen MLP per-sensor cells (seed-specific)
    Pmlp_tr = {sd: {s: infer(load_bank(BANKS / f"HETERO_{s}_seed{sd}.pt", H_CELL), F_tr[s])
                    for s in SENSORS} for sd in SEEDS}
    Pmlp_he = {sd: {s: infer(load_bank(BANKS / f"HETERO_{s}_seed{sd}.pt", H_CELL), F_he[s])
                    for s in SENSORS} for sd in SEEDS}
    Pj_tr = {sd: infer(load_bank(BANKS / f"JOINT_seed{sd}.pt", H_JOINT), F_tr["S1"]) for sd in SEEDS}
    Pj_he = {sd: infer(load_bank(BANKS / f"JOINT_seed{sd}.pt", H_JOINT), F_he["S1"]) for sd in SEEDS}

    # cheap per-view cells (bootstrap-resampled refits, one per "seed")
    Pc_tr, Pc_he = {}, {}
    for k, cs in enumerate(SEEDS):
        b = np.random.default_rng(cs).integers(0, n_tr, n_tr)
        Pc_tr[k], Pc_he[k] = {}, {}
        for s in SENSORS:
            clf = LogisticRegression(solver="lbfgs", C=1.0, max_iter=3000,
                                     random_state=cs).fit(F_tr[s][b], y_tr[b])
            Pc_tr[k][s] = clf.predict_proba(F_tr[s])[:, 1]
            Pc_he[k][s] = clf.predict_proba(F_he[s])[:, 1]

    # ── arms ───────────────────────────────────────────────────────────────
    pmat = {}
    for s in SENSORS:                                        # frozen MLP singles
        pmat[s] = np.stack([Pmlp_he[sd][s] for sd in SEEDS])
    pmat["S4-MONO"] = pmat["S4"].copy()
    pmat["JOINT"] = np.stack([Pj_he[sd] for sd in SEEDS])
    for s in SENSORS:                                        # cheap singles
        pmat[f"PV-cheap-{s}"] = np.stack([Pc_he[k][s] for k in range(len(SEEDS))])
    pmat["S1-cheap"] = pmat["PV-cheap-S1"].copy()

    # 0-param MLP-family federations
    pmat["FED-IL"] = np.stack([route_minp(Pmlp_he[sd], SENSORS) for sd in SEEDS])
    pmat["FED-IL-2S"] = np.stack([route_minp(Pmlp_he[sd], ["S1", "S4"]) for sd in SEEDS])
    pmat["FED-IL-MARGIN"] = np.stack([route_margin(Pmlp_he[sd], SENSORS) for sd in SEEDS])
    pmat["FED-IL-MAJ"] = np.stack([route_majority(Pmlp_he[sd], SENSORS) for sd in SEEDS])

    # learned routers / combiners (per seed, TRAIN-fit)
    nparam = {}

    def _router(arm, trc_by_k, hec_by_k, names):
        rows = []
        for k in range(len(SEEDS)):
            clf, _ = fit_gate(trc_by_k[k], y_tr, names)
            rows.append(apply_gate(clf, hec_by_k[k], names))
            nparam[arm] = int(clf.coef_.size + clf.intercept_.size)
        pmat[arm] = np.stack(rows)

    mlp_tr_k = {k: Pmlp_tr[sd] for k, sd in enumerate(SEEDS)}
    mlp_he_k = {k: Pmlp_he[sd] for k, sd in enumerate(SEEDS)}
    _router("FED-IL-GATE", mlp_tr_k, mlp_he_k, SENSORS)
    _router("FED-CHEAP-GATE", Pc_tr, Pc_he, SENSORS)
    g8_tr = {k: {**{f"m_{s}": mlp_tr_k[k][s] for s in SENSORS},
                 **{f"c_{s}": Pc_tr[k][s] for s in SENSORS}} for k in range(len(SEEDS))}
    g8_he = {k: {**{f"m_{s}": mlp_he_k[k][s] for s in SENSORS},
                 **{f"c_{s}": Pc_he[k][s] for s in SENSORS}} for k in range(len(SEEDS))}
    _router("FED-GATE-8", g8_tr, g8_he, list(g8_tr[0].keys()))

    # logistic stackers on the per-cell logits (combiner, not router; secondary)
    for arm, tr_src, he_src in (("FED-CHEAP-STACK", Pc_tr, Pc_he),):
        rows = []
        for k in range(len(SEEDS)):
            Ltr = np.log(np.clip(np.stack([tr_src[k][s] for s in SENSORS], axis=1), 1e-6, 1 - 1e-6) /
                         (1 - np.clip(np.stack([tr_src[k][s] for s in SENSORS], axis=1), 1e-6, 1 - 1e-6)))
            Lhe = np.log(np.clip(np.stack([he_src[k][s] for s in SENSORS], axis=1), 1e-6, 1 - 1e-6) /
                         (1 - np.clip(np.stack([he_src[k][s] for s in SENSORS], axis=1), 1e-6, 1 - 1e-6)))
            clf = LogisticRegression(solver="lbfgs", C=1.0, max_iter=3000,
                                     random_state=BOOT_SEED).fit(Ltr, y_tr)
            rows.append(clf.predict_proba(Lhe)[:, 1])
        pmat[arm] = np.stack(rows)

    # ── correctness + BEST-SINGLE ──────────────────────────────────────────
    correct = {a: ((pmat[a] >= 0.5) == (y_he == 1)[None, :]) for a in pmat}
    single_arms = SENSORS + [f"PV-cheap-{s}" for s in SENSORS]
    acc_single = {s: round(float(correct[s].mean()), 4) for s in single_arms}
    best_s = max(acc_single, key=acc_single.get)
    pmat["BEST-SINGLE"] = pmat[best_s].copy()
    correct["BEST-SINGLE"] = correct[best_s].copy()

    # oracle upper bound (per-item best single cell)
    Pall = np.stack([pmat[s].mean(axis=0) for s in single_arms], axis=1)      # (n, 8)
    ok = ((Pall >= 0.5) == (y_he[:, None] == 1))
    kor = np.argmax(np.where(ok, np.abs(Pall - 0.5), -1.0), axis=1)
    oracle_acc = float(np.take_along_axis(ok, kor[:, None], axis=1).mean())
    # deployable (TRAIN-selected) best single view -- no held-out peeking
    acc_single_tr = {}
    for s in SENSORS:
        acc_single_tr[s] = float(((np.stack([Pmlp_tr[sd][s] for sd in SEEDS]).mean(axis=0) >= 0.5)
                                  == (y_tr == 1)).mean())
        acc_single_tr[f"PV-cheap-{s}"] = float(((np.stack([Pc_tr[k][s] for k in range(len(SEEDS))])
                                                  .mean(axis=0) >= 0.5) == (y_tr == 1)).mean())
    best_s_tr = max(acc_single_tr, key=acc_single_tr.get)
    best_single_train_sel = {"pick": best_s_tr, "train_acc": round(acc_single_tr[best_s_tr], 4),
                             "held_acc": acc_single[best_s_tr]}
    # ── routing diagnostics (how resolvable is the item-local choice?) ─────
    Pmlp_n = np.stack([pmat[s].mean(axis=0) for s in SENSORS], axis=1)        # (n, 4) MLP
    ok_mlp = ((Pmlp_n >= 0.5) == (y_he[:, None] == 1))
    kor_mlp = np.argmax(np.where(ok_mlp, np.abs(Pmlp_n - 0.5), -1.0), axis=1)
    margin_pick = np.argmax(np.abs(Pmlp_n - 0.5), axis=1)
    routing = {
        "oracle_best_single_cell_acc_all8": round(oracle_acc, 4),
        "best_fixed_single_acc": round(acc_single[best_s], 4),
        "perfect_router_headroom_all8": round(oracle_acc - acc_single[best_s], 4),
        "margin_router_pick_agreement_with_oracle_mlp4": round(
            float((margin_pick == kor_mlp).mean()), 4),
        "frac_items_where_fixed_best_is_wrong_but_some_view_is_right": round(
            float((~ok_mlp[:, SENSORS.index(max(SENSORS, key=lambda s: acc_single[s]))]
                   & ok_mlp.any(axis=1)).mean()), 4),
        "n_single_arms": len(single_arms),
    }

    # ── boards ─────────────────────────────────────────────────────────────
    def boards_of(a):
        c = correct[a]
        out = {"full": round(float(c.mean()), 4)}
        for r in REGIMES:
            out[r] = round(float(c[:, idx[r]].mean()), 4)
        for g, ix in grp.items():
            out[g] = round(float(c[:, ix].mean()), 4) if len(ix) else None
        return out
    boards = {a: boards_of(a) for a in correct}
    seed_std = {a: round(float(correct[a].mean(axis=1).std()), 4) for a in correct}

    # ── gates ──────────────────────────────────────────────────────────────
    G_IL1_hits = {a: acc_single[a] for a in single_arms
                  if acc_single[a] >= chance["full"] + 0.02}
    G_IL1 = bool(G_IL1_hits)
    PRIM = "FED-CHEAP-GATE"
    G_IL2 = gate(correct, PRIM, "BEST-SINGLE", bar=0.05,
                 label=f"{PRIM} - BEST-SINGLE (full board)")
    G_IL2b = gate(correct, PRIM, "S4-MONO", bar=0.05, label=f"{PRIM} - S4-MONO")
    secondary = {f"{a} - BEST-SINGLE": gate(correct, a, "BEST-SINGLE")
                 for a in ("FED-IL", "FED-IL-2S", "FED-IL-MAJ", "FED-IL-MARGIN",
                           "FED-IL-GATE", "FED-GATE-8", "FED-CHEAP-STACK", "JOINT")}
    within = {"best_mlp_single": max(SENSORS, key=lambda s: acc_single[s]),
              "best_cheap_single": max([f"PV-cheap-{s}" for s in SENSORS],
                                       key=lambda s: acc_single[s]),
              "FED-IL-GATE - best_mlp_single": gate(correct, "FED-IL-GATE",
                                                    max(SENSORS, key=lambda s: acc_single[s])),
              "FED-CHEAP-GATE - best_cheap_single": gate(
                  correct, "FED-CHEAP-GATE",
                  max([f"PV-cheap-{s}" for s in SENSORS], key=lambda s: acc_single[s]))}
    per_regime_ci = {f"{PRIM} - BEST-SINGLE @{r}": gate(correct, PRIM, "BEST-SINGLE", idx[r])
                     for r in REGIMES}
    per_channel = {g: {a: boards[a][g] for a in ("FED-IL", "FED-IL-GATE", "FED-CHEAP-GATE",
                                                 "BEST-SINGLE", "S4-MONO", "S1")}
                   for g in grp}

    if not validity["determinism_w1"]:
        verdict, sentence = "INCONCLUSIVE_CORPUS (W1)", "determinism failed."
    elif not G_IL1:
        verdict = "CONSTRUCTION-FAILED"
        sentence = ("construction failed — items not genuinely dual-view (no single-view arm "
                    "clears chance + 0.02).")
    elif G_IL2["verdict"] == "INCONCLUSIVE (std==0 law)":
        verdict, sentence = "INCONCLUSIVE", "std==0 in a deciding pair — INCONCLUSIVE."
    elif G_IL2["verdict"] == "PASS":
        verdict = "PASS-FEDERATION-PREMIUM-ITEM-LOCAL"
        sentence = ("federation premium exists exactly where sensor choice is item-local — "
                    "the thesis is bounded, not dead.")
    else:
        verdict = "FAIL-NO-PREMIUM"
        sentence = ("no federation premium even item-local — the thesis narrows to sensor "
                    "selection, full stop.")
    if pilot:
        verdict, sentence = "PILOT-" + verdict, "PILOT (disclosed direction-finding; NOT a booking)"

    result = {
        "experiment": "COMPOSITE-2 phase 3 — C2-IL item-local sensor corpus",
        "prereg": "proposals/runs/C2-item-local.md", "mode": "pilot" if pilot else "run",
        "variant": variant, "cpu_only": True, "gpu_wh": 0.0, "new_banks": 0,
        "primary_arm": PRIM,
        "corpus": {"seed": CORPUS_SEED, "n_target": N_TARGET, "per_regime": per_regime,
                   "sha_sequence": sha_sequence(train + held), **validity},
        "chance_majority": chance, "sensors": SENSORS, "regimes": REGIMES,
        "arms": sorted(correct.keys()), "router_params": nparam,
        "boards_seedmean": boards, "seed_std": seed_std,
        "best_single_view": best_s, "single_view_acc": acc_single,
        "best_single_train_selected": best_single_train_sel,
        "oracle_route_acc": round(oracle_acc, 4), "routing_diagnostics": routing,
        "G_IL1": {"pass": G_IL1, "bar": round(chance["full"] + 0.02, 4), "hits": G_IL1_hits},
        "G_IL2": G_IL2, "G_IL2b": G_IL2b, "secondary": secondary, "within_family": within,
        "per_regime_ci": per_regime_ci, "per_channel": per_channel,
        "verdict": verdict, "booked_sentence": sentence,
        "wall_seconds": round(time.time() - t0, 1)}
    if pilot:
        (out_dir / "pilot_results.json").write_text(json.dumps(result, indent=2))
    else:
        (out_dir / "il_results.json").write_text(json.dumps(result, indent=2))
        (out_dir / "corpus.jsonl").write_text("\n".join(json.dumps(it) for it in train + held) + "\n")
        (out_dir / "per_item_stub.jsonl").write_text("\n".join(
            json.dumps({"sha256": it["sha256"], "key": it["sha256"][:16], "regime": it["kind"],
                        "label": it["label"], "channel": it["channel"],
                        "split": "train" if int(it["sha256"][0], 16) < 12 else "heldout",
                        "p": None, "correct": None, "margin": None,
                        "routed_sensor": None, "cell": None}) for it in train + held) + "\n")
        write_predictions(out_dir, held, y_he, pmat, correct)

    print("VERDICT " + verdict, flush=True)
    print("SENTENCE " + sentence, flush=True)
    print("G_IL1 " + json.dumps(G_IL1_hits), flush=True)
    print("G_IL2 " + json.dumps(G_IL2), flush=True)
    print("G_IL2b " + json.dumps(G_IL2b), flush=True)
    print("within " + json.dumps(within), flush=True)
    print("routing " + json.dumps(routing), flush=True)
    print("full_boards " + json.dumps({k: boards[k]["full"] for k in sorted(boards)}), flush=True)
    print("oracle " + str(round(oracle_acc, 4)), flush=True)
    print("wall %.1fs" % (time.time() - t0), flush=True)
    return 0


def write_predictions(out_dir, held, y_he, pmat, correct):
    base = [{"sha256": it["sha256"], "key": it["sha256"][:16], "regime": it["kind"],
             "label": it["label"], "channel": it["channel"], "split": "heldout"} for it in held]
    for arm, Pm in pmat.items():
        seeds = SEEDS
        with gzip.open(out_dir / "predictions" / f"{arm}.jsonl.gz", "wt") as fh:
            for si in range(Pm.shape[0]):
                for j, b in enumerate(base):
                    p = float(Pm[si, j])
                    row = dict(b)
                    row.update({"arm": arm, "seed": seeds[si] if si < len(seeds) else si,
                                "p": round(p, 6), "correct": bool(correct[arm][si, j]),
                                "margin": round(abs(p - 0.5), 6),
                                "routed_sensor": None, "cell": arm})
                    fh.write(json.dumps(row) + "\n")


if __name__ == "__main__":
    args = sys.argv[1:]
    out = OUT
    if "--out" in args:
        out = Path(args[args.index("--out") + 1])
    sys.exit(main(out, pilot="--pilot" in args))
