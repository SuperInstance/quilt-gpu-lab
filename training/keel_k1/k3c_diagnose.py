#!/usr/bin/env python3
"""K3c — collapse DIAGNOSIS (pre-registered: proposals/runs/K3c-plan.md).

Not a boundary roll. Replicates the K1/K3/K3b training loop EXACTLY
(same RNG order: manual_seed -> TinyPredictor init -> randint-per-step) with
ONE addition: per-100-step train-batch MSE + full-val reconstruction MSE,
plus per-domain val MSE at the end. Bit-identity with K3b's booked finals is
asserted per cell — if a replica diverges, the diagnosis is void (fail loud).

Cells (from K3b): P1 r.25@42 state (3.111202), P2 r.25@42 diff (3.079373),
P3 r.00@7 state (4.349166) poisoned; C1 r.00@7 diff (2.382021),
C2 r.25@1337 state (1.571900), C3 r.00@42 state (2.568257) healthy.
"""
import json, os, time
import torch
import torch.nn as nn

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_JSON = os.path.join(HERE, "results", "k3c_diagnose.json")

import importlib.util
spec = importlib.util.spec_from_file_location("k1run", os.path.join(HERE, "k1_run.py"))
k1run = importlib.util.module_from_spec(spec)
os.environ.setdefault("K1_CACHE", os.path.join(HERE, "cache.pt"))
spec.loader.exec_module(k1run)

def load(path):
    ck = torch.load(path, map_location="cpu")
    return ck["data"]["train"]["latents"], ck["data"]["val"]["latents"], ck["meta"]

def mix(tr_s, tr_l, r, seed):
    g = torch.Generator().manual_seed(99_991 + seed)
    n = min(len(tr_s), len(tr_l))
    pick = (torch.rand(n, generator=g) < r)
    out = torch.where(pick.unsqueeze(-1), tr_s[:n], tr_l[:n])
    return out[torch.randperm(n, generator=g)]

CELLS = [  # (name, r, seed, target, expected_final_from_K3b, role)
    ("P1", 0.25, 42,   "state", 3.111202, "poisoned (K3+K3b identical)"),
    ("P2", 0.25, 42,   "diff",  3.079373, "poisoned (K3+K3b identical)"),
    ("P3", 0.00, 7,    "state", 4.349166, "poisoned (order-only draw)"),
    ("C1", 0.00, 7,    "diff",  2.382021, "healthy control, same draw as P3"),
    ("C2", 0.25, 1337, "state", 1.571900, "healthy control, same r as P1"),
    ("C3", 0.00, 42,   "state", 2.568257, "healthy control, r=0 sibling of P3"),
]

def train_logged(target, seed, tr, va, va_sdom, va_ldom, floor):
    torch.manual_seed(seed)
    Xtr, Ytr = k1run.windows(tr); Xva, Yva = k1run.windows(va)
    model = k1run.TinyPredictor(Xtr.shape[-1]).to(k1run.DEV)
    opt = torch.optim.AdamW(model.parameters(), lr=k1run.LR)
    n = len(Xtr)

    def val_mse_of(seq):
        Xd, Yd = k1run.windows(seq)
        with torch.no_grad():
            rec = model(Xd.to(k1run.DEV))
            rec = rec + Xd[:, -1].to(k1run.DEV) if target == "diff" else rec
            return nn.functional.mse_loss(rec, Yd.to(k1run.DEV)).item()

    steps = list(range(0, k1run.STEPS + 1, 100))
    val_curve = [round(val_mse_of(va), 6)]  # step 0 (identical scoring path)
    tr_curve, wsum, wcnt = [], 0.0, 0
    for step in range(1, k1run.STEPS + 1):
        idx = torch.randint(0, n, (k1run.BATCH,))
        xb, yb = Xtr[idx].to(k1run.DEV), Ytr[idx].to(k1run.DEV)
        out = model(xb)
        tgt = (yb - xb[:, -1]) if target == "diff" else yb
        loss = nn.functional.mse_loss(out, tgt)
        loss.backward()
        opt.step(); opt.zero_grad()
        wsum += loss.item(); wcnt += 1
        if step % 100 == 0:
            tr_curve.append(round(wsum / wcnt, 6)); wsum, wcnt = 0.0, 0
            val_curve.append(round(val_mse_of(va), 6))
    final_val = val_curve[-1]
    dom_s, dom_l = round(val_mse_of(va_sdom), 6), round(val_mse_of(va_ldom), 6)

    # frozen classification (K3c-plan.md)
    t_first, t_last = tr_curve[0], tr_curve[-1]
    v_min = min(val_curve)
    if final_val < floor:
        mode = "healthy"
    elif t_last >= 0.8 * t_first:
        mode = "no-learn"
    elif t_last < 0.5 * t_first and final_val >= floor:
        mode = "train-val-split"
    elif final_val >= floor and v_min < 0.9 * final_val:
        mode = "late-loss"
    else:
        mode = "unclassified"
    domain_split = (dom_s >= floor) != (dom_l >= floor)
    return {"steps": steps, "train_mse": tr_curve, "val_mse": val_curve,
            "final_val_mse": final_val, "domain_val_mse": {"synth": dom_s, "lavfi": dom_l},
            "domain_split": domain_split, "mode": mode}

def main():
    t0 = time.time()
    tr_s, va_s, _ = load(os.path.join(HERE, "cache.pt"))
    tr_l, va_l, _ = load(os.path.join(HERE, "cache_lavfi.pt"))
    nva = min(len(va_s), len(va_l))
    va = torch.stack([x for pair in zip(va_s[:nva], va_l[:nva]) for x in pair])
    va_sdom, va_ldom = va_s[:nva], va_l[:nva]
    Xv, Yv = k1run.windows(va)
    floor = round(nn.functional.mse_loss(Yv, Xv[:, -1]).item(), 6)
    print(f"[K3c] persistence floor (fixed mixed val) = {floor}  (K3 booked 2.879)", flush=True)

    res = {"experiment": "K3c collapse diagnosis", "floor": floor, "cells": {}}
    for name, r, seed, target, expected, role in CELLS:
        trmix = mix(tr_s, tr_l, r, seed)
        cell = train_logged(target, seed, trmix, va, va_sdom, va_ldom, floor)
        cell.update({"r": r, "seed": seed, "target": target, "role": role,
                     "expected_k3b_final": expected,
                     "replication_match": abs(cell["final_val_mse"] - expected) < 5e-4})
        res["cells"][name] = cell
        print(f"[K3c] {name} r={r:.2f} {target}@{seed} [{role}]: final_val={cell['final_val_mse']}"
              f" (k3b {expected}, match={cell['replication_match']}) mode={cell['mode']}"
              f" dom={cell['domain_val_mse']} ({time.time()-t0:.0f}s)", flush=True)

    res["seconds"] = round(time.time() - t0, 1)
    json.dump(res, open(OUT_JSON, "w"), indent=1)
    print(f"[K3c] DONE {res['seconds']}s -> {OUT_JSON}", flush=True)
    print(json.dumps({k: {"mode": c["mode"], "domain_split": c["domain_split"],
                          "match": c["replication_match"]} for k, c in res["cells"].items()}), flush=True)

if __name__ == "__main__":
    main()
