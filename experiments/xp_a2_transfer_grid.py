#!/usr/bin/env python3
"""XP-A2 "instrument-transfer grid" — pre-registered 2026-10-01, lane XP-A2.

Follow-up to XP-A (experiments/xp_a_instrument_transfer.py, results/xp_a/),
which came back INCONCLUSIVE because the Spearman known/unknown gate is nearly
binary at n=3 instruments (4-value support; rho>=0.70 satisfiable only at
perfect rank agreement). XP-A2 extends the SAME corpus and harness to >=6
instruments so the rank correlation is meaningful, and adds a substantive
design-FAMILY comparison.

CLAIM UNDER TEST (unchanged, verbatim): "an instrument reports success unless it
has been given a way to fail." Operationised: an instrument's detection power
against KNOWN failure classes predicts its power against UNKNOWN (held-out)
classes.

CORPUS (reused byte-for-byte from XP-A)
  Master seed 2718 -> documented child seeds (seed_train/val/eval from the same
  master draw). 600 eval receipts = 200 clean / 240 known (6 ops x 40) /
  160 held-out (4 ops x 40). KNOWN ops = st1 SYN_OPS; HELD-OUT ops = XP-A's
  four novel classes. This script ADDS one field to the render: a sealed
  manifest `digest:` line = sha256 over the receipt's judgment core, computed on
  the HONEST state and carried (stale) through every corruption. Clean receipts
  therefore always carry a correct digest.

INSTRUMENTS (7; >=6 full-corpus for the frozen gates)
  family invariant  A "verdict_gate_pins"  — tools/verdict_gate.py pins on parsed
                       booking fields (XP-A instrument A, unchanged semantics).
  family invariant  B "step_parser"        — canfail-style frozen checks B1-B8
                       (XP-A instrument B, unchanged semantics).
  family digest     D "digest_manifest"    — NEW. Recompute the manifest digest
                       from the receipt's declared judgment core and compare to
                       the sealed `digest:` line. Detects tamper-without-re-seal
                       over DIGEST_BOUND fields; silent on unbind fields.
  family schema     E "g7_field_validator"— NEW. Faithful port of the check
                       battery in ../fleet-seeds/scripts/g7_validate.mjs
                       (required fields, types, ranges, enums, digest FORMAT)
                       applied to the parsed receipt. No semantics, no digest
                       recomputation (g7 validates state_digest format only).
  family schema     F "schema_lint"        — NEW. Strict TEXT shape + enum-ish
                       lint, no numerics, no cross-field, no stream state.
  family trained    C "trained_classifier" — logistic on hashed char-3gram+token
                       features (XP-A instrument C), retrained on the XP-A2
                       corpus. CPU-torch child (house law: this is a CPU lane).
  family judgment   G "typesafe_jev"       — OPTIONAL. api.typesafe.ai
                       systemone "jev-preview" noul gate on a <=24-receipt
                       stratified sample. Reported SUPPLEMENTARY (tiny n); it is
                       NOT folded into the frozen n>=6 rank correlation.

FROZEN GATES (identical to XP-A; set before the run, no post-hoc tuning):
    chance = 0.50; BEATS_CHANCE (held-out) >= 0.60; HIGH_KNOWN_POWER >= 0.65;
    FLUNKS_HELD_OUT <= 0.50; RHO_MIN = 0.70.
    KEEP iff Spearman(known, unknown) over the 6 full-corpus instruments
             >= 0.70 AND every instrument beats chance on held-out.
    KILL iff any instrument has known >= 0.65 AND held-out <= 0.50.
    (Precedence KILL > KEEP: KILL is an existence condition.)
    INCONCLUSIVE iff valid grid < 6 instruments x 4 held-out ops, or the
             classifier cannot be produced at all.
  Reported beside the gates: exact permutation p for rho at n=6 (6!=720), and
  Wilson 95% CIs + exact binomial p for each instrument's held-out recall.

HOUSE LAWS: seed 2718; fail loud; CPU only (no CUDA call in this lane);
artifacts only under results/xp_a2/; no RESULTS.md append; no commit.

Usage: python3 experiments/xp_a2_transfer_grid.py            # CPU lane (default)
       python3 experiments/xp_a2_transfer_grid.py --no-jev   # skip judgment API
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import re
import subprocess
import sys
import time
import zlib
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))

from tools.verdict_gate import Gate, StatMeta, finalize  # noqa: E402
from experiments.st1_quilt_cell_v0 import (  # noqa: E402
    RULES,
    SYN_OPS,
    TAU_GRID,
    corrupt_example,
    honest_verdict,
    make_example,
    render,
)

MASTER_SEED = 2718
N_CLEAN_EVAL = 200
N_PER_OP_EVAL = 40
N_TRAIN_CLEAN, N_TRAIN_CORRUPT = 3000, 3000
N_VAL_CLEAN, N_VAL_CORRUPT = 750, 750
FEAT_DIMS = 8192
PY_TORCH = "/home/eileen/venvs/elephant-gpu/bin/python"

KNOWN_OPS = list(SYN_OPS)
HELDOUT_OPS = ["nan_injection", "dtype_cast", "split_boundary", "receipt_copy_prior"]

# ---- frozen gates (verbatim from XP-A) --------------------------------------
CHANCE = 0.50
BEATS_CHANCE = 0.60
HIGH_KNOWN_POWER = 0.65
FLUNKS_HELD_OUT = 0.50
RHO_MIN = 0.70
TAU_LO, TAU_HI = 0.40, 0.60
VERDICT_LATTICE = {"KEEP", "KILL", "INCONCLUSIVE", "DEGENERATE", "VOID"}
MIN_FULL_INSTRUMENTS = 6

OUT_DIR = LAB / "results" / "xp_a2"

# digest binds the JUDGMENT CORE only: the numeric/seed state that determines
# the verdict. `receipt` id and `verdict` label are deliberately UNBOUND (so a
# re-labelled or re-identified receipt with an intact core is silent to D).
DIGEST_BOUND = ("wins", "n_pairs", "mean_rel_improvement", "tau", "seeds", "rule")


# ---------------------------------------------------------------------------
# corpus (reused; one sealed field added)
# ---------------------------------------------------------------------------

def canon_core(core: dict) -> str:
    return json.dumps({k: core.get(k) for k in DIGEST_BOUND}, sort_keys=True,
                      default=str)


def core_digest(ex: dict) -> str:
    return hashlib.sha256(canon_core(ex).encode("utf-8")).hexdigest()


def make_example_sealed(rng: random.Random) -> dict:
    """XP-A make_example + a sealed manifest digest of the honest core."""
    ex = make_example(rng)
    ex["digest"] = core_digest(ex)
    return ex


def render2(ex: dict) -> str:
    """XP-A template render + the sealed digest line."""
    return render(ex, "template") + f"\ndigest: {ex['digest']}"


def corrupt_heldout(ex: dict, rng: random.Random, op: str, source_id: str | None):
    """Held-out ops — novel corruption classes, implemented fresh (not in st1)."""
    o = json.loads(json.dumps(ex))
    if op == "nan_injection":
        o[rng.choice(["mean_rel_improvement", "tau"])] = float("nan")
    elif op == "dtype_cast":
        o["wins"] = float(o["wins"])
    elif op == "split_boundary":
        o["wins"] = max(0, math.ceil(0.8 * o["n_pairs"]) - 1)
        assert o["verdict"] == "KEEP"
    elif op == "receipt_copy_prior":
        assert source_id, "receipt_copy_prior needs a prior receipt id"
        o["receipt"] = source_id
    else:
        raise ValueError(f"unknown held-out op {op}")
    return o


def keep_honest(rng: random.Random) -> dict:
    for _ in range(1000):
        ex = make_example_sealed(rng)
        if ex["verdict"] == "KEEP":
            return ex
    raise RuntimeError("no KEEP example in 1000 draws")


def parse_field_id(text: str) -> str:
    f = parse_full(text)
    return f["receipt"] if f else ""


def build_streams():
    master = random.Random(MASTER_SEED)
    seed_train, seed_val, seed_eval, _reserve = (
        master.getrandbits(32) for _ in range(4))

    def gen(seed, n_clean, corrupt_spec):
        rng = random.Random(seed)
        out = []
        for _ in range(n_clean):
            out.append(("CLEAN", render2(make_example_sealed(rng)), False))
        for op, count, held in corrupt_spec:
            for _ in range(count):
                base = keep_honest(rng) if op == "split_boundary" else make_example_sealed(rng)
                if op in KNOWN_OPS:
                    o = corrupt_example(base, rng, op)
                else:
                    src = None
                    if op == "receipt_copy_prior":
                        src = out[rng.randrange(len(out))][1]
                        src = parse_field_id(src)
                    o = corrupt_heldout(base, rng, op, src)
                out.append((op, render2(o), held))
        return out

    train = gen(seed_train, N_TRAIN_CLEAN,
                [(op, N_TRAIN_CORRUPT // len(KNOWN_OPS), False) for op in KNOWN_OPS])
    val = gen(seed_val, N_VAL_CLEAN,
              [(op, N_VAL_CORRUPT // len(KNOWN_OPS), False) for op in KNOWN_OPS])
    spec = ([(op, N_PER_OP_EVAL, False) for op in KNOWN_OPS]
            + [(op, N_PER_OP_EVAL, True) for op in HELDOUT_OPS])
    ev = gen(seed_eval, N_CLEAN_EVAL, spec)

    identity_cases = []
    for i, (op, text, _) in enumerate(ev):
        if op == "denom_swap":
            m = re.search(r"^wins: (\d+) of (\d+) pairs$", text, re.M)
            if m and m.group(1) == m.group(2):
                identity_cases.append({"index": i, "reason": "wins==n_pairs (denom_swap no-op)"})
    return train, val, ev, identity_cases


# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------

FIELDS = {
    "receipt": re.compile(r"^receipt\s+(\S+)$", re.M),
    "verdict": re.compile(r"^verdict:\s*(\S+)\s*$", re.M),
    "mri": re.compile(r"^mean_rel_improvement:\s*(\S+)\s*$", re.M),
    "wins": re.compile(r"^wins:\s*(\S+)\s+of\s+(\S+)\s+pairs\s*$", re.M),
    "tau": re.compile(r"^tau:\s*(\S+)\s+\(grid", re.M),
    "seeds": re.compile(r"^seeds:[ \t]*(.*?)[ \t]*$", re.M),
    "rule": re.compile(r"^rule:\s*(\S+)\s*$", re.M),
    "digest": re.compile(r"^digest:\s*(\S+)\s*$", re.M),
}
RECEIPT_ID_RX = re.compile(r"^[a-z]{4}_r[1-9]_s\d{4}$")
HEX64_RX = re.compile(r"^[0-9a-f]{64}$")


def parse_full(text: str) -> dict | None:
    f = {}
    for name, rx in FIELDS.items():
        m = rx.search(text)
        if m is None:
            return None
        f[name] = m.group(1)
    m = FIELDS["wins"].search(text)
    f["n_pairs"] = m.group(2)
    return f


def _finite_number(s: str):
    v = float(s)
    return v if math.isfinite(v) else None


# ---------------------------------------------------------------------------
# instruments
# ---------------------------------------------------------------------------

def instrument_a(text: str) -> bool:
    """A — tools/verdict_gate.py pins (invariant-pin family)."""
    f = parse_full(text)
    if f is None or f["verdict"] not in {"KEEP", "KILL"}:
        return True
    completeness = all(f.get(k) for k in FIELDS)
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
        return True


class InstrumentB:
    """B — canfail-style frozen parser checks B1-B8 (invariant-parser family)."""
    name = "step_parser"

    def __init__(self):
        self.seen_ids: set[str] = set()

    def __call__(self, text: str) -> bool:
        f = parse_full(text)
        if f is None or not all(f.get(k) for k in FIELDS):
            return True  # B1
        if f["receipt"] in self.seen_ids:
            return True  # B8
        self.seen_ids.add(f["receipt"])
        if not RECEIPT_ID_RX.match(f["receipt"]):
            return True  # B2
        if f["verdict"] not in VERDICT_LATTICE:
            return True  # B3
        try:
            mri = float(f["mri"])
            if not math.isfinite(mri):
                return True  # B4
            tau = float(f["tau"])
            if not math.isfinite(tau) or not any(abs(tau - g) < 1e-9 for g in TAU_GRID):
                return True  # B5
            wins = int(f["wins"]); n = int(f["n_pairs"])
            if n < 2 or not (0 <= wins <= n):
                return True  # B6
            if f["verdict"] in {"KEEP", "KILL"} and honest_verdict(wins, n, mri) != f["verdict"]:
                return True  # B7
        except ValueError:
            return True
        return False


def instrument_d(text: str) -> bool:
    """D — digest-manifest checker (digest-checker family).

    Recompute the manifest digest from the receipt's OWN declared judgment core
    and compare to the sealed `digest:` line. silent on unbound fields.
    """
    f = parse_full(text)
    if f is None or not f.get("digest"):
        return True
    try:
        core = {
            "wins": int(f["wins"]),
            "n_pairs": int(f["n_pairs"]),
            "mean_rel_improvement": float(f["mri"]),
            "tau": float(f["tau"]),
            "seeds": f["seeds"],
            "rule": f["rule"],
        }
    except ValueError:
        return True  # an unparseable bound field cannot match the seal
    return core_digest(core) != f["digest"]


def instrument_e(text: str) -> bool:
    """E — g7 receipt-field validator (schema-lint family, typed port).

    Ports the check battery of ../fleet-seeds/scripts/g7_validate.mjs:
    required non-empty fields; typed numeric fields; integer fields; ranged
    fields; enum membership; a 64-hex digest FORMAT check. No semantics; the
    digest is format-checked (g7 validates state_digest format only) and is NOT
    recomputed.
    """
    f = parse_full(text)
    if f is None:
        return True
    # required non-empty fields
    for k in FIELDS:
        if not f.get(k):
            return True
    # receipt id shape (g7 bounds receipt_id to a non-empty string; the lab's
    # id pattern is a stricter, still non-semantic, shape check)
    if not RECEIPT_ID_RX.match(f["receipt"]):
        return True
    # enum membership
    if f["verdict"] not in VERDICT_LATTICE:
        return True
    if f["rule"] not in RULES:
        return True
    # typed + ranged numerics
    try:
        wins = int(f["wins"]); n = int(f["n_pairs"])
        mri = _finite_number(f["mri"]); tau = _finite_number(f["tau"])
    except ValueError:
        return True
    if mri is None or tau is None:
        return True
    if n < 2 or not (0 <= wins <= n):
        return True
    if not any(abs(tau - g) < 1e-9 for g in TAU_GRID):
        return True
    # digest binding, FORMAT only (port of determinism.state_digest 64-hex check)
    if not HEX64_RX.match(f["digest"]):
        return True
    return False


LINT_LINE_RX = {
    "receipt": re.compile(r"^receipt\s+\S+$", re.M),
    "verdict": re.compile(r"^verdict:\s*[A-Z]+$", re.M),
    "mri": re.compile(r"^mean_rel_improvement:\s*[+-]\d+\.\d{4}$", re.M),
    "wins": re.compile(r"^wins:\s*\d+\s+of\s+\d+\s+pairs$", re.M),
    "tau": re.compile(r"^tau:\s*\d\.\d{2}\s+\(grid\s+0\.40-0\.60\)$", re.M),
    "seeds": re.compile(r"^seeds:\s*\d{4}-\d{4}$", re.M),
    "rule": re.compile(r"^rule:\s*[a-z-]+$", re.M),
    "digest": re.compile(r"^digest:\s*[0-9a-f]{64}$", re.M),
}


def instrument_f(text: str) -> bool:
    """F — schema_lint (schema-lint family, pure TEXT shape).

    Strict line-shape lint only: every required line present and matching a
    syntactic shape regex. No numeric ranges, no enum semantics, no cross-field
    consistency, no stream state.
    """
    for name, rx in LINT_LINE_RX.items():
        if not rx.search(text):
            return True
    return False


# ---- instrument C features (hashed char-3gram + token) ----------------------

def featurize(texts: list[str]):
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


def train_classifier_c(train, val, ev):
    """C — logistic classifier on hashed n-gram features, CPU torch child."""
    import numpy as np
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tr_npz, va_npz, ev_npz = OUT_DIR / "c_train.npz", OUT_DIR / "c_val.npz", OUT_DIR / "c_eval.npz"
    probs_npz = OUT_DIR / "c_probs.npz"
    Xtr = featurize([t for _, t, _ in train])
    ytr = np.array([0 if op == "CLEAN" else 1 for op, _, _ in train])
    Xva = featurize([t for _, t, _ in val])
    yva = np.array([0 if op == "CLEAN" else 1 for op, _, _ in val])
    Xev = featurize([t for _, t, _ in ev])
    np.savez(tr_npz, X=Xtr.astype(np.uint8), y=ytr)
    np.savez(va_npz, X=Xva.astype(np.uint8), y=yva)
    np.savez(ev_npz, X=Xev.astype(np.uint8))
    r = subprocess.run(
        [PY_TORCH, "-c", CPU_CHILD_CODE, str(tr_npz), str(va_npz), str(ev_npz),
         str(OUT_DIR / "c_meta.json"), str(probs_npz)],
        cwd=str(LAB), capture_output=True, text=True, timeout=1200)
    if r.returncode != 0:
        raise RuntimeError(f"instrument C failed (CPU torch): {r.stderr[-400:]}")
    meta = json.loads((OUT_DIR / "c_meta.json").read_text())
    probs = np.load(probs_npz)
    p_val, p_eval = probs["p_val"], probs["p_eval"]
    y_va = np.array([0 if op == "CLEAN" else 1 for op, _, _ in val])
    best_t, best_ba = 0.5, -1.0
    for t in [i / 100 for i in range(1, 100)]:
        pred = p_val >= t
        ba = 0.5 * (pred[y_va == 1].mean() + (~pred[y_va == 0]).mean())
        if ba > best_ba:
            best_t, best_ba = t, ba
    meta.update({"threshold": best_t, "val_balanced_acc": round(best_ba, 4)})
    (OUT_DIR / "c_meta.json").write_text(json.dumps(meta, indent=2))
    return (p_eval >= best_t).tolist(), meta


# ---- instrument G (judgment API, optional / supplementary) ------------------

TYPESAFE_KEY = Path("/mnt/c/Users/casey/key.txt")
TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"
JEV_N_CLEAN, JEV_N_HELD, JEV_N_KNOWN = 6, 3, 1   # 6 + 6 + 12 = 24 receipts
JEV_MIN_NOUL = 0.50


def _load_typesafe_key() -> str | None:
    try:
        for line in TYPESAFE_KEY.read_text().splitlines():
            if line.startswith("TYPESAFE_AI_KEY="):
                return line.split("=", 1)[1].strip()
    except OSError:
        return None
    return None


def instrument_g(ev, deadline_s: float = 480.0):
    """G — typesafe JEV noul gate on a small stratified sample (supplementary)."""
    import urllib.request

    key = _load_typesafe_key()
    if not key:
        return None, {"status": "skipped", "reason": "no TYPESAFE_AI_KEY"}

    by_op: dict[str, list[int]] = {}
    for i, (op, _, _) in enumerate(ev):
        by_op.setdefault(op, []).append(i)
    sample: list[tuple[str, int, bool]] = []
    for i in by_op.get("CLEAN", [])[:JEV_N_CLEAN]:
        sample.append(("CLEAN", i, False))
    for op in KNOWN_OPS:
        for i in by_op.get(op, [])[:JEV_N_KNOWN]:
            sample.append((op, i, False))
    for op in HELDOUT_OPS:
        for i in by_op.get(op, [])[:JEV_N_HELD]:
            sample.append((op, i, True))

    t0 = time.time()
    rows, errors = [], 0
    for op, idx, held in sample:
        if time.time() - t0 > deadline_s:
            return None, {"status": "aborted_timeout", "n_done": len(rows),
                          "reason": f">{deadline_s:.0f}s budget"}
        body = json.dumps({
            "model": "jev-preview",
            "state": ev[idx][1],
            "questions": {"gate": {
                "type": "noul",
                "question": "Is this receipt internally consistent and free of data-integrity errors?",
                "instructions": ("Answer true (high noul) only if every field is internally "
                                 "consistent and the receipt contains no corrupted, tampered, "
                                 "out-of-range, malformed, or contradictory data. Answer false "
                                 "(low noul) if any field is missing, of the wrong type, out of "
                                 "its declared range, or inconsistent with the others."),
            }},
        }).encode("utf-8")
        req = urllib.request.Request(TYPESAFE_URL, data=body, method="POST", headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                obj = json.loads(resp.read().decode("utf-8"))
            noul = float(obj["answers"]["gate"]["noul"])
        except Exception as e:  # noqa: BLE001 - network/API: count and continue
            errors += 1
            rows.append({"op": op, "index": idx, "heldout": held, "error": type(e).__name__})
            continue
        rows.append({"op": op, "index": idx, "heldout": held, "noul": round(noul, 4),
                     "detect": noul < JEV_MIN_NOUL})
    good = [r for r in rows if "detect" in r]
    if not good:
        return None, {"status": "failed_no_answers", "errors": errors}
    detections = {r["index"]: bool(r["detect"]) for r in good}
    kk = [r for r in good if not r["heldout"] and r["op"] != "CLEAN"]
    hh = [r for r in good if r["heldout"]]
    meta = {
        "status": "ok", "model": "jev-preview", "n_sample": len(sample),
        "n_answered": len(good), "errors": errors, "min_noul": JEV_MIN_NOUL,
        "known_power": round(sum(r["detect"] for r in kk) / len(kk), 4) if kk else None,
        "unknown_power": round(sum(r["detect"] for r in hh) / len(hh), 4) if hh else None,
        "per_receipt": rows,
        "note": "supplementary only; small stratified sample, NOT in the frozen rho",
    }
    return detections, meta


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------

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


def spearman(x, y):
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return (max(0.0, c - h), min(1.0, c + h))


def binom_tail_ge(k, n, p):
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    run_jev = "--no-jev" not in sys.argv
    train, val, ev, identity_cases = build_streams()
    ops = [op for op, _, _ in ev]
    texts = [t for _, t, _ in ev]
    held_flags = [h for _, _, h in ev]
    print(f"corpus: eval={len(ev)} (clean {N_CLEAN_EVAL}, known {6 * N_PER_OP_EVAL}, "
          f"heldout {4 * N_PER_OP_EVAL}), train={len(train)}, val={len(val)}; "
          f"identity_cases={len(identity_cases)}")

    FAMILY = {
        "verdict_gate_pins": "invariant-pin",
        "step_parser": "invariant-parser",
        "digest_manifest": "digest-checker",
        "g7_field_validator": "schema-lint",
        "schema_lint": "schema-lint",
        "trained_classifier": "trained-classifier",
    }

    detections = {}
    detections["verdict_gate_pins"] = [instrument_a(t) for t in texts]
    b = InstrumentB()
    detections["step_parser"] = [b(t) for t in texts]
    detections["digest_manifest"] = [instrument_d(t) for t in texts]
    detections["g7_field_validator"] = [instrument_e(t) for t in texts]
    detections["schema_lint"] = [instrument_f(t) for t in texts]
    c_meta = None
    try:
        detections["trained_classifier"], c_meta = train_classifier_c(train, val, ev)
    except Exception as e:  # noqa: BLE001
        print(f"[C] FAILED: {e}", file=sys.stderr)
        c_meta = {"error": str(e)}

    # per-op recall + clean FPR
    grid, per_receipt = {}, []
    for inst, det in detections.items():
        grid[inst] = {}
        for op in ["CLEAN"] + KNOWN_OPS + HELDOUT_OPS:
            idx = [i for i, o in enumerate(ops) if o == op]
            if not idx:
                continue
            grid[inst][op] = round(sum(det[i] for i in idx) / len(idx), 4)
        for i, o in enumerate(ops):
            if o != "CLEAN" and det[i]:
                per_receipt.append({"instrument": inst, "index": i, "op": o,
                                    "heldout": held_flags[i]})

    summary = {}
    for inst in detections:
        kp = sum(grid[inst][op] for op in KNOWN_OPS) / len(KNOWN_OPS)
        up = sum(grid[inst][op] for op in HELDOUT_OPS) / len(HELDOUT_OPS)
        summary[inst] = {"family": FAMILY[inst],
                         "known_power": round(kp, 4),
                         "unknown_power": round(up, 4),
                         "clean_fpr": grid[inst].get("CLEAN")}

    # exact stats on the FULL-corpus instruments
    n_held = 4 * N_PER_OP_EVAL
    n_known = 6 * N_PER_OP_EVAL
    n_clean = N_CLEAN_EVAL
    stats = {}
    for inst in detections:
        kk = sum(r["op"] in KNOWN_OPS for r in per_receipt if r["instrument"] == inst)
        kh = sum(r["heldout"] for r in per_receipt if r["instrument"] == inst)
        fpr = grid[inst].get("CLEAN", 0.0)
        kc = round(fpr * n_clean)
        rec_h = kh / n_held
        bal = 0.5 * (rec_h + (1.0 - kc / n_clean))
        stats[inst] = {
            "heldout_recall": round(rec_h, 4),
            "heldout_recall_wilson95": [round(v, 4) for v in wilson(kh, n_held)],
            "p_ge_vs_chance_0.50": round(binom_tail_ge(kh, n_held, CHANCE), 8),
            "p_ge_vs_gate_0.60": round(binom_tail_ge(kh, n_held, BEATS_CHANCE), 8),
            "clean_fpr": fpr,
            "balanced_accuracy_heldout": round(bal, 4),
            "beats_chance": rec_h > CHANCE,
            "beats_chance_gate": rec_h >= BEATS_CHANCE,
            "high_known_power": summary[inst]["known_power"] >= HIGH_KNOWN_POWER,
            "flunks_held_out": rec_h <= FLUNKS_HELD_OUT,
        }

    instruments = list(detections)  # 6 full-corpus
    rho = None
    perm_p = None
    verdict, reasons = "INCONCLUSIVE", []
    n_cells = len(instruments) * len(HELDOUT_OPS)
    if len(instruments) < MIN_FULL_INSTRUMENTS or n_cells < MIN_FULL_INSTRUMENTS * len(HELDOUT_OPS):
        verdict = "INCONCLUSIVE"
        reasons = [f"grid {len(instruments)}x{len(HELDOUT_OPS)} < {MIN_FULL_INSTRUMENTS}x4"]
    else:
        xs = [summary[i]["known_power"] for i in instruments]
        ys = [summary[i]["unknown_power"] for i in instruments]
        rho = round(spearman(xs, ys), 4)
        perms = list(itertools.permutations(range(len(instruments))))
        rho_dist = [spearman(list(p), ys) for p in perms]
        perm_p = round(sum(1 for r in rho_dist if r >= rho - 1e-12) / len(perms), 6)
        all_beat = all(stats[i]["beats_chance_gate"] for i in instruments)
        killers = [i for i in instruments
                   if stats[i]["high_known_power"] and stats[i]["flunks_held_out"]]
        if killers:
            verdict = "KILL"
            reasons = [f"high-known-power instrument(s) {killers} flunk held-out "
                       f"(<= {FLUNKS_HELD_OUT}): known-power does not predict unknown-power"]
        elif rho >= RHO_MIN and all_beat:
            verdict = "KEEP"
            reasons = [f"rho={rho} >= {RHO_MIN} and all instruments beat chance on held-out"]
        else:
            verdict = "INCONCLUSIVE"
            reasons = [f"rho={rho} vs {RHO_MIN}; all_beat={all_beat} — neither KEEP nor KILL fired"]

    # supplementary judgment-API instrument
    jev_meta = {"status": "disabled"}
    if run_jev:
        try:
            _, jev_meta = instrument_g(ev)
        except Exception as e:  # noqa: BLE001 - supplementary: never kill the grid
            jev_meta = {"status": "error", "reason": f"{type(e).__name__}: {e}"}
        print(f"[G] typesafe JEV: {json.dumps({k: v for k, v in jev_meta.items() if k != 'per_receipt'})}",
              file=sys.stderr)

    # design-family roll-up (mean held-out over family members)
    fam = {}
    for inst, s in summary.items():
        fam.setdefault(s["family"], []).append(s["unknown_power"])
    family_rollup = {f: {"n_instruments": len(v),
                         "mean_unknown_power": round(sum(v) / len(v), 4),
                         "mean_known_power": round(
                             sum(summary[i]["known_power"] for i in summary
                                 if summary[i]["family"] == f) / len(v), 4),
                         "members": [i for i in summary if summary[i]["family"] == f]}
                     for f, v in fam.items()}

    out = {
        "experiment": "XP-A2-instrument-transfer-grid",
        "pre_reg": "lanes XP-A2 (extend XP-A to >=6 instruments); gates verbatim from experiments/xp_a_instrument_transfer.py",
        "master_seed": MASTER_SEED,
        "claim": "known-failure detection power predicts unknown-failure detection power",
        "frozen_gates": {"chance": CHANCE, "beats_chance": BEATS_CHANCE,
                         "high_known_power": HIGH_KNOWN_POWER,
                         "flunks_held_out": FLUNKS_HELD_OUT, "rho_min": RHO_MIN,
                         "min_full_instruments": MIN_FULL_INSTRUMENTS},
        "known_ops": KNOWN_OPS, "heldout_ops": HELDOUT_OPS,
        "digest_bound_fields": list(DIGEST_BOUND),
        "grid_recall_per_op": grid,
        "instrument_summary": summary,
        "instrument_stats": stats,
        "design_family_rollup": family_rollup,
        "spearman_known_unknown": rho,
        "spearman_n": len(instruments),
        "spearman_exact_permutation_p_ge": perm_p,
        "spearman_permutation_space": math.factorial(len(instruments)),
        "verdict": verdict,
        "verdict_reasons": reasons,
        "classifier_meta": c_meta,
        "judgment_api_supplementary": {k: v for k, v in jev_meta.items() if k != "per_receipt"},
        "op_identity_cases": identity_cases,
        "n_eval": len(ev), "n_train": len(train), "n_val": len(val),
        "design_family_question": (
            "Which instrument DESIGN FAMILY (invariant-parser, digest-checker, "
            "schema-lint, trained-classifier, judgment-API) transfers to unknown "
            "failure classes?"),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "grid.json").write_text(json.dumps(out, indent=2) + "\n")
    (OUT_DIR / "per_receipt_detections.json").write_text(json.dumps(per_receipt, indent=2) + "\n")
    (OUT_DIR / "judgment_api_receipts.json").write_text(
        json.dumps(jev_meta.get("per_receipt", []), indent=2) + "\n")
    (OUT_DIR / "eval_stream.txt").write_text(
        "".join(f"### entry {i} op={o} heldout={h}\n{t}\n" for i, (o, t, h) in enumerate(ev)))

    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
