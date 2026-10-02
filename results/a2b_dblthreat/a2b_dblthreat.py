#!/usr/bin/env python3
"""A2B-DBLTHREAT — designed double-threat boards: does a DESIGNED set host the composition contrast?

Lane A2B-DBLTHREAT (quilt-gpu-lab), the A2-HARVEST booked fix #1.
Pre-registration: results/a2b_dblthreat/PREREG.md (frozen BEFORE the measured run in this file).

CPU ONLY. No CUDA call is made; energy = 0 Wh by construction.
No shell=True anywhere; the one subprocess is the repo's C solver, list-form.

Read-only inputs:
  results/a2_ga4444/dataset.jsonl       66,297 our-turn gravity boards, exact set-valued labels
  results/a2_ga4444/smoke_{mlp,linear}_metrics.json   A2's booked arms (continuity anchor)
"""
from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import time

import numpy as np

W = H = 4
SEED = 2718
HERE = os.path.dirname(os.path.abspath(__file__))
A2DIR = os.path.join(os.path.dirname(HERE), "a2_ga4444")
DATASET = os.path.join(A2DIR, "dataset.jsonl")
C_SOLVER = os.environ.get("A2_C_SOLVER", "/tmp/gt4444")
DESIGN_OUT = os.path.join(HERE, "design.jsonl")
METRICS = os.path.join(HERE, "a2b_metrics.json")

# ------------------------------------------------------------------ game (gravity)
bit = lambda r, c: 1 << (r * W + c)
COLMASK = [sum(bit(r, c) for r in range(H)) for c in range(W)]
LINES = []
for _r in range(H):
    LINES.append(("row%d" % _r, sum(bit(_r, _c) for _c in range(W))))
for _c in range(H):
    LINES.append(("col%d" % _c, sum(bit(_r, _c) for _r in range(H))))
LINES.append(("diag\\", sum(bit(_i, _i) for _i in range(W))))
LINES.append(("diag/", sum(bit(_i, W - 1 - _i) for _i in range(W))))
FULL = (1 << (W * H)) - 1


def has_line(s):
    for _n, L in LINES:
        if s & L == L:
            return True
    return False


def legal_cols(occ):
    return [c for c in range(W) if (occ & COLMASK[c]) != COLMASK[c]]


def drop_cell(occ, c):
    for r in range(H):
        m = bit(r, c)
        if not (occ & m):
            return m, r
    return None, None


def board_to_masks(board):
    a = b = 0
    for i, v in enumerate(board):
        if v == 1:
            a |= 1 << i
        elif v == -1:
            b |= 1 << i
    return a, b


def threats(mine, occ):
    """Exhaustive legal-drop probe: [(col, row, [line names completed])]."""
    out = []
    for c in legal_cols(occ):
        m, r = drop_cell(occ, c)
        nm = mine | m
        ls = [n for n, L in LINES if (nm & L) == L]
        if ls:
            out.append((c, r, ls))
    return out


def stratify(line1, line2, r1, r2, c1, c2):
    """Verbatim PREREG §2 strata."""
    if line1.startswith("col") and line2.startswith("col"):
        return "stacked-column"
    if ((r1 < 2) != (r2 < 2)) and ((c1 < 2) != (c2 < 2)):
        return "cross-quadrant"
    return "split-column"


def fnv1a64(data: bytes) -> int:
    h = 0xCBF29CE484222325
    for byte in data:
        h ^= byte
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h


def fold_of(fnv: int) -> int:
    return (fnv >> 32) % 5


