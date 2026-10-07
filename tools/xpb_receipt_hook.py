#!/usr/bin/env python3
"""XP-B — git pre-commit receipt gate (digest-only, no keys).

Refuses every pre-registered receipt-corruption class on results/g7/:
  C1 receipt-reuse          same receipt_id twice with divergent content / re-add at HEAD
  C2 chain-repair           any byte modification of a receipt tracked at HEAD
  C3 truncated-receipt      invalid JSON or missing required fields
  C4 digest-substitution    non-sha256 (non-64-hex) digest pin in ledger or receipt
  C5 seed-mutation          determinism.seed / state_digest changed vs HEAD
Clean classes P1 (valid new receipt + ledger append) and P2 (unrelated files) exit 0.

Modes:
  --staged            run against the current git index (for use as a pre-commit hook)
  --selftest [DIR]    build a throwaway repo, fire all 7 classes, print exit matrix
Exit codes: 0 clean, 1 corruption refused, 2 harness error.
"""
import hashlib
import json
import os
import subprocess
import sys

RECEIVED_DIR = "results/g7"
LEDGER = os.path.join(RECEIVED_DIR, "ledger.jsonl")
REQUIRED_FIELDS = ("schema", "receipt_id", "determinism", "gate")
SHA_LEN = 64


def sh(args, cwd, **kw):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, **kw)


def _sha256(b):
    return hashlib.sha256(b).hexdigest()


def _blob_at_head(repo, path):
    r = sh(["git", "show", f"HEAD:{path}"], cwd=repo)
    return r.stdout.encode() if r.returncode == 0 else None


def check_staged(repo):
    """Return list of refusals for staged changes in repo (string worktree)."""
    st = sh(["git", "status", "--porcelain"], cwd=repo)
    if st.returncode != 0:
        return [("HARNESS", f"git status failed: {st.stderr.strip()}")]
    refusals = []
    ledger_staged = sh(["git", "diff", "--cached", "--name-status"], cwd=repo)
    staged = {}
    for line in ledger_staged.stdout.splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2:
            staged[parts[1]] = parts[0]

    ledger_lines_new = []
    ledger_head = _blob_at_head(repo, LEDGER)
    for f, status in staged.items():
        if not (f == LEDGER or f.startswith(RECEIVED_DIR + "/")):
            continue  # P2: unrelated files pass untouched
        if f == LEDGER:
            content = sh(["git", "show", f":{f}"], cwd=repo)
            if content.returncode != 0:
                refusals.append(("C3", f"ledger unreadable in index: {f}"))
                continue
            head_lines = (ledger_head or b"").decode().splitlines()
            new_lines = [l for l in content.stdout.splitlines() if l not in head_lines]
            for l in new_lines:
                try:
                    ledger_lines_new.append(json.loads(l))
                except json.JSONDecodeError:
                    refusals.append(("C3", f"ledger line not JSON: {l[:80]}"))
                except Exception:
                    pass
                d = None
                try:
                    d = json.loads(l).get("digest")
                except Exception:
                    pass
                if d is not None and (len(d) != SHA_LEN or any(c not in "0123456789abcdef" for c in d)):
                    refusals.append(("C4", f"non-sha256 digest pin in ledger: {d!r}"))
        else:
            blob = sh(["git", "show", f":{f}"], cwd=repo)
            content = blob.stdout.encode() if blob.returncode == 0 else b""
            head = _blob_at_head(repo, f)
            if head is not None:
                if status.startswith(("M", "T", "D")) or content != head:
                    name = "C5" if _is_seed_edit(head, content) else "C2"
                    refusals.append((name, f"append-only violation: {f} modified vs HEAD"))
                continue
            # new receipt file: C3/C4 structural checks
            rec = None
            try:
                rec = json.loads(content.decode())
                missing = [k for k in REQUIRED_FIELDS if k not in rec]
                if missing:
                    refusals.append(("C3", f"{f} missing required fields {missing}"))
            except Exception:
                refusals.append(("C3", f"{f} not valid JSON"))
            for key in ("state_digest", "digest", "sha"):
                v = _find_digest(rec, key) if rec else None
                if v is not None and (len(v) != SHA_LEN or any(c not in "0123456789abcdef" for c in v)):
                    refusals.append(("C4", f"{f} carries non-sha256 pin {key}={v!r}"))

    # C1: reuse — same receipt_id twice in staged ledger lines, or id already at HEAD
    ids = [l.get("receipt_id") for l in ledger_lines_new]
    if len(ids) != len(set(ids)):
        refusals.append(("C1", "receipt-reuse: duplicate receipt_id in staged ledger lines"))
    if ledger_head:
        head_ids = set()
        for l in ledger_head.decode().splitlines():
            try:
                head_ids.add(json.loads(l).get("receipt_id"))
            except Exception:
                pass
        dup = [i for i in ids if i in head_ids]
        if dup:
            refusals.append(("C1", f"receipt-reuse: {dup[0]} already ledgered at HEAD"))
    # C1 content-divergence: two ledger lines same id but the receipt files differ
    by_id = {}
    for l in ledger_lines_new:
        by_id.setdefault(l.get("receipt_id"), set()).add(
            (l.get("gate_verdict"), l.get("schema_valid")))
    for rid, vals in by_id.items():
        if rid and len(vals) > 1:
            refusals.append(("C1", f"receipt-reuse: divergent ledger lines for {rid}"))
    # dedupe, keep first-named
    out, seen = [], set()
    for name, msg in refusals:
        k = (name, msg)
        if k not in seen:
            seen.add(k)
            out.append((name, msg))
    return out


