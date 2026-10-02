#!/usr/bin/env python3
"""COMPOSITE-2 phase 2 — ARMS (federation v3): 6 MLP banks x 3 seeds + sensor router.

Pre-registered: proposals/runs/COMPOSITE-2-federation3.md (frozen 2026-10-01 17:2x,
phase 1 GREEN at results/comp2_corpus/, corpus frozen iteration 5).
Phase 1 (corpus + F-gate) is a DIFFERENT lane's artifact and is read here read-only.

Two measured phases, deliberately split by cost-accounting law:

  --inner  (GPU, GUARDED): the only GPU-touching work. Trains the 6 banks x 3 seeds,
           saves checkpoints + raw per-item margins + sensor feature matrices.
           Wrapped by guard.py (G7 watt receipt; INSTRUMENT-01 ramp >=0.6 s first).
  --cpu    (CPU, 0 GPU-Wh): sensor router fit, LA, per-item predictions, bootstrap
           gates P1/P2/P3, secondary full-board, cheap-arm 361p bracket G4a/G4b.

The CPU phase is run OUTSIDE the guard window on purpose: the G7 receipt reports the
whole window the job held the GPU (idle floor NOT subtracted), so routing/bootstrap
work must not inflate the booked Wh.

Run:  python -m experiments.comp2_arms            (outer: guarded inner, then cpu)
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

OUT_DIR = LAB / "results" / "comp2"
CORPUS = LAB / "results" / "comp2_corpus" / "corpus.jsonl"
COMP1_CORPUS = LAB / "results" / "comp1" / "corpus.jsonl"

GUARD_TIMEOUT_S = 3600.0
SEEDS = [2718, 2719, 2720]
ROUTER_SEED = 2718
D = 64
H_CELL = 16
H_JOINT = 64
LR = 1e-3
BATCH = 16
EP_ALL = 30          # all-train arms/cells -> ~551k updates
EP_SLICE = 30        # slice cells on ~4.6k items -> ~138k updates
BOOT_B = 2000
BOOT_B_TOPUP = 10000
TAU_PCT = 20
ROUTER_LO, ROUTER_HI = 0.40, 0.95

REGIMES = ["semantic", "counting-address", "negation-scope", "agent-role"]
SENSORS = ["S1", "S2", "S3", "S4"]
# Frozen structural assignment table (prereg §3, declared BEFORE calibration).
MATCH = {"semantic": "S2", "counting-address": "S1",
         "negation-scope": "S4", "agent-role": "S3"}
SENSOR_OF_REGIME = MATCH
REGIME_OF_SENSOR = {v: k for k, v in MATCH.items()}
ARM_NAMES = ["JOINT", "SINGLE", "S4MONO", "FED_WORD", "FED_HETERO",
             "FED_HE_MATCHED", "FED_LA"]

# COMP1 booked boards (frozen bracket targets, W5 provenance).
COMP1_FED_BOARDS = {"full": 0.5605, "semantic": 0.5816,
                    "counting-address": 0.5731, "negation-scope": 0.5541,
                    "agent-role": 0.5370}
COMP1_CORPUS_SHA = "c195e558f49c98c81c33eecf6ce07a7e37d3b452663bf796e510c03deaac604f"

NEG_MARKERS = {"not", "no", "never", "none", "without", "n't", "cannot"}
COUNT_WORDS = {"two", "three", "four", "five", "six", "seven", "eight", "nine"}


# ── corpus io ───────────────────────────────────────────────────────────────
def load_corpus(path: Path) -> tuple[list, list]:
    items = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    for it in items:
        it["regime"] = it.get("kind") or it.get("regime")
        it["split"] = "train" if int(it["sha256"][0], 16) < 12 else "heldout"
    train = [it for it in items if it["split"] == "train"]
    held = [it for it in items if it["split"] == "heldout"]
    return train, held


# ── sensors (VIEW is the manipulated variable; prereg §2, frozen) ────────────
from experiments.comp1_federation2 import (  # noqa: E402
    _tok, feat_word, feat_char, pearson, y_of, _rng, _sha256,
)

_H = lambda s: int(hashlib.sha1(s.encode()).hexdigest(), 16)


def _l2(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def feat_pos(item: dict) -> np.ndarray:
    """S3 positional: ordered adjacent bigrams (w_i,w_{i+1}) |o| (token,pos-bucket).
    Buckets: 0-2 -> 0, 3-5 -> 1, 6+ -> 2. 32 dims + 32 dims -> D=64."""
    toks = _tok(item["claim"] + " " + item["evidence"])
    v = np.zeros(D, dtype=np.float32)
    for i in range(len(toks) - 1):
        v[_H("bg|" + toks[i] + "|" + toks[i + 1]) % 32] += 1.0
    for i, t in enumerate(toks):
        b = 0 if i <= 2 else (1 if i <= 5 else 2)
        v[32 + _H("tp|" + t + "|" + str(b)) % 32] += 1.0
    return _l2(v)


def feat_neg(item: dict) -> np.ndarray:
    """S4 negation-marker-aware: word BoW (60 dims) |o| 4 explicit dims ->
    [in-claim neg marker, in-evidence neg marker, XOR, count-word present]. D=64."""
    v = np.zeros(D, dtype=np.float32)
    for tok in _tok(item["claim"] + " " + item["evidence"]):
        v[_H("w|" + tok) % 60] += 1.0
    ct, et = set(_tok(item["claim"])), set(_tok(item["evidence"]))
    nc = 1.0 if (ct & NEG_MARKERS) else 0.0
    ne = 1.0 if (et & NEG_MARKERS) else 0.0
    v[60] = nc
    v[61] = ne
    v[62] = 1.0 if (nc != ne) else 0.0
    v[63] = 1.0 if ((ct | et) & COUNT_WORDS) else 0.0
    return _l2(v)


FEAT = {"S1": feat_word, "S2": feat_char, "S3": feat_pos, "S4": feat_neg}


def featurize(items: list, sensors=SENSORS) -> dict:
    return {s: np.stack([FEAT[s](it) for it in items]).astype(np.float32)
            for s in sensors}


# ── torch training (inner/GPU only) ─────────────────────────────────────────
def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except Exception:
        return default


def train_mlp(X, Y, hid: int, seed: int, epochs: int):
    """Adam/BCE, batch 16, fp32. Returns (model, meta) with first/last epoch loss."""
    import torch.nn as nn
    import torch
    torch.manual_seed(seed)
    model = nn.Sequential(nn.Linear(D, hid), nn.Tanh(), nn.Linear(hid, 1)).to(X.device)
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    lf = nn.BCEWithLogitsLoss()
    n = len(X)
    first = last = None
    step = 0
    for ep in range(epochs):
        perm = torch.randperm(n, device=X.device)
        want = (ep == 0 or ep == epochs - 1)
        tot = 0.0
        for i in range(0, n, BATCH):
            idx = perm[i:i + BATCH]
            opt.zero_grad()
            loss = lf(model(X[idx]).squeeze(-1), Y[idx])
            loss.backward()
            opt.step()
            step += 1
            if step % 200 == 0:
                lv = float(loss.detach())
                import math
                if not math.isfinite(lv):          # fail loud: bank dies -> booked
                    raise RuntimeError(
                        f"DIVERGENCE: non-finite loss ({lv}) at epoch {ep} step {step} "
                        f"(hid={hid} seed={seed}) — bank dies, NOT re-rolled")
            if want:
                tot += float(loss.detach()) * len(idx)
        if want:
            if ep == 0:
                first = tot / n
            last = tot / n
    meta = {"hid": hid, "epochs": epochs, "updates": int(n * epochs),
            "loss_first": round(float(first), 5), "loss_last": round(float(last), 5),
            "loss_decreased": bool(last <= first)}
    return model, meta


def predict(model, X) -> np.ndarray:
    import torch
    with torch.no_grad():
        return torch.sigmoid(model(X).squeeze(-1)).cpu().numpy()


def ramp_burn(device) -> dict:
    import torch
    a = torch.randn(2048, 2048, device=device)
    t0 = time.time()
    while time.time() - t0 < 0.6:
        for _ in range(20):
            a = a @ a
            a = a / a.norm()
        torch.cuda.synchronize()
    return {"ramp_s": round(time.time() - t0, 3), "synced": True}


# ── inner (GPU, measured, guarded) ──────────────────────────────────────────
def run_inner(out_dir: Path) -> int:
    import torch
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "banks").mkdir(exist_ok=True)
    (out_dir / "raw").mkdir(exist_ok=True)
    t_start = time.time()

    ep_all = _env_int("COMP2_EP_ALL", EP_ALL)
    ep_slice = _env_int("COMP2_EP_SLICE", EP_SLICE)
    limit = _env_int("COMP2_LIMIT", 0)

    train, held = load_corpus(CORPUS)
    corpus_sha = hashlib.sha256(CORPUS.read_bytes()).hexdigest()
    if limit:
        train, held = train[:limit], held[:limit]
    n_tr, n_he = len(train), len(held)
    y_tr = np.array([y_of(it) for it in train], dtype=np.float32)
    y_he = np.array([y_of(it) for it in held], dtype=np.float32)

    tr_f = featurize(train)
    he_f = featurize(held)
    np.savez_compressed(out_dir / "raw" / "features.npz",
                        **{f"tr_{s}": tr_f[s] for s in SENSORS},
                        **{f"he_{s}": he_f[s] for s in SENSORS})

    T = {s: torch.tensor(tr_f[s], device=device) for s in SENSORS}
    H = {s: torch.tensor(he_f[s], device=device) for s in SENSORS}
    Ytr = torch.tensor(y_tr, device=device)

    ramp = ramp_burn(device) if device.type == "cuda" else {"ramp_s": 0.0, "synced": True}

    slices = {r: np.array([i for i, it in enumerate(train) if it["regime"] == r])
              for r in REGIMES}
    slice_sizes = {r: int(len(v)) for r, v in slices.items()}

    # register all banks to train (7 all-train + 8 slice per seed = ~4.96M updates)
    banks = []
    for si, seed in enumerate(SEEDS):
        torch.manual_seed(seed)
        banks += [
            (si, seed, "JOINT", "S1", "all", None, H_JOINT, ep_all),
            (si, seed, "SINGLE", "S1", "all", None, H_CELL, ep_all),
            (si, seed, "S4MONO", "S4", "all", None, H_CELL, ep_all),
        ]
        for r in REGIMES:
            banks.append((si, seed, f"FEDWORD:{r}", "S1", "slice", r, H_CELL, ep_slice))
        for s in SENSORS:
            banks.append((si, seed, f"HETERO:{s}", s, "all", None, H_CELL, ep_all))
        for r in REGIMES:
            banks.append((si, seed, f"HEMATCH:{r}", MATCH[r], "slice", r, H_CELL, ep_slice))

    per_seed = {}
    meta_all = []
    wall_marks = []
    for (si, seed, name, sensor, kind, regime, hid, eps) in banks:
        if kind == "all":
            X, Y, idx = T[sensor], Ytr, None
        else:
            idx = torch.tensor(slices[regime], device=device)
            X, Y = T[sensor][idx], Ytr[idx]
        model, meta = train_mlp(X, Y, hid, seed, eps)
        tag = name.replace(":", "_") + f"_seed{seed}"
        torch.save(model.state_dict(), out_dir / "banks" / f"{tag}.pt")
        meta.update({"seed": seed, "bank": name, "sensor": sensor,
                     "kind": kind, "regime": regime, "n_items": int(len(X))})
        meta_all.append(meta)
        d = per_seed.setdefault(si, {})
        if name == "JOINT":
            d["p_joint"] = predict(model, H["S1"])
        elif name == "SINGLE":
            d["p_single"] = predict(model, H["S1"])
        elif name == "S4MONO":
            d["p_s4mono"] = predict(model, H["S4"])
        elif name.startswith("FEDWORD:"):
            d[f"p_fedword:{name.split(':')[1]}"] = predict(model, H["S1"])
        elif name.startswith("HETERO:"):
            s = name.split(":")[1]
            d[f"p_hetero:{s}"] = predict(model, H[s])
            d[f"p_hetero_train:{s}"] = predict(model, T[s])
        elif name.startswith("HEMATCH:"):
            d[f"p_hematch:{name.split(':')[1]}"] = predict(model, H[MATCH[name.split(':')[1]]])
        print(f"[inner] seed{seed} {tag} updates={meta['updates']} "
              f"loss {meta['loss_first']}->{meta['loss_last']}", flush=True)
        wall_marks.append({"bank": tag, "t": round(time.time() - t_start, 1)})

    for si, d in per_seed.items():
        np.savez_compressed(out_dir / "raw" / f"seed{SEEDS[si]}.npz", **d)

    report = {
        "phase": "inner", "device": str(device), "torch": torch.__version__,
        "corpus": str(CORPUS), "corpus_sha256": corpus_sha,
        "n_train": n_tr, "n_heldout": n_he, "regimes": REGIMES,
        "slice_sizes": slice_sizes, "sensors": SENSORS, "match_table": MATCH,
        "epochs_all": ep_all, "epochs_slice": ep_slice, "batch": BATCH, "lr": LR,
        "seeds": SEEDS, "n_banks": len(meta_all),
        "total_updates": int(sum(m["updates"] for m in meta_all)),
        "banks": meta_all, "ramp_receipt": ramp,
        "wall_seconds": round(time.time() - t_start, 1),
        "wall_marks": wall_marks,
    }
    (out_dir / "inner_report.json").write_text(json.dumps(report, indent=2))
    print("INNER OK updates=%d wall=%.1fs" % (report["total_updates"], report["wall_seconds"]),
          flush=True)
    return 0


# ── router (36p) + LA + boards + gates (CPU) ────────────────────────────────
def _centroid_scores(F_tr, F_q, reg_tr, sensors=SENSORS):
    """4 per-sensor centroid-Pearson scores (0-param geometry, COMP1/D13d law).

    Sensor k's key = the centroid, IN SENSOR k'S OWN SPACE, of the train items of
    the regime sensor k is structurally tuned to (frozen MATCH table). score_k =
    Pearson(feat_Sk(item), key_k). 4 features -> 1 per sensor. Disclosed: this is
    the literal reading of '4 per-sensor centroid-Pearson scores'."""
    cents = {s: F_tr[s][reg_tr == REGIME_OF_SENSOR[s]].mean(axis=0) for s in sensors}
    return np.stack([[pearson(F_q[s][i], cents[s]) for s in sensors]
                     for i in range(len(F_q["S1"]))], axis=0)


def per_regime_centroid_order(F_tr, F_q, reg_tr, sensors=SENSORS):
    """COMP1 CorrRouter VERBATIM on the S1 view: per-REGIME centroid keys in S1
    space, held items ranked by Pearson. 0 params. Used by FED_WORD."""
    cents = {r: F_tr["S1"][reg_tr == r].mean(axis=0) for r in REGIMES}
    sc = np.stack([[pearson(F_q["S1"][i], cents[r]) for r in REGIMES]
                   for i in range(len(F_q["S1"]))], axis=0)
    return np.argsort(-sc, axis=1), sc


def _cheap_margins(F_tr, y_tr, F_q, sensors=SENSORS, seed=ROUTER_SEED):
    """4 per-sensor TRAIN-fit logistic margins |p-0.5|, plus fitted cells."""
    from sklearn.linear_model import LogisticRegression
    cells, margins = {}, {}
    for s in sensors:
        lr_ = LogisticRegression(solver="lbfgs", C=1.0, max_iter=2000,
                                 random_state=seed)
        lr_.fit(F_tr[s], y_tr)
        cells[s] = lr_
        margins[s] = np.abs(lr_.predict_proba(F_q[s])[:, 1] - 0.5)
    return cells, np.stack([margins[s] for s in sensors], axis=1)


def _router_features(F_tr, y_tr, reg_tr, F_q, sensors=SENSORS):
    cen = _centroid_scores(F_tr, F_q, reg_tr, sensors)
    _, mar = _cheap_margins(F_tr, y_tr, F_q, sensors)
    return np.concatenate([cen, mar], axis=1)


def fit_router(F_tr, y_tr, reg_tr, sensors=SENSORS, seed=ROUTER_SEED):
    """Multinomial logistic 8->4 (32 weights + 4 intercepts = 36p), TRAIN-fit."""
    from sklearn.linear_model import LogisticRegression
    Xtr = _router_features(F_tr, y_tr, reg_tr, F_tr, sensors)
    clf = LogisticRegression(solver="lbfgs", C=1.0, max_iter=3000,
                             random_state=seed)
    clf.fit(Xtr, reg_tr)
    nparam = int(clf.coef_.size + clf.intercept_.size)
    return clf, nparam


def router_order(clf, F_tr, y_tr, reg_tr, F_q, sensors=SENSORS):
    Xq = _router_features(F_tr, y_tr, reg_tr, F_q, sensors)
    proba = clf.predict_proba(Xq)
    return proba, np.argsort(-proba, axis=1)


def sensor_centroid_top1(F_tr, F_q, reg_tr, sensors=SENSORS):
    """Variant-B 0-param top-1 regime via argmax over the 4 per-sensor scores."""
    cen = _centroid_scores(F_tr, F_q, reg_tr, sensors)
    return np.array([REGIME_OF_SENSOR[sensors[int(k)]] for k in cen.argmax(axis=1)])


def _board(correct_seedmean, idx=None):
    sel = np.arange(len(correct_seedmean)) if idx is None else idx
    return float(correct_seedmean[sel].mean())


def _std(correct, idx=None):
    sel = np.arange(correct.shape[1]) if idx is None else idx
    return float(correct[:, sel].mean(axis=1).std())


def boot_ci(d, b=BOOT_B, seed=ROUTER_SEED):
    rng = np.random.default_rng(seed)
    n = len(d)
    draws = np.empty(b)
    for k in range(b):
        draws[k] = d[rng.integers(0, n, n)].mean()
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return {"diff": round(float(d.mean()), 4),
            "ci95": [round(float(lo), 4), round(float(hi), 4)]}


def gate_from_correct(correct, a, b, idx=None, b_boot=BOOT_B, bar=None):
    sel = np.arange(correct[a].shape[1]) if idx is None else idx
    va = correct[a][:, sel].mean(axis=0)
    vb = correct[b][:, sel].mean(axis=0)
    ci = boot_ci(va - vb, b=b_boot)
    deg = (_std(correct[a], idx) == 0.0) or (_std(correct[b], idx) == 0.0)
    pt_ok = (ci["diff"] >= bar) if bar is not None else (ci["diff"] > 0)
    if deg:
        verdict = "INCONCLUSIVE (std==0 law)"
    elif pt_ok and ci["ci95"][0] > 0:
        verdict = "PASS"
    elif bar is not None and ci["ci95"][1] >= bar and ci["ci95"][0] <= 0:
        verdict = "INCONCLUSIVE_BORDERLINE"
    else:
        verdict = "FAIL"
    return {"diff": ci["diff"], "ci95": ci["ci95"], "bar": bar,
            "std0_a": _std(correct[a], idx) == 0.0,
            "std0_b": _std(correct[b], idx) == 0.0, "verdict": verdict}


def run_cpu(out_dir: Path) -> int:
    t_start = time.time()
    train, held = load_corpus(CORPUS)
    n_tr, n_he = len(train), len(held)
    reg_tr = np.array([it["regime"] for it in train])
    reg_he = np.array([it["regime"] for it in held])
    y_tr = np.array([y_of(it) for it in train], dtype=np.float32)
    y_he = np.array([y_of(it) for it in held], dtype=np.float32)
    kind_idx = {r: np.array([i for i, rg in enumerate(reg_he) if rg == r]) for r in REGIMES}
    chance = {"full": round(float(max(y_he.mean(), 1 - y_he.mean())), 4)}
    for r in REGIMES:
        yr = y_he[kind_idx[r]]
        chance[r] = round(float(max(yr.mean(), 1 - yr.mean())), 4)

    z = np.load(out_dir / "raw" / "features.npz")
    F_tr = {s: z[f"tr_{s}"] for s in SENSORS}
    F_he = {s: z[f"he_{s}"] for s in SENSORS}
    seeds_present = [s for s in SEEDS if (out_dir / "raw" / f"seed{s}.npz").exists()]
    def _ld(p):
        zz = np.load(p)
        return {k: zz[k] for k in zz.files}
    pred = {s: _ld(out_dir / "raw" / f"seed{s}.npz") for s in seeds_present}

    # ── 36p sensor-picking router (TRAIN-only) ─────────────────────────────
    clf, n_router = fit_router(F_tr, y_tr, reg_tr)
    proba_he, order_he = router_order(clf, F_tr, y_tr, reg_tr, F_he)
    proba_tr, order_tr = router_order(clf, F_tr, y_tr, reg_tr, F_tr)
    cen_order_he, _ = per_regime_centroid_order(F_tr, F_he, reg_tr)
    cen_order_tr, _ = per_regime_centroid_order(F_tr, F_tr, reg_tr)
    cenB_top_he = sensor_centroid_top1(F_tr, F_he, reg_tr)
    cenB_top_tr = sensor_centroid_top1(F_tr, F_tr, reg_tr)
    # NB: clf.classes_ is ALPHABETICAL, not REGIMES order. Index with classes_.
    r_top1_he = float((clf.classes_[order_he[:, 0]] == reg_he).mean())
    r_top1_tr = float((clf.classes_[order_tr[:, 0]] == reg_tr).mean())
    c_top1_he = float((np.array(REGIMES)[cen_order_he[:, 0]] == reg_he).mean())
    c_top1_tr = float((np.array(REGIMES)[cen_order_tr[:, 0]] == reg_tr).mean())
    cB_top1_he = float((cenB_top_he == reg_he).mean())
    cB_top1_tr = float((cenB_top_tr == reg_tr).mean())
    np.savez_compressed(out_dir / "raw" / "router.npz",
                        order_he=order_he, order_tr=order_tr,
                        cen_order_he=cen_order_he, cen_order_tr=cen_order_tr,
                        reg_he=reg_he, coef=clf.coef_, intercept=clf.intercept_,
                        classes=np.array(clf.classes_, dtype=object))

    # ── per-seed arm correctness cubes ─────────────────────────────────────
    nse = len(seeds_present)
    correct = {a: np.zeros((nse, n_he), dtype=bool) for a in ARM_NAMES}
    routed_regime = clf.classes_[order_he[:, 0]]
    routed_sensor = np.array([MATCH[r] for r in routed_regime])
    second_sensor = np.array([MATCH[r] for r in clf.classes_[order_he[:, 1]]])
    cen_routed_regime = np.array(REGIMES)[cen_order_he[:, 0]]

    la_info = []
    for si, seed in enumerate(seeds_present):
        d = pred[seed]

        def corr(p):
            return ((p >= 0.5) == (y_he == 1))

        correct["JOINT"][si] = corr(d["p_joint"])
        correct["SINGLE"][si] = corr(d["p_single"])
        correct["S4MONO"][si] = corr(d["p_s4mono"])

        # FED_WORD: 0-param centroid router over S1 slice cells
        pf = np.empty(n_he, dtype=np.float64)
        for j, r in enumerate(cen_routed_regime):
            pf[j] = d[f"p_fedword:{r}"][j]
        correct["FED_WORD"][si] = corr(pf)

        # FED_HETERO: learned router -> MATCH sensor -> sensor cell on ALL train
        ph = np.empty(n_he, dtype=np.float64)
        for j, s in enumerate(routed_sensor):
            ph[j] = d[f"p_hetero:{s}"][j]
        correct["FED_HETERO"][si] = corr(ph)

        # FED_HE_MATCHED: learned router -> regime slice cell with matched sensor
        pm = np.empty(n_he, dtype=np.float64)
        for j, r in enumerate(routed_regime):
            pm[j] = d[f"p_hematch:{r}"][j]
        correct["FED_HE_MATCHED"][si] = corr(pm)

        # FED+LA (zero-param): 2nd-choice sensor re-read when routed margin < tau
        routed_tr = np.array([MATCH[r] for r in clf.classes_[order_tr[:, 0]]])
        m_tr = np.abs(np.array([d[f"p_hetero_train:{s}"][j]
                               for j, s in enumerate(routed_tr)]) - 0.5)
        tau = float(np.percentile(m_tr, TAU_PCT))
        pa = ph.copy()
        trig = flip = 0
        for j in range(n_he):
            m1 = abs(ph[j] - 0.5)
            if m1 < tau:
                trig += 1
                s2 = second_sensor[j]
                m2 = abs(d[f"p_hetero:{s2}"][j] - 0.5)
                if m2 > m1:
                    flip += 1
                    pa[j] = d[f"p_hetero:{s2}"][j]
        correct["FED_LA"][si] = corr(pa)
        la_info.append({"seed": seed, "tau": round(tau, 4),
                        "triggers": trig, "flips": flip})

    # within-disagreement routing accuracy (target >= 0.60; CX-CHEAP-1 gap 0.5003)
    dis = 0
    hit = 0
    for j in range(n_he):
        answers = []
        ok_sensors = []
        for s in SENSORS:
            p = np.mean([pred[seed][f"p_hetero:{s}"][j] for seed in seeds_present])
            answers.append(p >= 0.5)
            ok_sensors.append(((p >= 0.5) == (y_he[j] == 1)))
        if len(set(answers)) > 1:
            dis += 1
            if ok_sensors[SENSORS.index(routed_sensor[j])]:
                hit += 1
    within_disagree = round(hit / dis, 4) if dis else None

    router_audit = {
        "n_params": n_router,
        "learned_top1_heldout": round(r_top1_he, 4),
        "learned_top1_train": round(r_top1_tr, 4),
        "centroid_comp1_top1_heldout": round(c_top1_he, 4),
        "centroid_comp1_top1_train": round(c_top1_tr, 4),
        "centroid_persensor_top1_heldout": round(cB_top1_he, 4),
        "centroid_persensor_top1_train": round(cB_top1_tr, 4),
        "band": [ROUTER_LO, ROUTER_HI], "chance": 0.25,
        "learned_in_band": bool(ROUTER_LO <= r_top1_he <= ROUTER_HI),
        "centroid_in_band": bool(ROUTER_LO <= c_top1_he <= ROUTER_HI),
        "centroid_persensor_in_band": bool(ROUTER_LO <= cB_top1_he <= ROUTER_HI),
        "within_disagreement_routing_acc": within_disagree,
        "within_disagreement_n": dis,
        "within_disagreement_target": 0.60,
    }
    router_ok = (router_audit["learned_in_band"] and router_audit["centroid_in_band"]
                 and router_audit["centroid_persensor_in_band"])

    # ── boards ─────────────────────────────────────────────────────────────
    boards = {}
    for a in ARM_NAMES:
        cm = correct[a].mean(axis=0)
        boards[a] = {"full": round(float(cm.mean()), 4)}
        for r in REGIMES:
            boards[a][r] = round(float(cm[kind_idx[r]].mean()), 4)
    seed_std = {a: {"full": round(_std(correct[a]), 4),
                    **{r: round(_std(correct[a], kind_idx[r]), 4) for r in REGIMES}}
                for a in ARM_NAMES}

    # ── gates ──────────────────────────────────────────────────────────────
    neg = kind_idx["negation-scope"]
    P1 = gate_from_correct(correct, "FED_HETERO", "SINGLE", neg, bar=0.08)
    topup = None
    if P1["verdict"] == "INCONCLUSIVE_BORDERLINE":
        topup = {"b": BOOT_B_TOPUP,
                 "P1_reanalysis": gate_from_correct(correct, "FED_HETERO", "SINGLE",
                                                    neg, b_boot=BOOT_B_TOPUP, bar=0.08)}
        P1 = topup["P1_reanalysis"]
    P2 = gate_from_correct(correct, "FED_HE_MATCHED", "FED_WORD", neg)
    P3 = gate_from_correct(correct, "FED_LA", "FED_HETERO", neg)
    secondary = {
        "full_FED_HETERO_vs_SINGLE": gate_from_correct(correct, "FED_HETERO", "SINGLE"),
        "full_FED_HETERO_vs_JOINT": gate_from_correct(correct, "FED_HETERO", "JOINT"),
        "full_FED_LA_vs_FED_HETERO": gate_from_correct(correct, "FED_LA", "FED_HETERO"),
        "full_FED_HE_MATCHED_vs_FED_WORD": gate_from_correct(correct, "FED_HE_MATCHED", "FED_WORD"),
        "G2b_FED_HETERO_vs_HE_MATCHED_full": gate_from_correct(correct, "FED_HETERO", "FED_HE_MATCHED"),
        "G2b_FED_HETERO_vs_HE_MATCHED_negation": gate_from_correct(correct, "FED_HETERO", "FED_HE_MATCHED", neg),
    }
    per_regime = {}
    for a, b in (("FED_HETERO", "SINGLE"), ("FED_HE_MATCHED", "FED_WORD"),
                 ("FED_LA", "FED_HETERO"), ("FED_HETERO", "JOINT")):
        for r in REGIMES:
            per_regime[f"{a}_vs_{b}@{r}"] = gate_from_correct(correct, a, b, kind_idx[r])

    s4_readout = {"boards": {r: boards["S4MONO"][r] for r in REGIMES},
                  "full": boards["S4MONO"]["full"],
                  "ge_fed_hetero_minus_0.02": sum(
                      1 for r in REGIMES
                      if boards["S4MONO"][r] >= boards["FED_HETERO"][r] - 0.02)}

    # ── verdict lattice ────────────────────────────────────────────────────
    if not router_ok:
        overall = "INCONCLUSIVE_CORPUS (router out of band)"
    elif len(seeds_present) < len(SEEDS):
        overall = "INCONCLUSIVE (TRUNC-B)"
    elif "INCONCLUSIVE" in P1["verdict"]:
        overall = "INCONCLUSIVE_BORDERLINE-at-max-power"
    elif P1["verdict"] == "PASS" and P2["verdict"] == "PASS":
        overall = "KEEP"
    else:
        parts = [n for n, g in (("P1", P1), ("P2", P2), ("P3", P3))
                 if g["verdict"] == "PASS"]
        overall = ("SPLIT_KEEP_" + "_".join(parts)) if parts else (
            "STRIKE-3-CANDIDATE (P1 CI_high<+0.08)" if P1["ci95"][1] < 0.08 else "INCONCLUSIVE")

    # prereg §Risks-4 interpretation rule: honest narrowing, NOT a verdict change.
    if overall == "KEEP" and s4_readout["ge_fed_hetero_minus_0.02"] >= 3:
        interpretation = ("NARROWED: S4-MONO (single right sensor, 1057p) is within 0.02 of "
                          "FED-HETERO on %d/4 regimes -> the win re-reads as 'buy the right "
                          "sensor once'; federation thesis narrowed honestly."
                          % s4_readout["ge_fed_hetero_minus_0.02"])
    else:
        interpretation = "no narrowing trigger"
    if P3["verdict"] == "PASS":
        interpretation += " | P3 PASS: LA doctrine refined (independent reach = a different SENSOR to escape to)."
    else:
        interpretation += " | P3 FAIL: LA closed to a D1b footnote (booked)."

    result = {
        "experiment": "COMPOSITE-2 federation v3 (6 MLP banks, heterogeneous sensors, "
                      "learned sensor-picking router, difficulty-wired corpus)",
        "prereg": "proposals/runs/COMPOSITE-2-federation3.md",
        "phase": "2-arms", "seeds": seeds_present, "device_note": "banks trained GPU (inner)",
        "corpus": str(CORPUS),
        "corpus_sha256": hashlib.sha256(CORPUS.read_bytes()).hexdigest(),
        "n_train": n_tr, "n_heldout": n_he, "regime_counts_heldout":
            {r: int(len(kind_idx[r])) for r in REGIMES},
        "chance_majority": chance,
        "match_table": MATCH, "params": {"JOINT": 4225, "SINGLE": 1057, "S4MONO": 1057,
                                          "FED_WORD": 4228, "FED_HETERO": 4228 + 36,
                                          "FED_HE_MATCHED": 4228 + 36, "FED_LA": 0},
        "router_audit": router_audit, "router_ok": bool(router_ok),
        "boards_seedmean": boards, "seed_std": seed_std,
        "P1": P1, "P2": P2, "P3": P3, "P1_topup": topup,
        "secondary_full_board": secondary, "per_regime_ci": per_regime,
        "s4_mono_readout": s4_readout, "la": la_info,
        "verdict": overall, "interpretation": interpretation,
        "wall_seconds": round(time.time() - t_start, 1),
    }
    (out_dir / "comp2_results.json").write_text(json.dumps(result, indent=2))

    # ── per-item predictions (MANDATORY persistence law) ───────────────────
    write_predictions(out_dir, train, held, pred, seeds_present, correct,
                      routed_sensor, routed_regime, la_info, second_sensor,
                      cen_routed_regime)

    print("VERDICT " + overall, flush=True)
    print("P1 " + json.dumps(P1), flush=True)
    print("P2 " + json.dumps(P2), flush=True)
    print("P3 " + json.dumps(P3), flush=True)
    print("boards " + json.dumps(boards), flush=True)
    print("router " + json.dumps(router_audit), flush=True)
    return 0


def write_predictions(out_dir, train, held, pred, seeds_present, correct,
                      routed_sensor, routed_regime, la_info, second_sensor,
                      cen_routed_regime):
    (out_dir / "predictions").mkdir(exist_ok=True)
    y_he = np.array([y_of(it) for it in held], dtype=np.float32)
    base = [{"sha256": it["sha256"], "key": it["sha256"][:16], "regime": it["regime"],
             "label": it["label"], "split": "heldout"} for it in held]
    for a in ARM_NAMES:
        p = np.empty((len(seeds_present), len(held)))
        rs = np.array([None] * len(held), dtype=object)
        cell = np.array([None] * len(held), dtype=object)
        trig = np.zeros(len(held), dtype=int)
        flip = np.zeros(len(held), dtype=int)
        for si, seed in enumerate(seeds_present):
            d = pred[seed]
            if a == "JOINT":
                p[si] = d["p_joint"]
            elif a == "SINGLE":
                p[si] = d["p_single"]
            elif a == "S4MONO":
                p[si] = d["p_s4mono"]
            elif a == "FED_WORD":
                # FED_WORD is the COMP1-verbatim 0-param CENTROID router, NOT the
                # learned router (prereg §3). Dump must use cen_routed_regime.
                pf = np.empty(len(held))
                for j, r in enumerate(cen_routed_regime):
                    pf[j] = d[f"p_fedword:{r}"][j]
                p[si] = pf
                rs = np.array(cen_routed_regime, dtype=object)
                cell = np.array(["fedword_" + r for r in cen_routed_regime], dtype=object)
            elif a == "FED_HETERO":
                ph = np.empty(len(held))
                for j, s in enumerate(routed_sensor):
                    ph[j] = d[f"p_hetero:{s}"][j]
                p[si] = ph
                rs = np.array(routed_sensor, dtype=object)
                cell = np.array(["hetero_" + s for s in routed_sensor], dtype=object)
            elif a == "FED_HE_MATCHED":
                pm = np.empty(len(held))
                for j, r in enumerate(routed_regime):
                    pm[j] = d[f"p_hematch:{r}"][j]
                p[si] = pm
                rs = np.array([MATCH[r] for r in routed_regime], dtype=object)
                cell = np.array(["hematch_" + r for r in routed_regime], dtype=object)
            elif a == "FED_LA":
                ph = np.empty(len(held))
                for j, s in enumerate(routed_sensor):
                    ph[j] = d[f"p_hetero:{s}"][j]
                tau = la_info[si]["tau"]
                for j in range(len(held)):
                    m1 = abs(ph[j] - 0.5)
                    if m1 < tau:
                        trig[j] = 1
                        s2 = second_sensor[j]
                        m2 = abs(d[f"p_hetero:{s2}"][j] - 0.5)
                        if m2 > m1:
                            flip[j] = 1
                            ph[j] = d[f"p_hetero:{s2}"][j]
                p[si] = ph
                rs = np.array(routed_sensor, dtype=object)
                cell = np.array(["hetero_" + s for s in routed_sensor], dtype=object)
        f = out_dir / "predictions" / f"{a}.jsonl.gz"
        with gzip.open(f, "wt") as fh:
            for si, seed in enumerate(seeds_present):
                for j, b in enumerate(base):
                    row = dict(b)
                    row.update({
                        "seed": seed, "arm": a, "p": round(float(p[si][j]), 6),
                        "correct": bool((p[si][j] >= 0.5) == (y_he[j] == 1)),
                        "margin": round(float(abs(p[si][j] - 0.5)), 6),
                        "routed_sensor": rs[j], "cell": cell[j],
                        "la_trigger": int(trig[j]) if a == "FED_LA" else None,
                        "la_flip": int(flip[j]) if a == "FED_LA" else None,
                    })
                    fh.write(json.dumps(row) + "\n")


# ── cheap-arm 361p bracket (CPU, dual corpus) ──────────────────────────────
def cheap_two_arm(F_tr, y_tr, reg_tr, F_he, y_he, reg_he, seeds=(ROUTER_SEED,)):
    """SINGLE-cheap = logistic on S1 (65p). FED-cheap-hetero = 4 logistic cells
    (4x65=260p) + the SAME 36p router -> 361p. Returns correctness + params."""
    from sklearn.linear_model import LogisticRegression
    single = LogisticRegression(solver="lbfgs", C=1.0, max_iter=3000, random_state=seeds[0])
    single.fit(F_tr["S1"], y_tr)
    ps = single.predict_proba(F_he["S1"])[:, 1]
    corr_single = ((ps >= 0.5) == (y_he == 1))
    clf, nrouter = fit_router(F_tr, y_tr, reg_tr, seed=seeds[0])
    _, order = router_order(clf, F_tr, y_tr, reg_tr, F_he)
    routed = clf.classes_[order[:, 0]]
    routed_sens = np.array([MATCH[r] for r in routed])
    cells, _ = _cheap_margins(F_tr, y_tr, F_he)
    pf = np.empty(len(y_he))
    for j, s in enumerate(routed_sens):
        pf[j] = cells[s].predict_proba(F_he[s][j:j + 1])[:, 1][0]
    corr_fed = ((pf >= 0.5) == (y_he == 1))
    params = {"single": 65, "fed_cells": 260, "router": nrouter, "total": 65 + 260 + nrouter}
    return {"single": corr_single, "fed": corr_fed, "p_single": ps, "p_fed": pf,
            "params": params, "routed_sensor": routed_sens, "routed_regime": routed}


def _cheap_mean(correct, idx):
    return float(correct[idx].mean())


def run_cheap_bracket(out_dir: Path, c2_boards: dict) -> dict:
    (out_dir / "cheap").mkdir(exist_ok=True)
    # ── G4a: frozen COMP1 corpus (1810/590) ────────────────────────────────
    from experiments.comp1_federation2 import gen_corpus as comp1_gen
    c1_train, c1_held, _ = comp1_gen()
    c1_sha = hashlib.sha256(COMP1_CORPUS.read_bytes()).hexdigest()
    assert c1_sha == COMP1_CORPUS_SHA, f"COMP1 corpus sha mismatch {c1_sha}"
    F_tr = featurize(c1_train)
    F_he = featurize(c1_held)
    y_tr = np.array([y_of(it) for it in c1_train], dtype=np.float32)
    y_he = np.array([y_of(it) for it in c1_held], dtype=np.float32)
    reg_tr = np.array([it["kind"] for it in c1_train])
    reg_he = np.array([it["kind"] for it in c1_held])
    kb = {r: np.array([i for i, rg in enumerate(reg_he) if rg == r]) for r in REGIMES}
    ch = cheap_two_arm(F_tr, y_tr, reg_tr, F_he, y_he, reg_he)
    g4a_boards = {"full": round(float(ch["fed"].mean()), 4)}
    for r in REGIMES:
        g4a_boards[r] = round(_cheap_mean(ch["fed"], kb[r]), 4)
    deltas = {r: round(g4a_boards[r] - COMP1_FED_BOARDS[r], 4) for r in REGIMES}
    maxabs = round(max(abs(v) for v in deltas.values()), 4)
    dneg = ch["fed"][kb["negation-scope"]].astype(float) - ch["single"][kb["negation-scope"]].astype(float)
    neg_ci = boot_ci(dneg)
    g4a = {"boards_fed_cheap": g4a_boards, "board_single_cheap": {
               "full": round(float(ch["single"].mean()), 4),
               **{r: round(_cheap_mean(ch["single"], kb[r]), 4) for r in REGIMES}},
           "booked_comp1_fed_boards": COMP1_FED_BOARDS,
           "delta_vs_booked": deltas, "max_abs_delta": maxabs,
           "max_abs_delta_bar": 0.02,
           "negation_fed_minus_single": neg_ci, "negation_bar": 0.126,
           "verdict": "PASS" if (maxabs <= 0.02 and neg_ci["diff"] >= 0.126
                                 and neg_ci["ci95"][0] > 0) else "FAIL",
           "params": ch["params"], "comp1_corpus_sha256": c1_sha}

    # ── G4b: in-corpus vs C2's own FED_WORD seed-mean boards ───────────────
    z = np.load(out_dir / "raw" / "features.npz")
    F2_tr = {s: z[f"tr_{s}"] for s in SENSORS}
    F2_he = {s: z[f"he_{s}"] for s in SENSORS}
    t2, h2 = load_corpus(CORPUS)
    y2_tr = np.array([y_of(it) for it in t2], dtype=np.float32)
    y2_he = np.array([y_of(it) for it in h2], dtype=np.float32)
    rg2_tr = np.array([it["regime"] for it in t2])
    rg2_he = np.array([it["regime"] for it in h2])
    kc = {r: np.array([i for i, rg in enumerate(rg2_he) if rg == r]) for r in REGIMES}
    c2 = cheap_two_arm(F2_tr, y2_tr, rg2_tr, F2_he, y2_he, rg2_he)
    g4b_boards = {"full": round(float(c2["fed"].mean()), 4)}
    for r in REGIMES:
        g4b_boards[r] = round(_cheap_mean(c2["fed"], kc[r]), 4)
    ref = {r: c2_boards["FED_WORD"][r] for r in REGIMES}
    d2 = {r: round(g4b_boards[r] - ref[r], 4) for r in REGIMES}
    maxabs2 = round(max(abs(v) for v in d2.values()), 4)
    dneg2 = c2["fed"][kc["negation-scope"]].astype(float) - c2["single"][kc["negation-scope"]].astype(float)
    neg_ci2 = boot_ci(dneg2)
    g4b = {"boards_fed_cheap": g4b_boards, "board_single_cheap": {
               "full": round(float(c2["single"].mean()), 4),
               **{r: round(_cheap_mean(c2["single"], kc[r]), 4) for r in REGIMES}},
           "fed_word_seedmean_boards": ref, "delta_vs_fed_word": d2,
           "max_abs_delta": maxabs2, "max_abs_delta_bar": 0.02,
           "negation_fed_minus_single": neg_ci2, "negation_bar": 0.126,
           "verdict": "PASS" if (maxabs2 <= 0.02 and neg_ci2["diff"] >= 0.126
                                 and neg_ci2["ci95"][0] > 0) else "FAIL",
           "params": c2["params"]}

    if g4a["verdict"] == "PASS" and g4b["verdict"] == "PASS":
        ret = "MLP-RETIRED"
    elif g4a["verdict"] == "PASS":
        ret = "RETIRED-OLD-CORPUS-ONLY"
    else:
        ret = "NOT-RETIRED"
    out = {"experiment": "COMPOSITE-2 P4 cheap-arm 361p bracket (dual corpus)",
           "prereg": "proposals/runs/COMPOSITE-2-federation3.md §4 + §6 P4",
           "G4a_comp1": g4a, "G4b_c2": g4b,
           "verdict": f"{ret} (G4a {g4a['verdict']} / G4b {g4b['verdict']})",
           "retirement": ret}
    (out_dir / "cheap" / "cheap_bracket.json").write_text(json.dumps(out, indent=2))

    # per-item predictions for both corpora (mandatory persistence)
    for tag, held_items, arms in (("comp1", c1_held, ch), ("c2", h2, c2)):
        with gzip.open(out_dir / "cheap" / f"predictions_{tag}.jsonl.gz", "wt") as fh:
            for j, it in enumerate(held_items):
                for arm, pk in (("SINGLE_cheap", arms["p_single"]),
                                ("FED_cheap_hetero", arms["p_fed"])):
                    p = float(pk[j])
                    yv = 1 if it["label"] == "canon" else 0
                    fh.write(json.dumps({
                        "sha256": it.get("sha256"), "regime": it["kind"], "label": it["label"],
                        "split": "heldout", "arm": arm, "p": round(p, 6),
                        "correct": bool((p >= 0.5) == (yv == 1)),
                        "margin": round(abs(p - 0.5), 6),
                        "routed_sensor": str(arms["routed_sensor"][j]) if arm.startswith("FED") else None,
                        "cell": str(arms["routed_regime"][j]) if arm.startswith("FED") else None,
                        "la_trigger": None, "la_flip": None}) + "\n")
    return out


# ── outer (guarded) run ─────────────────────────────────────────────────────
def run_outer(out_dir: Path) -> int:
    import guard
    g = guard.Guard(timeout_s=GUARD_TIMEOUT_S, task_id="COMPOSITE-2-federation3",
                    agent="quilt-gpu-lab keeper (Lucineer, main Super Z)",
                    seed="2718,2719,2720", receipt_dir=str(out_dir / "guard"))
    ok = g.preflight()
    if not ok:
        print(f"PREFLIGHT REFUSED: {g.breach} — retry once after 60 s", flush=True)
        time.sleep(60.0)
        ok = g.preflight()
    if not ok:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "comp2_results.json").write_text(json.dumps(
            {"lane": "COMPOSITE-2-federation3", "verdict": "NOT-RUN",
             "reason": f"guard preflight refused twice: {g.breach}"}, indent=2))
        g.emit_receipt(verdict="VOID", void_reason=f"preflight refused twice: {g.breach}")
        print("BOOKED NOT-RUN (guard preflight refused twice)", flush=True)
        return 2

    cmd = [sys.executable, str(Path(__file__).resolve()), "--inner", "--out", str(out_dir)]
    rc, out, err = g.run(cmd, cwd=str(LAB), env=dict(os.environ))
    print(f"inner rc={rc}", flush=True)
    print(out[-4000:], flush=True)
    if err.strip():
        print("stderr tail:", err[-1500:], flush=True)
    if rc == 0:
        rpath, receipt = g.emit_receipt()
        okv, msg = g.validate_receipt(rpath)
        print(f"guard MEASURED receipt: {rpath} valid={okv} {msg}", flush=True)
        wh = receipt["energy"]["watt_hours"]
        print(f"G7 watt receipt: {wh} Wh (envelope 20.0)", flush=True)
        (out_dir / "wh_receipt.json").write_text(json.dumps(
            {"watt_hours": wh, "joules": receipt["energy"]["joules"],
             "gpu_seconds": receipt["compute"]["gpu_seconds"],
             "receipt_id": receipt["receipt_id"], "valid": okv,
             "envelope_wh": 20.0, "within_envelope": wh <= 20.0}, indent=2))
    else:
        g.emit_receipt(verdict="VOID", void_reason=f"inner exit {rc}")
        print("VOID receipt sealed for failed run", flush=True)
        return 2
    rc2 = run_cpu(out_dir)
    rc3 = run_cheap_bracket(out_dir, json.loads((out_dir / "comp2_results.json").read_text())
                            ["boards_seedmean"])
    print("CHEAP " + json.dumps({"G4a": rc3["G4a_comp1"]["verdict"],
                                 "G4b": rc3["G4b_c2"]["verdict"],
                                 "retirement": rc3["retirement"]}), flush=True)
    return 0 if (rc2 == 0 and rc3) else 2


if __name__ == "__main__":
    args = sys.argv[1:]
    out = OUT_DIR
    if "--out" in args:
        out = Path(args[args.index("--out") + 1])
    if "--inner" in args:
        sys.exit(run_inner(out))
    if "--cpu" in args:
        sys.exit(run_cpu(out))
    if "--cheap" in args:
        sys.exit(0 if run_cheap_bracket(out, json.loads(
            (out / "comp2_results.json").read_text())["boards_seedmean"]) else 2)
    sys.exit(run_outer(out))
