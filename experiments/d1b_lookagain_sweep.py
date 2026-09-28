"""D1b — look-again sweep: a ready-to-run, bundled-corpus packaging of D1.

D1 (`experiments/d1_look_again_scale.py`, KEEP, 2026-09-27) already showed
that G21's Look-Again effect survives at N=600: buying a reader with
INDEPENDENT REACH (the counting-address symbolic reader — Law 7, the Reach
Bound: a fold can't land a truth no reader's evidence reaches) beats
best-single, while buying a CORRELATED reader (another dense embedder) does
not. This module packages that same doctrine for a zero-friction overnight
run: a committed item set (no network needed to get *an* answer), an
explicit oracle/safe-fold/Look-Again comparison (not just a chord sweep),
and a scaling readout over #items and #readers so the local agent can see
where the reach bound actually bites as N grows.

Readers.
  - DENSE (LLM-strong): sentence-embedding models, each folding
    content-addressed evidence under its OWN weights (Law 6, "a fold is
    real only once more than one reader can fold it" — jev-quilt
    `g20b.rs`). Real models (`bge-small-en-v1.5`, `all-MiniLM-L6-v2`,
    `gte-small`) are tried first; if `sentence-transformers`/`torch` or the
    model weights are unreachable, each dense slot falls back to a
    deterministic hashing-trick embedding (own seeded random projection —
    still "own weights", just cheaper and always available). This is what
    makes the script runnable with zero setup: no GPU, no network, no
    pip installs required for a correctness smoke pass.
  - SYMBOLIC (LLM-blind reach): the G21 counting-address reader — exact
    dock/count/cargo parse against a limited grammar. It reaches truths the
    dense readers structurally can't bind (number->address attribution) and
    HONESTLY ABSTAINS outside its grammar (one manifest family is written in
    a format it cannot parse) — the reach bound is a real, finite fence, not
    an assumption.

Metrics (the four things the docket asks for, per item-subset):
  - best_single      — best individual dense reader, SELECTED on the
                        calibration split, SCORED on held-out eval.
  - oracle(D)         — existential ceiling over the dense readers alone:
                        an item counts if ANY dense reader's witness is
                        correct. The best any selector could ever do
                        without buying reach.
  - oracle(D+S)       — same ceiling with the symbolic (bought-reach)
                        reader added. If this doesn't rise past oracle(D),
                        the reach purchase bought nothing.
  - safe_fold(D[,+S]) — the naive combiner: majority vote (the "chord"),
                        no oracle peeking. D1 already showed this can LOSE
                        to best-single when dense witnesses are correlated
                        and liberal — booked here again as a control.
  - look_again        — the deliberate purchase: default to best_single's
                        witness, OVERRIDE with the symbolic reader's
                        witness wherever it has reach (non-abstain). This is
                        literally "buy the independent-reach reader at the
                        addresses where the others are blind."

HONESTY RULES (same as D1): thresholds and best-single/best-pool selection
happen on the calibration split ONLY; every reported accuracy is scored on
the held-out eval split. Bootstrap CIs (seed 2718) share one resample index
matrix so paired comparisons (look_again vs best_single) are apples-to-apples.
Smoke runs (the default, no env vars) never claim KEEP/KILL — they print
INCONCLUSIVE (smoke) and name the full-scale recipe, exactly like D4/D15.

Knobs (env vars — all optional, sane defaults give a fast offline smoke run):
  D1B_FULL=1        run the docket-scale sweep: generate D1B_N items on the
                     fly (default 3000) instead of the committed bundle, use
                     more bootstrap draws, and let a verdict be KEEP/KILL.
  D1B_N             item count (default: full bundle in smoke mode, 3000 in
                     full mode).
  D1B_BOOT          bootstrap draws (default 500 smoke / 2000 full).
  D1B_FORCE_HASH=1  force the offline hashing-trick embedding even if
                     sentence-transformers/torch are available (fast dev
                     loop, or an air-gapped box).
  D1B_MODELS        comma-separated HF model ids, default the lab's usual
                     three (bge-small-en-v1.5, all-MiniLM-L6-v2, gte-small).

VRAM / time. The docket's <2 GB envelope: 3 sentence-embedding models
(~130-400 MB combined) plus cached claim/evidence tensors for a few
thousand items is well under 1 GB; the symbolic reader and the hashing
fallback never touch the GPU at all.

Run: `python -m experiments.d1b_lookagain_sweep` (smoke, no setup) or
`D1B_FULL=1 python -m experiments.d1b_lookagain_sweep` (the overnight sweep).
"""
from __future__ import annotations

