#!/usr/bin/env python3
"""ie3 — specialist trunks: sequential specialization vs joint multi-task training.

Pre-registered: proposals/runs/IE3-plan.md (frozen before any IE3 run).
Question: can ONE shared trunk serve TWO specialist heads (wide-field grating
direction + small-field blob direction) without dilution — and does SEQUENTIAL
specialization (blob epochs to a frozen competence gate, then +direction head)
beat JOINT training (both losses summed from step 0)?

Arms (identical sensor, streams, eval):
  A_joint         shared trunk, blob+direction losses summed from epoch 0
  B_sequential    phase 1 blob-only to val r2 >= 0.40 (min 50 / cap 400
                  epochs), then direction head created (fresh init), phase 2
                  both losses until 600 total trunk epochs (A's budget)
  C_split_trunks  independent specialist per family (crew-doctrine baseline)

Sensor stack = IE2 verbatim, imported from ie1_reichardt.py: blob sigma 2/3,
speeds 0.25/0.5, 4 cardinals, densities 8/16/32, tau 2, warmup 12 / kept 48;
grating lambdas 8/16 at the same frozen speeds. Reader = gradient-trained
trunk (4->12->8 tanh, 164 params) + linear heads (8->2), Adam lr 0.01, L2
weight decay 0.01 (IE2 ridge alpha lineage, weights only). Seed base 20260929,
IE2 seed law verbatim (blob ci 0-15, grating ci 100-115; train si 0-2,
val si 3 [B's gate only], test si 0-3 @ offset 100).

Gates (frozen; precedence 1->2->3):
  SPECIALIZATION_WINS  r2_dir_B[32] - r2_dir_A[32] >= 0.15 AND
                       r2_blob_B[32] >= r2_blob_C[32] - 0.05
  else JOINT_OK        at EVERY density: A within 0.05 of the per-density max
                       on BOTH heads
  else DILUTION_CONFIRMS
  Any P1 competence miss / non-finite number / shape assert -> INVALID_HARNESS.

CPU-only numpy (system python3). No GPU lock. Minutes-scale.
"""
import importlib.util
import json
import os
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.normpath(os.path.join(HERE, "..", "results"))

spec = importlib.util.spec_from_file_location("ie1", os.path.join(HERE, "ie1_reichardt.py"))
ie1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ie1)  # main() is __main__-guarded

# ---------------- frozen config (proposals/runs/IE3-plan.md) ----------------
SEED_BASE = 20260929                  # fresh base per plan (IE2 used 20260928)
DENSITIES = ie1.DENSITIES             # (8, 16, 32)
TAU = ie1.TAU_BASELINE                # 2.0 frames
GRAT_SPEEDS = (0.25, 0.5)             # IE2's frozen speed set governs BOTH
                                     # families (IE1 grating speed 1.0 dropped)
WEIGHT_DECAY = 1e-2                   # IE2 ridge alpha lineage -> L2 on W
TRUNK_HIDDEN = (12, 8)                # trunk 4 -> 12 -> 8, tanh incl. output
HEAD_OUT = 2                          # (vx, vy)
TOTAL_EPOCHS = 600                    # trunk-epoch budget per arm (B: p1+p2)
P1_MIN_EPOCHS = 50
P1_MAX_EPOCHS = 400
P1_COMPETENCE_R2 = 0.40               # val blob r2 gate (specialist territory)
ADAM_LR = 1e-2
ADAM_B1, ADAM_B2, ADAM_EPS = 0.9, 0.999, 1e-8

SPEC_MARGIN_DIR = 0.15                # B.dir - A.dir >= this at density 32
SPEC_BLOB_SLACK = 0.05                # B.blob >= C.blob - this at density 32
JOINT_SLACK = 0.05                    # A within this of per-density max, both heads
DENSITY_OF_RECORD = 32

GRAT_CI_BLOCK = 100                   # grating cfg ci 100..115 (blob 0..15)
MODEL_SEED_OFFSET = 500000
ARMS = ("A_joint", "B_sequential", "C_split_trunks")
ARM_INDEX = {a: i for i, a in enumerate(ARMS)}