def _find_digest(obj, key, depth=0):
    if depth > 6 or not isinstance(obj, dict):
        return None
    if key in obj and isinstance(obj[key], str):
        return obj[key]
    for v in obj.values():
        r = _find_digest(v, key, depth + 1)
        if r is not None:
            return r
    return None


def _is_seed_edit(head, new):
    try:
        h, n = json.loads(head.decode()), json.loads(new.decode())
        return (h.get("determinism") != n.get("determinism")
                and h.get("receipt_id") == n.get("receipt_id"))
    except Exception:
        return False


VALID_RECEIPT = {
    "schema": "g7-watt-receipt@1",
    "receipt_id": "g7-wr-xp-b-clean-class-p1-1799999999",
    "determinism": {"seed": 2718, "state_digest": _sha256(b"xp-b-clean")},
    "gate": {"rule": "no receipt -> run VOID", "verdict": "PASS"},
}


def selftest(base):
    """Fire all classes in a throwaway repo under base. Returns matrix rows."""
    import shutil
    repo = os.path.join(base, "xpb_selftest_repo")
    shutil.rmtree(repo, ignore_errors=True)
    os.makedirs(os.path.join(repo, RECEIVED_DIR), exist_ok=True)
    sh(["git", "init", "-q"], cwd=repo)
    sh(["git", "config", "user.email", "xpb@test"], cwd=repo)
    sh(["git", "config", "user.name", "xpb"], cwd=repo)
    with open(os.path.join(repo, LEDGER), "w") as f:
        pass
    rows = []

    def stage_and_commit():
        sh(["git", "add", "-A"], cwd=repo)
        return sh(["git", "commit", "-qm", "anchor"], cwd=repo).returncode

    def fire(name, expect_refuse, desc, mutate):
        sh(["git", "reset", "-q"], cwd=repo)
        sh(["git", "checkout", "-q", "--", "."], cwd=repo)
        sh(["git", "clean", "-qfd", RECEIVED_DIR], cwd=repo)
        mutate()
        r = sh([sys.executable, os.path.abspath(__file__), "--staged"], cwd=repo)
        refused = r.returncode == 1
        named = any(cls in r.stderr for cls in ("C1", "C2", "C3", "C4", "C5")) if refused else False
        ok = (refused and named) if expect_refuse else (r.returncode == 0)
        rows.append((name, desc, r.returncode, "PASS" if ok else "RED",
                     r.stderr.strip()[:120]))

    # anchor commit: one valid receipt + ledger
    def anchor():
        p = os.path.join(repo, RECEIVED_DIR, VALID_RECEIPT["receipt_id"] + ".json")
        with open(p, "w") as f:
            json.dump(VALID_RECEIPT, f, indent=2)
        with open(os.path.join(repo, LEDGER), "a") as f:
            f.write(json.dumps({"receipt_id": VALID_RECEIPT["receipt_id"],
                                "digest": VALID_RECEIPT["determinism"]["state_digest"],
                                "gate_verdict": "PASS"}) + "\n")
    anchor()
    assert stage_and_commit() == 0

    # P1 clean valid append
    def p1():
        rec = dict(VALID_RECEIPT)
        rec["receipt_id"] = "g7-wr-xp-b-p1-append-1800000000"
        rec["determinism"] = {"seed": 2719, "state_digest": _sha256(b"xp-b-p1")}
        with open(os.path.join(repo, RECEIVED_DIR, rec["receipt_id"] + ".json"), "w") as f:
            json.dump(rec, f, indent=2)
        with open(os.path.join(repo, LEDGER), "a") as f:
            f.write(json.dumps({"receipt_id": rec["receipt_id"],
                                "digest": rec["determinism"]["state_digest"],
                                "gate_verdict": "PASS"}) + "\n")
    fire("P1", False, "valid new receipt + ledger append", p1)

    # P2 unrelated file
    def p2():
        with open(os.path.join(repo, "unrelated.txt"), "w") as f:
            f.write("hello\n")
    fire("P2", False, "unrelated staged file", p2)

    # C1 reuse: re-append existing id
    def c1():
        with open(os.path.join(repo, LEDGER), "a") as f:
            f.write(json.dumps({"receipt_id": VALID_RECEIPT["receipt_id"],
                                "digest": _sha256(b"different"),
                                "gate_verdict": "PASS"}) + "\n")
        sh(["git", "add", "-A"], cwd=repo)
    fire("C1", True, "receipt-reuse (id already at HEAD)", c1)

    # C2 chain-repair: modify tracked receipt
    def c2():
        p = os.path.join(repo, RECEIVED_DIR, VALID_RECEIPT["receipt_id"] + ".json")
        rec = dict(VALID_RECEIPT)
        rec["gate"] = {"rule": "no receipt -> run VOID", "verdict": "VOID"}
        with open(p, "w") as f:
            json.dump(rec, f, indent=2)
        sh(["git", "add", "-A"], cwd=repo)
    fire("C2", True, "chain-repair (tracked receipt edited)", c2)

    # C3 truncated receipt
    def c3():
        with open(os.path.join(repo, RECEIVED_DIR, "g7-wr-xp-b-c3-trunc-1800000001.json"), "w") as f:
            f.write('{"schema": "g7-watt-rece')
        sh(["git", "add", "-A"], cwd=repo)
    fire("C3", True, "truncated receipt (invalid JSON)", c3)

    # C4 fnv-64 digest pin
    def c4():
        with open(os.path.join(repo, LEDGER), "a") as f:
            f.write(json.dumps({"receipt_id": "g7-wr-xp-b-c4-fnv-1800000002",
                                "digest": "9ae16a3b2f90404f",
                                "gate_verdict": "PASS"}) + "\n")
        sh(["git", "add", "-A"], cwd=repo)
    fire("C4", True, "digest-substitution (fnv-64 pin)", c4)

    # C5 seed mutation
    def c5():
        p = os.path.join(repo, RECEIVED_DIR, VALID_RECEIPT["receipt_id"] + ".json")
        rec = dict(VALID_RECEIPT)
        rec["determinism"] = {"seed": 999, "state_digest": rec["determinism"]["state_digest"]}
        with open(p, "w") as f:
            json.dump(rec, f, indent=2)
        sh(["git", "add", "-A"], cwd=repo)
    fire("C5", True, "GPU-cell seed mutation", c5)

    return rows


def main():
    args = sys.argv[1:]
    if args and args[0] == "--selftest":
        base = args[1] if len(args) > 1 else "/home/eileen/scratch"
        rows = selftest(base)
        print("class  desc                                  exit  verdict  detail")
        for name, desc, code, verdict, detail in rows:
            print(f"{name:6} {desc:37} {code:4}  {verdict:7}  {detail}")
        bad = [r for r in rows if r[3] == "RED"]
        print(f"\nmatrix: {len(rows) - len(bad)}/{len(rows)} PASS")
        return 0 if not bad else 1
    # hook mode
    repo = os.getcwd()
    refusals = check_staged(repo)
    if refusals:
        for name, msg in refusals:
            print(f"XP-B REFUSE [{name}]: {msg}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