import itertools
import json
import os
import re
import sys
import time
import zlib
from pathlib import Path
from typing import List, Tuple

import numpy as np

try:
    import torch
    HAVE_TORCH = True
except Exception:  # pragma: no cover - exercised by the CPU-only smoke box
    HAVE_TORCH = False

SEED = 2718
LAB = Path(__file__).resolve().parents[1]
RESULTS_DIR = LAB / "results"
SCALING_JSON = RESULTS_DIR / "d1_lookagain_scaling.json"
BUNDLE_PATH = Path(__file__).resolve().parent / "data" / "d1_lookagain_items.jsonl"

DEFAULT_MODELS = [
    "BAAI/bge-small-en-v1.5",
    "sentence-transformers/all-MiniLM-L6-v2",
    "thenlper/gte-small",
]
CALIB_FRAC = 0.25

FULL = os.environ.get("D1B_FULL", "0") == "1"
N_ITEMS = int(os.environ.get("D1B_N", "3000" if FULL else "0"))  # 0 = "use whole bundle"
N_BOOT = int(os.environ.get("D1B_BOOT", "2000" if FULL else "500"))
FORCE_HASH = os.environ.get("D1B_FORCE_HASH", "0") == "1"
MODELS = os.environ.get("D1B_MODELS", ",".join(DEFAULT_MODELS)).split(",")

# ============================================================== the corpus
# Two address families, by construction:
#   "semantic"  — LLM-strong: paraphrase / negation / object-swap over a
#                 natural-language claim. Dense embedders bind this well.
#   "counting"  — LLM-blind: a claim about an exact (dock, count, cargo)
#                 triple planted among near-miss distractors. Binding a
#                 specific NUMBER to a specific ADDRESS is the well-known
#                 dense-embedding weak spot; the symbolic reader is built to
#                 reach exactly this address (and only this address).
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
    s, v, o = rng.choice(SUBJECTS), rng.choice(VERBS), rng.choice(OBJECTS)
    shift = rng.choice(SHIFTS)
    roll = rng.random()
    if roll < 0.5:  # gold: supported — claim restates the evidence line
        claim = main = f"{s} {v} {o} {shift}."
        gold = 1
    elif roll < 0.75:  # negative: polarity flip — hard for pure similarity
        claim = f"{s} {v} {o} {shift}."
        main = f"{s} never {v} {o} {shift}."
        gold = 0
    else:  # negative: object mismatch (a near-duplicate object appears)
        o2 = rng.choice([x for x in OBJECTS if x != o])
        claim = f"{s} {v} {o2} {shift}."
        main = f"{s} {v} {o} {shift}."
        gold = 0
    n_distract = int(rng.integers(2, 4))
    distractors, seen_d = [], set()
    while len(distractors) < n_distract:
        ds, dv, do = rng.choice(SUBJECTS), rng.choice(VERBS), rng.choice(OBJECTS)
        if (ds, dv, do) == (s, v, o) or (ds, dv, do) in seen_d:
            continue
        seen_d.add((ds, dv, do))
        distractors.append(f"{ds} {dv} {do} {rng.choice(SHIFTS)}.")
    evidence = main + " " + " ".join(distractors)
    return {"kind": "semantic", "claim": claim, "evidence": evidence, "gold": gold}


