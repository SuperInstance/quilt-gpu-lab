#!/usr/bin/env python3
"""IB1a — the fly-rule, no backprop, vs three controls (delayed-receipt bandit).

Rule (il-science 2026-09-28, primary-sourced): frozen random sparse encoder
(PN 50 -> KC 2000, ~10 PN/KC), k-WTA sparse code, K.V value (~8k params),
plasticity STRICTLY gated on pre-before-delta temporal order (Hige 2015),
delta as BROADCAST receipt-event (6% direct contact — Takemura 2017),
eligibility traces = our wager, RW-style extinction (Felsenberg 2017),
small homeostatic decay. NO backprop.

Arms: A fly-rule | B no-third-factor (Hebbian pre-only) | C order-swapped
(update uses post-delta eligibility — anti-causal) | D matched backprop
(frozen KC features -> 2-layer MLP, Adam, replay; reported, ungated).

Gates (frozen in proposals/runs/IB1a-plan.md):
  KEEP  iff A beats B by >=0.05 AND A beats C by >=0.05 (final train reward,
         mean over 3 seeds).
  A vs D: reported honestly, ungated.
Receipt: results/ib1a_fly_rule.json + stdout block.
"""
import json, os, time
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(HERE, "results")
D_CTX, N_KC, K_ACTIVE = 50, 2000, 160
N_ACTIONS, DELAY, T_TOTAL = 8, 3, 600
EPS, ETA, LAM, DECAY = 0.1, 0.05, 0.9, 2e-4
N_TRAIN_CTX, N_EVAL_CTX = 200, 100
SEEDS = (2718, 42, 1337)
GATE_MARGIN = 0.05

def make_world(rng):
    W_map = rng.normal(size=(D_CTX, N_ACTIONS))
    def correct(x): return int(np.argmax(x @ W_map))
    def reward(x, a):
        c = correct(x)
        return 1.0 if (rng.random() < 0.8 if a == c else rng.random() < 0.2) else 0.0
    return correct, reward

def context(rng, active=6):
    x = np.zeros(D_CTX); x[rng.choice(D_CTX, active, replace=False)] = rng.normal(size=active)
    return x

class FlyBrain:
    """Eligibility = instantaneous KC response at action time (pre-before-delta,
    by construction: the action precedes its receipt)."""
    def __init__(self, rng, arm):
        self.arm = arm
        W = rng.normal(size=(N_KC, D_CTX)) * (rng.random((N_KC, D_CTX)) < 10 / D_CTX)
        self.W_enc = W / np.maximum(1e-6, np.abs(W).sum(1, keepdims=True))
        self.V = np.zeros((N_KC, N_ACTIONS))
        self.pending = []; self.hist = {}
    def kc(self, x):
        h = np.maximum(0.0, self.W_enc @ x)
        thr = np.partition(h, -K_ACTIVE)[-K_ACTIVE]
        return (h >= max(thr, 1e-9)) * h
    def act(self, x, rng):
        v = self.kc(x) @ self.V
        return int(rng.choice(N_ACTIONS) if rng.random() < EPS else np.argmax(v))
    def note(self, t, action, elig):
        self.hist[t] = (action, elig.copy())
    def learn(self, t, x, r):
        if self.arm in ("A", "C"):
            self.pending.append((t, r))
            for (t0, r0) in [p for p in self.pending if p[0] == t - DELAY]:
                a0, e_pre = self.hist.get(t - DELAY, (0, np.zeros(N_KC)))
                e = e_pre if self.arm == "A" else self.kc(x)  # C: post-delta eligibility (anti-causal)
                v_hat = float((self.V[:, a0] * e).sum())
                delta = r0 - v_hat
                self.V[:, a0] += ETA * delta * e
            self.pending = [p for p in self.pending if p[0] > t - DELAY]
            self.V *= (1.0 - DECAY)
        elif self.arm == "B":  # no third factor: Hebbian pre-only, every step
            a0, e = self.hist.get(t, (0, self.kc(x)))
            self.V[:, a0] += ETA * e
            self.V = np.clip(self.V, -2.0, 2.0)

