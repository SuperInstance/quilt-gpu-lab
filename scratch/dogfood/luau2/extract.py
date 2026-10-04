#!/usr/bin/env python3
"""Extract the three delimited sections from a Ling reply into files.
Sections: === LUAU_MODULE === / === LUA_TEST === / === NOTES ===
Tolerant: strips a leading ```lang fence if the model wrapped a section.
"""
import re
import sys
from pathlib import Path

MARK = re.compile(r"^===\s*(LUAU_MODULE|LUA_TEST|NOTES)\s*===\s*$")


def strip_fences(text: str) -> str:
    lines = text.splitlines()
    out = []
    in_fence = False
    for ln in lines:
        s = ln.strip()
        if s.startswith("```"):
            in_fence = not in_fence
            continue
        out.append(ln)
    return "\n".join(out)


def main():
    src = Path(sys.argv[1]).read_text()
    outdir = Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    sections = {}
    cur = None
    for ln in src.splitlines():
        m = MARK.match(ln)
        if m:
            cur = m.group(1)
            sections[cur] = []
            continue
        if cur:
            sections[cur].append("\n".join([ln]) if False else ln)
    hist = {}
    for name, lines in sections.items():
        body = strip_fences("\n".join(lines)).strip("\n") + "\n"
        (outdir / name).write_text(body)
        hist[name] = len(body)
    print(hist)


if __name__ == "__main__":
    main()
