#!/usr/bin/env python3
"""S6b — does the loop need somewhere to write? (edge-mine M16 falsifier)

Pre-registered: proposals/runs/S6b-memory-tokens-scratchpad-prereg.md
(owner: farm). STATUS: written untested — owning lane reviews before fire.
Fail-loud harness receipts if anything crashes; no gate may be loosened.

Task (our own physics): partner discovery for channel 0. Channel streams use
exact d12j semantics (seeded perm pairing; per-sample correlated w.p. p).
At each timestep t the model receives the evidence vector
    e_t[j] = (1/W) * sum_w s0[w,t] * sj[w,t]
(signed; the partner leans positive with mean p, noise ~ N(0, 1/sqrt(W))).
It must output partner[0] (N-way). Self-evidence e_t[0] is pinned to 0.0
(self excluded, same as the D-line argmax rule). The full-trajectory
solution is the running correlation sum — the model must integrate noisy
evidence across T rounds.

Arms (frozen):
  MEM    — 4 persistent memory tokens; each timestep attends to
           [mem | token], looped R=4 times, mem written back per iteration;
           readout pools the T per-step outputs AND the final mem state.
  NOMEM  — same looped block, no persistent tokens, mean-pool readout.
  MATCH  — NOMEM at extra width d=1088 (params >= MEM, per the frozen
           "extra width instead of memory tokens" control).
Model: one transformer block applied R=4 times per timestep.
MEM d=1024 (~8.7M params), NOMEM d=1024 (~8.4M), MATCH d=1088 (~9.3M).

Gates (mechanical, _verdict): WRITE_HELPS / WRITE_NEUTRAL /
CAPACITY_CONFOUND / MIXED_OR_FAIL. Floors on frozen corners, T ladder
1..32, 5 draws, acc bar 0.9 (strict over 5 draws => 5/5 — declared).
"""
import json
import sys
import time
import traceback

import torch
import torch.nn as nn

SEED = 2718
ARM_SEEDS = {"MEM": 11, "NOMEM": 22, "MATCH": 33}
TRAIN_CORNERS = [(8, 32, 0.3), (16, 64, 0.3), (16, 32, 0.5), (32, 64, 0.7)]
EVAL_CORNERS = [(32, 128, 0.3), (64, 128, 0.3), (64, 64, 0.5)]
T_LADDER = list(range(1, 33))
EVAL_DRAWS = 5
ACC_BAR = 0.9
R_DEPTH = 4
N_MEM = 4
STEPS = 30000
BATCH = 64
WALL_BUDGET_S = 3 * 3600
OUT_PATH = "results/s6b_memory_tokens.json"


def preflight():
    free, _total = torch.cuda.mem_get_info()
    if free < 2 * 1024 * 1024 * 1024:
        raise RuntimeError(f"preflight FAIL: only {free/2**20:.0f} MiB VRAM free (< 2048)")


def make_batch(W, N, p, T, bs, dev, gen):
    """Vectorized d12j semantics. Returns evidence (bs,T,N), partner0 (bs,)."""
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
    s0 = cells[:, 0]                                   # channel 0's own stream
    ev = torch.einsum("bwt,bnwt->btn", s0, cells) / W  # (bs,T,N)
    ev[:, :, 0] = 0.0                                  # self excluded
    return ev, partner[:, 0]


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


class DiscoveryNet(nn.Module):
    def __init__(self, d, n_channels, mem, r=R_DEPTH):
        super().__init__()
        self.d, self.mem, self.r = d, mem, r
        self.inp = nn.Linear(1, d)
        self.pos = nn.Embedding(40, d)
        self.mem_tok = nn.Parameter(torch.randn(N_MEM, d) * 0.02) if mem else None
        self.block = LoopedBlock(d)
        read_d = 2 * d if mem else d
        self.read = nn.Sequential(nn.LayerNorm(read_d), nn.Linear(read_d, n_channels))

    def forward(self, ev, mask):
        bs, T, N = ev.shape
        state = (self.mem_tok.unsqueeze(0).expand(bs, -1, -1)
                 if self.mem else None)
        outs = []
        for t in range(T):
            tok = self.inp(ev[:, t:t + 1]) + self.pos.weight[t]
            seq = torch.cat([state, tok], dim=1) if self.mem else tok
            for _ in range(self.r):
                seq = self.block(seq)
            if self.mem:
                state, cur = seq[:, :-1], seq[:, -1:]
                outs.append(cur)
            else:
                outs.append(seq)
        pooled = torch.cat(outs, 1)                    # (bs,T,d)
        m = mask.unsqueeze(-1)
        pooled = (pooled * m).sum(1) / m.sum(1).clamp(min=1)
        if self.mem:
            pooled = torch.cat([pooled, state.mean(1)], dim=-1)
        return self.read(pooled)


