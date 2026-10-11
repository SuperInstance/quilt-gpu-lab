#!/usr/bin/env python3
"""commit_cite_check.py — phantom-commit-citation gate (read-only, stdlib-only).

PATTERN LIFTED FROM: SCOUT lineage (verdict_cite_check 2026-10-06 mechanized
"the receipt is the record"; git_anchor_check 2026-10-10 mechanized seal
verification). Remaining hole: docs/receipts cite git SHAs
("commit 5fbf882", "prereg 19810da", "5fbf882~1 -> 5fbf882") and nothing
verifies those commits actually exist in history. A typo'd or deleted-SHA
cite is a phantom citation — evidence that points nowhere.

WHAT IT DOES: scans text files for hex tokens that look like commit cites,
classifies each unique token via `git cat-file -e <tok>^{commit}`
(list-form subprocess, no shell):
  RESOLVED  — names a commit object in this repo
  PHANTOM   — hex-shaped, citation-context, but git says no such commit (RED)
  IGNORED   — no citation context AND not commit-suffixed (prose hex, ids,
              timestamps — the docs are full of 8-digit numeric ids like
              01677063; sweeping ALL hex books hundreds of false REDs)
Exit 0 = CLEAN (all cites resolve, possibly none), 1 = PHANTOM (named),
2 = fail-loud (missing file, git failure). `--all-hex` drops the context
gate for sweeping a file you know is pure cite text. `--allow tok` books a
documented-allow phantom instead of RED.

CLI:
  python tools/commit_cite_check.py --file tools/README.md [--ref HEAD --out r.json]
  python tools/commit_cite_check.py --file docs/PREREG-CLAIM-PROTOCOL.md
  python tools/commit_cite_check.py --files tools/ experiments/ --glob "*.py"
  python tools/commit_cite_check.py --selftest

WORKED EXAMPLE (do this):
  python tools/commit_cite_check.py --file tools/README.md --out /tmp/cc.json
  -> exit 0, every SHA cited in the catalog resolves.

Library API:
    from commit_cite_check import check_commits
    receipt = check_commits(["tools/README.md"])
    receipt["verdict"]  # "CLEAN" | "PHANTOM"
    receipt["phantom"]  # list of {token, file} that do not resolve

Read-only: never mutates the repo, never writes except --out receipt.
Keys never echoed; no network. Stdlib-only.
"""

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys

HEX_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
# commit-ish suffixes: 5fbf882~1, 5fbf882^2, deadbee^{}
SUFFIX_RE = re.compile(r"\b[0-9a-f]{7,40}(?:~\d+|\^\d+|\^\{\})")
# citation context on the same line: near a commit-ish word
CONTEXT_RE = re.compile(
    r"\b(commit|sha|prereg|revision|rev\b|ref\b|git|booked|reseal|anchored|"
    r"landed|in history|at HEAD)\b", re.IGNORECASE)
CONTEXT_WINDOW = 48  # chars either side


def run_git(args, cwd):
    """List-form subprocess only. Returns (rc, stdout, stderr)."""
    p = subprocess.run(["git"] + args, cwd=cwd,
                       capture_output=True, text=True, timeout=30)
    return p.returncode, p.stdout, p.stderr


def has_citation_context(line, tok):
    """Citation context = commit-suffix OR near a commit-ish word."""
    if SUFFIX_RE.search(line):
        return True
    for m in HEX_RE.finditer(line):
        if m.group(0) != tok:
            continue
        lo = max(0, m.start() - CONTEXT_WINDOW)
        hi = min(len(line), m.end() + CONTEXT_WINDOW)
        if CONTEXT_RE.search(line[lo:hi]):
            return True
    return False


def resolve_token(tok, cwd):
    """True iff tok names a commit object. rc==0 means exists."""
    rc, _, _ = run_git(["cat-file", "-e", tok + "^{commit}"], cwd)
    return rc == 0


def iter_files(paths, glob_pat):
    for p in paths:
        if os.path.isfile(p):
            yield p
        elif os.path.isdir(p):
            for root, _dirs, files in os.walk(p):
                for f in sorted(files):
                    if glob_pat is None or fnmatch.fnmatch(f, glob_pat):
                        yield os.path.join(root, f)


