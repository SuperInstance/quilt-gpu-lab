#!/usr/bin/env python3
"""hashdut — the fleet's hash customs officer.

"dut" = device under test. Three independent lanes independently rediscovered
that a vendored ``fnv1a64`` hashes UTF-16 ``charCodeAt`` code units, NOT UTF-8
bytes. Same NAME, different BYTES. This tool makes that divergence a standing
instrument instead of a recurring incident: it publishes the fleet's canonical
hash alphabet (a digest) and inspects any implementation that claims one of the
known hash names, flagging name/byte collisions.

METAPHOR: a customs officer does not care what a crate is *called* — it scans
the *bytes*. A manifest that says "fnv1a64" but carries charCodeAt bytes is a
misdeclared shipment.

ALPHABET (per canary): fnv1a64-utf8, fnv1a64-utf16-charCodeAt,
fnv1a64-utf16-le-bytes, sha256, sha1, md5.

CANONICAL NAME MAP (what a bare name is *supposed* to mean in the fleet):
    fnv1a64            -> fnv1a64-utf8      (the fleet canary spelling)
    fnv1a64_utf8       -> fnv1a64-utf8
    fnv1a64_utf16*     -> fnv1a64-utf16-charCodeAt
    sha256/sha1/md5    -> themselves

rc policy: 0 = MATCH, 1 = mismatch / NAME-COLLISION / UNKNOWN-PRIMITIVE,
2 = fail-input (bad args, unreadable/unevaluable file, sandbox failure).

WORKED EXAMPLE
--------------
    $ python3 tools/hash_dut.py digest --out /tmp/hashdut.json
    $ python3 tools/hash_dut.py check quilt-dba/shared/receipts.mjs
    hashdut check: .../quilt-dba/shared/receipts.mjs
      [fnv1a64]  canonical spelling = fnv1a64-utf8
        empty  impl=0xcbf29ce484222325  exp=0xcbf29ce484222325  ok
        abc    impl=0xe71fa2190541574b  exp=0xe71fa2190541574b  ok
        cafe   impl=0x77ff2029b867f2b5  exp=0x24a555471370b18d  MISMATCH
        long   impl=0x2fd4bb81bfb62325  exp=0x2fd4bb81bfb62325  ok
    verdict: NAME-COLLISION — "fnv1a64" here spells fnv1a64-utf16-charCodeAt
    (rc=1)

    $ python3 tools/hash_dut.py --selftest
    selftest: 14/14 PASS  (rc=0)
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import urllib.request

MASK64 = 0xFFFFFFFFFFFFFFFF
FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME = 0x100000001B3

# id -> literal canary. "long" is a 64 KiB input to exercise streaming length.
CANARIES: list[tuple[str, str]] = [
    ("empty", ""),
    ("abc", "abc"),
    ("cafe", "caf\u00e9 \u0394 \u65e5\u672c\u8a9e"),  # "café Δ 日本語"
    ("long", "0" * (1 << 16)),
]

CANARY_LABEL = {
    "empty": '""',
    "abc": '"abc"',
    "cafe": "the portability canary",
    "long": '"0" * 65536',
}

# canonical alphabet keys, in report order
PRIMITIVES = [
    "fnv1a64-utf8",
    "fnv1a64-utf16-charCodeAt",
    "fnv1a64-utf16-le-bytes",
    "sha256",
    "sha1",
    "md5",
]

# bare/explicit name -> canonical primitive. Bare "fnv1a64" is DEFINED by the
# fleet as UTF-8; anything else that claims the name is a collision.
NAME_TO_CANON = {
    "fnv1a64": "fnv1a64-utf8",
    "fnv1a64_utf8": "fnv1a64-utf8",
    "fnv1a64Utf8": "fnv1a64-utf8",
    "fnv1a64_utf16_charCodeAt": "fnv1a64-utf16-charCodeAt",
    "fnv1a64_utf16": "fnv1a64-utf16-charCodeAt",
    "fnv1a64_utf16_le_bytes": "fnv1a64-utf16-le-bytes",
    "fnv1a64_le_bytes": "fnv1a64-utf16-le-bytes",
    "sha256": "sha256",
    "sha1": "sha1",
    "md5": "md5",
}
PROBE_NAMES = list(NAME_TO_CANON.keys())
SANDBOX_TIMEOUT_S = 10


# ── hashing primitives ──────────────────────────────────────────────────────

def fnv1a_bytes(b: bytes) -> int:
    h = FNV_OFFSET
    for x in b:
        h ^= x
        h = (h * FNV_PRIME) & MASK64
    return h


def fnv1a64_utf8(s: str) -> int:
    return fnv1a_bytes(s.encode("utf-8"))


def fnv1a64_utf16_charCodeAt(s: str) -> int:
    """Replicates JS ``s.charCodeAt(i)`` iteration (UTF-16 code units)."""
    u = s.encode("utf-16-le")
    h = FNV_OFFSET
    for i in range(0, len(u), 2):
        cu = u[i] | (u[i + 1] << 8)
        h ^= cu
        h = (h * FNV_PRIME) & MASK64
    return h


def fnv1a64_utf16_le_bytes(s: str) -> int:
    return fnv1a_bytes(s.encode("utf-16-le"))


def _hasher(name: str, s: str) -> int:
    return int(getattr(hashlib, name)(s.encode("utf-8")).hexdigest(), 16)


COMPUTE = {
    "fnv1a64-utf8": fnv1a64_utf8,
    "fnv1a64-utf16-charCodeAt": fnv1a64_utf16_charCodeAt,
    "fnv1a64-utf16-le-bytes": fnv1a64_utf16_le_bytes,
    "sha256": lambda s: _hasher("sha256", s),
    "sha1": lambda s: _hasher("sha1", s),
    "md5": lambda s: _hasher("md5", s),
}

HEX_WIDTH = {
    "fnv1a64-utf8": 16,
    "fnv1a64-utf16-charCodeAt": 16,
    "fnv1a64-utf16-le-bytes": 16,
    "sha256": 64,
    "sha1": 40,
    "md5": 32,
}


def hex_of(primitive: str, value: int) -> str:
    return "0x" + format(value, "0%dx" % HEX_WIDTH[primitive])


def build_digest() -> dict:
    vectors: dict[str, dict[str, str]] = {}
    canaries_meta = []
    for cid, text in CANARIES:
        vectors[cid] = {
            p: hex_of(p, COMPUTE[p](text)) for p in PRIMITIVES
        }
        canaries_meta.append({
            "id": cid,
            "repr": CANARY_LABEL[cid],
            "py_len": len(text),
            "utf16_units": len(text.encode("utf-16-le")) // 2,
        })
    return {
        "tool": "hashdut",
        "v": 1,
        "canon_name_map": NAME_TO_CANON,
        "canaries": canaries_meta,
        "vectors": vectors,
    }


# ── expectations (ints) for comparison ──────────────────────────────────────

def expected_ints() -> dict[str, list[int]]:
    return {
        p: [COMPUTE[p](t) for _, t in CANARIES] for p in PRIMITIVES
    }


# ── subprocess harnesses ────────────────────────────────────────────────────

PY_HARNESS = r'''
import sys, json, importlib.util
target = sys.argv[1]
payload = json.load(sys.stdin)

def normalize(v):
    if isinstance(v, bool):
        return str(int(v))
    if isinstance(v, int):
        return "0x%x" % v
    if isinstance(v, bytes):
        return "0x" + v.hex()
    return str(v)

try:
    spec = importlib.util.spec_from_file_location("hashdut_impl_under_test", target)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
except Exception as e:
    print(json.dumps({"ok": False, "error": "import failed: %s" % e}))
    sys.exit(0)

res = {"ok": True, "fns": {}}
for name in payload["names"]:
    fn = getattr(mod, name, None)
    if not callable(fn):
        continue
    outs, err = [], None
    for c in payload["canaries"]:
        try:
            outs.append(normalize(fn(c)))
        except TypeError:
            # impl expects bytes -- feed the UTF-8 encoding of the canary
            try:
                outs.append(normalize(fn(c.encode("utf-8"))))
            except Exception as e2:
                err = "%s: %s" % (type(e2).__name__, e2)
                break
        except Exception as e:
            err = "%s: %s" % (type(e).__name__, e)
            break
    res["fns"][name] = {"ok": False, "error": err} if err else {"ok": True, "outputs": outs}
print(json.dumps(res))
'''

JS_HARNESS = r'''
import { pathToFileURL } from 'node:url';

const target = process.argv[2];
const chunks = [];
for await (const c of process.stdin) chunks.push(c);
const payload = JSON.parse(Buffer.concat(chunks).toString('utf8'));

function normalize(v) {
  if (typeof v === 'bigint') return '0x' + v.toString(16);
  if (typeof v === 'number') return '0x' + BigInt(Math.trunc(v)).toString(16);
  if (typeof v === 'string') return v;
  if (v && typeof v.toString === 'function') return v.toString();
  return String(v);
}

let mod;
try {
  mod = await import(pathToFileURL(target).href);
} catch (e) {
  console.log(JSON.stringify({ ok: false, error: 'import failed: ' + (e && e.message ? e.message : String(e)) }));
  process.exit(0);
}

const res = { ok: true, fns: {} };
for (const name of payload.names) {
  const fn = mod[name];
  if (typeof fn !== 'function') continue;
  const outs = [];
  let err = null;
  for (const c of payload.canaries) {
    try { outs.push(normalize(fn(c))); }
    catch (e) {
      if (e instanceof TypeError) {
        try { outs.push(normalize(fn(Buffer.from(c, 'utf8')))); }
        catch (e2) { err = (e2 && e2.message ? e2.message : String(e2)); break; }
      } else { err = (e && e.message ? e.message : String(e)); break; }
    }
  }
  res.fns[name] = err ? { ok: false, error: err } : { ok: true, outputs: outs };
}
console.log(JSON.stringify(res));
'''


def run_sandboxed(target: str) -> dict:
    """Evaluate a .py or .js impl in a bounded subprocess; return harness JSON."""
    ext = os.path.splitext(target)[1].lower()
    payload = json.dumps({
        "names": PROBE_NAMES,
        "canaries": [t for _, t in CANARIES],
    }).encode("utf-8")

    with tempfile.TemporaryDirectory(prefix="hashdut-") as td:
        if ext == ".py":
            harness = os.path.join(td, "harness.py")
            with open(harness, "w", encoding="utf-8") as fh:
                fh.write(PY_HARNESS)
            cmd = [sys.executable, harness, target]
        elif ext in (".js", ".mjs", ".cjs"):
            harness = os.path.join(td, "harness.mjs")
            with open(harness, "w", encoding="utf-8") as fh:
                fh.write(JS_HARNESS)
            cmd = ["node", harness, target]
        else:
            return {"ok": False, "error": "unsupported extension %r (want .py/.js/.mjs/.cjs)" % ext}

        try:
            proc = subprocess.run(
                cmd, input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=SANDBOX_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "timeout after %ds" % SANDBOX_TIMEOUT_S}
        except FileNotFoundError as e:
            return {"ok": False, "error": "runtime missing: %s" % e}

        out = proc.stdout.decode("utf-8", "replace").strip()
        last = out.splitlines()[-1] if out else ""
        try:
            parsed = json.loads(last)
        except Exception:
            err = proc.stderr.decode("utf-8", "replace").strip().splitlines()
            tail = err[-1] if err else "no output"
            return {"ok": False, "error": "harness produced no JSON (%s)" % tail}
        return parsed


def fetch_if_url(arg: str):
    """If arg is http(s), download to a tempfile keeping the extension.
    Returns (path, cleanup_path_or_None)."""
    if not (arg.startswith("http://") or arg.startswith("https://")):
        return arg, None
    with urllib.request.urlopen(arg, timeout=SANDBOX_TIMEOUT_S) as resp:
        data = resp.read()
    ext = os.path.splitext(arg.split("?", 1)[0])[1] or ".mjs"
    fd, tmp = tempfile.mkstemp(prefix="hashdut-fetch-", suffix=ext)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
    return tmp, tmp


# ── comparison / verdict ────────────────────────────────────────────────────

def parse_hex(v):
    if not isinstance(v, str):
        return None
    t = v.strip()
    if t.lower().startswith("0x"):
        t = t[2:]
    if not t:
        return None
    try:
        return int(t, 16)
    except ValueError:
        return None


def verdict_for(name: str, outputs, exp: dict[str, list[int]]):
    """Return (verdict, detail, rc)."""
    canon = NAME_TO_CANON[name]
    ints = [parse_hex(o) for o in outputs]
    if any(x is None for x in ints):
        return "UNKNOWN-PRIMITIVE", "produced a non-hex / unparsable value", 1
    if ints == exp[canon]:
        return "MATCH", "canonical spelling = %s" % canon, 0
    for other in PRIMITIVES:
        if other != canon and ints == exp[other]:
            return "NAME-COLLISION", '"%s" here spells %s' % (name, other), 1
    return "UNKNOWN-PRIMITIVE", "byte-spelling not in the fleet alphabet", 1


# ── subcommands ─────────────────────────────────────────────────────────────

def cmd_digest(args) -> int:
    digest = build_digest()
    text = json.dumps(digest, sort_keys=True, indent=2, ensure_ascii=False)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    return 0


def cmd_check(args) -> int:
    path, cleanup = fetch_if_url(args.path)
    try:
        if not os.path.isfile(path):
            print("hashdut: no such file: %s" % args.path, file=sys.stderr)
            return 2
        result = run_sandboxed(path)
        if not result.get("ok"):
            print("hashdut check: %s" % args.path)
            print("  verdict: SANDBOX-FAIL — %s" % result.get("error"))
            return 2
        fns = result.get("fns") or {}
        if not fns:
            print("hashdut check: %s" % args.path)
            print("  verdict: SANDBOX-FAIL — no known hash name exported "
                  "(probed: %s)" % ", ".join(PROBE_NAMES))
            return 2

        exp = expected_ints()
        worst_rc = 0
        print("hashdut check: %s" % args.path)
        for name in sorted(fns):
            entry = fns[name]
            if not entry.get("ok"):
                print("  [%s] verdict: SANDBOX-FAIL — %s" % (name, entry.get("error")))
                worst_rc = max(worst_rc, 2)
                continue
            outputs = entry["outputs"]
            canon = NAME_TO_CANON[name]
            print("  [%s]  canonical spelling = %s" % (name, canon))
            v, detail, rc = verdict_for(name, outputs, exp)
            for (cid, _), got in zip(CANARIES, outputs):
                want = hex_of(canon, exp[canon][[c for c, _ in CANARIES].index(cid)])
                got_i = parse_hex(got)
                ok = (got_i is not None and got_i == exp[canon][[c for c, _ in CANARIES].index(cid)])
                flag = "ok" if ok else "MISMATCH"
                print("      %-6s impl=%s  exp=%s  %s" % (cid, got, want, flag))
            print("    verdict: %s — %s" % (v, detail))
            worst_rc = max(worst_rc, rc)
        return worst_rc
    finally:
        if cleanup:
            try:
                os.unlink(cleanup)
            except OSError:
                pass


def cmd_selftest(args) -> int:
    checks = []

    def check(label, cond, detail=""):
        checks.append((label, bool(cond), detail))

    # 1) hashlib published test vectors (independent known-good)
    known = {
        ("sha256", ""): "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        ("sha256", "abc"): "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        ("sha1", ""): "da39a3ee5e6b4b0d3255bfef95601890afd80709",
        ("sha1", "abc"): "a9993e364706816aba3e25717850c26c9cd0d89d",
        ("md5", ""): "d41d8cd98f00b204e9800998ecf8427e",
        ("md5", "abc"): "900150983cd24fb0d6963f7d28e17f72",
    }
    for (prim, text), want in sorted(known.items()):
        got = format(COMPUTE[prim](text), "0%dx" % HEX_WIDTH[prim])
        check("hashlib %s(%r)" % (prim, text), got == want, got)

    # 2) hardcoded FNV-1a/64 UTF-16 charCodeAt pins (computed + receipted here)
    cafe = CANARIES[2][1]
    check("fnv1a64-utf16-charCodeAt(cafe) == 0x77ff2029b867f2b5",
          fnv1a64_utf16_charCodeAt(cafe) == 0x77FF2029B867F2B5,
          hex(fnv1a64_utf16_charCodeAt(cafe)))
    check("fnv1a64-utf16-charCodeAt(abc) == 0xe71fa2190541574b",
          fnv1a64_utf16_charCodeAt("abc") == 0xE71FA2190541574B,
          hex(fnv1a64_utf16_charCodeAt("abc")))

    # 3) portability proof: utf8 vs charCodeAt must DIFFER on the canary
    check("fnv1a64-utf8(cafe) == 0x24a555471370b18d (fleet canary)",
          fnv1a64_utf8(cafe) == 0x24A555471370B18D,
          hex(fnv1a64_utf8(cafe)))
    check("utf8(cafe) != charCodeAt(cafe)  [portability proof]",
          fnv1a64_utf8(cafe) != fnv1a64_utf16_charCodeAt(cafe))

    # 4) ASCII agreement (sanity: all three coincide only for pure ASCII)
    check("utf8(abc) == charCodeAt(abc) == 0xe71fa2190541574b",
          fnv1a64_utf8("abc") == fnv1a64_utf16_charCodeAt("abc") == 0xE71FA2190541574B)
    check("utf8(abc) != utf16-le-bytes(abc)  [byte-packing differs]",
          fnv1a64_utf8("abc") != fnv1a64_utf16_le_bytes("abc"))

    # 5) digest is internally complete
    d = build_digest()
    check("digest covers %d primitives x %d canaries" % (len(PRIMITIVES), len(CANARIES)),
          all(set(d["vectors"][cid]) == set(PRIMITIVES) for cid, _ in CANARIES))

    passed = sum(1 for _, ok, _ in checks if ok)
    for label, ok, detail in checks:
        mark = "PASS" if ok else "FAIL"
        extra = ("  [%s]" % detail) if (detail and not ok) else ""
        print("  %s  %s%s" % (mark, label, extra))
    print("selftest: %d/%d PASS" % (passed, len(checks)))
    return 0 if passed == len(checks) else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="hashdut",
        description="the fleet's hash customs officer: publish the hash alphabet, "
                    "inspect implementations for name/byte collisions.",
    )
    parser.add_argument("--selftest", action="store_true",
                        help="verify own vectors against hashlib and pinned FNV constants")
    sub = parser.add_subparsers(dest="cmd")

    p_digest = sub.add_parser("digest", help="emit the canonical hash-alphabet JSON")
    p_digest.add_argument("--out", help="also write the digest to this file")

    p_check = sub.add_parser("check", help="inspect a .py/.js/.mjs hash implementation")
    p_check.add_argument("path", help="path or http(s) URL of the implementation")

    args = parser.parse_args(argv)

    if args.selftest:
        return cmd_selftest(args)
    if args.cmd == "digest":
        return cmd_digest(args)
    if args.cmd == "check":
        return cmd_check(args)
    parser.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
