#!/usr/bin/env python3
"""K1 — latent diff-target vs state-target on frozen V-JEPA 2 latents.

The keel's first rung (K1-plan.md gates frozen BEFORE build):
  KEEP  iff diff beats state by >=0.05 relative val reconstruction MSE at BOTH
         seeds AND both arms beat persistence.
  KILL  iff state >= diff pooled paired with healthy harness.
  INCONCLUSIVE (K-G5) iff the win is MLP-reader-only.
Verdict computed in-script against these exact gates. Receipts to results/.
"""
import json, os, time
import torch, torch.nn as nn

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache.pt")
RESULTS = os.path.join(HERE, "results")
DEV = "cuda" if torch.cuda.is_available() else "cpu"
SEEDS = (42, 1337)
K_CTX, D_MODEL, STEPS, BATCH, LR = 8, 512, 1200, 64, 3e-4
GATE_REL, GATE_MARGIN_AB = 0.05, 0.05

class TinyPredictor(nn.Module):
    def __init__(self, din):
        super().__init__()
        self.proj = nn.Linear(din, D_MODEL)
        self.pos = nn.Parameter(torch.randn(1, K_CTX, D_MODEL) * 0.02)
        layer = nn.TransformerEncoderLayer(D_MODEL, nhead=8, dim_feedforward=4 * D_MODEL,
                                           batch_first=True, norm_first=True)
        self.blocks = nn.TransformerEncoder(layer, num_layers=2)
        self.head = nn.Linear(D_MODEL, din)
    def forward(self, x):                      # x: (B, K, din)
        h = self.proj(x) + self.pos
        h = self.blocks(h)                     # causal mask omitted: K fixed-window, no leak of target
        return self.head(h[:, -1])             # (B, din)

def windows(z, k=K_CTX):
    return torch.stack([z[i:i + k] for i in range(len(z) - k)]), \
           torch.stack([z[i + k] for i in range(len(z) - k)])

def ridge_fit(X, y, lam=1.0):
    Y = torch.nn.functional.one_hot(y, 4).float()
    A = X.T @ X + lam * torch.eye(X.shape[1]); w = torch.linalg.solve(A, X.T @ Y)
    return w

def mlp_fit(X, y, hidden=64, epochs=200, lr=1e-2, seed=0):
    torch.manual_seed(seed)
    net = nn.Sequential(nn.Linear(X.shape[1], hidden), nn.ReLU(), nn.Linear(hidden, 4))
    opt = torch.optim.Adam(net.parameters(), lr=lr)
    Y = torch.nn.functional.one_hot(y, 4).float()
    for _ in range(epochs):
        opt.zero_grad(); loss = nn.functional.cross_entropy(net(X), Y); loss.backward(); opt.step()
    return net

def run_arm(target, seed, tr, va):
    torch.manual_seed(seed)
    Xtr, Ytr = windows(tr); Xva, Yva = windows(va)
    model = TinyPredictor(Xtr.shape[-1]).to(DEV)
    opt = torch.optim.AdamW(model.parameters(), lr=LR)
    n = len(Xtr)
    for step in range(STEPS):
        idx = torch.randint(0, n, (BATCH,))
        xb, yb = Xtr[idx].to(DEV), Ytr[idx].to(DEV)
        out = model(xb)
        tgt = (yb - xb[:, -1]) if target == "diff" else yb
        loss = nn.functional.mse_loss(out, tgt)
        opt.zero_grad(); loss.backward(); opt.step()
    with torch.no_grad():  # IDENTICAL scoring: reconstruction MSE vs z_{t+1}
        rec = model(Xva.to(DEV))
        rec = rec + Xva[:, -1].to(DEV) if target == "diff" else rec
        mse = nn.functional.mse_loss(rec, Yva.to(DEV)).item()
    return mse, (rec.cpu(), Yva)

def readers(rec_va, labels_va):
    """Quadrant classification from reconstructed latents; returns (ridge acc, mlp acc)."""
    Lva = labels_va[K_CTX:]
    X, Xl = rec_va[0].float(), rec_va[1].float()
    Xc = X - X.mean(0, keepdim=True); Xs = Xc / (Xc.norm(dim=1, keepdim=True) + 1e-6)
    # ridge on train half of val (honest: readers fit on held-out-from-arms data only)
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
    tr_z, tr_l = data["train"]["latents"], data["train"]["labels"]
    va_z, va_l = data["val"]["latents"], data["val"]["labels"]
    persistence = {s: nn.functional.mse_loss(va_z[1:], va_z[:-1]).item() for s in SEEDS}
    res = {"experiment": "K1 latent diff-target vs state-target", "meta": meta,
           "seeds": SEEDS, "steps": STEPS, "persistence_mse": persistence, "arms": {}}
    for target in ("state", "diff"):
        for seed in SEEDS:
            mse, rec = run_arm(target, seed, tr_z, va_z)
            r_acc, m_acc = readers(rec, va_l)
            res["arms"][f"{target}_{seed}"] = {"val_rec_mse": round(mse, 6),
                                               "reader_ridge": r_acc, "reader_mlp": m_acc}
            print(f"[K1] {target}@{seed}: mse={mse:.6f} ridge={r_acc} mlp={m_acc} ({time.time()-t0:.0f}s)", flush=True)
    def mse(t, s): return res["arms"][f"{t}_{s}"]["val_rec_mse"]
    rel = {s: (mse("state", s) - mse("diff", s)) / mse("state", s) for s in SEEDS}
    healthy = all(mse(t, s) < persistence[s] for t in ("state", "diff") for s in SEEDS)
    mlp_only = all(res["arms"][f"diff_{s}"]["reader_mlp"] > res["arms"][f"state_{s}"]["reader_mlp"]
                   for s in SEEDS) and not all(res["arms"][f"diff_{s}"]["reader_ridge"] >= res["arms"][f"state_{s}"]["reader_ridge"]
                   for s in SEEDS)
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
    with open(os.path.join(RESULTS, "k1_results.json"), "w") as f:
        json.dump(res, f, indent=2)
    print(json.dumps({"experiment": "K1", "verdict": verdict,
                      "relative_win": res["relative_win"], "persistence": persistence,
                      "arms": res["arms"]}, indent=2))

if __name__ == "__main__":
    main()
