#!/usr/bin/env python3
"""XQ0 — does consolidation-by-substrate think? (G0 falsifier, docs/XQ-PROGRAM.md)

Pre-registered: proposals/runs/XQ0-substrate-consolidation-prereg.md (owner: farm).
STATUS: written untested — owning lane reviews before fire. Fail-loud receipts.

Task: partner-of-channel-0 discovery on d12j-exact streams (make_batch copied
verbatim from s6b_memory_tokens.py). Arms:
  NOMEM   d=1024, no quilt, mean-pool readout (internal integration)
  MATCH   d=1088, no quilt, extra width control
  PASSIVE d=1024, quilt F=0 (state persists, nothing consolidates)
  QFLOW   d=1024, quilt F=4 (flow consolidates between timesteps)
Quilt arms: cells [0..N) = evidence block SET to 3*e_t each timestep (±3 = the
oracle's inject convention); cells [N..q*q) = annotation block SET by the NN's
write head (3*tanh). Read = full field each timestep; final logits from a
post-flow field read. Declared asymmetry vs no-quilt arms (pool readout): each
arm integrates by its own means — that IS the comparison. Quilt semantics =
oracle flow (k=0.22, res=0.4), torch re-implementation, gradients flow through.
"""
import json
import sys
import time
import traceback

import torch
import torch.nn as nn

SEED = 2718
ARM_SEEDS = {"NOMEM": 11, "MATCH": 22, "PASSIVE": 33, "QFLOW": 44}
TRAIN_CORNERS = [(8, 32, 0.3), (16, 64, 0.3), (16, 32, 0.5), (32, 64, 0.7)]
EVAL_CORNERS = [(32, 128, 0.3), (64, 128, 0.3), (64, 64, 0.5)]
T_LADDER = list(range(1, 33))
EVAL_DRAWS = 5
ACC_BAR = 0.9
R_DEPTH = 4
Q_GRID = 16
STEPS = 30000
BATCH = 64
WALL_BUDGET_S = 3 * 3600
OUT_PATH = "results/xq0_substrate_consolidation.json"


def preflight():
    free, _total = torch.cuda.mem_get_info()
    if free < 2 * 1024 * 1024 * 1024:
        raise RuntimeError(f"preflight FAIL: only {free/2**20:.0f} MiB VRAM free (< 2048)")


def make_batch(W, N, p, T, bs, dev, gen):
    """Verbatim from s6b_memory_tokens.py — d12j semantics."""
    perm = torch.rand(bs, N, generator=gen, device=dev).argsort(dim=1)
    partner = torch.empty(bs, N, dtype=torch.long, device=dev)
    pa, pb = perm[:, 0::2], perm[:, 1::2]
    partner.scatter_(1, pa, pb)
    partner.scatter_(1, pb, pa)
    P = N // 2
    shape = (bs, P, W, T)
    corr = torch.rand(shape, generator=gen, device=dev) < p
    base = torch.where(torch.rand(shape, generator=gen, device=dev) < 0.5, 1.0, -1.0)
    ia = torch.where(torch.rand(shape, generator=gen, device=dev) < 0.5, 1.0, -1.0)
    ib = torch.where(torch.rand(shape, generator=gen, device=dev) < 0.5, 1.0, -1.0)
    cells = torch.empty(bs, N, W, T, device=dev)
    bidx = torch.arange(bs, device=dev).unsqueeze(1)
    cells[bidx, pa] = torch.where(corr, base, ia)
    cells[bidx, pb] = torch.where(corr, base, ib)
    s0 = cells[:, 0]
    ev = torch.einsum("bwt,bnwt->btn", s0, cells) / W
    ev[:, :, 0] = 0.0
    return ev, partner[:, 0]


def quilt_step(pot, res_val, k=0.22, q=Q_GRID):
    """One flow pass, oracle semantics (snapshot diffs, S/N/E/W), differentiable.
    Border neighbors padded +1e4 so the d > res gate never fires out of bounds."""
    B = pot.shape[0]
    g = pot.view(B, q, q)
    up = torch.nn.functional.pad(g[:, :-1, :], (0, 0, 0, 1), value=1e4)
    down = torch.nn.functional.pad(g[:, 1:, :], (0, 0, 1, 0), value=1e4)
    left = torch.nn.functional.pad(g[:, :, :-1], (0, 1, 0, 0), value=1e4)
    right = torch.nn.functional.pad(g[:, :, 1:], (1, 0, 0, 0), value=1e4)
    adj = g
    for nb in (down, up, right, left):          # S, N, E, W (oracle op order)
        d = g - nb
        adj = adj - torch.where(d > res_val, (d - res_val) * k,
                                torch.zeros_like(d))
    return adj.reshape(B, -1)


