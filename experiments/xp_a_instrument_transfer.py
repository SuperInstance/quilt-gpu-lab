#!/usr/bin/env python3
"""XP-A "instrument-transfer" — pre-registered 2026-10-01 (scout-2026-10-01-pushwave.md §1c).

CLAIM UNDER TEST (fleet-triage synergy mechanism, verbatim): "an instrument reports
success unless it has been given a way to fail." Falsifiable prediction: an
instrument's detection power against KNOWN failure classes predicts its power
against UNKNOWN (held-out) failure classes.

DESIGN
  Corpus: this lab's own verdict/booking machinery (experiments/st1_quilt_cell_v0.py
  receipt schema + generator + its 6 corruption ops = the KNOWN ops), rendered in
  template style. Master seed 2718; all child seeds drawn from it.

  KNOWN ops (6, from st1's own SYN_OPS): sign_flip, wins_over, verdict_flip,
  tau_off, seed_drop, denom_swap.
  HELD-OUT ops (4, novel, this script): nan_injection (float field <- NaN),
  dtype_cast (wins silently int->float), split_boundary (wins = threshold-1 with
  verdict kept KEEP), receipt_copy_prior (earlier receipt id re-certifies new
  state = chain-repair).

  INSTRUMENTS (3):
    A "verdict_gate pins"  — tools/verdict_gate.py finalize() wired to parsed
        booking fields (gates: wins_frac<=1, tau in [0.40,0.60], mri>=0 iff
        claimed KEEP; completeness = required fields present; n = n_pairs).
        Detect = verdict != PASS.
    B "step parser"        — canfail-style reimplementation: parses RESULTS.md-like
        entries for verdict/format invariants ONLY (frozen checks B1-B8 below).
        No op-specific knowledge; cross-entry state = seen receipt ids.
    C "trained classifier" — logistic regression on hashed char-3gram+token
        features of receipt text, trained on clean + KNOWN-op corrupt ONLY.
        Torch/CUDA under guard.py (house law: GPU => Guard + receipt), CPU-torch
        fallback declared. Frozen threshold = max balanced accuracy on a KNOWN-op
        validation split.

  FROZEN GATES (set before the run, derived from chance=0.5 for a binary detector
  under the balanced prior; no post-hoc tuning):
    chance            = 0.50  (coin-flip detector)
    BEATS_CHANCE      = held-out recall >= 0.60  (chance + ~2 binomial se, n=160)
    HIGH_KNOWN_POWER  = known recall   >= 0.65  (chance + 0.15: genuinely given
                        ways to fail)
    FLUNKS_HELD_OUT   = held-out recall <= 0.50  (at or below chance)
    KEEP iff Spearman(known-power, unknown-power) over instruments >= 0.70 AND
             every instrument BEATS_CHANCE on held-out.
    KILL iff any instrument has HIGH_KNOWN_POWER and FLUNKS_HELD_OUT.
             (Precedence KILL > KEEP: KILL is an existence condition — one
             non-transferring instrument falsifies the blanket claim.)
    INCONCLUSIVE iff valid grid < 3 instruments x 4 held-out ops, or C cannot be
             produced at all (GPU + declared fallback both fail).

  HOUSE LAWS: seed 2718 everywhere; fail loud; does not edit other lanes' ledger
  lines; no commit (keeper commits + re-seals receipt manifest).

CPU-LANE NOTE (2026-10-01): XP-A is booked as a CPU lane. The canonical
invocation is `--skip-gpu`, which takes the declared CPU-torch child for
instrument C and issues NO CUDA call. The booked grid in results/xp_a/ was
produced under `--skip-gpu` (classifier_meta.device == "cpu-fallback") and is
byte-reproducible: a second run reproduces grid.json identically.

Usage: python3 experiments/xp_a_instrument_transfer.py --skip-gpu   # CPU lane
       python3 experiments/xp_a_instrument_transfer.py               # allows GPU guard arm
"""
from __future__ import annotations

import json
import math
import random
import re
import sys
import zlib
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))

from tools.verdict_gate import Gate, StatMeta, finalize  # noqa: E402
from experiments.st1_quilt_cell_v0 import (  # noqa: E402
    SYN_OPS,
    honest_verdict,
    make_example,
    corrupt_example,
    render,
)

