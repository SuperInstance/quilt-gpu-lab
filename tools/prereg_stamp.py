#!/usr/bin/env python3
"""prereg-stamp — bind run receipts to the committed pre-registration plan.

Pattern lifted from the lab's pre-registration doctrine (proposals/runs/*-plan.md:
"frozen delta + gate written BEFORE code runs; no post-hoc loosening"). Until now
the discipline was prose — nothing mechanical tied a booked receipt to the plan
actually committed in git. This tool makes the binding a receipt field:

  1. STAMP   sha256 over the plan file bytes -> a short fingerprint. Stamp the
             plan at run-start and write the stamp into the receipt's "prereg"
             block (helper function provided; also works via CLI).
  2. CHECK   at booking time: re-derive the plan stamp; receipt must match, and
             the plan file must be COMMITTED CLEAN in git (no uncommitted or
             untracked plan — a plan that only exists in the working tree was
             never frozen). Mismatch or dirty plan books FAIL loudly.

Fail-loud contract: rc=0 PASS, rc=1 FAIL (tamper/dirty), rc=2 FAIL-INPUT
(missing files, bad receipt, git errors). Keys are never read; stdlib-only.

EXEMPTION NOTE (2026-10-04): receipts for runs that PRE-DATE this tool's
landing (b70c64c, 2026-10-04 12:42) carry no stamp by construction — their
prereg binding is the git-verifiable pre-fire push of the plan (e.g. C5:
plan pushed e80673f 15 min before fire, receipt 0fc073f). --check on such
receipts fails by design; do NOT retro-stamp (a post-hoc stamp forges a
run-time binding). Record the pre-fire push sha as the binding instead.
"""

Worked example (self-contained):
    import prereg_stamp, json, pathlib
    plan = pathlib.Path("/tmp/plan.md"); plan.write_text("# run plan\\ngate: R2>=0.8\\n")
    stamp = prereg_stamp.stamp_file(plan)               # at run start
    receipt = {"prereg": prereg_stamp.prereg_block(plan), "verdict": "KEEP"}
    pathlib.Path("/tmp/r.json").write_text(json.dumps(receipt))
    # ... later, at booking:
    ok, why = prereg_stamp.check(plan, receipt)          # in git? -> (True, "ok")
    # edit the plan after the fact -> check() returns (False, "stamp-mismatch: ...")

CLI:
    python tools/prereg_stamp.py --stamp proposals/runs/X-plan.md
    python tools/prereg_stamp.py --check proposals/runs/X-plan.md --receipt r.json
    python tools/prereg_stamp.py --selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile

RC_PASS, RC_FAIL, RC_INPUT = 0, 1, 2


def stamp_file(plan: pathlib.Path) -> str:
    """sha256 over the raw plan bytes."""
    try:
        data = plan.read_bytes()
    except OSError as e:
        raise PreregError(f"cannot read plan {plan}: {e}")
    return hashlib.sha256(data).hexdigest()


def prereg_block(plan: pathlib.Path) -> dict:
    """The 'prereg' block to embed in a receipt at run start."""
    plan = pathlib.Path(plan)
    return {"plan": str(plan), "stamp": stamp_file(plan)}


def git(*args: str, cwd: str | None = None) -> str:
    try:
        p = subprocess.run(["git", *args], capture_output=True, text=True, timeout=30,
                           cwd=cwd)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise PreregError(f"git invocation failed: {e}")
    if p.returncode != 0:
        raise PreregError(f"git {' '.join(args)} failed: {p.stderr.strip()[:300]}")
    return p.stdout.strip()


def _plan_git_state(plan: pathlib.Path) -> str:
    """'committed-clean' | 'dirty' | 'untracked' — is the plan actually frozen?"""
    plan = plan.resolve()
    rel = str(plan)
    cwd = str(plan.parent)
    status = git("status", "--porcelain", "--", rel, cwd=cwd)
    if status:
        # '??' untracked, or modified/staged — either way not frozen as-is
        return "untracked" if status.startswith("??") else "dirty"
    ls = git("ls-files", "--", rel, cwd=cwd)
    return "committed-clean" if ls else "untracked"


class PreregError(RuntimeError):
    """Fail-loud (rc=2) input/environment problem."""


def check(plan: pathlib.Path, receipt: dict) -> tuple[bool, str]:
    """Verify a receipt's prereg block against the plan and git state."""
    plan = pathlib.Path(plan)
    if not isinstance(receipt, dict):
        raise PreregError("receipt is not a JSON object")
    block = receipt.get("prereg")
    if not isinstance(block, dict) or "stamp" not in block:
        raise PreregError("receipt has no prereg block with a stamp")
    now = stamp_file(plan)
    if now != block["stamp"]:
        recorded = str(block["stamp"])
        return False, (f"stamp-mismatch: receipt recorded {recorded[:16]}…, "
                       f"plan now hashes {now[:16]}… — plan changed after the run")
    state = _plan_git_state(plan)
    if state != "committed-clean":
        return False, f"plan not frozen in git: state={state} (uncommitted or untracked)"
    return True, "ok: stamp matches and plan is committed clean"


