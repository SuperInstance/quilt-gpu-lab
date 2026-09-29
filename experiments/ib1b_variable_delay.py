#!/usr/bin/env python3
"""IB1b — the fly-rule under VARIABLE delay + NONLINEAR structure (IB1a hardened).

Hardening vs IB1a (KEEP; results/ib1a_fly_rule.json), everything else frozen at
IB1a values (encoder, k-WTA, V, eps, eta, lambda, decay, T, contexts, seeds):
  1. Variable delay: each receipt arrives d ~ Uniform{1..5} steps after its
     action, resampled per receipt. No timestamps, no delay clock — the
     per-action eligibility trace is the only bridge over the jitter.
  2. Nonlinear world: correct(x) = argmax(ReLU(x@W1)@W2), W1 50x16, W2 16x8,
     frozen standard normals per seed (IB1a was linear argmax).

Arms: A fly-rule (order-gated delta-broadcast spent on PRE-coincidences held in
per-action eligibility traces) | B no-third-factor (identical trace machinery,
delta := constant +1 — no reward information enters plasticity) | C order-swapped
(each delta is banked and spent on LATER coincidences via a decaying delta-trace;
receipt ticks themselves spend nothing) | D matched backprop with replay (numpy
manual backprop + Adam, same variable-delay receipt schedule — the replay buffer
is its stand-in for the trace; delayed by the same uniform 1-5 jitter).

NO torch anywhere (system numpy only; GPU belongs to K2). D's gradients are
hand-derived and finite-difference checked (--gradcheck) before the fire.

Gate (frozen in proposals/runs/IB1b-plan.md before any IB1b code existed):
  KEEP iff A-B >= 0.05 AND A-C >= 0.05 (train reward, last 200 steps, 3-seed mean).
  A vs D: reported honestly, ungated.
Receipt: results/ib1b_variable_delay.json + stdout block.
"""
import json, os, time
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(HERE, "results")
D_CTX, N_KC, K_ACTIVE = 50, 2000, 160
N_ACTIONS, T_TOTAL = 8, 600
D_MIN, D_MAX = 1, 5            # receipt delay ~ Uniform{1..5}, resampled per receipt
H_WORLD = 16                   # hidden width of the frozen world MLP (nonlinear structure)
EPS, ETA, LAM, DECAY = 0.1, 0.05, 0.9, 2e-4
LAM_DELTA = 0.9                # decay of arm C's banked delta-trace (per non-receipt tick)
N_TRAIN_CTX, N_EVAL_CTX = 200, 100
SEEDS = (2718, 42, 1337)
GATE_MARGIN = 0.05
CHANCE = 1 / N_ACTIONS * 0.8 + (1 - 1 / N_ACTIONS) * 0.2   # 0.275


def make_world(rng):
    """Nonlinear correct-action structure: argmax(ReLU(x@W1)@W2), frozen per seed."""
    W1 = rng.normal(size=(D_CTX, H_WORLD))
    W2 = rng.normal(size=(H_WORLD, N_ACTIONS))
    def correct(x):
        return int(np.argmax(np.maximum(0.0, x @ W1) @ W2))
    def reward(x, a):
        c = correct(x)
        return 1.0 if (rng.random() < 0.8 if a == c else rng.random() < 0.2) else 0.0
    return correct, reward


def context(rng, active=6):
    x = np.zeros(D_CTX)
    x[rng.choice(D_CTX, active, replace=False)] = rng.normal(size=active)
    return x


def make_encoder(rng):
    W = rng.normal(size=(N_KC, D_CTX)) * (rng.random((N_KC, D_CTX)) < 10 / D_CTX)
    return W / np.maximum(1e-6, np.abs(W).sum(1, keepdims=True))


def kwta(W_enc, x):
    h = np.maximum(0.0, W_enc @ x)
    thr = np.partition(h, -K_ACTIVE)[-K_ACTIVE]
    return (h >= max(thr, 1e-9)) * h