INTERPRETATIONS = {
    "SPECIALIZATION_WINS": ("schedule is the cure: one trunk serves both "
                            "specialists, but only when specialized first"),
    "JOINT_OK": ("the generalist is viable at this scale: compartmentalized "
                 "heads already prevent IE1-style dilution; schedule irrelevant"),
    "DILUTION_CONFIRMS": ("trunk sharing dilutes under BOTH schedules at this "
                          "scale; split specialists remain the reader doctrine"),
    "INVALID_HARNESS": ("pre-registered failure path fired; per-density data "
                        "booked, no science claim"),
}


# ---------------- data: IE2 sensor stack + seed law, fresh base ----------------
def blob_cfgs():
    """16 cfgs, IE2 enumeration order: sigma x speed x DIR_ORDER."""
    return [dict(sigma=s, v=v, dvec=ie1.DIRS[name])
            for s in ie1.BLOB_SIGMAS for v in ie1.BLOB_SPEEDS
            for name in ie1.DIR_ORDER]


def grat_cfgs():
    """16 cfgs: lambda x speed x DIR_ORDER (speeds frozen to IE2's set)."""
    return [dict(lam=lam, v=v, dvec=ie1.DIRS[name])
            for lam in ie1.GRAT_LAMBDAS for v in GRAT_SPEEDS
            for name in ie1.DIR_ORDER]


def family_frames(n, cfgs, ci_offset, si_list, split_offset):
    """(x, y) over cfgs x si_list. Seed law IE2-verbatim with new base:
    seed = base + 1000*ci + 10*si + split_offset."""
    feats, y = [], []
    for ci0, kw in enumerate(cfgs):
        ci = ci_offset + ci0
        for si in si_list:
            rng = np.random.default_rng(SEED_BASE + 1000 * ci + 10 * si + split_offset)
            n_frames = ie1.WARMUP + ie1.T_FRAMES
            if "sigma" in kw:
                seq = ie1.blob_scene(n, kw["sigma"], kw["v"], kw["dvec"], n_frames, rng)
            else:
                seq = ie1.grating_scene(n, kw["lam"], kw["v"], kw["dvec"], n_frames, rng)
            codes = ie1.fam_codes(seq, TAU)[ie1.WARMUP:]
            feats.append(codes)
            vx, vy = kw["dvec"]
            y.append(np.tile(np.array([vx, vy]), (ie1.T_FRAMES, 1)))
    return np.concatenate(feats), np.concatenate(y)


def build_density(n):
    """All streams for one density. Built ONCE, shared across arms (same objects)."""
    bc, gc = blob_cfgs(), grat_cfgs()
    assert len(bc) == 16 and len(gc) == 16
    data = {}
    for fam, cfgs, off in (("blob", bc, 0), ("grat", gc, GRAT_CI_BLOCK)):
        data[fam] = {
            "train": family_frames(n, cfgs, off, (0, 1, 2), 0),
            "val": family_frames(n, cfgs, off, (3,), 0),
            "test": family_frames(n, cfgs, off, (0, 1, 2, 3), 100),
        }
        assert data[fam]["train"][0].shape == (16 * 3 * ie1.T_FRAMES, 4)
        assert data[fam]["val"][0].shape == (16 * 1 * ie1.T_FRAMES, 4)
        assert data[fam]["test"][0].shape == (16 * 4 * ie1.T_FRAMES, 4)
        assert data[fam]["train"][1].shape == (16 * 3 * ie1.T_FRAMES, 2)
    return data


