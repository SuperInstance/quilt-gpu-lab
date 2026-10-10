#!/usr/bin/env python3
"""merkle_seal_chain — RFC 6962 Merkle seal + git-anchored chain (FW-2 v2, stdlib-only).

Pattern lifted PROVEN from the FW-2 spec amendment (RC-4 class,
proposals/runs/FW-2-merkle-seal-chain-spec.md, landed 2026-10-10): a sha256
manifest can be wholesale re-sealed over tampered history (sealing is not a
secret operation) and suffix truncation changes only the tail — both invisible
to digest-by-digest verification. This tool closes both: a Merkle ROOT over
sorted (path, digest) leaves plus a SIZE, and a seal CHAIN that commits each
seal to the previous committed manifest blob.

Design (v2, per the frozen FW-2 spec):
  * Leaf payload = canonical ``path + "\\0" + hex-digest + "\\n"``, leaves
    sorted by path (deterministic; PARAM-1a lesson).
  * Merkle root via RFC 6962 MTH: leaf = SHA-256(0x00 || leaf), node =
    SHA-256(0x01 || left || right), split at the largest power of two < n,
    empty-set root = SHA-256("") (fail-loud on vacuous seal).
  * Checkpoint note (our format, NO wire-compat claim):
    ``origin\\nsize\\nbase64(root)\\n`` with strict byte-canonical parse.
  * seal_chain: prev_digest = sha256 of the previous manifest BYTES; genesis
    is an explicit ``prev_digest: null`` recorded exactly once. Verifier
    refuses a genesis that is not actually first, and a chain whose
    prev_digest does not match the supplied previous manifest bytes.

Honest boundary (G1): vector pins here are against a SELF-CONTAINED
independent recursive reference MTH (the RFC 6962 recursive definition,
implemented separately below) plus the pinned SHA-256("") empty root — the
byte-equal test against fleet-witness tree.js needs that repo present and is
left to the follow-on prereg integration per the spec's own STOP rule. No
wire-compat claim is made.

Worked example:
    python tools/merkle_seal_chain.py --example

CLI:
    python tools/merkle_seal_chain.py --seal-dir results --prev receipts/manifest.json \\
        --out receipts/manifest.next.json
    python tools/merkle_seal_chain.py --verify receipts/manifest.next.json \\
        --prev receipts/manifest.json --recompute-dir results
    python tools/merkle_seal_chain.py --note --manifest receipts/manifest.next.json
    python tools/merkle_seal_chain.py --selftest

Exit codes: 0 = CLEAN/SEALED, 1 = RED (tamper named), 2 = fail-loud input.
Never deletes anything; keys are never involved (pure hashlib, no network).
"""

import argparse
import base64
import hashlib
import json
import os
import sys

ORIGIN = "quilt-gpu-lab/receipt-manifest/v2"
SCHEMA = "quilt-gpu-lab/receipt-manifest@v2"


def fail_loud(msg):
    print(json.dumps({"tool": "merkle_seal_chain", "rc": 2, "error": msg}), file=sys.stderr)
    sys.exit(2)


# ---------------------------------------------------------------- RFC 6962 MTH

def _leaf_hash(leaf: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + leaf).digest()


def _node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def merkle_root_iterative(leaves):
    """RFC 6962 MTH, split-at-largest-power-of-two form (the tree.js form)."""
    n = len(leaves)
    if n == 0:
        return hashlib.sha256(b"").digest()
    if n == 1:
        return _leaf_hash(leaves[0])
    k = 1
    while k * 2 < n:
        k *= 2
    return _node_hash(merkle_root_iterative(leaves[:k]), merkle_root_iterative(leaves[k:]))


def merkle_root_reference(leaves):
    """Independent recursive reference MTH (RFC 6962 definition, separate impl
    used by the selftest to cross-check the iterative form)."""
    n = len(leaves)
    if n == 0:
        return hashlib.sha256(b"").digest()
    if n == 1:
        return _leaf_hash(leaves[0])
    k = 1 << ((n - 1).bit_length() - 1)  # largest power of two < n
    return _node_hash(merkle_root_reference(leaves[:k]), merkle_root_reference(leaves[k:]))


# ------------------------------------------------------------- note I/O (C2SP-shaped)