def scan_text(path, text, allow):
    """Return (cited_tokens, allow_hits, ignored_count) for one file's text.
    Allow hits are tokens WITH citation context that are on the allow list —
    booked by the caller, never silently swallowed."""
    cited, allow_hits = [], []
    ignored = 0
    seen = set()
    for line in text.splitlines():
        for tok in sorted(set(HEX_RE.findall(line))):
            if not has_citation_context(line, tok):
                if tok not in allow:
                    ignored += 1
                continue
            if tok in seen:
                continue
            seen.add(tok)
            (allow_hits if tok in allow else cited).append(tok)
    return cited, allow_hits, ignored


def check_commits(files, cwd=".", ref=None, allow=(), all_hex=False):
    """Main gate. Returns fail-loud rc=2, or receipt dict."""
    allow = set(allow)
    rc, out, err = run_git(["rev-parse", "--show-toplevel"], cwd)
    if rc != 0:
        return {"verdict": "FAIL-INPUT", "rc": 2,
                "why": "not a git repo / git failure: " + err.strip()[:200]}
    toplevel = out.strip()

    resolved, phantom, allowlisted = [], [], []
    ignored_total = 0
    files_scanned = 0
    for path in files:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as e:
            return {"verdict": "FAIL-INPUT", "rc": 2,
                    "why": f"unreadable {path}: {e}"}
        files_scanned += 1
        if all_hex:
            cited = sorted(set(HEX_RE.findall(text)) - allow)
            allow_hits = sorted(set(HEX_RE.findall(text)) & allow)
            ignored_total += 0
        else:
            cited, allow_hits, ig = scan_text(path, text, allow)
            ignored_total += ig
        for tok in cited:
            entry = {"token": tok, "file": path}
            if resolve_token(tok, toplevel):
                resolved.append(entry)
            else:
                phantom.append(entry)
        for tok in allow_hits:
            allowlisted.append({"token": tok, "file": path})

    verdict = "PHANTOM" if phantom else "CLEAN"
    receipt = {
        "tool": "commit_cite_check",
        "verdict": verdict,
        "rc": 1 if phantom else 0,
        "files_scanned": files_scanned,
        "cites_resolved": len(resolved),
        "cites_phantom": len(phantom),
        "allowlisted": allowlisted,
        "hex_ignored_no_context": ignored_total,
        "resolved": resolved,
        "phantom": phantom,
    }
    if phantom:
        receipt["why"] = "; ".join(
            f"{e['token']} in {e['file']}" for e in phantom[:8])
    return receipt


def _write_out(receipt, out):
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(receipt, fh, indent=2)


# ---------------------------------------------------------------- selftest