class FlyBrain:
    """Per-action eligibility traces; plasticity strictly gated on the receipt
    (the third factor). Arms differ ONLY in what the delta is spent on:
      A: immediately, on pre-coincidences (trace contents through t-1).
      B: nothing — delta is replaced by the constant +1 (no reward information).
      C: banked and spent on LATER coincidences (anti-causal)."""
    def __init__(self, rng, arm):
        self.arm = arm
        self.W_enc = make_encoder(rng)
        self.V = np.zeros((N_KC, N_ACTIONS))
        self.E = np.zeros((N_KC, N_ACTIONS))   # per-action eligibility traces
        self.delta_trace = 0.0                 # arm C's banked, decaying delta
    def act(self, kc, rng):
        v = kc @ self.V
        return int(rng.choice(N_ACTIONS) if rng.random() < EPS else int(np.argmax(v)))
    def trace(self, a, kc):
        self.E *= LAM
        self.E[:, a] += kc
        if self.arm == "B":                    # no third factor: delta := +1, every tick
            self.V[:, a] += ETA * self.E[:, a]
            np.clip(self.V, -2.0, 2.0, out=self.V)
    def deliver(self, receipts, ):
        """receipts: list of (a0, r0) arriving this tick. Traces still hold
        coincidences through t-1 (strictly pre-delta)."""
        if self.arm == "A":
            for a0, r0 in receipts:
                v_hat = float((self.V[:, a0] * self.E[:, a0]).sum())
                delta = r0 - v_hat
                self.V[:, a0] += ETA * delta * self.E[:, a0]
        elif self.arm == "C":
            for a0, r0 in receipts:
                v_hat = float((self.V[:, a0] * self.E[:, a0]).sum())
                self.delta_trace += r0 - v_hat   # banked AFTER this tick's coincidence step
    def post_tick(self, a, had_receipt):
        if self.arm == "A":
            self.V *= (1.0 - DECAY)
        elif self.arm == "C":
            if not had_receipt:                # receipt ticks bank only; spend on later coincidences
                self.V[:, a] += ETA * self.delta_trace * self.E[:, a]
                self.delta_trace *= LAM_DELTA
            self.V *= (1.0 - DECAY)


def run(arm, seed):
    rng = np.random.default_rng(seed)
    correct, reward_fn = make_world(rng)
    ctxs = [context(rng) for _ in range(N_TRAIN_CTX)]
    eval_ctxs = [context(rng) for _ in range(N_EVAL_CTX)]
    brain = FlyBrain(rng, arm)
    schedule = {}                              # arrival tick -> list of (a0, r0)
    R_LOG = []
    for t in range(T_TOTAL):
        x = ctxs[rng.integers(len(ctxs))]
        receipts = schedule.pop(t, [])
        brain.deliver(receipts)                              # 1. pre-delta spend (A) / bank (C)
        kc = kwta(brain.W_enc, x)
        a = brain.act(kc, rng)                               # 2. act
        brain.trace(a, kc)                                   # 3. this tick's coincidence
        brain.post_tick(a, had_receipt=bool(receipts))       # 4/5. C spends; homeostasis
        r = reward_fn(x, a)
        R_LOG.append(r)                                      # logged at choice time, all arms
        schedule.setdefault(t + int(rng.integers(D_MIN, D_MAX + 1)), []).append((a, r))
    hits = sum(int(np.argmax(kwta(brain.W_enc, xe) @ brain.V) == correct(xe)) for xe in eval_ctxs)
    return float(np.mean(R_LOG[-200:])), hits / len(eval_ctxs)


# ---------- D: matched backprop with replay (numpy manual backprop, Adam) ----------

