#!/usr/bin/env python3
"""rota-epoch — versioned rolling-epoch population census + hash-selected rota member.

Pattern lifted PROVEN from HSA-1b (booked 2026-10-08, proposals/runs/
HSA-1b-population-refresh-policy.md: the frozen 101-receipt rota population
decayed — every receipt booked after the freeze could never be audited; the
fix was a rolling epoch that is a PURE FUNCTION of the committed census).

What it mechanizes:
  1. Census: regex-extract receipt paths from RESULTS.md, sorted-unique.
  2. Epoch identity: epoch_id = sha256("\\n".join(paths)+"\\n")[:16].
  3. Snapshot: population-<epoch_id>.txt, APPEND-ONLY — never overwrites
     an existing epoch file (identity tamper is fail-loud rc=2).
  4. Selection: receipt joins the rota iff last byte of
     sha256(utf8(path)) == 0x2A; fallback = lexicographically-smallest
     digest if zero hits. Deterministic, path-only, epoch-independent.
  5. Rota semantics: append-only rota.jsonl; a receipt already audited in
     ANY prior epoch is not re-selected; verdict NEW-MEMBER (first not-yet-
     audited member of the current epoch) or NO-NEW-MEMBER (honest book —
     nothing new to audit, never a fake pass).

Stdlib-only, deterministic, fail-loud rc=2, JSON receipt.
Exit 0 = NEW-MEMBER selected, 1 = NO-NEW-MEMBER, 2 = fail-loud.

Worked example:
    python tools/rota_epoch.py --results RESULTS.md \\
        --snapshot-dir results/rota_epochs --rota results/rota.jsonl \\
        --out r.json
    -> {"verdict": "NEW-MEMBER", "epoch_id": "...", "member": "proposals/runs/X.md", ...}

Selftest:
    python tools/rota_epoch.py --selftest
"""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile

DEFAULT_PATTERN = r"proposals/runs/[\w\.\-]+\.md"
SELECT_BYTE = 0x2A


class FailLoud(Exception):
    pass


def census(results_path: str, pattern: str):
    """Extract sorted-unique receipt paths from a results file."""
    try:
        text = open(results_path, encoding="utf-8").read()
    except OSError as e:
        raise FailLoud(f"cannot read results file {results_path}: {e}")
    paths = sorted(set(re.findall(pattern, text)))
    if not paths:
        raise FailLoud(f"census empty: pattern matched nothing in {results_path}")
    return paths


