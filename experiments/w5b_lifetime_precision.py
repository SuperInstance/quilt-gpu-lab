#!/usr/bin/env python3
"""W5b — lifetime-scaled ternary delta state (frozen pre-reg: proposals/runs/W5b-lifetime-precision.md).

Question: does allocating a small high-precision budget to the LONGEST-LIVED ternary delta positions
beat uniform/random allocation on held-out bpb, at equal budget and equal training budget?

Arms (fork from one shared warmup checkpoint per seed): lifetime / uniform / random / antirank(secondary).
"""
import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "results" / "w5b_lifetime_precision"

SEQ, BATCH, C_COMMIT = 64, 64, 25
HID, LR, CLIP, K_FRAC = 384, 3e-3, 1.0, 0.02
T_WARM, T_MAIN, EVAL_EVERY = 4000, 6000, 1000
SEEDS = [4241, 4242, 4243]
CORPUS_CAP = 2 * 1024 * 1024
ARMS = ["lifetime", "uniform", "random", "antirank"]
MARGIN = 0.005  # frozen: >=0.5% relative bpb improvement, lifetime vs random


def build_corpus():
    """All tracked *.md at the fire commit, sorted, concatenated. No shell (critical-path rule)."""
    r = subprocess.run(["git", "ls-files", "*.md"], cwd=str(REPO),
                       capture_output=True, text=True, check=True)
    files = sorted(f for f in r.stdout.splitlines() if f.strip())
    parts = []
    for f in files:
        try:
            parts.append((REPO / f).read_text(encoding="utf-8", errors="replace"))
        except OSError:
            pass
    return ("\n\n".join(parts))[:CORPUS_CAP], files


def ternarize(W):
    """Frozen TWN: delta = 0.7*mean|W|; Q = sign(W) where |W|>delta else 0; s = mean|W| over survivors."""
    with torch.no_grad():
        delta = 0.7 * W.abs().mean()
        mask = W.abs() > delta
        Q = torch.where(mask, torch.sign(W), torch.zeros_like(W))
        s = W[mask].abs().mean() if bool(mask.any()) else torch.zeros((), device=W.device)
    return Q.detach(), s.detach().float()


class TernaryState:
    """Per-tensor: committed ternary Q, scale s, high-precision slots (permanently exact), change counters."""

    def __init__(self, W):
        self.Q, self.s = ternarize(W)
        self.HP = torch.zeros_like(W, dtype=torch.bool)
        self.H = torch.zeros_like(W)
        self.changes = torch.zeros(W.shape, dtype=torch.int32, device=W.device)
        self.n_commits = 0

    def commit(self, W):
        Qn, sn = ternarize(W)
        with torch.no_grad():
            self.changes += (Qn != self.Q).to(torch.int32)   # committed-state flips
            self.Q, self.s = Qn, sn
            self.H = torch.where(self.HP, W.detach() - self.s * self.Q, torch.zeros_like(W))
            self.n_commits += 1

    def eff(self, W):
        """Forward weight: s*Q + H on HP slots (exact); identity straight-through for the master W."""
        base = self.s * self.Q + self.H
        return base + (W - W.detach())


def gru_cell(x, h, Wih, Whh, bih, bhh, H):
    """PyTorch gate order: [reset, update, new]. Verified against nn.GRU in --smoke."""
    gi = x @ Wih.t() + bih
    gh = h @ Whh.t() + bhh
    r = torch.sigmoid(gi[..., :H] + gh[..., :H])
    z = torch.sigmoid(gi[..., H:2 * H] + gh[..., H:2 * H])
    n = torch.tanh(gi[..., 2 * H:] + r * gh[..., 2 * H:])
    return (1 - z) * n + z * h


