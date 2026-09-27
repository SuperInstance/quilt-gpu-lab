"""D1 — look-again-scale: does the fold beat best-single, and where does the reach bound bite?

G21 (small demo) showed Look-Again beating best-single by buying a symbolic
reader with independent reach (Law 7, the Reach Bound: a fold can't land a
truth no reader's evidence reaches — raise the ceiling by buying a reader
that reaches what the others structurally cannot). This scales the check:

  - 3 dense readers (bge-small-en-v1.5, all-MiniLM-L6-v2, gte-small), each
    folding content-addressed evidence under its OWN weights (Law 6,
    Reader's Fold — cosine between claim and evidence embeddings,
    per-reader calibrated threshold).
  - 1 symbolic reader: the G21 counting-address reader (exact
    dock→count/cargo match against a limited parsing grammar — its honest
    reach limit; manifests in the inverted format are unreachable and it
    abstains).
  - >=500 seeded synthetic (claim, evidence, gold) triples, ~40% planted
    counting-address facts with near-miss counts that dense embeddings
    structurally struggle to bind (number→address attribution), so the
    reach-bound effect is testable, not assumed.

Fold verdict = the chord (oracle_chord.md): mean of reader witnesses;
abstains count 0, ties read not-supported (conservative).

HONESTY RULES. Reader thresholds are calibrated on a calibration split;
the chord configuration for the verdict is SELECTED on the same calibration
split and only SCORED on the held-out eval split (no selection on the test
set). The eval-best envelope over all subsets is also reported, clearly
labeled as an oracle bound, not a claim. Bootstrap CIs share one resample
matrix across configs (paired, seed 2718). Docket verdict rule: KEEP iff
the Look-Again chord beats best-single beyond overlapping CIs AND buying
the independent symbolic reader lifts the ceiling more than buying a
correlated dense one. Dense models used plain (no retrieval prompt) —
honest out-of-the-box folds, no per-model prompt tuning.
"""
from __future__ import annotations

import itertools
import json
import os
import re
import sys
import time
from pathlib import Path

import numpy as np
import torch

SEED = 2718
LAB = Path(__file__).resolve().parents[1]
RESULTS_DIR = LAB / "results"
CURVE_JSON = RESULTS_DIR / "d1_reach_bound_curve.json"

DENSE_MODELS = [
    "BAAI/bge-small-en-v1.5",
    "sentence-transformers/all-MiniLM-L6-v2",
    "thenlper/gte-small",
]
SYMBOLIC = "counting-address"
READER_KEYS = ["d1_bge", "d2_minilm", "d3_gte", "s_symbolic"]

N_ITEMS = int(os.environ.get("D1_N", "600"))
N_BOOT = int(os.environ.get("D1_BOOT", "1000"))
CALIB_FRAC = 0.25

# ---------------------------------------------------------------- synthetic corpus
SUBJECTS = ["the lighthouse keeper", "the harbor master", "the night welder",
            "the tide clerk", "the rope quartermaster", "the signalman",
            "the boilerman", "the pier warden"]
VERBS = ["photographed", "cataloged", "inspected", "measured", "sketched",
         "inventoried", "checked", "logged"]
OBJECTS = ["the fog bell", "the mooring lines", "the tide gauge",
           "the cargo manifest", "the lamp glass", "the bilge pump",
           "the signal flags", "the anchor chain"]
SHIFTS = ["at dawn", "before dusk", "at noon", "after midnight"]
CARGO = ["crates of limes", "barrels of pitch", "rolls of canvas",
         "kegs of nails", "bolts of wool", "tins of oil",
         "bundles of rope", "cases of lamps"]
COUNTS = [3, 5, 7, 8, 11, 12, 14, 17, 19, 21, 24, 27]