MASTER_SEED = 2718
N_CLEAN_EVAL = 200
N_PER_OP_EVAL = 40
N_TRAIN_CLEAN, N_TRAIN_CORRUPT = 3000, 3000   # 500 per known op
N_VAL_CLEAN, N_VAL_CORRUPT = 750, 750         # 125 per known op
FEAT_DIMS = 8192
PY_GPU = "/home/eileen/venvs/elephant-gpu/bin/python"

KNOWN_OPS = list(SYN_OPS)
HELDOUT_OPS = ["nan_injection", "dtype_cast", "split_boundary", "receipt_copy_prior"]

# ---- frozen gates -----------------------------------------------------------
CHANCE = 0.50
BEATS_CHANCE = 0.60
HIGH_KNOWN_POWER = 0.65
FLUNKS_HELD_OUT = 0.50
RHO_MIN = 0.70
TAU_GRID = (0.40, 0.45, 0.50, 0.55, 0.60)
TAU_LO, TAU_HI = 0.40, 0.60

OUT_DIR = LAB / "results" / "xp_a"

# ---------------------------------------------------------------------------
# corpus
# ---------------------------------------------------------------------------

def corrupt_heldout(ex: dict, rng: random.Random, op: str, source_id: str | None):
    """Held-out ops — novel corruption classes, implemented fresh (not in st1)."""
    o = json.loads(json.dumps(ex))
    if op == "nan_injection":
        o[rng.choice(["mean_rel_improvement", "tau"])] = float("nan")
    elif op == "dtype_cast":
        o["wins"] = float(o["wins"])  # silent int->float through a JSON round-trip
    elif op == "split_boundary":
        # base is KEEP-honest; drop wins one below the KEEP threshold, keep verdict
        o["wins"] = max(0, math.ceil(0.8 * o["n_pairs"]) - 1)
        assert o["verdict"] == "KEEP"
    elif op == "receipt_copy_prior":
        assert source_id, "receipt_copy_prior needs a prior receipt id"
        o["receipt"] = source_id
    else:
        raise ValueError(f"unknown held-out op {op}")
    return o


def keep_honest(rng: random.Random) -> dict:
    """Draw until the example is honestly KEEP (needed by split_boundary)."""
    for _ in range(1000):
        ex = make_example(rng)
        if ex["verdict"] == "KEEP":
            return ex
    raise RuntimeError("no KEEP example in 1000 draws")


