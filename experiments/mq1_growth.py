#!/usr/bin/env python3
"""MQ1 — Growth-vs-Fixed (scalar arm). Pre-reg: proposals/runs/MQ1-growth-vs-fixed.md

Two arms, equal final params, equal steps:
  fixed: MLP(1,[8,8,1]) born full-size
  grown: starts MLP(1,[2,2,1]), grafts +1 neuron on plateau until [8,8]

Quilt instrumentation: per-run Tape (TICK per eval, prefix-GC via forget),
verify() at end; at every graft, a fresh audit-window tape + stochastic
rational auditor measures gradient-fabric drift across the graft.

Run: python3 experiments/mq1_growth.py            (from quilt-gpu-lab root)
"""
import json
import math
import os
import random
import sys
import time

sys.path.insert(0, "/home/eileen/projects/micrograd-quilt")
from quilt import auditor, tape  # noqa: E402
from quilt import engine as qengine  # noqa: E402
from quilt.engine import Value  # noqa: E402

STEPS = 3000
BATCH = 32
EVAL_EVERY = 50
PLATEAU_WINDOW = 4        # evals (~200 steps)
PLATEAU_EPS = 0.02        # relative improvement threshold
MAX_WIDTH = 8
OUT = os.path.join(os.path.dirname(__file__), "..", "results", "mq1")
CONTROL_STEPS = {400, 1600, 2800}


# -- quilt-Value MLP (micrograd/nn.py structure, quilt engine underneath) ----

class Neuron:
    def __init__(self, nin, nonlin=True):
        self.w = [Value(random.uniform(-1, 1)) for _ in range(nin)]
        self.b = Value(0)
        self.nonlin = nonlin

    def __call__(self, x):
        act = sum((wi * xi for wi, xi in zip(self.w, x)), self.b)
        return act.tanh() if self.nonlin else act

    def parameters(self):
        return self.w + [self.b]


class Layer:
    def __init__(self, nin, nout, nonlin=True):
        self.neurons = [Neuron(nin, nonlin) for _ in range(nout)]

    def __call__(self, x):
        out = [n(x) for n in self.neurons]
        return out[0] if len(out) == 1 else out

    def parameters(self):
        return [p for n in self.neurons for p in n.parameters()]


def graft_neuron(model, idx):
    """Append one neuron to hidden layer `idx` — with the RIGHT input width,
    and extend every neuron in the next layer by one fresh input weight.
    (The 21:20 bug: Neuron(1) grafted into a layer fed by 8 outputs, and the
    downstream layer never grew an input -> grown arm scored 0.1135 vs fixed
    0.0280. Dimensional, not scientific.)"""
    layers = model.layers
    nin = 1 if idx == 0 else len(layers[idx - 1].neurons)
    layers[idx].neurons.append(Neuron(nin, True))
    if idx + 1 < len(layers):
        for n in layers[idx + 1].neurons:
            n.w.append(Value(random.uniform(-1, 1)))


class MLP:
    def __init__(self, nin, nouts):
        sz = [nin] + nouts
        self.layers = [Layer(sz[i], sz[i + 1], nonlin=i < len(nouts) - 2)
                       for i in range(len(nouts))]

    def __call__(self, x):
        if isinstance(x, (int, float)):
            x = [x]
        for layer in self.layers:
            x = layer(x)
        return x

    def parameters(self):
        return [p for l in self.layers for p in l.parameters()]


# -- data ---------------------------------------------------------------------

def make_data():
    rng = random.Random(42)  # frozen dataset seed — shared by every run
    xs = [rng.uniform(-math.pi, math.pi) for _ in range(300)]
    ys = [math.sin(x) + rng.gauss(0, 0.15) for x in xs]
    return xs[:240], ys[:240], xs[240:], ys[240:]


def mse(model, X, Y):
    return sum((model(x).data - y) ** 2 for x, y in zip(X, Y)) / len(X)


def sgd_step(model, xb, yb, lr):
    losses = [((model(x) - y) ** 2) for x, y in zip(xb, yb)]
    loss = sum(losses[1:], losses[0]) * (1.0 / len(losses))
    for p in model.parameters():
        p.grad = 0.0
    loss.backward()
    for p in model.parameters():
        p.data -= lr * p.grad
    return loss.data


def count_params(model):
    return len(model.parameters())


def audit_at(model, X, Y, step, seed, kind="graft"):
    """One audited forward+backward (graft or matched control). Fresh tape."""
    t = tape.Tape()
    with tape.attach(t):
        for p in model.parameters():
            t.bind(p)  # weights predate this window — bind them so exact_values can bootstrap
        i = random.randrange(len(X) - BATCH)
        xb, yb = X[i:i + BATCH], Y[i:i + BATCH]
        losses = [((model(x) - y) ** 2) for x, y in zip(xb, yb)]
        loss = sum(losses[1:], losses[0]) * (1.0 / len(losses))
        t.tick(step, loss)
        loss.backward()
    grads = {v.id: v.grad for v in loss.topo()}
    if math.isnan(loss.data) or any(math.isnan(g) for g in grads.values()):
        # divergence: Fraction(NaN) is unrepresentable — flag it, don't crash the sweep
        return {"step": step, "kind": kind, "nan": True, "mean": None,
                "ci": None, "worst": None, "n_sampled": 0, "n_nodes": 0}
    rep = auditor.audit(t.rows, grads, mode="stochastic", seed=seed)
    return {"step": step, "kind": kind, "nan": False, "mean": rep.mean, "ci": list(rep.ci95),
            "worst": rep.worst[1] if rep.worst else None,
            "n_sampled": rep.n_sampled, "n_nodes": rep.n_nodes}