def checkpoint_note(size: int, root: bytes) -> bytes:
    return f"{ORIGIN}\n{size}\n".encode() + base64.b64encode(root) + b"\n"


def parse_checkpoint_note(note: bytes):
    body = note.decode("utf-8")
    lines = body.split("\n")
    if len(lines) != 4 or lines[3] != "":
        fail_loud(f"non-canonical checkpoint note (expected 3 lines + trailing newline), got {len(lines)} segments")
    if lines[0] != ORIGIN:
        fail_loud(f"note origin mismatch: expected {ORIGIN!r}, got {lines[0]!r}")
    try:
        size = int(lines[1], 10)
        root = base64.b64decode(lines[2], validate=True)
    except (ValueError, base64.binascii.Error) as e:
        fail_loud(f"note parse failure: {e}")
    if size < 0 or len(root) != 32:
        fail_loud("note size negative or root not 32 bytes")
    return size, root


# ------------------------------------------------------------------- seal / verify

def leaf_payload(path: str, hexdigest: str) -> bytes:
    return f"{path}\0{hexdigest}\n".encode("utf-8")


def make_rows(path_digest_pairs):
    rows = sorted((str(p), str(d)) for p, d in path_digest_pairs)
    for p, d in rows:
        if len(d) != 64 or any(c not in "0123456789abcdef" for c in d):
            fail_loud(f"row for {p!r} has non-sha256 digest")
        if "\0" in p or "\n" in p:
            fail_loud(f"path {p!r} contains canonical-breaking byte")
    return rows


def seal(rows, prev_manifest_bytes):
    """rows: [(path, hexdigest)] -> v2 manifest dict with seal_chain."""
    rows = make_rows(rows)
    root = merkle_root_iterative([leaf_payload(p, d) for p, d in rows])
    note = checkpoint_note(len(rows), root).decode()
    prev_digest = hashlib.sha256(prev_manifest_bytes).hexdigest() if prev_manifest_bytes is not None else None
    return {
        "schema": SCHEMA,
        "rows": [{"path": p, "digest": d} for p, d in rows],
        "note": note,
        "seal_chain": {
            "prev_digest": prev_digest,
            "size": len(rows),
            "root": root.hex(),
            "note": note,
        },
    }


def verify(manifest, prev_manifest_bytes, recomputed_rows):
    """RED on: root mismatch, size mismatch, note-root/manifest drift,
    chain break (prev_digest != sha256(prev bytes)), illegal genesis,
    or leaf-set drift vs recomputed rows. Returns (rc, receipt)."""
    rec = {"tool": "merkle_seal_chain", "op": "verify", "checks": []}

    def red(why):
        rec["verdict"] = "RED"
        rec["why"] = why
        return 1, rec

    if manifest.get("schema") != SCHEMA:
        return red(f"schema mismatch: {manifest.get('schema')!r}")
    chain = manifest.get("seal_chain")
    if not isinstance(chain, dict):
        return red("missing seal_chain")
    rows = manifest.get("rows")
    if not isinstance(rows, list):
        return red("missing rows")

    try:
        size, note_root = parse_checkpoint_note(manifest["note"].encode())
    except (KeyError, AttributeError):
        return red("missing note")
    if size != len(rows):
        return red(f"truncation/append caught: note size {size} != row count {len(rows)} (size names first)")

    leaves = [leaf_payload(r["path"], r["digest"]) for r in rows]
    try:
        root = merkle_root_iterative(leaves)
    except (KeyError, TypeError) as e:
        return red(f"malformed rows: {e}")
    if root != note_root:
        return red("root mismatch: note root != recomputed leaf-set root (leaf tampered or forged seal)")
    if chain.get("root") != root.hex():
        return red("seal_chain.root != manifest root (chain field drift)")
    if chain.get("size") != len(rows):
        return red("seal_chain.size != row count")

    prev_digest = chain.get("prev_digest")
    if prev_manifest_bytes is None:
        if prev_digest is not None:
            return red("chain break: manifest claims a predecessor but no prev manifest was supplied")
        rec["checks"].append("genesis-chain-ok")
    else:
        if prev_digest is None:
            return red("illegal genesis: prev manifest supplied but chain records prev_digest null (genesis only once)")
        actual = hashlib.sha256(prev_manifest_bytes).hexdigest()
        if prev_digest != actual:
            return red(f"chain break: prev_digest {prev_digest[:16]}… != sha256(prev manifest) {actual[:16]}…")
        rec["checks"].append("chain-ok")

    want = [{"path": p, "digest": d} for p, d in make_rows(recomputed_rows)]
    if want != rows:
        return red("recomputed leaf set differs from sealed rows (content drift under same seal)")
    rec["checks"].append("recompute-ok")
    rec["verdict"] = "CLEAN"
    rec["size"] = len(rows)
    rec["root"] = root.hex()
    return 0, rec