# ---------------- tiny full-batch MLP: manual backprop + Adam + L2 ----------------
class MLP:
    """Tanh MLP, linear or tanh output. W init N(0,1)/sqrt(fan_in), b zeros."""

    def __init__(self, sizes, rng, out_act):
        assert out_act in ("tanh", "lin") and len(sizes) >= 2
        self.Ws = [rng.standard_normal((a, b)) / np.sqrt(a)
                   for a, b in zip(sizes[:-1], sizes[1:])]
        self.bs = [np.zeros(b) for b in sizes[1:]]
        self.acts = ["tanh"] * (len(sizes) - 2) + [out_act]
        self.t = 0
        self._mW = [np.zeros_like(W) for W in self.Ws]
        self._vW = [np.zeros_like(W) for W in self.Ws]
        self._mb = [np.zeros_like(b) for b in self.bs]
        self._vb = [np.zeros_like(b) for b in self.bs]

    def forward(self, x):
        self._fw = []
        h = x
        for W, b, a in zip(self.Ws, self.bs, self.acts):
            out = np.tanh(h @ W + b) if a == "tanh" else h @ W + b
            self._fw.append((h, out, a))
            h = out
        return h

    def backward(self, g_y):
        """g_y = dL/d_out -> (gW, gb, g_x). Must follow this net's forward()."""
        gW = [None] * len(self.Ws)
        gb = [None] * len(self.bs)
        g = g_y
        for i in range(len(self.Ws) - 1, -1, -1):
            h_prev, out, a = self._fw[i]
            if a == "tanh":
                g = g * (1.0 - out * out)
            gW[i] = h_prev.T @ g
            gb[i] = g.sum(axis=0)
            g = g @ self.Ws[i].T
        return gW, gb, g

    def step(self, gW, gb):
        self.t += 1
        c1 = 1.0 - ADAM_B1 ** self.t
        c2 = 1.0 - ADAM_B2 ** self.t
        for i in range(len(self.Ws)):
            gWi = gW[i] + WEIGHT_DECAY * self.Ws[i]   # ridge lineage: W only
            self._mW[i] = ADAM_B1 * self._mW[i] + (1.0 - ADAM_B1) * gWi
            self._vW[i] = ADAM_B2 * self._vW[i] + (1.0 - ADAM_B2) * (gWi * gWi)
            self.Ws[i] -= ADAM_LR * (self._mW[i] / c1) / (np.sqrt(self._vW[i] / c2) + ADAM_EPS)
            self._mb[i] = ADAM_B1 * self._mb[i] + (1.0 - ADAM_B1) * gb[i]
            self._vb[i] = ADAM_B2 * self._vb[i] + (1.0 - ADAM_B2) * (gb[i] * gb[i])
            self.bs[i] -= ADAM_LR * (self._mb[i] / c1) / (np.sqrt(self._vb[i] / c2) + ADAM_EPS)

    def n_params(self):
        return int(sum(W.size + b.size for W, b in zip(self.Ws, self.bs)))


def mse(pred, y):
    d = pred - y
    return float((d * d).mean()), d


def path_pass(trunk, head, x, y):
    """One full-batch forward/backward through trunk->head. Eats forward caches
    immediately (per-path), so a second path may overwrite them safely."""
    h = trunk.forward(x)
    p = head.forward(h)
    loss, d = mse(p, y)
    if not np.isfinite(loss):
        raise ValueError(f"non-finite loss {loss}")
    g_p = 2.0 * d / d.size                     # L = mean(d^2) over frames*dims
    hgW, hgb, g_h = head.backward(g_p)
    tgW, tgb, _ = trunk.backward(g_h)
    return loss, (tgW, tgb), (hgW, hgb)


def sum_grads(g1, g2):
    return ([a + b for a, b in zip(g1[0], g2[0])],
            [a + b for a, b in zip(g1[1], g2[1])])


def train_epoch(trunk, paths):
    """paths: list of (head, x, y). Each head sees ONLY its own frames;
    trunk receives the SUM of per-path gradients."""
    head_grads, trunk_grads = [], None
    for head, x, y in paths:
        _, tg, hg = path_pass(trunk, head, x, y)
        trunk_grads = tg if trunk_grads is None else sum_grads(trunk_grads, tg)
        head_grads.append((head, hg))
    trunk.step(*trunk_grads)
    for head, hg in head_grads:
        head.step(*hg)


def predict(trunk, head, x):
    return head.forward(trunk.forward(x))


def standardize_fit(x):
    mu, sd = x.mean(0), x.std(0)
    sd = np.where(sd < 1e-12, 1.0, sd)
    return mu, sd


def standardize_apply(fit, x):
    return (x - fit[0]) / fit[1]


def make_reader(rng):
    """Trunk + one linear head, fixed draw order from rng."""
    trunk = MLP([4, *TRUNK_HIDDEN], rng, out_act="tanh")
    head = MLP([TRUNK_HIDDEN[-1], HEAD_OUT], rng, out_act="lin")
    return trunk, head


def arm_seed(arm, di):
    return np.random.default_rng(
        SEED_BASE + MODEL_SEED_OFFSET + 1000 * ARM_INDEX[arm] + 17 * di)


def pooled_fit(data):
    """A/B shared-trunk standardization: pooled train frames of both families."""
    return standardize_fit(np.concatenate(
        [data["blob"]["train"][0], data["grat"]["train"][0]]))


def _xy(fit, data, fam, split):
    return (standardize_apply(fit, data[fam][split][0]),
            data[fam][split][1])


