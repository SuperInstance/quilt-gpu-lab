#!/usr/bin/env python3
"""git_anchor_check.py — verify a sealed receipt-manifest against COMMITTED
git content, not the working tree.

Pattern lifted from SCOUT-92 (booked 2026-10-10, canons d5c8ccc): the
fleet-witness report's executed attack was exactly the reseal-forgery class
— an attacker with write access re-seals tampered content (sealing is not a
secret operation) and the verifier consults a mutable working-tree state, so
nothing in the verify path reads back through git history. receipt-manifest
--check has the same shape gap: it compares sealed digests vs working-tree
tracked files. This tool closes it: every (path, sha256) in the manifest is
re-derived from the bytes git actually committed at --ref via
`git show <ref>:<path>` (list-form subprocess, no shell).

Verdicts:
  ANCHORED rc=0  every manifest digest matches the committed blob AND the
                 path is tracked at --ref (seal commit landed with content).
  RED     rc=1   any digest drift vs committed content, any path absent from
                 the commit (phantom seal — sealed bytes git never saw), or
                 any unreadable blob. Named per-path.
  FAIL-INPUT rc=2 bad manifest JSON, malformed digests, bad ref, git failure.

Manifest schema: tolerant — any nested dict whose leaf values are 64-hex
sha256 and whose key paths resolve under repo root are censused (works with
receipts/manifest.json's ledgers/experiments/tools sections and flat maps).

Stdlib-only. Read-only: never mutates the repo, never checks out anything.

CLI:
    python tools/git_anchor_check.py --manifest receipts/manifest.json --ref HEAD [--out r.json]
    python tools/git_anchor_check.py --selftest

Worked example:
    # after `git commit -m "spool"` and `python tools/receipt_manifest.py`:
    #   python tools/git_anchor_check.py --manifest receipts/manifest.json --ref HEAD
    # -> ANCHORED rc=0, every digest re-derived from HEAD blobs matches.
    # The forgery control: tamper RESULTS.md, re-seal, DON'T commit ->
    # HEAD blob digest != sealed digest -> RED rc=1 naming the path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import os
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

HEX64 = set("0123456789abcdef")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def is_sha256(s) -> bool:
    return isinstance(s, str) and len(s) == 64 and set(s.lower()) <= HEX64


def looks_like_path(p) -> bool:
    return isinstance(p, str) and bool(p) and not p.startswith(".") and "\\" not in p \
        and ".." not in PurePosixPath(p).parts


def extract_pairs(manifest: dict) -> list[tuple[str, str, str]]:
    """Walk any nested manifest; collect (raw_key, sha256, prefix) triples where
    values are 64-hex digests and keys look like repo paths. Prefix carries the
    section name (e.g. 'experiments') so the caller can resolve implied-dir keys
    like experiments/<name>.py and flat ledgers like RESULTS.md."""
    out: list[tuple[str, str, str]] = []

    def walk(d, prefix):
        for k, v in d.items():
            if isinstance(v, dict):
                walk(v, "" if (not isinstance(k, str) or "/" in k) else str(k))
            elif is_sha256(v) and looks_like_path(k):
                out.append((str(k), v.lower(), prefix))

    walk(manifest, "")
    if not out:
        raise ValueError("no (path, sha256) pairs found in manifest — is this a sealed manifest?")
    return out


def resolve_path(raw: str, prefix: str, repo: Path, ref: str) -> str:
    """Resolve a manifest key to a repo-relative path: try prefixed (section-dir
    implied) then bare; prefer whichever exists in the working tree, else whichever
    exists in git at ref, else the prefixed form (it will RED as phantom — named)."""
    cands = ([f"{prefix}/{raw}", raw] if prefix and "/" not in raw else [raw])
    seen: list[str] = []
    for c in cands:
        if c not in seen:
            seen.append(c)
    for c in seen:
        if (repo / c).is_file():
            return c
    for c in seen:
        blob, gerr = git_show(repo, ref, c)
        if blob is not None:
            return c
    return seen[0]


def git_show(repo: Path, ref: str, path: str):
    """Return committed bytes at ref:path. (None, None) = absent; (None, err) = git failure."""
    r = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=repo, capture_output=True)
    if r.returncode == 0:
        return r.stdout, None
    err = (r.stderr or b"").decode(errors="replace")
    if "does not exist" in err or "exists on disk, but not in" in err or "Not a valid object name" in err:
        return None, None
    return None, err.strip()


def git_ref_exists(repo: Path, ref: str) -> str | None:
    r = subprocess.run(["git", "rev-parse", "--verify", ref], cwd=repo, capture_output=True, text=True)
    if r.returncode != 0:
        return (r.stderr or "unknown git error").strip()
    return None


def check(manifest_path: Path, ref: str, repo: Path) -> dict:
    receipt = {
        "tool": "git-anchor-check",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "manifest": str(manifest_path), "ref": ref, "repo": str(repo),
        "verdict": None, "paths": {}, "n_paths": 0,
        "why": None,
    }
    err = git_ref_exists(repo, ref)
    if err is not None:
        receipt["verdict"] = "FAIL-INPUT"
        receipt["why"] = f"bad ref {ref!r}: {err}"
        return receipt
    try:
        pairs = extract_pairs(json.loads(manifest_path.read_text()))
    except Exception as e:
        receipt["verdict"] = "FAIL-INPUT"
        receipt["why"] = f"manifest unreadable/invalid: {e}"
        return receipt
    receipt["n_paths"] = len(pairs)
    red = []
    for raw, sealed, prefix in sorted(pairs):
        path = resolve_path(raw, prefix, repo, ref)
        blob, gerr = git_show(repo, ref, path)
        if gerr is not None:
            receipt["paths"][path] = {"verdict": "FAIL-INPUT", "why": f"git show failed: {gerr}"}
            red.append(path)
            continue
        if blob is None:
            receipt["paths"][path] = {
                "verdict": "RED", "sealed": sealed,
                "why": f"path absent from {ref} — phantom seal (sealed bytes git never saw)"}
            red.append(path)
            continue
        committed = sha256_bytes(blob)
        if committed != sealed:
            receipt["paths"][path] = {
                "verdict": "RED", "sealed": sealed, "committed": committed,
                "why": f"digest drift vs {ref} — tampered-or-resealed working tree"}
            red.append(path)
        else:
            receipt["paths"][path] = {"verdict": "ANCHORED", "committed": committed}
    receipt["red"] = red
    receipt["verdict"] = "RED" if red else "ANCHORED"
    if red:
        receipt["why"] = f"{len(red)} path(s) unanchored at {ref}: {', '.join(red[:5])}"
    return receipt


def selftest() -> int:
    """Pins: (P1) clean commit -> ANCHORED; (R1) tamper+reseal, uncommitted -> RED
    (the fleet-witness class); (R2) path never committed -> RED phantom-seal;
    (F1) bad ref -> FAIL-INPUT. Returns 0 iff all pins pass."""
    ok = True
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td) / "lab"
        repo.mkdir()
        (repo / "results").mkdir()

        def g(*a):
            r = subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True)
            assert r.returncode == 0, r.stderr
            return r.stdout

        g("init", "-q", "-b", "main")
        g("config", "user.email", "t@t"); g("config", "user.name", "t")
        content = b"honest ledger line\n"
        (repo / "results" / "ledger.json").write_bytes(content)
        g("add", "."); g("commit", "-qm", "land")

        def digest_of(p):
            return sha256_bytes((repo / p).read_bytes())

        # P1: manifest matching committed content -> ANCHORED
        man = repo / "receipts.json"
        man.write_text(json.dumps({"ledgers": {"results/ledger.json": digest_of("results/ledger.json")}}))
        r1 = check(man, "HEAD", repo)
        p1 = r1["verdict"] == "ANCHORED" and r1["n_paths"] == 1
        ok &= p1
        print(f"P1 clean-anchored: {'PASS' if p1 else 'FAIL'} -> {r1['verdict']}")

        # R1: tamper content + re-seal, DO NOT commit -> RED vs HEAD (forgery class)
        (repo / "results" / "ledger.json").write_bytes(b"forged ledger line\n")
        man.write_text(json.dumps({"ledgers": {"results/ledger.json": digest_of("results/ledger.json")}}))
        r2 = check(man, "HEAD", repo)
        p2 = r2["verdict"] == "RED" and "tampered-or-resealed" in r2["paths"]["results/ledger.json"]["why"]
        ok &= p2
        print(f"R1 reseal-forgery RED: {'PASS' if p2 else 'FAIL'} -> {r2['verdict']} {r2.get('why','')[:70]}")

        # R2: path absent from git -> phantom-seal RED
        (repo / "results" / "ghost.json").write_bytes(b"never committed\n")
        man.write_text(json.dumps({"ledgers": {
            "results/ledger.json": sha256_bytes(b"honest ledger line\n"),
            "results/ghost.json": sha256_bytes(b"never committed\n")}}))
        r3 = check(man, "HEAD", repo)
        p3 = r3["verdict"] == "RED" and "phantom seal" in r3["paths"]["results/ghost.json"]["why"] \
            and r3["paths"]["results/ledger.json"]["verdict"] == "ANCHORED"
        ok &= p3
        print(f"R2 phantom-seal RED: {'PASS' if p3 else 'FAIL'} -> {r3['verdict']}")

        # F1: bad ref -> FAIL-INPUT
        r4 = check(man, "nosuchref", repo)
        p4 = r4["verdict"] == "FAIL-INPUT"
        ok &= p4
        print(f"F1 bad-ref fail-loud: {'PASS' if p4 else 'FAIL'} -> {r4['verdict']}")

    print("selftest:", "OK 4/4" if ok else "FAIL")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Verify a sealed manifest against committed git blobs (git show <ref>:<path>), not the working tree.")
    ap.add_argument("--manifest", type=Path, help="sealed manifest JSON (path->sha256 map, any nesting)")
    ap.add_argument("--ref", default="HEAD", help="git ref to anchor against (default HEAD)")
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent.parent, help="repo root (default: this checkout)")
    ap.add_argument("--out", type=Path, help="write JSON receipt here too")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.manifest or not args.manifest.is_file():
        print("FAIL-INPUT: --manifest required and must exist", file=sys.stderr)
        return 2
    rc = {"ANCHORED": 0, "RED": 1, "FAIL-INPUT": 2}
    try:
        rec = check(args.manifest, args.ref, args.repo.resolve())
    except Exception as e:
        print(f"FAIL-INPUT: {e}", file=sys.stderr)
        return 2
    if args.out:
        args.out.write_text(json.dumps(rec, indent=1))
        rec["receipt"] = str(args.out)
    print(json.dumps(rec, indent=1))
    return rc[rec["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
