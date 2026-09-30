#!/usr/bin/env python3
"""MQ1 shadow — tensor-scale replication of growth-vs-fixed on the RTX 4050.

Pre-reg: proposals/runs/MQ1-growth-vs-fixed.md (shadow section).
Same protocol as the scalar arm, different scale:
  fixed: MLP(1,[64,64,1]) born full-size
  grown: starts MLP(1,[16,16,1]), grafts +8 neurons per hidden layer on plateau
Adam 1e-3, 4000 steps, batch 32, same 240/60 split (seed 42), 5 seeds/arm.

Growth operator (identical in spirit to scalar): append units with fresh init;
new inputs to the next layer are fresh-init too. Adam state is rebuilt after a
graft — part of the (dumb) operator, reported honestly, not hidden.

Run: /home/eileen/venvs/elephant-gpu/bin/python experiments/mq1_shadow.py
"""
import json
import math
import os
import random
import time

import torch
import torch.nn as nn

STEPS = 4000
BATCH = 32
EVAL_EVERY = 100
PLATEAU_WINDOW = 3          # evals (~300 steps)
PLATEAU_EPS = 0.02
START_W, MAX_W, GRAFT_K = 16, 64, 8
OUT = os.path.join(os.path.dirname(__file__), "..", "results", "mq1")
DEV = "cuda" if torch.cuda.is_available() else "cpu"


class GrowNet(nn.Module):
    """MLP with growable hidden widths (fresh-init grafts, honest operator)."""

    def __init__(self, widths):
        super().__init__()
        dims = [1] + list(widths) + [1]
        self.layers = nn.ModuleList(
            [nn.Linear(dims[i], dims[i + 1]) for i in range(len(dims) - 1)])

    def forward(self, x):
        h = x
        for i, layer in enumerate(self.layers):
            h = layer(h)
            if i < len(self.layers) - 1:
                h = torch.tanh(h)
        return h

    @torch.no_grad()
    def grow(self, idx, k):
        old, nxt = self.layers[idx], self.layers[idx + 1]
        dev = old.weight.device  # grafts must land where the model lives (CUDA)
        new = nn.Linear(old.in_features, old.out_features + k).to(dev)
        new.weight[:old.out_features] = old.weight
        new.bias[:old.out_features] = old.bias
        nn.init.uniform_(new.weight[old.out_features:], -1 / math.sqrt(old.in_features),
                         1 / math.sqrt(old.in_features))
        nn.init.zeros_(new.bias[old.out_features:])

        nxt_new = nn.Linear(new.out_features, nxt.out_features).to(dev)
        nxt_new.weight[:, :nxt.in_features] = nxt.weight
        nxt_new.bias[:] = nxt.bias
        nn.init.uniform_(nxt_new.weight[:, nxt.in_features:],
                         -1 / math.sqrt(nxt.in_features), 1 / math.sqrt(nxt.in_features))
        self.layers[idx], self.layers[idx + 1] = new, nxt_new

    def n_params(self):
        return sum(p.numel() for p in self.parameters())


def make_data():
    rng = random.Random(42)  # frozen dataset seed — identical to the scalar arm
    xs = [rng.uniform(-math.pi, math.pi) for _ in range(300)]
    ys = [math.sin(x) + rng.gauss(0, 0.15) for x in xs]
    t = lambda a: torch.tensor(a, dtype=torch.float32, device=DEV).unsqueeze(1)
    return (t(xs[:240]), t(ys[:240]), t(xs[240:]), t(ys[240:]))


def run_arm(arm, seed, lr, data):
    torch.manual_seed(seed)
    Xtr, Ytr, Xva, Yva = data
    widths = [MAX_W, MAX_W] if arm == "fixed" else [START_W, START_W]
    model = GrowNet(widths).to(DEV)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    growable = arm == "grown"
    history, grafts = [], []
    diverged_at = None

    for step in range(STEPS):
        i = random.randrange(Xtr.shape[0] - BATCH)
        xb, yb = Xtr[i:i + BATCH], Ytr[i:i + BATCH]
        opt.zero_grad()
        loss = nn.functional.mse_loss(model(xb), yb)
        loss.backward()
        opt.step()
        if not torch.isfinite(loss):
            diverged_at = step
            break

        if step % EVAL_EVERY == 0 or step == STEPS - 1:
            with torch.no_grad():
                v = nn.functional.mse_loss(model(Xva), Yva).item()
            history.append({"step": step, "val": v, "params": model.n_params()})

            if growable and len(history) > PLATEAU_WINDOW:
                w = [h["val"] for h in history[-(PLATEAU_WINDOW + 1):]]
                prev = sum(w[:-1]) / len(w[:-1])
                if prev > 0 and (prev - w[-1]) / prev < PLATEAU_EPS:
                    target = 0 if model.layers[0].out_features < MAX_W else 1
                    if model.layers[target].out_features < MAX_W:
                        model.grow(target, GRAFT_K)
                        opt = torch.optim.Adam(model.parameters(), lr=lr)  # operator cost
                        grafts.append({"step": step, "layer": target,
                                       "width": model.layers[target].out_features,
                                       "params": model.n_params()})

    return {"arm": arm, "seed": seed, "lr": lr, "history": history,
            "grafts": grafts, "diverged_at": diverged_at,
            "final_val": history[-1]["val"] if history else float("nan"),
            "final_params": history[-1]["params"] if history else 0}


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    data = make_data()
    print(f"MQ1 shadow — device={DEV} ({torch.cuda.get_device_name(0) if DEV == 'cuda' else 'cpu'}), "
          f"batch={BATCH}, steps={STEPS}", flush=True)

    results = []
    for arm in ("fixed", "grown"):
        for seed in range(5):
            t0 = time.time()
            r = run_arm(arm, seed, 1e-3, data)
            r["seconds"] = round(time.time() - t0, 1)
            results.append(r)
            print(f"  {arm} seed={seed}: val={r['final_val']:.5f} "
                  f"params={r['final_params']} grafts={len(r['grafts'])} "
                  f"diverged={r['diverged_at']} ({r['seconds']}s)", flush=True)

    f = sorted(r["final_val"] for r in results if r["arm"] == "fixed")
    g = sorted(r["final_val"] for r in results if r["arm"] == "grown")
    med_f, med_g = f[len(f) // 2], g[len(g) // 2]
    ratio = med_g / med_f if med_f else float("inf")
    verdict = "GROWN_WINS" if ratio < 0.95 else ("FIXED_WINS" if ratio > 1.05 else "TIE")
    summary = {"experiment": "MQ1-growth-vs-fixed (tensor shadow, CUDA)",
               "device": DEV, "lr": 1e-3, "steps": STEPS, "batch": BATCH,
               "fixed_vals": f, "grown_vals": g,
               "median_fixed": med_f, "median_grown": med_g, "ratio": ratio,
               "verdict": verdict,
               "total_grafts": sum(len(r["grafts"]) for r in results)}
    with open(os.path.join(OUT, "mq1_shadow_results.json"), "w") as fh:
        json.dump({"summary": summary, "runs": results}, fh, indent=2)
    print(json.dumps(summary, indent=2), flush=True)