class QuiltField:
    def __init__(self, bs, N, F, res=0.4, k=0.22, dev="cuda"):
        self.bs, self.N, self.F, self.res, self.k = bs, N, F, res, k
        self.pot = torch.zeros(bs, Q_GRID * Q_GRID, device=dev)

    def reset(self):
        self.pot = torch.zeros_like(self.pot)

    def inject_evidence(self, e):
        n = e.shape[1]
        self.pot = self.pot.clone()
        self.pot[:, :n] = 3.0 * e

    def write_annotation(self, w, n):
        # annotation block = cells [n..q*q); write head emits q*q, sliced to fit
        self.pot = self.pot.clone()
        self.pot[:, n:] = 3.0 * torch.tanh(w[:, : self.pot.shape[1] - n])

    def flow_steps(self):
        for _ in range(self.F):
            self.pot = quilt_step(self.pot, self.res, self.k)

    def read(self):
        return self.pot


class LoopedBlock(nn.Module):
    def __init__(self, d, ff=2048, heads=8):
        super().__init__()
        self.attn = nn.MultiheadAttention(d, heads, batch_first=True)
        self.ln1 = nn.LayerNorm(d)
        self.ln2 = nn.LayerNorm(d)
        self.ff = nn.Sequential(nn.Linear(d, ff), nn.GELU(), nn.Linear(ff, d))

    def forward(self, x):
        a, _ = self.attn(x, x, x, need_weights=False)
        x = self.ln1(x + a)
        return self.ln2(x + self.ff(x))


class XQNet(nn.Module):
    def __init__(self, d, n_channels, q=None, r=R_DEPTH):
        super().__init__()
        self.d, self.q, self.r = d, q, r
        self.n_channels = n_channels
        in_dim = n_channels + (q * q if q else 0)
        self.inp = nn.Linear(in_dim, d)
        self.pos = nn.Embedding(40, d)
        self.block = LoopedBlock(d)
        self.write = nn.Linear(d, q * q) if q else None
        self.read = nn.Sequential(nn.LayerNorm(d), nn.Linear(d, n_channels))

    def forward(self, ev, mask, quilt=None):
        bs, T, N = ev.shape
        outs = []
        for t in range(T):
            ev_t = torch.nn.functional.pad(ev[:, t], (0, self.n_channels - N))
            if quilt is not None:
                tok_in = torch.cat([ev_t, quilt.read()], dim=1)
            else:
                tok_in = ev_t
            seq = (self.inp(tok_in) + self.pos.weight[t]).unsqueeze(1)
            for _ in range(self.r):
                seq = self.block(seq)
            outs.append(seq[:, 0])
            if quilt is not None:
                quilt.write_annotation(self.write(seq[:, 0]), n=N)
                quilt.inject_evidence(ev[:, t])
                quilt.flow_steps()
        if quilt is not None:
            seq = (self.inp(quilt.read()) + self.pos.weight[0]).unsqueeze(1)
            for _ in range(self.r):
                seq = self.block(seq)
            return self.read(seq[:, 0])
        pooled = torch.stack(outs, 1)
        m = mask.unsqueeze(-1)
        pooled = (pooled * m).sum(1) / m.sum(1).clamp(min=1)
        return self.read(pooled)


def _floor(accs_by_T):
    for T in T_LADDER:
        if accs_by_T.get(T, 0.0) >= ACC_BAR:
            return T
    return None


def _beat(floors, a, b):
    n = 0
    for c in EVAL_CORNERS:
        fa, fb = floors[a].get(str(c)), floors[b].get(str(c))
        if fa is not None and (fb is None or fa < fb):
            n += 1
    return n


def _min_le(floors, arms_a, arm_b, strict=False):
    n = 0
    for c in EVAL_CORNERS:
        vals = [floors[a].get(str(c)) for a in arms_a]
        fb = floors[arm_b].get(str(c))
        cand = min((v for v in vals if v is not None), default=None)
        ok = (cand is not None
              and (fb is None or (cand < fb if strict else cand <= fb)))
        n += ok
    return n


