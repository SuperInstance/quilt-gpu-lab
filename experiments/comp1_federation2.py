#!/usr/bin/env python3
"""COMP1 — federation v2: blurred K=4 regimes, capacity-starved, bootstrap CIs.

Pre-registered: proposals/runs/COMP1-federation2.md (2026-10-01 15:21 AKDT,
before build). Re-runs COMP0's federation thesis where it can be judged:
>=200-item held-out + item-level paired bootstrap; blurred regime boundaries
(router must face ambiguity); starved narrow cells (IE3 dilution regime);
LA-v2 second cells with a DIFFERENT featurization (char trigrams — D1b
independent reach); per-regime boards as primary gates.

Arms: JOINT 4225p / SINGLE 1057p / FED 4228p (4 cells + 0-param corr router)
/ FED+LA-v2 6344p (+4 char-view twins) / JOINT+LA-v2 6341p (control).

Run:  python -m experiments.comp1_federation2            (guarded, fires GPU)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

LAB = Path(__file__).resolve().parents[1]
OUT_DIR = LAB / "results" / "comp1"
GUARD_TIMEOUT_S = 2700.0
CORPUS_SEED = 2718
SEEDS = [2718, 2719, 2720]
D = 64                 # hashed BoW dim, both views (frozen in prereg)
H_CELL = 16            # cell hidden (starved)
H_JOINT = 64           # joint hidden (param-matched total: 4225 vs 4228)
H_TWIN = 8             # char-view twin hidden
EPOCHS = 300
BATCH = 16
LR = 1e-3
TAU_PCT = 20           # look-again tau percentile on train (frozen)
N_TARGET = 2400
BLUR_BETA = 0.35
BOOT_B = 2000
ROUTER_LO, ROUTER_HI = 0.40, 0.95   # corpus validity band (prereg)
CONTESTED = ["counting-address", "negation-scope"]  # declared by construction

# ── corpus: seeded grammar, K=4 blurred regimes ─────────────────────────────
DOCKS = ["wharf-3", "berth-9", "pier-1", "quay-7", "slip-2", "dock-5", "jetty-4", "mole-6"]
CARGOS = ["sockeye", "halibut", "cod", "crab", "kelp", "gear", "herring", "oysters"]
SUBJECTS = ["the fleet", "the barge", "the tender", "the trawler", "the skiff",
            "the cutter", "the longboat", " the launch"]
SUBJECTS[7] = "the launch"
VERBS = ["offloaded", "stowed", "unloaded", "secured", "stacked", "delivered", "transferred", "logged"]
COUNTS = ["two", "three", "four", "five", "six", "seven", "eight", "nine"]
KINDS = ["semantic", "counting-address", "negation-scope", "agent-role"]
NATIVE_STYLE = {"counting-address": "manifest", "semantic": "prose",
                "negation-scope": "logbook", "agent-role": "passive"}
STYLE_MIX_P_NATIVE = 0.5   # amendment A1: evidence style decorrelation


def render_evidence(style, subj, verb, cargo, dock, n, deny):
    if style == "manifest":
        if deny:
            return f"manifest: {dock} -> no {cargo} load listed, signed {subj}."
        return f"manifest: {dock} -> {n} crates {cargo}, signed {subj}."
    if style == "prose":
        if deny:
            return f"{subj} did not {verb} the {cargo} load at {dock}."
        return f"{subj} brought a {cargo} shipment of {n} crates to {dock}."
    if style == "passive":
        if deny:
            return f"the {cargo} load at {dock} was not {verb} by {subj}."
        return f"the {cargo} crates at {dock} were {verb} by {subj}."
    # logbook
    if deny:
        return f"per the harbor log, no {cargo} load was {verb} at {dock}."
    return f"per the harbor log, the {cargo} load was {verb} at {dock} by {subj}."


def ev_style_for(rng, kind):
    """Native style w.p. 0.5, else uniform over others. Counting is
    restricted to styles that carry the count param (rule preservation)."""
    if kind == "counting-address":
        pool = ["manifest", "prose"]
    else:
        pool = ["manifest", "prose", "passive", "logbook"]
    native = NATIVE_STYLE[kind]
    others = [s for s in pool if s != native] or pool
    if rng() < STYLE_MIX_P_NATIVE:
        return native
    return others[int(rng() * len(others)) % len(others)]


def _rng(seed):
    """Deterministic uniform [0,1) callable (LCG; no python hash salt)."""
    a = seed & 0xFFFFFFFF
    state = [a]

    def _next() -> float:
        state[0] = (state[0] + 0x6D2B79F5) & 0xFFFFFFFF
        t = state[0]
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t = (t ^ (t + ((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0

    return _next


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _pick(rng, pool, exclude=()):
    excl = set(exclude)
    while True:
        x = pool[int(rng() * len(pool)) % len(pool)]
        if x not in excl:
            return x


def gen_item(rng, kind: str, i: int) -> dict:
    subj = _pick(rng, SUBJECTS)
    verb = _pick(rng, VERBS)
    cargo = _pick(rng, CARGOS)
    dock = _pick(rng, DOCKS)
    n = _pick(rng, COUNTS)
    deny = (rng() < 0.5)
    canon = (i % 2 == 0)
    meta = {"kind": kind}

    # evidence params: regime-relevant one perturbed on distortion, rest consistent
    e_subj, e_cargo, e_dock, e_n, e_deny = subj, cargo, dock, n, deny
    if not canon:
        if kind == "semantic":
            if rng() < 0.5:
                e_cargo = _pick(rng, CARGOS, exclude=[cargo])
            else:
                e_dock = _pick(rng, DOCKS, exclude=[dock])
        elif kind == "counting-address":
            j = COUNTS.index(n)
            e_n = COUNTS[(j + (1 if rng() < 0.5 else -1)) % len(COUNTS)]
            meta["n_claim"], meta["n_true"] = n, e_n
        elif kind == "negation-scope":
            e_deny = not deny
        else:  # agent-role
            e_subj = _pick(rng, SUBJECTS, exclude=[subj])

    # claim (per-regime native claim templates, as originally frozen)
    if kind == "semantic":
        claim = f"{subj} {verb} the {cargo} consignment at {dock}."
    elif kind == "counting-address":
        claim = f"{subj} {verb} {n} crates of {cargo} at {dock}."
    elif kind == "negation-scope":
        if deny:
            claim = f"{subj} did not {verb} the {cargo} load at {dock}."
        else:
            claim = f"{subj} {verb} the {cargo} load at {dock}."
    else:  # agent-role
        claim = f"{subj} {verb} the {cargo} crates at {dock}."

    style = ev_style_for(rng, kind)
    evid = render_evidence(style, e_subj, verb, e_cargo, e_dock, e_n, e_deny)
    item = {"claim": claim, "evidence": evid, "ev_style": style,
            "label": "canon" if canon else "distortion", **meta}

    # ── blur overlay (beta=0.35, label-preserving) ─────────────────────────
    if rng() < BLUR_BETA:
        o = int(rng() * 4) % 4
        if o == 0:
            k = _pick(rng, COUNTS)
            item["evidence"] += f" side note: {k} other shipments were logged."
        elif o == 1:
            k = _pick(rng, COUNTS)
            item["claim"] += f" the log also mentions {k} earlier arrivals."
        elif o == 2:
            item["evidence"] = "per the harbor log, " + item["evidence"]
        else:
            other_dock = _pick(rng, DOCKS, exclude=[dock])
            item["evidence"] += f" no discrepancies were reported for {other_dock}."
        item["overlay"] = o
    return item


def gen_corpus():
    rng = _rng(CORPUS_SEED)
    items, seen, n_overlay = [], set(), 0
    per_kind = N_TARGET // len(KINDS)
    for kind in KINDS:
        made = 0
        while made < per_kind:
            it = gen_item(rng, kind, made)
            h = _sha256(it["claim"] + " " + it["evidence"])
            if h in seen:
                continue
            seen.add(h)
            it["sha256"] = h
            items.append(it)
            made += 1
            n_overlay += 1 if "overlay" in it else 0
    train = [it for it in items if int(it["sha256"][0], 16) < 12]
    held = [it for it in items if int(it["sha256"][0], 16) >= 12]
    return train, held, n_overlay


# ── featurization: TWO views ────────────────────────────────────────────────
def _tok(text: str) -> list[str]:
    out, cur = [], []
    for ch in text.lower():
        if ch.isalnum():
            cur.append(ch)
        elif cur:
            out.append("".join(cur)); cur = []
    if cur:
        out.append("".join(cur))
    return out


def feat_word(item: dict) -> np.ndarray:
    v = np.zeros(D, dtype=np.float32)
    for tok in _tok(item["claim"] + " " + item["evidence"]):
        h = int(hashlib.sha1(tok.encode()).hexdigest(), 16) % D
        v[h] += 1.0
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def feat_char(item: dict) -> np.ndarray:
    s = (item["claim"] + " " + item["evidence"]).lower()
    v = np.zeros(D, dtype=np.float32)
    for j in range(len(s) - 2):
        g = s[j:j + 3]
        h = int(hashlib.sha1(g.encode()).hexdigest(), 16) % D
        v[h] += 1.0
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def y_of(item: dict) -> int:
    return 1 if item["label"] == "canon" else 0


# ── correlation router (D13d): centroid keys, Pearson, 0 params ─────────────
def pearson(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean(); b = b - b.mean()
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


class CorrRouter:
    def __init__(self, regimes, train_items):
        self.regimes = regimes
        self.keys = {}
        for r in regimes:
            vecs = np.stack([feat_word(it) for it in train_items if it["kind"] == r])
            self.keys[r] = vecs.mean(axis=0)

    def scores(self, item):
        v = feat_word(item)
        return {r: pearson(v, self.keys[r]) for r in self.regimes}

    def order(self, item):
        return sorted(self.regimes, key=lambda r: -self.scores(item)[r])


# ── torch nets ──────────────────────────────────────────────────────────────
def build_net(hid: int):
    import torch.nn as nn
    return nn.Sequential(nn.Linear(D, hid), nn.Tanh(), nn.Linear(hid, 1))


def train_net(model, X, Y, seed, device):
    import torch
    torch.manual_seed(seed)
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    lossf = torch.nn.BCEWithLogitsLoss()
    n = len(X)
    for _ep in range(EPOCHS):
        perm = torch.randperm(n, device=X.device)
        for i in range(0, n, BATCH):
            idx = perm[i:i + BATCH]
            xb, yb = X[idx], Y[idx]
            opt.zero_grad()
            loss = lossf(model(xb).squeeze(-1), yb)
            loss.backward()
            opt.step()
    return model


def predict(model, X) -> np.ndarray:
    import torch
    with torch.no_grad():
        p = torch.sigmoid(model(X).squeeze(-1))
    return p.cpu().numpy()


def ramp_burn(device) -> dict:
    import torch
    a = torch.randn(2048, 2048, device=device)
    t0 = time.time(); synced = False
    while time.time() - t0 < 0.6:
        for _ in range(20):
            a = a @ a; a /= a.norm()
        torch.cuda.synchronize(); synced = True
    return {"ramp_s": round(time.time() - t0, 3), "synced": synced}


# ── inner (measured) run ────────────────────────────────────────────────────
def run_inner(out_dir: Path) -> int:
    import torch
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    out_dir.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    train_items, held_items, n_overlay = gen_corpus()
    (out_dir / "corpus.jsonl").write_text(
        "\n".join(json.dumps(it) for it in train_items + held_items) + "\n")
    regimes = sorted({it["kind"] for it in train_items})
    assert regimes == sorted(KINDS), regimes

    # ── corpus validity gates (prereg) ──────────────────────────────────────
    n_tr, n_he = len(train_items), len(held_items)
    per_kind_held = {r: sum(1 for it in held_items if it["kind"] == r) for r in regimes}
    canon_frac = float(np.mean([y_of(it) for it in held_items]))
    validity = {
        "n_train": n_tr, "n_heldout": n_he, "per_kind_heldout": per_kind_held,
        "canon_frac_heldout": round(canon_frac, 4),
        "overlay_items": n_overlay, "overlay_rate": round(n_overlay / (n_tr + n_he), 4),
    }
    ok_corpus = (n_he >= 200 and n_tr >= 600
                 and all(v >= 80 for v in per_kind_held.values())
                 and abs(canon_frac - 0.5) <= 0.06)
    per_kind_canon = {r: float(np.mean([y_of(it) for it in held_items if it["kind"] == r]))
                      for r in regimes}
    ok_corpus = ok_corpus and all(abs(v - 0.5) <= 0.06 for v in per_kind_canon.values())
    validity["per_kind_canon_frac"] = {k: round(v, 4) for k, v in per_kind_canon.items()}

    Xtr_w = torch.tensor(np.stack([feat_word(it) for it in train_items]), device=device)
    Ytr = torch.tensor(np.array([y_of(it) for it in train_items], dtype=np.float32), device=device)
    Xtr_c = torch.tensor(np.stack([feat_char(it) for it in train_items]), device=device)
    Xhe_w = torch.tensor(np.stack([feat_word(it) for it in held_items]), device=device)
    Xhe_c = torch.tensor(np.stack([feat_char(it) for it in held_items]), device=device)
    yhe = np.array([y_of(it) for it in held_items])

    ramp = ramp_burn(device) if device.type == "cuda" else {"ramp_s": 0.0, "synced": True}

    router = CorrRouter(regimes, train_items)
    orders_he = [router.order(it) for it in held_items]
    orders_tr = [router.order(it) for it in train_items]

    def router_stats(items, orders):
        ok = sum(1 for it, o in zip(items, orders) if o[0] == it["kind"])
        gaps = [o and (router.scores(it)[o[0]] - router.scores(it)[o[1]])
                for it, o in zip(items, orders)]
        return round(ok / len(items), 4), round(float(np.mean(gaps)), 4)

    r_train_acc, _ = router_stats(train_items, orders_tr)
    r_held_acc, r_gap = router_stats(held_items, orders_he)
    router_audit = {"train_acc": r_train_acc, "heldout_acc": r_held_acc,
                    "mean_top1_top2_corr_gap_heldout": r_gap}
    in_band = ROUTER_LO <= r_held_acc <= ROUTER_HI

    # per-seed arms → per-item correctness cubes: arms[arm][seed] = bool array
    ARM_NAMES = ["JOINT", "SINGLE", "FED", "FED_LA", "JOINT_LA"]
    correct = {a: np.zeros((len(SEEDS), n_he), dtype=bool) for a in ARM_NAMES}
    per_seed_meta = []

    if ok_corpus and in_band:
        for si, seed in enumerate(SEEDS):
            joint = train_net(build_net(H_JOINT).to(device), Xtr_w, Ytr, seed, device)
            pj = predict(joint, Xhe_w)
            correct["JOINT"][si] = (pj >= 0.5) == (yhe == 1)

            single = train_net(build_net(H_CELL).to(device), Xtr_w, Ytr, seed, device)
            ps = predict(single, Xhe_w)
            correct["SINGLE"][si] = (ps >= 0.5) == (yhe == 1)

            cells, twins = {}, {}
            for r in regimes:
                idx = [i for i, it in enumerate(train_items) if it["kind"] == r]
                cells[r] = train_net(build_net(H_CELL).to(device), Xtr_w[idx], Ytr[idx], seed, device)
                twins[r] = train_net(build_net(H_TWIN).to(device), Xtr_c[idx], Ytr[idx], seed, device)

            reads_w = {r: predict(cells[r], Xhe_w) for r in regimes}
            reads_c = {r: predict(twins[r], Xhe_c) for r in regimes}
            tr_read_w = {r: predict(cells[r], Xtr_w) for r in regimes}

            tau = float(np.percentile(
                [abs(tr_read_w[orders_tr[i][0]][i] - 0.5) for i in range(n_tr)], TAU_PCT))
            j_tr = predict(joint, Xtr_w)
            tau_j = float(np.percentile([abs(p - 0.5) for p in j_tr], TAU_PCT))

            la_trig = la_flip = jla_trig = jla_flip = 0
            for i in range(n_he):
                r1 = orders_he[i][0]
                p1 = reads_w[r1][i]; m1 = abs(p1 - 0.5)
                fed_ans = p1 >= 0.5
                if m1 < tau:                       # LA-v2: same-regime char twin
                    la_trig += 1
                    m2 = abs(reads_c[r1][i] - 0.5)
                    if m2 > m1:
                        la_flip += 1
                        fed_ans = reads_c[r1][i] >= 0.5
                correct["FED"][si, i] = ((p1 >= 0.5) == (yhe[i] == 1))
                correct["FED_LA"][si, i] = ((fed_ans) == (yhe[i] == 1))

                jp = pj[i]; jm = abs(jp - 0.5)
                j_ans = jp >= 0.5
                if jm < tau_j:                     # control arm, same twin bank
                    jla_trig += 1
                    m2 = abs(reads_c[r1][i] - 0.5)
                    if m2 > jm:
                        jla_flip += 1
                        j_ans = reads_c[r1][i] >= 0.5
                correct["JOINT_LA"][si, i] = ((j_ans) == (yhe[i] == 1))

            per_seed_meta.append({
                "seed": seed, "tau_la": round(tau, 4), "tau_joint_la": round(tau_j, 4),
                "la_triggers": la_trig, "la_flips": la_flip,
                "joint_la_triggers": jla_trig, "joint_la_flips": jla_flip})
            print(f"seed {seed} done", flush=True)

    # ── boards, bootstrap, gates ────────────────────────────────────────────
    kind_idx = {r: np.array([i for i, it in enumerate(held_items) if it["kind"] == r])
                for r in regimes}

    def board_acc(arm, idx=None):
        sel = np.arange(n_he) if idx is None else idx
        return float(correct[arm][:, sel].mean())

    def seed_std(arm, idx=None):
        sel = np.arange(n_he) if idx is None else idx
        return float(correct[arm][:, sel].mean(axis=1).std())

    def boot_ci(arm_a, arm_b, idx=None, b=BOOT_B):
        """item-level paired bootstrap of seed-mean acc difference."""
        sel = np.arange(n_he) if idx is None else idx
        a = correct[arm_a][:, sel].mean(axis=0)   # per-item seed-mean correctness
        bb = correct[arm_b][:, sel].mean(axis=0)
        d = a - bb
        rng = np.random.default_rng(CORPUS_SEED)
        n = len(d)
        draws = np.empty(b)
        for k in range(b):
            samp = rng.integers(0, n, n)
            draws[k] = d[samp].mean()
        lo, hi = np.percentile(draws, [2.5, 97.5])
        return {"diff": round(float(d.mean()), 4),
                "ci95": [round(float(lo), 4), round(float(hi), 4)]}

    boards = {}
    for a in ARM_NAMES:
        boards[a] = {"full": round(board_acc(a), 4)}
        for r in regimes:
            boards[a][r] = round(board_acc(a, kind_idx[r]), 4)
    seed_stds = {a: {"full": round(seed_std(a), 4)} for a in ARM_NAMES}
    chance = {"full": round(float(max(yhe.mean(), 1 - yhe.mean())), 4)}
    for r in regimes:
        yr = yhe[kind_idx[r]]
        chance[r] = round(float(max(yr.mean(), 1 - yr.mean())), 4)

    def gate(a, b, idx=None):
        ci = boot_ci(a, b, idx)
        degenerate = seed_std(a, idx) == 0.0 or seed_std(b, idx) == 0.0
        verdict = ("INCONCLUSIVE (std==0 law)" if degenerate else
                   ("PASS" if (ci["diff"] > 0 and ci["ci95"][0] > 0) else
                    ("KILLSIDE" if ci["ci95"][1] < 0 else "FAIL")))
        return {"diff": ci["diff"], "ci95": ci["ci95"],
                "std0_a": seed_std(a, idx) == 0.0, "std0_b": seed_std(b, idx) == 0.0,
                "verdict": verdict}

    gates = {
        "G1_fed_gt_single_full": gate("FED", "SINGLE"),
        "G1R_fed_gt_single_counting": gate("FED", "SINGLE", kind_idx["counting-address"]),
        "G1R_fed_gt_single_negation": gate("FED", "SINGLE", kind_idx["negation-scope"]),
        "G2_la_gt_fed_full": gate("FED_LA", "FED"),
        "G3_fed_gt_joint_full_secondary": gate("FED", "JOINT"),
    }
    la_premium = boot_ci("FED_LA", "FED")
    joint_la_premium = boot_ci("JOINT_LA", "JOINT")
    g2c_diff = round(la_premium["diff"] - joint_la_premium["diff"], 4)
    control = {"fed_la_premium": la_premium, "joint_la_premium": joint_la_premium,
               "g2c_premium_gap": g2c_diff,
               "verdict": "CONTROL_OK (LA buys more in federation)" if g2c_diff > 0
                          else "CONTROL_FAIL (LA win looks like capacity)"}
    per_regime_ci = {f"{a}_vs_{b}@{r}": boot_ci(a, b, kind_idx[r])
                     for a, b in (("FED", "SINGLE"), ("FED", "JOINT"), ("FED_LA", "FED"))
                     for r in regimes}

    g1, g1c, g1n, g2 = (gates["G1_fed_gt_single_full"],
                        gates["G1R_fed_gt_single_counting"],
                        gates["G1R_fed_gt_single_negation"],
                        gates["G2_la_gt_fed_full"])
    if not ok_corpus:
        overall = "INCONCLUSIVE_CORPUS (validity gate)"
    elif not in_band:
        overall = "INCONCLUSIVE_CORPUS (router out of band)"
    elif len(per_seed_meta) < len(SEEDS):
        overall = "INCONCLUSIVE (TRUNC-B)"
    elif g1["verdict"] == "PASS" and g1c["verdict"] == "PASS" and g1n["verdict"] == "PASS" \
            and g2["verdict"] == "PASS":
        overall = "KEEP"
    elif g1["verdict"] == "PASS" and g1c["verdict"] == "PASS" and g1n["verdict"] == "PASS":
        overall = "SPLIT_KEEP_G1"
    elif g1["verdict"] == "KILLSIDE":
        overall = "KILL"
    else:
        overall = "INCONCLUSIVE"

    result = {
        "experiment": "COMP1 federation v2 (blurred K=4, starved cells, bootstrap CIs)",
        "prereg": "proposals/runs/COMP1-federation2.md",
        "device": str(device), "torch": torch.__version__,
        "corpus": {"seed": CORPUS_SEED, "n_target": N_TARGET, "blur_beta": BLUR_BETA,
                   **validity, "validity_ok": bool(ok_corpus)},
        "router_audit": router_audit, "router_band": [ROUTER_LO, ROUTER_HI],
        "router_in_band": bool(in_band),
        "params": {"JOINT": 4225, "SINGLE": 1057, "FED": 4228,
                   "FED_LA": 6344, "JOINT_LA_control": 6341},
        "chance_majority": chance,
        "boards_seedmean": boards, "seed_std": seed_stds,
        "gates": gates, "capacity_control": control,
        "per_regime_ci": per_regime_ci,
        "per_seed_meta": per_seed_meta,
        "ramp_receipt": ramp,
        "wall_seconds": round(time.time() - t_start, 1),
        "seeds_complete": len(per_seed_meta),
        "verdict": overall,
    }
    (out_dir / "comp1_results.json").write_text(json.dumps(result, indent=2))
    print("VERDICT " + overall, flush=True)
    print("boards " + json.dumps(boards), flush=True)
    print("router " + json.dumps(router_audit), flush=True)
    print("gates " + json.dumps(gates), flush=True)
    print("control " + json.dumps(control), flush=True)
    return 0


# ── outer (guarded) run ─────────────────────────────────────────────────────
def run_outer(out_dir: Path) -> int:
    sys.path.insert(0, str(LAB))
    import guard
    g = guard.Guard(timeout_s=GUARD_TIMEOUT_S, task_id="COMP1-federation2",
                    agent="quilt-gpu-lab keeper (Lucineer, main Super Z)",
                    seed="2718,2719,2720", receipt_dir=str(out_dir / "guard"))
    ok = g.preflight()
    if not ok:
        print(f"PREFLIGHT REFUSED: {g.breach} — retry once after 60 s", flush=True)
        time.sleep(60.0)
        ok = g.preflight()
    if not ok:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "comp1_results.json").write_text(json.dumps(
            {"lane": "COMP1-federation2", "verdict": "NOT-RUN",
             "reason": f"guard preflight refused twice: {g.breach}"}, indent=2))
        g.emit_receipt(verdict="VOID", void_reason=f"preflight refused twice: {g.breach}")
        print("BOOKED NOT-RUN (guard preflight refused twice)", flush=True)
        return 2

    cmd = [sys.executable, str(Path(__file__).resolve()), "--inner", "--out", str(out_dir)]
    rc, out, err = g.run(cmd, cwd=str(LAB), env=dict(os.environ))
    print(f"inner rc={rc}", flush=True)
    print(out[-3000:], flush=True)
    if err.strip():
        print("stderr tail:", err[-800:], flush=True)
    if rc == 0:
        rpath, receipt = g.emit_receipt()
        okv, msg = g.validate_receipt(rpath)
        print(f"guard MEASURED receipt: {rpath} valid={okv} {msg}", flush=True)
    else:
        g.emit_receipt(verdict="VOID", void_reason=f"inner exit {rc}")
        print("VOID receipt sealed for failed run", flush=True)
    return 0 if rc == 0 else 2


if __name__ == "__main__":
    args = sys.argv[1:]
    out = OUT_DIR
    if "--out" in args:
        out = Path(args[args.index("--out") + 1])
    if "--inner" in args:
        sys.exit(run_inner(out))
    sys.exit(run_outer(out))
