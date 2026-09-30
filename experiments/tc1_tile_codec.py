#!/usr/bin/env python3
"""TC1 — 384-byte tile codec showdown: deterministic text fields vs int8 vs learned bottleneck.
Pre-reg: proposals/runs/TC1-tile-codec-384.md (frozen gates; do not amend after firing)."""
import glob, hashlib, json, os, re, struct, time
import numpy as np, torch, torch.nn as nn

MAXID, MAXQ, MAXA, MAXD, MAXT, BINARY = 64, 128, 128, 32, 20, 384
DEV = "cuda" if torch.cuda.is_available() else "cpu"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results", "tc1")
SOURCES = ([os.path.join(ROOT, "RESULTS.md")] + glob.glob(os.path.join(ROOT, "proposals", "**", "*.md"), recursive=True)
           + glob.glob("/home/eileen/projects/quilt-research-canons/research/*.md")
           + glob.glob("/home/eileen/.openclaw/workspace/memory/*.md"))

# ---------- crate-faithful codec (byte-truncating, strict-UTF8 decode) ----------
def write_str(buf, off, s, mx):
    b = s.encode("utf-8"); n = min(len(b), mx)
    buf[off:off + n] = b[:n]; return off + mx

def read_str(buf, off, mx):
    end = off + mx
    if end > len(buf): return None
    sl = buf[off:end]; nul = sl.find(0)
    if nul == -1: nul = mx
    try: return sl[:nul].decode("utf-8"), end
    except UnicodeDecodeError: return None      # <- the whole tile is lost, exactly as read_str does

def encode_binary(t):
    buf = bytearray(BINARY); off = 0
    off = write_str(buf, off, t["id"], MAXID)
    off = write_str(buf, off, t["question"], MAXQ)
    off = write_str(buf, off, t["answer"], MAXA)
    off = write_str(buf, off, t["domain"], MAXD)
    off = write_str(buf, off, ",".join(t["tags"]), MAXT)
    buf[off:off + 4] = struct.pack("<f", float(t["confidence"])); off += 4
    buf[off:off + 4] = struct.pack("<f", float(t["ghost_score"])); off += 4
    buf[off:off + 4] = struct.pack("<I", t["use_count"]); off += 4
    assert off == BINARY, off
    return bytes(buf)

def decode_binary(b):
    if len(b) < BINARY: return None
    out, off = {}, 0
    for k, mx in (("id", MAXID), ("question", MAXQ), ("answer", MAXA), ("domain", MAXD)):
        r = read_str(b, off, mx)
        if r is None: return None
        out[k], off = r
    r = read_str(b, off, MAXT)
    if r is None: return None
    out["tags"] = [x for x in r[0].split(",") if x]; out["_end"] = r[1]
    off = r[1]
    out["confidence"] = struct.unpack("<f", b[off:off + 4])[0]; off += 4
    out["ghost_score"] = struct.unpack("<f", b[off:off + 4])[0]; off += 4
    out["use_count"] = struct.unpack("<I", b[off:off + 4])[0]
    return out

