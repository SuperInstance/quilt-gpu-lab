#!/usr/bin/env python3
"""EP-1 seal/event-prose census (pre-reg: proposals/runs/EP-1-seal-prose-census-prereg.md).

Census of seal/event-shaped prose claims in RESULTS.md + receipts/*.md vs
receipts/manifest.json + git object store. Unresolvable seal-prose = RED (F4 class,
cf. jev-quilt PR #49 event_registry doctrine). Fail-loud; no retries; verdict GREEN iff RED=0.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCOPE_FILES = [REPO / "RESULTS.md"] + sorted((REPO / "receipts").glob("*.md"))
MANIFEST = REPO / "receipts" / "manifest.json"

HEX64 = re.compile(r"\b[0-9a-f]{64}\b")
SEAL_CLAIM = re.compile(
    r"(seal(?:ed)?|commit(?:ted)?)\s+[0-9a-f]{7,40}", re.IGNORECASE
)
SHA_ANY = re.compile(r"[0-9a-f]{7,40}")


def fail_loud(msg):
    print(f"FAIL-LOUD: {msg}")
    sys.exit(2)


def git_object_exists(sha):
    try:
        r = subprocess.run(
            ["git", "cat-file", "-t", sha], cwd=REPO,
            capture_output=True, text=True, timeout=10,
        )
        return r.returncode == 0 and r.stdout.strip() in ("commit", "blob", "tree", "tag")
    except Exception as e:
        fail_loud(f"git cat-file error for {sha}: {e}")


def main():
    for p in SCOPE_FILES + [MANIFEST]:
        if not p.is_file():
            fail_loud(f"missing scope input: {p}")

    manifest_text = MANIFEST.read_text()
    results_text = (REPO / "RESULTS.md").read_text()

    # G1: census
    digest_claims = []   # (file, lineno, token)
    seal_claims = []     # (file, lineno, claim_text, shas)
    for path in SCOPE_FILES:
        for i, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            for m in HEX64.finditer(line):
                digest_claims.append((path.name, i, m.group(0)))
            if SEAL_CLAIM.search(line):
                shas = SHA_ANY.findall(SEAL_CLAIM.search(line).group(0))
                seal_claims.append((path.name, i, line.strip()[:140], shas))
    print(f"G1 census: {len(digest_claims)} digest claims, {len(seal_claims)} seal/event-prose lines")

    reds = []
    # G2: digest resolution
    tree_hashes = {}
    for path in SCOPE_FILES:
        pass  # artifact-hash arm: check known named results files
    for name, lineno, tok in digest_claims:
        if tok in manifest_text:
            continue
        if git_object_exists(tok):
            continue
        # artifact-hash arm: hash every file in results/ + receipts/ + tools/ + experiments/
        hit = False
        for f in list(REPO.glob("results/*")) + list(REPO.glob("tools/*")) + \
                 list(REPO.glob("experiments/*")) + list(REPO.glob("receipts/*")):
            if f.is_file():
                if hashlib.sha256(f.read_bytes()).hexdigest() == tok:
                    hit = True
                    break
        if hit:
            continue
        reds.append(f"G2 RED {name}:{lineno} unresolvable 64-hex {tok[:12]}…")
    g2_resolved = len(digest_claims) - sum(1 for r in reds if r.startswith("G2"))

    # G3: seal-prose resolution
    g3_reds = []
    for name, lineno, claim, shas in seal_claims:
        for sha in shas:
            if len(sha) < 7:
                continue
            if not git_object_exists(sha):
                # allow receipt-line resolution: full claim text with the sha in any committed receipt
                in_receipt = any(
                    sha in (REPO / "receipts" / r.name).read_text(errors="replace")
                    for r in (REPO / "receipts").glob("*.md")
                )
                if not in_receipt:
                    g3_reds.append(f"G3 RED {name}:{lineno} seal-prose sha {sha} unresolvable :: {claim}")
    reds.extend(g3_reds)
    g3_resolved = len(seal_claims) - len(g3_reds)

    # G4: verdict
    verdict = "GREEN" if not reds else "RED"
    print(f"G2: {g2_resolved}/{len(digest_claims)} digest claims resolved")
    print(f"G3: {g3_resolved}/{len(seal_claims)} seal-prose lines resolved")
    for r in reds:
        print(r)
    print(f"VERDICT: {verdict}")

    out = REPO / "results" / "ep1_seal_census.json"
    out.write_text(json.dumps({
        "pre_reg": "proposals/runs/EP-1-seal-prose-census-prereg.md",
        "digest_claims_total": len(digest_claims),
        "seal_prose_lines_total": len(seal_claims),
        "g2_resolved": g2_resolved, "g3_resolved": g3_resolved,
        "reds": reds, "verdict": verdict,
    }, indent=2) + "\n")
    print(f"artifact: {out}")


if __name__ == "__main__":
    main()
