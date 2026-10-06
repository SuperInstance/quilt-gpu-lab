#!/usr/bin/env python3
"""contam-gate — train/heldout pool contamination gate.

Pattern lifted PROVEN from DET-1/DET-1b (booked aborted-partial 2026-10-05:
4/6 arms died on pool/heldout expr collision — contamination was DISCOVERED
at run time, after the pre-reg, instead of being gated before fire; remedy
DET-1c added exclusion-by-construction in experiments/rest_em_loop.py).
This tool mechanizes the gate: given two JSON pools of records (train,
heldout) and an identity rule, verify the pools are disjoint.

Identity rules:
  --key dotted.field   identity = the value at that key path in each record
                       (missing key = fail-loud, silently-missing keys are
                       how contamination hides)
  (default, no --key)  identity = sha256 of the record's canonical JSON
                       (sort_keys, compact separators) — whole-record exactness

Never mutates the pools. Read-only, stdlib-only, deterministic.
Exit codes: 0 = CLEAN (0 overlapping identities), 1 = CONTAMINATED (rc=1,
overlaps listed, capped at --max-show), 2 = FAIL-INPUT (bad JSON, empty
pool, missing key, unreadable file). A JSON receipt is written either way
when --out is given; fail-loud exits write a receipt too when possible.

Library: identities(records, key) -> list of identity strings
         overlap(train_recs, held_recs, key) -> (set, n_train, n_held)

Worked example:
    python tools/contam_gate.py --train train.json --heldout heldout.json \
        --key expr --out receipt.json
    echo "[{\"expr\":\"1+1\"}]" > /tmp/t.json
    echo "[{\"expr\":\"2+2\"}]" > /tmp/h.json
    python tools/contam_gate.py --train /tmp/t.json --heldout /tmp/h.json --key expr
    -> CLEAN rc=0

    python tools/contam_gate.py --selftest
"""
import argparse
import hashlib
import json
import sys

MAX_SHOW_DEFAULT = 10


def fail_loud(msg, receipt=None):
    print(f"FAIL-LOUD: {msg}")
    if receipt:
        try:
            receipt["verdict"] = "FAIL-INPUT"
            receipt["why"] = msg
            with open(receipt["_out"], "w") as f:
                json.dump({k: v for k, v in receipt.items() if not k.startswith("_")}, f, indent=2)
        except Exception:
            pass
    sys.exit(2)