def run_arm(arm, seed, lr, Xtr, Ytr, Xva, Yva):
    random.seed(seed)
    Value.reset_ids()
    t = tape.Tape()
    model = MLP(1, [8, 8, 1]) if arm == "fixed" else MLP(1, [2, 2, 1])
    history, grafts, audits = [], [], []
    diverged_at = None
    growing = arm == "grown"

    with tape.attach(t):
        for step in range(STEPS):
            i = random.randrange(len(Xtr) - BATCH)
            try:
                with qengine.quiet():  # bulk ops stay out of the WAL; TICKs carry the chain
                    loss = sgd_step(model, Xtr[i:i + BATCH], Ytr[i:i + BATCH], lr)
            except ValueError:
                # divergence: engine.__pow__ does Fraction(NaN) ** n inside the step
                diverged_at = step
                break
            if math.isnan(loss) or math.isinf(loss):
                diverged_at = step
                break

            if step % EVAL_EVERY == 0 or step == STEPS - 1:
                v = mse(model, Xva, Yva)
                history.append({"step": step, "train": loss, "val": v,
                                "params": count_params(model)})
                t.tick(step, Value(v))
                if len(t.rows) > 50_000:
                    t.forget(len(t.rows) - 5_000)  # prefix GC, chain intact

                # matched control audits (transcendental drift floor, both arms)
                if step in CONTROL_STEPS:
                    audits.append(audit_at(model, Xtr, Ytr, step, seed, "control"))

                # growth: plateau trigger, graft layer0 then layer1, to width 8
                if growing and len(history) > PLATEAU_WINDOW:
                    w = [h["val"] for h in history[-(PLATEAU_WINDOW + 1):]]
                    prev = sum(w[:-1]) / len(w[:-1])
                    if prev > 0 and (prev - w[-1]) / prev < PLATEAU_EPS:
                        target = 0 if len(model.layers[0].neurons) < MAX_WIDTH else 1
                        if len(model.layers[target].neurons) < MAX_WIDTH:
                            graft_neuron(model, target)
                            grafts.append({"step": step, "layer": target,
                                           "width": len(model.layers[target].neurons),
                                           "val": v, "params": count_params(model)})
                            audits.append(audit_at(model, Xtr, Ytr, step, seed, "graft"))

    ok = t.verify()
    final = history[-1]
    return {"arm": arm, "seed": seed, "lr": lr, "tape_verified": ok,
            "diverged_at": diverged_at,
            "history": history, "grafts": grafts, "audits": audits,
            "final_val": final["val"], "final_params": final["params"]}


def job(args):
    arm, seed, lr, = args
    Xtr, Ytr, Xva, Yva = DATA
    t0 = time.time()
    r = run_arm(arm, seed, lr, Xtr, Ytr, Xva, Yva)
    r["seconds"] = round(time.time() - t0, 1)
    print(f"  {arm} seed={seed} lr={lr}: val={r['final_val']:.4f} "
          f"params={r['final_params']} grafts={len(r['grafts'])} "
          f"tape_ok={r['tape_verified']} ({r['seconds']}s)", flush=True)
    return r


DATA = make_data()

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    Xtr, Ytr, Xva, Yva = DATA
    print(f"MQ1 scalar arm — 240/60 split, batch={BATCH}, steps={STEPS}")

    # 1) LR grid on the FIXED arm alone (train loss), grown inherits the winner
    grid = [job(("fixed", 0, lr)) for lr in (0.01, 0.05, 0.1)]
    clean = [g for g in grid if g["diverged_at"] is None] or grid
    best = min(clean, key=lambda r: r["history"][-1]["train"])
    lr = best["lr"]
    print(f"LR grid -> winner lr={lr} (train={best['history'][-1]['train']:.4f})"
          f"{' [divergence noted in grid]' if len(clean) != len(grid) else ''}", flush=True)

    # 2) 5 seeds per arm at the shared lr (sequential: pool pickling was the crash vector)
    jobs = [("fixed", s, lr) for s in range(5)] + [("grown", s, lr) for s in range(5)]
    results = [job(j) for j in jobs]

    fixed = sorted(r["final_val"] for r in results if r["arm"] == "fixed")
    grown = sorted(r["final_val"] for r in results if r["arm"] == "grown")
    med_f = fixed[len(fixed) // 2]
    med_g = grown[len(grown) // 2]
    ratio = med_g / med_f
    verdict = "GROWN_WINS" if ratio < 0.95 else ("FIXED_WINS" if ratio > 1.05 else "TIE")

    g_drift = [a["mean"] for r in results for a in r["audits"]
               if a["kind"] == "graft" and not a.get("nan")]
    c_drift = [a["mean"] for r in results for a in r["audits"]
               if a["kind"] == "control" and not a.get("nan")]
    med_g = sorted(g_drift)[len(g_drift) // 2] if g_drift else None
    med_c = sorted(c_drift)[len(c_drift) // 2] if c_drift else None
    graft_damage = bool(g_drift and c_drift) and med_g > 2 * med_c

    summary = {
        "experiment": "MQ1-growth-vs-fixed (scalar)",
        "lr": lr, "steps": STEPS, "batch": BATCH,
        "fixed_vals": fixed, "grown_vals": grown,
        "median_fixed": med_f, "median_grown": med_g, "ratio": ratio,
        "verdict": verdict,
        "graft_drift_median": med_g,
        "control_drift_median": med_c,
        "fabric_verdict": "GRAFT_DAMAGE" if graft_damage else "FABRIC_INTACT",
        "total_grafts": sum(len(r["grafts"]) for r in results),
        "total_controls": sum(1 for r in results for a in r["audits"] if a["kind"] == "control"),
    }
    with open(os.path.join(OUT, "mq1_scalar_results.json"), "w") as f:
        json.dump({"summary": summary, "runs": results}, f, indent=2)
    print(json.dumps(summary, indent=2))
