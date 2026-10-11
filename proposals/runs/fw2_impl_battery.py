#!/usr/bin/env python3
"""FW-2-IMPL booking battery (prereg: proposals/runs/FW-2-impl-booking-2026-10-10.md).

Independent RFC 6962 vectors (NOT imported from the tool) + G2 chain-tamper RED +
G3 truncation RED + G4 v1 non-regression probe. Run from committed tree only.
"""
import hashlib, json, subprocess, sys, tempfile, os

sys.path.insert(0, "tools")
import merkle_seal_chain as msc

fails = []

def check(name, ok, why=""):
    print(("PASS" if ok else "RED"), name, why)
    if not ok:
        fails.append(name)

# ---- G1: independent RFC 6962 MTH (spec: split at largest power of two < n)
def ref_root(leaves):
    if len(leaves) == 0:
        return hashlib.sha256(b"").digest()
    if len(leaves) == 1:
        return hashlib.sha256(b"\x00" + leaves[0]).digest()
    k = 1
    while k * 2 < len(leaves):
        k *= 2
    l = ref_root(leaves[:k]); r = ref_root(leaves[k:])
    return hashlib.sha256(b"\x01" + l + r).digest()

corpus = [b"a", b"bb", b"ccc", b"dddd", b"e" * 5, b"f" * 6, b"g" * 7]
check("G1-empty", msc.merkle_root_iterative([]) == ref_root([]))
check("G1-singleton", msc.merkle_root_iterative([b"x"]) == ref_root([b"x"]))
for n in range(2, len(corpus) + 1):
    sub = [msc.leaf_payload(f"p{i}", hashlib.sha256(corpus[i]).hexdigest()) for i in range(n)]
    check(f"G1-n{n}", msc.merkle_root_iterative(sub) == ref_root(sub))
    check(f"G1-n{n}-refcross", msc.merkle_root_reference(sub) == ref_root(sub))
st = msc.selftest.__wrapped__() if hasattr(msc.selftest, "__wrapped__") else None

# tool selftest battery (G1-G3 per its own header) — capture its verdict
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc_selftest = msc.selftest()
check("G1-tool-selftest", rc_selftest == 0, buf.getvalue()[-300:])

# ---- G2: chain tamper RED
rows = [("a.txt", hashlib.sha256(b"a").hexdigest()), ("b.txt", hashlib.sha256(b"b").hexdigest())]
prev_bytes = b"PREV-MANIFEST-BYTES"
man = msc.seal(rows, prev_bytes)
tampered = json.loads(json.dumps(man))
tampered["seal_chain"]["prev_digest"] = "0" * 64
rc, rec = msc.verify(tampered, prev_bytes, rows)
check("G2-tamper-prev-RED", rc != 0 and "chain" in rec.get("why", ""), rec.get("why", ""))

# ---- G3: truncation RED, size named first
trunc = json.loads(json.dumps(man)); trunc["rows"] = trunc["rows"][:1]
rc, rec = msc.verify(trunc, prev_bytes, rows)
check("G3-truncate-RED-size-first", rc != 0 and "size" in rec.get("why", ""), rec.get("why", ""))
# re-seal of truncated set with stale prev -> chain-break RED
man2 = msc.seal(rows[:1], prev_bytes)
rc, rec = msc.verify(man2, prev_bytes, rows[:1])  # honest chain: should be CLEAN
check("G3-honest-reseal-CLEAN", rc == 0, rec.get("why", ""))
rc, rec = msc.verify(man2, b"OTHER-PREV", rows[:1])
check("G3-stale-prev-RED", rc != 0, rec.get("why", ""))

# ---- G4: v1 non-regression
r = subprocess.run([sys.executable, "tools/receipt_manifest.py", "--check"], capture_output=True, text=True)
check("G4-v1-check-runs", r.returncode in (0, 1), f"rc={r.returncode} {r.stderr[-200:]}")
r = subprocess.run([sys.executable, "tools/git_anchor_check.py", "--manifest", "receipts/manifest.json"], capture_output=True, text=True)
check("G4-gitanchor", "ANCHORED" in r.stdout, r.stdout[-200:] + r.stderr[-200:])

print(json.dumps({"battery": "FW-2-IMPL", "verdict": "RED" if fails else "GREEN",
                  "fails": fails}))
sys.exit(1 if fails else 0)