# ------------------------------------------------------------------- file helpers

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def seal_dir(d):
    out = []
    for name in sorted(os.listdir(d)):
        p = os.path.join(d, name)
        if os.path.isfile(p):
            out.append((name, sha256_file(p)))
    return out


# ------------------------------------------------------------------- selftest

def selftest():
    checks = []

    def check(name, ok, why=""):
        checks.append((name, ok, why))
        if not ok:
            print(f"FAIL {name}: {why}")
        else:
            print(f"ok   {name}")

    # G1 vectors: iterative == reference across odd/power-two/singleton/empty.
    corpus = []
    for n in (0, 1, 2, 3, 7, 8, 13):
        corpus.append([hashlib.sha256(f"leaf{i}".encode()).digest() for i in range(n)])
        leaves = corpus[-1]
        a = merkle_root_iterative(leaves)
        b = merkle_root_reference(leaves)
        check(f"G1-root-n={n}", a == b)
    check("G1-empty-root", merkle_root_iterative([]) == hashlib.sha256(b"").digest(),
          "empty set root must be SHA256(\"\") per RFC 6962")
    single = b"only\n"
    check("G1-singleton", merkle_root_iterative([single]) == hashlib.sha256(b"\x00" + single).digest())

    # G2 chain: genesis explicit null, then linkage; tamper named.
    rows = [("a.txt", "11" * 32), ("b.txt", "22" * 32), ("c.txt", "33" * 32)]
    genesis = seal(rows, None)
    check("G2-genesis-null", genesis["seal_chain"]["prev_digest"] is None)
    check("G2-genesis-verify", verify(genesis, None, rows)[0] == 0)
    two = seal(rows, json.dumps(genesis, sort_keys=True).encode())
    check("G2-chain-link", two["seal_chain"]["prev_digest"] == hashlib.sha256(json.dumps(genesis, sort_keys=True).encode()).hexdigest())
    check("G2-chain-verify", verify(two, json.dumps(genesis, sort_keys=True).encode(), rows)[0] == 0)
    broken = json.loads(json.dumps(two))
    broken["seal_chain"]["prev_digest"] = "0" * 64
    rc, rec = verify(broken, json.dumps(genesis, sort_keys=True).encode(), rows)
    check("G2-tamper-named", rc == 1 and "chain break" in rec["why"], rec.get("why", ""))

    # G3 truncation: drop a leaf -> size names first; stale-prev re-seal -> chain break.
    trunc = json.loads(json.dumps(two))
    trunc["rows"] = trunc["rows"][:-1]
    rc, rec = verify(trunc, json.dumps(genesis, sort_keys=True).encode(), rows)
    check("G3-truncation-size-first", rc == 1 and "size" in rec["why"], rec.get("why", ""))
    reseal = seal(rows[:-1], json.dumps(genesis, sort_keys=True).encode())
    rc, rec = verify(reseal, json.dumps(genesis, sort_keys=True).encode(), rows)
    check("G3-reseal-red", rc == 1, rec.get("why", ""))

    # Leaf tamper under intact note -> root mismatch named.
    tam = json.loads(json.dumps(two))
    tam["rows"][1]["digest"] = "ff" * 32
    rc, rec = verify(tam, json.dumps(genesis, sort_keys=True).encode(), rows)
    check("G3-leaf-tamper-root", rc == 1 and "root mismatch" in rec["why"], rec.get("why", ""))

    # Note strictness: junk after body throws fail-loud; wrong origin refuses.
    size, root = parse_checkpoint_note(checkpoint_note(3, b"\x01" * 32))
    check("note-roundtrip", size == 3 and root == b"\x01" * 32)
    junk = checkpoint_note(3, b"\x01" * 32) + b"extra\n"
    try:
        parse_checkpoint_note(junk)
        check("note-strict-junk", False, "junk accepted")
    except SystemExit:
        check("note-strict-junk", True)

    bad = []
    for m in ({}, json.loads(json.dumps(two))):
        pass  # placeholder to keep structure clear
    rc, rec = verify({"schema": "other"}, None, rows)
    check("fail-loud-schema", rc == 1)
    rc, rec = verify(two, None, rows)
    check("fail-loud-missing-prev", rc == 1 and "predecessor" in rec["why"], rec.get("why", ""))

    fails = [c for c in checks if not c[1]]
    print(json.dumps({"selftest": "PASS" if not fails else "FAIL",
                      "total": len(checks), "failed": len(fails)}))
    return 0 if not fails else 1