def selftest(cwd="."):
    rc, head, err = run_git(["rev-parse", "HEAD"], cwd)
    if rc != 0:
        return {"verdict": "FAIL-INPUT", "rc": 2, "why": "no git repo: " + err}
    real = head.strip()[:12]

    # craft a phantom that git genuinely does not resolve
    phantom_sha = None
    for i in range(256):
        cand = format(i, "02x") * 6 + "0000"  # 16-hex, certainly absent
        if not resolve_token(cand, cwd):
            phantom_sha = cand
            break
    assert phantom_sha, "could not craft phantom"

    checks = []

    # PIN 1: real commit cite WITH context -> RESOLVED -> CLEAN
    with tempfile_named(f"commit {real}") as f:
        r = check_commits([f], cwd=cwd)
    checks.append(("real-cite-CLEAN", r["verdict"] == "CLEAN"
                   and r["cites_resolved"] >= 1, r))

    # PIN 2: phantom commit cite -> PHANTOM rc=1, token named
    with tempfile_named(f"prereg {phantom_sha}") as f:
        r = check_commits([f], cwd=cwd)
    checks.append(("phantom-RED", r["verdict"] == "PHANTOM"
                   and r["phantom"][0]["token"] == phantom_sha
                   and r["rc"] == 1, r))

    # PIN 3: bare numeric ids WITHOUT context -> ignored -> CLEAN rc=0
    with tempfile_named("ids 01677063 26637800 41421341 and 0xdeadbeef hash") as f:
        r = check_commits([f], cwd=cwd)
    checks.append(("context-gate-noise-ignored", r["verdict"] == "CLEAN"
                   and r["hex_ignored_no_context"] >= 3, r))

    # PIN 4: allow-listed phantom WITH context -> CLEAN rc=0, booked allowlisted
    with tempfile_named(f"commit {phantom_sha}") as f:
        r = check_commits([f], cwd=cwd, allow=[phantom_sha])
    checks.append(("allowlist-booking", r["verdict"] == "CLEAN"
                   and r["allowlisted"]
                   and r["allowlisted"][0]["token"] == phantom_sha
                   and r["cites_phantom"] == 0, r))

    # PIN 4b: allow token with NO context stays ignored, not allowlisted
    with tempfile_named(phantom_sha) as f:
        r = check_commits([f], cwd=cwd, allow=[phantom_sha])
    checks.append(("allow-no-context-ignored", r["verdict"] == "CLEAN"
                   and not r["allowlisted"], r))

    # PIN 5: suffix cite 5fbf882~1 style context counts even for a real sha
    short = real[:7]
    with tempfile_named(f"git show {short}~1 -> {short}") as f:
        r = check_commits([f], cwd=cwd)
    # short~1 may not exist if HEAD~1 lacks that prefix — resolve individually
    parent_resolves = resolve_token(short + "~1", cwd)
    if parent_resolves:
        checks.append(("suffix-context-resolved", r["verdict"] == "CLEAN", r))
    else:
        checks.append(("suffix-context-phantom-named",
                       r["verdict"] == "PHANTOM"
                       and any(e["token"].startswith(short) for e in r["phantom"])
                       or r["cites_phantom"] >= 1, r))

    # PIN 6: missing file -> fail-loud rc=2
    r = check_commits(["/nonexistent/nope.md"], cwd=cwd)
    checks.append(("missing-file-rc2", r["rc"] == 2, r))

    failed = [n for n, ok, _ in checks if not ok]
    return {
        "tool": "commit_cite_check", "mode": "selftest",
        "verdict": "PASS" if not failed else "FAIL",
        "rc": 0 if not failed else 1,
        "checks": [{"name": n, "ok": ok, "detail": _small(d)}
                   for n, ok, d in checks],
        "failed": failed,
    }


def _small(d):
    return {k: d[k] for k in ("verdict", "cites_resolved", "cites_phantom",
                              "hex_ignored_no_context", "why") if k in d}


import contextlib


@contextlib.contextmanager
def tempfile_named(text):
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as fh:
        fh.write(text + "\n")
        name = fh.name
    try:
        yield name
    finally:
        os.unlink(name)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Phantom-commit-citation gate: hex SHA cites in docs/"
                    "receipts must resolve to real commits (git cat-file).")
    ap.add_argument("--file", action="append", default=[], help="file to scan")
    ap.add_argument("--files", action="append", default=[],
                    help="dir to scan (walk)")
    ap.add_argument("--glob", default=None, help="fnmatch filter for --files")
    ap.add_argument("--ref", default=None, help="informational ref label")
    ap.add_argument("--all-hex", action="store_true",
                    help="check EVERY 7-40 hex token, no citation context")
    ap.add_argument("--allow", action="append", default=[],
                    help="documented allow for a known phantom token")
    ap.add_argument("--out", default=None, help="write JSON receipt here")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        r = selftest()
        print(json.dumps(r, indent=2))
        _write_out(r, a.out)
        sys.exit(r["rc"])

    files = list(a.file)
    if a.files:
        files.extend(iter_files(a.files, a.glob))
    if not files:
        ap.error("nothing to scan: pass --file or --files")

    r = check_commits(files, allow=a.allow, all_hex=a.all_hex, ref=a.ref)
    print(json.dumps(r, indent=2))
    _write_out(r, a.out)
    sys.exit(r["rc"])


if __name__ == "__main__":
    main()
