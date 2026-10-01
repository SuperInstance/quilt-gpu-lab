#!/usr/bin/env python3
"""COMP0 — federation of dedicated micro-trunks with between-cell routing.

Pre-registered: proposals/runs/COMP0-federation.md (2026-10-01, before build).
Composes IE3 (dedicated specialist trunks), D13d (correlation router, not
reward), D1b (look-again to an independent-reach second choice).

Arms at matched TOTAL params (see prereg):
  JOINT      64->64->1   4225 params, trained on ALL items
  SINGLE     64->32->1   2113 params, trained on ALL items
  FED        2 x 64->32->1 (4226), one per regime, correlation router
  FED+LA     same cells + look-again (tau calibrated on train only)

Corpus: D5 probe foundry probes.jsonl (seed 2718, sha256 hash-split).
Run:  python -m experiments.comp0_federation            (guarded, fires GPU)
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

LAB = Path(__file__).resolve().parents[1]
OUT_DIR = LAB / "results" / "comp0"
PROBES = LAB / "probes.jsonl"
GUARD_TIMEOUT_S = 1800.0
SEEDS = [2718, 2719, 2720]
D = 64                 # hashed BoW dim (frozen in prereg)
H_CELL = 32            # cell hidden
H_JOINT = 64           # joint hidden (param-matched: 4225 vs 2x2113)
EPOCHS = 300
BATCH = 16
LR = 1e-3
TAU_PCT = 20           # look-again tau percentile on train (frozen)


# ── corpus: reuse D5 foundry on disk ────────────────────────────────────────
def load_corpus() -> list[dict]:
    if not PROBES.exists():
        print("probes.jsonl missing — regenerating via experiments.d5_probe_foundry")
        import experiments.d5_probe_foundry as d5
        d5.main()
    items = [json.loads(l) for l in PROBES.read_text().splitlines() if l.strip()]
    train = [it for it in items if int(it["sha256"][0], 16) < 12]
    held = [it for it in items if int(it["sha256"][0], 16) >= 12]
    return train, held


# ── featurization: word count BoW hashed to D dims ─────────────────────────
def _tok(text: str) -> list[str]:
    out, cur = [], []
    for ch in text.lower():
        if ch.isalnum():
            cur.append(ch)
        elif cur:
            out.append("".join(cur)); cur = []
    if cur:
        out.append("".join(cur))
    return out


def featurize(item: dict) -> np.ndarray:
    v = np.zeros(D, dtype=np.float32)
    for tok in _tok(item["claim"] + " " + item["evidence"]):
        h = int(hashlib.sha1(tok.encode()).hexdigest(), 16) % D
        v[h] += 1.0
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def y_of(item: dict) -> int:
    return 1 if item["label"] == "canon" else 0


# ── correlation router (D13d): centroid keys, Pearson score, 0 params ──────
def pearson(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean(); b = b - b.mean()
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


class CorrRouter:
    def __init__(self, regimes: list[str], train_items: list[dict]):
        self.regimes = regimes
        self.keys = {}
        for r in regimes:
            vecs = np.stack([featurize(it) for it in train_items if it["kind"] == r])
            self.keys[r] = vecs.mean(axis=0)

    def scores(self, item: dict) -> dict[str, float]:
        v = featurize(item)
        return {r: pearson(v, self.keys[r]) for r in self.regimes}

    def order(self, item: dict) -> list[str]:
        return sorted(self.regimes, key=lambda r: -self.scores(item)[r])


# ── torch nets ──────────────────────────────────────────────────────────────
def build_net(hid: int):
    import torch.nn as nn
    return nn.Sequential(nn.Linear(D, hid), nn.Tanh(), nn.Linear(hid, 1))


def train_net(model, X, Y, seed, device):
    import torch
    torch.manual_seed(seed)
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    lossf = torch.nn.BCEWithLogitsLoss()
    n = len(X)
    for _ep in range(EPOCHS):
        perm = torch.randperm(n, device=X.device)
        for i in range(0, n, BATCH):
            idx = perm[i:i + BATCH]
            xb, yb = X[idx], Y[idx]
            opt.zero_grad()
            loss = lossf(model(xb).squeeze(-1), yb)
            loss.backward()
            opt.step()
    return model


def predict(model, X) -> np.ndarray:
    import torch
    with torch.no_grad():
        p = torch.sigmoid(model(X).squeeze(-1))
    return p.cpu().numpy()


def ramp_burn(device) -> dict:
    """INSTRUMENT-01: >=0.6 s sustained synced load before any timed readout."""
    import torch
    a = torch.randn(2048, 2048, device=device)
    t0 = time.time(); synced = False
    while time.time() - t0 < 0.6:
        for _ in range(20):
            a = a @ a; a /= a.norm()
        torch.cuda.synchronize(); synced = True
    return {"ramp_s": round(time.time() - t0, 3), "synced": synced}


# ── inner (measured) run ────────────────────────────────────────────────────
def run_inner(out_dir: Path) -> int:
    import torch
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    out_dir.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    train_items, held_items = load_corpus()
    regimes = sorted({it["kind"] for it in train_items})
    assert len(regimes) == 2, f"expected K=2 regimes, got {regimes}"

    Xtr_all = torch.tensor(np.stack([featurize(it) for it in train_items]), device=device)
    Ytr_all = torch.tensor(np.array([y_of(it) for it in train_items], dtype=np.float32), device=device)
    Xhe = torch.tensor(np.stack([featurize(it) for it in held_items]), device=device)
    yhe = np.array([y_of(it) for it in held_items])

    ramp = ramp_burn(device) if device.type == "cuda" else {"ramp_s": 0.0, "synced": True, "device": "cpu"}

    router = CorrRouter(regimes, train_items)

    # router audit (train + held-out): does argmax-corr find the true regime?
    def router_acc(items):
        ok = sum(1 for it in items if router.order(it)[0] == it["kind"])
        return ok / len(items)
    router_audit = {"train_acc": round(router_acc(train_items), 4),
                    "heldout_acc": round(router_acc(held_items), 4)}

    per_seed = []
    for seed in SEEDS:
        arms = {}
        # -- JOINT -------------------------------------------------------
        joint = train_net(build_net(H_JOINT).to(device), Xtr_all, Ytr_all, seed, device)
        pj = predict(joint, Xhe)
        arms["JOINT"] = (pj >= 0.5).astype(int)

        # -- BEST-SINGLE (one cell size, trained on ALL) -------------------
        single = train_net(build_net(H_CELL).to(device), Xtr_all, Ytr_all, seed, device)
        ps = predict(single, Xhe)
        arms["SINGLE"] = (ps >= 0.5).astype(int)

        # -- FED: one dedicated cell per regime slice ---------------------
        cells, Xsl, Ysl = {}, {}, {}
        for r in regimes:
            idx = [i for i, it in enumerate(train_items) if it["kind"] == r]
            Xsl[r] = Xtr_all[idx]
            Ysl[r] = Ytr_all[idx]
            cells[r] = train_net(build_net(H_CELL).to(device), Xsl[r], Ysl[r], seed, device)

        # per-item cell reads on held-out (needed for FED and FED+LA)
        reads, margins = {}, {}
        for r in regimes:
            p = predict(cells[r], Xhe)
            reads[r] = p
            margins[r] = np.abs(p - 0.5)

        fed = np.zeros(len(held_items), dtype=int)
        la_trig = 0
        la_flip = 0
        # tau: 20th pct of ROUTED cell confidence margin on TRAIN items
        tr_read = {r: predict(cells[r], Xtr_all) for r in regimes}
        tr_margins = np.array([np.abs(tr_read[router.order(it)[0]][i] - 0.5)
                               for i, it in enumerate(train_items)])
        tau = float(np.percentile(tr_margins, TAU_PCT))

        for i, it in enumerate(held_items):
            order = router.order(it)
            r1, r2 = order[0], order[1]
            fed[i] = int(reads[r1][i] >= 0.5)
            # look-again: short-reach evidence -> independent-reach 2nd cell
            if margins[r1][i] < tau:
                la_trig += 1
                if margins[r2][i] > margins[r1][i]:
                    la_flip += 1
                    fed[i] = int(reads[r2][i] >= 0.5)  # re-read wins

        # FED arm (no LA): recompute clean routing-only predictions
        fed_nola = np.array([int(reads[router.order(it)[0]][i] >= 0.5)
                             for i, it in enumerate(held_items)])
        arms["FED"] = fed_nola
        arms["FED_LA"] = fed

        def acc(pred):
            return float((pred == yhe).mean())
        boards = {a: {"full": round(acc(p), 4)} for a, p in arms.items()}
        for a, p in arms.items():
            for r in regimes:
                idx = [i for i, it in enumerate(held_items) if it["kind"] == r]
                boards[a][r] = round(float((p[idx] == yhe[idx]).mean()), 4)

        per_seed.append({
            "seed": seed, "boards": boards, "tau_la": round(tau, 4),
            "la_triggers": la_trig, "la_flips": la_flip,
            "params": {"JOINT": 64 * H_JOINT + H_JOINT + H_JOINT + 1,
                       "SINGLE": 64 * H_CELL + H_CELL + H_CELL + 1,
                       "FED": 2 * (64 * H_CELL + H_CELL + H_CELL + 1),
                       "FED_LA": 2 * (64 * H_CELL + H_CELL + H_CELL + 1)},
        })
        print(f"seed {seed}: " + json.dumps(boards), flush=True)

    # ── aggregate: mean±std, frozen gates ──────────────────────────────────
    def stat(arm, board="full"):
        v = np.array([s["boards"][arm][board] for s in per_seed], dtype=float)
        return float(v.mean()), float(v.std())

    agg = {a: {"mean": round(stat(a)[0], 4), "std": round(stat(a)[1], 4)} for a in
           ("JOINT", "SINGLE", "FED", "FED_LA")}
    chance = float(max(yhe.mean(), 1 - yhe.mean()))  # majority class, computed

    def gate(d_arm, base, margin):
        m_diff = stat(d_arm)[0] - stat(base)[0]
        degenerate = stat(d_arm)[1] == 0.0 or stat(base)[1] == 0.0  # prereg: std==0 -> INCONCLUSIVE, never PASS
        return {"diff": round(m_diff, 4), "margin_required": margin,
                "degenerate_std0": bool(degenerate),
                "verdict": ("INCONCLUSIVE" if degenerate else
                            ("PASS" if m_diff >= margin else "FAIL"))}

    g1 = gate("FED", "SINGLE", 0.05)      # federation > best-single
    g2 = gate("FED_LA", "FED", 0.01)      # look-again > federation
    g3 = gate("FED", "JOINT", 0.05)       # secondary: federation > joint

    n_complete = len(per_seed)
    truncated = n_complete < len(SEEDS)
    if truncated:
        for g in (g1, g2, g3):
            g["verdict"] = "INCONCLUSIVE (TRUNC-B)"
    overall = ("KEEP" if (g1["verdict"] == "PASS" and g2["verdict"] == "PASS")
               else ("SPLIT_KEEP_GATE1" if g1["verdict"] == "PASS"
                     else ("INCONCLUSIVE" if any(g["verdict"].startswith("INCONCLUSIVE")
                                                 for g in (g1, g2)) else "KILL")))

    result = {
        "experiment": "COMP0 federation of dedicated micro-trunks (between-cell routing)",
        "prereg": "proposals/runs/COMP0-federation.md",
        "composed_of": {"IE3": "dedicated specialist trunks (dilution)",
                        "D13d": "correlation router (not reward)",
                        "D1b": "look-again to independent-reach second choice"},
        "device": str(device), "torch": torch.__version__,
        "corpus": {"source": "probes.jsonl (D5 foundry, seed 2718, reused)",
                   "n_train": len(train_items), "n_heldout": len(held_items),
                   "regimes": regimes},
        "chance_baseline_majority": round(chance, 4),
        "router_audit": router_audit,
        "aggregate_full_board": agg,
        "gates": {"G1_fed_gt_single": g1, "G2_la_gt_fed": g2,
                  "G3_fed_gt_joint_secondary": g3},
        "per_seed": per_seed,
        "ramp_receipt": ramp,
        "wall_seconds": round(time.time() - t_start, 1),
        "seeds_complete": n_complete,
        "verdict": overall,
    }
    (out_dir / "comp0_results.json").write_text(json.dumps(result, indent=2))
    print("VERDICT " + overall + " | agg " + json.dumps(agg) +
          " | chance " + str(round(chance, 4)) +
          " | router " + json.dumps(router_audit), flush=True)
    return 0


# ── outer (guarded) run ─────────────────────────────────────────────────────
def run_outer(out_dir: Path) -> int:
    sys.path.insert(0, str(LAB))
    import guard
    g = guard.Guard(timeout_s=GUARD_TIMEOUT_S, task_id="COMP0-federation",
                    agent="quilt-gpu-lab keeper (Lucineer, main Super Z)",
                    seed="2718,2719,2720", receipt_dir=str(out_dir / "guard"))
    ok = g.preflight()
    if not ok:  # co-tenancy rule: retry once after 60 s, else NOT-RUN
        print(f"PREFLIGHT REFUSED: {g.breach} — retry once after 60 s", flush=True)
        time.sleep(60.0)
        ok = g.preflight()
    if not ok:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "comp0_results.json").write_text(json.dumps(
            {"lane": "COMP0-federation", "verdict": "NOT-RUN",
             "reason": f"guard preflight refused twice (<1 GB free): {g.breach}"}, indent=2))
        g.emit_receipt(verdict="VOID", void_reason=f"preflight refused twice: {g.breach}")
        print("BOOKED NOT-RUN (guard preflight refused twice)", flush=True)
        return 2

    cmd = [sys.executable, str(Path(__file__).resolve()), "--inner", "--out", str(out_dir)]
    rc, out, err = g.run(cmd, cwd=str(LAB), env=dict(os.environ))
    print(f"inner rc={rc}", flush=True)
    print(out[-3000:], flush=True)
    if err.strip():
        print("stderr tail:", err[-800:], flush=True)
    if rc == 0:
        rpath, receipt = g.emit_receipt()
        okv, msg = g.validate_receipt(rpath)
        print(f"guard MEASURED receipt: {rpath} valid={okv} {msg}", flush=True)
    else:
        g.emit_receipt(verdict="VOID", void_reason=f"inner exit {rc}")
        print("VOID receipt sealed for failed run", flush=True)
    return 0 if rc == 0 else 2


if __name__ == "__main__":
    args = sys.argv[1:]
    out = OUT_DIR
    if "--out" in args:
        out = Path(args[args.index("--out") + 1])
    if "--inner" in args:
        sys.exit(run_inner(out))
    sys.exit(run_outer(out))