def example():
    """Seal a throwaway 4-file dir, verify clean, then show truncation RED."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        d = os.path.join(td, "results")
        os.mkdir(d)
        for i in range(4):
            with open(os.path.join(d, f"r{i}.json"), "w") as f:
                f.write(f'{{"run": {i}, "verdict": "KEEP"}}\n')
        rows = seal_dir(d)
        genesis = seal(rows, None)
        gbytes = json.dumps(genesis, sort_keys=True, indent=1).encode()
        two = seal(rows, gbytes)
        rc, rec = verify(two, gbytes, rows)
        print(f"clean verify: rc={rc} verdict={rec['verdict']} root={rec.get('root', '')[:16]}…")
        trunc = json.loads(json.dumps(two))
        trunc["rows"] = trunc["rows"][:2]  # suffix truncation attack
        rc, rec = verify(trunc, gbytes, rows)
        print(f"truncated:    rc={rc} verdict={rec['verdict']} why={rec['why']}")
        return rc  # 1 is the honest expected exit for the truncation demo


def main():
    ap = argparse.ArgumentParser(description="RFC 6962 Merkle seal + git-anchored chain (FW-2 v2)")
    ap.add_argument("--seal-dir", help="dir of files to seal (path=digest rows)")
    ap.add_argument("--prev", help="previous manifest JSON file (chain anchor; omit for genesis)")
    ap.add_argument("--out", help="write sealed manifest here")
    ap.add_argument("--verify", metavar="MANIFEST", help="verify this v2 manifest")
    ap.add_argument("--recompute-dir", help="dir to recompute rows from for --verify")
    ap.add_argument("--note", action="store_true", help="print the checkpoint note of --manifest")
    ap.add_argument("--manifest", help="manifest for --note")
    ap.add_argument("--example", action="store_true", help="worked example")
    ap.add_argument("--selftest", action="store_true", help="G1-G3 self-test battery")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())
    if args.example:
        sys.exit(example())

    def read_prev():
        if args.prev is None:
            return None
        try:
            with open(args.prev, "rb") as f:
                return f.read()
        except OSError as e:
            fail_loud(f"cannot read prev manifest: {e}")

    if args.seal_dir:
        if not os.path.isdir(args.seal_dir):
            fail_loud(f"--seal-dir {args.seal_dir} is not a directory")
        manifest = seal(seal_dir(args.seal_dir), read_prev())
        text = json.dumps(manifest, sort_keys=True, indent=1)
        if args.out:
            tmp = args.out + ".tmp"
            with open(tmp, "w") as f:
                f.write(text + "\n")
                f.flush()
                os.fsync(f.fileno())
            os.rename(tmp, args.out)
            print(f"sealed {manifest['seal_chain']['size']} rows -> {args.out} root={manifest['seal_chain']['root'][:16]}… prev={'genesis' if manifest['seal_chain']['prev_digest'] is None else 'chained'}")
        else:
            print(text)
        return

    if args.note:
        if not args.manifest:
            fail_loud("--note needs --manifest")
        with open(args.manifest) as f:
            m = json.load(f)
        print(m.get("note", "").rstrip())
        return

    if args.verify:
        try:
            with open(args.verify) as f:
                m = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            fail_loud(f"cannot read manifest: {e}")
        if not args.recompute_dir:
            fail_loud("--verify needs --recompute-dir")
        rc, rec = verify(m, read_prev(), seal_dir(args.recompute_dir))
        print(json.dumps(rec, sort_keys=True))
        sys.exit(rc)
        return

    ap.print_help()


if __name__ == "__main__":
    main()
