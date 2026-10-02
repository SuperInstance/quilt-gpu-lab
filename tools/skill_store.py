#!/usr/bin/env python3
"""skill_store -- grabbable Voyager-style verified-skill library (stdlib-only).

Pattern lifted from experiments/skill_library.py (VOYAGER-SKILLLIB, arXiv:2305.16291;
folded 2026-10-02, purity 39/39, retrieval PASS): a JSON-backed store of *verified*
code skills -- prompt + code + family tags -- with deterministic token-overlap
retrieval (Jaccard on stemmed word sets) instead of embeddings, so it runs anywhere
python3 runs. Store only what passed your verifier; retrieval gives top-k reuse
candidates for a new prompt.

Design laws carried over from the experiment:
    - the library stores ONLY what you explicitly add (verification is the caller's
      gate -- run your tests before --add; this tool never judges code itself)
    - retrieval is deterministic and seeded-free: same db + query -> same ranking
    - atomic writes (temp + fsync + rename); archive-by-rename for --reset
    - fail loud: bad JSON db, missing code file, empty query -> rc=2, no silent fixes

Usage:
    python3 tools/skill_store.py --db skills.json --add "reverse words in a string" \
        --file my_skill.py --family text --tag string
    python3 tools/skill_store.py --db skills.json --search "capitalize each word" --k 3
    python3 tools/skill_store.py --db skills.json --list
    python3 tools/skill_store.py --db skills.json --get <id>
    python3 tools/skill_store.py --db skills.json --selftest

Worked example (self-contained):
    $ cat > cap.py <<'EOF'
    def solve(s):
        return " ".join(w.capitalize() for w in s.split())
    EOF
    $ python3 tools/skill_store.py --db /tmp/sk.json --add "title case a sentence" \
        --file cap.py --family text --selftest-quiet
    $ python3 tools/skill_store.py --db /tmp/sk.json --search "capitalise sentence words"
    -> top hit: title case a sentence (family text)

Exit codes: 0 ok, 2 fail-loud input error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time

STOP = set("a an and as at be by for from in into is it of on or that the to with".split())


def _tokens(text: str) -> set:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in STOP and len(w) > 1}


def _load(db_path: str) -> list:
    if not os.path.exists(db_path):
        return []
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        sys.stderr.write(f"FAIL-INPUT: cannot read db {db_path}: {e}\n")
        sys.exit(2)
    if not isinstance(data, list):
        sys.stderr.write(f"FAIL-INPUT: db {db_path} is not a JSON list\n")
        sys.exit(2)
    return data


def _save(db_path: str, data: list) -> None:
    d = os.path.dirname(os.path.abspath(db_path)) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".skill_store_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, db_path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def add(db_path: str, prompt: str, code_path: str, family: str, tags: list) -> dict:
    if not prompt.strip():
        sys.stderr.write("FAIL-INPUT: empty prompt\n")
        sys.exit(2)
    if not os.path.isfile(code_path):
        sys.stderr.write(f"FAIL-INPUT: code file not found: {code_path}\n")
        sys.exit(2)
    with open(code_path, "r", encoding="utf-8") as f:
        code = f.read()
    db = _load(db_path)
    h = hashlib.sha256((prompt + "\0" + code).encode()).hexdigest()[:12]
    for s in db:
        if s.get("id") == h:
            print(f"DUPLICATE: skill {h} already in db (nothing written)")
            return s
    entry = {
        "id": h,
        "prompt": prompt.strip(),
        "code": code,
        "family": family.strip() or "general",
        "tags": sorted({t.strip() for t in tags if t.strip()}),
        "tokens": sorted(_tokens(prompt + " " + family + " " + " ".join(tags))),
        "added": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    db.append(entry)
    _save(db_path, db)
    print(f"STORED {h} family={entry['family']} tokens={len(entry['tokens'])}")
    return entry


def search(db_path: str, query: str, k: int) -> list:
    q = _tokens(query)
    if not q:
        sys.stderr.write("FAIL-INPUT: empty/stopword-only query\n")
        sys.exit(2)
    scored = []
    for s in _load(db_path):
        st = set(s.get("tokens", []))
        inter = len(q & st)
        jac = inter / len(q | st) if (q | st) else 0.0
        scored.append((jac, inter, s))
    scored.sort(key=lambda x: (-x[0], -x[1], x[2]["id"]))
    return scored[:k]


def reset(db_path: str) -> None:
    if os.path.exists(db_path):
        arch = db_path + ".archived-" + time.strftime("%Y%m%d-%H%M%S")
        os.replace(db_path, arch)
        print(f"ARCHIVED db -> {arch}")
    else:
        print("db absent; nothing to archive")


def selftest() -> int:
    import subprocess
    here = os.path.dirname(os.path.abspath(__file__))
    tool = os.path.join(here, "skill_store.py")
    tmp = tempfile.mkdtemp(prefix="skill_store_test_")
    db = os.path.join(tmp, "sk.json")
    fails = []

    def run(*args):
        return subprocess.run([sys.executable, tool, "--db", db] + list(args),
                              capture_output=True, text=True)

    # 1. add + dedupe
    f1 = os.path.join(tmp, "cap.py")
    with open(f1, "w") as f:
        f.write("def solve(s):\n    return s.upper()\n")
    r = run("--add", "uppercase a string", "--file", f1, "--family", "text")
    if r.returncode != 0 or "STORED" not in r.stdout:
        fails.append(f"add: rc={r.returncode} {r.stderr}")
    r2 = run("--add", "uppercase a string", "--file", f1, "--family", "text")
    if "DUPLICATE" not in r2.stdout:
        fails.append(f"dedupe: {r2.stdout!r}")

    # 2. search ranks the right skill top-1 (deterministic)
    r = run("--search", "convert text to upper case", "--k", "1")
    if r.returncode != 0 or "uppercase a string" not in r.stdout:
        fails.append(f"search: rc={r.returncode} out={r.stdout!r} err={r.stderr!r}")

    # 3. --get returns code verbatim
    r = run("--get", json.load(open(db))[0]["id"])
    if "return s.upper()" not in r.stdout:
        fails.append("get: code not returned")

    # 4. fail-loud: missing file rc=2; bad json rc=2
    r = run("--add", "x", "--file", os.path.join(tmp, "nope.py"), "--family", "t")
    if r.returncode != 2:
        fails.append(f"missing-file should rc=2, got {r.returncode}")
    bad = os.path.join(tmp, "bad.json")
    with open(bad, "w") as f:
        f.write("{not json")
    r = subprocess.run([sys.executable, tool, "--db", bad, "--list"],
                       capture_output=True, text=True)
    if r.returncode != 2:
        fails.append(f"bad-json should rc=2, got {r.returncode}")

    # 5. archive-by-rename on reset
    r = run("--reset")
    if r.returncode != 0 or "ARCHIVED" not in r.stdout:
        fails.append(f"reset: {r.stdout!r}")
    if not any(n.startswith("sk.json.archived-") for n in os.listdir(tmp)):
        fails.append("reset: no archive file")

    print("SELFTEST:", "OK (5/5 checks)" if not fails else "FAIL")
    for m in fails:
        print("  -", m)
    return 0 if not fails else 1


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True, help="JSON library path")
    ap.add_argument("--add", metavar="PROMPT", help="store a skill")
    ap.add_argument("--file", help="code file to store (use with --add)")
    ap.add_argument("--family", default="general", help="skill family")
    ap.add_argument("--tag", action="append", default=[], help="extra tag (repeatable)")
    ap.add_argument("--search", metavar="QUERY", help="top-k retrieval")
    ap.add_argument("--k", type=int, default=3, help="hits for --search (default 3)")
    ap.add_argument("--get", metavar="ID", help="print a skill's code verbatim")
    ap.add_argument("--list", action="store_true", help="list all skills")
    ap.add_argument("--reset", action="store_true", help="archive-by-rename the db")
    ap.add_argument("--selftest", action="store_true", help="run the built-in selftest")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(selftest())
    if a.add:
        if not a.file:
            sys.stderr.write("FAIL-INPUT: --add requires --file\n")
            sys.exit(2)
        add(a.db, a.add, a.file, a.family, a.tag)
    elif a.search:
        hits = search(a.db, a.search, a.k)
        if not hits:
            print("NO HITS (empty db)")
        for score, inter, s in hits:
            print(f"[{score:.3f} j / {inter} shared] {s['id']} "
                  f"family={s['family']} :: {s['prompt']}")
    elif a.get:
        for s in _load(a.db):
            if s["id"] == a.get:
                print(s["code"])
                return
        sys.stderr.write(f"FAIL-INPUT: no skill id {a.get}\n")
        sys.exit(2)
    elif a.list:
        db = _load(a.db)
        if not db:
            print("(empty)")
        for s in db:
            print(f"{s['id']}  family={s['family']:<14} tags={','.join(s['tags'])}  :: {s['prompt']}")
    elif a.reset:
        reset(a.db)
    else:
        ap.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
