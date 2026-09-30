#!/usr/bin/env python3
"""TC4 — prefix locality + discrete budgets on the 96-d meaning code. Pre-reg: TC456-five-face-queue.md"""
import importlib.util, json, os, time
import numpy as np, torch, torch.nn as nn
DEV = "cuda" if torch.cuda.is_available() else "cpu"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results", "tc4")
spec = importlib.util.spec_from_file_location("tc1", os.path.join(ROOT, "experiments", "tc1_tile_codec.py"))
tc1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(tc1)

def kmeans(X, k, iters=25, seed=0):
    g = torch.Generator(device="cpu").manual_seed(seed); Xd = torch.tensor(X, device=DEV)
    k = min(k, len(X)); idx = torch.randperm(len(X), generator=g)[:k]
    C = Xd[idx].clone()
    for _ in range(iters):
        a = torch.cdist(Xd, C); lab = a.argmin(1)
        for j in range(k):
            sel = lab == j
            if sel.any(): C[j] = Xd[sel].mean(0)
    lab = torch.cdist(Xd, C).argmin(1)
    return lab.cpu().numpy(), C.cpu().numpy()

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True); t0 = time.time()
    from sentence_transformers import SentenceTransformer
    tiles = tc1.mine_tiles(); n = len(tiles)
    m = SentenceTransformer("thenlper/gte-small", device=DEV)
    E = lambda xs: m.encode(list(xs), batch_size=32, convert_to_numpy=True, show_progress_bar=False).astype(np.float32)
    full = E([t["question"] + " " + t["answer"] for t in tiles]); qonly = E([t["question"] for t in tiles])
    X = torch.tensor(full, device=DEV); Q = torch.tensor(qonly, device=DEV)
    torch.manual_seed(0)
    enc = nn.Sequential(nn.Linear(384, 96), nn.Tanh()).to(DEV)
    opt = torch.optim.Adam(enc.parameters(), lr=2e-3)
    for _ in range(1500):
        opt.zero_grad(); z = enc(X)
        zq = nn.functional.normalize(enc(Q), dim=1); zz = nn.functional.normalize(z, dim=1)
        loss = nn.functional.cross_entropy(zz @ zq.T / 0.07, torch.arange(n, device=DEV))
        loss.backward(); opt.step()
    with torch.no_grad(): Z = enc(X).cpu().numpy(); ZQ = enc(Q).cpu().numpy()
    zn = Z / (np.linalg.norm(Z, axis=1, keepdims=True) + 1e-9); zqn = ZQ / (np.linalg.norm(ZQ, axis=1, keepdims=True) + 1e-9)
    zn_f = full / (np.linalg.norm(full, axis=1, keepdims=True) + 1e-9); qn_f = qonly / (np.linalg.norm(qonly, axis=1, keepdims=True) + 1e-9)
    truth = np.argmax(qn_f @ zn_f.T, axis=1)  # oracle cosine top-1 in full space
    res = {"flat": {}, "prefix": {}}
    for k, bits in ((256, 8), (1024, 10), (4096, 12)):
        lab_t, _ = kmeans(Z, k); lab_q, _ = kmeans(ZQ, k)  # note: query cells from SAME codebook
        # rebuild codebook labels via nearest centroid for queries instead of separate kmeans:
        _, C = kmeans(Z, k)
        Cd = torch.tensor(C, device=DEV); ZQd = torch.tensor(ZQ, device=DEV); Zd = torch.tensor(Z, device=DEV)
        lab_t = torch.cdist(Zd, Cd).argmin(1).cpu().numpy(); lab_q = torch.cdist(ZQd, Cd).argmin(1).cpu().numpy()
        cont = float((lab_t[truth] == lab_q).mean())
        sizes = np.bincount(lab_t, minlength=len(C))
        res["flat"][f"{bits}b_{k}cells"] = {"containment": cont, "mean_candidates": float(sizes[sizes > 0].mean()), "n_cells_used": int((sizes > 0).sum())}
        print(f"  flat {bits}b/{k}: containment {cont:.4f}", flush=True)
    lab1, C1 = kmeans(Z, 32); Zd = torch.tensor(Z, device=DEV); Cd1 = torch.tensor(C1, device=DEV)
    lab1 = torch.cdist(Zd, Cd1).argmin(1).cpu().numpy()
    lab2 = lab1.copy(); lab3 = lab1.copy()
    for c in range(32):
        mem = np.where(lab1 == c)[0]
        if len(mem) < 32: lab2[mem] = 0; continue
        _, Cc = kmeans(Z[mem], 32)
        lab2[mem] = torch.cdist(torch.tensor(Z[mem], device=DEV), torch.tensor(Cc, device=DEV)).argmin(1).cpu().numpy() + c * 32
    for c in range(1024):
        mem = np.where(lab2 == c)[0]
        if len(mem) < 32: lab3[mem] = 0; continue
        _, Cc = kmeans(Z[mem], 32)
        lab3[mem] = torch.cdist(torch.tensor(Z[mem], device=DEV), torch.tensor(Cc, device=DEV)).argmin(1).cpu().numpy() + c * 32
    def q_cell(depth):
        if depth == 1: return torch.cdist(torch.tensor(ZQ, device=DEV), Cd1).argmin(1).cpu().numpy()
        # descend: nearest L1, then nearest within-cell centroid (approx via member means)
        q1 = torch.cdist(torch.tensor(ZQ, device=DEV), Cd1).argmin(1).cpu().numpy()
        out = np.zeros(len(ZQ), dtype=np.int64); return_q = np.zeros(len(ZQ), dtype=np.int64)
        for c in range(32):
            sel = q1 == c
            if not sel.any(): continue
            mem = np.where(lab1 == c)[0]
            if len(mem) < 32: out[sel] = lab2[mem][:1] if len(mem) else 0; continue
            sub = {}
            for j in mem: sub.setdefault(lab2[j], []).append(j)
            Csub = torch.tensor(np.array([Z[v].mean(0) for v in sub.values()]), device=DEV)
            pick = torch.cdist(torch.tensor(ZQ[sel], device=DEV), Csub).argmin(1).cpu().numpy()
            keys = list(sub.keys()); out[sel] = np.array([keys[p] for p in pick])
            if depth == 3:
                out3 = np.zeros(int(sel.sum()), dtype=np.int64)
                for si, key in enumerate(keys):
                    ssel = pick == si; memk = sub[key]
                    if len(memk) < 32: out3[ssel] = lab3[memk][:1]; continue
                    sub3 = {}
                    for j in memk: sub3.setdefault(lab3[j], []).append(j)
                    C3 = torch.tensor(np.array([Z[v].mean(0) for v in sub3.values()]), device=DEV)
                    p3 = torch.cdist(torch.tensor(ZQ[sel][ssel], device=DEV), C3).argmin(1).cpu().numpy()
                    k3 = list(sub3.keys()); out3[ssel] = np.array([k3[p] for p in p3])
                return_q[sel] = out3
        return out if depth == 2 else return_q
    for depth, bits in ((1, 5), (2, 10), (3, 15)):
        qc = q_cell(depth)
        cont = float((np.array([lab1, lab2, lab3][depth - 1])[truth] == qc).mean())
        sizes = np.bincount([lab1, lab2, lab3][depth - 1])
        res["prefix"][f"depth{depth}_{bits}b"] = {"containment": cont, "mean_candidates": float(sizes[sizes > 0].mean()), "n_cells_used": int((sizes > 0).sum())}
        print(f"  prefix d{depth} ({bits}b): containment {cont:.4f}", flush=True)
    # hybrid: prefix@2 candidates reranked by z-cosine; metric = self-match (standard eval)
    qc2 = q_cell(2); hits = 0; fb = 0
    for i in range(n):
        cand = np.where(lab2 == qc2[i])[0]
        if len(cand) == 0: fb += 1; cand = np.arange(n)
        if i in cand:
            sims = zqn[i] @ zn[cand].T
            if cand[np.argmax(sims)] == i: hits += 1
    res["hybrid_prefix2_zrerank"] = {"top1_selfmatch": hits / n, "fallbacks": fb}
    f = res["flat"]; g1 = f.get("12b_4096cells", {}).get("containment", 0) >= 0.50
    p = res["prefix"]; g2 = p["depth2_10b"]["containment"] >= 0.45 and p["depth3_15b"]["containment"] >= 0.70
    g3 = res["hybrid_prefix2_zrerank"]["top1_selfmatch"] >= 0.85
    summary = {"experiment": "TC4 prefix locality + discrete budgets", "n_tiles": n, "device": DEV, **res,
               "gates": {"G1_discrete_12b": bool(g1), "G2_prefix": bool(g2), "G3_hybrid": bool(g3)},
               "verdict": "GREPPABLE" if (g2 and g3) else ("DISCRETE_VIABLE" if (g1 and g3) else "MEASURED"),
               "wall_clock_s": round(time.time() - t0, 1)}
    json.dump(summary, open(os.path.join(OUT, "tc4_results.json"), "w"), indent=2)
    print(summary["gates"], summary["verdict"], flush=True)
