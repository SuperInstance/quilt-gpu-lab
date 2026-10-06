#!/usr/bin/env python3
"""SIG-1: HMAC prereg seals (SCOUT-49 variant).

sign <prereg.md>  -> writes <prereg>.sig (HMAC-SHA256 over raw file bytes)
check <prereg.md> -> exit 0 match | 2 MISMATCH | 3 key unset | 4 sig missing

Key: env QUILT_PREREG_KEY. Never echoed, never written. Throwaway per-invocation
keys are fine; no persistent key material is generated or stored.
Scope: touches only <prereg>.sig. Does NOT touch receipt_manifest.py / results sealer.
"""
import hashlib
import hmac
import os
import stat
import sys
import time

KEY_ENV = "QUILT_PREREG_KEY"


def die(code: int, msg: str) -> None:
    print(f"prereg_seal: {msg}", file=sys.stderr)
    sys.exit(code)


def get_key() -> bytes:
    v = os.environ.get(KEY_ENV, "")
    if not v:
        die(3, f"{KEY_ENV} not set — refusing (fail-loud, no fallback)")
    return v.encode("utf-8")


def digest(key: bytes, data: bytes) -> str:
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] not in ("sign", "check"):
        die(3, "usage: prereg_seal.py {sign|check} <prereg.md>")
    mode, path = sys.argv[1], sys.argv[2]
    sig_path = path + ".sig"

    key = get_key()
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        die(3, f"cannot read prereg: {e}")
    d = digest(key, data)

    if mode == "sign":
        if os.path.exists(sig_path):
            die(3, f"{sig_path} already exists — refuse to overwrite (archive-never-delete)")
        mode_str = oct(stat.S_IMODE(os.stat(path).st_mode))
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with open(sig_path, "w", encoding="utf-8") as f:
            f.write(f"# prereg seal {stamp} sha256-of-file:{hashlib.sha256(data).hexdigest()[:16]}\n")
            f.write(d + "\n")
        print(f"prereg_seal: signed {path} -> {sig_path}")
        return

    # check mode
    if not os.path.exists(sig_path):
        die(4, f"{sig_path} missing — prereg is UNSEALED, refuse to treat as gated")
    try:
        with open(sig_path, encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    except OSError as e:
        die(3, f"cannot read sig: {e}")
    if not lines:
        die(2, f"{sig_path} empty/corrupt — MISMATCH")
    if hmac.compare_digest(d, lines[-1]):
        print(f"prereg_seal: OK {path}")
        return
    die(2, f"MISMATCH: {path} does not match its seal (tamper or silent edit)")


if __name__ == "__main__":
    main()