class MLP:
    """2000 -> 64 ReLU -> 8. Init mirrors torch.Linear default (kaiming uniform).
    act='tanh' exists ONLY for the finite-difference gradcheck (smooth oracle)."""
    def __init__(self, rng, n_in=N_KC, n_h=64, n_out=N_ACTIONS, act="relu"):
        self.act = act
        lim1 = 1.0 / np.sqrt(n_in)   # torch.Linear default: U(-1/sqrt(fan_in), 1/sqrt(fan_in))
        self.W1 = rng.uniform(-lim1, lim1, size=(n_in, n_h))
        self.b1 = rng.uniform(-lim1, lim1, size=(n_h,))
        lim2 = 1.0 / np.sqrt(n_h)
        self.W2 = rng.uniform(-lim2, lim2, size=(n_h, n_out))
        self.b2 = rng.uniform(-lim2, lim2, size=(n_out,))
        self.params = [self.W1, self.b1, self.W2, self.b2]
        self.m = [np.zeros_like(p) for p in self.params]
        self.v = [np.zeros_like(p) for p in self.params]
        self.step_n = 0
    def _act(self, q):
        return np.maximum(0.0, q) if self.act == "relu" else np.tanh(q)
    def _act_d(self, q, h):
        return (q > 0).astype(float) if self.act == "relu" else (1.0 - h * h)
    def forward(self, H):
        q1 = H @ self.W1 + self.b1
        h1 = self._act(q1)
        return q1, h1, h1 @ self.W2 + self.b2
    def grads(self, H, A, R):
        """MSE on the taken action's q toward r (IB1a-D's exact objective)."""
        B = len(A)
        q1, h1, z = self.forward(H)
        idx = np.arange(B)
        pred = z[idx, A]
        dpred = 2.0 * (pred - R) / B
        dz = np.zeros_like(z); dz[idx, A] = dpred
        gW2 = h1.T @ dz; gb2 = dz.sum(0)
        dq1 = (dz @ self.W2.T) * self._act_d(q1, h1)
        gW1 = H.T @ dq1; gb1 = dq1.sum(0)
        return [gW1, gb1, gW2, gb2]
    def adam(self, g, lr=1e-3, b1=0.9, b2=0.999, eps=1e-8):
        self.step_n += 1
        for p, g_, m_, v_ in zip(self.params, g, self.m, self.v):
            m_ *= b1; m_ += (1 - b1) * g_
            v_ *= b2; v_ += (1 - b2) * (g_ * g_)
            mhat = m_ / (1 - b1 ** self.step_n)
            vhat = v_ / (1 - b2 ** self.step_n)
            p -= lr * mhat / (np.sqrt(vhat) + eps)


def gradcheck(rng, act="relu", n_in=6, n_h=5, n_out=3, B=4, eps=1e-6):
    """Finite-difference verification of the manual backprop (pre-fire gate).
    act='tanh': smooth oracle, rigorous everywhere. act='relu': rejection-sample
    the batch until every |q1| > 1e-3 so no unit straddles the kink (the ReLU
    subgradient is correct there; finite differences are not)."""
    net = MLP(rng, n_in, n_h, n_out, act=act)
    H = rng.normal(size=(B, n_in))
    for _ in range(200):
        q1 = H @ net.W1 + net.b1
        if np.abs(q1).min() > 1e-3:
            break
        H = rng.normal(size=(B, n_in))
    A = rng.integers(0, n_out, size=B)
    R = rng.normal(size=(B,))
    def loss():
        _, _, z = net.forward(H)
        idx = np.arange(B)
        return float(np.mean((z[idx, A] - R) ** 2))
    g = net.grads(H, A, R)
    worst = 0.0
    for p, g_ in zip(net.params, g):
        coords = list(np.ndindex(p.shape))   # works for 0-d biases too (reshape(-1) on 0-d copies!)
        for idx in [coords[j] for j in rng.choice(len(coords), size=min(12, len(coords)), replace=False)]:
            old = p[idx]
            p[idx] = old + eps; lp = loss()
            p[idx] = old - eps; lm = loss()
            p[idx] = old
            num = (lp - lm) / (2 * eps)
            ana = float(g_[idx])
            denom = max(1e-8, abs(num), abs(ana))
            worst = max(worst, abs(num - ana) / denom)
    return worst


def run_backprop(seed):
    rng = np.random.default_rng(seed)
    correct, reward_fn = make_world(rng)
    ctxs = [context(rng) for _ in range(N_TRAIN_CTX)]
    eval_ctxs = [context(rng) for _ in range(N_EVAL_CTX)]
    W_enc = make_encoder(np.random.default_rng(seed + 1))   # frozen encoder, IB1a convention
    net = MLP(np.random.default_rng(seed + 2))
    pending = {}                               # arrival tick -> list of (h, a0)
    buf = []; R_LOG = []
    for t in range(T_TOTAL):
        x = ctxs[rng.integers(len(ctxs))]
        for h0, a0, r0 in pending.pop(t, []):  # same variable-delay schedule as the fly arms
            buf.append((h0, a0, r0))
        kc = kwta(W_enc, x)
        _, _, q = net.forward(kc[None, :])
        q = q[0]
        a = int(rng.choice(N_ACTIONS) if rng.random() < EPS else int(np.argmax(q)))
        r = reward_fn(x, a)
        R_LOG.append(r)
        pending.setdefault(t + int(rng.integers(D_MIN, D_MAX + 1)), []).append((kc, a, r))
        if len(buf) > 32:
            idx = rng.integers(len(buf), size=16)
            H = np.stack([buf[i][0] for i in idx])
            A = np.array([buf[i][1] for i in idx])
            R = np.array([buf[i][2] for i in idx], dtype=np.float64)
            net.adam(net.grads(H, A, R))
    hits = 0
    for xe in eval_ctxs:
        _, _, qe = net.forward(kwta(W_enc, xe)[None, :])
        hits += int(int(np.argmax(qe[0])) == correct(xe))
    return float(np.mean(R_LOG[-200:])), hits / len(eval_ctxs)


