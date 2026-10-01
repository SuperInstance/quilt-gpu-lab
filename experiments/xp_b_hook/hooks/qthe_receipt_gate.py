#!/usr/bin/env python3
"""qthe_receipt_gate.py — XP-B hook: refuse dishonest cell commits, accept honest ones.

Installed (symlinked) as .git/hooks/pre-commit AND .git/hooks/commit-msg in the
corpus repo. The commit message is NOT available to pre-commit (git exposes a
stale/absent .git/COMMIT_EDITMSG), so:

  * commit-msg mode ($1 = message file) -> FULL validation:
        structural + receipt parse + sha256 + fnv64 + chain(prev) match.
  * pre-commit mode                      -> STRUCTURAL validation of staged cells.

Exit 0 = accept, exit 1 = refuse (named reason on stderr). Fail loud.
No shell=True anywhere; list-form subprocess only.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

PREFIX = "QTHE-GATE"


def git(*args: str, cwd: str = None) -> str:
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), p.stderr.strip()))
    return p.stdout


def refuse(reason: str) -> int:
    sys.stderr.write("%s REFUSE: %s\n" % (PREFIX, reason))
    return 1


def accept(detail: str = "") -> int:
    sys.stderr.write("%s ACCEPT%s\n" % (PREFIX, (" " + detail) if detail else ""))
    return 0


def load_staged_cells(root: str):
    """Return {path: cell-dict} for staged cells/*.json (added/copied/modified)."""
    out = git("diff", "--cached", "--name-only", "--diff-filter=ACMR",
              "--", "cells", cwd=root)
    paths = [ln.strip() for ln in out.splitlines() if ln.strip().endswith(".json")]
    cells = {}
    for rel in paths:
        full = os.path.join(root, rel)
        try:
            with open(full, "r", encoding="utf-8") as f:
                cell = json.load(f)
        except Exception as e:
            raise ValueError("staged %s unreadable/not JSON: %s" % (rel, e))
        cells[rel] = cell
    return cells


def structural_check(cells: dict) -> None:
    if not cells:
        raise ValueError("no staged cells/*.json in this commit")
    for rel, c in cells.items():
        for k in ("id", "kind", "dials", "seed", "body"):
            if k not in c:
                raise ValueError("%s missing field %r" % (rel, k))
        if not isinstance(c["dials"], list) or len(c["dials"]) != 16:
            raise ValueError("%s dials must be a list of 16 (got %r)"
                             % (rel, len(c["dials"]) if isinstance(c["dials"], list) else c["dials"]))
        for d in c["dials"]:
            if isinstance(d, bool) or not isinstance(d, int):
                raise ValueError("%s dial not an int: %r" % (rel, d))
        if isinstance(c["seed"], bool) or not isinstance(c["seed"], int):
            raise ValueError("%s seed not an int" % rel)
        if not isinstance(c["body"], str) or not c["body"]:
            raise ValueError("%s body empty/not a string" % rel)
        if exp_id_ok(c["id"]) is False:
            raise ValueError("%s id malformed: %r" % (rel, c["id"]))


def exp_id_ok(cell_id) -> bool:
    return isinstance(cell_id, str) and cell_id.startswith("cell-")


def parent_receipt_sha(root: str) -> str:
    """Parent commit's receipt sha256 (chain link), or GENESIS."""
    p = subprocess.run(["git", "log", "-1", "--format=%B", "HEAD"],
                       cwd=root, capture_output=True, text=True)
    if p.returncode != 0:
        return "GENESIS"  # no parent (root commit)
    body = p.stdout
    sys.path.insert(0, root)
    import qthe_receipt as q  # noqa: E402
    try:
        return q.parse_receipt(body)["sha256"]
    except ValueError:
        return "GENESIS"


def main() -> int:
    hook = os.path.basename(sys.argv[0])
    root = git("rev-parse", "--show-toplevel").strip()
    sys.path.insert(0, root)
    import qthe_receipt as q  # noqa: E402

    try:
        cells = load_staged_cells(root)
        structural_check(cells)
    except (ValueError, RuntimeError) as e:
        return refuse("staged cell state invalid: %s" % e)

    if hook == "pre-commit":
        # message not reliably available here; structural gate only.
        return accept("(pre-commit: structural ok, %d staged cell file(s))" % len(cells))

    # ---- commit-msg: full validation -------------------------------------
    msg_file = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        git("rev-parse", "--git-dir").strip(), "COMMIT_EDITMSG")
    try:
        with open(msg_file, "r", encoding="utf-8") as f:
            msg = f.read()
    except Exception as e:
        return refuse("cannot read commit message file %r: %s" % (msg_file, e))

    try:
        rc = q.parse_receipt(msg)
    except ValueError as e:
        return refuse("receipt parse: %s" % e)

    prev = parent_receipt_sha(root)
    got = q.digests(cells, prev)

    if rc["prev"] != prev:
        return refuse("chain link: receipt prev=%s but parent receipt=%s (chain-repair?)"
                      % (rc["prev"][:12], prev[:12]))
    if rc["sha256"] != got["sha256"]:
        return refuse("sha256 mismatch: receipt=%s recomputed=%s (%d staged cell file(s))"
                      % (rc["sha256"][:12], got["sha256"][:12], len(cells)))
    if rc["fnv64"] != got["fnv64"]:
        return refuse("fnv64 mismatch: receipt=%s recomputed=%s"
                      % (rc["fnv64"], got["fnv64"]))
    return accept("(sha256 %s, chain %s, %d cell file(s))"
                  % (got["sha256"][:12], prev[:12], len(cells)))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # fail loud, never silently pass
        sys.stderr.write("%s REFUSE: gate error: %r\n" % (PREFIX, e))
        sys.exit(1)