# ------------------------------------------------------------------ corpus
def build_corpus():
    rows = []
    for ln in open(DATASET):
        rows.append(json.loads(ln))
    D, Dstar, Dstar2, Sz = [], [], [], []
    for r in rows:
        a, b = board_to_masks(r["board"])
        occ = a | b
        th = threats(a, occ)
        oth = threats(b, occ)
        chance = len(r["opt"]) / r["n_legal"]
        base = dict(board=r["board"], opt=r["opt"], n_legal=r["n_legal"], ply=r["ply"],
                    fnv=r["fnv"], chance=chance, n_threats=len(th),
                    n_opp_threats=len(oth), imm_wins=r["imm_wins"],
                    defA_threats=r["defA_threats"], value=r["value"])
        if len(th) >= 2:
            s = stratify(th[0][2][0], th[1][2][0], th[0][1], th[1][1], th[0][0], th[1][0])
            base["strata"] = s
            D.append(dict(base, role="D"))
            if len(oth) >= 1:
                Dstar.append(dict(base, role="D*"))
                if chance < 1.0:
                    Dstar2.append(dict(base, role="D**"))
        elif len(th) == 1:
            Sz.append(dict(base, role="S_all", strata="single"))
    # ---- matched single-threat controls for D* (ply, n_legal, opp-threat flag)
    rng = random.Random(SEED)
    pool = {}
    for r in Sz:
        pool.setdefault((r["ply"], r["n_legal"], r["n_opp_threats"] >= 1), []).append(r)
    for k in pool:
        rng.shuffle(pool[k])
    used = {}
    pairs = []
    matched_S = []
    for i, r in enumerate(Dstar):
        k = (r["ply"], r["n_legal"], r["n_opp_threats"] >= 1)
        j = used.get(k, 0)
        if j >= len(pool.get(k, [])):
            raise SystemExit("match infeasible at key %r" % (k,))
        s = pool[k][j]
        used[k] = j + 1
        s = dict(s, role="S", pair_id=i)
        matched_S.append(s)
        pairs.append((i, r["fnv"], s["fnv"]))
    return rows, D, Dstar, Dstar2, Sz, matched_S, pairs


# ------------------------------------------------------------------ arms
def train_arm(recs, arm: str, epochs: int, lr: float, keys=None):
    """Replicates A2's booked arm exactly, on CPU. Returns per-board out-of-fold preds."""
    import torch
    import torch.nn as nn
    import numpy as np

    torch.manual_seed(SEED)
    np.random.seed(SEED)
    n = len(recs)
    X = torch.tensor([r["board"] for r in recs], dtype=torch.float32)
    Lg = torch.zeros((n, W), dtype=torch.bool)
    T = torch.zeros((n, W), dtype=torch.bool)
    folds = torch.zeros(n, dtype=torch.long)
    for i, r in enumerate(recs):
        occ = sum((1 << j) for j, v in enumerate(r["board"]) if v != 0)
        for c in range(W):
            Lg[i, c] = (occ & COLMASK[c]) != COLMASK[c]
        for c in r["opt"]:
            T[i, c] = True
        folds[i] = fold_of(r["fnv"])

    if arm == "mlp":
        net = nn.Sequential(nn.Linear(W * H, 64), nn.ReLU(), nn.Linear(64, W))
    else:
        net = nn.Linear(W * H, W)
    net = net.to("cpu")

    def masked_logsoftmax(z, mask):
        neg = torch.finfo(z.dtype).min
        return z.masked_fill(~mask, neg) - torch.logsumexp(z.masked_fill(~mask, neg), dim=1, keepdim=True)

    def setval_loss(z, mask, tgt):
        ls = masked_logsoftmax(z, mask)
        neg = torch.finfo(ls.dtype).min
        return -ls.masked_fill(~tgt, neg).logsumexp(dim=1).mean()

    pred_all = torch.zeros(n, dtype=torch.long)
    per_fold = {}
    for k in range(5):
        tr = (folds != k).nonzero(as_tuple=True)[0]
        te = (folds == k).nonzero(as_tuple=True)[0]
        torch.manual_seed(SEED + k)
        if arm == "mlp":
            for m in net.modules():
                if isinstance(m, nn.Linear):
                    nn.init.kaiming_uniform_(m.weight, nonlinearity="relu")
                    nn.init.zeros_(m.bias)
        else:
            nn.init.normal_(net.weight, 0, 0.1)
            nn.init.zeros_(net.bias)
        opt = torch.optim.Adam(net.parameters(), lr=lr)
        Xtr, Ltr, Ttr = X[tr], Lg[tr], T[tr]
        nt = Xtr.shape[0]
        bs = 1024
        g = torch.Generator(device="cpu").manual_seed(SEED + k)
        net.train()
        for _ep in range(epochs):
            perm = torch.randperm(nt, generator=g)
            for s in range(0, nt, bs):
                bidx = perm[s:s + bs]
                z = net(Xtr[bidx])
                loss = setval_loss(z, Ltr[bidx], Ttr[bidx])
                opt.zero_grad()
                loss.backward()
                opt.step()
        net.eval()
        with torch.no_grad():
            z = net(X[te])
            neg = torch.finfo(z.dtype).min
            pred_all[te] = z.masked_fill(~Lg[te], neg).argmax(dim=1)
        per_fold[k] = te
    return pred_all.numpy(), per_fold


