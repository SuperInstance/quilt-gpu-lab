#!/usr/bin/env python3
"""TC2 — retrieval-objective 384-byte tile codec. Pre-reg: proposals/runs/TC2-tile-codec-retrieval.md"""
import importlib.util, json, os, time
import numpy as np, torch, torch.nn as nn

DEV = "cuda" if torch.cuda.is_available() else "cpu"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results", "tc2")
spec = importlib.util.spec_from_file_location("tc1", os.path.join(ROOT, "experiments", "tc1_tile_codec.py"))
tc1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(tc1)

def topk(index, query, k=5):
    i = index / (np.linalg.norm(index, axis=1, keepdims=True) + 1e-9)
    q = query / (np.linalg.norm(query, axis=1, keepdims=True) + 1e-9)
    rank = np.argsort(-(q @ i.T), axis=1); n = len(index)
    return float((rank[:, 0] == np.arange(n)).mean()), float(np.mean([np.arange(n)[i] in rank[i, :k] for i in range(n)]))

def cos(a, b):
    a = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-9); b = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-9)
    return float((a * b).sum(1).mean())

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True); t0 = time.time()
    from sentence_transformers import SentenceTransformer
    tiles = tc1.mine_tiles()
    m = SentenceTransformer("thenlper/gte-small", device=DEV)
    E = lambda xs: m.encode(xs, batch_size=32, convert_to_numpy=True, show_progress_bar=False).astype(np.float32)
    full = E([t["question"] + " " + t["answer"] for t in tiles]); qonly = E([t["question"] for t in tiles])
    print(f"TC2 — {len(tiles)} tiles, same corpus as TC1, device={DEV}", flush=True)

    # arm A: deterministic text fields (same semantics as TC1)
    det = [tc1.decode_binary(tc1.encode_binary(t)) for t in tiles]
    a_txt = E([(d["question"] + " " + d["answer"]) if d else "" for d in det])
    # arm B: int8
    sc = np.abs(full).max(1, keepdims=True) / 127.0
    b_hat = np.clip(np.round(full / (sc + 1e-12)), -127, 127) * sc

    X = torch.tensor(full, device=DEV); Q = torch.tensor(qonly, device=DEV)
    torch.manual_seed(0); T = 0.07

    def train(kind):
        torch.manual_seed(0)
        enc = nn.Sequential(nn.Linear(384, 96), nn.Tanh()).to(DEV)
        dec = nn.Linear(96, 384).to(DEV)
        ps = list(enc.parameters()) + (list(dec.parameters()) if kind in ("mse", "hybrid") else [])
        opt = torch.optim.Adam(ps, lr=2e-3)
        for ep in range(1500):
            opt.zero_grad(); z = enc(X); loss = torch.zeros((), device=DEV)
            if kind in ("mse", "hybrid"): loss = loss + nn.functional.mse_loss(dec(z), X)
            if kind in ("retr", "hybrid"):
                zq = enc(Q); zq = nn.functional.normalize(zq, dim=1); zz = nn.functional.normalize(z, dim=1)
                loss = loss + nn.functional.cross_entropy(zz @ zq.T / T, torch.arange(len(z), device=DEV))
            loss.backward(); opt.step()
        with torch.no_grad():
            z = enc(X).cpu().numpy()
            rec = dec(torch.tensor(z, device=DEV)).cpu().numpy() if kind in ("mse", "hybrid") else None
            zq = enc(Q).cpu().numpy()
        return z, zq, rec, float(loss.item())

    res = {}
    for name, v in (("A_deterministic", a_txt), ("B_int8_full", b_hat)):
        t1, t5 = topk(v, qonly); res[name] = {"top1": t1, "top5": t5, "cos": cos(full, v), "bytes": 384}
    for name, kind in (("C_mse_96d", "mse"), ("E_retrieval_96d", "retr"), ("F_hybrid_96d", "hybrid")):
        z, zq, rec, fl = train(kind)
        t1, t5 = topk(z, zq)
        res[name] = {"top1": t1, "top5": t5, "bytes": 384, "final_loss": fl}
        if rec is not None: res[name]["cos"] = cos(full, rec)
        print(f"  {name}: top1 {t1:.4f} top5 {t5:.4f}" + (f" cos {res[name]['cos']:.4f}" if rec is not None else ""), flush=True)

    best = max(res["E_retrieval_96d"]["top1"], res["F_hybrid_96d"]["top1"])
    g1 = best >= res["A_deterministic"]["top1"] + 0.05
    g2 = best >= res["B_int8_full"]["top1"] + 0.05
    g3 = best <= res["A_deterministic"]["top1"]
    verdict = "RETRIEVAL_OBJECTIVE_WINS" if g1 else ("RECONSTRUCTION_STILL_RULES" if g3 else "TIE")
    summary = {"experiment": "TC2 — retrieval-objective 384-byte tile codec", "n_tiles": len(tiles),
               "device": DEV, "arms": res,
               "gates": {"G1_retrieval_objective_wins": bool(g1), "G2_beats_int8": bool(g2), "G3_reconstruction_rules": bool(g3)},
               "verdict": verdict, "wall_clock_s": round(time.time() - t0, 1)}
    json.dump(summary, open(os.path.join(OUT, "tc2_results.json"), "w"), indent=2)
    print(json.dumps(summary, indent=2))
