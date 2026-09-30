"""QG1 — exact statevector census of exp022's recorded populations (pre-reg: proposals/runs/QG1-exact-census.md)."""
import json, math, itertools, torch
DEV = "cuda"
def gate2(g):
    n = g[0]
    if n == "h":  return torch.tensor([[1,1],[1,-1]], dtype=torch.complex128)/math.sqrt(2)
    if n == "x":  return torch.tensor([[0,1],[1,0]], dtype=torch.complex128)
    if n == "rx":
        t = float(g[1])/2
        return torch.tensor([[complex(math.cos(t),0),complex(0,-math.sin(t))],[complex(0,-math.sin(t)),complex(math.cos(t),0)]], dtype=torch.complex128)
    if n == "rz":
        t = float(g[1])/2
        return torch.tensor([[complex(math.cos(t),-math.sin(t)),0],[0,complex(math.cos(t),math.sin(t))]], dtype=torch.complex128)
    raise ValueError(f"unknown 1q gate {n}")
def kron(a,b): return torch.kron(a,b)
def embed1(u,q):
    I = torch.eye(2, dtype=torch.complex128)
    return kron(kron(u,I),I) if q==0 else (kron(kron(I,u),I) if q==1 else kron(kron(I,I),u))
def perm(pairs):  # permutation matrix from index map old->new
    P = torch.zeros(8,8, dtype=torch.complex128)
    for s in range(8):
        b = [(s>>(2-q))&1 for q in range(3)]
        for c,t in pairs: b[t] ^= b[c]
        P[(b[0]<<2)|(b[1]<<1)|b[2], s] = 1
    return P
def genome_unitary(genome):
    M = torch.eye(8, dtype=torch.complex128)
    for g in genome:
        n = g[0]
        if n in ("h","x","rx","rz"): M = embed1(gate2(g), int(g[-1])) @ M
        elif n == "crx":
            th, c, t = float(g[1]), int(g[2]), int(g[3])
            U = embed1(gate2(["rx", g[1], t]), t)
            P0, P1 = torch.zeros(8,8, dtype=torch.complex128), torch.zeros(8,8, dtype=torch.complex128)
            for st in range(8):
                if (st>>(2-c))&1: P1[st,st]=1
                else: P0[st,st]=1
            M = (P0 + P1 @ U) @ M
        elif n == "cx": M = perm([(int(g[1]),int(g[2]))]) @ M
        elif n == "swap": M = perm([(int(g[1]),int(g[2])),(int(g[2]),int(g[1]))]) @ M
        else: raise ValueError(f"unknown gate {n}")
    return M
def lev(a,b):
    dp = list(range(len(b)+1))
    for i,ga in enumerate(a,1):
        nd=[i]
        for j,gb in enumerate(b,1): nd.append(min(dp[j]+1, nd[-1]+1, dp[j-1]+(ga!=gb)))
        dp=nd
    return dp[-1]
def key(g): return str([(t[0],)+tuple(round(float(x),6) if isinstance(x,(int,float)) else x for x in t[1:]) for t in g])
streams = {}
for k in ["k3","k4","k5","k6","k7"]:
    lines = [json.loads(l) for l in open(f"/home/eileen/projects/micromoth-quilt/receipts/exp022-desert-break/exp022.telemetry.{k}.jsonl")]
    streams[k] = [(gi, c) for gi, line in enumerate(lines) for c in line["census"]["cloud"]]
uniq = {}
for k in streams:
    for gi,c in streams[k]: uniq.setdefault(key(c["genome"]), (c["genome"],))[0]