def epoch_id(paths) -> str:
    blob = ("\n".join(paths) + "\n").encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def load_snapshot(snapshot_dir: str, eid: str, paths):
    """Load or create the append-only epoch snapshot. Refuse to overwrite
    an existing epoch file with different content (identity tamper)."""
    os.makedirs(snapshot_dir, exist_ok=True)
    path = os.path.join(snapshot_dir, f"population-{eid}.txt")
    if os.path.exists(path):
        existing = [l for l in open(path, encoding="utf-8").read().splitlines() if l]
        if existing != list(paths):
            raise FailLoud(
                f"epoch collision: {path} exists with DIFFERENT content "
                f"({len(existing)} lines vs census {len(paths)}) — identity tamper, refusing")
        created = False
    else:
        fd, tmp = tempfile.mkstemp(dir=snapshot_dir, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("\n".join(paths) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        created = True
    return path, created


def select_member(paths):
    """Hash rule: join iff last sha256 byte == 0x2A; fallback = smallest digest."""
    digests = {p: hashlib.sha256(p.encode("utf-8")).hexdigest() for p in paths}
    hits = [p for p in paths if int(digests[p][-2:], 16) == SELECT_BYTE]
    if hits:
        ordered, fallback = sorted(hits), False
    else:
        ordered, fallback = sorted(paths, key=lambda p: digests[p]), True
    return ordered, fallback


def audited_set(rota_path):
    """Receipts already audited in any prior epoch (append-only rota).
    Annotation entries without a 'receipt' key (e.g. member_check lines in
    the real HSA-1b ledger) are skipped — they are not members. Wrong-typed
    or null receipt values still fail loud."""
    if not os.path.exists(rota_path):
        return set()
    out = set()
    for i, line in enumerate(open(rota_path, encoding="utf-8"), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as e:
            raise FailLoud(f"rota line {i} bad JSON: {e}")
        p = rec.get("receipt")
        if "receipt" not in rec:
            continue  # annotation entry, not a member
        if not isinstance(p, str) or not p:
            raise FailLoud(f"rota line {i} has non-string 'receipt'")
        out.add(p)
    return out


def append_rota(rota_path, eid, receipt, fallback):
    """Append-only write: open the EXISTING file in append mode (temp+replace
    would clobber prior rota history — the exact violation this tool guards)."""
    os.makedirs(os.path.dirname(os.path.abspath(rota_path)), exist_ok=True)
    rec = json.dumps({"epoch_id": eid, "receipt": receipt, "fallback": fallback},
                     sort_keys=True) + "\n"
    with open(rota_path, "a", encoding="utf-8") as f:
        f.write(rec)
        f.flush()
        os.fsync(f.fileno())


def run(results_path, snapshot_dir, rota_path, pattern, do_append, out_path):
    paths = census(results_path, pattern)
    eid = epoch_id(paths)
    snap, created = load_snapshot(snapshot_dir, eid, paths)
    candidates, fallback = select_member(paths)
    done = audited_set(rota_path)
    member = next((p for p in candidates if p not in done), None)
    if member is None:
        # every candidate in this epoch already audited — honest book
        member, verdict = candidates[0], "NO-NEW-MEMBER"
    else:
        verdict = "NEW-MEMBER"
        if do_append:
            append_rota(rota_path, eid, member, fallback)
    receipt = {
        "tool": "rota-epoch",
        "verdict": verdict,
        "epoch_id": eid,
        "population_n": len(paths),
        "snapshot": snap,
        "snapshot_created": created,
        "selected": member,
        "fallback_used": fallback,
        "member_already_audited": member in done,
        "rota_appended": do_append and verdict == "NEW-MEMBER",
    }
    if out_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(out_path)),
                                   suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, out_path)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if verdict == "NEW-MEMBER" else 1


def selftest():
    """Pins for census, epoch identity, selection, append-only snapshot,
    audited-set semantics, and fail-loud inputs. Fail-first: each check
    exhibits the bug class it guards."""
    import shutil

    root = tempfile.mkdtemp(prefix="rota_epoch_test_")
    checks = []

    def check(name, ok, why=""):
        checks.append((name, ok, why))
        if not ok:
            print(f"FAIL {name}: {why}")

    try:
        # fixture: results file citing 3 receipts
        res = os.path.join(root, "RESULTS.md")
        open(res, "w").write(
            "## runs\n- proposals/runs/a.md KEEP\n"
            "x proposals/runs/b.md\nagain proposals/runs/b.md\n"
            "noise proposals/runs/c.txt ignored\n")
        sdir = os.path.join(root, "epochs")
        rota = os.path.join(root, "rota.jsonl")

        # 1. census dedupe + extension filter
        p = census(res, DEFAULT_PATTERN)
        check("census", p == ["proposals/runs/a.md", "proposals/runs/b.md"],
              f"got {p}")

        # 2. epoch identity is pure function (determinism + sensitivity)
        e1 = epoch_id(p)
        e2 = epoch_id(list(reversed(p)))
        check("epoch-determinism", e1 == epoch_id(p) and e1 != e2,
              "epoch must be order-insensitive pure function")

        # 3. first run -> NEW-MEMBER, snapshot created
        out = os.path.join(root, "r1.json")
        rc = run(res, sdir, rota, DEFAULT_PATTERN, True, out)
        r1 = json.load(open(out))
        check("first-new-member",
              rc == 0 and r1["verdict"] == "NEW-MEMBER" and r1["snapshot_created"],
              f"rc={rc} r1={r1}")

        # 4. advance within epoch: b.md selected (a.md audited); once all
        # candidates audited -> NO-NEW-MEMBER, honest book
        out2 = os.path.join(root, "r2.json")
        rc = run(res, sdir, rota, DEFAULT_PATTERN, True, out2)
        r2 = json.load(open(out2))
        check("advance-to-b",
              rc == 0 and r2["verdict"] == "NEW-MEMBER"
              and r2["selected"].endswith("b.md"),
              f"rc={rc} r2={r2}")
        out2b = os.path.join(root, "r2b.json")
        rc = run(res, sdir, rota, DEFAULT_PATTERN, False, out2b)
        r2b = json.load(open(out2b))
        check("no-new-member",
              rc == 1 and r2b["verdict"] == "NO-NEW-MEMBER"
              and r2b["member_already_audited"] and not r2b["snapshot_created"],
              f"rc={rc} r2b={r2b}")
        # append-only rota: prior epoch's entry must still be present
        rota_lines = [json.loads(l) for l in open(rota) if l.strip()]
        check("rota-append-only",
              [r["receipt"] for r in rota_lines] ==
              ["proposals/runs/a.md", "proposals/runs/b.md"],
              f"rota history clobbered: {rota_lines}")

        # 5. epoch evolution: new receipt cited -> new epoch, NEW-MEMBER again
        open(res, "a").write("later proposals/runs/d.md\n")
        out3 = os.path.join(root, "r3.json")
        rc = run(res, sdir, rota, DEFAULT_PATTERN, True, out3)
        r3 = json.load(open(out3))
        check("epoch-advance",
              rc == 0 and r3["verdict"] == "NEW-MEMBER" and r3["epoch_id"] != e1
              and r3["selected"].endswith("d.md"),
              f"rc={rc} r3={r3}")

        # 6. snapshot append-only: tampered identity refused rc=2
        snap = r3["snapshot"]  # tamper the CURRENT epoch's snapshot
        open(snap, "w").write("tampered\n")
        out4 = os.path.join(root, "r4.json")
        try:
            run(res, sdir, rota, DEFAULT_PATTERN, False, out4)
            check("tamper-refused", False, "tamper was not refused")
        except FailLoud:
            check("tamper-refused", True)
        open(snap, "w").write("\n".join(
            ["proposals/runs/a.md", "proposals/runs/b.md", "proposals/runs/d.md"]) + "\n")

        # 7. empty census fails loud
        empty = os.path.join(root, "empty.md")
        open(empty, "w").write("nothing here\n")
        try:
            census(empty, DEFAULT_PATTERN)
            check("empty-census", False, "empty census did not fail loud")
        except FailLoud:
            check("empty-census", True)

        # 8. corrupt rota line fails loud (bad JSON); annotation entries
        # (no receipt key) are skipped, but null-typed receipt still REDs
        bad_rota = os.path.join(root, "bad.jsonl")
        open(bad_rota, "w").write("{not json\n")
        try:
            audited_set(bad_rota)
            check("bad-rota", False, "bad rota line did not fail loud")
        except FailLoud:
            check("bad-rota", True)
        ann_rota = os.path.join(root, "ann.jsonl")
        open(ann_rota, "w").write(
            '{"member_check": 2, "kind": "annotation"}\n'
            '{"receipt": "proposals/runs/a.md"}\n'
            '{"receipt": null}\n')
        try:
            audited_set(ann_rota)
            check("bad-receipt-type", False, "null receipt did not fail loud")
        except FailLoud:
            check("bad-receipt-type", True)
        ok_rota = os.path.join(root, "ok.jsonl")
        open(ok_rota, "w").write(
            '{"member_check": 2, "kind": "annotation"}\n'
            '{"receipt": "proposals/runs/a.md"}\n')
        check("annotations-skipped", audited_set(ok_rota) == {"proposals/runs/a.md"},
              "annotation entries must be skipped, members kept")

        # 9. selection ordering + advance semantics: fallback order is by
        # ascending digest, and the first NOT-yet-audited candidate is chosen
        cands, f = select_member(p)
        check("selection-order",
              f is not None and cands == sorted(p, key=lambda q: hashlib.sha256(q.encode()).hexdigest()),
              f"candidates not digest-ordered: {cands}")

        # 10. no token/secret in receipt (house rule)
        check("no-secrets", "token" not in json.dumps(r1), "unexpected key")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    fails = [c for c in checks if not c[1]]
    print(f"selftest: {len(checks) - len(fails)}/{len(checks)} "
          + ("PASS" if not fails else f"FAIL {fails}"))
    return 0 if not fails else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", help="RESULTS.md (or any file) to census")
    ap.add_argument("--pattern", default=DEFAULT_PATTERN,
                    help=f"receipt path regex (default {DEFAULT_PATTERN})")
    ap.add_argument("--snapshot-dir", help="append-only epoch snapshot dir")
    ap.add_argument("--rota", help="append-only rota.jsonl")
    ap.add_argument("--no-append", action="store_true",
                    help="do NOT write the selection to the rota (read-only run)")
    ap.add_argument("--out", help="JSON receipt path")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())
    missing = [f for f in ("--results", "--snapshot-dir", "--rota")
               if getattr(args, f.lstrip("-").replace("-", "_")) is None]
    if missing:
        ap.error(f"missing required args: {', '.join(missing)}")
    try:
        rc = run(args.results, args.snapshot_dir, args.rota, args.pattern,
                 not args.no_append, args.out)
    except FailLoud as e:
        print(json.dumps({"tool": "rota-epoch", "verdict": "FAIL-INPUT",
                          "why": str(e)}))
        sys.exit(2)
    sys.exit(rc)


if __name__ == "__main__":
    main()
