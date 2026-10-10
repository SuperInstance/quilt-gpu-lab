#!/usr/bin/env python3
"""SIG-1: HMAC-SHA256 prereg seal (SCOUT-49 spawn, prereg 4dcfe09).

The signature is the leash: a prereg file sealed at commit time; a runner
calls `check` before firing and refuses on TAMPER/missing. Secret comes from
env PREREG_SEAL_SECRET and is never written or echoed.

Usage:
  prereg_seal.py seal <prereg>     -> writes <prereg>.seal.json (exit 0)
  prereg_seal.py verify <f> <seal> -> exit 0 MATCH / 1 TAMPERED
  prereg_seal.py check <prereg>    -> verify against default seal path (refuse-to-fire gate)
Missing/empty secret on seal: exit 2 (fail-loud). Canonical bytes = raw file bytes.
"""
import hashlib
import hmac
import json
import os
import sys


def _secret() -> bytes:
    s = os.environ.get("PREREG_SEAL_SECRET", "").strip()
    # VNaN-1: whitespace-only secret sealed successfully — strip before the empty check.
    if not s:
        print("REFUSE: PREREG_SEAL_SECRET missing/empty", file=sys.stderr)
        sys.exit(2)
    return s.encode()


def _key_id(secret: bytes) -> str:
    return hashlib.sha256(secret).hexdigest()[:8]


def seal(path: str) -> None:
    data = open(path, "rb").read()
    secret = _secret()
    mac = hmac.new(secret, data, hashlib.sha256).hexdigest()
    record = {
        "algo": "hmac-sha256",
        "key_id": _key_id(secret),
        "file": path,
        "digest": mac,
    }
    seal_path = path + ".seal.json"
    with open(seal_path, "w") as f:
        json.dump(record, f, sort_keys=True)
        f.write("\n")
    print(f"SEALED {path} -> {seal_path} key_id={record['key_id']}")


def _load(path: str):
    rec = json.load(open(path))
    assert rec["algo"] == "hmac-sha256", "bad algo"
    return rec


def verify(target: str, seal_path: str) -> None:
    secret = _secret()
    rec = _load(seal_path)
    data = open(target, "rb").read()
    mac = hmac.new(secret, data, hashlib.sha256).hexdigest()
    if hmac.compare_digest(mac, rec["digest"]):
        print("MATCH")
        sys.exit(0)
    print(f"TAMPERED {target}")
    sys.exit(1)


def check(path: str) -> None:
    seal_path = path + ".seal.json"
    if not os.path.exists(seal_path):
        print(f"REFUSE-TO-FIRE: no seal for {path}", file=sys.stderr)
        sys.exit(3)
    verify(path, seal_path)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "seal":
        seal(sys.argv[2])
    elif cmd == "verify":
        verify(sys.argv[2], sys.argv[3])
    elif cmd == "check":
        check(sys.argv[2])
    else:
        print(__doc__, file=sys.stderr)
        sys.exit(64)
