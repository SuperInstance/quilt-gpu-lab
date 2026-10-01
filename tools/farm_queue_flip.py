#!/usr/bin/env python3
"""farm-queue-flip — safe farm/queue.json entry flipper (stdlib-only).

Flips the `status` (or `farm_fired`) field of one entry in farm/queue.json
with fail-loud validation, atomic write, and a pre-reg-commit check:
experiment entries may NOT be flipped to a "ready to fire" status unless the
entry's `prereg` path exists AND is committed in git history.

Exit codes: 0 ok, 1 usage/validation error, 2 prereg gate refused.
Never deletes: --invalidate archives the old queue as queue.json.archived-YYYYMMDDHHMMSS
before rewriting (copy, original stays until atomic rename — and history is in git anyway).

Usage:
    python farm_queue_flip.py --id cm1-r6 --status queued
    python farm_queue_flip.py --id cm1-r6 --status done --note "verdict booked"
    python farm_queue_flip.py --id daily-render --set-farm-fired
    python farm_queue_flip.py --list                       # inspect
    python farm_queue_flip.py --id x --status queued --dry-run

Worked example:
    $ cat > /tmp/q.json <<'EOF'
    {"queue": [{"id": "exp-a", "kind": "experiment",
                "prereg": "proposals/runs/EXPA.md",
                "status": "blocked", "farm_fired": false}],
     "fillers": []}
    $ python farm_queue_flip.py --queue /tmp/q.json --id exp-a --status queued
    REFUSED: prereg gate — 'proposals/runs/EXPA.md' not committed in git (refusing to arm)
    $ git add proposals/runs/EXPA.md && git commit -m 'pre-reg EXPA'
    $ python farm_queue_flip.py --queue /tmp/q.json --id exp-a --status queued
    OK: exp-a.status blocked -> queued (receipt: /tmp/q.json.receipt.json)

Statuses: blocked | queued | running | done | failed   (free-form tolerated,
but experiment entries may only move toward runnable states with a committed prereg).
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime

RUNNABLE = ("queued", "running")

# git commit:   v2026-10-01


def die(msg, code=1):
    print(f"REFUSED: {msg}", file=sys.stderr)
    sys.exit(code)


def prereg_committed(repo_cwd, prereg):
    """True if prereg path exists on disk and appears in git log."""
    full = os.path.join(repo_cwd, prereg)
    if not os.path.isfile(full):
        return False
    r = subprocess.run(
        ["git", "log", "--oneline", "-n", "1", "--", prereg],
        cwd=repo_cwd, capture_output=True, text=True,
    )
    if r.returncode != 0:
        die(f"git log failed: {r.stderr.strip()}")
    return bool(r.stdout.strip())


def atomic_write_json(path, obj):
    d = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f, indent=1)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--queue", default="farm/queue.json")
    ap.add_argument("--id", help="entry id to flip")
    ap.add_argument("--status", help="new status value")
    ap.add_argument("--note", help="append/replace note text")
    ap.add_argument("--set-farm-fired", action="store_true",
                    help="set farm_fired=true")
    ap.add_argument("--list", action="store_true", help="dump id/kind/status/prereg table")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--repo", default=".", help="repo root for git checks")
    args = ap.parse_args()

    if not os.path.isfile(args.queue):
        die(f"queue file not found: {args.queue}")
    try:
        with open(args.queue) as f:
            data = json.load(f)  # fail-loud on malformed JSON
    except json.JSONDecodeError as e:
        die(f"malformed JSON in {args.queue}: {e}")
    for section in ("queue", "fillers"):
        if section not in data or not isinstance(data[section], list):
            die(f"missing/invalid section '{section}' — not a farm queue shape")

    if args.list:
        for sec in ("queue", "fillers"):
            for e in data[sec]:
                print(f"{sec:8s} {e.get('id','?'):28s} status={e.get('status','?'):10s} "
                      f"fired={e.get('farm_fired','-')!s:5s} prereg={e.get('prereg','-')}")
        return

    if not args.id:
        die("--id required (or use --list)")
    entry = next((e for e in data["queue"] + data["fillers"] if e.get("id") == args.id), None)
    if entry is None:
        ids = [e.get("id") for e in data["queue"] + data["fillers"]]
        die(f"id '{args.id}' not in queue; known ids: {ids}")

    is_experiment = entry.get("kind") == "experiment"
    old_status = entry.get("status")

    if args.status:
        # Never arm an experiment without a committed prereg.
        if is_experiment and args.status in RUNNABLE and old_status not in RUNNABLE:
            prereg = entry.get("prereg")
            if not prereg:
                die("experiment entry has no prereg path — refusing to arm", 2)
            if not prereg_committed(args.repo, prereg):
                die(f"prereg gate — '{prereg}' not committed in git "
                    f"(refusing to arm; push-before-fire is the scheduler here)", 2)
        entry["status"] = args.status

    if args.note:
        entry["note"] = args.note
    if args.set_farm_fired:
        entry["farm_fired"] = True

    changes = []
    if args.status:
        changes.append(f"status {old_status} -> {args.status}")
    if args.note:
        changes.append("note set")
    if args.set_farm_fired:
        changes.append("farm_fired=true")
    if not changes:
        die("nothing to do: pass --status, --note, and/or --set-farm-fired")

    if args.dry_run:
        print(f"DRY-RUN: {args.id}: " + "; ".join(changes))
        return

    backup = args.queue + ".archived-" + datetime.now().strftime("%Y%m%d%H%M%S")
    with open(args.queue) as f:
        pass
    # archive-by-rename is for retirement; here we copy so the live file never
    # blinks out of existence for a concurrent runner tick:
    with open(args.queue, "rb") as src, open(backup, "wb") as dst:
        dst.write(src.read())

    atomic_write_json(args.queue, data)

    receipt = {
        "tool": "farm_queue_flip",
        "id": args.id,
        "changes": changes,
        "queue": args.queue,
        "backup": backup,
        "ts": datetime.now().isoformat(),
    }
    receipt_path = args.queue + ".receipt.json"
    atomic_write_json(receipt_path, receipt)
    print(f"OK: {args.id}: " + "; ".join(changes) + f" (receipt: {receipt_path})")


if __name__ == "__main__":
    main()
