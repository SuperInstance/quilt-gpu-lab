"""D6 — tiny "fun" scorer + ranked seed bank for cargo-line-tycoon procgen.

Source: the REAL cargo-line-tycoon procgen (no synthetic fallback). The
world generator is the GameEngine constructor (game/src/engine.js): seeded
pencil ports (±0.3° jitter, ~25% decoys), seeded per-port markets, seeded
reveal schedule — then TICKS ticks of the deterministic world loop (panama /
chokepoint events, price drift, ambient reveals) with no player actions.
Driver: tools/d6_worldgen.js (node, JSONL), called via subprocess list form.

Pipeline (seed 2718 everywhere):
  1. Batch-generate 3000 worlds (seeds 1..3000) from the engine; extract
     per-world scalar features. Probed first (30 seeds) — features with zero
     seed-variance (demand entropy: demands are static uniform 1.0; decoy
     share: fixed 4/31; reveal count: index-based schedule) are EXCLUDED and
     the "resource entropy" slot is redefined on the resource field that
     actually varies (market prices), documented below.
  2. Transparent fun-proxy = fixed-weight z-scored sum (weights
     pre-registered before training; z-stats frozen on the TRAIN split).
  3. Two tiny MLPs (<1M params each) trained to predict the proxy from raw
     world tensors:
       model A (upper bound): condensed port distance matrix + binned tensor
       model B (shippable):   binned tensor only (8x8 grid, markets, hists)
  4. Held-out Spearman ρ (predicted vs proxy) on 240 held-out seeds;
     score all 3000 seeds with the better-ρ model; write top-25 to
     results/d6_seed_bank.json.

Verdict (pre-registered, on model B — the deployable scorer):
  KEEP    if ρ_B ≥ 0.60
  KILL    if ρ_B < 0.30
  else INCONCLUSIVE.  (Random ranking ≈ 0.)
"""
from __future__ import annotations

import heapq
import json
import math
import subprocess

import numpy as np
import torch
import torch.nn as nn

SEED = 2718
TYCOON = "/home/eileen/projects/cargo-line-tycoon"
DRIVER = "/home/eileen/projects/quilt-gpu-lab/tools/d6_worldgen.js"
TICKS = 40
N_WORLDS = 3000          # seeds 1..3000: train + heldout + score range
N_TRAIN, N_HELD = 960, 240
TOP_K = 25
KNN_K = 3                # shipping-lane graph: each port -> k nearest by nm
RADIUS_NM = 1200.0       # radius-graph threshold for the connectivity feature
PRICE_BINS = np.linspace(-0.30, 0.30, 9)  # fixed 8 bins for log(price/base)
# Fun-proxy weights (pre-registered; sum = 1.0). Rationale: a fun world to
# ship in is CONNECTED (few stranded clusters), PRICE-VARIED (arbitrage
# opportunities spread across price levels), ROUTE-DIVERSE (short/long/medium
# legs), REACHABLE (many playable OD pairs), with mild price DISPERSION, in a
# world that is ALIVE (events firing). Documented, no magic.
PROXY_WEIGHTS = {
    "lcc_fraction": 0.28,        # largest-CC fraction, radius graph
    "price_entropy_bits": 0.24,  # entropy of markets over log-price bins
    "route_diversity_nm": 0.20,  # std of finite-pair shortest-path lengths
    "reachability": 0.14,        # finite OD pairs / all pairs
    "price_dispersion": 0.08,    # std of log(price/base)
    "activity": 0.06,            # 0.5*z(cp_stress) + 0.5*z(panama_frac)
}


def dist_matrix(P: list[dict]) -> np.ndarray:
    """Great-circle distances (nm) between all ports, vectorized haversine."""
    lat = np.radians(np.array([p["lat"] for p in P]))
    lng = np.radians(np.array([p["lng"] for p in P]))
    dlat = lat[:, None] - lat[None, :]
    dlng = lng[:, None] - lng[None, :]
    h = np.sin(dlat / 2) ** 2 + np.cos(lat)[:, None] * np.cos(lat)[None, :] * np.sin(dlng / 2) ** 2
    return 2.0 * 3440.065 * np.arcsin(np.sqrt(np.clip(h, 0.0, 1.0)))


def knn_adjacency(D: np.ndarray) -> list[list[set]]:
    n = D.shape[0]
    out: list[list[set]] = [[set(), set()] for _ in range(n)]  # [knn, radius]
    for i in range(n):
        for j in np.argsort(D[i])[1 : KNN_K + 1]:
            out[i][0].add(int(j))
            out[int(j)][0].add(i)
        for j in range(n):
            if i != j and D[i, j] <= RADIUS_NM:
                out[i][1].add(j)
    return out


