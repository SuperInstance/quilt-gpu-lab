#!/usr/bin/env python3
"""fresh_clone_witness.py — verify the sealed manifest from a pristine clone of HEAD.

Pattern lifted PROVEN from tonight's FR-2 / VX-1 / MR-1 lane (booked
2026-10-04, commit 224dc59): a seal can be green in a dirty working tree
and RED on a fresh clone — because the clone only carries what git saw.
The phantom-seal class (d23b, fc79ff1) is invisible locally and glaring
from the outside. This tool IS the outside: it clones HEAD (or any ref)
into a throwaway temp dir and re-derives every sealed digest there.

What it checks, in the clone (never the working tree):
  1. receipts/manifest.json exists at the ref
  2. every sealed digest (ledgers / experiments / tools) re-derives
     from the cloned bytes — no drift, nothing missing, nothing unsealed
  3. (optional --run-pins) the clone's own pin suite still passes

The local tree's opinions are irrelevant to this witness; if you want
local drift, use `python tools/receipt_manifest.py --check`. Exit codes:
0 = PASS (clean on the pristine clone), 1 = RED (drift found), 2 = FAIL
(bad invocation / git error — never a silent pass).

Worked example (self-witness this repo at HEAD):
    python tools/fresh_clone_witness.py --ref HEAD
    python tools/fresh_clone_witness.py --ref HEAD --run-pins
    python tools/fresh_clone_witness.py --ref origin/main --out witness.json

Negative control (the point of the tool — demonstrated live 2026-10-04):
tamper a sealed file in an index without committing, push nothing; the
local tree still seals fine; this witness clones HEAD and sees the truth.

Stdlib-only. List-form subprocess throughout. Never mutates the repo —
clone lands in a tempfile.TemporaryDirectory and is deleted by the OS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCHEMA = "fresh-clone-witness@1"
SEALED_PATHS = ("RESULTS.md", "QUEUE.md", "experiments", "tools")
TOOL_SUFFIXES = {".py", ".pt", ".sh", ".mjs", ".js"}


def die(msg: str) -> None:
    print(f"WITNESS-FAIL: {msg}", file=sys.stderr)
    raise SystemExit(2)


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def live_digests(lab: Path) -> dict[str, dict[str, str]]:
    """Re-derive the manifest's digest universe from a tree on disk."""
    out: dict[str, dict[str, str]] = {
        "ledgers": {
            "RESULTS.md": sha256(lab / "RESULTS.md"),
            "QUEUE.md": sha256(lab / "QUEUE.md"),
        },
        "experiments": {
            p.name: sha256(p) for p in sorted((lab / "experiments").glob("*.py"))
        },
        "tools": {},
    }
    for p in sorted((lab / "tools").iterdir()):
        if p.is_file() and (p.suffix in TOOL_SUFFIXES or p.name == "README.md"):
            out["tools"][p.name] = sha256(p)
    return out


def clone_head(repo: Path, ref: str, dest: Path) -> str:
    r = run(["git", "clone", "--quiet", "--no-hardlinks", str(repo), str(dest)])
    if r.returncode != 0:
        die(f"git clone failed: {r.stderr.strip()[:300]}")
    r = run(["git", "checkout", "--quiet", ref], cwd=dest)
    if r.returncode != 0:
        die(f"git checkout {ref} failed: {r.stderr.strip()[:300]}")
    r = run(["git", "rev-parse", "HEAD"], cwd=dest)
    if r.returncode != 0:
        die("git rev-parse failed in clone")
    return r.stdout.strip()


