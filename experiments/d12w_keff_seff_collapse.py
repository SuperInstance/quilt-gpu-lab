#!/usr/bin/env python3
"""D12w: does k_eff collapse onto a single function of s_eff = p*(1-2eps)?

D12v certified k_eff(p) monotone but noted k_eff drifts with eps within each p,
so 'k_eff(p)' may really be k_eff(s_eff). Test using saved floors from
D12u2 (p=0.3), D12u4 (p=0.4), D12v (p=0.45). Model is linear in k, so
k_eff_implied = k_ref_used * (harness_floor / model_floor_at_k_ref).

Gates (pre-registered):
  G1: Spearman-monotone DECREASING k_eff vs s_eff with <= 2 inversions
      across the pooled point set (grid-pinned cells excluded).
  G2: fit log k_eff = a + b*log s_eff; b <= 0 with leave-one-p-out
      prediction of the omitted p's mean k_eff within 25%.

Exclude: p=0.7 (all floors grid-pinned at T=10-15 -> unresolvable),
and cells whose harness floor sits at the T-grid minimum (10).
"""
import json, math, itertools

BASE = "results/"
# (file, p, k_ref, key naming)
SOURCES = [
    ("d12u2_n64_heldout.json", 0.3, 0.657),
    ("d12u4_p04_heldout.json", 0.4, 0.657),
    ("d12v_keff_p045.json", 0.45, 0.836475),
]
T_GRID_MIN = 10

points = []
for fname, p, k_ref in SOURCES:
    d = json.load(open(BASE + fname))
    for c in d["cells"]:
        w = c.get("w", c.get("W"))
        eps = c["eps"]
        hf = c["harness_floor"]
        mf = c.get("model_pred", c.get("model_floor"))
        if hf <= T_GRID_MIN:  # grid-pinned, unresolvable
            continue
        ratio = hf / mf
        k_eff = k_ref * ratio
        s_eff = p * (1 - 2 * eps)
        points.append(dict(p=p, w=w, eps=eps, s_eff=s_eff, hf=hf, mf=mf, k_eff=k_eff))

print(f"{len(points)} resolvable points (grid-pinned excluded)")
for pt in points:
    print(f"p={pt['p']:.2f} W={pt['w']:2d} eps={pt['eps']:.2f} s={pt['s_eff']:.3f} "
          f"hf={pt['hf']:4.0f} mf={pt['mf']:6.1f} k_eff={pt['k_eff']:.3f}")

# G1: monotone decreasing k_eff vs s_eff (count inversions over s-sorted pairs)
pts = sorted(points, key=lambda r: -r["s_eff"])  # descending s
inv = 0
for i in range(len(pts)):
    for j in range(i + 1, len(pts)):
        if pts[j]["s_eff"] < pts[i]["s_eff"] and pts[j]["k_eff"] > pts[i]["k_eff"] * 1.02:
            inv += 1
print(f"\nG1 inversions (k_eff should FALL as s_eff RISES): {inv}")

# G2: log-log fit + leave-one-p-out
import statistics
def fit(pts_subset):
    xs = [math.log(r["s_eff"]) for r in pts_subset]
    ys = [math.log(r["k_eff"]) for r in pts_subset]
    n = len(xs); mx = sum(xs)/n; my = sum(ys)/n
    b = sum((x-mx)*(y-my) for x, y in zip(xs, ys)) / sum((x-mx)**2 for x in xs)
    a = my - b*mx
    return a, b

a, b = fit(points)
print(f"G2 pooled fit: log k_eff = {a:.3f} + ({b:.3f}) log s_eff  (b should be <= 0)")

errs = []
for p_hold in sorted({r["p"] for r in points}):
    tr = [r for r in points if r["p"] != p_hold]
    te = [r for r in points if r["p"] == p_hold]
    ah, bh = fit(tr)
    for r in te:
        pred = math.exp(ah + bh*math.log(r["s_eff"]))
        err = abs(pred - r["k_eff"]) / r["k_eff"]
        errs.append(err)
        print(f"  L1O p={p_hold}: W={r['w']} eps={r['eps']} k_eff={r['k_eff']:.3f} pred={pred:.3f} err={err:.1%}")
max_err = max(errs)
print(f"G2 max L1O error: {max_err:.1%} (bar 25%)")

g1 = inv <= 2
g2 = b <= 0 and max_err <= 0.25
verdict = "KEEP_k_eff_is_k_eff_seff" if (g1 and g2) else "KILL_k_eff_is_p_local"
print(f"\nG1={g1} G2={g2} -> {verdict}")

out = dict(seed=2718, n_points=len(points),
           points=[{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()} for r in points],
           inversions=inv, fit_b=round(b, 3), max_l1o_err=round(max_err, 4),
           G1=bool(g1), G2=bool(g2), verdict=verdict)
json.dump(out, open(BASE + "d12w_keff_seff_collapse.json", "w"), indent=1)
print("saved results/d12w_keff_seff_collapse.json")