def dijkstra(n: int, adj: list[list[tuple[int, float]]], src: int) -> list[float]:
    dist = [math.inf] * n
    dist[src] = 0.0
    pq = [(0.0, src)]
    seen = [False] * n
    while pq:
        d, u = heapq.heappop(pq)
        if seen[u]:
            continue
        seen[u] = True
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    return dist


def largest_cc_fraction(n: int, adj_r: list[set]) -> float:
    seen = [False] * n
    best = 0
    for i in range(n):
        if seen[i]:
            continue
        st, c = [i], 0
        seen[i] = True
        while st:
            u = st.pop()
            c += 1
            for v in adj_r[u]:
                if not seen[v]:
                    seen[v] = True
                    st.append(v)
        best = max(best, c)
    return best / n


def graph_features(w: dict, D: np.ndarray) -> dict:
    P = w["ports"]
    n = len(P)
    adj_sets = knn_adjacency(D)
    adj = [[(j, float(D[i, j])) for j in adj_sets[i][0]] for i in range(n)]
    sp = [dijkstra(n, adj, i) for i in range(n)]
    pairs = [sp[i][j] for i in range(n) for j in range(n) if i != j and math.isfinite(sp[i][j])]
    lpr = np.log(np.array([p["price"] for p in P]) / np.array([p["base"] for p in P]))
    hist, _ = np.histogram(np.clip(lpr, PRICE_BINS[0], PRICE_BINS[-1]), bins=PRICE_BINS)
    pk = hist / hist.sum()
    p_ent = float(-(pk[pk > 0] * np.log2(pk[pk > 0])).sum())
    cp = np.array(w["chokepoints"], dtype=np.float64)
    return {
        "reachability": len(pairs) / (n * (n - 1)),
        "avg_route_length_nm": float(np.mean(pairs)),
        "route_diversity_nm": float(np.std(pairs)),
        "price_entropy_bits": p_ent,
        "price_dispersion": float(np.std(lpr)),
        "lcc_fraction": largest_cc_fraction(n, [s[1] for s in adj_sets]),
        "activity_raw": 0.5 * float(cp.mean()) / 2.0 + 0.5 * min(w["panama_ticks"], TICKS) / TICKS,
        # recorded for transparency, NOT in the proxy (zero seed-variance:
        # demands are static uniform -> H == log2(n); decoy share fixed 4/31)
        "demand_entropy_bits_const": None,
        "decoy_fraction_const": float(np.mean([p["decoy"] for p in P])),
    }


def binned_tensor(w: dict, degrees: np.ndarray, grid_edges: list[np.ndarray]) -> np.ndarray:
    """Raw-ish fixed-size world tensor: 8x8 spatial grid (train-frozen edges),
    per-port log price ratio, degree histogram, pencil-trust histogram,
    chokepoint statuses, event scalars. 121 dims."""
    P = w["ports"]
    n = len(P)
    lat = np.clip([p["lat"] for p in P], grid_edges[0][0], grid_edges[0][-1])
    lng = np.clip([p["lng"] for p in P], grid_edges[1][0], grid_edges[1][-1])
    g, _, _ = np.histogram2d(
        lat, lng, bins=8,
        range=[(grid_edges[0][0], grid_edges[0][-1]), (grid_edges[1][0], grid_edges[1][-1])],
    )
    grid = (g / n).ravel()
    lpr = np.log(np.array([p["price"] for p in P]) / np.array([p["base"] for p in P]))
    dhist, _ = np.histogram(np.minimum(degrees, 7), bins=range(9))
    trust = np.array([p["trust"] for p in P if p["pencil"]], dtype=np.float64)
    thist, _ = np.histogram(trust, bins=np.linspace(0.2, 0.8, 7))
    cp = np.array(w["chokepoints"], dtype=np.float64) / 2.0
    scal = np.array([
        float(np.mean([p["decoy"] for p in P])),
        float(np.mean([1.0 if p["proven"] else 0.0 for p in P if p["pencil"]])),
        min(w["panama_ticks"], TICKS) / TICKS,
        w["fact_landed"] / 20.0,
    ])
    return np.concatenate([
        grid.astype(np.float64), lpr, dhist / n, thist / max(len(trust), 1), cp, scal,
    ]).astype(np.float32)