# ---------------- the three arms ----------------
def train_A_joint(data, di):
    """Shared trunk, both losses summed from epoch 0."""
    rng = arm_seed("A_joint", di)
    trunk, head_b = make_reader(rng)
    head_d = MLP([TRUNK_HIDDEN[-1], HEAD_OUT], rng, out_act="lin")
    fit = pooled_fit(data)
    xb, yb = _xy(fit, data, "blob", "train")
    xd, yd = _xy(fit, data, "grat", "train")
    for _ in range(TOTAL_EPOCHS):
        train_epoch(trunk, [(head_b, xb, yb), (head_d, xd, yd)])
    return {"trunk": trunk, "head_blob": head_b, "head_dir": head_d,
            "fit": fit, "trunk_epochs": TOTAL_EPOCHS}


def train_B_sequential(data, di):
    """Phase 1: blob-only to val r2 >= 0.40 (min 50, cap 400). Phase 2:
    direction head created at the switch, both losses, 600 total trunk epochs."""
    rng = arm_seed("B_sequential", di)
    trunk, head_b = make_reader(rng)
    fit = pooled_fit(data)
    xb, yb = _xy(fit, data, "blob", "train")
    xd, yd = _xy(fit, data, "grat", "train")
    xv, yv = _xy(fit, data, "blob", "val")

    p1_used, p1_reached, switch_val = 0, False, None
    for ep in range(P1_MAX_EPOCHS):
        train_epoch(trunk, [(head_b, xb, yb)])
        p1_used = ep + 1
        if p1_used >= P1_MIN_EPOCHS:
            r2v = float(ie1.r2_multi(yv, predict(trunk, head_b, xv)))
            assert np.isfinite(r2v), "non-finite val r2 in B phase 1"
            if r2v >= P1_COMPETENCE_R2:
                p1_reached, switch_val = True, round(r2v, 6)
                break
    if not p1_reached:  # competence miss at cap: book it, still finish for receipt
        r2v = float(ie1.r2_multi(yv, predict(trunk, head_b, xv)))
        switch_val = round(r2v, 6)

    head_d = MLP([TRUNK_HIDDEN[-1], HEAD_OUT], rng, out_act="lin")  # arrives at switch
    p2 = TOTAL_EPOCHS - p1_used
    assert p2 > 0, "phase-1 cap must stay under the total budget"
    for _ in range(p2):
        train_epoch(trunk, [(head_b, xb, yb), (head_d, xd, yd)])
    final_val = round(float(ie1.r2_multi(yv, predict(trunk, head_b, xv))), 6)
    return {"trunk": trunk, "head_blob": head_b, "head_dir": head_d,
            "fit": fit, "trunk_epochs": TOTAL_EPOCHS,
            "p1_epochs": p1_used, "p1_reached": p1_reached,
            "p1_switch_val_r2": switch_val, "final_val_blob_r2": final_val,
            "forgetting_val_r2": round(switch_val - final_val, 6)}


def train_C_split(data, di):
    """Independent trunk+head specialist per family (draw order: blob first)."""
    rng = arm_seed("C_split_trunks", di)
    res = {}
    for fam in ("blob", "grat"):
        trunk, head = make_reader(rng)
        fit = standardize_fit(data[fam]["train"][0])  # specialist owns its stats
        x, y = _xy(fit, data, fam, "train")
        for _ in range(TOTAL_EPOCHS):
            train_epoch(trunk, [(head, x, y)])
        res[fam] = {"trunk": trunk, "head": head, "fit": fit}
    return {"blob_specialist": res["blob"], "dir_specialist": res["grat"],
            "trunk_epochs": TOTAL_EPOCHS}


TRAINERS = {"A_joint": train_A_joint, "B_sequential": train_B_sequential,
            "C_split_trunks": train_C_split}


# ---------------- evaluation (same held-out streams across arms) ----------------
def eval_reader(trunk, head, fit, x, y):
    p = predict(trunk, head, standardize_apply(fit, x))
    r2 = float(ie1.r2_multi(y, p))
    acc = float(ie1.cardinal_accuracy(y, p))
    assert np.isfinite(r2) and np.isfinite(acc), "non-finite test metric"
    return round(r2, 6), round(acc, 6)