def run(arm, seed):
    rng = np.random.default_rng(seed)
    correct, reward_fn = make_world(rng)
    ctxs = [context(rng) for _ in range(N_TRAIN_CTX)]
    eval_ctxs = [context(rng) for _ in range(N_EVAL_CTX)]
    brain = FlyBrain(rng, arm)
    R_LOG = []
    for t in range(T_TOTAL):
        x = ctxs[rng.integers(len(ctxs))]
        a = brain.act(x, rng); brain.note(t, a, brain.kc(x))
        r = reward_fn(x, a)
        brain.learn(t, x, r)
        R_LOG.append(r)
    hits = sum(int(np.argmax(brain.kc(xe) @ brain.V) == correct(xe)) for xe in eval_ctxs)
    return float(np.mean(R_LOG[-200:])), hits / len(eval_ctxs)

def run_backprop(seed):
    import torch, torch.nn as nn
    rng = np.random.default_rng(seed)
    correct, reward_fn = make_world(rng)
    ctxs = [context(rng) for _ in range(N_TRAIN_CTX)]
    eval_ctxs = [context(rng) for _ in range(N_EVAL_CTX)]
    fb = FlyBrain(np.random.default_rng(seed + 1), "D")  # reuse frozen encoder
    net = nn.Sequential(nn.Linear(N_KC, 64), nn.ReLU(), nn.Linear(64, N_ACTIONS))
    opt = torch.optim.Adam(net.parameters(), lr=1e-3)
    buf = []; R_LOG = []
    for t in range(T_TOTAL):
        x = ctxs[rng.integers(len(ctxs))]
        h = fb.kc(x)
        with torch.no_grad():
            q = net(torch.tensor(h, dtype=torch.float32)).numpy()
        a = int(rng.choice(N_ACTIONS) if rng.random() < EPS else int(np.argmax(q)))
        r = reward_fn(x, a); buf.append((h, a, r)); R_LOG.append(r)
        if len(buf) > 32:
            idx = rng.integers(len(buf), size=16)
            H = torch.tensor(np.stack([buf[i][0] for i in idx]), dtype=torch.float32)
            A = torch.tensor([buf[i][1] for i in idx])
            R = torch.tensor([buf[i][2] for i in idx], dtype=torch.float32)
            loss = nn.functional.mse_loss(net(H).gather(1, A[:, None]).squeeze(1), R)
            opt.zero_grad(); loss.backward(); opt.step()
    hits = 0
    with torch.no_grad():
        for xe in eval_ctxs:
            hits += int(net(torch.tensor(fb.kc(xe), dtype=torch.float32)).argmax() == correct(xe))
    return float(np.mean(R_LOG[-200:])), hits / len(eval_ctxs)

def main():
    t0 = time.time()
    out = {"experiment": "IB1a fly-rule (no backprop) vs controls",
           "rule": "frozen sparse PN->KC, k-WTA, K.V, order-gated delta-broadcast, "
                   "eligibility traces, RW extinction, homeostatic decay",
           "seeds": SEEDS, "arms": {}}
    for arm, desc in (("A", "fly-rule"), ("B", "no-third-factor"), ("C", "order-swapped")):
        rs, hs = zip(*(run(arm, s) for s in SEEDS))
        out["arms"][f"{arm}_{desc}"] = {"train_reward_last200": round(float(np.mean(rs)), 4),
                                        "eval_transfer": round(float(np.mean(hs)), 4),
                                        "per_seed": [round(float(x), 4) for x in rs]}
        print(f"[IB1a] {arm} ({desc}): reward={np.mean(rs):.4f} transfer={np.mean(hs):.4f}", flush=True)
    rs, hs = zip(*(run_backprop(s) for s in SEEDS))
    out["arms"]["D_backprop"] = {"train_reward_last200": round(float(np.mean(rs)), 4),
                                 "eval_transfer": round(float(np.mean(hs)), 4),
                                 "per_seed": [round(float(x), 4) for x in rs]}
    print(f"[IB1a] D (backprop): reward={np.mean(rs):.4f} transfer={np.mean(hs):.4f}", flush=True)
    A = out["arms"]["A_fly-rule"]["train_reward_last200"]
    B = out["arms"]["B_no-third-factor"]["train_reward_last200"]
    C = out["arms"]["C_order-swapped"]["train_reward_last200"]
    verdict = "KEEP" if (A - B >= GATE_MARGIN and A - C >= GATE_MARGIN) else "KILL"
    out.update({"verdict": verdict,
                "gate": f"A-B>={GATE_MARGIN} and A-C>={GATE_MARGIN} (train reward, 3-seed mean)",
                "A_vs_D_ungated": {"A": A, "D": out["arms"]["D_backprop"]["train_reward_last200"]},
                "seconds": round(time.time() - t0, 1)})
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "ib1a_fly_rule.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
