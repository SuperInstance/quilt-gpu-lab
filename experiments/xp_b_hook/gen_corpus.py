#!/usr/bin/env python3
"""gen_corpus.py — seeded (2718) synthetic git history of 120 receipted commits.

Usage: python3 gen_corpus.py [repo_dir]
Creates the repo, installs the gate hooks (symlinked), and makes 120 commits whose
messages embed a qthe-receipt@1 line over the staged cell state + seed + chain.
Every clean commit MUST be accepted by the gate (fail loud otherwise).
"""
from __future__ import annotations

import json
import os
import random
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qthe_receipt as q  # noqa: E402

N_COMMITS = int(os.environ.get("XP_B_COMMITS", "120"))
KINDS = ["matmul", "attn", "scan", "mix"]
SEED = 2718


def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def make_cell(idx, rng):
    return {
        "id": "cell-%03d" % idx,
        "kind": KINDS[idx % len(KINDS)],
        "dials": [rng.randrange(0, 100) for _ in range(16)],
        "seed": (SEED + idx) & 0xFFFF,
        "body": "cell %03d tick %d payload %08x" % (idx, idx, rng.getrandbits(32)),
    }


def write_cell(root, idx, cell):
    os.makedirs(os.path.join(root, "cells"), exist_ok=True)
    rel = "cells/cell_%03d.json" % idx
    with open(os.path.join(root, rel), "w", encoding="utf-8") as f:
        json.dump(cell, f, indent=2, sort_keys=True)
    return rel


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "repo")
    if os.path.exists(root):
        shutil.rmtree(root)
    os.makedirs(root)

    run(["git", "init", "-q", "-b", "main", "."], root)
    run(["git", "config", "user.email", "xp-b@lab.local"], root)
    run(["git", "config", "user.name", "XP-B lane"], root)
    run(["git", "config", "commit.gpgsign", "false"], root)

    shutil.copy(os.path.join(HERE, "qthe_receipt.py"), os.path.join(root, "qthe_receipt.py"))
    hooks_dir = os.path.join(root, ".git", "hooks")
    os.makedirs(hooks_dir, exist_ok=True)
    gate = os.path.join(HERE, "hooks", "qthe_receipt_gate.py")
    for name in ("pre-commit", "commit-msg"):
        dst = os.path.join(hooks_dir, name)
        if os.path.exists(dst):
            os.remove(dst)
        os.symlink(gate, dst)
        os.chmod(gate, 0o755)

    rng = random.Random(SEED)
    prev_sha = "GENESIS"
    accepted = 0
    log = []
    for i in range(N_COMMITS):
        cell = make_cell(i, rng)
        rel = write_cell(root, i, cell)
        staged = {rel: cell}
        if i > 0 and i % 10 == 9:
            j = rng.randrange(i)
            path_j = "cells/cell_%03d.json" % j
            with open(os.path.join(root, path_j), "r", encoding="utf-8") as f:
                cj = json.load(f)
            k = rng.randrange(16)
            cj["dials"][k] = (cj["dials"][k] + 1 + rng.randrange(1, 9)) % 100
            with open(os.path.join(root, path_j), "w", encoding="utf-8") as f:
                json.dump(cj, f, indent=2, sort_keys=True)
            staged[path_j] = cj
        d = q.digests(staged, prev_sha)
        msg = "tick %03d\n\n%s\n" % (i, q.receipt_line(d["sha256"], d["fnv64"], prev_sha))
        run(["git", "add", "-A", "--", "cells"], root)
        cp = subprocess.run(["git", "commit", "-q", "-m", msg.strip()],
                            cwd=root, capture_output=True, text=True)
        rc = cp.returncode
        if rc != 0:
            sys.stderr.write(cp.stderr)
        p = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                           capture_output=True, text=True)
        ok = (rc == 0)
        log.append({"commit": i, "accepted": ok, "sha_receipt": d["sha256"],
                    "staged": sorted(staged), "head": p.stdout.strip() if ok else None})
        if not ok:
            sys.stderr.write("FATAL: clean commit %d REFUSED\n" % i)
            return 1
        accepted += 1
        prev_sha = d["sha256"]

    out = {
        "root": root, "commits": N_COMMITS, "accepted_clean": accepted,
        "seed": SEED, "final_receipt_sha": prev_sha,
        "history": log,
    }
    with open(os.path.join(HERE, "clean_history.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(json.dumps({"commits": N_COMMITS, "accepted_clean": accepted,
                      "final_receipt_sha": prev_sha}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