def _semantic_item(rng: np.random.Generator) -> dict:
    s = rng.choice(SUBJECTS)
    v = rng.choice(VERBS)
    o = rng.choice(OBJECTS)
    shift = rng.choice(SHIFTS)
    if rng.random() < 0.5:  # gold: supported — claim restates the evidence line
        claim = f"{s} {v} {o} {shift}."
        main = f"{s} {v} {o} {shift}."
        gold = 1
    elif rng.random() < 0.5:  # negative: polarity flip ("never" — hard for dense)
        claim = f"{s} {v} {o} {shift}."
        main = f"{s} never {v} {o} {shift}."
        gold = 0
    else:  # negative: object mismatch, with O2 present in a distractor line
        o2 = rng.choice([x for x in OBJECTS if x != o])
        claim = f"{s} {v} {o2} {shift}."
        main = f"{s} {v} {o} {shift}."
        gold = 0
    n_distract = int(rng.integers(2, 4))
    distractors = []
    while len(distractors) < n_distract:
        ds, dv, do = rng.choice(SUBJECTS), rng.choice(VERBS), rng.choice(OBJECTS)
        if (ds, dv, do) == (s, v, o):
            continue
        distractors.append(f"{ds} {dv} {do} {rng.choice(SHIFTS)}.")
    evidence = main + " " + " ".join(distractors)
    return {"kind": "semantic", "claim": claim, "evidence": evidence, "gold": gold}


def _manifest_line(fam: str, mid: int, d: int, n: int, c: str) -> str:
    if fam == "A":
        return f"Manifest AX-{mid}: dock {d} holds {n} {c}."
    if fam == "B":
        return f"Dock {d} — {n} {c} logged at dawn."
    return f"{n} {c} at dock {d}, sealed."  # fam C: inverted, outside symbolic grammar


def _counting_item(rng: np.random.Generator) -> dict:
    fam = str(rng.choice(["A", "B", "C"], p=[0.35, 0.35, 0.30]))
    mid = int(rng.integers(1000, 9999))
    dt = int(rng.integers(1, 10))
    ct = str(rng.choice(CARGO))
    nt = int(rng.choice(COUNTS))
    docks = [d for d in range(1, 10) if d != dt]
    others = rng.choice(docks, size=int(rng.integers(3, 6)), replace=False)
    lines, other_counts = [], []
    lines.append(_manifest_line(fam, mid, dt, nt, ct))  # plant the truth
    for d in others:
        if rng.random() < 0.5:
            c = ct  # same cargo at other docks — harder for embeddings
        else:
            c = str(rng.choice([x for x in CARGO if x != ct]))
        while True:
            n = int(rng.choice(COUNTS))
            if n != nt:
                break
        other_counts.append(n)
        lines.append(_manifest_line(fam, mid, int(d), n, c))
    rng.shuffle(lines)
    filler = (f"Manifest AX-{mid} filed by the pier warden."
              if fam != "C" else f"Sheet {mid} filed by the pier warden.")
    evidence = " ".join(lines) + " " + filler
    if rng.random() < 0.5:  # gold: supported — exact planted (dock, count, cargo)
        claim = f"Dock {dt} holds {nt} {ct}."
        gold = 1
    else:  # near-miss count, present verbatim at another dock
        wrong = int(rng.choice(other_counts)) if other_counts else (nt + 1) % 28
        claim = f"Dock {dt} holds {wrong} {ct}."
        gold = 0
    return {"kind": "counting", "claim": claim, "evidence": evidence,
            "gold": gold, "dock": dt, "count": nt if gold else None,
            "family": fam}


def generate_items(n: int, rng: np.random.Generator) -> list:
    items, seen = [], set()
    n_count = int(n * 0.40)
    while len(items) < n:
        it = _counting_item(rng) if len(items) < n_count else _semantic_item(rng)
        key = (it["claim"], it["evidence"])
        if key in seen:
            continue
        seen.add(key)
        items.append(it)
    rng.shuffle(items)
    return items


