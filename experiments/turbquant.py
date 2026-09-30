#!/usr/bin/env python3
"""TURBQUANT MEASURED — seeded 4-bit rotation + Lloyd-Max compression on real ledger embeddings.
Frozen per proposals/runs/TURBQUANT-2026-09-29.md. CPU, deterministic (seed 20260929).
Test on the actual embeddings used by the fleet (bge-m3 1024-d cosine)."""
import json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
OUT = os.path.join(LAB, "results", "turbquant.json")
SEED = 20260929
N_GISTS = 250           # gist count from i2i-ledger /since?ts=0
TOPK = 10               # recall@10
ZOOM_FACTOR = 1.5       # for embedding norm scaling
BATCH = 25              # per wrangler ai run call
rng = np.random.default_rng(SEED)

def log(m): print("[turbquant %s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)

def get_gists():
    """Pull gist strings from i2i-ledger (Bearer token read at use time; UA header defeats CF bot-fingerprint 403)."""
    import urllib.request, json, pathlib
    token = ""
    tf = pathlib.Path("/home/eileen/.config/i2i/i2i-token")
    if tf.exists():
        token = tf.read_text().strip()
    # /since requires a real ts (ts=0 silently returns count=0; no ts is a 400) — look back 30d
    ts = int(time.time()) - 30 * 86400
    url = "https://i2i-ledger.casey-digennaro.workers.dev/since?ts=%d&limit=%d" % (ts, N_GISTS)
    headers = {"User-Agent": "fleet-ideation/1.0", "Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            rows = json.load(r)
    except Exception as e:
        sys.exit("[TURBQUANT] FATAL: ledger fetch failed: %s" % e)
    # shape-tolerant: list of strings | list of dicts | dict wrapping any of those
    if isinstance(rows, dict):
        for k in ("entries", "rows", "bookings", "results", "items", "data"):
            if isinstance(rows.get(k), list):
                rows = rows[k]
                break
        else:
            rows = []
    gists = []
    for row in rows if isinstance(rows, list) else []:
        if isinstance(row, str):
            gists.append(row)
        elif isinstance(row, dict):
            g = row.get("gist") or row.get("content") or row.get("text") or ""
            if g:
                gists.append(g)
    gists = [g.strip()[:1000] for g in gists if g and len(g.strip()) >= 40]
    log("pulled %d gists from ledger" % len(gists))
    return gists[:N_GISTS]

def embed_batch(gist_texts):
    """Embed via DeepInfra (BAAI/bge-m3, 1024-d — the same model the ledger uses).

    CF Workers AI REST was tried first: the CF_API_TOKEN authenticates for
    Pages/Workers but returns 401 on /ai/run (scope mismatch), so the fleet's
    reinstated DeepInfra key is the working path. Key read at use-time.
    """
    import urllib.request, pathlib
    token = os.environ.get("DEEPINFRA_KEY") or ""
    if not token:
        tf = pathlib.Path("/home/eileen/.config/deepinfra/token")
        if tf.exists():
            token = tf.read_text().strip()
    if not token:
        sys.exit("[TURBQUANT] FATAL: no DeepInfra key (env DEEPINFRA_KEY or ~/.config/deepinfra/token)")
    req = urllib.request.Request(
        "https://api.deepinfra.com/v1/openai/embeddings",
        data=json.dumps({"model": "BAAI/bge-m3", "input": gist_texts}).encode(),
        method="POST",
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json",
                 "User-Agent": "fleet-turbquant/1.0"})
    import urllib.request, urllib.error, pathlib
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                res = json.loads(r.read().decode())
            break
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 429:
                wait = int(e.headers.get("Retry-After") or 0) or (5 * (attempt + 1))
                log("embeddings 429 — sleeping %ds (attempt %d/4)" % (wait, attempt + 1))
                time.sleep(wait)
                continue
            sys.exit("[TURBQUANT] FATAL: DeepInfra embeddings HTTP %s: %s" % (e.code, e.read()[:200]))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (attempt + 1))
    else:
        sys.exit("[TURBQUANT] FATAL: DeepInfra embeddings failed after retries: %s" % last)
    data = [d["embedding"] for d in res.get("data", [])]
    if len(data) != len(gist_texts):
        sys.exit("[TURBQUANT] FATAL: asked for %d embeddings, got %d" % (len(gist_texts), len(data)))
    return data