def eval_arm(arm, m, data):
    if arm == "C_split_trunks":
        bs, ds = m["blob_specialist"], m["dir_specialist"]
        r2b, accb = eval_reader(bs["trunk"], bs["head"], bs["fit"], *data["blob"]["test"])
        r2d, accd = eval_reader(ds["trunk"], ds["head"], ds["fit"], *data["grat"]["test"])
        leak_bg, _ = eval_reader(bs["trunk"], bs["head"], bs["fit"], *data["grat"]["test"])
        leak_db, _ = eval_reader(ds["trunk"], ds["head"], ds["fit"], *data["blob"]["test"])
    else:
        r2b, accb = eval_reader(m["trunk"], m["head_blob"], m["fit"], *data["blob"]["test"])
        r2d, accd = eval_reader(m["trunk"], m["head_dir"], m["fit"], *data["grat"]["test"])
        leak_bg, _ = eval_reader(m["trunk"], m["head_blob"], m["fit"], *data["grat"]["test"])
        leak_db, _ = eval_reader(m["trunk"], m["head_dir"], m["fit"], *data["blob"]["test"])
    return {"r2_blob": r2b, "r2_direction": r2d,
            "cardinal_acc_blob": accb, "cardinal_acc_direction": accd,
            "r2_blobhead_on_grat_leak": leak_bg,   # descriptive
            "r2_dirhead_on_blob_leak": leak_db}    # descriptive


