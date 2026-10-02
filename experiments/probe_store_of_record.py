#!/usr/bin/env python3
"""PROBE-BATTERY #6 — air-gap / worktree-vs-index store-of-record (quilt-in-git #4).

GATE (from pr_harvest/SUMMARY.md top-10 table, #6):
    "worktree-style loader diverges >=1 under 50% drop; index-style digest exact 100%"
CARD (quilt-in-git #4): GPU analogue of their worktree-vs-index bug — a checkpoint
    loader reading MATERIALIZED tensors vs the AUTHORITATIVE store. Under simulated
    partial materialization (drop 50% of tensors), the worktree-style loader must
    silently produce wrong output (>=1 divergence) while the index-style loader
    reproduces the exact digest 100%.

Mechanism (numpy, tempdir, CPU):
  - STORE (the objects, like git): content-addressed blob per tensor shard.
  - INDEX/manifest: per checkpoint, slot name -> object digest (the store-of-record).
  - WORKTREE: a partial mirror where only a seeded 50% of shards are materialized.
  - worktree-style loader: globs whatever files exist in the worktree dir, assembles,
    silently keeps the resident prior (zeros) for missing slots -> digest.
  - index-style loader: resolves every slot through the manifest to the store,
    verifies each blob digest, refuses LOUDLY on any missing/corrupt object.
  - Harsher arm (doctrinal): 50% of STORE objects dropped too — index-style must
    refuse loudly 100% of the time (never silently wrong).

Booked to results/probe_battery/store_of_record.json. No commit.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import time

import numpy as np

SEED = 2718
ROUNDS = 5
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "results", "probe_battery", "store_of_record.json")


def blob_bytes(arr: np.ndarray) -> bytes:
    return (f"{arr.dtype.str}|{','.join(map(str, arr.shape))}|".encode()
            + arr.tobytes())


def digest(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class Store:
    def __init__(self, root):
        self.objs = os.path.join(root, "objects")
        os.makedirs(self.objs, exist_ok=True)

    def put(self, data: bytes) -> str:
        h = digest(data)
        with open(os.path.join(self.objs, h), "wb") as f:
            f.write(data)
        return h

    def get(self, h: str) -> bytes:
        with open(os.path.join(self.objs, h), "rb") as f:
            data = f.read()
        if digest(data) != h:
            raise IOError(f"object {h[:12]}: content digest mismatch (corrupt)")
        return data


def parse_blob(data: bytes) -> np.ndarray:
    hdr_s = data.split(b"|", 2)
    dtype = hdr_s[0].decode()
    shape = tuple(int(x) for x in hdr_s[1].decode().split(","))
    body = data[len(hdr_s[0]) + len(hdr_s[1]) + 2:]
    return np.frombuffer(body, dtype=np.dtype(dtype)).reshape(shape).copy()


def load_worktree_style(ckpt_dir, slot_names, fallback_shape=(8, 8)):
    """The bug under test: read whatever is materialized; missing slots silently keep
    the resident prior (zeros). No manifest consulted, no refusal."""
    state = {}
    for slot in slot_names:
        p = os.path.join(ckpt_dir, f"{slot}.npy.bin")
        if os.path.exists(p):
            with open(p, "rb") as f:
                state[slot] = parse_blob(f.read())
        else:
            state[slot] = np.zeros(fallback_shape, dtype=np.float64)  # silent prior
    return state


def load_index_style(manifest, store, slot_names):
    """Store-of-record: every slot resolved through the index to the object store,
    digest-verified; any missing object is a LOUD refusal naming the slot."""
    state = {}
    for slot in slot_names:
        if slot not in manifest:
            raise FileNotFoundError(f"index-style: slot {slot!r} not in manifest (refusing)")
        data = store.get(manifest[slot])  # raises IOError if corrupt
        state[slot] = parse_blob(data)
    return state


def state_digest(state, slot_names) -> str:
    h = hashlib.sha256()
    for slot in sorted(slot_names):
        h.update(blob_bytes(state[slot]))
    return h.hexdigest()


def main() -> int:
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    tmp = tempfile.mkdtemp(prefix="probe6_sor_")
    rounds = []
    try:
        for rd in range(ROUNDS):
            store = Store(os.path.join(tmp, f"r{rd}"))
            n_ckpt, slots = 20, ["enc", "hid", "dec", "head", "embed", "norm"]
            manifests, refs, worktrees = [], [], []
            for c in range(n_ckpt):
                manifest, ref_state, wt_dir = {}, {}, os.path.join(
                    tmp, f"r{rd}", f"wt_{c}")
                os.makedirs(wt_dir, exist_ok=True)
                for slot in slots:
                    arr = rng.normal(0, 1, size=(8, 8))
                    ref_state[slot] = arr
                    manifest[slot] = store.put(blob_bytes(arr))
                refs.append(ref_state)
                manifests.append(manifest)
                worktrees.append(wt_dir)

            # partial materialization: exactly 50% of (ckpt, slot) shards dropped
            total_shards = n_ckpt * len(slots)
            keep = rng.random(total_shards) >= 0.5
            kept = dropped = 0
            for i, keep_it in enumerate(keep):
                c, s = divmod(i, len(slots))
                if keep_it:
                    with open(os.path.join(worktrees[c], f"{slots[s]}.npy.bin"), "wb") as f:
                        f.write(blob_bytes(refs[c][slots[s]]))
                    kept += 1
                else:
                    dropped += 1

            wt_diverge = 0
            wt_silent = 0  # diverged WITHOUT any error raised
            for c in range(n_ckpt):
                try:
                    st = load_worktree_style(worktrees[c], slots)
                except Exception:
                    wt_diverge += 1
                    continue
                if state_digest(st, slots) != state_digest(refs[c], slots):
                    wt_diverge += 1
                    wt_silent += 1  # wrong output, no exception

            idx_exact = idx_loaded = 0
            for c in range(n_ckpt):
                st = load_index_style(manifests[c], store, slots)
                idx_loaded += 1
                if state_digest(st, slots) == state_digest(refs[c], slots):
                    idx_exact += 1

            # harsher arm: drop 50% of STORE objects — index-style must refuse loudly
            for i, h in enumerate(sorted(os.listdir(store.objs))):
                if i % 2 == 0:
                    os.remove(os.path.join(store.objs, h))
            refused_loud = silent_wrong = still_ok = 0
            for c in range(n_ckpt):
                try:
                    st = load_index_style(manifests[c], store, slots)
                    if state_digest(st, slots) == state_digest(refs[c], slots):
                        still_ok += 1
                    else:
                        silent_wrong += 1
                except Exception:
                    refused_loud += 1

            rounds.append({
                "round": rd, "shards_kept": kept, "shards_dropped": dropped,
                "worktree_silent_wrong": wt_silent, "worktree_divergent_total": wt_diverge,
                "index_exact_digest": idx_exact, "index_loaded": idx_loaded,
                "store_drop_arm": {"refused_loud": refused_loud,
                                   "silent_wrong": silent_wrong,
                                   "fully_loaded_ok": still_ok},
            })
            print(f"[round {rd}] kept={kept} dropped={dropped} | worktree silent-wrong="
                  f"{wt_silent}/{n_ckpt} | index exact={idx_exact}/{n_ckpt} | "
                  f"store-drop: refused-loud={refused_loud} silent-wrong={silent_wrong} "
                  f"fully-loaded-ok={still_ok}")

        tot_wt = sum(r["worktree_silent_wrong"] for r in rounds)
        tot_idx = sum(r["index_exact_digest"] for r in rounds)
        tot_load = sum(r["index_loaded"] for r in rounds)
        tot_refuse = sum(r["store_drop_arm"]["refused_loud"] for r in rounds)
        tot_silent_after_drop = sum(r["store_drop_arm"]["silent_wrong"] for r in rounds)
        gate_wt = tot_wt >= 1
        gate_idx = (tot_idx == tot_load) and tot_load > 0
        verdict = "PASS" if (gate_wt and gate_idx) else "FAIL"

        result = {
            "probe": "air-gap / worktree-vs-index store-of-record",
            "source": "pr_harvest/SUMMARY.md #6 / CARDS.md quilt-in-git #4",
            "gate": "worktree-style loader diverges >=1 under 50% drop (silently); "
                    "index-style loader digest-exact 100%. Doctrinal extra: with store "
                    "objects dropped too, index-style refuses loudly 100%, never "
                    "silently wrong",
            "verdict": verdict,
            "numbers": {
                "rounds": rounds,
                "totals": {"worktree_silent_wrong": tot_wt,
                           "index_exact": f"{tot_idx}/{tot_load}",
                           "store_drop_refused_loud": tot_refuse,
                           "store_drop_silent_wrong": tot_silent_after_drop},
                "gate_clauses": {"worktree_diverges_ge_1": bool(gate_wt),
                                 "index_exact_100pct": bool(gate_idx)},
                "reading": ("reading the materialized worktree silently fabricates state "
                            "for un-materialized shards (zeros prior) — the exact "
                            "quilt-in-git #4 sparse-view blindness; resolving every slot "
                            "through the manifest + content-addressed store is immune to "
                            "worktree state and refuses loudly when the store itself is "
                            "damaged"),
            },
            "seed": SEED,
            "runtime_seconds": round(time.time() - t0, 1),
            "device": "cpu",
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(result, f, indent=2)
    print(f"VERDICT: {verdict} (worktree silent-wrong total={tot_wt}, "
          f"index exact={tot_idx}/{tot_load}, store-drop refused-loud={tot_refuse})")
    print(f"booked -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
