#!/usr/bin/env python3
"""death_watch — heartbeat + recheck-before-claiming conductor-death detector.

Pattern lifted PROVEN from LC-1 (BOOKED PASS 2026-10-06, prereg 19810da): all 6
historical conductor-death instances in this repo were caught within one wake by
the two-line doctrine — (a) append a heartbeat line at slice START to a wake-log,
(b) re-check before claiming: the next wake verifies the PREVIOUS heartbeat's
slice reached its booking commit. "Work claims alone are insufficient — you need
a death detector" (ledger-continuity 5818938).

Usage
-----
  # at slice start:
  python tools/death_watch.py --beat lc1-audit --log .wake_log.jsonl
  # at next wake (or anywhere, before claiming anything):
  python tools/death_watch.py --check --log .wake_log.jsonl
      rc=0  CLEAN   latest beat's slice has a booking commit after it
      rc=1  DEAD    latest beat never got a commit — previous slice died mid-air
      rc=2  FAIL-INPUT  bad log, bad beats, git failure
  python tools/death_watch.py --check --log .wake_log.jsonl --branch main
  python tools/death_watch.py --selftest

Semantics
---------
The wake log is JSONL: {"ts": <epoch float>, "beat": "<slice id>"}. A beat is
CLOSED if any commit on --branch (default: HEAD) has commit time >= beat ts and
beat != latest, OR it is the latest beat and a commit exists with time >= ts.
So: start slice -> --beat; finish work -> git commit; next wake --check sees the
commit and books CLEAN; if the slice died after the beat, no commit exists and
--check books DEAD with the dead beat named. Beats are never deleted (append-only;
archive-by-rename if the log must be reset: `mv .wake_log.jsonl .wake_log.jsonl.archived-YYYYMMDD`).

Worked example
--------------
  cd some-git-repo
  python /path/to/death_watch.py --beat demo-1 --log /tmp/wake.jsonl   # beat line
  python /path/to/death_watch.py --check --log /tmp/wake.jsonl         # -> DEAD rc=1
    (no commit yet — correct: the slice hasn't booked)
  git commit --allow-empty -m "book demo-1"
  python /path/to/death_watch.py --check --log /tmp/wake.jsonl         # -> CLEAN rc=0

Stdlib-only. Git via list-form subprocess only. Timestamps never fabricated:
--beat uses time.time(); --check refuses beats with ts in the future (clock skew
fails loud, rc=2).
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

RC_CLEAN, RC_DEAD, RC_FAIL = 0, 1, 2


class FailLoud(Exception):
    pass


def run_git(repo, args):
    p = subprocess.run(["git", "-C", repo] + args,
                       capture_output=True, text=True, shell=False)
    if p.returncode != 0:
        raise FailLoud("git %s failed: %s" % (" ".join(args), p.stderr.strip()))
    return p.stdout.strip()


def latest_commit_ts(repo, branch):
    p = subprocess.run(["git", "-C", repo, "log", "-1", "--format=%ct", branch],
                       capture_output=True, text=True, shell=False)
    out = p.stdout.strip()
    if p.returncode != 0:
        if not out and any(s in p.stderr for s in ("does not have any commits", "unknown revision", "ambiguous argument")):
            return float("-inf")  # unborn branch: nothing is ever booked
        raise FailLoud("git log failed: %s" % p.stderr.strip())
    if not out:
        return float("-inf")  # repo with no commits: nothing is ever booked
    try:
        return float(out)
    except ValueError:
        raise FailLoud("git log returned non-numeric commit time: %r" % out)


def load_log(path):
    beats = []
    try:
        f = open(path, "r", encoding="utf-8")
    except OSError as e:
        raise FailLoud("wake log %s unreadable: %s" % (path, e))
    with f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                raise FailLoud("wake log line %d is not JSON: %s" % (i, e))
            if not isinstance(rec.get("ts"), (int, float)) or not isinstance(rec.get("beat"), str):
                raise FailLoud("wake log line %d missing ts(float)/beat(str): %r" % (i, line[:120]))
            beats.append({"ts": float(rec["ts"]), "beat": rec["beat"]})
    if not beats:
        raise FailLoud("wake log %s has no beats" % path)
    for prev, cur in zip(beats, beats[1:]):
        if cur["ts"] < prev["ts"]:
            raise FailLoud("wake log ts out of order at beat %r" % cur["beat"])
    now = time.time()
    for b in beats:
        if b["ts"] > now + 300:  # 5 min skew allowance
            raise FailLoud("beat %r has future ts %.0f (clock skew?)" % (b["beat"], b["ts"]))
    return beats


def check(repo, log_path, branch):
    beats = load_log(log_path)
    head_ts = latest_commit_ts(repo, branch)
    latest = beats[-1]
    # every beat except the latest must be covered by a commit at/after its ts;
    # the latest is DEAD unless a commit exists at/after its own ts.
    dead = [b for b in beats[:-1] if b["ts"] > head_ts]
    latest_dead = latest["ts"] > head_ts
    if latest_dead:
        dead.append(latest)
    return {
        "verdict": "DEAD" if dead else "CLEAN",
        "dead_beats": [b["beat"] for b in dead],
        "latest_beat": latest["beat"],
        "head_commit_ts": head_ts,
        "n_beats": len(beats),
        "checked_at": time.time(),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1],
                                 epilog="Exit: 0=CLEAN, 1=DEAD, 2=fail-loud.")
    ap.add_argument("--beat", help="append a heartbeat for slice id BEAT at slice start")
    ap.add_argument("--check", action="store_true", help="recheck: did the latest beat book?")
    ap.add_argument("--log", default=".wake_log.jsonl", help="wake-log JSONL path")
    ap.add_argument("--branch", default="HEAD", help="branch/ref whose commits count as bookings")
    ap.add_argument("--out", help="write JSON receipt here")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        ok, fails = selftest()
        print("selftest %d/%d" % (ok, ok + fails))
        sys.exit(0 if fails == 0 else 1)

    if a.beat:
        rec = {"ts": time.time(), "beat": a.beat}
        with open(a.log, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
            f.flush()
            os.fsync(f.fileno())
        print("beat recorded: %s" % a.beat)
        sys.exit(0)
    if not a.check:
        ap.error("need --beat or --check (or --selftest)")

    repo = os.getcwd()
    try:
        res = check(repo, a.log, a.branch)
        rc = RC_CLEAN if res["verdict"] == "CLEAN" else RC_DEAD
    except (FailLoud, OSError) as e:
        res = {"verdict": "FAIL-INPUT", "error": str(e), "checked_at": time.time()}
        rc = RC_FAIL
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
    print(json.dumps(res, indent=2))
    sys.exit(rc)


# ---------------- selftest ----------------

def _git(repo, *args, msg=None):
    subprocess.run(["git", "-C", repo, "init", "-q"], check=True, shell=False)
    subprocess.run(["git", "-C", repo, "config", "user.email", "t@t"], check=True, shell=False)
    subprocess.run(["git", "-C", repo, "config", "user.name", "t"], check=True, shell=False)


def _commit(repo, msg, when=None):
    env = dict(os.environ)
    if when is not None:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = str(when)
    open(os.path.join(repo, "f.txt"), "a").write(msg + "\n")
    subprocess.run(["git", "-C", repo, "add", "f.txt"], check=True, shell=False)
    subprocess.run(["git", "-C", repo, "commit", "-q", "-m", msg], check=True, env=env, shell=False)


def selftest():
    ok = fails = 0
    tmp = tempfile.mkdtemp(prefix="death_watch_st_")
    repo = os.path.join(tmp, "repo")
    os.mkdir(repo)
    _git(repo)
    log = os.path.join(repo, "wake.jsonl")

    def case(name, cond):
        nonlocal ok, fails
        if cond:
            ok += 1
        else:
            fails += 1
            print("  FAIL: %s" % name)

    def run_check():
        try:
            return RC_CLEAN if check(repo, log, "HEAD")["verdict"] == "CLEAN" else RC_DEAD
        except FailLoud:
            return RC_FAIL

    # C1: no log at all -> fail-loud
    case("missing log rc=2", run_check() == RC_FAIL)

    # C2: beat, no commit -> DEAD
    with open(log, "a") as f:
        f.write(json.dumps({"ts": time.time(), "beat": "s1"}) + "\n")
    case("unbooked beat DEAD", run_check() == RC_DEAD)

    # C3: commit after beat -> CLEAN
    _commit(repo, "book s1", when=time.time() + 1)
    case("booked beat CLEAN", run_check() == RC_CLEAN)

    # C4: new beat after booking -> DEAD again (fresh slice, unbooked)
    with open(log, "a") as f:
        f.write(json.dumps({"ts": time.time() + 2, "beat": "s2"}) + "\n")
    case("fresh unbooked beat DEAD", run_check() == RC_DEAD)

    # C5: two unbooked beats stack -> DEAD names both (each wake rechecks the
    # latest; beats only close when a commit lands at/after their own ts)
    _commit(repo, "book s2", when=time.time() + 3)
    with open(log, "a") as f:
        f.write(json.dumps({"ts": time.time() + 4, "beat": "s3"}) + "\n")
    with open(log, "a") as f:
        f.write(json.dumps({"ts": time.time() + 5, "beat": "s4"}) + "\n")
    res = check(repo, log, "HEAD")
    case("unbooked stack DEAD", res["verdict"] == "DEAD" and res["dead_beats"] == ["s3", "s4"])

    # C6: future-ts beat -> fail-loud
    with open(log, "a") as f:
        f.write(json.dumps({"ts": time.time() + 100000, "beat": "future"}) + "\n")
    case("future ts rc=2", run_check() == RC_FAIL)

    return ok, fails


if __name__ == "__main__":
    main()