# ---------------- main ----------------
def main():
    t0 = time.time()
    rng0 = np.random.default_rng(0)
    _tr, _hd = make_reader(rng0)
    out = {
        "experiment": "ie3 specialist trunks: sequential specialization vs joint training",
        "date": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "plan": "proposals/runs/IE3-plan.md",
        "cpu_only": True, "numpy_version": np.__version__,
        "config": {
            "arms": ["A_joint: shared trunk, blob+dir losses summed from epoch 0",
                     "B_sequential: blob-only to val r2>=0.40 (min 50/cap 400), "
                     "then +dir head, both losses, 600 total trunk epochs",
                     "C_split_trunks: independent specialist per family (baseline)"],
            "sensor": "IE2 stack verbatim via ie1_reichardt import: blob sigma 2/3, "
                      "speeds 0.25/0.5, 4 cardinals, densities 8/16/32, tau 2, "
                      "warmup 12 / kept 48; grating lambdas 8/16 at speeds 0.25/0.5 "
                      "(IE1 grating speed 1.0 dropped: both families share IE2's set)",
            "reader": f"trunk 4-{TRUNK_HIDDEN[0]}-{TRUNK_HIDDEN[1]} tanh "
                      f"({_tr.n_params()} params) + linear heads 8->2 "
                      f"({_hd.n_params()} params each); Adam lr {ADAM_LR}; "
                      f"L2 weight decay {WEIGHT_DECAY} (IE2 ridge alpha lineage, W only)",
            "standardization": "A/B pooled over both families' train frames; "
                               "C per-family (specialists own their stats)",
            "seed_base": SEED_BASE,
            "seed_law": "base + 1000*ci + 10*si + split_offset; blob ci 0-15, "
                        "grating ci 100-115; train si 0-2, val si 3 (B gate only), "
                        "test si 0-3 @ offset 100; model rng "
                        "base+500000+1000*arm+17*density_idx",
            "frames_per_family_per_density": {"train": 2304, "val": 768, "test": 3072},
            "gates": {
                "SPECIALIZATION_WINS": f"r2_dir_B[32]-r2_dir_A[32] >= {SPEC_MARGIN_DIR} "
                                       f"AND r2_blob_B[32] >= r2_blob_C[32]-{SPEC_BLOB_SLACK}",
                "JOINT_OK": f"else: A within {JOINT_SLACK} of per-density max on BOTH "
                            f"heads at ALL densities",
                "else": "DILUTION_CONFIRMS",
                "invalid": "any P1 competence miss / non-finite metric / shape assert"},
        },
        "densities": {},
        "gate": {},
    }
    print("[ie3] 3 arms x 3 densities, CPU-only; gates frozen in IE3-plan.md", flush=True)
    p1_all_reached = True
    for di, n in enumerate(DENSITIES):
        data = build_density(n)  # shared objects across arms
        out["densities"][str(n)] = {}
        for arm in ARMS:
            models = TRAINERS[arm](data, di)
            metrics = eval_arm(arm, models, data)
            metrics["trunk_epochs"] = models["trunk_epochs"]
            if arm == "B_sequential":
                metrics.update({k: models[k] for k in
                                ("p1_epochs", "p1_reached", "p1_switch_val_r2",
                                 "final_val_blob_r2", "forgetting_val_r2")})
                p1_all_reached = p1_all_reached and models["p1_reached"]
                if not models["p1_reached"]:
                    print(f"[ie3] FAIL-LOUD: B p1 competence ({P1_COMPETENCE_R2}) "
                          f"unreached at density {n} "
                          f"(val r2 {models['p1_switch_val_r2']} at cap)", flush=True)
            out["densities"][str(n)][arm] = metrics
            print(f"[ie3] density {n} {arm}: r2_blob={metrics['r2_blob']} "
                  f"r2_dir={metrics['r2_direction']} "
                  f"acc_b={metrics['cardinal_acc_blob']} "
                  f"acc_d={metrics['cardinal_acc_direction']}", flush=True)
            if arm == "B_sequential":
                print(f"[ie3]   B p1_epochs={metrics['p1_epochs']} "
                      f"switch_val_r2={metrics['p1_switch_val_r2']} "
                      f"forgetting={metrics['forgetting_val_r2']}", flush=True)

    # ---- gates (frozen arithmetic, precedence 1 -> 2 -> 3) ----
    d32 = out["densities"][str(DENSITY_OF_RECORD)]
    dir_gap = round(d32["B_sequential"]["r2_direction"] - d32["A_joint"]["r2_direction"], 6)
    blob_gap = round(d32["B_sequential"]["r2_blob"] - d32["C_split_trunks"]["r2_blob"], 6)
    out["gate"].update({
        "density_of_record": DENSITY_OF_RECORD,
        "B_dir_minus_A_dir": dir_gap, "spec_margin_dir": SPEC_MARGIN_DIR,
        "B_blob_minus_C_blob": blob_gap, "spec_blob_slack": SPEC_BLOB_SLACK,
        "joint_slack": JOINT_SLACK,
    })
    print(f"[ie3] gate inputs @32: B-A dir={dir_gap} (need >={SPEC_MARGIN_DIR}); "
          f"B-C blob={blob_gap} (need >={-SPEC_BLOB_SLACK})", flush=True)
    if dir_gap >= SPEC_MARGIN_DIR and blob_gap >= -SPEC_BLOB_SLACK:
        verdict = "SPECIALIZATION_WINS"
    else:
        joint_rows, joint_ok = {}, True
        for n in DENSITIES:
            row = out["densities"][str(n)]
            max_b = max(row[a]["r2_blob"] for a in ARMS)
            max_d = max(row[a]["r2_direction"] for a in ARMS)
            ok_b = row["A_joint"]["r2_blob"] >= max_b - JOINT_SLACK
            ok_d = row["A_joint"]["r2_direction"] >= max_d - JOINT_SLACK
            joint_rows[str(n)] = {
                "A_blob_minus_max": round(row["A_joint"]["r2_blob"] - max_b, 6),
                "A_dir_minus_max": round(row["A_joint"]["r2_direction"] - max_d, 6),
                "ok": bool(ok_b and ok_d)}
            joint_ok = joint_ok and ok_b and ok_d
        out["gate"]["joint_rows"] = joint_rows
        verdict = "JOINT_OK" if joint_ok else "DILUTION_CONFIRMS"
    if not p1_all_reached:
        verdict = "INVALID_HARNESS"
        out["gate"]["invalid_reason"] = (
            f"B phase-1 competence (val blob r2 >= {P1_COMPETENCE_R2}) unreached "
            f"at the {P1_MAX_EPOCHS}-epoch cap at >=1 density; sequential arm "
            "never specialized — per-density data booked, no science claim")
    out["verdict"] = verdict
    out["interpretation"] = INTERPRETATIONS[verdict]
    print(f"[ie3] VERDICT: {verdict}", flush=True)

    out["seconds"] = round(time.time() - t0, 1)
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "ie3_specialist_trunks.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"[ie3] DONE {out['seconds']}s -> results/ie3_specialist_trunks.json", flush=True)
    print(json.dumps({"verdict": out["verdict"],
                      "gate": {k: v for k, v in out["gate"].items()
                               if k != "joint_rows"},
                      "by_density": {n: {a: {"r2_blob": out["densities"][n][a]["r2_blob"],
                                             "r2_direction": out["densities"][n][a]["r2_direction"]}
                                         for a in ARMS}
                                     for n in map(str, DENSITIES)}}, indent=2), flush=True)


if __name__ == "__main__":
    main()