def _identity(rec, key):
    if key:
        cur = rec
        for part in key.split("."):
            if not isinstance(cur, dict) or part not in cur:
                raise KeyError(f"key path {key!r} missing at {part!r} in record: {str(rec)[:120]}")
            cur = cur[part]
        return json.dumps(cur, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(
        json.dumps(rec, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def identities(records, key=None):
    """Identity string for each record; KeyError propagates fail-loud."""
    return [_identity(r, key) for r in records]


def overlap(train_recs, held_recs, key=None):
    """(overlapping identity set, n_train, n_held). KeyError on missing key."""
    tr = identities(train_recs, key)
    hr = identities(held_recs, key)
    return set(tr) & set(hr), len(tr), len(hr)


def load_pool(path, label, out=None):
    try:
        with open(path) as f:
            data = json.load(f)
    except OSError as e:
        fail_loud(f"{label} unreadable: {e}", out)
    except json.JSONDecodeError as e:
        fail_loud(f"{label} not valid JSON: {e}", out)
    if not isinstance(data, list) or not data:
        fail_loud(f"{label} must be a non-empty JSON list of records", out)
    if not all(isinstance(r, (dict, list, str, int, float, bool)) for r in data):
        fail_loud(f"{label} contains a non-JSON record type", out)
    return data


def run_gate(train_path, held_path, key=None, out_path=None, max_show=MAX_SHOW_DEFAULT):
    out = {"_out": out_path, "tool": "contam-gate"} if out_path else None
    train = load_pool(train_path, "train", out)
    held = load_pool(held_path, "heldout", out)
    try:
        ov, n_tr, n_hd = overlap(train, held, key)
    except KeyError as e:
        fail_loud(str(e), out)
    receipt = {
        "tool": "contam-gate",
        "train": {"path": train_path, "n": n_tr},
        "heldout": {"path": held_path, "n": n_hd},
        "identity_rule": key if key else "sha256(canonical-json)",
        "overlap_n": len(ov),
        "overlap_samples": sorted(ov)[:max_show],
        "verdict": "CLEAN" if not ov else "CONTAMINATED",
    }
    if out_path:
        with open(out_path, "w") as f:
            json.dump(receipt, f, indent=2)
    print(json.dumps({k: v for k, v in receipt.items()}, indent=2))
    if ov:
        print(f"CONTAMINATED: {len(ov)} overlapping identities "
              f"(showing <= {max_show}) — gate rc=1")
        return 1
    print(f"CLEAN: {n_tr} train / {n_hd} heldout, 0 overlap")
    return 0


def selftest():
    """Positive + RED controls; any failure exits 1."""
    ok = 0
    total = 0

    def check(name, cond):
        nonlocal ok, total
        total += 1
        if cond:
            ok += 1
            print(f"  PASS {name}")
        else:
            print(f"  FAIL {name}")

    clean_t = [{"expr": "1+1", "tid": 0}, {"expr": "2*3", "tid": 1}]
    clean_h = [{"expr": "5-2", "tid": 100}, {"expr": "7/2", "tid": 101}]
    contam_h = [{"expr": "2*3", "tid": 999}]  # collides with train[1]

    # 1. clean pools, --key rule -> 0 overlap
    ov, n_tr, n_hd = overlap(clean_t, clean_h, key="expr")
    check("clean key-rule 0 overlap", ov == set() and n_tr == 2 and n_hd == 2)

    # 2. RED control: collided pools -> exactly the collided identity
    ov, _, _ = overlap(clean_t, contam_h, key="expr")
    check("contaminated key-rule catches expr", ov == {json.dumps("2*3")})

    # 3. whole-record hash: identical record collides, reordered dict does NOT
    rec = {"a": 1, "b": [1, 2]}
    ov, _, _ = overlap([rec], [{"b": [1, 2], "a": 1}], key=None)
    check("whole-record hash key-order insensitive", ov != set())
    ov2, _, _ = overlap([rec], [{"a": 1, "b": [2, 1]}], key=None)
    check("whole-record hash content-sensitive", ov2 == set())

    # 4. missing key fails loud (KeyError), not silent skip
    try:
        overlap(clean_t, [{"wrong": 1}], key="expr")
        missing_ok = False
    except KeyError:
        missing_ok = True
    check("missing key raises KeyError (fail-loud)", missing_ok)

    # 5. run_gate end-to-end rc mapping via temp files
    import tempfile, os
    with tempfile.TemporaryDirectory() as d:
        tp, hp, cp = os.path.join(d, "t.json"), os.path.join(d, "h.json"), os.path.join(d, "r.json")
        for p, recs in ((tp, clean_t), (hp, clean_h)):
            with open(p, "w") as f:
                json.dump(recs, f)
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_clean = run_gate(tp, hp, key="expr", out_path=cp)
        with open(cp) as f:
            rr = json.load(f)
        check("run_gate clean rc=0 + receipt", rc_clean == 0 and rr["verdict"] == "CLEAN")
        with open(hp, "w") as f:
            json.dump(contam_h, f)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_contam = run_gate(tp, hp, key="expr", out_path=cp)
        check("run_gate contaminated rc=1", rc_contam == 1)

    print(f"selftest {ok}/{total}")
    return 0 if ok == total else 1


def main():
    ap = argparse.ArgumentParser(
        description="train/heldout contamination gate (DET-1c pattern)")
    ap.add_argument("--train", help="train pool JSON (list of records)")
    ap.add_argument("--heldout", help="heldout pool JSON (list of records)")
    ap.add_argument("--key", default=None,
                    help="dotted key path for record identity (default: whole-record canonical sha256)")
    ap.add_argument("--out", default=None, help="JSON receipt path")
    ap.add_argument("--max-show", type=int, default=MAX_SHOW_DEFAULT,
                    help="max overlapping identities to list (default 10)")
    ap.add_argument("--selftest", action="store_true", help="run controls and exit")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())
    if not args.train or not args.heldout:
        ap.error("--train and --heldout are required (or use --selftest)")
    sys.exit(run_gate(args.train, args.heldout, key=args.key,
                      out_path=args.out, max_show=args.max_show))


if __name__ == "__main__":
    main()