class TGRU(nn.Module):
    def __init__(self, V, H):
        super().__init__()
        self.H, self.V = H, V
        b = 1.0 / math.sqrt(H)
        self.emb = nn.Embedding(V, H)
        self.W_ih = nn.Parameter(torch.empty(3 * H, H).uniform_(-b, b))
        self.W_hh = nn.Parameter(torch.empty(3 * H, H).uniform_(-b, b))
        self.b_ih = nn.Parameter(torch.zeros(3 * H))
        self.b_hh = nn.Parameter(torch.zeros(3 * H))
        self.head = nn.Linear(H, V)
        self._st = {}          # built lazily so state lives on the parameter's device
        self.hp_ready = False

    def tern_params(self):
        return [("W_ih", self.W_ih), ("W_hh", self.W_hh), ("head", self.head.weight)]

    def state(self, n, p):
        s = self._st.get(n)
        if s is None or s.changes.device != p.device:
            s = TernaryState(p)
            self._st[n] = s
        return s

    def forward(self, x):
        e = self.emb(x)                       # (B, T, H) float, excluded from pool
        Wih = self.state("W_ih", self.W_ih).eff(self.W_ih)
        Whh = self.state("W_hh", self.W_hh).eff(self.W_hh)
        h = torch.zeros(e.shape[0], self.H, device=e.device, dtype=e.dtype)
        outs = []
        for t in range(e.shape[1]):
            h = gru_cell(e[:, t], h, Wih, Whh, self.b_ih, self.b_hh, self.H)
            outs.append(h)
        hh = torch.stack(outs, dim=1)         # (B, T, H)
        Whead = self.state("head", self.head.weight).eff(self.head.weight)
        return F.linear(hh, Whead, self.head.bias)

    def commit_all(self):
        for n, p in self.tern_params():
            self.state(n, p).commit(p)

    def assign_hp(self, arm, rng):
        k_total = int(K_FRAC * sum(p.numel() for _, p in self.tern_params()))
        for n, p in self.tern_params():
            N = p.numel()
            k = int(round(K_FRAC * N))
            ch = self.state(n, p).changes.flatten()
            if arm == "lifetime":
                idx = torch.argsort(ch)[:k]                     # fewest flips
            elif arm == "antirank":
                idx = torch.argsort(ch)[-k:]                    # most flips
            elif arm == "uniform":
                idx = torch.from_numpy(np.linspace(0, N - 1, k).astype(np.int64))
            elif arm == "random":
                idx = torch.from_numpy(rng.choice(N, size=k, replace=False))
            else:
                raise ValueError(arm)
            mask = torch.zeros(N, dtype=torch.bool)
            mask[idx.cpu()] = True
            st = self.state(n, p)
            st.HP = mask.view_as(p).to(p.device)
            st.H = torch.zeros_like(p)
        self.hp_ready = True
        return k_total

    def n_hp(self):
        return sum(int(self.state(n, p).HP.sum()) for n, p in self.tern_params())


def get_batch(data, rng):
    ix = rng.integers(0, len(data) - SEQ - 1, size=BATCH)
    x = torch.stack([data[i:i + SEQ] for i in ix])
    y = torch.stack([data[i + 1:i + SEQ + 1] for i in ix])
    return x, y


def evaluate(model, data, V):
    """Non-overlapping crops over the valid slice, batched (batch size = BATCH), all bytes counted."""
    model.eval()
    starts = list(range(0, len(data) - SEQ - 1, SEQ))
    tot_bits, tot_n = 0.0, 0
    with torch.no_grad():
        for i in range(0, len(starts), BATCH):
            chunk = starts[i:i + BATCH]
            x = torch.stack([data[s:s + SEQ] for s in chunk])
            y = torch.stack([data[s + 1:s + SEQ + 1] for s in chunk])
            logits = model(x)
            nll = F.cross_entropy(logits.reshape(-1, V), y.reshape(-1), reduction="sum") / math.log(2.0)
            tot_bits += float(nll)
            tot_n += int(y.numel())
    model.train()
    return tot_bits / max(tot_n, 1)