# ---------------------------------------------------------------- readers
def symbolic_witness(claim: str, evidence: str) -> int:
    """Counting-address reader (G21). +1 supported / -1 refuted / 0 cannot-reach."""
    m = re.fullmatch(r"Dock (\d+) holds (\d+) (.+?)\.", claim.strip())
    if not m:
        return 0
    d, n, c = int(m.group(1)), int(m.group(2)), m.group(3).lower()
    norm = lambda x: re.sub(r"\s+", " ", x.strip().lower())
    entries: dict[int, set] = {}
    for a, b, cc in re.findall(r"Manifest AX-\d+: dock (\d+) holds (\d+) ([a-z ]+?)\.",
                               evidence, re.I):
        entries.setdefault(int(a), set()).add((int(b), norm(cc)))
    for a, b, cc in re.findall(r"[Dd]ock (\d+) [—–-] (\d+) ([a-z ]+?) logged", evidence):
        entries.setdefault(int(a), set()).add((int(b), norm(cc)))
    if d not in entries:
        return 0  # Reach Bound: the claim's address is not in this reader's grammar
    if len(entries[d]) > 1:
        return -1  # manifest contradicts itself — refuted
    (n2, c2), = entries[d]
    return 1 if (n2 == n and c2 == c) else -1


def calibrate_threshold(cos_calib: np.ndarray, gold_calib: np.ndarray) -> float:
    grid = np.unique(np.quantile(cos_calib, np.linspace(0.02, 0.98, 49)))
    accs = [((cos_calib > t).astype(float) == gold_calib).mean() for t in grid]
    return float(grid[int(np.argmax(accs))])


def chord(wit: np.ndarray) -> np.ndarray:
    """The fold: mean witness > 0 → supported. Abstains (0) don't vote."""
    return (wit.sum(axis=0) > 0).astype(np.int64)


