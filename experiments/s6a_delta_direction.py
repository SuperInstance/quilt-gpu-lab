#!/usr/bin/env python3
"""S6a — law vs geometry on the D-ledger (edge-mine M15 falsifier). CPU-only.

Pre-registered: proposals/runs/S6a-delta-direction-ledger-prereg.md (owner: farm).
Question: does a contrastive direction in embedded run-space (keep vs miss)
predict held-out discovery ABOVE the physics scalars we already own?

ANTI-LEAK (frozen): the embedding text contains ONLY structural fields —
family, W, N, p, T. Outcome fields (acc, verdict, floors) are NEVER embedded;
the label is used only for the direction fit and AUC scoring.

Arms: GEOM (nomic-embed-text via local Ollama), SCALAR-1 (T*W), SCALAR-2
(T*W / per-corner C-hat from train folds only), CHANCE (1000 label perms).
Protocol: leave-one-family-out; families lacking both classes are excluded
and reported. Gates mechanical, mapped in _verdict(); small-n is declared.
"""
import glob
import json
import math
import os
import sys
import traceback
import urllib.request

import numpy as np

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
OUT_PATH = os.path.join(RESULTS_DIR, "s6a_delta_direction.json")
ACC_BAR = 0.9
OLLAMA = "http://127.0.0.1:11434/api/embeddings"
MODEL = "nomic-embed-text"
N_PERM = 1000


def _rows_from_grid(family, grid, acc_key):
    rows = []
    for g in grid:
        try:
            rows.append({"family": family,
                         "W": int(g["W"]), "N": int(g["N"]),
                         "p": float(g.get("p_corr", g.get("p"))),
                         "T": int(g["T"]),
                         "acc": float(g[acc_key])})
        except (KeyError, TypeError, ValueError):
            continue
    return rows


def extract_rows(path, data):
    """Known extractors + tolerant probe; returns (rows, extractor_name)."""
    if isinstance(data.get("grid"), list):
        acc_key = next((k for k in ("partner_id_acc", "acc", "mean_acc")
                        if data["grid"] and isinstance(data["grid"][0], dict)
                        and k in data["grid"][0]), None)
        if acc_key:
            fam = data.get("experiment") or os.path.basename(path)
            return _rows_from_grid(fam, data["grid"], acc_key), f"grid:{acc_key}"
    if isinstance(data.get("floors"), dict):
        return None, "floors-only (no per-T grid -> no both-class labels; excluded)"
    # tolerant probe: any list-of-dicts with T + acc-like + W/N/p
    for key, val in data.items():
        if (isinstance(val, list) and val and isinstance(val[0], dict)
                and "T" in val[0]):
            acc_key = next((k for k in val[0] if "acc" in k.lower()), None)
            if acc_key and {"W", "N"} <= set(val[0]):
                fam = data.get("experiment") or f"{os.path.basename(path)}:{key}"
                return _rows_from_grid(fam, val, acc_key), f"probe:{key}:{acc_key}"
    return None, "unparsed"


