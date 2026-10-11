#!/usr/bin/env python3
"""trace-id — deterministic-replay trace identity witness.

Pattern lifted PROVEN from SCOUT-103/q35 (rc-20260824-11, booked 2026-10-11):
the BREADTH-b arm's draft-1 claimed it RAISED something vs FIXED(1.0), but the
trace cross-check showed BREADTH-1 was TRACE-IDENTICAL to FIXED(1.0) — a false
positive caught only by comparing the event streams, not the summary numbers.
"A raise happened" is a measurement over the trace, not a claim.

What it does: read two event traces (JSONL; each line a JSON object, or fall
back to raw-line text), normalize each event (JSON canonical form, key-order
insensitive; optional --ignore dotted fields like ts/wall for wall-clock
noise), and compare the sequences:

    IDENTICAL  — every normalized event byte-equal in order
    DIVERGED   — first divergent index named, both events shown (truncated)
    (edge)     — length mismatch after common prefix = DIVERGED with the
                 extra tail named; empty-vs-empty = IDENTICAL honestly

Stdlib-only, no network, read-only, fail-loud rc=2 on unreadable/malformed
beyond-repair input. Exit 0 = IDENTICAL, 1 = DIVERGED, 2 = fail-loud.

Usage:
    python tools/trace_id.py --a runA.jsonl --b runB.jsonl [--ignore ts,wall --out r.json]
    python tools/trace_id.py --selftest

Worked example (docstring form):
    $ printf '{"e":"tick","i":1,"ts":100}\\n{"e":"tick","i":2,"ts":101}\\n' > a.jsonl
    $ printf '{"ts":900,"i":1,"e":"tick"}\\n{"e":"tick","i":2,"ts":901}\\n' > b.jsonl
    $ python tools/trace_id.py --a a.jsonl --b b.jsonl --ignore ts
    -> IDENTICAL rc=0 (key-order and ts-insensitive)
    $ printf '{"e":"tick","i":1,"ts":100}\\n{"e":"tick","i":3,"ts":101}\\n' > c.jsonl
    $ python tools/trace_id.py --a a.jsonl --c c.jsonl
    -> DIVERGED rc=1 at event 1 ("i": 2 vs "i": 3)
"""

import argparse
import json
import sys
import hashlib
import time
import tempfile
import os

IGNORE_DEFAULT = ""  # no ignored fields by default


def fail(msg, rc=2):
    print(f"FAIL-INPUT: {msg}", file=sys.stderr)
    sys.exit(rc)


def load_events(path):
    """Read a trace file -> list of normalized event strings (canonical JSON
    per line when parseable, else the stripped raw line)."""
    try:
        with open(path, "r", encoding="utf-8", errors="strict") as f:
            lines = f.read().splitlines()
    except OSError as e:
        fail(f"cannot read {path}: {e}")
    events = []
    for n, line in enumerate(lines, 1):
        s = line.strip()
        if not s:
            continue  # blank lines are not events
        try:
            obj = json.loads(s)
        except (json.JSONDecodeError, ValueError):
            events.append(s)  # raw-text event, verbatim
            continue
        if isinstance(obj, dict):
            events.append(json.dumps(obj, sort_keys=True, separators=(",", ":")))
        else:
            events.append(json.dumps(obj, separators=(",", ":")))
    return events


def drop_ignored(events, ignore_fields):
    """Remove --ignore dotted fields from dict-events (top-level keys here;
    a dotted 'a.b' drills one dict level). Non-matching shapes left intact."""
    if not ignore_fields:
        return events
    out = []
    for ev in events:
        try:
            obj = json.loads(ev)
        except (json.JSONDecodeError, ValueError):
            out.append(ev)
            continue
        if isinstance(obj, dict):
            for f in ignore_fields:
                parts = f.split(".")
                cur = obj
                ok = True
                for p in parts[:-1]:
                    if isinstance(cur, dict) and p in cur:
                        cur = cur[p]
                    else:
                        ok = False
                        break
                if ok and isinstance(cur, dict) and parts[-1] in cur:
                    del cur[parts[-1]]
            out.append(json.dumps(obj, sort_keys=True, separators=(",", ":")))
        else:
            out.append(ev)
    return out


def compare(a_events, b_events):
    """-> (verdict, detail dict). Verdict in {IDENTICAL, DIVERGED}."""
    la, lb = len(a_events), len(b_events)
    for i in range(min(la, lb)):
        if a_events[i] != b_events[i]:
            return "DIVERGED", {
                "first_divergence": i,
                "a_event": a_events[i][:200],
                "b_event": b_events[i][:200],
                "len_a": la,
                "len_b": lb,
                "why": "event content differs at first divergent index",
            }
    if la != lb:
        longer, name = (a_events, "a") if la > lb else (b_events, "b")
        return "DIVERGED", {
            "first_divergence": min(la, lb),
            "len_a": la,
            "len_b": lb,
            "extra_tail": [e[:200] for e in longer[min(la, lb): min(la, lb) + 5]],
            "why": f"trace {name} has extra events after common prefix",
        }
    return "IDENTICAL", {"len": la}