def _run_check(plan: pathlib.Path, receipt_path: pathlib.Path) -> int:
    try:
        receipt = json.loads(receipt_path.read_text())
        ok, why = check(plan, receipt)
    except PreregError as e:
        print(json.dumps({"tool": "prereg-stamp", "verdict": "FAIL-INPUT",
                          "detail": str(e)}, indent=2))
        return RC_INPUT
    except (json.JSONDecodeError, OSError) as e:
        print(json.dumps({"tool": "prereg-stamp", "verdict": "FAIL-INPUT",
                          "detail": f"receipt unreadable: {e}"}, indent=2))
        return RC_INPUT
    out = {"tool": "prereg-stamp", "plan": str(plan), "receipt": str(receipt_path),
           "verdict": "PASS" if ok else "FAIL", "detail": why}
    print(json.dumps(out, indent=2))
    return RC_PASS if ok else RC_FAIL


def _selftest() -> int:
    """Heredmetic battery: honest PASS, post-hoc edit FAIL, untracked FAIL,
    bad-INPUT rc=2. Positive controls exhibit the failure they guard."""
    checks: list[tuple[str, bool, str]] = []
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        repo = td / "repo"
        repo.mkdir()
        git_c = lambda *a: subprocess.run(["git", "-C", str(repo), *a],
                                          capture_output=True, text=True, check=True)
        git_c("init", "-q")
        git_c("config", "user.email", "t@t")
        git_c("config", "user.name", "t")
        plan = repo / "plan.md"
        plan.write_text("# prereg\ngate: acc >= 0.9\n")
        receipt = {"prereg": prereg_block(plan), "v": 1}

        # control 1: committed plan, untouched -> PASS
        git_c("add", ".")
        git_c("commit", "-qm", "prereg")
        ok, why = check(plan, receipt)
        checks.append(("committed-clean PASS", ok and why.startswith("ok"), why))

        # control 2: post-hoc plan edit -> stamp mismatch FAIL
        plan.write_text("# prereg\ngate: acc >= 0.5\n")  # loosened!
        ok2, why2 = check(plan, receipt)
        checks.append(("post-hoc-edit FAIL", (not ok2) and "stamp-mismatch" in why2, why2))
        plan.write_text("# prereg\ngate: acc >= 0.9\n")  # restore bytes

        # control 3: untracked plan (fresh receipt, matching stamp, never committed)
        (repo / "untracked_plan.md").write_text("# other plan\n")
        r3 = {"prereg": prereg_block(repo / "untracked_plan.md")}
        ok3, why3 = check(repo / "untracked_plan.md", r3)
        checks.append(("untracked FAIL", (not ok3) and "untracked" in why3, why3))

        # control 4: dirty plan (committed then modified, stamp updated by attacker)
        plan.write_text("# prereg\ngate: acc >= 0.95\n")
        r4 = {"prereg": prereg_block(plan)}  # stamp matches NOW but plan is dirty
        ok4, why4 = check(plan, r4)
        checks.append(("dirty FAIL", (not ok4) and "dirty" in why4, why4))

        # control 5: receipt without prereg block -> rc=2
        try:
            check(plan, {"nope": 1})
            checks.append(("missing-block rc2", False, "no exception"))
        except PreregError:
            checks.append(("missing-block rc2", True, "PreregError raised"))

    bad = [n for n, okk, _ in checks if not okk]
    print(json.dumps({"tool": "prereg-stamp", "selftest": "OK" if not bad else "FAIL",
                      "n": len(checks), "failed": bad,
                      "detail": [{n: d} for n, _, d in checks]}, indent=2))
    return RC_PASS if not bad else RC_FAIL


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="prereg-stamp — bind run receipts to the committed pre-reg plan")
    ap.add_argument("--stamp", metavar="PLAN", help="print the plan's sha256 stamp")
    ap.add_argument("--check", metavar="PLAN", help="verify receipt vs plan (with --receipt)")
    ap.add_argument("--receipt", metavar="JSON", help="receipt JSON to check")
    ap.add_argument("--selftest", action="store_true", help="run the control battery")
    a = ap.parse_args(argv)
    try:
        if a.selftest:
            return _selftest()
        if a.stamp:
            print(stamp_file(pathlib.Path(a.stamp)))
            return RC_PASS
        if a.check:
            if not a.receipt:
                ap.error("--check requires --receipt")
            return _run_check(pathlib.Path(a.check), pathlib.Path(a.receipt))
        ap.print_help()
        return RC_INPUT
    except PreregError as e:
        print(json.dumps({"tool": "prereg-stamp", "verdict": "FAIL-INPUT",
                          "detail": str(e)}, indent=2))
        return RC_INPUT


if __name__ == "__main__":
    sys.exit(main())
