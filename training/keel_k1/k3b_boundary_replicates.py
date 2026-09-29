#!/usr/bin/env python3
"""K3b — the boundary map, replicated draws (K3 repair).

Pre-registered (proposals/runs/K3b-plan.md) BEFORE build. K3 went
INVALID_HARNESS: one deterministic mix draw (r=0.25, seed 42) failed the
persistence floor for BOTH arms while seed 1337 passed comfortably at the same
r. ONE delta here: 3 draws per cell (seeds 42, 1337, 7); the floor applies to
per-cell draw-MEANS (floor value unchanged). Gates textually identical to K3.
"""
import json, os, time
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
OUT_JSON = os.path.join(RESULTS, "k3b_results.json")
DEV = "cuda" if torch.cuda.is_available() else "cpu"
SEEDS = (42, 1337, 7)
RATIOS = (1.00, 0.75, 0.50, 0.25, 0.00)
GATE_SPREAD = 0.05

import importlib.util
spec = importlib.util.spec_from_file_location("k1run", os.path.join(HERE, "k1_run.py"))
k1run = importlib.util.module_from_spec(spec)
os.environ.setdefault("K1_CACHE", os.path.join(HERE, "cache.pt"))
spec.loader.exec_module(k1run)  # module-level constants only; main() not called

def load(path):
    ck = torch.load(path, map_location="cpu")
    return ck["data"]["train"]["latents"], ck["data"]["val"]["latents"], ck["meta"]

def mix(tr_s, tr_l, r, seed):
    """Deterministic mix: keep ordering stable, choose per-slot by seeded coin at r."""
    g = torch.Generator().manual_seed(99_991 + seed)
    n = min(len(tr_s), len(tr_l))
    pick = (torch.rand(n, generator=g) < r)
    out = torch.where(pick.unsqueeze(-1), tr_s[:n], tr_l[:n])
    return out[torch.randperm(n, generator=g)]  # shuffle so windows straddle domains

def main():
    t0 = time.time()
    tr_s, va_s, meta_s = load(os.path.join(HERE, "cache.pt"))
    tr_l, va_l, meta_l = load(os.path.join(HERE, "cache_lavfi.pt"))
    # val = fixed 50/50 interleave (same testbed for every r; identical to K3)
    nva = min(len(va_s), len(va_l))
    va = torch.stack([x for pair in zip(va_s[:nva], va_l[:nva]) for x in pair])
    persistence = torch.nn.functional.mse_loss(va[1:], va[:-1]).item()
    res = {"experiment": "K3b boundary map (3 draws, mean-gated K3 repair)",
           "ratios": list(RATIOS), "seeds": SEEDS, "persistence_mse": round(persistence, 6),
           "meta": {"synth": meta_s["encoder"], "lavfi": meta_l["encoder"], "dim": meta_s["latent_dim"]},
           "grid": {}, "cell_mean": {}, "rel_win_by_ratio": {}}
    for r in RATIOS:
        for target in ("state", "diff"):
            for seed in SEEDS:
                trmix = mix(tr_s, tr_l, r, seed)
                mse, _ = k1run.run_arm(target, seed, trmix, va)
                res["grid"][f"{target}_r{r}_{seed}"] = round(mse, 6)
                print(f"[K3b] r={r:.2f} {target}@{seed}: mse={mse:.6f} ({time.time()-t0:.0f}s)", flush=True)
            res["cell_mean"][f"state_r{r}"] = round(sum(res["grid"][f"state_r{r}_{s}"] for s in SEEDS) / len(SEEDS), 6)
            res["cell_mean"][f"diff_r{r}"] = round(sum(res["grid"][f"diff_r{r}_{s}"] for s in SEEDS) / len(SEEDS), 6)
        rel = {s: (res["grid"][f"state_r{r}_{s}"] - res["grid"][f"diff_r{r}_{s}"])
                  / res["grid"][f"state_r{r}_{s}"] for s in SEEDS}
        res["rel_win_by_ratio"][f"{r:.2f}"] = round(sum(rel.values()) / len(SEEDS), 4)
    healthy = all(v < persistence for v in res["cell_mean"].values())
    xs = list(RATIOS); ys = [res["rel_win_by_ratio"][f"{r:.2f}"] for r in RATIOS]
    def spearman(a, b):
        ra = torch.tensor(a).argsort().argsort().float()
        rb = torch.tensor(b).argsort().argsort().float()
        num = ((ra - ra.mean()) * (rb - rb.mean())).sum()
        den = (ra - ra.mean()).norm() * (rb - rb.mean()).norm()
        return float(num / den) if den > 0 else 0.0
    rho = spearman(xs, ys)
    spread = max(ys) - min(ys)
    if not healthy:
        verdict = "INVALID_HARNESS"
    elif spread >= GATE_SPREAD and rho < 0:
        r_star = None
        for i in range(len(xs) - 1):
            if ys[i] > 0 >= ys[i + 1]:
                x0, x1, y0, y1 = xs[i], xs[i + 1], ys[i], ys[i + 1]
                r_star = round(x0 + (0 - y0) * (x1 - x0) / (y1 - y0), 3)
                break
        verdict = f"BOUNDARY_MAPPED (r*={r_star if r_star is not None else 'edge:' + ('<0' if ys[0] < 0 else '>1')})"
    else:
        verdict = "NO_BOUNDARY"
    res.update({"spearman_r_relwin": round(rho, 3), "spread": round(spread, 4),
                "verdict": verdict, "seconds": round(time.time() - t0, 1)})
    os.makedirs(RESULTS, exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(res, f, indent=2)
    print(json.dumps({"experiment": "K3b", "verdict": verdict, "rel_win_by_ratio": res["rel_win_by_ratio"],
                      "cell_mean": res["cell_mean"], "spearman": res["spearman_r_relwin"],
                      "spread": res["spread"]}, indent=2))

if __name__ == "__main__":
    main()