def upper_tri(D: np.ndarray) -> np.ndarray:
    return D[np.triu_indices(D.shape[0], 1)].astype(np.float32)


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    def rank(a: np.ndarray) -> np.ndarray:
        a = np.asarray(a, np.float64)
        idx = np.argsort(a, kind="mergesort")
        r = np.empty(len(a))
        r[idx] = np.arange(len(a), dtype=np.float64)
        sa = a[idx]
        i = 0
        while i < len(sa):  # average ties (continuous data: rare, but correct)
            j = i
            while j + 1 < len(sa) and sa[j + 1] == sa[i]:
                j += 1
            if j > i:
                r[idx[i : j + 1]] = (i + j) / 2.0
            i = j + 1
        return r

    rx, ry = rank(x), rank(y)
    rx -= rx.mean()
    ry -= ry.mean()
    return float((rx * ry).sum() / math.sqrt((rx * rx).sum() * (ry * ry).sum()))


class FunScorer(nn.Module):
    """Tiny MLP, ~130k params at dim 583 / ~41k at dim 121 — both < 1M."""

    def __init__(self, in_dim: int):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(in_dim, 192), nn.ReLU(), nn.Linear(192, 96), nn.ReLU(), nn.Linear(96, 1))

    def forward(self, x):
        return self.net(x).squeeze(-1)


def generate_worlds(n: int) -> list[dict]:
    r = subprocess.run(["node", DRIVER, "1", str(n), str(TICKS)], capture_output=True, text=True, check=True)
    return [json.loads(line) for line in r.stdout.splitlines()]


