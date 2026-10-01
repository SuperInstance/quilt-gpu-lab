#!/usr/bin/env python3
"""run_all.py — XP-B mutation-class harness.

Runs the 5 pre-registered corruption classes + clean controls against the
receipt gate in the seeded corpus repo. Writes raw results to <out>/mutations.json.
List-form subprocess only; no shell=True. Fail loud.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qthe_receipt as q  # noqa: E402

REPO = os.path.join(HERE, "repo")
OUT = os.path.join(HERE, "out")
GPU_JSON = os.path.join(OUT, "m5_gpu.json")
BASE = None  # pinned base commit; test commits must not advance the chain base


def sh(cmd, cwd=REPO):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def head_receipt_line() -> str:
    body = sh(["git", "log", "-1", "--format=%B", "HEAD"]).stdout
    for ln in body.splitlines():
        if ln.strip().startswith(q.RECEIPT_PREFIX):
            return ln.strip()
    raise RuntimeError("no receipt in HEAD message")


def head_receipt_sha() -> str:
    return q.parse_receipt(head_receipt_line())["sha256"]


def write_cell(rel, cell):
    path = os.path.join(REPO, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cell, f, indent=2, sort_keys=True)


def restore():
    sh(["git", "reset", "-q", "--hard", BASE])
    sh(["git", "clean", "-qfd", "--", "cells"])


def attempt(name, files, msg):
    """files: {rel: cell}. msg: full message text. Returns dict."""
    restore()
    for rel, cell in files.items():
        write_cell(rel, cell)
    paths = sorted(files)
    sh(["git", "add", "--"] + paths)
    msg_path = os.path.join(OUT, "msg_%s.txt" % name)
    with open(msg_path, "w", encoding="utf-8") as f:
        f.write(msg)
    p = sh(["git", "commit", "-F", msg_path])
    # find the gate's verdict line
    verdict = None
    reason = None
    for ln in (p.stderr or "").splitlines():
        if ln.startswith("QTHE-GATE"): 
            verdict = "ACCEPT" if " ACCEPT" in ln else "REFUSE"
            reason = ln.strip()
    if verdict is None:
        verdict = "NO-GATE-VERDICT"
        reason = (p.stderr or "").strip()[:300]
    committed = p.returncode == 0
    restore()
    return {"test": name, "committed": committed, "gate_verdict": verdict,
            "gate_line": reason, "git_stderr": (p.stderr or "").strip()[:400]}


def make_new_cell(idx, kind="matmul", seed=2718):
    return {"id": "cell-x%03d" % idx, "kind": kind,
            "dials": [(idx * 7 + k * 13) % 100 for k in range(16)],
            "seed": seed, "body": "xp-b probe cell %d" % idx}


def main() -> int:
    global BASE
    os.makedirs(OUT, exist_ok=True)
    BASE = sh(["git", "rev-parse", "HEAD"]).stdout.strip()
    restore()
    results = {"classes": [], "controls": []}
    prev = head_receipt_sha()

    # ---------------- CLEAN CONTROLS (must ACCEPT) ----------------
    # C1: honest new cell, correct receipt
    c1 = make_new_cell(1)
    rel1 = "cells/cell_x001.json"
    d1 = q.digests({rel1: c1}, prev)
    results["controls"].append(attempt(
        "C1_honest_new_cell", {rel1: c1},
        "xp-b c1\n\n%s\n" % q.receipt_line(d1["sha256"], d1["fnv64"], prev)))

    # C2: legitimate dial change with a correctly updated receipt
    c2 = make_new_cell(2)
    rel2 = "cells/cell_x002.json"
    d_a = q.digests({rel2: c2}, prev)
    c2b = json.loads(json.dumps(c2)); c2b["dials"][3] = (c2b["dials"][3] + 5) % 100
    d_b = q.digests({rel2: c2b}, prev)
    results["controls"].append(attempt(
        "C2_honest_dial_update", {rel2: c2b},
        "xp-b c2\n\n%s\n" % q.receipt_line(d_b["sha256"], d_b["fnv64"], prev)))
    results["controls"].append({
        "test": "C2_receipt_changed_after_update",
        "receipt_before": d_a["sha256"][:12], "receipt_after": d_b["sha256"][:12],
        "changed": d_a["sha256"] != d_b["sha256"]})

    # C3: two cells staged in one commit
    c3a, c3b = make_new_cell(3), make_new_cell(4, kind="attn")
    rel3a, rel3b = "cells/cell_x003.json", "cells/cell_x004.json"
    d3 = q.digests({rel3a: c3a, rel3b: c3b}, prev)
    results["controls"].append(attempt(
        "C3_two_cells_one_commit", {rel3a: c3a, rel3b: c3b},
        "xp-b c3\n\n%s\n" % q.receipt_line(d3["sha256"], d3["fnv64"], prev)))

    # ---------------- M1: dial changed, receipt stale ----------------
    m1 = make_new_cell(11)
    relm1 = "cells/cell_x011.json"
    dm1 = q.digests({relm1: m1}, prev)
    m1b = json.loads(json.dumps(m1)); m1b["dials"][0] = (m1b["dials"][0] + 1) % 100
    results["classes"].append(attempt(
        "M1_dial_changed_no_receipt_update", {relm1: m1b},
        "xp-b m1\n\n%s\n" % q.receipt_line(dm1["sha256"], dm1["fnv64"], prev)))

    # ---------------- M2a: receipt reused from an earlier commit ----------------
    m2 = make_new_cell(12)
    relm2 = "cells/cell_x012.json"
    old_line = head_receipt_line()  # belongs to HEAD, not this new state
    results["classes"].append(attempt(
        "M2a_chain_repair_receipt_reused", {relm2: m2},
        "xp-b m2a\n\n%s\n" % old_line))

    # ---------------- M2b: correct state digest, forged chain link ----------------
    m2b = make_new_cell(13)
    relm2b = "cells/cell_x013.json"
    dm2b = q.digests({relm2b: m2b}, prev)
    older = sh(["git", "log", "-2", "--format=%B", "HEAD~1"]).stdout
    older_sha = "0" * 64
    for ln in older.splitlines():
        if ln.strip().startswith(q.RECEIPT_PREFIX):
            older_sha = q.parse_receipt(ln)["sha256"]; break
    results["classes"].append(attempt(
        "M2b_chain_link_forged_prev", {relm2b: m2b},
        "xp-b m2b\n\n%s\n" % q.receipt_line(dm2b["sha256"], dm2b["fnv64"], older_sha)))

    # ---------------- M3a/M3b: truncated / incomplete receipt ----------------
    m3 = make_new_cell(14)
    relm3 = "cells/cell_x014.json"
    dm3 = q.digests({relm3: m3}, prev)
    trunc = q.receipt_line(dm3["sha256"], dm3["fnv64"], prev).replace(
        dm3["sha256"], dm3["sha256"][:40])
    results["classes"].append(attempt(
        "M3a_truncated_sha256", {relm3: m3}, "xp-b m3a\n\n%s\n" % trunc))

    m3b = make_new_cell(15)
    relm3b = "cells/cell_x015.json"
    dm3b = q.digests({relm3b: m3b}, prev)
    nofnv = "qthe-receipt@1 seed=2718 sha256=%s prev=%s" % (dm3b["sha256"], prev)
    results["classes"].append(attempt(
        "M3b_missing_fnv64_field", {relm3b: m3b}, "xp-b m3b\n\n%s\n" % nofnv))

    # ---------------- M4: 64-bit-only integrity (FNV recomputed, sha256 stale) --
    m4 = make_new_cell(16)
    relm4 = "cells/cell_x016.json"
    honest = q.digests({relm4: m4}, prev)
    m4b = json.loads(json.dumps(m4)); m4b["dials"][5] = (m4b["dials"][5] + 3) % 100
    corrupt = q.digests({relm4: m4b}, prev)
    line_m4 = q.receipt_line(honest["sha256"], corrupt["fnv64"], prev)
    results["classes"].append(attempt(
        "M4_fnv64_recomputed_sha256_stale", {relm4: m4b}, "xp-b m4\n\n%s\n" % line_m4))
    results["classes"].append({
        "test": "M4_fnv_primary_gate_counterfactual",
        "description": "gate variant that validates fnv64 ONLY, on the same forged commit",
        "receipt_fnv64": corrupt["fnv64"],
        "recomputed_fnv64_over_corrupted_state": corrupt["fnv64"],
        "fnv_primary_gate_would": "ACCEPT",
        "fnv_field_was_internally_consistent": True,
        "sha256_pinned_gate": "REFUSED (see M4 row above)"})

    # ---- SCOPE BOUNDARY PROBE (not a pre-registered class) -----------------
    # A deliberate forger with no keys recomputes a fully consistent receipt.
    # Expected: ACCEPT.  This is the gate's honest boundary, reported loudly.
    b1 = make_new_cell(17)
    relb1 = "cells/cell_x017.json"
    b1b = json.loads(json.dumps(b1)); b1b["dials"][9] = (b1b["dials"][9] + 4) % 100
    db1 = q.digests({relb1: b1b}, prev)
    results["boundary_probe"] = attempt(
        "BP1_deliberate_forger_recomputes_receipt", {relb1: b1b},
        "xp-b bp1\n\n%s\n" % q.receipt_line(db1["sha256"], db1["fnv64"], prev))

    # ---------------- M5: GPU-derived cell ----------------
    results["classes"].append(gpu_class(prev))

    with open(os.path.join(OUT, "mutations.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    ok_controls = all(c.get("gate_verdict") == "ACCEPT" for c in results["controls"]
                      if "gate_verdict" in c)
    refused = [c["test"] for c in results["classes"]
               if c.get("gate_verdict") == "REFUSE"]
    print(json.dumps({
        "controls_all_accepted": ok_controls,
        "controls": [(c["test"], c.get("gate_verdict")) for c in results["controls"]],
        "classes": [(c["test"], c.get("gate_verdict")) for c in results["classes"]],
        "boundary_probe": (results["boundary_probe"]["test"],
                           results["boundary_probe"]["gate_verdict"]),
        "refused": refused}, indent=2))
    return 0


def gpu_class(prev) -> dict:
    """M5: run the GPU ticks under guard, then the clean + mutated-seed commits."""
    if not os.path.exists(GPU_JSON):
        return {"test": "M5_gpu_cell", "gate_verdict": "NOT-RUN",
                "note": "no GPU evidence file (m5_gpu.json missing)"}
    with open(GPU_JSON) as f:
        g = json.load(f)
    if not g.get("ran"):
        return {"test": "M5_gpu_cell", "gate_verdict": "NOT-RUN",
                "note": g.get("note", "guard refused")}

    rel = "cells/cell_gpu000.json"
    d_honest = q.digests({rel: g["cell_seed2718"]}, prev)
    clean = attempt("M5a_gpu_cell_clean", {rel: g["cell_seed2718"]},
                    "xp-b m5 clean gpu cell\n\n%s\n"
                    % q.receipt_line(d_honest["sha256"], d_honest["fnv64"], prev))
    dirty = {"id": "cell-gpu000", "kind": "matmul", "seed": 2719,
             "body": "gpu tick seed 2719 replay", "dials": g["dials_seed2719"]}
    refuse = attempt("M5b_gpu_cell_mutated_seed", {rel: dirty},
                     "xp-b m5 mutated-seed replay\n\n%s\n"
                     % q.receipt_line(d_honest["sha256"], d_honest["fnv64"], prev))
    return {
        "test": "M5_gpu_cell",
        "determinism": g.get("determinism"),
        "gate_verdict": refuse["gate_verdict"],
        "clean_gpu_commit": clean.get("gate_verdict"),
        "clean_gpu_committed": clean.get("committed"),
        "mutated_seed_commit": refuse,
        "guard_receipt": g.get("guard_receipt"),
        "ramp_receipt": g.get("ramp_receipt"),
    }


if __name__ == "__main__":
    sys.exit(main())