def _manifest_line(fam: str, mid: int, d: int, n: int, c: str) -> str:
    if fam == "A":
        return f"Manifest AX-{mid}: dock {d} holds {n} {c}."
    if fam == "B":
        return f"Dock {d} - {n} {c} logged at dawn."
    return f"{n} {c} at dock {d}, sealed."  # fam C: outside the symbolic grammar


def _counting_item(rng: np.random.Generator) -> dict:
    fam = str(rng.choice(["A", "B", "C"], p=[0.35, 0.35, 0.30]))
    mid = int(rng.integers(1000, 9999))
    dt = int(rng.integers(1, 10))
    ct = str(rng.choice(CARGO))
    nt = int(rng.choice(COUNTS))
    docks = [d for d in range(1, 10) if d != dt]
    others = rng.choice(docks, size=int(rng.integers(3, 6)), replace=False)
    lines, other_counts = [_manifest_line(fam, mid, dt, nt, ct)], []
    for d in others:
        c = ct if rng.random() < 0.5 else str(rng.choice([x for x in CARGO if x != ct]))
        while True:
            n = int(rng.choice(COUNTS))
            if n != nt:
                break
        other_counts.append(n)
        lines.append(_manifest_line(fam, mid, int(d), n, c))
    rng.shuffle(lines)
    filler = (f"Manifest AX-{mid} filed by the pier warden." if fam != "C"
              else f"Sheet {mid} filed by the pier warden.")
    evidence = " ".join(lines) + " " + filler
    if rng.random() < 0.5:  # gold: supported — exact planted (dock, count, cargo)
        claim, gold = f"Dock {dt} holds {nt} {ct}.", 1
    else:  # near-miss: a count that IS present, just at another dock
        wrong = int(rng.choice(other_counts)) if other_counts else (nt + 1) % 28
        claim, gold = f"Dock {dt} holds {wrong} {ct}.", 0
    return {"kind": "counting", "claim": claim, "evidence": evidence, "gold": gold, "family": fam}


def generate_items(n: int, rng: np.random.Generator) -> List[dict]:
    items, seen, n_count = [], set(), int(n * 0.5)
    while len(items) < n:
        it = _counting_item(rng) if len(items) < n_count else _semantic_item(rng)
        key = (it["claim"], it["evidence"])
        if key in seen:
            continue
        seen.add(key)
        items.append(it)
    rng.shuffle(items)
    return items