def smoke_gru_equivalence(V, H, dev):
    """Manual cell vs nn.GRU on identical weights — must match or we exit loudly."""
    torch.manual_seed(0)
    ref = nn.GRU(H, H, batch_first=True).to(dev).double()
    x = torch.randn(4, 7, H, device=dev, dtype=torch.float64)
    with torch.no_grad():
        want, _ = ref(x)
        Wih = ref.weight_ih_l0.detach().clone()
        Whh = ref.weight_hh_l0.detach().clone()
        bih = ref.bias_ih_l0.detach().clone()
        bhh = ref.bias_hh_l0.detach().clone()
        h = torch.zeros(4, H, device=dev, dtype=torch.float64)
        outs = []
        for t in range(x.shape[1]):
            h = gru_cell(x[:, t], h, Wih, Whh, bih, bhh, H)
            outs.append(h)
        got = torch.stack(outs, dim=1)
    err = float((want - got).abs().max())
    print(f"[check] manual GRU cell vs nn.GRU max|err| = {err:.3e}")
    if err > 1e-6:
        print("FAIL: manual cell does not match nn.GRU semantics")
        sys.exit(1)
    return err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    t_warm, t_main, seeds = (T_WARM, T_MAIN, SEEDS)
    if args.smoke:
        t_warm, t_main, seeds = 40, 80, [1]

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    OUT.mkdir(parents=True, exist_ok=True)

    print(f"[cfg] device={dev} warm={t_warm} main={t_main} seeds={seeds} k_frac={K_FRAC}")
    corpus, files = build_corpus()
    chars = sorted(set(corpus))
    stoi = {c: i for i, c in enumerate(chars)}
    V = len(chars)
    ids = torch.tensor([stoi[c] for c in corpus], dtype=torch.long)
    cut = int(len(ids) * 0.9)
    train_ids, valid_ids = ids[:cut].to(dev), ids[cut:].to(dev)
    print(f"[corpus] files={len(files)} bytes={len(corpus)} vocab={V} "
          f"train={len(train_ids)} valid={len(valid_ids)}")

    eq = smoke_gru_equivalence(min(V, 32), 32, dev) if args.smoke else None

    results = {"config": {"seq": SEQ, "batch": BATCH, "commit_every": C_COMMIT, "hidden": HID,
                          "lr": LR, "k_frac": K_FRAC, "t_warm": t_warm, "t_main": t_main,
                          "seeds": seeds, "arms": ARMS, "margin": MARGIN,
                          "corpus_bytes": len(corpus), "corpus_files": len(files), "vocab": V,
                          "gru_equiv_max_err": eq},
               "seeds": {}, "verdict": None}

    torch.manual_seed(0)
    for seed in seeds:
        t0 = time.time()
        torch.manual_seed(seed)
        model = TGRU(V, HID).to(dev)
        opt = torch.optim.Adam(model.parameters(), lr=LR)
        rng = np.random.default_rng(seed * 7 + 1)
        for step in range(t_warm):
            x, y = get_batch(train_ids, rng)
            loss = F.cross_entropy(model(x).view(-1, V), y.view(-1))
            opt.zero_grad(); loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), CLIP)
            opt.step()
            if (step + 1) % C_COMMIT == 0:
                model.commit_all()
        model.commit_all()
        warm_bpb = evaluate(model, valid_ids, V)
        warm_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        ch = {n: model.state(n, p).changes.clone() for n, p in model.tern_params()}
        print(f"[seed {seed}] warmup done bpb={warm_bpb:.5f} "
              f"commits={model.state('W_ih', model.W_ih).n_commits} ({time.time() - t0:.0f}s)")

        row = {"warmup_bpb": round(warm_bpb, 6), "arms": {}}
        for arm in ARMS:
            torch.manual_seed(seed)
            model.load_state_dict(warm_state)
            for n, p in model.tern_params():
                st = model.state(n, p)
                st.changes = ch[n].clone()
                st.HP = torch.zeros_like(p, dtype=torch.bool)
                st.H = torch.zeros_like(p)
                st.Q, st.s = ternarize(p)
            k = model.assign_hp(arm, np.random.default_rng(seed * 13 + 5))
            opt = torch.optim.Adam(model.parameters(), lr=LR)     # identical fresh optimizer, all arms
            rng = np.random.default_rng(seed * 7 + 1)             # identical data order, all arms
            curve = []
            ta = time.time()
            for step in range(t_main):
                x, y = get_batch(train_ids, rng)
                loss = F.cross_entropy(model(x).view(-1, V), y.view(-1))
                opt.zero_grad(); loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), CLIP)
                opt.step()
                if (step + 1) % C_COMMIT == 0:
                    model.commit_all()
                if (step + 1) % EVAL_EVERY == 0:
                    curve.append([step + 1, round(evaluate(model, valid_ids, V), 6)])
            model.commit_all()
            final = evaluate(model, valid_ids, V)
            row["arms"][arm] = {"final_bpb": round(final, 6), "hp_slots": model.n_hp(),
                                "curve": curve, "secs": round(time.time() - ta, 1)}
            print(f"[seed {seed}] arm={arm:8s} final_bpb={final:.5f} hp={model.n_hp()} "
                  f"({time.time() - ta:.0f}s)", flush=True)
        results["seeds"][str(seed)] = row

    # frozen gates
    pairs = []
    for seed in seeds:
        a = results["seeds"][str(seed)]["arms"]
        if "lifetime" in a and "random" in a:
            l, r = a["lifetime"]["final_bpb"], a["random"]["final_bpb"]
            pairs.append({"seed": seed, "lifetime": l, "random": r, "rel_improvement": (r - l) / r})
    if pairs:
        mean_rel = float(np.mean([p["rel_improvement"] for p in pairs]))
        wins = sum(1 for p in pairs if p["rel_improvement"] > 0)
        need = math.ceil(2 / 3 * len(pairs))
        keep = mean_rel >= MARGIN and wins >= need
        verdict = {"rule": f"KEEP iff mean_rel>={MARGIN} and wins>={need}/{len(pairs)}",
                   "mean_rel_improvement": round(mean_rel, 6),
                   "wins": wins, "n_pairs": len(pairs), "pairs": pairs,
                   "verdict": "KEEP" if keep else "KILL",
                   "secondary_antirank_vs_lifetime": {
                       str(s): round(results["seeds"][str(s)]["arms"]["antirank"]["final_bpb"]
                                     - results["seeds"][str(s)]["arms"]["lifetime"]["final_bpb"], 6)
                       for s in seeds if "antirank" in results["seeds"][str(s)]["arms"]}}
        results["verdict"] = verdict
        print(f"[VERDICT] {verdict['verdict']} mean_rel={mean_rel:+.5f} wins={wins}/{len(pairs)}")

    (OUT / "results.json").write_text(json.dumps(results, indent=2))
    print(f"[wrote] {OUT / 'results.json'}")


if __name__ == "__main__":
    main()
