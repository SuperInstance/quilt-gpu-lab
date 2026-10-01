#!/usr/bin/env python3
"""D12j — GPU-scale width: does the W·T product rule survive W=64/128?

Frozen per proposals/runs/D12j-gpu-width-plan.md (pre-registered 2026-10-01,
pushed before fire). D12i semantics, vectorized in torch on the 4050:
- pairing: seeded shuffle, consecutive pairing
- streams: per pair/channel/step — correlated w.p. p (both cells get the
  same base ±1), else each cell draws an independent ±1
- corr(a,b) = |Σ products| / (W·T); discovery = FIRST-index tie-break argmax
  (D12i's max(others, key=corr) semantics, replicated deterministically)
- acc bar 0.9; floor = min T on the ladder with mean acc ≥ bar
- streams RE-DRAWN (torch CUDA generator, the D12i seed formula family);
  claims are about the floor RULES, not per-draw identity (booked in plan).
Instrument hygiene (wave-73 law): 0.6s sustained GPU ramp before the grid;
frozen gates untouched.
"""
import json
import os
import subprocess
import time
import traceback

import torch

SEED = 2718
W_VALUES = (32, 64, 128)
N_VALUES = (32, 64, 128)
P_VALUES = (0.3, 0.5, 0.7)
T_VALUES = (1, 2, 3, 5, 10, 25, 50, 100)
DRAWS = 3
ACC_BAR = 0.9
HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
OUT_JSON = os.path.join(LAB, "results", "d12j_gpu_width.json")