def main() -> dict:
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    rng = np.random.default_rng(SEED)
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"[d6] generating {N_WORLDS} worlds from {TYCOON} (ticks={TICKS}) ...")
    worlds = generate_worlds(N_WORLDS)
    assert len(worlds) == N_WORLDS and worlds[0]["seed"] == 1

    print("[d6] featurizing ...")
    Dmats = [dist_matrix(w["ports"]) for w in worlds]
    feats = [graph_features(w, D) for w, D in zip(worlds, Dmats)]

    # deterministic split by seeded permutation of world indices
    perm = rng.permutation(N_WORLDS)
    tr, he = np.sort(perm[:N_TRAIN]), np.sort(perm[N_TRAIN : N_TRAIN + N_HELD])

    # proxy z-stats frozen on TRAIN only
    def zstats(key: str) -> tuple[float, float]:
        v = np.array([feats[i][key] for i in tr])
        return float(v.mean()), float(v.std() + 1e-8)

    z = {k: zstats(k) for k in PROXY_WEIGHTS if k != "activity"}
    za = zstats("activity_raw")

    def proxy(fi: dict) -> float:
        total = PROXY_WEIGHTS["activity"] * (fi["activity_raw"] - za[0]) / za[1]
        for k, wgt in PROXY_WEIGHTS.items():
            if k == "activity":
                continue
            m, s = z[k]
            total += wgt * (fi[k] - m) / s
        return float(total)

    y_all = np.array([proxy(fi) for fi in feats], dtype=np.float32)

    # raw tensors. grid edges frozen on TRAIN worlds (cross-world bin alignment)
    tr_lat = np.concatenate([[p["lat"] for p in worlds[i]["ports"]] for i in tr])
    tr_lng = np.concatenate([[p["lng"] for p in worlds[i]["ports"]] for i in tr])
    grid_edges = [np.linspace(tr_lat.min(), tr_lat.max(), 9), np.linspace(tr_lng.min(), tr_lng.max(), 9)]
    Xb, Xf = [], []
    for w, D in zip(worlds, Dmats):
        adj_sets = knn_adjacency(D)
        degrees = np.array([len(s[0]) for s in adj_sets], dtype=np.float64)
        bt = binned_tensor(w, degrees, grid_edges)
        Xb.append(bt)
        Xf.append(np.concatenate([upper_tri(D), bt]))
    Xb, Xf = np.stack(Xb), np.stack(Xf)

    def train_eval(Xin: np.ndarray, tag: str):
        mu, sd = Xin[tr].mean(0), Xin[tr].std(0) + 1e-6
        Xs = (Xin - mu) / sd
        model = FunScorer(Xs.shape[1]).to(dev)
        n_params = sum(p.numel() for p in model.parameters())
        assert n_params < 1_000_000, n_params
        Xt = torch.tensor(Xs[tr])
        yt = torch.tensor(y_all[tr])
        opt = torch.optim.Adam(model.parameters(), lr=1e-3)
        lossf = nn.MSELoss()
        model.train()
        for _ in range(400):
            opt.zero_grad()
            loss = lossf(model(Xt.to(dev)), yt.to(dev))
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            pred_all = model(torch.tensor(Xs).to(dev)).cpu().numpy()
        rho_tr = spearman(pred_all[tr], y_all[tr])
        rho_he = spearman(pred_all[he], y_all[he])
        print(f"[d6] {tag}: params={n_params} train_rho={rho_tr:.4f} heldout_rho={rho_he:.4f}")
        return pred_all, n_params, rho_tr, rho_he

    print(f"[d6] training model A (distance matrix + binned, dim={Xf.shape[1]}) on {dev} ...")
    predA, paramsA, rhoA_tr, rhoA_he = train_eval(Xf, "model-A")
    print(f"[d6] training model B (binned only, dim={Xb.shape[1]}) on {dev} ...")
    predB, paramsB, rhoB_tr, rhoB_he = train_eval(Xb, "model-B")

    # ship the better held-out model (selection on heldout, documented)
    ship = "B" if rhoB_he >= rhoA_he else "A"
    pred_ship = predB if ship == "B" else predA

    order = np.argsort(-pred_ship, kind="mergesort")
    bank = [
        {
            "rank": r + 1,
            "seed": int(worlds[i]["seed"]),
            "predicted_fun": float(pred_ship[i]),
            "proxy_true": float(y_all[i]),
            "lcc_fraction": float(feats[i]["lcc_fraction"]),
            "price_entropy_bits": float(feats[i]["price_entropy_bits"]),
            "route_diversity_nm": float(feats[i]["route_diversity_nm"]),
        }
        for r, i in enumerate(order[:TOP_K])
    ]
    topk_proxy = float(np.mean(y_all[order[:TOP_K]]))
    pop_proxy = float(np.mean(y_all))

    verdict = "KEEP" if rhoB_he >= 0.60 else ("KILL" if rhoB_he < 0.30 else "INCONCLUSIVE")

    with open("/home/eileen/projects/quilt-gpu-lab/results/d6_seed_bank.json", "w") as f:
        json.dump({
            "experiment": "D6 fun-scorer seed bank",
            "seed": SEED,
            "source": "cargo-line-tycoon GameEngine procgen (real import, node driver tools/d6_worldgen.js)",
            "ticks_per_world": TICKS,
            "score_range": [1, N_WORLDS],
            "shipped_model": ship,
            "heldout_spearman": {"A_full": float(rhoA_he), "B_binned": float(rhoB_he)},
            "top_k": bank,
        }, f, indent=2)
    print("[d6] wrote results/d6_seed_bank.json")

    out = {
        "experiment": "D6 fun-scorer + seed bank",
        "device": dev,
        "seed": SEED,
        "source": "cargo-line-tycoon GameEngine procgen (real import, no fallback)",
        "worlds": N_WORLDS,
        "ticks": TICKS,
        "n_train": N_TRAIN,
        "n_heldout": N_HELD,
        "params": {"A_full": paramsA, "B_binned": paramsB},
        "features_used": sorted(PROXY_WEIGHTS.keys()),
        "features_excluded_zero_variance": [
            "demand_entropy_bits (static uniform demand, H == log2(31) for every seed)",
            "decoy_fraction (fixed 4/31 by DECOY_SHARE)",
            "fact_landed count (index-based reveal schedule, seed-invariant)",
        ],
        "proxy_definition": {
            "form": "sum_i w_i * z_i(f), z-stats frozen on train split",
            "weights": PROXY_WEIGHTS,
            "activity_inner": "0.5*z(chokepoint_stress) + 0.5*z(panama_frac)",
            "rationale": "connected + price-varied + route-diverse + reachable + mildly dispersed + alive worlds are more interesting to ship in",
        },
        "graph": {"knn_k": KNN_K, "radius_nm": RADIUS_NM, "nodes": 31},
        "train_spearman": {"A_full": float(rhoA_tr), "B_binned": float(rhoB_tr)},
        "heldout_spearman": {"A_full": float(rhoA_he), "B_binned": float(rhoB_he)},
        "shipped_model": ship,
        "topk_mean_proxy": topk_proxy,
        "population_mean_proxy": pop_proxy,
        "seed_bank_file": "results/d6_seed_bank.json",
        "verdict_thresholds": {"KEEP": "rho_B >= 0.60", "KILL": "rho_B < 0.30", "else": "INCONCLUSIVE"},
        "verdict": verdict,
    }
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