def witness_drift(clone: Path) -> list[str]:
    """Compare sealed manifest vs re-derived digests, all inside the clone."""
    manifest_path = clone / "receipts" / "manifest.json"
    if not manifest_path.exists():
        return [f"{manifest_path.relative_to(clone)}: MISSING — ref was never sealed"]
    try:
        sealed = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as e:
        return [f"receipts/manifest.json: CORRUPT JSON ({e})"]
    live = live_digests(clone)
    drift: list[str] = []
    for section in ("ledgers", "experiments", "tools"):
        want, got = sealed.get(section, {}), live[section]
        for name in sorted(set(want) | set(got)):
            if name not in want:
                drift.append(f"{section}/{name}: UNSEALED (in clone, not manifest) {got[name][:12]}…")
            elif name not in got:
                drift.append(f"{section}/{name}: sealed but MISSING from clone")
            elif want[name] != got[name]:
                drift.append(f"{section}/{name}: DRIFT sealed {want[name][:12]}… clone {got[name][:12]}…")
    return drift


def run_pins(clone: Path) -> tuple[bool, str]:
    r = run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=clone)
    tail = "\n".join(r.stdout.strip().splitlines()[-5:])
    return r.returncode == 0, tail or r.stderr.strip()[-300:]


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Witness the sealed manifest from a pristine clone of HEAD (or any ref).")
    ap.add_argument("--ref", default="HEAD", help="git ref to witness (default HEAD)")
    ap.add_argument("--out", help="write a JSON witness receipt here")
    ap.add_argument("--run-pins", action="store_true",
                    help="also run the clone's unittest pin suite (requires tests/)")
    ap.add_argument("--selftest", action="store_true", help="run the RED/GOOD control battery and exit")
    args = ap.parse_args()

    if args.selftest:
        rc = selftest(Path(__file__).resolve().parent.parent)
        raise SystemExit(rc)

    repo = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory(prefix="fcw-") as td:
        clone = Path(td) / "clone"
        commit = clone_head(repo, args.ref, clone)
        drift = witness_drift(clone)
        pins_ok, pins_tail = (run_pins(clone) if args.run_pins else (None, ""))
        receipt = {
            "schema": SCHEMA,
            "repo": str(repo),
            "ref": args.ref,
            "commit": commit,
            "verdict": "RED" if drift else ("PASS" if pins_ok is not False else "PINS-RED"),
            "drift": drift,
            "pins_run": pins_ok is not None,
            "pins_ok": pins_ok,
        }
        print(json.dumps(receipt, indent=2))
        if pins_ok is False:
            print("clone pin suite tail:\n" + pins_tail)
        if args.out:
            Path(args.out).write_text(json.dumps(receipt, indent=2) + "\n")
        if drift:
            print(f"WITNESS-RED at {args.ref} ({commit[:12]}): {len(drift)} drift line(s). "
                  "The working tree may be clean-sealed; the clone disagrees. Re-seal and commit.",
                  file=sys.stderr)
            raise SystemExit(1)
        if pins_ok is False:
            raise SystemExit(1)
        print(f"witness: PASS — {args.ref} ({commit[:12]}) is clean from the outside.")
    return


def selftest(lab: Path) -> int:
    """GOOD control: HEAD witnesses clean. RED control: a fabricated clone
    with one tampered sealed file must trip DRIFT. Both run in temp dirs."""
    failures = 0
    with tempfile.TemporaryDirectory(prefix="fcw-st-") as td:
        # GOOD
        clone = Path(td) / "good"
        commit = clone_head(lab, "HEAD", clone)
        drift = witness_drift(clone)
        print(f"selftest GOOD control: {'PASS' if not drift else 'RED?! ' + str(drift[:3])}"
              f" @ {commit[:12]}, {len(witness_drift(clone))} drift")
        if drift:
            failures += 1
        # RED: flip one byte of a sealed ledger in the clone only
        (clone / "RESULTS.md").write_text(
            (clone / "RESULTS.md").read_text() + "\n<!-- tamper -->\n")
        drift2 = witness_drift(clone)
        if not any("DRIFT" in d and d.startswith("ledgers/") for d in drift2):
            print("selftest RED control: FAIL — tamper not witnessed")
            failures += 1
        else:
            print("selftest RED control: PASS — tamper witnessed: "
                  + [d for d in drift2 if "DRIFT" in d][0])
    print(f"selftest: {'OK' if failures == 0 else f'{failures} failure(s)'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    main()