def log(msg):
    print("[d12j %s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def preflight():
    free, total = torch.cuda.mem_get_info()
    if free < 1024 ** 3:
        raise RuntimeError("preflight: only %d B VRAM free (need 1 GiB)" % free)
    temp = None
    try:
        out = subprocess.run(
            ["/usr/lib/wsl/lib/nvidia-smi", "--query-gpu=temperature.gpu",
             "--format=csv,noheader"], capture_output=True, text=True,
            timeout=10).stdout.strip().splitlines()[0]
        temp = float(out)
        if temp > 80:
            raise RuntimeError("preflight: GPU temp %.0fC > 80C" % temp)
    except RuntimeError:
        raise
    except Exception:
        pass  # temp probe optional; VRAM gate is the hard one
    return {"free_vram_bytes": int(free), "temp_c": temp}


def ramp(seconds=0.6):
    """Wave-73 instrument law: sustained synced load before any timing."""
    x = torch.rand(4096, 4096, device="cuda")
    t0 = time.time()
    while time.time() - t0 < seconds:
        x = (x @ x).clamp_(-2.0, 2.0)
    torch.cuda.synchronize()


def run_cell(n, p, t, w, draw):
    dev = "cuda"
    g = torch.Generator(device=dev)
    g.manual_seed(SEED * 100000 + w * 10000 + n * 1000 +
                  int(p * 100) * 10 + t * 2 + draw)
    npairs = n // 2
    keep = torch.rand(npairs, w, t, generator=g, device=dev) < p
    base = (torch.randint(0, 2, (npairs, w, t), generator=g, device=dev)
            * 2 - 1).to(torch.float32)
    ia = (torch.randint(0, 2, (npairs, w, t), generator=g, device=dev)
          * 2 - 1).to(torch.float32)
    ib = (torch.randint(0, 2, (npairs, w, t), generator=g, device=dev)
          * 2 - 1).to(torch.float32)
    sa = torch.where(keep, base, ia)
    sb = torch.where(keep, base, ib)
    perm = torch.randperm(n, generator=g, device=dev)
    X = torch.zeros(n, w, t, device=dev)
    a_idx, b_idx = perm[0::2], perm[1::2]
    X[a_idx] = sa
    X[b_idx] = sb
    C = (X.reshape(n, -1) @ X.reshape(n, -1).T)
    C.abs_()
    C /= (w * t)
    C.fill_diagonal_(float("-inf"))
    # deterministic FIRST-index argmax over others (unique-min trick:
    # among maxima pick the smallest cell index, D12i-compatible)
    maxv = C.max(dim=1, keepdim=True).values
    is_max = C == maxv
    idxplus = torch.arange(1, n + 1, device=dev,
                           dtype=torch.float32).unsqueeze(0).expand(n, n)
    # argmin returns the 0-based COLUMN index already; the +1 encoding only
    # orders the VALUES so the first-max column wins the min. No offset.
    # (r1 harness bug: a stray '- 1' here made disc = partner-1 for every
    # cell -> acc == 0.0 everywhere; receipt archived as HARNESS_INVALID.)
    disc = torch.where(is_max, idxplus,
                       torch.full_like(idxplus, float("inf"))
                       ).argmin(dim=1).to(torch.long)
    partner = torch.zeros(n, dtype=torch.long, device=dev)
    partner[a_idx] = b_idx
    partner[b_idx] = a_idx
    return (disc == partner).float().mean().item()


def main():
    receipt = {
        "schema": "d12j",
        "plan": "proposals/runs/D12j-gpu-width-plan.md",
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "guard": {}, "torch": torch.__version__,
        "grid": [], "floors": {}, "verdicts": {}, "ok": False,
    }
    t0 = time.time()
    try:
        receipt["guard"] = preflight()
        ramp()
        log("preflight + ramp done; running %d-cell grid"
            % (len(W_VALUES) * len(N_VALUES) * len(P_VALUES) * len(T_VALUES)))
        accs = {}
        for w in W_VALUES:
            for n in N_VALUES:
                for p in P_VALUES:
                    for t in T_VALUES:
                        vals = [run_cell(n, p, t, w, d) for d in range(DRAWS)]
                        mean = sum(vals) / len(vals)
                        accs[(w, n, p, t)] = mean
                        receipt["grid"].append({
                            "W": w, "N": n, "p_corr": p, "T": t,
                            "partner_id_acc": round(mean, 4),
                            "draws": [round(v, 4) for v in vals],
                            "chance": round(1 / (n - 1), 4),
                        })
        log("grid complete; computing floors")

        def floor(w, n, p):
            for t in T_VALUES:
                if accs[(w, n, p, t)] >= ACC_BAR:
                    return t
            return None

        floors = {(w, n, p): floor(w, n, p)
                  for w in W_VALUES for n in N_VALUES for p in P_VALUES}
        receipt["floors"] = {"|".join(map(str, k)): v
                             for k, v in sorted(floors.items())}

        # J1: floors non-increasing in W at every (N, p); None counts as +inf
        inversions = []
        for n in N_VALUES:
            for p in P_VALUES:
                seq = [floors[(w, n, p)] for w in W_VALUES]
                inf = [float("inf") if v is None else v for v in seq]
                if any(inf[i] < inf[i + 1] for i in range(len(inf) - 1)):
                    inversions.append({"N": n, "p": p, "floors": seq})
        j1 = not inversions

        # J2/J3 at the hardest corner (N=128, p=0.3)
        f32 = floors[(32, 128, 0.3)]
        f64 = floors[(64, 128, 0.3)]
        f128 = floors[(128, 128, 0.3)]
        j2 = f128 is not None and f128 <= 3
        j3 = f32 == f128

        if not j1:
            verdict = "KILL-monotonicity (D12i's rule broken at scale)"
        elif j3:
            verdict = "KILL-product-rule / PLATEAU (floor is steps-bound)"
        elif j2:
            verdict = "KEEP (product rule survives to W=128)"
        else:
            verdict = "PARTIAL (floor keeps shrinking, sub-linearly)"
        receipt["verdicts"] = {
            "J1_monotone": j1, "J1_inversions": inversions,
            "J2_boundary": j2,
            "corner_floors": {"W32": f32, "W64": f64, "W128": f128},
            "J3_plateau": j3, "verdict": verdict,
        }
        receipt["ok"] = True
        log("verdict: " + verdict)
    except Exception:
        receipt["ok"] = False
        receipt["error"] = traceback.format_exc()
        receipt["verdicts"] = {"verdict": "KILL-harness"}
        log("HARNESS FAIL:\n" + receipt["error"])
    finally:
        receipt["wall_s"] = round(time.time() - t0, 2)
        os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
        with open(OUT_JSON, "w") as f:
            json.dump(receipt, f, indent=1, default=str)
        log("receipt -> %s (wall %ss)" % (OUT_JSON, receipt["wall_s"]))


if __name__ == "__main__":
    main()