# ---------- corpus ----------
def mine_tiles():
    tiles = []
    for p in SOURCES:
        try: txt = open(p, encoding="utf-8", errors="replace").read()
        except OSError: continue
        parts = re.split(r"^#{2,3}\s+(.+)$", txt, flags=re.M)
        for i in range(1, len(parts) - 1, 2):
            head = parts[i].strip()[:200]; body = parts[i + 1].strip()
            body = re.sub(r"\s+", " ", body)
            if len(body) < 80: continue
            ans = body[:400]
            tags = [w.strip(".,;:()[]`*#") for w in head.split()[:3]]
            tags = [t for t in tags if t][:3]
            h = hashlib.sha256((head + ans).encode()).hexdigest()
            tiles.append({"id": h, "question": head, "answer": ans, "domain": os.path.basename(os.path.dirname(p)) or "root",
                          "tags": tags, "confidence": 0.9, "ghost_score": 0.1, "use_count": 1})
    return tiles

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True); t0 = time.time()
    from sentence_transformers import SentenceTransformer
    tiles = mine_tiles()
    print(f"TC1 — {len(tiles)} tiles mined from our own docs; embedder gte-small on {DEV}", flush=True)

    det, fails = [], 0
    for t in tiles:
        d = decode_binary(encode_binary(t))
        if d is None: fails += 1; det.append(None)
        else: det.append((d["question"] + " " + d["answer"]))
    # a failed decode is total loss -> represent as empty string (embedder sees nothing)
    det_text = [d if d else "" for d in det]
    fail_rate = fails / max(1, len(tiles))

    m = SentenceTransformer("thenlper/gte-small", device=DEV)
    emb = lambda xs: m.encode(xs, batch_size=32, convert_to_numpy=True, show_progress_bar=False).astype(np.float32)
    full = emb([t["question"] + " " + t["answer"] for t in tiles])
    qonly = emb([t["question"] for t in tiles])
    a_txt = emb(det_text)

    def cos(a, b):
        a = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-9)
        b = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-9)
        return (a * b).sum(1)

    # arm B: int8 of the full 384-d embedding (384 bytes exactly)
    scale = np.abs(full).max(axis=1, keepdims=True) / 127.0
    b_hat = np.clip(np.round(full / (scale + 1e-12)), -127, 127) * scale

    # arm C: learned 96-d float32 bottleneck (96*4 = 384 bytes)
    ae = nn.Sequential(nn.Linear(384, 96), nn.Tanh(), nn.Linear(96, 384)).to(DEV)
    opt = torch.optim.Adam(ae.parameters(), lr=2e-3); X = torch.tensor(full, device=DEV)
    for _ in range(1200):
        opt.zero_grad(); loss = nn.functional.mse_loss(ae(X), X); loss.backward(); opt.step()
    with torch.no_grad(): c_hat = ae(X).cpu().numpy()
    print(f"  AE final MSE {loss.item():.5f}", flush=True)

    def retrieval(index, query=qonly):
        i = index / (np.linalg.norm(index, axis=1, keepdims=True) + 1e-9)
        q = query / (np.linalg.norm(query, axis=1, keepdims=True) + 1e-9)
        S = q @ i.T; rank = np.argsort(-S, axis=1)
        t1 = (rank[:, 0] == np.arange(len(index))).mean()
        t5 = np.mean([np.arange(len(index))[i] in rank[i, :5] for i in range(len(index))])
        return float(t1), float(t5)

    arms = {"A_deterministic": a_txt, "B_int8_full": b_hat, "C_learned_96d": c_hat}
    res = {"A_deterministic": {"cos": float(cos(full, a_txt).mean()), "bytes": 384, "decode_fail_rate": float(fail_rate)}}
    for k, v in list(arms.items())[1:]:
        res[k] = {"cos": float(cos(full, v).mean()), "bytes": 384}
    for k, v in arms.items():
        t1, t5 = retrieval(v); res[k]["top1"], res[k]["top5"] = t1, t5

    g1 = fail_rate >= 0.05
    best_ad = max(res["B_int8_full"]["cos"], res["C_learned_96d"]["cos"]); best_k = max(("B_int8_full", "C_learned_96d"), key=lambda k: res[k]["cos"])
    g2 = (best_ad >= res["A_deterministic"]["cos"] + 0.10) and (res[best_k]["top1"] >= res["A_deterministic"]["top1"] + 0.05)
    g3 = res["A_deterministic"]["cos"] >= best_ad + 0.10
    verdict = "ADAPTIVE_WINS" if g2 else ("DETERMINISTIC_WINS" if g3 else "TIE")
    summary = {"experiment": "TC1 — 384-byte tile codec showdown", "n_tiles": len(tiles), "device": DEV,
               "arms": res, "gates": {"G1_deterministic_decode_loss": bool(g1), "G2_adaptive_wins": bool(g2),
                                      "G3_deterministic_wins": bool(g3)},
               "best_adaptive": best_k, "verdict": verdict, "wall_clock_s": round(time.time() - t0, 1)}
    json.dump(summary, open(os.path.join(OUT, "tc1_results.json"), "w"), indent=2)
    print(json.dumps(summary, indent=2))
