#!/usr/bin/env python3
"""K1/K2 — latent diff-target vs state-target on frozen V-JEPA 2 latents.

Env overrides (K2 = same harness, real-video cache):
  K1_CACHE (default cache.pt) · K1_OUT (default results/k1_results.json)
  K1_NAME (default "K1")
Gates frozen in proposals/runs/K1-plan.md BEFORE build:
  KEEP  iff diff beats state by >=0.05 relative val reconstruction MSE at BOTH
         seeds AND both arms beat persistence.
  KILL  iff state >= diff pooled paired with healthy harness.
  INCONCLUSIVE (K-G5) iff the win is MLP-reader-only.
Verdict computed in-script against these exact gates.
"""
import json, os, time
import torch, torch.nn as nn

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.environ.get("K1_CACHE", os.path.join(HERE, "cache.pt"))
NAME = os.environ.get("K1_NAME", "K1")
RESULTS = os.path.join(HERE, "results")
OUT_JSON = os.environ.get("K1_OUT", os.path.join(RESULTS, "k1_results.json"))
DEV = "cuda" if torch.cuda.is_available() else "cpu"
SEEDS = (42, 1337)
K_CTX, D_MODEL, STEPS, BATCH, LR = 8, 512, 1200, 64, 3e-4
GATE_REL = 0.05

class TinyPredictor(nn.Module):
    def __init__(self, din):
        super().__init__()
        self.proj = nn.Linear(din, D_MODEL)
        self.pos = nn.Parameter(torch.randn(1, K_CTX, D_MODEL) * 0.02)
        layer = nn.TransformerEncoderLayer(D_MODEL, nhead=8, dim_feedforward=4 * D_MODEL,
                                           batch_first=True, norm_first=True)
        self.blocks = nn.TransformerEncoder(layer, num_layers=2)
        self.head = nn.Linear(D_MODEL, din)
    def forward(self, x):
        h = self.proj(x) + self.pos
        h = self.blocks(h)
        return self.head(h[:, -1])

def windows(z, k=K_CTX):
    return (torch.stack([z[i:i + k] for i in range(len(z) - k)]),
            torch.stack([z[i + k] for i in range(len(z) - k)]))

def ridge_fit(X, y, lam=1.0):
    Y = nn.functional.one_hot(y, int(y.max()) + 1).float()
    A = X.T @ X + lam * torch.eye(X.shape[1])
    return torch.linalg.solve(A, X.T @ Y)

def mlp_fit(X, y, hidden=64, epochs=200, lr=1e-2, seed=0):
    torch.manual_seed(seed)
    net = nn.Sequential(nn.Linear(X.shape[1], hidden), nn.ReLU(), nn.Linear(hidden, int(y.max()) + 1))
    opt = torch.optim.Adam(net.parameters(), lr=lr)
    Y = nn.functional.one_hot(y, int(y.max()) + 1).float()
    for _ in range(epochs):
        opt.zero_grad(); nn.functional.cross_entropy(net(X), Y).backward(); opt.step()
    return net

def run_arm(target, seed, tr, va):
    torch.manual_seed(seed)
    Xtr, Ytr = windows(tr); Xva, Yva = windows(va)
    model = TinyPredictor(Xtr.shape[-1]).to(DEV)
    opt = torch.optim.AdamW(model.parameters(), lr=LR)
    n = len(Xtr)
    for _ in range(STEPS):
        idx = torch.randint(0, n, (BATCH,))
        xb, yb = Xtr[idx].to(DEV), Ytr[idx].to(DEV)
        out = model(xb)
        tgt = (yb - xb[:, -1]) if target == "diff" else yb
        nn.functional.mse_loss(out, tgt).backward()
        opt.step(); opt.zero_grad()
    with torch.no_grad():  # IDENTICAL scoring: reconstruction MSE vs z_{t+1}
        rec = model(Xva.to(DEV))
        rec = rec + Xva[:, -1].to(DEV) if target == "diff" else rec
        mse = nn.functional.mse_loss(rec, Yva.to(DEV)).item()
    return mse, (rec.cpu(), Yva)

def readers(rec_va, labels_va, k_ctx=K_CTX):
    Lva = labels_va[k_ctx:]
    X = rec_va[0].float()
    Xc = X - X.mean(0, keepdim=True); Xs = Xc / (Xc.norm(dim=1, keepdim=True) + 1e-6)
    half = len(Xs) // 2
    w = ridge_fit(Xs[:half], Lva[:half])
    r_acc = ((Xs[half:] @ w).argmax(1) == Lva[half:]).float().mean().item()
    net = mlp_fit(Xs[:half], Lva[:half], seed=0)
    with torch.no_grad():
        m_acc = (net(Xs[half:]).argmax(1) == Lva[half:]).float().mean().item()
    return round(r_acc, 4), round(m_acc, 4)

def main():
    t0 = time.time()
    ck = torch.load(CACHE, map_location="cpu")
    data, meta = ck["data"], ck["meta"]
    tr_z, va_z = data["train"]["latents"], data["val"]["latents"]
    va_l = data["val"]["labels"]
    persistence = {s: nn.functional.mse_loss(va_z[1:], va_z[:-1]).item() for s in SEEDS}
    res = {"experiment": f"{NAME} latent diff-target vs state-target",
           "meta": meta, "seeds": SEEDS, "steps": STEPS,
           "persistence_mse": persistence, "arms": {}}
    for target in ("state", "diff"):
        for seed in SEEDS:
            mse, rec = run_arm(target, seed, tr_z, va_z)
            r_acc, m_acc = readers(rec, va_l)
            res["arms"][f"{target}_{seed}"] = {"val_rec_mse": round(mse, 6),
                                               "reader_ridge": r_acc, "reader_mlp": m_acc}
            print(f"[{NAME}] {target}@{seed}: mse={mse:.6f} ridge={r_acc} mlp={m_acc} ({time.time()-t0:.0f}s)", flush=True)
    def mse(t, s): return res["arms"][f"{t}_{s}"]["val_rec_mse"]
    rel = {s: (mse("state", s) - mse("diff", s)) / mse("state", s) for s in SEEDS}
    healthy = all(mse(t, s) < persistence[s] for t in ("state", "diff") for s in SEEDS)
    mlp_only = (all(res["arms"][f"diff_{s}"]["reader_mlp"] > res["arms"][f"state_{s}"]["reader_mlp"] for s in SEEDS)
                and not all(res["arms"][f"diff_{s}"]["reader_ridge"] >= res["arms"][f"state_{s}"]["reader_ridge"] for s in SEEDS))
    if not healthy:
        verdict = "INVALID_HARNESS"
    elif all(rel[s] >= GATE_REL for s in SEEDS):
        verdict = "INCONCLUSIVE (K-G5: MLP-reader-only win)" if mlp_only else "KEEP"
    else:
        pooled_state = sum(mse("state", s) for s in SEEDS)
        pooled_diff = sum(mse("diff", s) for s in SEEDS)
        verdict = "KILL" if pooled_state <= pooled_diff else "INCONCLUSIVE (mixed seeds)"
    res.update({"relative_win": {str(s): round(rel[s], 4) for s in SEEDS},
                "verdict": verdict, "seconds": round(time.time() - t0, 1)})
    os.makedirs(RESULTS, exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(res, f, indent=2)
    print(json.dumps({"experiment": NAME, "verdict": verdict,
                      "relative_win": res["relative_win"], "persistence": persistence,
                      "arms": res["arms"]}, indent=2))

if __name__ == "__main__":
    main()