def boot_ci(acc: np.ndarray, idx: np.ndarray) -> tuple:
    means = acc[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def main() -> dict:
    t0 = time.time()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    rng = np.random.default_rng(SEED)
    if dev == "cuda":
        torch.cuda.reset_peak_memory_stats()

    items = generate_items(N_ITEMS, rng)
    n = len(items)
    claims = [it["claim"] for it in items]
    evids = [it["evidence"] for it in items]
    gold = np.array([it["gold"] for it in items], dtype=np.int64)
    kinds = np.array([it["kind"] for it in items])
    n_calib = int(n * CALIB_FRAC)
    calib, evalm = np.arange(n) < n_calib, np.arange(n) >= n_calib

    # one shared bootstrap resample matrix → all comparisons are paired
    boot_idx = rng.integers(0, int(evalm.sum()), size=(N_BOOT, int(evalm.sum())))

    # symbolic reader (no GPU, exact reach)
    sym = np.array([symbolic_witness(c, e) for c, e in zip(claims, evids)], dtype=np.int64)

    # dense readers: encode once per model under its own weights (Law 6)
    from sentence_transformers import SentenceTransformer
    cos_all = {}
    for key, mname in zip(READER_KEYS[:3], DENSE_MODELS):
        st = SentenceTransformer(mname, device=dev)
        ce = st.encode(claims, batch_size=128, normalize_embeddings=True,
                       convert_to_numpy=True, show_progress_bar=False)
        ee = st.encode(evids, batch_size=128, normalize_embeddings=True,
                       convert_to_numpy=True, show_progress_bar=False)
        cos_all[key] = (ce * ee).sum(axis=1).astype(np.float32)  # normalized → dot = cos
        print(f"[d1] {mname}: encoded {n} claim/evidence pairs", file=sys.stderr, flush=True)
        del st, ce, ee
        if dev == "cuda":
            torch.cuda.empty_cache()

    # per-reader thresholds on the calibration split, then witnesses everywhere
    wit = np.zeros((4, n), dtype=np.int64)
    wit[3] = sym
    thresholds = {}
    for i, key in enumerate(READER_KEYS[:3]):
        t = calibrate_threshold(cos_all[key][calib], gold[calib].astype(float))
        thresholds[key] = t
        wit[i] = (cos_all[key] > t).astype(np.int64)

    # ---------------------------------------------------------------- sweep
    combos = [c for k in range(1, 5) for c in itertools.combinations(range(4), k)]

    def chord_pred(subset, mask):
        return chord(wit[list(subset)][:, mask])

    def score(subset, mask):
        """Point accuracy + bootstrap CI on `mask` items."""
        a = (chord_pred(subset, mask) == gold[mask]).astype(np.float64)
        return a, a.mean()

    cache_eval, cache_cal = {}, {}
    for c in combos:
        cache_eval[c] = score(c, evalm)
        cache_cal[c] = score(c, calib)

    def eval_ci(subset):
        lo, hi = boot_ci(cache_eval[subset][0], boot_idx)
        return float(cache_eval[subset][1]), [lo, hi], cache_eval[subset][0]

    # selection happens on CALIBRATION only (no peeking at eval)
    best_single_cal = max((c for c in combos if len(c) == 1), key=lambda c: cache_cal[c][1])
    best_chord_cal = max(combos, key=lambda c: (cache_cal[c][1], -len(c)))
    dense_only = tuple(range(3))
    best_dense_base_cal = max((c for c in combos if set(c) <= set(dense_only)),
                              key=lambda c: (cache_cal[c][1], -len(c)))
    # correlated purchase: best dense ADDITION to the base, by calibration
    extra_dense = [c for c in combos
                   if set(dense_only) <= set(c) and set(c) > set(best_dense_base_cal)]
    extra_dense = [c for c in extra_dense
                   if len(c) == len(best_dense_base_cal) + 1]
    best_extra_dense_cal = (max(extra_dense, key=lambda c: cache_cal[c][1])
                            if extra_dense else best_dense_base_cal)
    base_plus_sym = tuple(sorted(set(best_dense_base_cal) | {3}))

    singles = {}
    for i, key in enumerate(READER_KEYS):
        acc, ci, a = eval_ci((i,))
        pred = wit[i][evalm]
        singles[key] = {
            "acc": acc, "ci95": ci,
            "acc_semantic": float((a[kinds[evalm] == "semantic"]).mean()),
            "acc_counting": float((a[kinds[evalm] == "counting"]).mean()),
            "supported_rate": float((pred == 1).mean()),
            "abstain_rate": float((pred == 0).mean()),
        }

    # honest per-k curve: calib-selected subset of each size, eval-scored
    curve = []
    for k in range(1, 5):
        cands = [c for c in combos if len(c) == k]
        best_cal = max(cands, key=lambda c: (cache_cal[c][1], -len(c)))
        acc, ci, a = eval_ci(best_cal)
        row = {"k": k, "readers": [READER_KEYS[i] for i in best_cal],
               "acc": acc, "ci95": ci}
        if k > 1:
            prev_c = max((c for c in combos if len(c) == k - 1),
                         key=lambda c: (cache_cal[c][1], -len(c)))
            diff = a - cache_eval[prev_c][0]
            dlo, dhi = boot_ci(diff, boot_idx)
            row["lift_vs_best_prev"] = float(diff.mean())
            row["lift_ci95"] = [dlo, dhi]
        curve.append(row)

    # descriptive envelope: eval-best subset per k (oracle bound — selected on
    # eval, reported for transparency only, never carries the verdict)
    envelope = []
    for k in range(1, 5):
        best_e = max((c for c in combos if len(c) == k), key=lambda c: cache_eval[c][1])
        acc, ci, _ = eval_ci(best_e)
        envelope.append({"k": k, "readers": [READER_KEYS[i] for i in best_e],
                         "acc": acc, "ci95": ci})

    def subset_acc(subset, mask):
        return float((chord_pred(subset, mask) == gold[mask]).mean())

    sem_mask, cnt_mask = kinds == "semantic", kinds == "counting"

    def row(subset):
        acc, ci, _ = eval_ci(subset)
        return {"readers": [READER_KEYS[i] for i in subset], "acc": acc, "ci95": ci,
                "acc_semantic": subset_acc(subset, sem_mask),
                "acc_counting": subset_acc(subset, cnt_mask)}

    dc = dense_only
    dcs = tuple(range(4))
    ablation = {
        "best_single_calib_selected": row(best_single_cal),
        "dense_chord_all3": row(dc),
        "dense_chord_plus_symbolic": row(dcs),
        "look_again_chord_calib_selected": row(best_chord_cal),
        "symbolic_alone": row((3,)),
        "dense_base_calib_selected": row(best_dense_base_cal),
        "dense_base_plus_symbolic": row(base_plus_sym),
        "dense_base_plus_correlated_dense": row(best_extra_dense_cal),
    }

    # ceiling lifts (point estimates, eval)
    lift_la = ablation["look_again_chord_calib_selected"]["acc"] \
        - ablation["best_single_calib_selected"]["acc"]
    lift_sym = ablation["dense_base_plus_symbolic"]["acc"] \
        - ablation["dense_base_calib_selected"]["acc"]
    lift_corr = ablation["dense_base_plus_correlated_dense"]["acc"] \
        - ablation["dense_base_calib_selected"]["acc"]

    # chord diagnostics: why do liberal dense votes hurt?
    dc_pred = chord_pred(dc, evalm)
    dc_wit = wit[list(dc)][:, evalm]
    splits = ((dc_wit.sum(axis=0) != 0) & (dc_wit.min(axis=0) != dc_wit.max(axis=0)))
    pairwise = [float((wit[i][evalm] == wit[j][evalm]).mean())
                for i, j in itertools.combinations(range(3), 2)]

    # ---------------------------------------------------------- verdict (docket rule)
    chord_acc, chord_ci, _ = eval_ci(best_chord_cal)
    single_acc, single_ci, _ = eval_ci(best_single_cal)
    c1 = chord_acc > single_acc and chord_ci[0] > single_ci[1]  # CIs don't overlap
    diff_sym = cache_eval[base_plus_sym][0] - cache_eval[best_dense_base_cal][0]
    sym_lo, _ = boot_ci(diff_sym, boot_idx)
    c2 = lift_sym > lift_corr and sym_lo > 0
    if c1 and c2:
        verdict, reason = "KEEP", ("calib-selected chord beats calib-selected best-single "
                                   "beyond overlapping CIs, and the independent symbolic "
                                   "purchase out-lifts a correlated dense purchase")
    elif not c1 and not c2:
        verdict, reason = "KILL", "neither arm of the docket rule cleared (lift within CI noise)"
    else:
        verdict = "INCONCLUSIVE"
        reason = ("chord-vs-best-single arm cleared" if c1 else "chord-vs-best-single arm failed") + \
                 ("; symbolic-purchase arm cleared" if c2 else "; symbolic-purchase arm failed")

    peak_mib = (torch.cuda.max_memory_allocated() / 2**20) if dev == "cuda" else 0
    out = {
        "experiment": "D1 look-again-scale (reach-bound fold sweep)",
        "device": dev,
        "seed": SEED,
        "n_items": int(n),
        "n_semantic": int((kinds == "semantic").sum()),
        "n_counting": int((kinds == "counting").sum()),
        "n_calib": int(calib.sum()),
        "n_eval": int(evalm.sum()),
        "gold_balance_eval": float(gold[evalm].mean()),
        "readers": {**{k: m for k, m in zip(READER_KEYS[:3], DENSE_MODELS)},
                    "s_symbolic": SYMBOLIC},
        "calibrated_thresholds": thresholds,
        "singles": singles,
        "sweep": ablation,
        "curve_calib_selected_by_k": curve,
        "curve_eval_best_envelope_oracle": envelope,
        "chord_diagnostics": {
            "dense_pairwise_witness_agreement_eval": pairwise,
            "dense_chord_2_1_split_rate_eval": float(splits.mean()),
            "dense_chord_supported_rate_eval": float((dc_pred == 1).mean()),
            "note": "majority vote of correlated biased readers can underperform "
                    "the best member — lift must come from reach, not vote count",
        },
        "ceiling_lift": {
            "look_again_chord_vs_best_single": float(lift_la),
            "symbolic_purchase_on_dense_base": float(lift_sym),
            "correlated_dense_purchase_on_dense_base": float(lift_corr),
        },
        "bootstrap_draws": N_BOOT,
        "peak_vram_mib": round(float(peak_mib), 1),
        "runtime_s": round(time.time() - t0, 1),
        "verdict": verdict,
        "verdict_reason": reason,
    }
    RESULTS_DIR.mkdir(exist_ok=True)
    CURVE_JSON.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