def arm_metrics(pred, recs, fold_vec=None):
    """Accuracy + computed chance per partition, overall, and per fold."""
    import numpy as np
    corr = np.array([pred[i] in recs[i]["opt"] for i in range(len(recs))], dtype=np.float64)
    ch = np.array([recs[i]["chance"] for i in range(len(recs))], dtype=np.float64)
    out = {"n": len(recs), "acc": round(float(corr.mean()), 4),
           "chance": round(float(ch.mean()), 4),
           "delta_vs_chance": round(float((corr - ch).mean()), 4)}
    if fold_vec is not None:
        fv = np.array(fold_vec)
        pfa = [round(float(corr[fv == k].mean()), 4) for k in range(5) if (fv == k).any()]
        out["per_fold_acc"] = pfa
        out["std"] = round(float(np.std(pfa)), 4)
        out["per_fold_delta"] = [round(float((corr[fv == k] - ch[fv == k]).mean()), 4)
                                 for k in range(5) if (fv == k).any()]
    out["_corr"] = corr
    out["_ch"] = ch
    return out


def boot_ci(vals, B=2000, seed=SEED):
    import numpy as np
    v = np.asarray(vals, dtype=float)
    n = len(v)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(B, n))
    m = v[idx].mean(axis=1)
    return [round(float(np.percentile(m, 2.5)), 4), round(float(np.percentile(m, 97.5)), 4)]


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="skip the FULL-corpus arms (harness smoke)")
    args = ap.parse_args()
    t0 = time.time()

    rows, D, Dstar, Dstar2, Sz, matched_S, pairs = build_corpus()
    recon = {
        "n_boards_a2": len(rows),
        "D_mission_geq2_threats": len(D),
        "D_strata": {},
        "Dstar_geq2_and_opp_geq1": len(Dstar),
        "Dstar_strata": {},
        "Dstar2_chance_lt_1": len(Dstar2),
        "S_all_single_threat": len(Sz),
        "S_matched": len(matched_S),
        "D_chance_mean": round(sum(r["chance"] for r in D) / len(D), 4),
        "Dstar_chance_mean": round(sum(r["chance"] for r in Dstar) / len(Dstar), 4),
        "Dstar2_chance_mean": round(sum(r["chance"] for r in Dstar2) / len(Dstar2), 4),
        "S_matched_chance_mean": round(sum(r["chance"] for r in matched_S) / len(matched_S), 4),
    }
    for r in D:
        recon["D_strata"][r["strata"]] = recon["D_strata"].get(r["strata"], 0) + 1
    for r in Dstar:
        recon["Dstar_strata"][r["strata"]] = recon["Dstar_strata"].get(r["strata"], 0) + 1
    print(json.dumps(recon, indent=2), flush=True)

    # ---- design.jsonl (the constructed set, verbatim rules)
    with open(DESIGN_OUT, "w") as f:
        for tag, rs in (("D", D), ("D*", Dstar), ("D**", Dstar2), ("S", matched_S)):
            for r in rs:
                f.write(json.dumps({k: v for k, v in r.items() if not k.startswith("_")}) + "\n")

    # ---- solver ground truth (rule 5): C solver on a designed-corpus sample
    control = {"ran": False}
    if os.path.exists(C_SOLVER):
        rng = random.Random(SEED)
        sample = rng.sample(Dstar, min(100, len(Dstar)))

        def cmask(a, b):
            mp = 0
            for src in (a, b):
                for r in range(H):
                    for c in range(W):
                        if (src >> (r * W + c)) & 1:
                            mp |= 1 << (c * 5 + r)
            return mp

        def cpos(a):
            mp = 0
            for r in range(H):
                for c in range(W):
                    if (a >> (r * W + c)) & 1:
                        mp |= 1 << (c * 5 + r)
            return mp

        lines = []
        for r in sample:
            a, b = board_to_masks(r["board"])
            lines.append(f"{cmask(a, b)} {cpos(a)}")
        try:
            pr = subprocess.run([C_SOLVER, "--probe"], input="\n".join(lines) + "\n",
                                capture_output=True, text=True, timeout=600)
            cv = [int(x) for x in pr.stdout.split()]
            agree = sum(1 for r, v in zip(sample, cv) if r["value"] == v)
            control = {"ran": True, "path": C_SOLVER, "n": len(sample),
                       "agreements": agree, "disagreements": len(sample) - agree}
        except Exception as e:  # noqa: BLE001
            control = {"ran": False, "error": repr(e)}
    print("solver control:", control, flush=True)

    # ---- fold vectors
    fold_Dstar = [fold_of(r["fnv"]) for r in Dstar]
    fold_S = [fold_of(r["fnv"]) for r in matched_S]
    fold_D = [fold_of(r["fnv"]) for r in D]
    fold_Dstar2 = [fold_of(r["fnv"]) for r in Dstar2]

    results = {"recon": recon, "solver_control": control, "arms": {}}

    # ---- PRIMARY: A2's exact arms trained on the whole corpus (continuity + designed eval)
    if not args.quick:
        for arm in ("mlp", "linear"):
            t1 = time.time()
            pred, _ = train_arm(rows, arm, epochs=120, lr=1e-3)
            print(f"[full-{arm}] trained in {time.time()-t1:.1f}s", flush=True)
            idx = {r["fnv"]: i for i, r in enumerate(rows)}
            pr_d = [pred[idx[r["fnv"]]] for r in D]
            pr_ds = [pred[idx[r["fnv"]]] for r in Dstar]
            pr_ds2 = [pred[idx[r["fnv"]]] for r in Dstar2]
            pr_s = [pred[idx[r["fnv"]]] for r in matched_S]
            mD = arm_metrics(pr_d, D, fold_D)
            mDs = arm_metrics(pr_ds, Dstar, fold_Dstar)
            mDs2 = arm_metrics(pr_ds2, Dstar2, fold_Dstar2)
            mS = arm_metrics(pr_s, matched_S, fold_S)
            # per-stratum breakdown on D*
            strata_stats = {}
            for s in sorted(set(r["strata"] for r in Dstar)):
                ii = [i for i, r in enumerate(Dstar) if r["strata"] == s]
                strata_stats[s] = {
                    "n": len(ii),
                    "acc": round(float(np.mean([mDs["_corr"][i] for i in ii])), 4),
                    "chance": round(float(np.mean([mDs["_ch"][i] for i in ii])), 4),
                }
            for key in ("Dstar_196", "Dstar2_88", "S_matched_196"):
                if key in ("Dstar_196", "S_matched_196"):
                    d = mDs if key == "Dstar_196" else mS
                else:
                    d = mDs2
                if d["chance"] < 1.0:
                    d["headroom_filled"] = round(
                        (d["acc"] - d["chance"]) / (1.0 - d["chance"]), 4)
            # A2 continuity partitions
            n = len(rows)
            corr = [1 if pred[i] in rows[i]["opt"] else 0 for i in range(n)]
            ch = [rows[i]["opt"].__len__() / rows[i]["n_legal"] for i in range(n)]
            folds_all = [fold_of(r["fnv"]) for r in rows]

            def part(mask, name):
                a = sum(corr[i] for i in range(n) if mask(rows[i]))
                b = sum(1 for i in range(n) if mask(rows[i]))
                c = sum(ch[i] for i in range(n) if mask(rows[i]))
                return {"n": b, "acc": round(a / b, 4) if b else None,
                        "chance": round(c / b, 4) if b else None}

            overall = {"n": n, "acc": round(sum(corr) / n, 4), "chance": round(sum(ch) / n, 4)}
            ostd = round(float((__import__("numpy").array(
                [sum(corr[i] for i in range(n) if folds_all[i] == k) /
                 max(1, sum(1 for i in range(n) if folds_all[i] == k)) for k in range(5)])).std()), 4)
            results["arms"][f"{arm}-full"] = {
                "info": {"train_rows": len(rows), "epochs": 120, "lr": 1e-3, "device": "cpu", "seed": SEED},
                "overall": overall, "overall_std_over_folds": ostd,
                "COMPOSED_B": part(lambda r: r["imm_wins"] >= 2, "COMPOSED_B"),
                "SIMPLE_B": part(lambda r: r["imm_wins"] <= 1, "SIMPLE_B"),
                "COMPOSED_A": part(lambda r: r["defA_threats"] >= 2, "COMPOSED_A"),
                "SIMPLE_A": part(lambda r: r["defA_threats"] <= 1, "SIMPLE_A"),
                "D_763": mD, "Dstar_196": mDs, "Dstar2_88": mDs2, "S_matched_196": mS,
                "Dstar_strata": strata_stats,
                "_corr_Dstar": mDs["_corr"], "_corr_S": mS["_corr"],
                "_ch_Dstar": mDs["_ch"], "_ch_S": mS["_ch"],
                "_corr_Dstar2": mDs2["_corr"], "_ch_Dstar2": mDs2["_ch"],
                "seconds": round(time.time() - t1, 1),
            }

    # ---- SECONDARY: DESIGN arms trained on D* u S only
    design_corpus = Dstar + matched_S
    fold_design = [fold_of(r["fnv"]) for r in design_corpus]
    nDs = len(Dstar)
    for arm in ("mlp", "linear"):
        t1 = time.time()
        pred, _ = train_arm(design_corpus, arm, epochs=120, lr=1e-3)
        pr_ds = list(pred[:nDs])
        pr_s = list(pred[nDs:])
        mDs = arm_metrics(pr_ds, Dstar, fold_Dstar)
        mS = arm_metrics(pr_s, matched_S, fold_S)
        for d in (mDs, mS):
            if d["chance"] < 1.0:
                d["headroom_filled"] = round((d["acc"] - d["chance"]) / (1.0 - d["chance"]), 4)
        results["arms"][f"{arm}-design"] = {
            "info": {"train_rows": len(design_corpus), "epochs": 120, "lr": 1e-3, "device": "cpu"},
            "Dstar_196": mDs, "S_matched_196": mS,
            "_corr_Dstar": mDs["_corr"], "_corr_S": mS["_corr"],
            "_ch_Dstar": mDs["_ch"], "_ch_S": mS["_ch"],
            "seconds": round(time.time() - t1, 1),
        }
    print(f"[done arms] {time.time()-t0:.1f}s", flush=True)

    # ---- GATES
    gates = {}

    def gate_a2b1(tag):
        a = results["arms"][tag]
        mD_c, mS_c = a["_corr_Dstar"], a["_corr_S"]
        lD_c, lS_c = results["arms"][tag.replace("mlp", "linear")]["_corr_Dstar"], \
            results["arms"][tag.replace("mlp", "linear")]["_corr_S"]
        d = (mD_c - mS_c) - (lD_c - lS_c)
        ci = boot_ci(d)
        sbar = float(d.mean())
        # per-fold statistic (house rule: std==0 -> INCONCLUSIVE)
        fv = __import__("numpy").array(fold_Dstar)
        perfold = [float(d[fv == k].mean()) for k in range(5) if (fv == k).any()]
        std = float(__import__("numpy").std(perfold))
        # A1-direction reporting
        d_mlp = float((mD_c - mS_c).mean())
        d_lin = float((lD_c - lS_c).mean())
        return {"tag": tag, "S_bar": round(sbar, 4), "ci95": ci, "ci_excludes_0": not (ci[0] <= 0 <= ci[1]),
                "per_fold": [round(x, 4) for x in perfold], "std_over_folds": round(std, 4),
                "n_pairs": int(len(d)),
                "delta_mlp_DminusS": round(d_mlp, 4), "delta_lin_DminusS": round(d_lin, 4),
                "a1_direction_dlin_minus_dmlp": round(d_lin - d_mlp, 4),
                "PASS": bool(sbar > 0.05 and not (ci[0] <= 0 <= ci[1]) and std != 0)}

    def gate_a2b2(tag, setname):
        a = results["arms"][tag]
        key = "_corr_Dstar" if setname == "D*196" else "_corr_Dstar2"
        ckey = "_ch_Dstar" if setname == "D*196" else "_ch_Dstar2"
        if key not in a or a.get(key) is None:
            return None
        corr, ch = np.asarray(a[key]), np.asarray(a[ckey])
        d = corr - ch
        ci = boot_ci(d)
        dbar = float(d.mean())
        return {"arm": tag, "set": setname, "n": int(len(d)),
                "acc": round(float(corr.mean()), 4), "chance": round(float(ch.mean()), 4),
                "delta": round(dbar, 4), "ci95": ci,
                "ci_excludes_0": not (ci[0] <= 0 <= ci[1]),
                "PASS": bool(dbar >= 0.05 and not (ci[0] <= 0 <= ci[1]))}

    if not args.quick:
        gates["G_A2b1_full_primary"] = gate_a2b1("mlp-full")
        gates["G_A2b1_design_secondary"] = gate_a2b1("mlp-design")
        g2 = {}
        for tag in [t for t in results["arms"] if t.endswith(("-full", "-design"))]:
            g2[tag + "|D*196"] = gate_a2b2(tag, "D*196")
        for tag in [t for t in results["arms"] if t.endswith("-full")]:
            g2[tag + "|D**88"] = gate_a2b2(tag, "D**88")
        gates["G_A2b2_signal"] = g2
        # frozen G-A2b2 reads the designed set D* (PREREG §4)
        any_pass = any(v and v["PASS"] for k, v in g2.items() if k.endswith("D*196"))
        gates["G_A2b2_verdict"] = "PASS" if any_pass else "FAIL (second strike)"
    # strip internal arrays before writing
    for a in results["arms"].values():
        for k in [k for k in a if k.startswith("_")]:
            a.pop(k, None)
        for sub in ("D_763", "Dstar_196", "Dstar2_88", "S_matched_196"):
            if sub in a:
                for k in [k for k in a[sub] if k.startswith("_")]:
                    a[sub].pop(k, None)
        for sub in ("Dstar_strata",):
            pass
    results["gates"] = gates
    results["wall_seconds"] = round(time.time() - t0, 1)
    results["energy_Wh"] = 0.0
    with open(METRICS, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(json.dumps({k: v for k, v in gates.items() if not isinstance(v, dict) or "tag" in v or "arm" in v},
                     indent=2, default=str), flush=True)
    print("wall_seconds:", results["wall_seconds"], flush=True)


if __name__ == "__main__":
    main()
