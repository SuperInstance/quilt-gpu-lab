#!/usr/bin/env python3
"""extract_sections.py — split a dog-food reply into named sections, strip fences.

Usage: extract_sections.py REPLY.md OUTDIR
Writes each `=== NAME ===` section to OUTDIR/NAME (fences stripped).
"""
import re
import sys
from pathlib import Path


def main() -> None:
    reply = Path(sys.argv[1]).read_text()
    outdir = Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    parts = re.split(r"^===\s*([A-Za-z0-9_.]+)\s*===\s*$", reply, flags=re.M)
    written = []
    for i in range(1, len(parts), 2):
        name = parts[i]
        body = parts[i + 1]
        # strip a single leading fenced block if present
        m = re.search(r"```[a-zA-Z0-9]*\n(.*?)```", body, flags=re.S)
        content = m.group(1) if m else body.strip() + "\n"
        (outdir / name).write_text(content)
        written.append((name, len(content)))
    for n, sz in written:
        print(f"{n}\t{sz}")


if __name__ == "__main__":
    main()