def main():
    t0 = time.time()
    out = {"experiment": "IB1b fly-rule under variable delay + nonlinear structure",
           "hardening_vs_ib1a": ["receipt delay ~ Uniform{1..5} resampled per receipt (was fixed 3)",
                                  "correct-action = argmax(ReLU(x@W1 50x16)@W2 16x8), frozen (was linear argmax)",
                                  "credit bridge = per-action eligibility traces only (no timestamps)",
                                  "D matched under the same variable-delay schedule (numpy manual backprop, no torch)"],
           "rule": "frozen sparse PN->KC, k-WTA, K.V, order-gated delta-broadcast, "
                   "per-action eligibility traces (lam=0.9), RW delta, RW extinction, homeostatic decay",
           "chance": round(CHANCE, 4), "seeds": SEEDS, "arms": {}}
    for arm, desc in (("A", "fly-rule"), ("B", "no-third-factor"), ("C", "order-swapped")):
        rs, hs = zip(*(run(arm, s) for s in SEEDS))
        out["arms"][f"{arm}_{desc}"] = {"train_reward_last200": round(float(np.mean(rs)), 4),
                                        "eval_transfer": round(float(np.mean(hs)), 4),
                                        "per_seed": [round(float(x), 4) for x in rs]}
        print(f"[IB1b] {arm} ({desc}): reward={np.mean(rs):.4f} transfer={np.mean(hs):.4f}", flush=True)
    rs, hs = zip(*(run_backprop(s) for s in SEEDS))
    out["arms"]["D_backprop"] = {"train_reward_last200": round(float(np.mean(rs)), 4),
                                 "eval_transfer": round(float(np.mean(hs)), 4),
                                 "per_seed": [round(float(x), 4) for x in rs]}
    print(f"[IB1b] D (backprop+replay, same delay): reward={np.mean(rs):.4f} transfer={np.mean(hs):.4f}", flush=True)
    A = out["arms"]["A_fly-rule"]["train_reward_last200"]
    B = out["arms"]["B_no-third-factor"]["train_reward_last200"]
    C = out["arms"]["C_order-swapped"]["train_reward_last200"]
    D = out["arms"]["D_backprop"]["train_reward_last200"]
    verdict = "KEEP" if (A - B >= GATE_MARGIN and A - C >= GATE_MARGIN) else "KILL"
    out.update({"verdict": verdict,
                "gate": f"A-B>={GATE_MARGIN} and A-C>={GATE_MARGIN} (train reward, 3-seed mean; frozen in proposals/runs/IB1b-plan.md)",
                "deltas": {"A-B": round(A - B, 4), "A-C": round(A - C, 4)},
                "A_vs_D_ungated": {"A": A, "D": D},
                "sanity_annotation": ("world-too-hard: D at/below chance+0.02 — arm separation is weak evidence"
                                      if D <= CHANCE + 0.02 else "D learned (above chance+0.02); world is learnable"),
                "seconds": round(time.time() - t0, 1)})
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "ib1b_variable_delay.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    if "--gradcheck" in __import__("sys").argv:
        w_tanh = gradcheck(np.random.default_rng(0), act="tanh")
        w_relu = gradcheck(np.random.default_rng(1), act="relu")
        worst = max(w_tanh, w_relu)
        print(f"[gradcheck] tanh oracle worst rel err: {w_tanh:.2e}")
        print(f"[gradcheck] relu (kink-free points) worst rel err: {w_relu:.2e}")
        print(f"[gradcheck] worst: {worst:.2e} ({'PASS' if worst < 1e-4 else 'FAIL'})")
        raise SystemExit(0 if worst < 1e-4 else 1)
    main()