def load_bundle(path: Path) -> List[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_bundle(items: List[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(it, sort_keys=True) for it in items) + "\n")


# ============================================================ symbolic reader
def symbolic_witness(claim: str, evidence: str) -> int:
    """The G21 counting-address reader. +1 supported / -1 refuted / 0
    cannot-reach (the honest reach limit — family C is outside its grammar).
    """
    m = re.fullmatch(r"Dock (\d+) holds (\d+) (.+?)\.", claim.strip())
    if not m:
        return 0
    d, n, c = int(m.group(1)), int(m.group(2)), m.group(3).lower()
    norm = lambda x: re.sub(r"\s+", " ", x.strip().lower())
    entries: dict = {}
    for a, b, cc in re.findall(r"Manifest AX-\d+: dock (\d+) holds (\d+) ([a-z ]+?)\.",
                                evidence, re.I):
        entries.setdefault(int(a), set()).add((int(b), norm(cc)))
    for a, b, cc in re.findall(r"[Dd]ock (\d+) - (\d+) ([a-z ]+?) logged", evidence):
        entries.setdefault(int(a), set()).add((int(b), norm(cc)))
    if d not in entries:
        return 0  # Reach Bound: this claim's address is not in this reader's grammar
    if len(entries[d]) > 1:
        return -1  # self-contradicting manifest -> refuted
    (n2, c2), = entries[d]
    return 1 if (n2 == n and c2 == c) else -1


# ================================================================ dense readers
class HashReader:
    """Deterministic hashing-trick embedding: no download, no network, no
    torch required. Each instance gets its OWN seeded random projection
    (Law 6's "own weights"), so it stands in for an independent embedder
    when a real model is unreachable — the fallback that makes this script
    runnable anywhere, at reduced fidelity relative to a real model.
    """
    def __init__(self, seed: int, dim: int = 512, proj_dim: int = 96, device: str = "cpu"):
        self.dim, self.device = dim, device
        rng = np.random.default_rng(seed)
        self.proj = rng.standard_normal((dim, proj_dim)).astype(np.float32) / np.sqrt(proj_dim)

    def _hash_vec(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        for tok in re.findall(r"[a-z0-9]+", text.lower()):
            h = zlib.crc32(tok.encode())
            vec[h % self.dim] += 1.0 if (h >> 16) % 2 == 0 else -1.0
        return vec

    def encode(self, texts: List[str]) -> np.ndarray:
        counts = np.stack([self._hash_vec(t) for t in texts])
        if HAVE_TORCH:
            ct = torch.from_numpy(counts).to(self.device)
            pt = torch.from_numpy(self.proj).to(self.device)
            emb = torch.nn.functional.normalize(ct @ pt, dim=1)
            return emb.cpu().numpy().astype(np.float32)
        emb = counts @ self.proj
        norms = np.linalg.norm(emb, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (emb / norms).astype(np.float32)


class STReader:
    """A real sentence-embedding model (GPU-accelerated by sentence-transformers
    itself when `device == 'cuda'`)."""
    def __init__(self, model_name: str, device: str):
        from sentence_transformers import SentenceTransformer
        self.model_name = model_name
        self.st = SentenceTransformer(model_name, device=device)

    def encode(self, texts: List[str]) -> np.ndarray:
        return self.st.encode(texts, batch_size=128, normalize_embeddings=True,
                               convert_to_numpy=True, show_progress_bar=False)


def build_dense_reader(model_name: str, seed: int, device: str, force_hash: bool
                        ) -> Tuple[object, str]:
    if not force_hash:
        try:
            return STReader(model_name, device), "sentence-transformers"
        except Exception as exc:
            print(f"[d1b] {model_name}: real model unavailable "
                  f"({exc.__class__.__name__}: {exc}) -> hashing-trick fallback",
                  file=sys.stderr, flush=True)
    return HashReader(seed, device=device), "hash-fallback"


def cosine_pairs(a: np.ndarray, b: np.ndarray, device: str) -> np.ndarray:
    """Paired cosine (both already L2-normalized) — the GPU-accelerated
    scoring step when torch/CUDA are available, numpy otherwise."""
    if HAVE_TORCH:
        ta, tb = torch.from_numpy(a).to(device), torch.from_numpy(b).to(device)
        return (ta * tb).sum(dim=1).cpu().numpy().astype(np.float32)
    return (a * b).sum(axis=1).astype(np.float32)


def calibrate_threshold(cos_calib: np.ndarray, gold_calib: np.ndarray) -> float:
    grid = np.unique(np.quantile(cos_calib, np.linspace(0.02, 0.98, 49)))
    accs = [((cos_calib > t).astype(float) == gold_calib).mean() for t in grid]
    return float(grid[int(np.argmax(accs))])


# =================================================================== metrics
def pred(witness: np.ndarray) -> np.ndarray:
    """witness in {-1, 0, +1} -> a binary supported/not-supported call.
    Abstain (0) and refute (-1) both read as "not supported" — conservative,
    matching D1's convention."""
    return (witness > 0).astype(np.int64)


def oracle_acc(wit_stack: np.ndarray, gold: np.ndarray) -> Tuple[float, np.ndarray]:
    """Existential ceiling: an item counts if ANY reader in the stack is
    correct on it. Never a claim about what a real selector achieves —
    the ceiling any selector could ever reach."""
    preds = pred(wit_stack)  # (R, n)
    hit = (preds == gold[None, :]).any(axis=0)
    return float(hit.mean()), hit.astype(np.float64)


def safe_fold(wit_stack: np.ndarray) -> np.ndarray:
    """The naive, no-oracle combiner: majority vote. Abstains don't vote;
    ties read not-supported (conservative)."""
    return (wit_stack.sum(axis=0) > 0).astype(np.int64)


def look_again_pred(best_witness: np.ndarray, reach_witness: np.ndarray) -> np.ndarray:
    """The deliberate purchase: trust best_single everywhere, EXCEPT at the
    addresses where the bought reach reader has evidence (non-abstain) —
    there, trust it instead. This is the literal "buy the reader at its
    addresses" mechanic, distinct from a blind vote."""
    base = pred(best_witness)
    has_reach = reach_witness != 0
    return np.where(has_reach, pred(reach_witness), base)


def boot_ci(correct: np.ndarray, idx: np.ndarray) -> Tuple[float, float]:
    means = correct[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


# ===================================================================== sweep
def score_pool(dense_idx: Tuple[int, ...], wit: np.ndarray, gold: np.ndarray,
               calib: np.ndarray, evalm: np.ndarray, sym_row: int) -> dict:
    """Everything the docket asks for, for one pool of dense readers."""
    d_wit_calib, d_wit_eval = wit[list(dense_idx)][:, calib], wit[list(dense_idx)][:, evalm]
    gold_calib, gold_eval = gold[calib], gold[evalm]

    single_accs_calib = [(pred(d_wit_calib[i]) == gold_calib).mean() for i in range(len(dense_idx))]
    best_local = int(np.argmax(single_accs_calib))  # index within dense_idx, calib-selected
    best_witness_eval = d_wit_eval[best_local]
    best_single_acc = float((pred(best_witness_eval) == gold_eval).mean())

    oracle_d_acc, _ = oracle_acc(d_wit_eval, gold_eval)
    all_idx_eval = np.concatenate([d_wit_eval, wit[sym_row][evalm][None, :]], axis=0)
    oracle_ds_acc, _ = oracle_acc(all_idx_eval, gold_eval)

    fold_d = safe_fold(d_wit_eval)
    fold_d_acc = float((fold_d == gold_eval).mean())
    fold_ds = safe_fold(all_idx_eval)
    fold_ds_acc = float((fold_ds == gold_eval).mean())

    la_pred = look_again_pred(best_witness_eval, wit[sym_row][evalm])
    la_correct = (la_pred == gold_eval).astype(np.float64)
    la_acc = float(la_correct.mean())

    return {
        "dense_readers": list(dense_idx),
        "best_single_acc": best_single_acc,
        "oracle_dense_acc": float(oracle_d_acc),
        "oracle_dense_plus_reach_acc": float(oracle_ds_acc),
        "safe_fold_dense_acc": fold_d_acc,
        "safe_fold_dense_plus_reach_acc": fold_ds_acc,
        "look_again_acc": la_acc,
        "look_again_minus_best_single": la_acc - best_single_acc,
        "reach_ceiling_lift": float(oracle_ds_acc - oracle_d_acc),
        "_best_witness_eval": best_witness_eval,
        "_la_correct": la_correct,
        "_best_correct": (pred(best_witness_eval) == gold_eval).astype(np.float64),
    }


def main() -> dict:
    t0 = time.time()
    np.random.seed(SEED)
    rng = np.random.default_rng(SEED)
    device = "cuda" if (HAVE_TORCH and torch.cuda.is_available()) else "cpu"
    if HAVE_TORCH:
        torch.manual_seed(SEED)
        if device == "cuda":
            torch.cuda.reset_peak_memory_stats()

    # --------------------------------------------------------- item set
    if N_ITEMS > 0:
        items = generate_items(N_ITEMS, rng)
        item_source = f"generated (D1B_N={N_ITEMS})"
    else:
        items = load_bundle(BUNDLE_PATH)
        rng.shuffle(items)
        item_source = f"bundle:{BUNDLE_PATH.name} (n={len(items)})"
    n = len(items)
    claims = [it["claim"] for it in items]
    evids = [it["evidence"] for it in items]
    gold = np.array([it["gold"] for it in items], dtype=np.int64)
    kinds = np.array([it["kind"] for it in items])
    n_calib = max(8, int(n * CALIB_FRAC))
    calib_mask, eval_mask = np.arange(n) < n_calib, np.arange(n) >= n_calib
    boot_idx = rng.integers(0, int(eval_mask.sum()), size=(N_BOOT, int(eval_mask.sum())))

    # --------------------------------------------------------- readers
    n_dense = min(len(MODELS), 3)
    reader_backend = {}
    cos_all = []
    for i in range(n_dense):
        reader, backend = build_dense_reader(MODELS[i].strip(), SEED + i, device, FORCE_HASH)
        reader_backend[f"dense_{i}"] = {"model": MODELS[i].strip(), "backend": backend}
        ce, ee = reader.encode(claims), reader.encode(evids)
        cos_all.append(cosine_pairs(ce, ee, device))
        print(f"[d1b] dense_{i} ({backend}): encoded {n} pairs", file=sys.stderr, flush=True)
        del reader
        if HAVE_TORCH and device == "cuda":
            torch.cuda.empty_cache()

    wit = np.zeros((n_dense + 1, n), dtype=np.int64)
    thresholds = {}
    for i in range(n_dense):
        t = calibrate_threshold(cos_all[i][calib_mask], gold[calib_mask].astype(float))
        thresholds[f"dense_{i}"] = t
        wit[i] = (cos_all[i] > t).astype(np.int64)
    sym_row = n_dense
    wit[sym_row] = np.array([symbolic_witness(c, e) for c, e in zip(claims, evids)], dtype=np.int64)

    # --------------------------------------------------------- headline (full pool)
    full_pool = tuple(range(n_dense))
    headline = score_pool(full_pool, wit, gold, calib_mask, eval_mask, sym_row)
    la_correct = headline.pop("_la_correct")
    best_correct = headline.pop("_best_correct")
    headline.pop("_best_witness_eval")
    lift_lo, lift_hi = boot_ci(la_correct - best_correct, boot_idx)
    headline["lift_ci95"] = [lift_lo, lift_hi]
    best_lo, best_hi = boot_ci(best_correct, boot_idx)
    headline["best_single_ci95"] = [best_lo, best_hi]
    beats_ci = lift_lo > 0.0

    # correlated-purchase control: does buying a 2nd/3rd dense reader lift
    # the ceiling as much as buying the independent symbolic one? (n_dense>=2)
    correlated_lift = None
    if n_dense >= 2:
        one = score_pool((0,), wit, gold, calib_mask, eval_mask, sym_row)
        two_dense_oracle, _ = oracle_acc(wit[[0, 1]][:, eval_mask], gold[eval_mask])
        correlated_lift = float(two_dense_oracle - one["oracle_dense_acc"])

    # --------------------------------------------------------- scaling: #items
    sizes = sorted(set(max(20, int(n * f)) for f in (0.15, 0.3, 0.5, 0.75, 1.0)))
    by_items = []
    for sz in sizes:
        sub = np.arange(sz)
        sub_calib, sub_eval = sub < max(6, int(sz * CALIB_FRAC)), sub >= max(6, int(sz * CALIB_FRAC))
        sub_wit, sub_gold = wit[:, :sz], gold[:sz]
        row = score_pool(full_pool, sub_wit, sub_gold, sub_calib, sub_eval, sym_row)
        by_items.append({"n_items": sz, "best_single_acc": row["best_single_acc"],
                          "look_again_acc": row["look_again_acc"],
                          "lift": row["look_again_minus_best_single"],
                          "oracle_dense_plus_reach_acc": row["oracle_dense_plus_reach_acc"]})

    # --------------------------------------------------------- scaling: #readers
    by_readers = []
    for k in range(1, n_dense + 1):
        row = score_pool(tuple(range(k)), wit, gold, calib_mask, eval_mask, sym_row)
        by_readers.append({"n_dense_readers": k, "best_single_acc": row["best_single_acc"],
                            "look_again_acc": row["look_again_acc"],
                            "lift": row["look_again_minus_best_single"],
                            "oracle_dense_acc": row["oracle_dense_acc"],
                            "oracle_dense_plus_reach_acc": row["oracle_dense_plus_reach_acc"],
                            "reach_ceiling_lift": row["reach_ceiling_lift"]})

    # --------------------------------------------------------- verdict
    ceiling_rises = headline["reach_ceiling_lift"] > 0.0
    smoke = not FULL
    if smoke:
        verdict = "INCONCLUSIVE"
        reason = "smoke run (D1B_FULL unset) — pipeline-proof only, not the docket decision"
    elif beats_ci and ceiling_rises:
        verdict, reason = "KEEP", ("Look-Again beats best-single beyond a 95% bootstrap CI, "
                                    "and buying the reach reader raises the existential oracle "
                                    "ceiling over the dense pool alone")
    elif not beats_ci and not ceiling_rises:
        verdict, reason = "KILL", "neither the accuracy lift nor the ceiling lift cleared"
    else:
        verdict = "INCONCLUSIVE"
        reason = ("accuracy-lift arm cleared" if beats_ci else "accuracy-lift arm failed") + \
                 ("; ceiling-lift arm cleared" if ceiling_rises else "; ceiling-lift arm failed")

    peak_mib = (torch.cuda.max_memory_allocated() / 2**20) if (HAVE_TORCH and device == "cuda") else 0.0
    out = {
        "experiment": "D1b look-again sweep (bundled corpus, reach-bound scaling)",
        "mode": "full" if FULL else "smoke",
        "device": device,
        "have_torch": HAVE_TORCH,
        "seed": SEED,
        "item_source": item_source,
        "n_items": int(n),
        "n_semantic": int((kinds == "semantic").sum()),
        "n_counting": int((kinds == "counting").sum()),
        "n_calib": int(calib_mask.sum()),
        "n_eval": int(eval_mask.sum()),
        "n_dense_readers": n_dense,
        "readers": reader_backend,
        "symbolic_reader": "counting-address (G21)",
        "calibrated_thresholds": thresholds,
        "headline": headline,
        "correlated_dense_purchase_oracle_lift": correlated_lift,
        "scaling_by_items": by_items,
        "scaling_by_readers": by_readers,
        "bootstrap_draws": N_BOOT,
        "peak_vram_mib": round(float(peak_mib), 1),
        "runtime_s": round(time.time() - t0, 1),
        "verdict": verdict,
        "verdict_reason": reason,
    }
    RESULTS_DIR.mkdir(exist_ok=True)
    SCALING_JSON.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))
    print(f"DONE d1b_lookagain_sweep mode={out['mode']} device={device} "
          f"n_items={n} best_single={headline['best_single_acc']:.4f} "
          f"look_again={headline['look_again_acc']:.4f} "
          f"lift={headline['look_again_minus_best_single']:+.4f} "
          f"verdict={verdict}")
    return out


if __name__ == "__main__":
    if "--regen-bundle" in sys.argv:
        n_bundle = int(os.environ.get("D1B_BUNDLE_N", "320"))
        bundle_items = generate_items(n_bundle, np.random.default_rng(SEED))
        write_bundle(bundle_items, BUNDLE_PATH)
        print(f"[d1b] wrote {len(bundle_items)} items -> {BUNDLE_PATH}")
    else:
        main()
