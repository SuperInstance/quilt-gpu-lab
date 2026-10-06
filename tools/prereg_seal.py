#!/usr/bin/env python3
"""SIG-1 — HMAC prereg seal + refuse-to-fire.

Seals a prereg file with HMAC-SHA256 over its sha256 digest (canonical JSON envelope).
Key comes from env QUILT_SEAL_KEY and is never echoed or written.

Usage:
  QUILT_SEAL_KEY=... python3 tools/prereg_seal.py seal   FILE
  QUILT_SEAL_KEY=... python3 tools/prereg_seal.py verify  FILE
Exit codes: 0 MATCH | 2 TAMPERED | 3 MISSING-SEAL | 4 KEY/ARG error.
"""
import hashlib
import hmac
import json
import os
import sys


def die(code, msg):
    print(msg, file=sys.stderr)
    sys.exit(code)


def key_from_env():
    k = os.environ.get("QUILT_SEAL_KEY")
    if not k:
        die(4, "QUILT_SEAL_KEY unset — refusing (fail loud, no silent defaults)")
    return k.encode()


def file_digest(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_seal(path):
    sp = path + ".seal.json"
    if not os.path.exists(sp):
        die(3, f"missing seal file: {sp}")
    with open(sp) as f:
        return json.load(f)


def canonical(b):
    return json.dumps(b, sort_keys=True, separators=(",", ":")).encode()


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("seal", "verify"):
        die(4, "usage: prereg_seal.py {seal|verify} FILE")
    cmd, path = sys.argv[1], sys.argv[2]
    key = key_from_env()
    digest = file_digest(path)
    if cmd == "seal":
        sp = path + ".seal.json"
        if os.path.exists(sp):
            die(4, f"refusing to overwrite existing seal: {sp} (re-seal is forgery surface)")
        env = {"alg": "HMAC-SHA256", "file": os.path.basename(path), "sha256": digest}
        mac = hmac.new(key, canonical(env), hashlib.sha256).hexdigest()
        with open(sp, "w") as f:
            json.dump({**env, "hmac": mac}, f, indent=2, sort_keys=True)
            f.write("\n")
        print(f"SEALED {path} sha256={digest}")
        return
    # verify
    env = {k: v for k, v in load_seal(path).items() if k != "hmac"}
    stored = load_seal(path)["hmac"]
    expect = hmac.new(key, canonical(env), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expect, stored):
        die(2, f"TAMPERED: HMAC mismatch on {path}")
    if env.get("sha256") != digest:
        die(2, f"TAMPERED: content digest drifted on {path} (sealed {env.get('sha256')[:12]} vs now {digest[:12]})")
    print(f"MATCH {path} sha256={digest}")


if __name__ == "__main__":
    main()
