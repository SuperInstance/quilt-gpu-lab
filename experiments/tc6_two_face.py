#!/usr/bin/env python3
"""TC6 — two-face split sweep at fixed 384B. Pre-reg: proposals/runs/TC456-five-face-queue.md"""
import importlib.util, json, os, time
import numpy as np, torch, torch.nn as nn
DEV = "cuda" if torch.cuda.is_available() else "cpu"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results", "tc6")
spec = importlib.util.spec_from_file_location("tc1", os.path.join(ROOT, "experiments", "tc1_tile_codec.py"))
tc1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(tc1)

def topk(index, query, k=5):
    i = index / (np.linalg.norm(index, axis=1, keepdims=True) + 1e-9)
    q = query / (np.linalg.norm(query, axis=1, keepdims=True) + 1e-9)
    rank = np.argsort(-(q @ i.T), axis=1); n = len(index)
    return float((rank[:, 0] == np.arange(n)).mean()), float(np.mean([np.arange(n)[j] in rank[j, :k] for j in range(n)]))

def menu_trunc(text, nbytes):
    b = text.encode("utf-8")[:nbytes]
    cut = b.rfind(b" ")
    if cut > nbytes * 0.6: b = b[:cut]
    while True:
        try: return b.decode("utf-8")
        except UnicodeDecodeError: b = b[:-1]

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True); t0 = time.time()
    from sentence_transformers import SentenceTransformer
    tiles = tc1.mine_tiles()
    m = SentenceTransformer("thenlper/gte-small", device=DEV)
    E = lambda xs: m.encode(list(xs), batch_size=32, convert_to_numpy=True, show_progress_bar=False).astype(np.float32)
    full = E([t["question"] + " " + t["answer"] for t in tiles]); qonly = E([t["question"] for t in tiles])
    X = torch.tensor(full, device=DEV); Q = torch.tensor(qonly, device=DEV)
    def train(dim, epochs=1500, T=0.07):
        torch.manual_seed(0)
        enc = nn.Sequential(nn.Linear(384, dim), nn.Tanh()).to(DEV)
        opt = torch.optim.Adam(enc.parameters(), lr=2e-3)
        for _ in range(epochs):
            opt.zero_grad(); z = enc(X)
            zq = nn.functional.normalize(enc(Q), dim=1); zz = nn.functional.normalize(z, dim=1)
            loss = nn.functional.cross_entropy(zz @ zq.T / T, torch.arange(len(z), device=DEV))
            loss.backward(); opt.step()
        with torch.no_grad(): return enc(X).cpu().numpy(), enc(Q).cpu().numpy()
    res = {}
    for menu_b, dim in ((384, 0), (288, 24), (192, 48), (96, 72), (0, 96)):
        row = {"menu_bytes": menu_b, "meaning_bytes": (384 - menu_b), "menu_top1": None, "meaning_top1": None}
        if menu_b:
            menus = E([menu_trunc(t["question"] + " " + t["answer"], menu_b) for t in tiles])
            row["menu_top1"], row["menu_top5"] = topk(menus, qonly)
        if dim:
            z, zq = train(dim); row["meaning_top1"], row["meaning_top5"] = topk(z, zq)
        if row["menu_top1"] is not None and row["meaning_top1"] is not None: row["sum"] = row["menu_top1"] + row["meaning_top1"]
        res[f"split_{menu_b}_{384-menu_b}"] = row
        print(f"  menu {menu_b:3d}B / meaning {384-menu_b:3d}B: menu {row['menu_top1']} meaning {row['meaning_top1']} sum {row.get('sum')}", flush=True)
    s = res["split_288_96"]
    g1 = s["meaning_top1"] >= 0.85; g2 = s["menu_top1"] >= 0.68; g3 = s.get("sum", 0) >= 1.50
    summary = {"experiment": "TC6 two-face split sweep", "n_tiles": len(tiles), "device": DEV, "splits": res,
               "gates": {"G1_meaning_holds": bool(g1), "G2_menu_survives": bool(g2), "G3_two_face_wins": bool(g3)},
               "verdict": "TWO_FACE" if (g1 and g2 and g3) else "MEASURED", "wall_clock_s": round(time.time() - t0, 1)}
    json.dump(summary, open(os.path.join(OUT, "tc6_results.json"), "w"), indent=2)
    print(json.dumps(summary["gates"], indent=2), summary["verdict"], flush=True)
