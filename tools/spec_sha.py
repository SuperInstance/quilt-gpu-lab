#!/usr/bin/env python3
"""SS-1: spec_sha — canon-form sha256 pins for pre-registration files.

Fleet pattern (SCOUT-36 spec_sha convergence: madlibs-jev ee7b73a, unspoken-resonance
3ad67d4): canon-form sha256 of the frozen gate text, committed before implementation,
`--check` NEVER writes, missing/mismatched pins are loud.

Canon form: decode UTF-8, normalize CRLF->LF, strip trailing whitespace per line,
collapse 3+ consecutive newlines to 2, final newline. Cosmetic churn does not move
the pin; any word-level edit does.

Subcommands:
  pin FILE...            print canon sha256 per file
  --init LEDGER FILE...  write/update ledger {path: sha} (the ONLY writing mode)
  --check LEDGER [FILE]  verify; exit 0 all MATCH, 2 MISMATCH, 3 STALE(missing),
                         4 UNPINNED (file not in ledger). Writes nothing.
"""
import hashlib, json, sys
from pathlib import Path


def canon(path: str) -> bytes:
    text = Path(path).read_text(encoding="utf-8")
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").split("\n")]
    out = "\n".join(lines)
    while "\n\n\n" in out:
        out = out.replace("\n\n\n", "\n\n")
    return (out.rstrip("\n") + "\n").encode("utf-8")


def sha(path: str) -> str:
    return hashlib.sha256(canon(path)).hexdigest()


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 4
    mode = argv[1]
    if mode == "pin":
        for f in argv[2:]:
            print(f"{sha(f)}  {f}")
        return 0
    if mode == "--init":
        ledger, files = argv[2], argv[3:]
        old = json.loads(Path(ledger).read_text()) if Path(ledger).exists() else {}
        old.update({f: sha(f) for f in files})
        Path(ledger).write_text(json.dumps(old, indent=2, sort_keys=True) + "\n")
        print(f"pinned {len(files)} files -> {ledger}")
        return 0
    if mode == "--check":
        ledger = argv[2]
        targets = argv[3:] or sorted(json.loads(Path(ledger).read_text()).keys())
        pins = json.loads(Path(ledger).read_text())
        bad = 0
        for f in targets:
            if f not in pins:
                print(f"UNPINNED {f}")
                bad = max(bad, 4)
                continue
            if not Path(f).exists():
                print(f"STALE {f} (missing)")
                bad = max(bad, 3)
                continue
            got = sha(f)
            if got != pins[f]:
                print(f"MISMATCH {f} pinned={pins[f][:16]} got={got[:16]}")
                bad = max(bad, 2)
            else:
                print(f"MATCH {f}")
        return bad
    print(f"unknown mode {mode!r}")
    return 4


if __name__ == "__main__":
    sys.exit(main(sys.argv))
