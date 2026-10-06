"""CC-1b — torch-seed-pinned re-certification of CC-1.
Prereg: proposals/runs/CC-1b-prereg-torch-seed-recert.md (committed BEFORE firing).
Identical to experiments/cc1_comfortable_collapse.py except:
  - torch.manual_seed(seed*10 + draw) at lane entry (fixes the unseeded torch.rand selection key)
  - 4 numpy seeds x 3 torch draws = 12 lanes; gates judged on the ensemble (QG7 convention).
"""
import sys, json, time, pathlib
import numpy as np
import torch

sys.path.insert(0, "tools")
sys.path.insert(0, "experiments")
from cc1_comfortable_collapse import (ANG, PAIRS, TEMPLATES, PAD, DEV, BAR, SEEDS, S, GENS,
                                      GSTAR, make_lib, exact_balance, run_lane_trajectory,
                                      rank_col, auc)  # noqa: E402  (kernel imported VERBATIM)

DRAWS = [0, 1, 2]


def run_lane_pinned(S_, W, gens, seed, draw, bar=BAR):
    torch.manual_seed(seed * 10 + draw)
    return run_lane_trajectory(S_, W, gens, seed, bar=bar)


if __name__ == "__main__":
    t0 = time.time()
    out = {"config": {"S": S, "gens": GENS, "seeds": SEEDS, "draws": DRAWS, "bar": BAR,
                      "gstar": GSTAR,
                      "prereg": "proposals/runs/CC-1b-prereg-torch-seed-recert.md",
                      "torch_pin": "manual_seed(seed*10+draw) at lane entry"}}
    LIB = make_lib()
    rng7 = np.random.default_rng(7)
    gsets = [[TEMPLATES[rng7.integers(0, PAD)][0] for _ in range(rng7.integers(1, 7))] for _ in range(50)]
    ref2 = [d["balance"] for d in __import__("qcell_sim", fromlist=["evaluate"]).evaluate(gsets, device="cpu")]
    ours = exact_balance(torch.tensor([[TEMPLATES.index([g]) for g in gs] + [PAD]*(6-len(gs)) for gs in gsets]), LIB, 6)
    aerr = float(np.max(np.abs(np.array(ref2) - ours.numpy())))
    out["anchor_vec_err"] = aerr
    assert aerr < 1e-9, f"ANCHOR FAIL {aerr}"

    per_seed, pooled = {}, {}
    for seed in SEEDS:
        for draw in DRAWS:
            r = run_lane_pinned(S, 6, GENS, seed, draw, bar=BAR)
            crossed24, cgen, traj, ltraj = r["crossed"], r["crossed_gen"], r["traj"], r["ltraj"]
            c24 = float(crossed24.mean()); c12 = float((((cgen >= 0) & (cgen <= GSTAR-1))).mean())
            hopeless = ~crossed24
            fenced = crossed24 & (cgen >= GSTAR)
            early = crossed24 & (cgen < GSTAR)
            v12, l12 = traj[GSTAR], ltraj[GSTAR]
            rk12 = rank_col(v12)
            prev = traj[max(0, GSTAR-8):GSTAR]
            rate = (v12 - prev[0]) / max(1, GSTAR-1) if prev.shape[0] > 1 else np.zeros_like(v12)
            feats = {"v": v12, "rank": rk12, "len": l12, "rate": rate}
            d = per_seed.setdefault(str(seed), {"c24": [], "c12": [], "fenced_n": 0, "hopeless_n": 0,
                                                "early_v_auc": []})
            d["c24"].append(c24); d["c12"].append(c12)
            d["fenced_n"] += int(fenced.sum()); d["hopeless_n"] += int(hopeless.sum())
            d["early_v_auc"].append(auc(v12[early], v12[hopeless]))
            for name, fv in feats.items():
                pooled.setdefault(name, {"pos": [], "neg": []})
                pooled[name]["pos"] += fv[fenced].tolist(); pooled[name]["neg"] += fv[hopeless].tolist()
    pooled_auc = {k: auc(np.array(x["pos"]), np.array(x["neg"])) for k, x in pooled.items()}
    out["per_seed"] = per_seed
    out["pooled_auc_gstar12"] = pooled_auc

    c24_all = [x for d in per_seed.values() for x in d["c24"]]
    c12_all = [x for d in per_seed.values() for x in d["c12"]]
    mean = lambda xs: sum(xs)/len(xs)
    spread = max(mean(d["c24"]) for d in per_seed.values()) - min(mean(d["c24"]) for d in per_seed.values())
    out["G1"] = {"c24_mean": mean(c24_all), "c12_mean": mean(c12_all),
                 "per_seed_c24_mean_spread": spread,
                 "pass": (abs(mean(c24_all)-0.755) <= 0.05 and abs(mean(c12_all)-0.578) <= 0.05
                          and spread <= 0.10)}
    out["G2"] = {"min_fenced_pooled": sum(d["fenced_n"] for d in per_seed.values()),
                 "pass": sum(d["fenced_n"] for d in per_seed.values()) >= 40}
    out["G4"] = {"early_v_auc_min": min(x for d in per_seed.values() for x in d["early_v_auc"] if x is not None),
                 "pass": min(x for d in per_seed.values() for x in d["early_v_auc"] if x is not None) > 0.9}
    pa = pooled_auc
    blind = all(0.45 <= (pa[k] or 0.0) <= 0.60 for k in ["v", "rank", "len", "rate"])
    newfeat = any((pa[k] or 0.0) >= 0.75 for k in ["v", "rank", "len", "rate"])
    out["G3"] = {"pooled": pa, "verdict": ("COMFORTABLE_COLLAPSE_CONFIRMED" if blind else
                 ("NEW_FEATURE" if newfeat else "INCONCLUSIVE"))}

    odir = pathlib.Path("results/cc1b_torch_seed_recert"); odir.mkdir(parents=True, exist_ok=True)
    (odir / "results.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({"G1": out["G1"], "G2": out["G2"]["pass"], "G3": out["G3"],
                      "G4": out["G4"], "secs": round(time.time()-t0, 1)}, indent=1))
