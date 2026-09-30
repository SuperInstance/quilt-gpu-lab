#!/usr/bin/env python3
"""TC5 — rooms are priors: per-room delta coding vs global coding at equal 24B/tile. Pre-reg: TC456."""
import importlib.util, json, os, time
from collections import defaultdict
import numpy as np
import torch
DEV = "cuda" if torch.cuda.is_available() else "cpu"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results", "tc5")
spec = importlib.util.spec_from_file_location("tc1", os.path.join(ROOT, "experiments", "tc1_tile_codec.py"))
tc1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(tc1)

def topk(index, query, k=5):
    i = index / (np.linalg.norm(index, axis=1, keepdims=True) + 1e-9)
    q = query / (np.linalg.norm(query, axis=1, keepdims=True) + 1e-9)
    rank = np.argsort(-(q @ i.T), axis=1); n = len(index)
    return float((rank[:, 0] == np.arange(n)).mean()), float(np.mean([np.arange(n)[j] in rank[j, :k] for j in range(n)]))

def pca_int8(V, dim):
    Vc = V - V.mean(0); _, _, Vt = np.linalg.svd(Vc, full_matrices=False)
    P = Vt[:dim]; L = Vc @ P.T
    sc = np.abs(L).max(0) / 127.0; Lq = np.clip(np.round(L / (sc + 1e-12)), -127, 127) * sc
    return Vc.mean(0) + Lq @ P, sc

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True); t0 = time.time()
    from sentence_transformers import SentenceTransformer
    tiles = tc1.mine_tiles(); n = len(tiles)
    rooms = defaultdict(list)
    for i, t in enumerate(tiles): rooms[t["domain"]].append(i)
    m = SentenceTransformer("thenlper/gte-small", device=DEV)
    E = lambda xs: m.encode(list(xs), batch_size=32, convert_to_numpy=True, show_progress_bar=False).astype(np.float32)
    full = E([t["question"] + " " + t["answer"] for t in tiles]); qonly = E([t["question"] for t in tiles])
    g_rec, _ = pca_int8(full, 24); g_top1, g_top5 = topk(g_rec, qonly)
    anchors = np.stack([full[v].mean(0) for v in rooms.values()])
    ridx = np.zeros(n, dtype=int)
    for r, (dom, v) in enumerate(rooms.items()): ridx[v] = r
    deltas = full - anchors[ridx]
    d_rec, _ = pca_int8(deltas, 24); r_rec = d_rec + anchors[ridx]; r_top1, r_top5 = topk(r_rec, qonly)
    sizes = [len(v) for v in rooms.values()]
    g1 = r_top1 >= g_top1 + 0.02
    summary = {"experiment": "TC5 rooms are priors", "n_tiles": n, "n_rooms": len(rooms), "mean_room_size": float(np.mean(sizes)), "device": DEV,
               "global_pca24_int8": {"top1": g_top1, "top5": g_top5, "bytes_per_tile": 24},
               "room_delta_pca24_int8": {"top1": r_top1, "top5": r_top5, "bytes_per_tile": 24, "anchor_bytes_amortized": float(384 * 4 / np.mean(sizes))},
               "gates": {"G1_rooms_are_real": bool(g1)},
               "verdict": "ROOMS_ARE_REAL" if g1 else ("TIE" if abs(r_top1 - g_top1) < 0.02 else "NOT_STATISTICAL"),
               "wall_clock_s": round(time.time() - t0, 1)}
    json.dump(summary, open(os.path.join(OUT, "tc5_results.json"), "w"), indent=2)
    print(json.dumps(summary, indent=2), flush=True)