genomes = [v[0] for v in uniq.values()]
keys = list(uniq.keys()); idx = {k:i for i,k in enumerate(keys)}
M = torch.stack([genome_unitary(g) for g in genomes]).to(DEV)
e0 = torch.zeros(len(genomes),8,1, dtype=torch.complex128, device=DEV); e0[:,0,0]=1
s = torch.bmm(M, e0).squeeze(-1)
p_exact = (s[:,0].abs()**2 + s[:,7].abs()**2).cpu()
p_bal = torch.minimum(s[:,0].abs()**2, s[:,7].abs()**2).cpu()
PB = {keys[i]: float(p_bal[i]) for i in range(len(keys))}
P = {keys[i]: float(p_exact[i]) for i in range(len(keys))}
res = {"anchor": {}, "gates": {}, "exploratory": {}}
dev_ok = tot = 0
for k in streams:
    for gi,c in streams[k]:
        e = PB[key(c["genome"])]; tot += 2
        dev_ok += sum(abs(e - c[x]) <= 0.044 for x in ("train_p","verify_p"))
res["anchor"] = {"within_2sigma": dev_ok, "total": tot, "frac": dev_ok/tot, "pass": dev_ok/tot >= 0.99}
hidden = sum(1 for k in streams for gi,c in streams[k] if c["verify_p"] < 0.45 and PB[key(c["genome"])] >= 0.45)
res["gates"]["G1_hidden_crossers"] = {"count": hidden, "pass": hidden == 0}
k4_cells = [c for gi,c in streams["k4"]]
k4_best = max(k4_cells, key=lambda c: c["verify_p"])
res["gates"]["G2_k4_near_miss"] = {"recorded_verify": k4_best["verify_p"], "exact_bal": PB[key(k4_best["genome"])], "pass": PB[key(k4_best["genome"])] < 0.45}
band = [PB[key(c["genome"])] for k in streams for gi,c in streams[k] if c.get("in_band")]
res["gates"]["G3_band_ceiling"] = {"n": len(band), "mean_exact_p": sum(band)/len(band), "pass": sum(band)/len(band) >= 0.48}
lon, anc = [], {}
for k in streams:
    bars = {}
    for gi,c in streams[k]:
        if c.get("in_band"): bars.setdefault(key(c["genome"]), []).append(gi)
    firsts = {kk: min(gi for gi,c in streams[k] if c.get("in_band") and key(c["genome"])==kk) for kk in bars}
    for kk, g0 in firsts.items():
        prior = [c for gi,c in streams[k] if gi < g0]
        if prior:
            bg = uniq[kk][0]
            tok = lambda g: tuple((t[0],)+tuple(round(float(x),6) if isinstance(x,(int,float)) else x for x in t[1:]) for t in g)
            best = min(((lev(list(tok(bg)), list(tok(c["genome"]))), c) for c in prior), key=lambda t:t[0])
            anc.setdefault(k, []).append({"break_first_gen": g0, "min_edit_distance": best[0],
                "parent_genome": best[1]["genome"], "parent_train_p": best[1]["train_p"],
                "parent_in_band": best[1].get("in_band"), "parent_is_champion": best[1].get("is_champion"),
                "break_exact_bal": PB[kk], "parent_exact_bal": PB[key(best[1]["genome"])], "break_union_p": P[kk]})
    for gi in range(12):
        ps = sorted((PB[key(c["genome"])] for gi2,c in streams[k] if gi2==gi), reverse=True)
        if len(ps) >= 2: lon.append(ps[0]-ps[1])
res["exploratory"] = {"loneliness_mean_gap": sum(lon)/len(lon), "loneliness_max": max(lon),
    "train_vs_verify_mad": sum(abs(PB[key(c["genome"])]-c["train_p"])+abs(PB[key(c["genome"])]-c["verify_p"]) for k in streams for gi,c in streams[k])/(2*tot//2), "band_union_p_mean": sum(band)/len(band),
    "ancestry": anc}
json.dump(res, open("results/qg1_exact_census/qg1_results.json","w"), indent=1, default=str)
print(json.dumps(res["anchor"])); print(json.dumps(res["gates"], indent=1))
print("loneliness mean gap:", res["exploratory"]["loneliness_mean_gap"], "| max:", res["exploratory"]["loneliness_max"])
print(json.dumps(res["exploratory"]["ancestry"], indent=1)[:1600])