def _floor(accs_by_T):
    for T in T_LADDER:
        if accs_by_T.get(T, 0.0) >= ACC_BAR:
            return T
    return None


def _verdict(floors):
    def d(arm, c):
        return floors[arm].get(str(c))
    wins = sum(1 for c in EVAL_CORNERS
               if d("MEM", c) is not None
               and (d("NOMEM", c) is None or d("MEM", c) < d("NOMEM", c)))
    not_conf = sum(1 for c in EVAL_CORNERS
                   if d("MEM", c) is not None
                   and (d("MATCH", c) is None or d("MEM", c) <= d("MATCH", c)))
    neutral = all(d("MEM", c) is not None and d("NOMEM", c) is not None
                  and abs(d("MEM", c) - d("NOMEM", c)) <= 1
                  for c in EVAL_CORNERS)
    if wins >= 2 and not_conf >= 2:
        return "WRITE_HELPS"
    if neutral:
        return "WRITE_NEUTRAL"
    if wins >= 2:
        return "CAPACITY_CONFOUND"
    return "MIXED_OR_FAIL"


def run_arm(name, d, mem, dev):
    torch.manual_seed(SEED + ARM_SEEDS[name])
    gen = torch.Generator(device=dev)
    gen.manual_seed(SEED + ARM_SEEDS[name])
    model = DiscoveryNet(d=d, n_channels=128, mem=mem).to(dev)
    n_params = sum(p.numel() for p in model.parameters())
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
        with torch.autocast("cuda", dtype=torch.bfloat16):
            loss = torch.nn.functional.cross_entropy(
                model(ev, mask).float(), y)
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
                    pred = model(ev, torch.ones(1, T, device=dev))[0].argmax()
                    hits += int(pred.item() == y.item())
                accs[T] = hits / EVAL_DRAWS
            floors[str((W, N, p))] = _floor(accs)
            if floors[str((W, N, p))] is None:
                floors[str((W, N, p)) + "|accs"] = {str(t): a for t, a in accs.items() if a > 0}
    return {"arm": name, "d": d, "params": n_params,
            "steps": step, "budget_capped": capped, "floors": floors}


def main():
    preflight()
    dev = "cuda"
    out = {}
    for name, d, mem in (("MEM", 1024, True), ("NOMEM", 1024, False),
                         ("MATCH", 1088, False)):
        out[name] = run_arm(name, d, mem, dev)
    verdict = _verdict({k: v["floors"] for k, v in out.items()})
    result = {
        "experiment": "s6b_memory_tokens",
        "device": torch.cuda.get_device_name(0),
        "runner_status": "written-untested; owning lane reviewed before fire",
        "arms": out,
        "gates": {"WRITE_HELPS": verdict == "WRITE_HELPS",
                  "WRITE_NEUTRAL": verdict == "WRITE_NEUTRAL",
                  "CAPACITY_CONFOUND": verdict == "CAPACITY_CONFOUND"},
        "verdict": verdict,
        "pre_registered": "proposals/runs/S6b-memory-tokens-scratchpad-prereg.md",
    }
    with open(OUT_PATH, "w") as fh:
        json.dump(result, fh, indent=2, default=str)
    print(json.dumps({"verdict": verdict,
                      "floors": {k: v["floors"] for k, v in out.items()}},
                     indent=2, default=str))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        with open(OUT_PATH, "w") as fh:
            json.dump({"experiment": "s6b_memory_tokens",
                       "verdict": "KILL-harness",
                       "error": traceback.format_exc(),
                       "python": sys.executable}, fh, indent=2)
        raise
