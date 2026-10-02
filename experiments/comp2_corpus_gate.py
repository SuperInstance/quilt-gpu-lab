#!/usr/bin/env python3
"""COMPOSITE-2 phase 1 — corpus build + F-gate calibration (CPU-only, 0 Wh, no GPU).

Implements phase 1 of proposals/runs/COMPOSITE-2-federation3.md ONLY:
  (1) CORPUS  — N=24,600 raw, K=4 regimes (= COMP1's exact four), grammar =
      COMP1-A1 VERBATIM (reuses experiments.comp1_federation2 raw generator,
      renderer, featurization, LCG law, sha256 content addressing, hash split),
      >=20x dedup-pool headroom with deterministic LCG regeneration.
  (2) F-GATE  — logistic linear probe (sklearn lbfgs, C=1.0, 3 refits) on the
      frozen S1 word64 view, TRAIN-fit; full-board in [0.65,0.85] AND every
      per-regime in [0.60,0.90] AND refit std > 0  ->  GATE GREEN.
      <=8 iterations over 4 declared knobs (k1 near-miss distance, k2 overlay
      rate beta, k3 vocab-overlap fraction, k4 style-mix probability).
  (3) PER-ITEM persistence structure for every downstream artifact (booked law).

ARMS ARE BLOCKED in this phase. No arm is trained here. No commit.

Modes:
  --explore            pilot direction-finding sweep (small N; disclosed, not
                       counted against the <=8 gate budget)
  --gate               the formal full-N F-gate calibration loop
  --verify             grammar-verbatim equivalence receipt + determinism (W1)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))

# ── COMP1-A1 VERBATIM imports (grammar-frozen law) ──────────────────────────
from experiments.comp1_federation2 import (  # noqa: E402
    KINDS, DOCKS, CARGOS, SUBJECTS, VERBS, COUNTS, NATIVE_STYLE,
    _rng, _sha256, _pick, render_evidence, feat_word, y_of,
    BLUR_BETA, STYLE_MIX_P_NATIVE,
)

OUT = LAB / "results" / "comp2_corpus"
CORPUS_SEED = 2718
N_TARGET = 24600
PER_KIND = N_TARGET // len(KINDS)          # 6,150
N_HELD_FLOOR = 5600
PER_KIND_HELD_FLOOR = 1350
DEDUP_FLOOR = 23000
FULL_LO, FULL_HI = 0.65, 0.85
REG_LO, REG_HI = 0.60, 0.90
REFIT_SEEDS = (2718, 2719, 2720)
MAX_ITERS = 8
# Robustness margin: the gate must not freeze on a knife-edge reading. A
# violated LOWER bound must be cleared by >= MARGIN_MIN, an UPPER bound
# approached by >= MARGIN_MIN (or 5x the refit std, whichever is larger).
# Rationale (prereg intent): the F-gate exists to ESTABLISH mid-band
# difficulty before a ~20 Wh arm run; a green within ~1 sigma of flipping is
# not an established corpus. Declared, applied uniformly to every bound.
MARGIN_MIN = 0.02

DEFAULT_KNOBS = {"near_miss": 1, "beta": BLUR_BETA,
                 "vocab_frac": 1.0, "style_mix": STYLE_MIX_P_NATIVE}

# k1 extra near-miss fields (applied AFTER COMP1's own regime perturbation,
# only when near_miss > 1; skipped if already perturbed by the base op).
EXTRA_FIELDS = {
    "semantic":         [("cargo", CARGOS), ("dock", DOCKS), ("verb", VERBS)],
    "counting-address": [("cargo", CARGOS), ("dock", DOCKS), ("verb", VERBS)],
    "negation-scope":   [("cargo", CARGOS), ("dock", DOCKS), ("verb", VERBS)],
    "agent-role":       [("verb", VERBS), ("dock", DOCKS), ("cargo", CARGOS)],
}
# k3 disjoint distractor lexicon (novel tokens; used only when vocab_frac < 1.0)
DISTRACTORS = ["almanac", "lantern", "compass", "driftwood", "barnacle",
               "sextant", "hoarfrost", "kestrel", "anvil", "chandlery"]


# ── parametric grammar (mirrors COMP1-A1; identical rng draw order at defaults)
def ev_style_k(rng, kind, style_mix):
    """COMP1 ev_style_for with the native-probability as a declared knob."""
    if kind == "counting-address":
        pool = ["manifest", "prose"]
    else:
        pool = ["manifest", "prose", "passive", "logbook"]
    native = NATIVE_STYLE[kind]
    others = [s for s in pool if s != native] or pool
    if rng() < style_mix:
        return native
    return others[int(rng() * len(others)) % len(others)]


def _sub(rng, pool, exclude, vocab_frac, distractors=None):
    """Substitution pick. vocab_frac >= 1.0 == COMP1 _pick (identical draws)."""
    if vocab_frac >= 1.0:
        return _pick(rng, pool, exclude)
    if rng() < vocab_frac:
        return _pick(rng, pool, exclude)
    return _pick(rng, distractors or DISTRACTORS, exclude)


def gen_item_c2(rng, kind, i, knobs):
    nm = float(knobs["near_miss"])          # expected # extra fields perturbed
    beta = float(knobs["beta"])
    vocab_frac = float(knobs["vocab_frac"])
    style_mix = float(knobs["style_mix"])

    subj = _pick(rng, SUBJECTS)
    verb = _pick(rng, VERBS)
    cargo = _pick(rng, CARGOS)
    dock = _pick(rng, DOCKS)
    n = _pick(rng, COUNTS)
    deny = (rng() < 0.5)
    canon = (i % 2 == 0)
    meta = {"kind": kind}

    e_subj, e_cargo, e_dock, e_n, e_deny = subj, cargo, dock, n, deny
    if not canon:
        # ── COMP1-A1 base perturbation, VERBATIM ──
        if kind == "semantic":
            if rng() < 0.5:
                e_cargo = _sub(rng, CARGOS, [cargo], vocab_frac)
            else:
                e_dock = _sub(rng, DOCKS, [dock], vocab_frac)
        elif kind == "counting-address":
            j = COUNTS.index(n)
            e_n = COUNTS[(j + (1 if rng() < 0.5 else -1)) % len(COUNTS)]
            meta["n_claim"], meta["n_true"] = n, e_n
        elif kind == "negation-scope":
            e_deny = not deny
        else:  # agent-role
            e_subj = _sub(rng, SUBJECTS, [subj], vocab_frac)
        # ── k1 extra near-miss distance (near_miss > 1 only) ──
        changed = set()
        if kind == "semantic":
            changed = {f for f, v in (("cargo", e_cargo), ("dock", e_dock))
                       if (f == "cargo" and v != cargo) or (f == "dock" and v != dock)}
        elif kind == "agent-role":
            changed = {"subject"}
        need, applied = max(0.0, nm - 1.0), 0
        for fname, pool in EXTRA_FIELDS[kind]:
            if applied >= need:
                break
            if fname in changed:
                continue
            p = min(1.0, need - applied)
            if p < 1.0 and rng() >= p:   # fractional tail -> stop (keeps
                break                     # the grammar hard at low nm)
            if fname == "cargo":
                e_cargo = _sub(rng, CARGOS, [cargo], vocab_frac)
            elif fname == "dock":
                e_dock = _sub(rng, DOCKS, [dock], vocab_frac)
            elif fname == "verb":
                meta["ev_verb"] = _sub(rng, VERBS, [verb], vocab_frac)
            changed.add(fname)
            applied += 1

    if kind == "semantic":
        claim = f"{subj} {verb} the {cargo} consignment at {dock}."
    elif kind == "counting-address":
        claim = f"{subj} {verb} {n} crates of {cargo} at {dock}."
    elif kind == "negation-scope":
        claim = (f"{subj} did not {verb} the {cargo} load at {dock}." if deny
                 else f"{subj} {verb} the {cargo} load at {dock}.")
    else:
        claim = f"{subj} {verb} the {cargo} crates at {dock}."

    style = ev_style_k(rng, kind, style_mix)
    ev_verb = meta.pop("ev_verb", verb)
    evid = render_evidence(style, e_subj, ev_verb, e_cargo, e_dock, e_n, e_deny)
    item = {"claim": claim, "evidence": evid, "ev_style": style,
            "label": "canon" if canon else "distortion", **meta}

    if rng() < beta:
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


def gen_corpus_c2(knobs, per_kind=PER_KIND):
    """LCG regeneration until the post-dedup floor is met (COMP1/D5 law)."""
    rng = _rng(CORPUS_SEED)
    items, seen, n_overlay, regen = [], set(), 0, 0
    for kind in KINDS:
        made = 0
        while made < per_kind:
            it = gen_item_c2(rng, kind, made, knobs)
            h = _sha256(it["claim"] + " " + it["evidence"])
            if h in seen:
                regen += 1
                continue
            seen.add(h)
            it["sha256"] = h
            items.append(it)
            made += 1
            n_overlay += 1 if "overlay" in it else 0
    train = [it for it in items if int(it["sha256"][0], 16) < 12]
    held = [it for it in items if int(it["sha256"][0], 16) >= 12]
    return train, held, {"n_raw": len(items), "n_overlay": n_overlay,
                         "overlay_rate": round(n_overlay / len(items), 4),
                         "regen_collisions": regen}


# ── near-miss distance (measured corpus statistic) ──────────────────────────
def _toks(s):
    out, cur = [], []
    for ch in s.lower():
        if ch.isalnum():
            cur.append(ch)
        elif cur:
            out.append("".join(cur)); cur = []
    if cur:
        out.append("".join(cur))
    return out


def near_miss_distance(items):
    """Mean claim/evidence token-multiset distance (Jaccard-style) per regime."""
    per = {r: [] for r in KINDS}
    for it in items:
        a, b = set(_toks(it["claim"])), set(_toks(it["evidence"]))
        per[it["kind"]].append(1.0 - len(a & b) / max(1, len(a | b)))
    return ({r: round(float(np.mean(v)), 4) for r, v in per.items()},
            round(float(np.mean([x for v in per.values() for x in v])), 4))


# ── F-gate probe ────────────────────────────────────────────────────────────
def probe_board(train, held):
    Xtr = np.stack([feat_word(it) for it in train])
    ytr = np.array([y_of(it) for it in train])
    Xhe = np.stack([feat_word(it) for it in held])
    yhe = np.array([y_of(it) for it in held])
    idx = {r: np.array([i for i, it in enumerate(held) if it["kind"] == r])
           for r in KINDS}
    fulls, per = [], {r: [] for r in KINDS}
    for s in REFIT_SEEDS:
        # lbfgs is seed-deterministic -> inject refit variance by bootstrap
        # resampling TRAIN per refit seed (documented; the refit-std law needs
        # genuinely different fits to be a meaningful degeneracy check).
        b = np.random.default_rng(s).integers(0, len(train), len(train))
        clf = LogisticRegression(C=1.0, solver="lbfgs", max_iter=5000,
                                 random_state=s).fit(Xtr[b], ytr[b])
        pred = clf.predict(Xhe)
        fulls.append(float((pred == yhe).mean()))
        for r in KINDS:
            per[r].append(float((pred[idx[r]] == yhe[idx[r]]).mean()))
    chance = {"full": round(float(max(yhe.mean(), 1 - yhe.mean())), 4)}
    for r in KINDS:
        yr = yhe[idx[r]]
        chance[r] = round(float(max(yr.mean(), 1 - yr.mean())), 4)
    return {"full": round(float(np.mean(fulls)), 4),
            "full_refits": [round(x, 4) for x in fulls],
            "full_std": round(float(np.std(fulls)), 6),
            "per_regime": {r: round(float(np.mean(per[r])), 4) for r in KINDS},
            "per_regime_refits": {r: [round(x, 4) for x in per[r]] for r in KINDS},
            "per_regime_std": {r: round(float(np.std(per[r])), 6) for r in KINDS},
            "chance": chance}


def gate_verdict(pb):
    fails = []
    if not (FULL_LO <= pb["full"] <= FULL_HI):
        fails.append(f"full {pb['full']} outside [{FULL_LO},{FULL_HI}]")
    for r, v in pb["per_regime"].items():
        if not (REG_LO <= v <= REG_HI):
            fails.append(f"{r} {v} outside [{REG_LO},{REG_HI}]")
    if not (pb["full_std"] > 0):
        fails.append(f"refit std {pb['full_std']} == 0")
    return ("GREEN" if not fails else "VIOLATION"), fails


def validity(train, held, stats):
    per_held = {r: sum(1 for it in held if it["kind"] == r) for r in KINDS}
    canon_frac = float(np.mean([y_of(it) for it in held]))
    per_canon = {r: float(np.mean([y_of(it) for it in held if it["kind"] == r]))
                 for r in KINDS}
    ok = (len(held) >= N_HELD_FLOOR and all(v >= PER_KIND_HELD_FLOOR
          for v in per_held.values()) and abs(canon_frac - 0.5) <= 0.06
          and all(abs(v - 0.5) <= 0.06 for v in per_canon.values())
          and stats["n_raw"] >= DEDUP_FLOOR)
    return {"n_train": len(train), "n_heldout": len(held),
            "per_regime_heldout": per_held,
            "canon_frac_heldout": round(canon_frac, 4),
            "per_regime_canon_frac": {k: round(v, 4) for k, v in per_canon.items()},
            "dedup_unique": len({it["sha256"] for it in train + held}),
            **stats, "validity_ok": bool(ok)}


def item_key(it):
    return hashlib.sha256((it["sha256"] + "|comp2").encode()).hexdigest()[:16]


# ── verbatim equivalence receipt ────────────────────────────────────────────
def verify_verbatim(n_per_kind=400):
    """At default knobs, gen_item_c2 must be byte-identical to COMP1's
    gen_item when driven by independent copies of the same LCG stream."""
    from experiments.comp1_federation2 import gen_item as c1_gen
    r1, r2 = _rng(CORPUS_SEED), _rng(CORPUS_SEED)
    mism = 0
    checked = 0
    for kind in KINDS:
        for i in range(n_per_kind):
            a = gen_item_c2(r1, kind, i, DEFAULT_KNOBS)
            b = c1_gen(r2, kind, i)
            checked += 1
            ak = {k: v for k, v in a.items()}
            if ak != b:
                mism += 1
                if mism <= 3:
                    print("MISMATCH", kind, i, "\n c2:", json.dumps(ak),
                          "\n c1:", json.dumps(b))
    return {"checked": checked, "mismatches": mism,
            "verbatim": mism == 0}


def determinism_receipt(per_kind=600):
    """W1: regenerate twice, compare sha256 sequences."""
    def seq(pk):
        tr, he, _ = gen_corpus_c2(DEFAULT_KNOBS, per_kind)
        return [it["sha256"] for it in tr + he]
    a, b = seq(per_kind), seq(per_kind)
    return {"n": len(a), "identical": a == b,
            "sha256_of_sequence": hashlib.sha256("".join(a).encode()).hexdigest()}


# ── main modes ──────────────────────────────────────────────────────────────
def run_explore():
    """Pilot direction-finding sweep (small N). NOT counted against <=8 budget."""
    grid = [
        ("p00_default",      {"near_miss": 1, "beta": 0.35, "vocab_frac": 1.0, "style_mix": 0.5}),
        ("p01_nm2",          {"near_miss": 2, "beta": 0.35, "vocab_frac": 1.0, "style_mix": 0.5}),
        ("p02_nm3",          {"near_miss": 3, "beta": 0.35, "vocab_frac": 1.0, "style_mix": 0.5}),
        ("p03_nm2_b20",      {"near_miss": 2, "beta": 0.20, "vocab_frac": 1.0, "style_mix": 0.5}),
        ("p04_nm2_b05",      {"near_miss": 2, "beta": 0.05, "vocab_frac": 1.0, "style_mix": 0.5}),
        ("p05_nm3_b20",      {"near_miss": 3, "beta": 0.20, "vocab_frac": 1.0, "style_mix": 0.5}),
        ("p06_nm1_b35_v60",  {"near_miss": 1, "beta": 0.35, "vocab_frac": 0.6, "style_mix": 0.5}),
        ("p07_nm1_sm10",     {"near_miss": 1, "beta": 0.35, "vocab_frac": 1.0, "style_mix": 0.1}),
    ]
    pk = 600
    rows = []
    for name, kn in grid:
        t0 = time.time()
        tr, he, st = gen_corpus_c2(kn, pk)
        pb = probe_board(tr, he)
        nd, nd_full = near_miss_distance(tr + he)
        v, f = gate_verdict(pb)
        rows.append({"setting": name, **kn, "per_kind": pk,
                     "full": pb["full"], "full_std": pb["full_std"],
                     "per_regime": pb["per_regime"], "near_miss_dist": nd_full,
                     "verdict": v, "sec": round(time.time() - t0, 1)})
        print(f"{name:18s} full={pb['full']:.4f} std={pb['full_std']:.6f} "
              f"nd={nd_full:.3f} {v} {pb['per_regime']}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pilot_sweep.json").write_text(json.dumps(
        {"note": "pilot direction-finding, small N; NOT the F-gate calibration loop",
         "rows": rows}, indent=2))
    print("pilot written ->", OUT / "pilot_sweep.json")


def _measure(knobs, per_kind=PER_KIND):
    tr, he, st = gen_corpus_c2(knobs, per_kind)
    pb = probe_board(tr, he)
    val = validity(tr, he, st)
    nd, nd_full = near_miss_distance(tr + he)
    verdict, fails = gate_verdict(pb)
    return {"tr": tr, "he": he, "st": st, "pb": pb, "val": val,
            "nd": nd, "nd_full": nd_full, "verdict": verdict, "fails": fails}


def run_gate():
    """Formal F-gate calibration loop (<=8 iterations over the 4 knobs).

    Search: adaptive bisection on k1 (near-miss distance, the dominant dial)
    to find the *minimal* near-miss that clears the band -- i.e. the hardest
    corpus that is still linearly learnable, which also keeps the
    easiest-regime reading away from the 0.90 cap. k2 (beta) is the declared
    fallback if k1 cannot reach the band; k3/k4 remain declared but unused.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    t_all = time.time()
    base = dict(DEFAULT_KNOBS)
    log = {"lane": "COMPOSITE-2 phase 1 (corpus + F-gate)",
           "run": "r3 — robust-margin freeze (MARGIN_MIN=0.02). r1 "
                  "(harness-invalid: bisection walked the wrong way when a "
                  "per-regime bound was binding) preserved as "
                  "calibration_log.harness-invalid-r1.json; r2 (correct "
                  "direction, minimal-near-miss freeze landing within ~1 sigma "
                  "of the negation floor) preserved as "
                  "calibration_log.r2-minimal-edge.json.",
           "margin_min": MARGIN_MIN,
           "prereg": "proposals/runs/COMPOSITE-2-federation3.md",
           "corpus_seed": CORPUS_SEED, "n_target": N_TARGET,
           "per_kind": PER_KIND, "max_iterations": MAX_ITERS,
           "knob_order": ["k1 near_miss", "k2 beta", "k3 vocab_frac",
                          "k4 style_mix"],
           "knob_defs": {
               "k1 near_miss": "expected # of regime-relevant evidence fields "
                               "perturbed on a distortion (1.0 = COMP1-A1 "
                               "verbatim; monotone: up = easier)",
               "k2 beta": "label-preserving overlay/blur rate (COMP1 0.35; "
                          "up = noisier = harder)",
               "k3 vocab_frac": "P(distortion substitution drawn from the "
                                "confusable in-pool vs a disjoint distractor pool)",
               "k4 style_mix": "P(native evidence style) (COMP1 0.5)"},
           "bands": {"full": [FULL_LO, FULL_HI],
                     "per_regime": [REG_LO, REG_HI],
                     "refit_std": "> 0"},
           "iterations": [], "search": "adaptive bisection on k1 near_miss"}
    best = None
    a, b = 1.0, 3.0            # a = known too-hard, b = known too-easy (loose)
    nm = 2.0
    tried = set()

    def direction(m):
        """Multi-constraint bisection direction (harness fix, r2) + declared
        robustness margin (r3): a lower bound must clear by MARGIN_MIN, an
        upper bound must be approached no closer than MARGIN_MIN. A violated
        LOWER bound means too hard (raise nm); a violated UPPER bound means
        too easy (lower nm). r1 only inspected the full board and walked the
        wrong way when a per-regime bound was binding."""
        pb = m["pb"]
        mg = max(MARGIN_MIN, 5.0 * pb["full_std"])
        if pb["full"] < FULL_LO + mg:
            return "hard"
        if pb["full"] > FULL_HI - mg:
            return "easy"
        if any(v < REG_LO + mg for v in pb["per_regime"].values()):
            return "hard"
        if any(v > REG_HI - mg for v in pb["per_regime"].values()):
            return "easy"
        return "green"

    def record(it, kn, m, tag):
        pb = m["pb"]
        mg = max(MARGIN_MIN, 5.0 * pb["full_std"])
        clear = [pb["full"] - FULL_LO, FULL_HI - pb["full"]] + \
                [v - REG_LO for v in pb["per_regime"].values()] + \
                [REG_HI - v for v in pb["per_regime"].values()]
        rec = {"iteration": it, "phase": tag, "knobs": kn,
               "required_margin": round(mg, 5),
               "min_bound_clearance": round(min(clear), 4),
               "n_raw": m["st"]["n_raw"], "n_heldout": len(m["he"]),
               "near_miss_distance_full": m["nd_full"],
               "near_miss_distance_per_regime": m["nd"],
               "full": m["pb"]["full"], "full_refits": m["pb"]["full_refits"],
               "full_std": m["pb"]["full_std"],
               "per_regime": m["pb"]["per_regime"],
               "per_regime_refits": m["pb"]["per_regime_refits"],
               "per_regime_std": m["pb"]["per_regime_std"],
               "chance": m["pb"]["chance"], "validity": m["val"],
               "verdict": m["verdict"], "failures": m["fails"],
               "sec": m["sec"]}
        log["iterations"].append(rec)
        print(f"iter {it} [{tag}] nm={kn['near_miss']} b={kn['beta']} "
              f"-> full={m['pb']['full']:.4f} std={m['pb']['full_std']:.6f} "
              f"nd={m['nd_full']:.3f} {m['verdict']} "
              f"{m['fails'] if m['fails'] else ''}", flush=True)
        print(f"      per-regime {m['pb']['per_regime']}", flush=True)
        return rec

    # ── phase A: bisection on k1 ──
    for it in range(1, 7):
        if nm in tried:
            break
        tried.add(nm)
        t0 = time.time()
        kn = {**base, "near_miss": nm}
        m = _measure(kn)
        m["sec"] = round(time.time() - t0, 1)
        rec = record(it, kn, m, "A:k1-bisection")
        d = direction(m)
        if d == "green" and m["val"]["validity_ok"]:
            best = rec
            b = min(b, nm)
        elif d == "hard":
            a = max(a, nm)              # too hard -> need a larger nm
        else:
            b = min(b, nm)              # too easy -> need a smaller nm
        nm = round(((a + best["knobs"]["near_miss"]) / 2.0) if best
                   else ((a + b) / 2.0), 3)
        if best and abs(nm - best["knobs"]["near_miss"]) < 0.03:
            break
        if not best and (b - a) < 0.03:
            break

    # ── phase B: k2 fallback (ease noise) if k1 alone never reached band ──
    if best is None:
        for j, beta in enumerate((0.20, 0.10, 0.05)):
            it = len(log["iterations"]) + 1
            if it > MAX_ITERS:
                break
            t0 = time.time()
            kn = {**base, "near_miss": 3.0, "beta": beta}
            m = _measure(kn)
            m["sec"] = round(time.time() - t0, 1)
            rec = record(it, kn, m, "B:k2-fallback")
            if m["verdict"] == "GREEN" and m["val"]["validity_ok"]:
                best = rec
                break

    # ── freeze ──
    if best is not None:
        kn = best["knobs"]
        t0 = time.time()
        m = _measure(kn)
        tr, he = m["tr"], m["he"]
        frozen = {"frozen": True, "iteration": best["iteration"],
                  "knobs": kn, "full": m["pb"]["full"],
                  "full_std": m["pb"]["full_std"],
                  "per_regime": m["pb"]["per_regime"],
                  "near_miss_distance": m["nd_full"],
                  "near_miss_distance_per_regime": m["nd"],
                  "validity": m["val"], "chance": m["pb"]["chance"]}
        with open(OUT / "corpus.jsonl", "w") as fh:
            for it_ in tr + he:
                fh.write(json.dumps(it_) + "\n")
        with open(OUT / "per_item_stub.jsonl", "w") as fh:
            for it_ in tr + he:
                fh.write(json.dumps({
                    "key": item_key(it_), "sha256": it_["sha256"],
                    "regime": it_["kind"], "label": it_["label"],
                    "split": ("train" if int(it_["sha256"][0], 16) < 12
                              else "heldout"),
                    "p": None, "correct": None, "margin": None,
                    "routed_sensor": None, "cell": None,
                    "la_trigger": None, "la_flip": None}) + "\n")
        seq_sha = hashlib.sha256(
            "".join(it_["sha256"] for it_ in tr + he).encode()).hexdigest()
        frozen["corpus_sha256_sequence"] = seq_sha
        frozen["corpus_bytes"] = (OUT / "corpus.jsonl").stat().st_size
        frozen["freeze_sec"] = round(time.time() - t0, 1)
        log["outcome"] = "GATE_GREEN"
        log["frozen"] = frozen
        log["note"] = (f"arms UNBLOCKED; corpus FROZEN at iteration "
                       f"{best['iteration']} (nm={kn['near_miss']}, "
                       f"beta={kn['beta']})")
    else:
        log["outcome"] = "WIRING_EXHAUSTION"
        log["frozen"] = {"frozen": False}
        log["note"] = ("arms BLOCKED; budget exhausted without a mid-band "
                       "corpus -> WIRING_VIOLATION (strike accounting is "
                       "keeper-level)")
    log["iterations_used"] = len(log["iterations"])
    log["near_miss_trajectory"] = [
        {"iteration": r["iteration"], "phase": r["phase"],
         "near_miss": r["knobs"]["near_miss"], "beta": r["knobs"]["beta"],
         "full": r["full"], "full_std": r["full_std"],
         "near_miss_distance": r["near_miss_distance_full"],
         "verdict": r["verdict"]} for r in log["iterations"]]
    log["wall_seconds"] = round(time.time() - t_all, 1)
    (OUT / "calibration_log.json").write_text(json.dumps(log, indent=2))
    print("OUTCOME", log["outcome"], "iters", log["iterations_used"],
          "->", OUT / "calibration_log.json", flush=True)
    return log


def run_verify():
    OUT.mkdir(parents=True, exist_ok=True)
    v = verify_verbatim()
    d = determinism_receipt()
    out = {"grammar_verbatim": v, "determinism_W1": d}
    (OUT / "verify_receipt.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--explore", action="store_true")
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    if a.explore:
        run_explore()
    elif a.verify:
        run_verify()
    else:
        run_gate()
