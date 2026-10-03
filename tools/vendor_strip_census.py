#!/usr/bin/env python3
"""VSB-1: vendor-stripped blob-bytes census (pre-reg proposals/runs/VSB-1-vendor-strip-census.md).

Port of quilt-research-canons SCOUT-2026-09-30T1955Z method: rank repo files by
git tree blob bytes, with vendored trees reported separately. The GitHub `size`
field is broken fleet-wide; git tree bytes are the verified replacement.

Usage: vendor_strip_census.py [--repo PATH] [--out results/vsb1/vendor_strip_census.json]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

VENDOR_DIRS = ("node_modules/", "target/", "vendor/", "dist/", "build/", ".next/",
               "out/", "_build/", "__pycache__/", ".wrangler/", "coverage/")


def git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL-LOUD: git {' '.join(args)} -> {r.returncode}: {r.stderr.strip()}")
        sys.exit(2)
    return r.stdout


def census_ls_tree(repo: Path) -> dict:
    out = {}
    for line in git(repo, "ls-tree", "-r", "-l", "HEAD").splitlines():
        meta, path = line.split("\t", 1)
        parts = meta.split()
        # <mode> <type> <sha> <size>\t<path>  (size is '-' for non-blobs)
        if parts[1] != "blob":
            continue
        size = int(parts[3]) if parts[3] != "-" else 0
        out[path] = size
    if not out:
        print("FAIL-LOUD (G3): empty tree at HEAD")
        sys.exit(2)
    return out


def census_cat_file(repo: Path) -> dict:
    names = git(repo, "ls-tree", "-r", "--name-only", "HEAD").splitlines()
    inp = "\n".join("HEAD:" + n for n in names) + "\n"
    r = subprocess.run(["git", "-C", str(repo), "cat-file", "--batch-check"],
                       input=inp, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL-LOUD: cat-file batch-check: {r.stderr.strip()}")
        sys.exit(2)
    lines = r.stdout.splitlines()
    if len(lines) != len(names):
        print(f"FAIL-LOUD (G1): batch-check returned {len(lines)} lines for {len(names)} paths")
        sys.exit(2)
    # batch-check echoes the RESOLVED oid (not the input ref); output order
    # matches input order, so map positionally.
    out = {}
    for name, line in zip(names, lines):
        parts = line.rsplit(" ", 2)
        if len(parts) != 3:
            print(f"FAIL-LOUD (G1): unparseable batch-check line for {name!r}: {line!r}")
            sys.exit(2)
        _oid, otype, size = parts
        if otype != "blob":
            continue
        out[name] = int(size)
    if not out:
        print("FAIL-LOUD (G3): no blobs via cat-file (empty tree at HEAD)")
        sys.exit(2)
    return out


def is_vendor(path: str) -> bool:
    # vendor dirs exclude at ANY tree depth (canons fleet method), not just root:
    # experiments/wg1_wgsl/target/... is vendored build output too.
    p = "/" + path
    return any("/" + v in p for v in VENDOR_DIRS)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--out", default="results/vsb1/vendor_strip_census.json")
    ap.add_argument("--top", type=int, default=20)
    a = ap.parse_args()
    repo = Path(a.repo).resolve()

    ls = census_ls_tree(repo)
    cf = census_cat_file(repo)

    # G1: two-method agreement (exact)
    only_ls = set(ls) - set(cf)
    only_cf = set(cf) - set(ls)
    mism = [p for p in set(ls) & set(cf) if ls[p] != cf[p]]
    g1 = not only_ls and not only_cf and not mism
    print(f"G1 two-method agreement: {'PASS' if g1 else 'FAIL'} "
          f"(files={len(ls)}, only_ls={len(only_ls)}, only_cf={len(only_cf)}, mismatches={len(mism)})")
    if not g1:
        for p in (list(only_ls)[:5] + list(only_cf)[:5] + mism[:5]):
            print(f"  delta: {p} ls={ls.get(p)} cf={cf.get(p)}")
        return 2

    raw_total = sum(ls.values())
    vend = {p: s for p, s in ls.items() if is_vendor(p)}
    real = {p: s for p, s in ls.items() if not is_vendor(p)}
    vend_total, real_total = sum(vend.values()), sum(real.values())

    ranking = sorted(real.items(), key=lambda kv: -kv[1])[:a.top]
    print(f"raw bytes      : {raw_total:>12,}  ({len(ls)} files)")
    print(f"vendored bytes : {vend_total:>12,}  ({len(vend)} files, "
          f"{100*vend_total/raw_total:.1f}%)")
    print(f"real bytes     : {real_total:>12,}  ({len(real)} files)")
    print("top real files:")
    for p, s in ranking:
        print(f"  {s:>10,}  {p}")

    out_path = (repo / a.out) if not Path(a.out).is_absolute() else Path(a.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "tool": "tools/vendor_strip_census.py",
        "pre_reg": "proposals/runs/VSB-1-vendor-strip-census.md",
        "head": git(repo, "rev-parse", "HEAD").strip(),
        "g1_two_method_agreement": g1,
        "raw_total_bytes": raw_total, "raw_files": len(ls),
        "vendored_bytes": vend_total, "vendored_files": len(vend),
        "vendored_share": round(vend_total / raw_total, 6),
        "real_bytes": real_total, "real_files": len(real),
        "top_real": [{"path": p, "bytes": s} for p, s in ranking],
        "vendor_dirs": list(VENDOR_DIRS),
    }, indent=2) + "\n")
    print(f"booked -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
