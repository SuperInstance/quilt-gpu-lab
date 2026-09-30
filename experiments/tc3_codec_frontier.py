#!/usr/bin/env python3
"""TC3 — compression frontier of the retrieval-trained tile codec. Pre-reg: proposals/runs/TC3-codec-frontier.md"""
import importlib.util, json, os, time
import numpy as np, torch, torch.nn as nn

DEV = "cuda" if torch.cuda.is_available() else "cpu"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results", "tc3")
spec = importlib.util.spec_from_file_location("tc1", os.path.join(ROOT, "experiments", "tc1_tile_codec.py"))
tc1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(tc1)

def topk(index, query, k=5):
    i = index / (np.linalg.norm(index, axis=1, keepdims=True) + 1e-9)
    q = query / (np.linalg.norm(query, axis=1, keepdims=True) + 1e-9)
    rank = np.argsort(-(q @ i.T), axis=1); n = len(index)
    return float((rank[:, 0] == np.arange(n)).mean()), float(np.mean([np.arange(n)[i] in rank[i, :k] for i in range(n)]))

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True); t0 = time.time()
    from sentence_transformers import SentenceTransformer
    tiles = tc1.mine_tiles()
    m = SentenceTransformer("thenlper/gte-small", device=DEV)
    E = lambda xs: m.encode(xs, batch_size=32, convert_to_numpy=True, show_progress_bar=False).astype(np.float32)
    full = E([t["question"] + " " + t["answer"] for t in tiles]); qonly = E([t["question"] for t in tiles])
    det = [tc1.decode_binary(tc1.encode_binary(t)) for t in tiles]
    a_txt = E([(d["question"] + " " + d["answer"]) if d else "" for d in det])
    sc = np.abs(full).max(1, keepdims=True) / 127.0
    b_hat = np.clip(np.round(full / (sc + 1e-12)), -127, 127) * sc
    X = torch.tensor(full, device=DEV); Q = torch.tensor(qonly, device=DEV)
    print(f"TC3 — {len(tiles)} tiles, frontier sweep, device={DEV}", flush=True)

    def train(dim, kind, T=0.07, epochs=1500):
        torch.manual_seed(0)
        enc = nn.Sequential(nn.Linear(384, dim), nn.Tanh()).to(DEV)
        dec = nn.Linear(dim, 384).to(DEV)
        ps = list(enc.parameters()) + (list(dec.parameters()) if kind == "hybrid" else [])
        opt = torch.optim.Adam(ps, lr=2e-3)
        for _ in range(epochs):
            opt.zero_grad(); z = enc(X); loss = torch.zeros((), device=DEV)
            if kind == "hybrid": loss = loss + nn.functional.mse_loss(dec(z), X)
            zq = nn.functional.normalize(enc(Q), dim=1); zz = nn.functional.normalize(z, dim=1)
            loss = loss + nn.functional.cross_entropy(zz @ zq.T / T, torch.arange(len(z), device=DEV))
            loss.backward(); opt.step()
        with torch.no_grad(): return enc(X).cpu().numpy(), enc(Q).cpu().numpy()

    res = {}
    for nm, v in (("A_deterministic_384B", a_txt), ("B_int8_384B", b_hat)):
        t1, t5 = topk(v, qonly); res[nm] = {"top1": t1, "top5": t5, "bytes": 384}
    for dim in (12, 24, 48, 96):
        z, zq = train(dim, "retr"); t1, t5 = topk(z, zq)
        res[f"E_retrieval_{dim*4}B"] = {"top1": t1, "top5": t5, "bytes": dim * 4}
        print(f"  retrieval {dim*4:4d}B: top1 {t1:.4f} top5 {t5:.4f}", flush=True)
    z, zq = train(96, "hybrid"); t1, t5 = topk(z, zq)
    res["F_hybrid_384B"] = {"top1": t1, "top5": t5, "bytes": 384}

    text = res["A_deterministic_384B"]["top1"]
    curve = [(int(k.split('_')[-1][:-1]), v["top1"]) for k, v in res.items() if k.startswith("E_retrieval")]
    curve.sort()
    monotone = all(curve[i + 1][1] >= curve[i][1] - 0.01 for i in range(len(curve) - 1))
    small = [p for p in curve if p[0] <= 192]
    g2 = any(v >= text - 0.01 for _, v in small)
    g3 = dict(curve)[48] < text
    summary = {"experiment": "TC3 — codec compression frontier", "n_tiles": len(tiles), "device": DEV,
               "arms": res, "curve_bytes_top1": curve, "text_reference_top1": text,
               "gates": {"G1_monotone": bool(monotone), "G2_crosses_text_at_or_below_192B": bool(g2), "G3_knee_above_48B": bool(g3)},
               "verdict": "FRONTIER_CROSSES" if (g2 and g3) else ("NO_CROSS" if not g2 else "FLAT"),
               "wall_clock_s": round(time.time() - t0, 1)}
    json.dump(summary, open(os.path.join(OUT, "tc3_results.json"), "w"), indent=2)
    print(json.dumps(summary, indent=2))