def run_compare(path_a, path_b, ignore_fields):
    a = drop_ignored(load_events(path_a), ignore_fields)
    b = drop_ignored(load_events(path_b), ignore_fields)
    verdict, detail = compare(a, b)
    receipt = {
        "tool": "trace-id",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "a": path_a,
        "b": path_b,
        "ignored": sorted(ignore_fields),
        "sha_a": hashlib.sha256("\n".join(a).encode()).hexdigest()[:16],
        "sha_b": hashlib.sha256("\n".join(b).encode()).hexdigest()[:16],
        "verdict": verdict,
        **detail,
    }
    return receipt


def selftest():
    """Positive + RED battery. Returns list of (name, ok) — raises on failure."""
    results = []
    d = tempfile.mkdtemp(prefix="traceid_selftest_")

    def w(name, text):
        p = os.path.join(d, name)
        with open(p, "w") as f:
            f.write(text)
        return p

    a = w("a.jsonl", '{"e":"tick","i":1,"ts":100}\n{"e":"tick","i":2,"ts":101}\n')
    # P1: key-order + ignore-field insensitive -> IDENTICAL
    b = w("b.jsonl", '{"ts":900,"i":1,"e":"tick"}\n{"e":"tick","i":2,"ts":901}\n')
    r = run_compare(a, b, {"ts"})
    results.append(("reorder+ignore IDENTICAL", r["verdict"] == "IDENTICAL"))
    # P2 (RED control): same files WITHOUT ignore -> DIVERGED (ts differs)
    r = run_compare(a, b, set())
    results.append(("without-ignore RED", r["verdict"] == "DIVERGED"))
    # P3: content divergence named at the right index
    c = w("c.jsonl", '{"e":"tick","i":1,"ts":100}\n{"e":"tick","i":3,"ts":101}\n')
    r = run_compare(a, c, {"ts"})
    ok = r["verdict"] == "DIVERGED" and r["first_divergence"] == 1 and '"i":3' in r["b_event"]
    results.append(("divergence named", ok))
    # P4: length mismatch (truncated tail) -> DIVERGED with extra tail
    e = w("e.jsonl", '{"e":"tick","i":1,"ts":100}\n')
    r = run_compare(a, e, {"ts"})
    ok = r["verdict"] == "DIVERGED" and "extra_tail" in r and r["first_divergence"] == 1
    results.append(("tail DIVERGED", ok))
    # P5: empty-vs-empty = IDENTICAL honestly
    f1, f2 = w("f1.jsonl", "\n\n"), w("f2.jsonl", "")
    r = run_compare(f1, f2, set())
    results.append(("empty IDENTICAL", r["verdict"] == "IDENTICAL"))
    # P6: raw non-JSON lines compared verbatim
    g = w("g.log", "alpha start\nbeta end\n")
    h = w("h.log", "alpha start\ngamma end\n")
    r = run_compare(g, h, set())
    ok = r["verdict"] == "DIVERGED" and r["first_divergence"] == 1
    results.append(("raw-line compare", ok))
    # P7: missing file fails loud rc=2
    try:
        run_compare(os.path.join(d, "nope.jsonl"), a, set())
        results.append(("missing file fail-loud", False))
    except SystemExit as ex:
        results.append(("missing file fail-loud", ex.code == 2))

    failed = [n for n, ok in results if not ok]
    print(json.dumps({
        "tool": "trace-id", "selftest": "PASS" if not failed else "FAIL",
        "checks": f"{len(results)-len(failed)}/{len(results)}", "failed": failed,
    }))
    if failed:
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description="deterministic-replay trace identity witness")
    ap.add_argument("--a", help="trace A (JSONL)")
    ap.add_argument("--b", help="trace B (JSONL)")
    ap.add_argument("--ignore", default=IGNORE_DEFAULT,
                    help="comma-separated dotted fields to strip before compare (e.g. ts,wall)")
    ap.add_argument("--out", help="write JSON receipt here")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return
    if not args.a or not args.b:
        fail("need --a and --b (or --selftest)")

    ignore = {s.strip() for s in args.ignore.split(",") if s.strip()} if args.ignore else set()
    receipt = run_compare(args.a, args.b, ignore)
    line = json.dumps(receipt)
    if args.out:
        tmp = args.out + ".tmp"
        with open(tmp, "w") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, args.out)
    if receipt["verdict"] == "IDENTICAL":
        print(f"VERDICT: IDENTICAL ({receipt['len']} events, sha {receipt['sha_a']})")
        sys.exit(0)
    else:
        print(f"VERDICT: DIVERGED at event {receipt['first_divergence']} — {receipt['why']}")
        print(f"  a: {receipt.get('a_event', '')}")
        print(f"  b: {receipt.get('b_event', '')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
