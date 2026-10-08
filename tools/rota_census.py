#!/usr/bin/env python3
"""rota_census.py -- rolling-epoch population census + hash selection for the HSA-1 audit rota.

HSA-1b policy (proposals/runs/HSA-1b-population-refresh-policy.md):
  population = sorted-unique proposals/runs/*.md cited in RESULTS.md
  epoch_id   = sha256(utf8(join(paths,"\n")+"\n")).hexdigest()[:16]
  selection  = paths whose sha256 last byte == 0x2A (fallback: lexicographically-smallest digest)
  snapshot   = results/hsa1_rota/population-<epoch_id>.txt  (append-only)

Read-only except for --write-snapshot, which writes ONLY the snapshot file.
Usage:
  python tools/rota_census.py --results RESULTS.md --snapshot-dir results/hsa1_rota
  python tools/rota_census.py ... --write-snapshot
"""
import argparse
import hashlib
import os
import re
import sys

RX = re.compile(r"proposals/runs/[A-Za-z0-9._-]+\.md")
PREFIX_BYTE = 0x2A


def census(results_path):
    text = open(results_path, encoding="utf-8").read()
    return sorted(set(RX.findall(text)))


def epoch_id(paths):
    blob = "\n".join(paths) + "\n"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def select(paths):
    sel = [p for p in paths if hashlib.sha256(p.encode("utf-8")).digest()[-1] == PREFIX_BYTE]
    if sel:
        return sel, "prefix"
    if not paths:
        return [], "empty"
    smallest = min(paths, key=lambda p: hashlib.sha256(p.encode("utf-8")).hexdigest())
    return [smallest], "fallback"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="RESULTS.md")
    ap.add_argument("--snapshot-dir", default="results/hsa1_rota")
    ap.add_argument("--write-snapshot", action="store_true")
    args = ap.parse_args()

    paths = census(args.results)
    ep = epoch_id(paths)
    sel, how = select(paths)

    print(f"census_n={len(paths)}")
    print(f"epoch_id={ep}")
    print(f"selection_mode={how}")
    print("selection=" + ("[" + ", ".join(sel) + "]" if sel else "[]"))

    snap = os.path.join(args.snapshot_dir, f"population-{ep}.txt")
    if args.write_snapshot:
        os.makedirs(args.snapshot_dir, exist_ok=True)
        with open(snap, "w", encoding="utf-8") as f:
            f.write("\n".join(paths) + "\n")
        print(f"wrote={snap}")
    else:
        if os.path.exists(snap):
            committed = [l.strip() for l in open(snap, encoding="utf-8") if l.strip()]
            ok = committed == paths
            print(f"snapshot_exists={snap} matches_census={ok}")
            if not ok:
                print("G1 FAIL: committed snapshot != live census", file=sys.stderr)
                return 1
        else:
            print(f"snapshot_missing={snap}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