def _verdict(floors, capped):
    if any(capped.values()):
        return "INCONCLUSIVE-CAPPED"
    if _beat(floors, "QFLOW", "PASSIVE") >= 2:
        return "SUBSTRATE_THINKS"
    if _min_le(floors, ("PASSIVE", "QFLOW"), "NOMEM", strict=True) >= 2 \
            and _min_le(floors, ("PASSIVE", "QFLOW"), "MATCH") >= 2:
        return "EXTERNAL_HELPS"
    if all(_min_le(floors, ("MATCH",), a) >= 2 for a in ("PASSIVE", "QFLOW")):
        return "CAPACITY_CONFOUND"
    return "DEAD_SUBSTRATE/MIXED"


def run_arm(name, d, quilt_F, dev):
    torch.manual_seed(SEED + ARM_SEEDS[name])
    gen = torch.Generator(device=dev)
    gen.manual_seed(SEED + ARM_SEEDS[name])
    has_q = quilt_F is not None
    model = XQNet(d=d, n_channels=128, q=(Q_GRID if has_q else None)).to(dev)
    n_params = sum(p.numel() for p in model.parameters())
    quilt = QuiltField(BATCH, 128, quilt_F, dev=dev) if has_q else None
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4)
    train_gen = torch.Generator(device=dev)
    train_gen.manual_seed(SEED + ARM_SEEDS[name] + 1)
    t_start = time.perf_counter()
    step = 0
    while step < STEPS and time.perf_counter() - t_start < WALL_BUDGET_S:
        W, N, p = TRAIN_CORNERS[step % len(TRAIN_CORNERS)]
        T = int(torch.randint(1, 17, (1,), device=dev,
                              generator=train_gen).item())
        ev, y = make_batch(W, N, p, T, BATCH, dev, train_gen)
        mask = torch.ones(BATCH, T, device=dev)
        if quilt is not None:
            quilt.reset()
        with torch.autocast("cuda", dtype=torch.bfloat16):
            loss = torch.nn.functional.cross_entropy(
                model(ev, mask, quilt).float(), y)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        step += 1
    capped = time.perf_counter() - t_start >= WALL_BUDGET_S

    model.eval()
    eval_gen = torch.Generator(device=dev)
    eval_gen.manual_seed(SEED + ARM_SEEDS[name] + 2)
    floors = {}
    with torch.no_grad():
        for (W, N, p) in EVAL_CORNERS:
            accs = {}
            for T in T_LADDER:
                hits = 0
                for _ in range(EVAL_DRAWS):
                    ev, y = make_batch(W, N, p, T, 1, dev, eval_gen)
                    q1 = QuiltField(1, N, quilt_F, dev=dev) if has_q else None
                    pred = model(ev, torch.ones(1, T, device=dev), q1)[0].argmax()
                    hits += int(pred.item() == y.item())
                accs[T] = hits / EVAL_DRAWS
            floors[str((W, N, p))] = _floor(accs)
            if floors[str((W, N, p))] is None:
                floors[str((W, N, p)) + "|accs"] = {str(t): a for t, a in accs.items() if a > 0}
    return {"arm": name, "d": d, "quilt_F": quilt_F, "params": n_params,
            "steps": step, "budget_capped": capped, "floors": floors}


def main():
    preflight()
    dev = "cuda"
    out = {}
    for name, d, F in (("NOMEM", 1024, None), ("MATCH", 1088, None),
                       ("PASSIVE", 1024, 0), ("QFLOW", 1024, 4)):
        out[name] = run_arm(name, d, F, dev)
    floors = {k: v["floors"] for k, v in out.items()}
    verdict = _verdict(floors, {k: v["budget_capped"] for k, v in out.items()})
    result = {
        "experiment": "xq0_substrate_consolidation",
        "device": torch.cuda.get_device_name(0),
        "runner_status": "written-untested; owning lane reviewed before fire",
        "arms": out,
        "gates": {"SUBSTRATE_THINKS": verdict == "SUBSTRATE_THINKS",
                  "EXTERNAL_HELPS": verdict == "EXTERNAL_HELPS",
                  "CAPACITY_CONFOUND": verdict == "CAPACITY_CONFOUND"},
        "verdict": verdict,
        "pre_registered": "proposals/runs/XQ0-substrate-consolidation-prereg.md",
    }
    with open(OUT_PATH, "w") as fh:
        json.dump(result, fh, indent=2, default=str)
    print(json.dumps({"verdict": verdict, "floors": floors}, indent=2, default=str))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        kill_path = OUT_PATH.replace(
            ".json", f".harness-invalid-{int(time.time())}.json")
        with open(kill_path, "w") as fh:
            json.dump({"experiment": "xq0_substrate_consolidation",
                       "kill_receipt": kill_path,
                       "verdict": "KILL-harness",
                       "error": traceback.format_exc(),
                       "python": sys.executable}, fh, indent=2)
        raise
