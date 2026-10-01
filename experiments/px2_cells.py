"""PX2 cell registry — patchwork-3x3 harness skeleton.

Pre-reg (FROZEN 2026-09-30, before any build): proposals/runs/PX2-patchwork-3x3.md
Rules honored in this module:
- Tree cells train on the PX1 seed-0 80% TRAIN split ONLY. No test state is ever
  touched by training. The 200-state quick-eval is drawn frozen (seed 0) from the
  36,073-state test split and is never trained on.
- The state-split and evaluate() logic are reused EXACTLY from px1_tree_ceiling.py
  (imported, not re-implemented).
- Ollama cells (tev1:0.8b, qwen3.5:0.8b, qwen2.5:0.5b) are wired but OFF by default
  (env flag PX2_ENABLE_OLLAMA=1 arms them) so smoke runs stay CPU-only.
- Cell contract: score_batch(B) -> list[np.ndarray(9) | None]; None = reject/abstain.
- No shell=True anywhere; subprocesses are not used at all in this skeleton.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

import numpy as np
from sklearn.tree import DecisionTreeRegressor

REPO = os.path.expanduser("~/projects/quilt-gpu-lab")
SOLVER_PATH = os.path.expanduser("~/projects/pie-minimax-readonly")
sys.path.insert(0, SOLVER_PATH)
sys.path.insert(0, os.path.join(REPO, "experiments"))

from minmax import enumerate_reachable, winner  # exact solver: ground truth computed, not asserted
from px1_tree_ceiling import evaluate, matrices, fnv1a64  # noqa: F401  (reused EXACTLY, re-exported)

EXPECTED_TERRAIN_DIGEST = "0x75f652bc1d8464b8"  # FNV-1a-64 from PX1 / pre-reg
OLLAMA_HOST = os.environ.get("PX2_OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODELS = ["tev1:0.8b", "qwen3.5:0.8b", "qwen2.5:0.5b"]
QUICK_EVAL_N = 200
QUICK_EVAL_SEED = 0


def device_string(enable_ollama: bool) -> str:
    import sklearn
    s = (f"cpu (numpy {np.__version__}, sklearn {sklearn.__version__}; "
         "decision trees, no CUDA involved")
    s += f"; ollama cells ARMED at {OLLAMA_HOST}" if enable_ollama \
        else "; ollama cells OFF (flag-gated, PX2_ENABLE_OLLAMA)"
    return s + ")"


def ollama_enabled() -> bool:
    return os.environ.get("PX2_ENABLE_OLLAMA", "0") == "1"


def px1_seed0_split(n_states: int, seed: int = 0):
    """EXACT mirror of px1_tree_ceiling.main() split (same rng, same call order):
    rng = default_rng(seed); idx = permutation(n); n_tr = int(0.8*len); tr, te = idx[:n_tr], idx[n_tr:]."""
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n_states)
    n_tr = int(0.8 * len(idx))
    return idx[:n_tr], idx[n_tr:]


def quick_eval_indices(test_idx: np.ndarray, n: int = QUICK_EVAL_N, seed: int = QUICK_EVAL_SEED):
    """Frozen quick-eval draw from the test split (pre-reg: seed 0, never trained on)."""
    qrng = np.random.default_rng(seed)
    perm = qrng.permutation(len(test_idx))
    return test_idx[perm[:n]]


# --------------------------------------------------------------------------
# (b) format gate — structural
# --------------------------------------------------------------------------
def row_ok(row) -> bool:
    """Format gate predicate: exactly 9 finite floats, or reject."""
    try:
        r = np.asarray(row, dtype=np.float64)
    except (TypeError, ValueError):
        return False
    return r.shape == (9,) and bool(np.all(np.isfinite(r)))


class FormatGate:
    """Structural gate wrapping any cell: passes 9-finite-float rows, rejects rest."""

    def __init__(self, inner):
        self.inner = inner
        self.name = f"format_gate({inner.name})"

    def score_batch(self, B):
        return [r if (r is not None and row_ok(r)) else None
                for r in self.inner.score_batch(B)]

    def meta(self):
        return {"kind": "format_gate", "wraps": self.inner.meta()}


# --------------------------------------------------------------------------
# (a) depth-k tree cells — trained on PX1 seed-0 train split ONLY
# --------------------------------------------------------------------------
class TreeCell:
    def __init__(self, name: str, depth: int, tree: DecisionTreeRegressor):
        self.name, self.depth, self.tree = name, depth, tree

    def score_batch(self, B):
        rows = self.tree.predict(np.asarray(B, dtype=np.float64))
        return [np.asarray(r, dtype=np.float64) for r in rows]

    def meta(self):
        return {"kind": "tree", "name": self.name, "max_depth": self.depth,
                "n_leaves": int(self.tree.get_n_leaves())}


def train_tree_cell(depth: int, Btr, Mtr, seed: int = 0) -> TreeCell:
    """Same constructor + fit as px1: max_depth=depth, min_samples_leaf=5, random_state=seed."""
    tree = DecisionTreeRegressor(max_depth=depth, min_samples_leaf=5, random_state=seed)
    tree.fit(Btr, Mtr)
    return TreeCell(f"tree_d{depth}", depth, tree)


# --------------------------------------------------------------------------
# (c) majority-vote combiner over any cell list
# --------------------------------------------------------------------------
class MajorityVote:
    """Votes on each cell's argmax move (stable tie-break: lowest move index).
    Abstaining (None / non-parseable) cells do not vote. If nothing valid remains,
    the combiner abstains (None). Combined row = vote counts + small deterministic
    tie-breaks (mean cell score at 1e-3, move-index at 1e-9) so top-1 under the
    exact px1 evaluate() is the majority winner and the full row is a parseable
    9-float score row."""

    def __init__(self, cells, name: str = "majority_vote"):
        self.cells = list(cells)
        self.name = name

    def score_batch(self, B):
        per_cell = [c.score_batch(B) for c in self.cells]
        out = []
        for j in range(len(B)):
            rows = [rc[j] for rc in per_cell if rc[j] is not None and row_ok(rc[j])]
            if not rows:
                out.append(None)
                continue
            votes = np.zeros(9)
            for r in rows:
                votes[int(np.argsort(-r, kind="stable")[0])] += 1.0
            mean_row = np.mean(np.stack([np.asarray(r, float) for r in rows]), axis=0)
            out.append(votes + 1e-3 * mean_row + 1e-9 * (9.0 - np.arange(9)))
        return out

    def meta(self):
        return {"kind": "majority_vote", "cells": [c.meta() for c in self.cells]}


# --------------------------------------------------------------------------
# (d) pinch-to-known-answer trivial cell
# --------------------------------------------------------------------------
class PinchCell:
    """center-if-empty-else-block trivial policy, thresholded.
    Fires (emits a confident 0/1 row) only when a trigger applies; otherwise
    abstains (None). Trigger A: center (move 4) empty -> score center.
    Trigger B: exactly the moves where the OPPONENT (-1) would immediately win
    get score 1 (block). No trigger -> abstain."""

    name = "pinch"

    def __init__(self, threshold: float = 0.5):
        self.threshold = float(threshold)

    def score_batch(self, B):
        out = []
        for b in B:
            b = [int(v) for v in b]
            row = np.zeros(9)
            if b[4] == 0:  # trigger A: center-if-empty
                row[4] = 1.0
                out.append(row)
                continue
            blocks = []
            for m in range(9):
                if b[m] != 0:
                    continue
                nb = list(b)
                nb[m] = -1  # opponent plays here
                if winner(nb) == -1:
                    blocks.append(m)
            if blocks:  # trigger B: block
                for m in blocks:
                    row[m] = 1.0
                out.append(row)
            else:
                out.append(None)  # thresholded: no trigger -> abstain
        return out

    def meta(self):
        return {"kind": "pinch", "policy": "center-if-empty-else-block",
                "threshold": self.threshold}


# --------------------------------------------------------------------------
# (e) ollama cell stubs — wired, flag-gated OFF by default
# --------------------------------------------------------------------------
class OllamaCell:
    """Stub interface to a local ollama chat model that is asked for a 9-float
    score row. Constructing is always allowed (wired); scoring RAISES unless
    PX2_ENABLE_OLLAMA=1 (fail loud if the flag-gated path is hit accidentally).
    When armed, transport/parse failures are REJECTIONS (None), recorded in
    reject_log — JSON-parse or reject, never a silent guess."""

    def __init__(self, model: str, host: str | None = None):
        self.model = model
        self.name = f"ollama:{model}"
        self.host = host or OLLAMA_HOST
        self.reject_log: list[dict] = []

    @property
    def enabled(self) -> bool:
        return ollama_enabled()

    def prompt(self, board) -> str:
        sym = {-1: "O", 0: ".", 1: "X"}
        pretty = " ".join(sym[int(v)] for v in board)
        return (
            "Tic-tac-toe board, row-major cells 0..8 (X = own, O = opponent, . = empty).\n"
            f"Board: {pretty}\n"
            "X to move. Score each of the 9 moves for X: higher = better for X.\n"
            "Respond with ONLY a JSON array of exactly 9 numbers, e.g. "
            "[0.1, 0.0, -1.0, 0.0, 2.0, 0.0, -1.0, 0.0, 0.3]"
        )

    def _chat(self, board) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [{"role": "user", "content": self.prompt(board)}],
        }
        req = urllib.request.Request(
            self.host + "/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return str(data.get("message", {}).get("content", ""))

    def _parse_row(self, content: str):
        i, j = content.find("["), content.rfind("]")
        if i < 0 or j <= i:
            return None
        try:
            arr = json.loads(content[i:j + 1])
        except json.JSONDecodeError:
            return None
        if not isinstance(arr, list) or len(arr) != 9:
            return None
        try:
            r = np.array([float(x) for x in arr], dtype=np.float64)
        except (TypeError, ValueError):
            return None
        return r if bool(np.all(np.isfinite(r))) else None

    def score_batch(self, B):
        if not self.enabled:
            raise RuntimeError(
                f"{self.name}: ollama cells are flag-gated OFF "
                "(set PX2_ENABLE_OLLAMA=1 to arm) — smoke runs must stay CPU-only"
            )
        out = []
        for b in B:
            try:
                row = self._parse_row(self._chat(b))
                reason = None if row is not None else "unparseable-or-not-9-finite-floats"
            except Exception as e:  # transport failure -> recorded rejection
                row, reason = None, repr(e)
            if row is None:
                self.reject_log.append({"board": [int(v) for v in b], "reason": reason})
            out.append(row)
        return out

    def meta(self):
        return {"kind": "ollama_stub", "model": self.model, "host": self.host,
                "enabled": self.enabled, "n_rejects": len(self.reject_log)}


def make_ollama_cells() -> dict:
    return {f"ollama:{m}": OllamaCell(m) for m in OLLAMA_MODELS}


# --------------------------------------------------------------------------
# registry builder
# --------------------------------------------------------------------------
def build_registry(seed: int = 0, depths=(3, 4, 6)):
    """Enumerate terrain, reproduce the PX1 seed-0 split, train tree cells on the
    TRAIN split ONLY, and assemble the full launch-roster cell set.
    Returns (states, (train_idx, test_idx), cells_dict, meta)."""
    t0 = time.time()
    states = enumerate_reachable()
    digest = fnv1a64(
        b"".join(bytes((int(v) + 1) for v in b) + bytes(opt) for b, opt in states)
    )
    if digest != EXPECTED_TERRAIN_DIGEST:
        raise RuntimeError(
            f"terrain digest mismatch: got {digest}, expected {EXPECTED_TERRAIN_DIGEST} "
            "(pre-reg terrain is SuperInstance/pie-minimax @ main)"
        )
    tr, te = px1_seed0_split(len(states), seed=seed)
    B, M = matrices(states)
    Btr, Mtr = B[tr], M[tr]

    cells: dict = {f"tree_d{k}": train_tree_cell(k, Btr, Mtr, seed=seed) for k in depths}
    cells["pinch"] = PinchCell()
    for name, oc in make_ollama_cells().items():  # wired, flag-gated OFF
        cells[name] = oc

    meta = {
        "registry": "PX2 patchwork cells (skeleton)",
        "pre_reg": "proposals/runs/PX2-patchwork-3x3.md (FROZEN 2026-09-30)",
        "device": device_string(ollama_enabled()),
        "terrain_digest_fnv1a64": digest,
        "n_states": len(states),
        "split_seed": seed,
        "n_train": int(len(tr)),
        "n_test": int(len(te)),
        "train_split_only": True,
        "tree_seed": seed,
        "tree_hyperparams": {"max_depths": list(depths), "min_samples_leaf": 5,
                             "random_state": seed},
        "ollama_flag_enabled": ollama_enabled(),
        "ollama_models": OLLAMA_MODELS,
        "ollama_host": OLLAMA_HOST,
        "cell_metas": {k: v.meta() for k, v in cells.items()},
        "build_seconds": round(time.time() - t0, 1),
    }
    return states, (tr, te), cells, meta


if __name__ == "__main__":
    # Tiny registry sanity pass (train-split states only; no test data touched).
    states, (tr, te), cells, meta = build_registry(seed=0)
    B, M = matrices(states)
    Btr, Mtr = B[tr], M[tr]
    print(json.dumps(meta["cell_metas"], indent=2))
    mv = MajorityVote([FormatGate(cells["tree_d3"]), FormatGate(cells["tree_d4"])])
    rows = mv.score_batch(Btr[:5])
    for j, r in enumerate(rows):
        ok = row_ok(r) and r is not None
        opt = set(int(m) for m in Mtr[j].nonzero()[0])
        top = int(np.argsort(-r, kind="stable")[0])
        print(f"train[{j}] row_ok={ok} top1={top} optimal={sorted(opt)} in_opt={top in opt}")
    pinch_rows = cells["pinch"].score_batch(Btr[:20])
    print("pinch fired on", sum(1 for r in pinch_rows if r is not None), "/20 train states")
    print("ollama stub armed?", {n: c.enabled for n, c in cells.items() if n.startswith("ollama")})
