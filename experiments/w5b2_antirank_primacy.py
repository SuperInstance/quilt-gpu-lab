#!/usr/bin/env python3
"""W5b2 — antirank-primacy confirmation (frozen pre-reg: proposals/runs/W5b2-antirank-primacy.md).

Reuses the COMMITTED W5b machinery unchanged (import); only arms, seeds, output dir, and gates differ.
Primary: antirank vs random. KEEP iff mean rel bpb improvement >= 0.5% AND wins >= 4/5 seeds.
"""
import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

import w5b_lifetime_precision as W

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "results" / "w5b2_antirank_primacy"
ARMS2 = ["antirank", "random"]
SEEDS2 = [5291, 5292, 5293, 5294, 5295]
MARGIN = 0.005


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    t_warm, t_main, seeds = (W.T_WARM, W.T_MAIN, SEEDS2)
    if args.smoke:
        t_warm, t_main, seeds = 40, 80, [1]

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    OUT.mkdir(parents=True, exist_ok=True)

    corpus, files = W.build_corpus()
    chars = sorted(set(corpus))
    stoi = {c: i for i, c in enumerate(chars)}
    V = len(chars)
    ids = torch.tensor([stoi[c] for c in corpus], dtype=torch.long)
    cut = int(len(ids) * 0.9)
    train_ids, valid_ids = ids[:cut].to(dev), ids[cut:].to(dev)
    print(f"[cfg] w5b2 device={dev} warm={t_warm} main={t_main} seeds={seeds} "
          f"arms={ARMS2} corpus={len(corpus)}B vocab={V} files={len(files)}")

    results = {"config": {"arms": ARMS2, "seeds": seeds, "margin": MARGIN,
                          "t_warm": t_warm, "t_main": t_main, "machinery": "w5b_lifetime_precision (committed)"},
               "seeds": {}, "verdict": None}

    torch.manual_seed(0)
    for seed in seeds:
        t0 = time.time()
        torch.manual_seed(seed)
        model = W.TGRU(V, W.HID).to(dev)
        opt = torch.optim.Adam(model.parameters(), lr=W.LR)
        rng = np.random.default_rng(seed * 7 + 1)
        for step in range(t_warm):
            x, y = W.get_batch(train_ids, rng)
            loss = F.cross_entropy(model(x).view(-1, V), y.view(-1))
            opt.zero_grad(); loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), W.CLIP)
            opt.step()
            if (step + 1) % W.C_COMMIT == 0:
                model.commit_all()
        model.commit_all()
        warm = W.evaluate(model, valid_ids, V)
        warm_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        ch = {n: model.state(n, p).changes.clone() for n, p in model.tern_params()}
        print(f"[seed {seed}] warm bpb={warm:.5f} ({time.time() - t0:.0f}s)")

        row = {"warmup_bpb": round(warm, 6), "arms": {}}
        for arm in ARMS2:
            torch.manual_seed(seed)
            model.load_state_dict(warm_state)
            for n, p in model.tern_params():
                st = model.state(n, p)
                st.changes = ch[n].clone()
                st.HP = torch.zeros_like(p, dtype=torch.bool)
                st.H = torch.zeros_like(p)
                st.Q, st.s = W.ternarize(p)
            model.assign_hp(arm, np.random.default_rng(seed * 13 + 5))
            opt = torch.optim.Adam(model.parameters(), lr=W.LR)   # fresh optimizer, all arms
            rng = np.random.default_rng(seed * 7 + 1)             # identical data order
            ta = time.time()
            for step in range(t_main):
                x, y = W.get_batch(train_ids, rng)
                loss = F.cross_entropy(model(x).view(-1, V), y.view(-1))
                opt.zero_grad(); loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), W.CLIP)
                opt.step()
                if (step + 1) % W.C_COMMIT == 0:
                    model.commit_all()
            model.commit_all()
            final = W.evaluate(model, valid_ids, V)
            row["arms"][arm] = {"final_bpb": round(final, 6), "hp": model.n_hp(),
                                "secs": round(time.time() - ta, 1)}
            print(f"[seed {seed}] arm={arm:8s} final={final:.5f} ({time.time() - ta:.0f}s)",
                  flush=True)
        results["seeds"][str(seed)] = row

    pairs = []
    for s in seeds:
        a = results["seeds"][str(s)]["arms"]
        anti, rand = a["antirank"]["final_bpb"], a["random"]["final_bpb"]
        pairs.append({"seed": s, "antirank": anti, "random": rand,
                      "rel_improvement": (rand - anti) / rand})
    mean_rel = float(np.mean([p["rel_improvement"] for p in pairs]))
    wins = sum(1 for p in pairs if p["rel_improvement"] > 0)
    need = 4 if len(pairs) == 5 else math.ceil(0.8 * len(pairs))
    keep = mean_rel >= MARGIN and wins >= need
    results["verdict"] = {
        "rule": f"KEEP iff mean_rel>={MARGIN} and wins>={need}/{len(pairs)}",
        "mean_rel_improvement": round(mean_rel, 6), "wins": wins, "n_pairs": len(pairs),
        "pairs": pairs, "verdict": "KEEP" if keep else "KILL"}
    print(f"[VERDICT] {results['verdict']['verdict']} mean_rel={mean_rel:+.5f} wins={wins}/{len(pairs)}")

    (OUT / ("smoke_results.json" if args.smoke else "results.json")).write_text(
        json.dumps(results, indent=2))
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