def build_streams():
    """All randomness flows from one master seed -> documented child seeds."""
    master = random.Random(MASTER_SEED)
    seed_train, seed_val, seed_eval, _seed_reserve = (
        master.getrandbits(32) for _ in range(4))

    def gen(seed, n_clean, corrupt_spec):
        """corrupt_spec: list of (op, count, heldout: bool). Returns list of
        (op_name, text, is_heldout_op)."""
        rng = random.Random(seed)
        out = []
        for _ in range(n_clean):
            out.append(("CLEAN", render(make_example(rng), "template"), False))
        for op, count, held in corrupt_spec:
            for _ in range(count):
                base = keep_honest(rng) if op == "split_boundary" else make_example(rng)
                if op in KNOWN_OPS:
                    o = corrupt_example(base, rng, op)
                else:
                    src = None
                    if op == "receipt_copy_prior":
                        src = out[rng.randrange(len(out))][1]  # any earlier entry's id
                        src = parse_field_id(src)
                    o = corrupt_heldout(base, rng, op, src)
                out.append((op, render(o, "template"), held))
        return out

    train = gen(seed_train, N_TRAIN_CLEAN,
                [(op, N_TRAIN_CORRUPT // len(KNOWN_OPS), False) for op in KNOWN_OPS])
    val = gen(seed_val, N_VAL_CLEAN,
              [(op, N_VAL_CORRUPT // len(KNOWN_OPS), False) for op in KNOWN_OPS])

    # eval grid: clean block first (guarantees copy-prior sources precede copies),
    # then known ops in fixed order, then held-out ops in fixed order.
    spec = ([(op, N_PER_OP_EVAL, False) for op in KNOWN_OPS]
            + [(op, N_PER_OP_EVAL, True) for op in HELDOUT_OPS])
    ev = gen(seed_eval, N_CLEAN_EVAL, spec)

    # identity-collision audit: denom_swap with wins==n_pairs is a byte-level no-op
    identity_cases = []
    for i, (op, text, _) in enumerate(ev):
        if op == "denom_swap":
            m = re.search(r"^wins: (\d+) of (\d+) pairs$", text, re.M)
            if m and m.group(1) == m.group(2):
                identity_cases.append({"index": i, "reason": "wins==n_pairs (denom_swap no-op)"})
    return train, val, ev, identity_cases


# ---------------------------------------------------------------------------
# instruments
# ---------------------------------------------------------------------------

FIELDS = {
    "receipt": re.compile(r"^receipt\s+(\S+)$", re.M),
    "verdict": re.compile(r"^verdict:\s*(\S+)\s*$", re.M),
    "mri": re.compile(r"^mean_rel_improvement:\s*(\S+)\s*$", re.M),
    "wins": re.compile(r"^wins:\s*(\S+)\s+of\s+(\S+)\s+pairs\s*$", re.M),
    "tau": re.compile(r"^tau:\s*(\S+)\s+\(grid", re.M),
    "seeds": re.compile(r"^seeds:[ \t]*(.*?)[ \t]*$", re.M),
    "rule": re.compile(r"^rule:\s*(\S+)\s*$", re.M),
}


def parse_receipt(text: str) -> dict | None:
    f = {}
    for name, rx in FIELDS.items():
        m = rx.search(text)
        if m is None:
            return None
        f[name] = m.group(1)
    if f["wins"] != "":  # wins line carries two groups
        m = FIELDS["wins"].search(text)
        f["n_pairs"] = m.group(2)
    return f


def parse_field_id(text: str) -> str:
    f = parse_receipt(text)
    return f["receipt"] if f else ""


def instrument_a(text: str) -> bool:
    """(a) tools/verdict_gate.py static pins on parsed booking fields.
    Detect = finalize() refuses PASS."""
    f = parse_receipt(text)
    if f is None or f["verdict"] not in {"KEEP", "KILL"}:
        return True  # unparseable / invalid verdict: refuse (fail loud)
    completeness = all(f.get(k) for k in FIELDS)  # seed_drop -> empty seeds -> False
    try:
        wins = float(f["wins"]); n = float(f["n_pairs"])
        tau = float(f["tau"]); mri = float(f["mri"])
        frac = wins / n if n > 0 else float("inf")
        gates = [Gate("wins_frac", frac, maximum=1.0),
                 Gate("tau", tau, minimum=TAU_LO, maximum=TAU_HI)]
        if f["verdict"] == "KEEP":
            gates.append(Gate("mri", mri, minimum=0.0))
        stats = {g.name: StatMeta(std=None, n=max(int(n), 2)) for g in gates}
        v = finalize(gates, stats, completeness=completeness, status_source="own")
        return v.verdict != "PASS"
    except ValueError:
        return True  # unparseable numeric: refuse


# Step-parser invariants, FROZEN (public booking schema; no op knowledge):
#   B1 all 7 required fields present, seeds non-empty
#   B2 receipt id matches the lab's id pattern <4lc>_r[1-9]_s<4d>
#   B3 verdict in the booking lattice
#   B4 mri parses as a FINITE float
#   B5 tau parses as a finite float AND is a member of the declared grid
#   B6 wins/n_pairs parse as strict integers, n_pairs >= 2, 0 <= wins <= n_pairs
#   B7 verdict consistency: claimed verdict == honest_verdict(wins, n, mri)
#   B8 receipt id not seen earlier in the stream (no re-certification)
RECEIPT_ID_RX = re.compile(r"^[a-z]{4}_r[1-9]_s\d{4}$")


class InstrumentB:
    name = "step_parser"

    def __init__(self):
        self.seen_ids: set[str] = set()

    def __call__(self, text: str) -> bool:
        f = parse_receipt(text)
        if f is None or not all(f.get(k) for k in FIELDS):
            return True  # B1
        # B8 FIRST (before format validation): an id is stream state the moment
        # it is parseable — a re-certified id is flagged even if its source
        # entry was itself malformed (smoke-run fix 2026-10-01, pre-recording).
        if f["receipt"] in self.seen_ids:
            return True  # B8
        self.seen_ids.add(f["receipt"])
        if not RECEIPT_ID_RX.match(f["receipt"]):
            return True  # B2
        if f["verdict"] not in {"KEEP", "KILL", "INCONCLUSIVE", "DEGENERATE", "VOID"}:
            return True  # B3
        try:
            mri = float(f["mri"])
            if not math.isfinite(mri):
                return True  # B4
            tau = float(f["tau"])
            if not math.isfinite(tau) or not any(abs(tau - g) < 1e-9 for g in TAU_GRID):
                return True  # B5
            wins = int(f["wins"]); n = int(f["n_pairs"])  # strict: "7.0" raises
            if n < 2 or not (0 <= wins <= n):
                return True  # B6
            if f["verdict"] in {"KEEP", "KILL"} and honest_verdict(wins, n, mri) != f["verdict"]:
                return True  # B7
        except ValueError:
            return True  # strict int/float parse failure (B4/B6)
        return False


def instrument_a_stream(texts):
    return [instrument_a(t) for t in texts]


def instrument_b_stream(texts):
    b = InstrumentB()
    return [b(t) for t in texts]


# ---- instrument C features (shared by main + torch child) -------------------

def featurize(texts: list[str]) -> "object":
    import numpy as np
    X = np.zeros((len(texts), FEAT_DIMS), dtype=np.float32)

    def h(s: str) -> int:
        return zlib.crc32(s.encode("utf-8")) % FEAT_DIMS

    for i, t in enumerate(texts):
        tt = t.lower()
        toks = re.findall(r"[a-z_0-9.+-]+", tt)
        grams = set(toks)
        grams.update("".join(k) for k in zip(tt, tt[1:], tt[2:]))
        for g in grams:
            X[i, h(g)] = 1.0
    return X


CHILD_CODE = r"""
import sys, json, numpy as np, torch
train_npz, val_npz, ev_npz, out_json, probs_npz = sys.argv[1:6]
tr = np.load(train_npz); va = np.load(val_npz); ev = np.load(ev_npz)
Xtr = torch.tensor(tr["X"], dtype=torch.float32)
ytr = torch.tensor(tr["y"], dtype=torch.float32)
dev = "cuda" if torch.cuda.is_available() else "cpu"
Xtr, ytr = Xtr.to(dev), ytr.to(dev)
torch.manual_seed(2718)
w = torch.zeros(Xtr.shape[1], device=dev, requires_grad=True)
b = torch.zeros(1, device=dev, requires_grad=True)
opt = torch.optim.AdamW([w, b], lr=0.05, weight_decay=1e-4)
for step in range(600):
    opt.zero_grad()
    loss = torch.nn.functional.binary_cross_entropy_with_logits(
        Xtr @ w + b, ytr)
    loss.backward(); opt.step()
with torch.no_grad():
    pv = (torch.tensor(va["X"], dtype=torch.float32).to(dev) @ w + b).sigmoid().cpu().numpy()
    pe = (torch.tensor(ev["X"], dtype=torch.float32).to(dev) @ w + b).sigmoid().cpu().numpy()
np.savez(probs_npz, p_val=pv, p_eval=pe)
json.dump({"device": dev, "final_loss": float(loss.item()),
           "train_n": int(Xtr.shape[0])}, open(out_json, "w"))
"""

CPU_CHILD_CODE = r"""
import sys, json, numpy as np, torch
train_npz, val_npz, ev_npz, out_json, probs_npz = sys.argv[1:6]
torch.manual_seed(2718); torch.set_num_threads(4)
tr = np.load(train_npz); va = np.load(val_npz); ev = np.load(ev_npz)
Xtr = torch.tensor(tr["X"], dtype=torch.float32); ytr = torch.tensor(tr["y"], dtype=torch.float32)
w = torch.zeros(Xtr.shape[1], requires_grad=True); b = torch.zeros(1, requires_grad=True)
opt = torch.optim.AdamW([w, b], lr=0.05, weight_decay=1e-4)
for step in range(300):
    opt.zero_grad()
    loss = torch.nn.functional.binary_cross_entropy_with_logits(Xtr @ w + b, ytr)
    loss.backward(); opt.step()
with torch.no_grad():
    pv = (torch.tensor(va["X"], dtype=torch.float32) @ w + b).sigmoid().numpy()
    pe = (torch.tensor(ev["X"], dtype=torch.float32) @ w + b).sigmoid().numpy()
np.savez(probs_npz, p_val=pv, p_eval=pe)
json.dump({"device": "cpu-fallback", "final_loss": float(loss.item()),
           "train_n": int(Xtr.shape[0])}, open(out_json, "w"))
"""


def train_classifier_c(train, val, ev, skip_gpu: bool):
    """Torch logistic under guard.py (GPU) with declared CPU-torch fallback."""
    import numpy as np
    import guard

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tr_npz, va_npz, ev_npz = OUT_DIR / "c_train.npz", OUT_DIR / "c_val.npz", OUT_DIR / "c_eval.npz"
    probs_npz = OUT_DIR / "c_probs.npz"
    Xtr = featurize([t for _, t, _ in train]); ytr = np.array([0 if op == "CLEAN" else 1 for op, _, _ in train])
    Xva = featurize([t for _, t, _ in val]); yva = np.array([0 if op == "CLEAN" else 1 for op, _, _ in val])
    Xev = featurize([t for _, t, _ in ev])
    np.savez(tr_npz, X=Xtr.astype(np.uint8), y=ytr)
    np.savez(va_npz, X=Xva.astype(np.uint8), y=yva)
    np.savez(ev_npz, X=Xev.astype(np.uint8))

    meta, used_fallback = None, False
    if not skip_gpu:
        g = guard.Guard(timeout_s=600.0, task_id="XP-A-instrument-transfer", seed=str(MASTER_SEED))
        if g.preflight():
            rc, out, err = g.run([PY_GPU, "-c", CHILD_CODE,
                                  str(tr_npz), str(va_npz), str(ev_npz),
                                  str(OUT_DIR / "c_meta.json"), str(probs_npz)],
                                 cwd=str(LAB), env={"PATH": "/usr/bin:/bin", "HOME": str(Path.home())})
            if rc == 0:
                meta = json.loads((OUT_DIR / "c_meta.json").read_text())
                path, receipt = g.emit_receipt()
                ok, msg = g.validate_receipt(path)
                meta["g7_receipt"] = {"path": path, "valid": ok, "msg": msg,
                                      "verdict": (receipt or {}).get("verdict")}
            else:
                print(f"[C] GPU child failed rc={rc}: {err[-400:]}", file=sys.stderr)
        else:
            print(f"[C] guard preflight refused: {g.breach}", file=sys.stderr)
    if meta is None:
        used_fallback = True
        print("[C] falling back to CPU torch (declared fallback)", file=sys.stderr)
        # CPU-only fallback: the GPU guard is a GPU watchdog, not needed here.
        import subprocess
        r = subprocess.run(
            [PY_GPU, "-c", CPU_CHILD_CODE, str(tr_npz), str(va_npz), str(ev_npz),
             str(OUT_DIR / "c_meta.json"), str(probs_npz)],
            cwd=str(LAB), capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            raise RuntimeError(f"instrument C failed on both paths: {r.stderr[-400:]}")
        meta = json.loads((OUT_DIR / "c_meta.json").read_text())

    probs = np.load(probs_npz)
    p_val, p_eval = probs["p_val"], probs["p_eval"]
    # frozen threshold: max balanced accuracy on the KNOWN-op validation split
    best_t, best_ba = 0.5, -1.0
    yva = np.array([0 if op == "CLEAN" else 1 for op, _, _ in val])
    for t in [i / 100 for i in range(1, 100)]:
        pred = p_val >= t
        tpr = pred[yva == 1].mean(); tnr = (~pred[yva == 0]).mean()
        ba = 0.5 * (tpr + tnr)
        if ba > best_ba:
            best_t, best_ba = t, ba
    meta.update({"threshold": best_t, "val_balanced_acc": round(best_ba, 4),
                 "fallback": used_fallback})
    detections = (p_eval >= best_t).tolist()
    (OUT_DIR / "c_meta.json").write_text(json.dumps(meta, indent=2))
    return detections, meta


# ---------------------------------------------------------------------------
# grid + gates
# ---------------------------------------------------------------------------

def spearman(x, y):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def main() -> int:
    skip_gpu = "--skip-gpu" in sys.argv
    train, val, ev, identity_cases = build_streams()
    ops = [op for op, _, _ in ev]
    texts = [t for _, t, _ in ev]
    held_flags = [h for _, _, h in ev]
    print(f"corpus: eval={len(ev)} (clean {N_CLEAN_EVAL}, known {6 * N_PER_OP_EVAL}, "
          f"heldout {4 * N_PER_OP_EVAL}), train={len(train)}, val={len(val)}; "
          f"identity_cases={len(identity_cases)}")

    detections = {}
    detections["verdict_gate_pins"] = instrument_a_stream(texts)
    detections["step_parser"] = instrument_b_stream(texts)
    c_meta = None
    try:
        detections["trained_classifier"], c_meta = train_classifier_c(train, val, ev, skip_gpu)
    except Exception as e:  # fail loud but leave the grid interpretable
        print(f"[C] FAILED: {e}", file=sys.stderr)
        c_meta = {"error": str(e)}

    # per-op recall + clean FPR
    grid, per_receipt = {}, []
    clean_idx = [i for i, op in enumerate(ops) if op == "CLEAN"]
    for inst, det in detections.items():
        grid[inst] = {}
        for op in ["CLEAN"] + KNOWN_OPS + HELDOUT_OPS:
            idx = [i for i, o in enumerate(ops) if o == op]
            if not idx:
                continue
            rate = sum(det[i] for i in idx) / len(idx)
            grid[inst][op] = round(rate, 4)
        for i, o in enumerate(ops):
            if o != "CLEAN" and det[i]:
                per_receipt.append({"instrument": inst, "index": i, "op": o,
                                    "heldout": held_flags[i]})

    summary = {}
    for inst in detections:
        kp = sum(grid[inst][op] for op in KNOWN_OPS) / len(KNOWN_OPS)
        up = sum(grid[inst][op] for op in HELDOUT_OPS) / len(HELDOUT_OPS)
        summary[inst] = {"known_power": round(kp, 4), "unknown_power": round(up, 4),
                         "clean_fpr": grid[inst].get("CLEAN")}

    instruments = list(detections)
    rho = None
    verdict = "INCONCLUSIVE"
    reasons = []
    if len(instruments) == 3:
        xs = [summary[i]["known_power"] for i in instruments]
        ys = [summary[i]["unknown_power"] for i in instruments]
        rho = round(spearman(xs, ys), 4)
        all_beat = all(summary[i]["unknown_power"] >= BEATS_CHANCE for i in instruments)
        kill = any(summary[i]["known_power"] >= HIGH_KNOWN_POWER
                   and summary[i]["unknown_power"] <= FLUNKS_HELD_OUT for i in instruments)
        cells = 3 * len(HELDOUT_OPS)
        if cells < 12:
            verdict, reasons = "INCONCLUSIVE", [f"grid {cells} < 3x4 valid cells"]
        elif kill:
            who = [i for i in instruments if summary[i]["known_power"] >= HIGH_KNOWN_POWER
                   and summary[i]["unknown_power"] <= FLUNKS_HELD_OUT]
            verdict = "KILL"
            reasons = [f"high-known-power instrument(s) {who} flunk held-out "
                       f"(<= {FLUNKS_HELD_OUT}): known-power does not predict unknown-power"]
        elif rho >= RHO_MIN and all_beat:
            verdict = "KEEP"
            reasons = [f"rho={rho} >= {RHO_MIN} and all instruments beat chance on held-out"]
        else:
            verdict = "INCONCLUSIVE"
            reasons = [f"rho={rho} vs {RHO_MIN}; all_beat={all_beat} — neither KEEP nor KILL gate fired"]

    out = {
        "experiment": "XP-A-instrument-transfer",
        "pre_reg": "scratch/scout-2026-10-01-pushwave.md §1c; frozen gates in script docstring",
        "master_seed": MASTER_SEED,
        "claim": "known-failure detection power predicts unknown-failure detection power",
        "frozen_gates": {"chance": CHANCE, "beats_chance": BEATS_CHANCE,
                         "high_known_power": HIGH_KNOWN_POWER,
                         "flunks_held_out": FLUNKS_HELD_OUT, "rho_min": RHO_MIN},
        "known_ops": KNOWN_OPS, "heldout_ops": HELDOUT_OPS,
        "grid_recall_per_op": grid,
        "instrument_summary": summary,
        "spearman_known_unknown": rho,
        "verdict": verdict,
        "verdict_reasons": reasons,
        "classifier_meta": c_meta,
        "op_identity_cases": identity_cases,
        "n_eval": len(ev), "n_train": len(train), "n_val": len(val),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "grid.json").write_text(json.dumps(out, indent=2))
    (OUT_DIR / "per_receipt_detections.json").write_text(json.dumps(per_receipt, indent=2))
    (OUT_DIR / "eval_stream.txt").write_text(
        "".join(f"### entry {i} op={o} heldout={h}\n{t}\n" for i, (o, t, h) in enumerate(ev)))

    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
