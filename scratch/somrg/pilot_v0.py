#!/usr/bin/env python3
"""SOMRG-PILOT-V0 — does a SOM's site-partition approximate geometric 2x2 RG blocking?

Pre-registration: proposals/runs/SOMRG-PILOT-V0.md (FROZEN before this run; seed 42).
Gate: PAIR-AGREE delta (SOM - shuffled control) >= +0.20 @ T=0.5 AND >= +0.10 @ T=0.8 -> PASS
Kill: delta <= 0 at every T in {0.5, 1.0} -> v0 dead.
rc: 0 PASS / 1 KILL / 2 fail-loud. numpy only, CPU, single seed.
"""
import json, sys, time
import numpy as np

L, J = 24, 1.0
TRI = np.int8([-1, 0, 1])
TEMPS = [0.5, 0.8, 1.0, 1.2, 1.5, 2.0]
N_EQ, N_SAMP, GAP = 3000, 200, 50
SOM_SIDE, EPOCHS = 12, 200
SEED = 42

def sweep(s, beta, rng, masks):
    for mask in masks:
        S = (np.roll(s, 1, 0) + np.roll(s, -1, 0) + np.roll(s, 1, 1) + np.roll(s, -1, 1)).astype(np.float32)
        prop = TRI[rng.integers(0, 3, size=s.shape)]
        dE = -((prop.astype(np.float32) - s.astype(np.float32)) * S) * J
        acc = (dE <= 0) | (rng.random(s.shape) < np.exp(-dE * beta))
        s[mask & acc] = prop[mask & acc]
    return s

def geo_block(s):
    b = (s[0::2, 0::2].astype(np.int32) + s[1::2, 0::2] + s[0::2, 1::2] + s[1::2, 1::2])
    return np.sign(b).astype(np.int8)  # (12,12)

def geo_partition():
    """Site-pair co-blocking membership for geometric blocking: pairs of sites in same 2x2 block."""
    lab = (np.arange(L) // 2)[:, None] * (L // 2) + (np.arange(L) // 2)[None, :]
    lab = lab.reshape(-1)
    return lab

def pair_agree(lab_a, lab_b):
    same_a = lab_a[:, None] == lab_a[None, :]
    same_b = lab_b[:, None] == lab_b[None, :]
    return float((same_a == same_b).mean())

def som_train(feats, seed, epochs=EPOCHS):
    rng = np.random.default_rng(seed)
    N = SOM_SIDE * SOM_SIDE
    W = rng.normal(size=(N, feats.shape[1])).astype(np.float32)
    coords = np.stack(np.meshgrid(np.arange(SOM_SIDE), np.arange(SOM_SIDE), indexing="ij"), -1).reshape(-1, 2).astype(np.float32)
    for ep in range(epochs):
        lr = 0.5 * np.exp(-ep / 80.0)
        sigma = max(6.0 * np.exp(-ep / 60.0), 0.6)
        for idx in rng.permutation(len(feats)):
            x = feats[idx]
            b = int(((W - x) ** 2).sum(1).argmin())
            gd = ((coords - coords[b]) ** 2).sum(1)
            W += (lr * np.exp(-gd / (2 * sigma * sigma)))[:, None] * (x - W)
    d2 = ((feats[:, None, :] - W[None, :, :]) ** 2).sum(-1)
    return d2.argmin(1)  # site -> block label

def shuffle_partition(sizes, seed):
    rng = np.random.default_rng(seed)
    perm = rng.permutation(L * L)
    lab = np.empty(L * L, dtype=np.int64)
    start = 0
    for i, sz in enumerate(sizes):
        lab[perm[start:start + sz]] = i
        start += sz
    return lab

def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    masks = [((np.add.outer(np.arange(L), np.arange(L)) % 2) == m) for m in (0, 1)]
    geo_lab = geo_partition()
    rows, verdicts = [], []
    for T in TEMPS:
        s = rng.choice(TRI, size=(L, L)).astype(np.int8)
        beta = 1.0 / T
        for _ in range(N_EQ):
            sweep(s, beta, rng, masks)
        cfgs = np.empty((N_SAMP, L * L), dtype=np.int8)
        for k in range(N_SAMP):
            for _ in range(GAP):
                sweep(s, beta, rng, masks)
            cfgs[k] = s.reshape(-1)
        f = np.stack([cfgs.mean(0), cfgs.std(0), (cfgs == 0).mean(0)], 1).astype(np.float32)
        f = (f - f.mean(0)) / (f.std(0) + 1e-9)
        som_lab = som_train(f, seed=SEED + int(T * 10))
        sizes = np.bincount(som_lab, minlength=SOM_SIDE * SOM_SIDE)
        sizes = sizes[sizes > 0]
        a_som = pair_agree(som_lab, geo_lab)
        a_shuf = float(np.mean([pair_agree(shuffle_partition(sizes, 1000 + i + int(T * 10)), geo_lab)
                                for i in range(5)]))
        m_mean = float(np.abs(cfgs.mean(1)).mean())
        nontrivial = int((sizes > 1).sum())
        delta = a_som - a_shuf
        rows.append(dict(T=T, pair_som=round(a_som, 4), pair_shuf=round(a_shuf, 4),
                         delta=round(delta, 4), m_abs=round(m_mean, 4),
                         som_blocks_nontrivial=int(nontrivial)))
        print(f"T={T:3.1f}  SOM={a_som:.3f}  shuf={a_shuf:.3f}  delta={delta:+.3f}  "
              f"|m|={m_mean:.3f}  nontrivial_blocks={nontrivial}")
    by_T = {r["T"]: r["delta"] for r in rows}
    d05, d08, d10 = by_T[0.5], by_T[0.8], by_T[1.0]
    if d05 >= 0.20 and d08 >= 0.10:
        verdict = "PASS"
    elif d05 <= 0 and d10 <= 0:
        verdict = "KILL"
    else:
        verdict = "GREY"
    out = dict(pilot="SOMRG-PILOT-V0", prereg="proposals/runs/SOMRG-PILOT-V0.md",
               seed=SEED, rows=rows, verdict=verdict, wall_s=round(time.time() - t0, 1))
    print(f"\nVERDICT: {verdict}  (gates: d05={d05:+.3f} need>=+0.20 | d08={d08:+.3f} need>=+0.10 | kill if d05<=0 and d10<=0)")
    with open("results/somrg_pilot_v0.json", "w") as f:
        json.dump(out, f, indent=1)
    sys.exit({"PASS": 0, "KILL": 1}.get(verdict, 0))

if __name__ == "__main__":
    main()
