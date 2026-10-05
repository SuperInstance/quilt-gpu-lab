#!/usr/bin/env python3
"""EP-1d seal/event-prose census, pointer arm v4 (pre-reg: proposals/runs/EP-1d-pointer-arm-v4-prereg.md).

Identical to EP-1b (tools/ep1b_seal_census.py) except WARN_POINTER is machine-checkable:
path-hit (existing/tracked repo-relative path on the citing line), receipt-hit (sha in a
COMMITTED receipt), or remote-hit (remote + sha pair on the citing line). No other deltas.
Read-only by default; --out refuses overwrite without --force. Fail-loud; no retries; no network.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCOPE_FILES = [REPO / "RESULTS.md"] + sorted((REPO / "receipts").glob("*.md"))
MANIFEST = REPO / "receipts" / "manifest.json"
ARM_DIRS = ["results", "tools", "experiments", "receipts"]
ARM_SKIP = {"__pycache__"}
SIZE_CAP = 64 * 1024 * 1024
HIST_COMMIT_CAP = 200

HEX64 = re.compile(r"\b[0-9a-f]{64}\b")
SEAL_CLAIM = re.compile(r"(seal(?:ed)?|commit(?:ted)?)\s+[0-9a-f]{7,40}", re.IGNORECASE)
SHA_ANY = re.compile(r"[0-9a-f]{7,40}")
PATH_RE = re.compile(r"((?:results|receipts|tools|experiments)/[A-Za-z0-9_./-]+)")
REMOTE_RE = re.compile(r"github\.com|SuperInstance/|workers\.dev|\.git\b|remote", re.IGNORECASE)
FOREIGN_RE = re.compile(r"SuperInstance/[A-Za-z0-9_.-]+", re.IGNORECASE)
SELFSCAN_RE = re.compile(r"EP-1|census|REPRO", re.IGNORECASE)


def fail_loud(msg):
    print(f"FAIL-LOUD: {msg}")
    sys.exit(2)


def git(args, timeout=30):
    r = subprocess.run(["git"] + args, cwd=REPO, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        return None
    return r.stdout


def git_object_exists(sha):
    out = git(["cat-file", "-t", sha], timeout=10)
    return out is not None and out.strip() in ("commit", "blob", "tree", "tag")


def arm_files():
    files = []
    for d in ARM_DIRS:
        base = REPO / d
        if not base.is_dir():
            continue
        for f in base.rglob("*"):
            if f.is_file() and not (ARM_SKIP & set(f.parts)):
                if f.stat().st_size <= SIZE_CAP:
                    files.append(f)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--sites", default=None,
                    help="dry-run: comma list of tok[:sha-prefix] to classify in isolation")
    a = ap.parse_args()
    if a.out:
        outp = Path(a.out)
        if outp.exists() and not a.force:
            print(f"FAIL-LOUD: --out {outp} exists; pass --force to overwrite")
            sys.exit(2)

    for p in SCOPE_FILES + [MANIFEST]:
        if not p.is_file():
            fail_loud(f"missing scope input: {p}")

    manifest_text = MANIFEST.read_text()
    # COMMITTED receipts only (working-tree untracked receipts do not count)
    tracked = git(["ls-files", "receipts"]) or ""
    tracked_receipt_names = {Path(x).name for x in tracked.splitlines() if x.startswith("receipts/")}
    receipt_texts = {
        r.name: r.read_text(errors="replace")
        for r in sorted((REPO / "receipts").glob("*.md"))
        if r.name in tracked_receipt_names
    }
    print(f"committed receipts scanned: {len(receipt_texts)}")

    # EP-1d delta: committed .md corpus for cross-reference arm
    tracked_md = [x for x in (git(["ls-files", "*.md"]) or "").splitlines() if x]
    corpus_texts = []
    for rel in tracked_md:
        p = REPO / rel
        if p.is_file():
            corpus_texts.append((rel, p.read_text(errors="replace")))
    print(f"committed .md corpus for xref: {len(corpus_texts)} files")

    # EP-1d G-DRY: dry-run over named sha prefixes, classified against real citing lines
    if a.sites:
        rc = (REPO / "RESULTS.md").read_text(errors="replace").splitlines()
        ok = True
        for prefix in a.sites.split(","):
            hits = 0
            for i, line in enumerate(rc, 1):
                if prefix in line:
                    hits += 1
                    cls = classify("RESULTS.md", i, next(s for s in SHA_ANY.findall(line) if s.startswith(prefix)) if SHA_ANY.search(line) else prefix, line)
                    print(f"DRY {prefix} @RESULTS.md:{i} -> {cls}")
                    if cls == "RED":
                        ok = False
            if hits == 0:
                print(f"DRY {prefix} -> NO SITE FOUND")
                ok = False
        print(f"DRY-VERDICT: {'PASS' if ok else 'FAIL'}")
        return

    # G1 census
    digest_claims, seal_claims = [], []
    for path in SCOPE_FILES:
        for i, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            for m in HEX64.finditer(line):
                digest_claims.append((path.name, i, m.group(0), line))
            if SEAL_CLAIM.search(line):
                shas = SHA_ANY.findall(SEAL_CLAIM.search(line).group(0))
                seal_claims.append((path.name, i, line.strip()[:140], shas))
    print(f"G1 census: {len(digest_claims)} digest claims, {len(seal_claims)} seal/event-prose lines")

    arm_files_list = arm_files()
    arm_capped = sum(1 for d in ARM_DIRS if (REPO / d).is_dir()
                     for f in (REPO / d).rglob("*") if f.is_file()
                     and f.stat().st_size > SIZE_CAP)
    arm_hashes = {hashlib.sha256(f.read_bytes()).hexdigest() for f in arm_files_list}
    print(f"  artifact arm: {len(arm_files_list)} files hashed (skipped {arm_capped} over {SIZE_CAP//1024//1024} MiB)")

    hist_cache = {}
    def hist_blobs(relpath):
        if relpath in hist_cache:
            return hist_cache[relpath]
        shas_out = set()
        if (REPO / relpath).is_file():
            out = git(["log", "--all", "--format=%H", "--", relpath])
            if out:
                for c in out.split()[:HIST_COMMIT_CAP]:
                    b = git(["show", f"{c}:{relpath}"], timeout=20)
                    if b is not None:
                        shas_out.add(hashlib.sha256(b.encode()).hexdigest())
        hist_cache[relpath] = shas_out
        return shas_out

    path_cache = {}
    def path_hit(line):
        for mp in PATH_RE.finditer(line):
            p = mp.group(1).rstrip(".,;:)")
            if p not in path_cache:
                path_cache[p] = (REPO / p).exists() or git(["ls-files", "--error-unmatch", p], timeout=10) is not None
            if path_cache[p]:
                return True
        return False

    def classify(name, lineno, tok, line):
        if tok in manifest_text or git_object_exists(tok) or tok in arm_hashes:
            return "resolved"
        for mp in re.finditer(r"((?:results|tools|experiments|receipts)/[A-Za-z0-9_./-]+)", line):
            if tok in hist_blobs(mp.group(1)):
                return "resolved-historical"
        receipt_hit = any(tok in t for t in receipt_texts.values())
        if FOREIGN_RE.search(line) or (receipt_hit and any(
                FOREIGN_RE.search(t[:t.find(tok) + 400]) for t in receipt_texts.values() if tok in t)):
            return "WARN_FOREIGN"
        # EP-1c arm: path/remote pointer (kept for lineage)
        pointer_v3 = receipt_hit or path_hit(line) or REMOTE_RE.search(line)
        # EP-1d delta: corpus cross-reference — tok in >=1 OTHER committed .md, excluding the citing line
        corpus_xref = False
        for rel, text in corpus_texts:
            if name == "RESULTS.md" and rel == "RESULTS.md":
                without_line = text.replace(line, "", 1)
                if tok in without_line:
                    corpus_xref = True
                    break
            elif tok in text:
                    corpus_xref = True
                    break
        if pointer_v3 or corpus_xref:
            return "WARN_POINTER"
        if SELFSCAN_RE.search(line):
            return "WARN_SELFSCAN"
        return "RED"

    counts = {"RED": [], "WARN_POINTER": [], "WARN_FOREIGN": [], "WARN_SELFSCAN": []}
    g2_resolved = 0
    for name, lineno, tok, line in digest_claims:
        c = classify(name, lineno, tok, line)
        if c.startswith("resolved"):
            g2_resolved += 1
        elif c == "RED":
            counts["RED"].append(f"G2 RED {name}:{lineno} unresolvable 64-hex {tok[:12]}…")
        else:
            counts[c].append(f"G2 {c} {name}:{lineno} {tok[:12]}…")

    g3_resolved, g3_n = 0, 0
    for name, lineno, claim, shas in seal_claims:
        for sha in shas:
            if len(sha) < 7:
                continue
            g3_n += 1
            c = classify(name, lineno, sha, claim)
            if c.startswith("resolved"):
                g3_resolved += 1
            elif c == "RED":
                counts["RED"].append(f"G3 RED {name}:{lineno} seal-prose sha {sha} :: {claim}")
            else:
                counts[c].append(f"G3 {c} {name}:{lineno} {sha[:12]}…")

    reds = counts["RED"]
    verdict = "GREEN" if not reds else "RED"
    print(f"G2: {g2_resolved}/{len(digest_claims)} digest claims resolved")
    print(f"G3: {g3_resolved}/{g3_n} seal-prose sha claims resolved")
    for cls in ("WARN_POINTER", "WARN_FOREIGN", "WARN_SELFSCAN"):
        print(f"  {cls}: {len(counts[cls])}")
        for item in counts[cls][:20]:
            print(f"    {item}")
    if len(counts["WARN_POINTER"]) > 20 or len(counts["WARN_FOREIGN"]) > 20 or len(counts["WARN_SELFSCAN"]) > 20:
        print("    … (truncated; full lists in artifact)")
    for r in reds:
        print(r)
    print(f"VERDICT: {verdict}")

    if a.out:
        outp.write_text(json.dumps({
            "pre_reg": "proposals/runs/EP-1d-pointer-arm-v4-prereg.md",
            "committed_receipts_scanned": len(receipt_texts),
            "digest_claims_total": len(digest_claims),
            "seal_prose_shas_total": g3_n,
            "g2_resolved": g2_resolved, "g3_resolved": g3_resolved,
            "warn_pointer": len(counts["WARN_POINTER"]),
            "warn_foreign": len(counts["WARN_FOREIGN"]),
            "warn_selfscan": len(counts["WARN_SELFSCAN"]),
            "reds": reds, "verdict": verdict,
            "declared_deviations": ["foreign ls-remote network arm deferred to RT-D1 real-probe arm (inherited from EP-1b)"],
        }, indent=2) + "\n")
        print(f"artifact: {outp}")


if __name__ == "__main__":
    main()
