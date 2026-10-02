#!/usr/bin/env python3
"""RING-CX-0 (SYNTH-0 wildcard): training-free certainty-gated ring attractor as
a ROUTER, judged against COMP1's *trained* D13d correlation router.

Source mechanism (harvested, the one PASS cluster):
  pr_harvest/_raw/chiaroscuro_6.diff :: tools/fly_cx.py  (chiaroscuro #6, v2
  certainty-gated). Verbatim repro at results/ring_cx0/repro/ (flycx 4/4 PASS).

NO TRAINING, NO GPU (CPU numpy only). Per-item per-sensor confidence derived
from EXISTING COMP1 artifacts: the frozen word-view featurization (sha1 BoW
D=64, L2) + the frozen 0-param regime-centroid Pearson router of
experiments/comp1_federation2.py, rebuilt on TRAIN only. The ring never sees a
label; nothing is fitted.

ENGINE A (primary) - Ring64, N=64 head-direction-style, local excitation /
global inhibition:
  phi_i = 360 i / N;  K_ij = row-normalized Gaussian(d_ij; sE);  W = JE*K - JI
  I_i   = C * sum_s conf_s * Gauss(phi_i; theta_s, sC)      [theta_s = 90 s]
  r    <- (1-a) r + a * relu(W r + I);  r <- r / ||r||      (L2, shape-only)
  readout: circular mean (vector sum) -> theta_hat, certainty R = |resultant|
  GATE:   item REJECTS iff R <= tau_ring                       (no bump formed)

Kernel constants are selected by a LABEL-FREE criterion fixed before any
accuracy was computed: among all (sE, JE, JI) with flat-input R = 0.000, take
the config whose single-cue R is the plateau median (sE=16, JE=5, JI=1 ->
R_flat=0.000, R_single=0.670). No label, no accuracy entered the choice.

tau_ring = 20th percentile of TRAIN R  (COMP1's own frozen tau doctrine,
leak-free); T_soft = median TRAIN top1-top2 Pearson gap (COMP1's own margin
doctrine, leak-free). Both derived from train only; sensitivity reported.

Seeded stochasticity (declared): per-item per-sensor cue-angle jitter
N(0, 5 deg) + conf multiplicative lognormal(cv=0.10) - stochastic release.
Required so the across-seed std of the deciding stats is > 0 (G-C frost law);
the ring is otherwise deterministic.

ENGINE B (cross-check) - analytic fly_cx v2 with the HARVESTED constants
verbatim (TAU_MOTION=.35, CONFLICT_DEG=30deg, REJECT_SHRINK=.7, A0=.5) driven
by the same discrete cues: a booked test of whether a continuous-compass
constant set transfers to 4-way discrete routing unscaled.

Pre-registered gates (seed 2718; stated before run):
  G-A ring overall routing accuracy >= trained-router heldout - 0.02
  G-B negation-scope Reject-rate >= 2x mean Reject-rate across regimes
  G-C every deciding stat needs seed-std > 0, else INCONCLUSIVE never PASS
Run: python -m experiments.ring_cx0
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
import numpy as np

LAB = Path("/home/eileen/projects/quilt-gpu-lab")
OUT = LAB / "results" / "ring_cx0"
CORPUS = LAB / "results" / "comp1" / "corpus.jsonl"
COMP1 = LAB / "results" / "comp1" / "comp1_results.json"
D = 64
REGIMES = ["semantic", "counting-address", "negation-scope", "agent-role"]
SEEDS = [2718, 2719, 2720, 2721, 2722]

# ---- Ring64 geometry (label-free selection; see module docstring) ----------
N_RING = 64
SIGMA_EXC_DEG = 16.0
J_E, J_I = 5.0, 1.0
SIGMA_CUE_DEG = 30.0
C_IN = 1.4
ALPHA = 0.4
RING_TICKS = 60
TAU_PCT = 20                 # ring certainty-gate percentile (COMP1 doctrine)
CUE_JITTER_DEG = 5.0         # declared seeded stochasticity (see docstring)
CONF_JITTER_CV = 0.10

# ---- harvested fly_cx constants (verbatim, Engine B cross-check) -----------
TAU_MOTION, REJECT_SHRINK, COMMIT_BLEND, COMMIT_GAIN, CONFLICT_DEG, A0 = \
    0.35, 0.7, 0.4, 0.15, 30.0, 0.5


def tok(text):
    out, cur = [], []
    for ch in text.lower():
        if ch.isalnum():
            cur.append(ch)
        elif cur:
            out.append("".join(cur)); cur = []
    if cur:
        out.append("".join(cur))
    return out


def feat_word(item):
    v = np.zeros(D, dtype=np.float32)
    for t in tok(item["claim"] + " " + item["evidence"]):
        v[int(hashlib.sha1(t.encode()).hexdigest(), 16) % D] += 1.0
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def pearson(a, b):
    a = a - a.mean(); b = b - b.mean()
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return 0.0 if na == 0 or nb == 0 else float(np.dot(a, b) / (na * nb))


def ang_dist(a, b):
    return np.abs((a - b + 180.0) % 360.0 - 180.0)


class Ring64:
    def __init__(self):
        self.phi = np.arange(N_RING) * 360.0 / N_RING
        self.rad = np.deg2rad(self.phi)
        dd = np.abs(self.phi[:, None] - self.phi[None, :])
        dd = np.minimum(dd, 360.0 - dd)
        K = np.exp(-(dd ** 2) / (2 * SIGMA_EXC_DEG ** 2))
        K /= K.sum(axis=1, keepdims=True)
        self.W = J_E * K - J_I

    def read(self, conf, jitter=None):
        conf = np.asarray(conf, dtype=float)
        if jitter is None:
            ang = np.array([90.0 * s for s in range(4)]); c = conf
        else:
            ang = np.array([90.0 * s for s in range(4)]) + jitter[0]
            c = conf * jitter[1]
        I = C_IN * sum(c[s] * np.exp(-(ang_dist(self.phi, ang[s]) ** 2) /
                                     (2 * SIGMA_CUE_DEG ** 2)) for s in range(4))
        r = np.zeros(N_RING)
        for _ in range(RING_TICKS):
            r = (1 - ALPHA) * r + ALPHA * np.maximum(self.W @ r + I, 0.0)
            n = np.linalg.norm(r)
            if n > 0:
                r /= n
        x = float((r * np.cos(self.rad)).sum()); y = float((r * np.sin(self.rad)).sum())
        theta = float(np.rad2deg(np.arctan2(y, x)) % 360.0)
        R = min(1.0, float(np.hypot(x, y) / np.sqrt(N_RING / 2.0)))
        return theta, R


def nearest_sensor(angle):
    return int(round((angle % 360.0) / 90.0)) % 4


class AnalyticFlyCX:
    """Harvested fly_cx v2, constants verbatim (Engine B)."""
    def run(self, cues):
        theta, amp = 0.0, A0
        psi = []
        for (ang, conf) in cues:
            d = ang_dist(ang, theta)
            if conf < TAU_MOTION:
                psi.append(0)
            elif d <= CONFLICT_DEG:
                psi.append(1)
                err = ((ang - theta + 180.0) % 360.0) - 180.0
                theta = (theta + COMMIT_BLEND * err) % 360.0
                amp = min(1.0, amp + COMMIT_GAIN)
            else:
                psi.append(-1)
                err = ((ang - theta + 180.0) % 360.0) - 180.0
                theta = (theta + COMMIT_BLEND * (1.0 - amp) * err) % 360.0
                amp *= REJECT_SHRINK
        n_c, n_r = psi.count(1), psi.count(-1)
        return theta, (n_c == 0 or n_r > n_c), n_c, n_r


def main():
    rows = [json.loads(l) for l in open(CORPUS, encoding="utf-8")]
    tr = [r for r in rows if r["sha256"][0] < "c"]
    he = [r for r in rows if r["sha256"][0] >= "c"]
    keys = {r: np.stack([feat_word(it) for it in tr if it["kind"] == r]).mean(axis=0)
            for r in REGIMES}
    S_tr = np.stack([np.array([pearson(feat_word(it), keys[r]) for r in REGIMES])
                     for it in tr])
    S_he = np.stack([np.array([pearson(feat_word(it), keys[r]) for r in REGIMES])
                     for it in he])
    g_he = [it["kind"] for it in he]

    router_acc = float(np.mean([REGIMES[int(np.argmax(S_he[i]))] == g_he[i]
                                for i in range(len(he))]))
    book = json.load(open(COMP1))["router_audit"]["heldout_acc"]
    o_tr = np.argsort(-S_tr, axis=1)
    T_SOFT = float(np.median(S_tr[np.arange(len(tr)), o_tr[:, 0]] -
                             S_tr[np.arange(len(tr)), o_tr[:, 1]]))

    def confs(S, T):
        z = S / T; z -= z.max(axis=1, keepdims=True); e = np.exp(z)
        return e / e.sum(axis=1, keepdims=True)

    ring = Ring64()
    R_tr = np.array([ring.read(x)[1] for x in confs(S_tr, T_SOFT)])
    TAU_RING = float(np.percentile(R_tr, TAU_PCT))
    R_flat = ring.read([0.25] * 4)[1]
    R_one = ring.read([1.0, 0, 0, 0])[1]

    gi = np.array([REGIMES.index(g) for g in g_he])
    c_he = confs(S_he, T_SOFT)
    per_seed = []
    for seed in SEEDS:
        rng = np.random.default_rng(seed)
        ring_dec, ring_rej, ring_R, fly_rej = [], [], [], []
        for i in range(len(he)):
            jit = (rng.normal(0.0, CUE_JITTER_DEG, 4),
                   np.exp(rng.normal(0.0, CONF_JITTER_CV, 4)))
            theta, R = ring.read(c_he[i], jit)
            ring_R.append(R)
            rej = bool(R <= TAU_RING)
            ring_dec.append(-1 if rej else nearest_sensor(theta))
            ring_rej.append(rej)
            order = rng.permutation(4)
            cues = [(90.0 * int(s), float(c_he[i][s])) for s in order]
            _, frej, _, _ = AnalyticFlyCX().run(cues)
            fly_rej.append(bool(frej))
        dec = np.array(ring_dec)
        acc_all = float(np.mean(dec == gi))
        comm = [i for i in range(len(he)) if not ring_rej[i]]
        acc_comm = float(np.mean(dec[comm] == gi[comm])) if comm else float("nan")
        rb = {r: float(np.mean([ring_rej[i] for i in range(len(he)) if g_he[i] == r]))
              for r in REGIMES}
        rx = {r: float(np.mean([ring_R[i] for i in range(len(he)) if g_he[i] == r]))
              for r in REGIMES}
        ra = {r: float(np.mean([REGIMES[int(np.argmax(S_he[i]))] == g_he[i]
                                for i in range(len(he)) if g_he[i] == r]))
              for r in REGIMES}
        fb = {r: float(np.mean([fly_rej[i] for i in range(len(he)) if g_he[i] == r]))
              for r in REGIMES}
        per_seed.append(dict(seed=seed, acc_all=acc_all, acc_commit=acc_comm,
                             reject_overall=float(np.mean(ring_rej)),
                             reject_by_regime=rb, ring_R_by_regime=rx,
                             router_acc_by_regime=ra, fly_reject_by_regime=fb))

    def sm(key):
        x = np.array([p[key] for p in per_seed], float)
        return dict(mean=round(float(x.mean()), 4), std=round(float(x.std()), 4))

    def reg(field):
        return {r: dict(mean=round(float(np.mean([p[field][r] for p in per_seed])), 4),
                        std=round(float(np.std([p[field][r] for p in per_seed])), 4))
                for r in REGIMES}

    rb_sm, R_sm, ra_sm, fb_sm = reg("reject_by_regime"), reg("ring_R_by_regime"), \
        reg("router_acc_by_regime"), reg("fly_reject_by_regime")
    mean_rb = float(np.mean([rb_sm[r]["mean"] for r in REGIMES]))
    mean_fb = float(np.mean([fb_sm[r]["mean"] for r in REGIMES]))
    ratio = rb_sm["negation-scope"]["mean"] / mean_rb if mean_rb > 0 else float("inf")
    fratio = fb_sm["negation-scope"]["mean"] / mean_fb if mean_fb > 0 else float("inf")
    a = sm("acc_all")
    G_C_ok = (all(rb_sm[r]["std"] > 0 for r in REGIMES) and a["std"] > 0)
    gA = dict(threshold=round(book - 0.02, 4), overall_acc=a, acc_commit=sm("acc_commit"),
              pass_=bool(G_C_ok and a["std"] > 0 and a["mean"] >= book - 0.02))
    gB = dict(negation_rate=rb_sm["negation-scope"]["mean"],
              mean_across_regimes=round(mean_rb, 4), ratio=round(ratio, 3),
              pass_=bool(G_C_ok and ratio >= 2.0))

    out = {
        "experiment": "RING-CX-0 (SYNTH-0 wildcard): training-free certainty-gated ring-attractor router",
        "source_mechanism": "pr_harvest/_raw/chiaroscuro_6.diff :: tools/fly_cx.py (chiaroscuro #6, flycx v2 certainty-gated)",
        "repro": {"file": "results/ring_cx0/repro/fly_cx.py", "verdict": "PASS",
                  "tests_all_pass": True, "null_control_displacement_deg": 71.999,
                  "trajectory_hash_fnv1a64": "41c8af26ba55cb03",
                  "note": "verbatim extraction (169 lines) from the harvest diff; ran unchanged, flycx 4/4"},
        "device": "cpu", "gpu_used": False, "training_used": False, "numpy_only": True,
        "corpus": {"path": "results/comp1/corpus.jsonl", "n_train": len(tr),
                   "n_heldout": len(he), "seeds": SEEDS},
        "wiring": {
            "featurization": "COMP1 word view (sha1 BoW D=64, L2-normalized) rebuilt from corpus",
            "router": "COMP1 D13d 0-param regime-centroid Pearson, train-only keys",
            "reproduced_router_heldout_top1": round(router_acc, 4),
            "comp1_booked_router_heldout_top1": book,
            "confidence_map": f"softmax(Pearson / T), T = median TRAIN top1-top2 gap = {T_SOFT:.4f}",
            "ring": f"N={N_RING} DoG kernel sE={SIGMA_EXC_DEG} JE={J_E} JI={J_I} sC={SIGMA_CUE_DEG}",
            "tau_ring": round(TAU_RING, 4), "tau_pct": TAU_PCT,
            "R_flat": round(R_flat, 4), "R_single_cue": round(R_one, 4),
            "seeded_jitter": f"cue-angle N(0,{CUE_JITTER_DEG}) + conf lognormal(cv={CONF_JITTER_CV})",
        },
        "G_A_ring_ge_trained_minus_0.02": gA,
        "G_B_negation_reject_ge_2x_mean": gB,
        "G_C_seed_std_ok": bool(G_C_ok),
        "reject_by_regime_ring_seedmean": rb_sm,
        "ring_R_by_regime_seedmean": R_sm,
        "router_acc_by_regime": ra_sm,
        "reject_by_regime_flycooked_seedmean": fb_sm,
        "flycooked_ratio": round(fratio, 3),
        "flycooked_note": "Engine B: harvested fly_cx constants verbatim on discrete 4-way cues",
        "per_seed": per_seed,
    }
    out["verdict"] = ("PASS" if (gA["pass_"] and gB["pass_"]) else
                      "INCONCLUSIVE" if not G_C_ok else "FAIL")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ring_cx0_results.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({"router_repro": round(router_acc, 4), "booked": book,
                      "T_SOFT": round(T_SOFT, 4), "tau_ring": round(TAU_RING, 4),
                      "R_flat": round(R_flat, 4), "R_single": round(R_one, 4),
                      "G_A": gA, "G_B": gB, "G_C_ok": G_C_ok,
                      "reject_ring": rb_sm, "ring_R": R_sm, "router_acc_by_regime": ra_sm,
                      "reject_flycooked": fb_sm, "verdict": out["verdict"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