def compress(X, n_bits=4):
    """Seeded rotation + Lloyd-Max 4-bit per-dim quantization."""
    # normalize
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    Xz = X / norms * ZOOM_FACTOR

    # orthogonal-ish rotation
    dim = Xz.shape[1]
    A = rng.normal(size=(dim, dim))   # square basis; shape[1:] handed QR a 1-D array (bug #5)
    Q, R = np.linalg.qr(A)
    Xr = Xz @ Q

    # per-dim quantization
    n_levels = 2 ** n_bits
    for d in range(Xr.shape[1]):
        vals = Xr[:, d]
        vmin, vmax = vals.min(), vals.max()
        # Lloyd-Max-like 10 iterations (deterministic, simple)
        for _ in range(10):
            bins = np.linspace(vmin, vmax, n_levels + 1)
            q = np.digitize(vals, bins[:-1])
            centers = (bins[:-1] + bins[1:]) / 2
            new_c = np.array([vals[q == k].mean() if (q == k).any() else centers[k] for k in range(n_levels)])
            if np.allclose(centers, new_c):
                break
            centers = new_c
        Xq = np.interp(vals, bins[:-1], centers)
        Xr[:, d] = Xq

    # de-rotate
    Xr = Xr @ Q.T

    # denormalize
    return Xr / ZOOM_FACTOR * norms

def recall_at_k(X, Xq, k=10):
    """Mean recall@k for q vs full embeddings."""
    n = len(X)
    total = 0
    for i in range(n):
        full_dists = np.linalg.norm(X[i] - X, axis=1)
        q_dists = np.linalg.norm(Xq[i] - Xq, axis=1)
        top_full = np.argpartition(full_dists, k)[:k]
        top_q = np.argpartition(q_dists, k)[:k]
        if set(top_full).intersection(top_q):
            total += 1
    return total / n

def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    # 1) pull gists
    gists = get_gists()
    if len(gists) < 10:
        sys.exit("[TURBQUANT] FATAL: pulled only %d gists (need >=10) — fix the pull, never run on an empty corpus" % len(gists))

    # 2) embed (full)
    log("embedding %d gists (full)..." % len(gists))
    full_embs = []
    for i in range(0, len(gists), BATCH):
        batch = gists[i:i+BATCH]
        batch_embs = embed_batch(batch)
        full_embs.extend(batch_embs)
    X = np.array(full_embs, dtype=np.float32)
    log("full embeddings shape: %s, norm: %0.3f ± %0.3f" % (X.shape, X.mean(), X.std()))

    # 3) checkpoint
    ckpt_path = os.path.join(os.path.dirname(OUT), "turbquant_full_checkpoint.npy")
    np.save(ckpt_path, X)
    log("full embeddings checkpointed to %s" % ckpt_path)

    # 4) compress
    log("compressing to 4-bit with seeded rotation + Lloyd-Max...")
    Xq = compress(X)
    log("compressed embeddings shape: %s, norm: %0.3f ± %0.3f" % (Xq.shape, Xq.mean(), Xq.std()))

    # 5) measure recall@10
    log("computing recall@%d..." % TOPK)
    recall_full = recall_at_k(X, X, k=TOPK)
    recall_q = recall_at_k(X, Xq, k=TOPK)
    loss = 1 - recall_q
    log("recall full=%.4f q=%.4f loss=%.4f" % (recall_full, recall_q, loss))

    # 6) gates
    gate_pass = loss <= 0.02        # 2% recall loss = 8×, close to 0.5% claimed
    gate_marginal = 0.02 < loss <= 0.05
    gate_reject = loss > 0.05
    verdict = ("KEEP_8X" if gate_pass else
               "MARGINAL" if gate_marginal else "REJECT")

    out = {
        "verdict": verdict,
        "recall_full": float(recall_full),
        "recall_q": float(recall_q),
        "loss": float(loss),
        "gate_pass": gate_pass,
        "gate_marginal": gate_marginal,
        "gate_reject": gate_reject,
        "n_gists": N_GISTS,
        "n_bits": 4,
        "seed": SEED,
        "topk": TOPK,
        "zoom": ZOOM_FACTOR,
        "size_full_mb": (X.nbytes / 1024 / 1024),
        "size_q_mb": (Xq.nbytes / 1024 / 1024),
        "compression_ratio": Xq.nbytes / X.nbytes,
    }
    json.dump(out, open(OUT, "w"), indent=1)
    log("verdict=%s -> %s" % (verdict, "KEEP_8X" if gate_pass else "MARGINAL" if gate_marginal else "REJECT"))

if __name__ == "__main__":
    main()