def embed(text):
    req = urllib.request.Request(
        OLLAMA, data=json.dumps({"model": MODEL, "prompt": text}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return np.asarray(json.load(resp)["embedding"], dtype=np.float64)


def _auc(scores, labels):
    """Mann-Whitney AUC via average ranks (ties handled)."""
    order = np.argsort(scores)
    ranks = np.empty(len(scores), dtype=np.float64)
    sorted_scores = scores[order]
    i = 0
    while i < len(scores):
        j = i
        while j + 1 < len(scores) and sorted_scores[j + 1] == sorted_scores[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    n_pos, n_neg = labels.sum(), (1 - labels).sum()
    if n_pos == 0 or n_neg == 0:
        return None
    return (ranks[labels == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def main():
    rows, unparsed, parsed_files = [], [], 0
    for path in sorted(glob.glob(os.path.join(RESULTS_DIR, "*.json"))):
        base = os.path.basename(path)
        if base.startswith("s6a"):
            continue
        if "harness-invalid" in base or "KILL" in base:
            unparsed.append({"file": base,
                             "reason": "validity filter: invalid/KILL receipt excluded"})
            continue
        try:
            with open(path) as fh:
                data = json.load(fh)
        except Exception:
            unparsed.append({"file": base, "reason": "bad json"})
            continue
        got, how = extract_rows(path, data)
        if got:
            rows.extend(got)
            parsed_files += 1
        else:
            unparsed.append({"file": base, "reason": how})
    d_line = sorted({r["family"] for r in rows if r["family"].startswith("d1")})
    rows = [r for r in rows if r["family"].startswith("d1")]
    if len(rows) < 40:
        raise RuntimeError(f"corpus too small: {len(rows)} rows — aborting, no fake data")

    labels = np.array([1 if r["acc"] >= ACC_BAR else 0 for r in rows])
    fams = np.array([r["family"] for r in rows])
    texts = [f"experiment {r['family']} width {r['W']} channels {r['N']} "
             f"corr_prob {r['p']} timesteps {r['T']}" for r in rows]
    X = np.stack([embed(t) for t in texts])
    if not np.isfinite(X).all():
        raise RuntimeError("non-finite embedding values — aborting (no garbage science)")
    scal1 = np.array([r["T"] * r["W"] for r in rows], dtype=np.float64)
    corner = np.array([f"{r['N']}|{r['p']}" for r in rows])

    usable = sorted({f for f in set(fams)
                     if 0 < labels[fams == f].sum() < (fams == f).sum()})
    folds, geom_aucs, s1_aucs, s2_aucs = [], [], [], []
    for held in usable:
        tr, te = fams != held, fams == held
        if labels[tr].sum() == 0 or (1 - labels[tr]).sum() == 0:
            continue
        mu_k, mu_m = X[tr & (labels == 1)].mean(0), X[tr & (labels == 0)].mean(0)
        u = mu_k - mu_m
        nrm = np.linalg.norm(u)
        if not np.isfinite(nrm) or nrm == 0:
            continue
        u /= nrm
        center = X[tr].mean(0)
        g = _auc((X[te] - center) @ u, labels[te])
        s1 = _auc(scal1[te], labels[te])
        chat = {c: np.median(scal1[tr & (labels == 1) & (corner == c)])
                for c in set(corner[tr])}
        gmed = np.median(scal1[tr & (labels == 1)])
        s2v = np.array([scal1[i] / chat.get(corner[i], gmed) for i in np.where(te)[0]])
        s2 = _auc(s2v, labels[te])
        if None not in (g, s1, s2):
            folds.append(held)
            geom_aucs.append(g)
            s1_aucs.append(s1)
            s2_aucs.append(s2)
    if not folds:
        raise RuntimeError("no usable LOFO folds — aborting")

    geom_m, s1_m, s2_m = (float(np.mean(a)) for a in (geom_aucs, s1_aucs, s2_aucs))
    best_scalar = max(s1_m, s2_m)
    perm_means = []
    rng = np.random.default_rng(2718)
    for _ in range(N_PERM):
        pl = rng.permutation(labels)
        pa = []
        for held in usable:
            tr, te = fams != held, fams == held
            if pl[tr].sum() == 0 or (1 - pl[tr]).sum() == 0:
                continue
            a = _auc((X[te] - X[tr].mean(0)) @ ((X[tr & (pl == 1)].mean(0)
                                                - X[tr & (pl == 0)].mean(0))
                                               / max(np.linalg.norm(
                                                   X[tr & (pl == 1)].mean(0)
                                                   - X[tr & (pl == 0)].mean(0)), 1e-12)),
                     pl[te])
            if a is not None:
                pa.append(a)
        if pa:
            perm_means.append(float(np.mean(pa)))
    p_val = float(np.mean([pm >= geom_m for pm in perm_means])) if perm_means else 1.0

    if geom_m >= best_scalar + 0.05 and p_val < 0.05:
        verdict = "GEOM_WINS"
    elif geom_m <= best_scalar + 0.05:
        verdict = "BASELINE_CARRIES"
    else:
        verdict = "SPLIT"
    result = {
        "experiment": "s6a_delta_direction",
        "runner_status": "reviewed 2026-10-01 (two-witness); validity filter + D-line restriction + NaN guards applied",
        "corpus": {"n_rows": len(rows), "n_files_parsed": parsed_files,
                   "families": d_line, "d_line_only": True},
        "n_rows": len(rows), "folds": folds,
        "excluded_unparsed": unparsed,
        "AUC": {"geom": round(geom_m, 4), "scalar_TW": round(s1_m, 4),
                "scalar_TW_over_Chat": round(s2_m, 4),
                "chance_perm_p": round(p_val, 4)},
        "verdict": verdict,
        "pre_registered": "proposals/runs/S6a-delta-direction-ledger-prereg.md",
    }
    with open(OUT_PATH, "w") as fh:
        json.dump(result, fh, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        kill_path = OUT_PATH.replace(
            ".json", f".harness-invalid-{int(time.time())}.json")
        with open(kill_path, "w") as fh:
            json.dump({"experiment": "s6a_delta_direction",
                       "kill_receipt": kill_path,
                       "verdict": "KILL-harness",
                       "error": traceback.format_exc(),
                       "python": sys.executable}, fh, indent=2)
        raise
