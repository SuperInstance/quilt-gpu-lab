#!/usr/bin/env python3
"""skill_store -- grabbable Voyager-style verified-skill library (stdlib-only).

Pattern lifted from experiments/skill_library.py (VOYAGER-SKILLLIB, arXiv:2305.16291;
folded 2026-10-02, purity 39/39, retrieval PASS): a JSON-backed store of *verified*
code skills -- prompt + code + family tags -- with deterministic retrieval.
Store only what passed your verifier; retrieval gives top-k reuse candidates for
a new prompt.

RETRIEVAL (2026-10-02 upgrade -- semantic default, Jaccard fallback)
-------------------------------------------------------------------
Two-stage, credential-free-at-rest:

  * store time: the skill's name+description+when-to-use text
    (`prompt | when_to_use | family | tags`) is embedded once with
    Cloudflare Workers AI `@cf/baai/bge-m3` (1024-d) and the vector is cached
    inside the skill record under `vector` (written with the record via the same
    atomic temp+fsync+rename path). If CF is unreachable the record is written
    with `vector: null` and the store continues -- a write is NEVER blocked on
    the network. `--embed` backfills missing vectors later (resume-safe: it
    skips records that already carry one).

  * search time: the query is embedded once and ranked by cosine. If embeddings
    are unavailable (no network / no cached vectors / `--no-semantic`), retrieval
    falls back to token-overlap Jaccard transparently and the output line marks
    the mode.

EXACT RANKING FUNCTION (documented contract)
--------------------------------------------
For a query q over candidate skills S, with q's token set `qt`, query vector
`qv` (or None), candidate token set `st` and cached vector `sv`:

    inter  = |qt & st|
    jacc   = inter / |qt | st|                 (0.0 when the union is empty)
    cos    = qv . sv / (||qv|| ||sv||)         iff qv is not None, sv is a
                                               cached 1024-d vector, and the
                                               blended mode is active; else None

    rank_key(s) = (has_cos, cos, jacc, inter, -id)     sorted descending,
                  where has_cos = 1 iff cos is not None else 0.

Blend rule: **cosine similarity is primary; Jaccard token overlap is the
tiebreak signal** (used to order candidates whose cosine is identically equal,
and as the sole score when embeddings are unavailable). Records without a cached
vector sort below vector-bearing records while semantic mode is active
(has_cos=0 < 1) but are still returned with their Jaccard score -- never dropped.
When the query vector is unavailable, `has_cos = 0` for every record and the
ordering collapses *exactly* to the pre-upgrade deterministic Jaccard ranking
(same scores, same tiebreaks, same ids). Determinism: same db + query + mode ->
same ranking; no seeds, no randomness.

Credentials for CF are read at use time and are NEVER echoed, hardcoded, or
committed: env `CF_API_TOKEN` -> `/mnt/c/Users/casey/key.txt` (`CF_API_TOKEN=`)
-> the machine's wrangler OAuth token (`~/.wrangler/config/default.toml`), with
an automatic `wrangler whoami` refresh on 401. Every error string is scrubbed of
any credential that was read. Reinstatement order may be reversed in situ --
this module just rotates candidates on 401.

Design laws carried over from the experiment:
    - the library stores ONLY what you explicitly add (verification is the caller's
      gate -- run your tests before --add; this tool never judges code itself)
    - retrieval is deterministic and seeded-free: same db + query -> same ranking
    - atomic writes (temp + fsync + rename); archive-by-rename for --reset
    - fail loud: bad JSON db, missing code file, empty query -> rc=2, no silent fixes
    - O(batch) memory: nothing larger than a 48-text embed batch is buffered at once

Usage:
    python3 tools/skill_store.py --db skills.json --add "reverse words in a string" \
        --file my_skill.py --family text --tag string [--when "use when input is a sentence"]
    python3 tools/skill_store.py --db skills.json --search "capitalize each word" --k 3
    python3 tools/skill_store.py --db skills.json --search "..." --no-semantic   # Jaccard control
    python3 tools/skill_store.py --db skills.json --embed      # backfill missing vectors
    python3 tools/skill_store.py --db skills.json --list
    python3 tools/skill_store.py --db skills.json --get <id>
    python3 tools/skill_store.py --db skills.json --reset
    python3 tools/skill_store.py --db skills.json --selftest   # hermetic (offline) checks

Worked example (self-contained):
    $ cat > cap.py <<'EOF'
    def solve(s):
        return " ".join(w.capitalize() for w in s.split())
    EOF
    $ python3 tools/skill_store.py --db /tmp/sk.json --add "title case a sentence" \
        --file cap.py --family text --when "use when you must capitalize each word"
    $ python3 tools/skill_store.py --db /tmp/sk.json --search "capitalise sentence words"
    -> MODE: semantic ...  top hit: title case a sentence (family text)

Exit codes: 0 ok, 2 fail-loud input error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request

STOP = set("a an and as at be by for from in into is it of on or that the to with".split())

# ---------------------------------------------------------------- CF embeddings
CF_MODEL = "@cf/baai/bge-m3"
CF_DIM = 1024
CF_BATCH = 48
_KEYFILE = os.environ.get("SKILL_STORE_KEYFILE", "/mnt/c/Users/casey/key.txt")
_WRANGLER_CFG = os.path.expanduser("~/.wrangler/config/default.toml")
_CF_BASE = os.environ.get("SKILL_STORE_CF_BASE", "https://api.cloudflare.com/client/v4")
_CACHE_DIR = os.environ.get(
    "SKILL_STORE_CACHE_DIR", os.path.join(os.path.expanduser("~"), ".cache", "skill_store"))

# credentials read at use time; remembered only so error text can be scrubbed
_SECRETS: set = set()


def _note_secret(tok):
    if tok and len(tok) > 6:
        _SECRETS.add(tok)


def _scrub(text):
    """Remove any credential material that passed through this process."""
    s = str(text)
    for sec in _SECRETS:
        if sec:
            s = s.replace(sec, "<redacted>")
    return s


def _kv(path):
    kv = {}
    try:
        with open(path, errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    kv[k.strip()] = v.strip().strip('"')
    except OSError:
        pass
    return kv


def _wrangler_token(refresh=False):
    if os.environ.get("SKILL_STORE_NO_WRANGLER"):
        return None
    if refresh:
        import subprocess
        try:
            subprocess.run(["wrangler", "whoami"], capture_output=True, timeout=180)
        except (OSError, subprocess.SubprocessError):
            pass
    return _kv(_WRANGLER_CFG).get("oauth_token")


def _candidate_tokens(refresh=False):
    """Yield (label, token) in credential-chain order. Never logs the token."""
    t = os.environ.get("CF_API_TOKEN")
    if t:
        _note_secret(t)
        yield "env:CF_API_TOKEN", t
    t = _kv(_KEYFILE).get("CF_API_TOKEN")
    if t:
        _note_secret(t)
        yield "keyfile:CF_API_TOKEN", t
    t = _wrangler_token(refresh=refresh)
    if t:
        _note_secret(t)
        yield "wrangler:oauth", t


def _http_json(url, token, data=None, tries=None):
    """Return (code, obj_or_text). 401 returns immediately for token rotation."""
    if tries is None:
        try:
            tries = max(1, int(os.environ.get("SKILL_STORE_HTTP_TRIES", "4")))
        except ValueError:
            tries = 4
    body = json.dumps(data).encode() if data is not None else None
    for attempt in range(tries):
        req = urllib.request.Request(url, data=body)
        req.add_header("Authorization", "Bearer " + token)
        if body:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return 200, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")
            if e.code == 401:
                return 401, raw
            ra = e.headers.get("Retry-After") if e.headers else None
            if e.code in (429, 500, 502, 503, 504, 522, 524) and attempt < tries - 1:
                wait = float(ra) if ra and re.fullmatch(r"\d+(\.\d+)?", ra) else min(2 ** attempt, 30)
                time.sleep(wait)
                continue
            return e.code, raw
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt < tries - 1:
                time.sleep(min(2 ** attempt, 8))
                continue
            return 0, _scrub(e)
    return 0, "retries exhausted"


def _cached_account():
    p = os.path.join(_CACHE_DIR, "cf_account")
    try:
        with open(p) as fh:
            return fh.read().strip() or None
    except OSError:
        return None


def _cache_account(acct):
    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        tmp = os.path.join(_CACHE_DIR, ".acct.tmp")
        with open(tmp, "w") as fh:
            fh.write(acct)
        os.replace(tmp, os.path.join(_CACHE_DIR, "cf_account"))
    except OSError:
        pass


def _account_for(token):
    acct = _cached_account()
    if acct:
        return acct
    code, obj = _http_json(_CF_BASE + "/accounts", token)
    if code == 200 and isinstance(obj, dict) and obj.get("result"):
        acct = obj["result"][0]["id"]
        _cache_account(acct)
        return acct
    return None


def embed_texts(texts):
    """Embed a batch of texts. Returns (vectors | None, reason | None).

    None vectors mean embeddings are UNAVAILABLE (offline / no credential /
    CF error); callers must fall back, never crash and never block a write.
    Reason is a scrubbed human string. O(batch) memory: chunks of CF_BATCH.
    """
    if os.environ.get("SKILL_STORE_NO_EMBED"):
        return None, "disabled by SKILL_STORE_NO_EMBED (offline simulation)"
    if not texts:
        return [], None
    payload = [t if t and t.strip() else "(empty)" for t in texts]
    url_tmpl = _CF_BASE + "/accounts/%s/ai/run/" + CF_MODEL
    reason = "no working credential"
    for refresh in (False, True):
        for label, tok in _candidate_tokens(refresh=refresh):
            acct = _account_for(tok)
            if not acct:
                reason = "could not resolve Cloudflare account (%s)" % label
                continue
            url = url_tmpl % acct
            out = []
            ok = True
            for i in range(0, len(payload), CF_BATCH):
                code, obj = _http_json(url, tok, {"text": payload[i:i + CF_BATCH]})
                if code == 401:
                    reason = "credential rejected (401) using %s" % label
                    ok = False
                    break
                if code != 200 or not isinstance(obj, dict) or not obj.get("success"):
                    detail = ""
                    if isinstance(obj, dict):
                        detail = json.dumps(obj.get("errors") or obj)[:160]
                    else:
                        detail = str(obj)[:160]
                    reason = "CF AI error (code=%s) using %s: %s" % (code, label, detail)
                    ok = False
                    break
                out.extend(obj["result"]["data"])
            if ok and len(out) == len(payload):
                return out, None
        # first pass exhausted -> refresh OAuth and loop once more
    return None, _scrub(reason)


def _cosine(a, b):
    if not a or not b or len(a) != len(b):
        return None
    dot = na = nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0.0 or nb <= 0.0:
        return None
    return dot / math.sqrt(na * nb)


# ---------------------------------------------------------------- token overlap
def _tokens(text: str) -> set:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in STOP and len(w) > 1}


def skill_text(prompt, when, family, tags) -> str:
    """The text embedded for a skill: name+description+when-to-use (+family/tags)."""
    parts = [str(prompt or ""), str(when or ""), str(family or ""), " ".join(tags or [])]
    return " | ".join(p for p in parts if p.strip())


def _vec_ok(v):
    return isinstance(v, list) and len(v) == CF_DIM and all(isinstance(x, (int, float)) for x in v)


# ---------------------------------------------------------------- db io
def _load(db_path: str) -> list:
    if not os.path.exists(db_path):
        return []
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        sys.stderr.write(_scrub(f"FAIL-INPUT: cannot read db {db_path}: {e}\n"))
        sys.exit(2)
    if not isinstance(data, list):
        sys.stderr.write(_scrub(f"FAIL-INPUT: db {db_path} is not a JSON list\n"))
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


# ---------------------------------------------------------------- store
def add(db_path: str, prompt: str, code_path: str, family: str, tags: list,
        when: str = "") -> dict:
    if not prompt.strip():
        sys.stderr.write("FAIL-INPUT: empty prompt\n")
        sys.exit(2)
    if not os.path.isfile(code_path):
        sys.stderr.write(_scrub(f"FAIL-INPUT: code file not found: {code_path}\n"))
        sys.exit(2)
    with open(code_path, "r", encoding="utf-8") as f:
        code = f.read()
    db = _load(db_path)
    h = hashlib.sha256((prompt + "\0" + code).encode()).hexdigest()[:12]
    for s in db:
        if s.get("id") == h:
            print(f"DUPLICATE: skill {h} already in db (nothing written)")
            return s
    tags = sorted({t.strip() for t in tags if t.strip()})
    when = (when or "").strip()
    entry = {
        "id": h,
        "prompt": prompt.strip(),
        "when_to_use": when,
        "code": code,
        "family": family.strip() or "general",
        "tags": tags,
        "tokens": sorted(_tokens(skill_text(prompt, when, family, tags))),
        "vector": None,  # cached bge-m3 vector; None until embedded
        "added": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    # embed now; NEVER block the write on the network
    vecs, _reason = embed_texts([skill_text(prompt, when, family, tags)])
    if vecs and _vec_ok(vecs[0]):
        entry["vector"] = [round(float(x), 6) for x in vecs[0]]
    db.append(entry)
    _save(db_path, db)
    vtag = "vec=%d" % len(entry["vector"]) if entry["vector"] else "vec=none"
    print(f"STORED {h} family={entry['family']} tokens={len(entry['tokens'])} {vtag}")
    return entry


def embed_missing(db_path: str, k_batch: int = CF_BATCH) -> dict:
    """Backfill vectors for records lacking one. Resume-safe: skips cached."""
    db = _load(db_path)
    todo = [s for s in db if not _vec_ok(s.get("vector"))]
    skipped = len(db) - len(todo)
    if not todo:
        print(f"EMBED: 0 pending, {skipped} already cached (nothing to do)")
        return {"embedded": 0, "skipped": skipped, "failed": 0, "reason": None}
    embedded = 0
    reason = None
    for i in range(0, len(todo), k_batch):
        batch = todo[i:i + k_batch]
        texts = [skill_text(s.get("prompt"), s.get("when_to_use"), s.get("family"), s.get("tags")) for s in batch]
        vecs, reason = embed_texts(texts)
        if not vecs:
            reason = reason or "embeddings unavailable"
            break
        for s, v in zip(batch, vecs):
            if _vec_ok(v):
                s["vector"] = [round(float(x), 6) for x in v]
                embedded += 1
        _save(db_path, db)  # checkpoint per batch -> resume-safe
    failed = len(todo) - embedded
    print(f"EMBED: {embedded} embedded, {skipped} already cached, {failed} pending"
          + (f"  (stopped: {reason})" if failed and reason else ""))
    return {"embedded": embedded, "skipped": skipped, "failed": failed, "reason": reason}


# ---------------------------------------------------------------- search
def search(db_path: str, query: str, k: int, no_semantic: bool = False) -> dict:
    """Rank candidates. See module docstring for the exact rank_key contract.

    Returns {"mode": "semantic"|"jaccard"|"jaccard-fallback", "reason": str|None,
             "rows": [ {entry, cos, jac, inter}, ... ]}
    """
    qt = _tokens(query)
    if not qt:
        sys.stderr.write("FAIL-INPUT: empty/stopword-only query\n")
        sys.exit(2)
    db = _load(db_path)

    qvec = None
    mode, reason = "jaccard", None
    if no_semantic:
        mode, reason = "jaccard", "semantic disabled by --no-semantic"
    else:
        qvecs, err = embed_texts([query])
        if qvecs:
            qvec = qvecs[0]
            mode, reason = "semantic", None
        else:
            mode, reason = "jaccard-fallback", (err or "embeddings unavailable")

    rows = []
    for s in db:
        st = set(s.get("tokens", []))
        inter = len(qt & st)
        jac = inter / len(qt | st) if (qt | st) else 0.0
        cos = None
        if qvec is not None:
            cos = _cosine(qvec, s.get("vector"))
        has_cos = 1 if cos is not None else 0
        rows.append({"entry": s, "cos": cos, "jac": jac, "inter": inter,
                     "key": (has_cos, cos if cos is not None else 0.0, jac, inter)})
    rows.sort(key=lambda r: (-r["key"][0], -r["key"][1], -r["key"][2], -r["key"][3],
                             r["entry"].get("id", "")))
    return {"mode": mode, "reason": reason, "rows": rows[:k]}


def _print_hits(res: dict) -> None:
    tag = res["mode"].upper()
    if res["mode"] == "semantic":
        print("MODE: semantic (bge-m3 cosine primary, Jaccard tiebreak)")
    else:
        print("MODE: %s (%s)" % (tag, res["reason"]))
    if not res["rows"]:
        print("NO HITS (empty db)")
    for r in res["rows"]:
        s = r["entry"]
        if r["cos"] is not None:
            metric = "%.4f cos / %.3f jac" % (r["cos"], r["jac"])
        else:
            metric = "%.3f jac / %d shared" % (r["jac"], r["inter"])
        print(f"[{metric}] {s['id']} family={s['family']} :: {s['prompt']}")


def reset(db_path: str) -> None:
    if os.path.exists(db_path):
        arch = db_path + ".archived-" + time.strftime("%Y%m%d-%H%M%S")
        os.replace(db_path, arch)
        print(f"ARCHIVED db -> {arch}")
    else:
        print("db absent; nothing to archive")


# ---------------------------------------------------------------- selftest
def selftest() -> int:
    import subprocess
    here = os.path.dirname(os.path.abspath(__file__))
    tool = os.path.join(here, "skill_store.py")
    tmp = tempfile.mkdtemp(prefix="skill_store_test_")
    db = os.path.join(tmp, "sk.json")
    fails = []
    env = dict(os.environ, SKILL_STORE_NO_EMBED="1")  # hermetic: force offline Jaccard

    def run(*args):
        return subprocess.run([sys.executable, tool, "--db", db] + list(args),
                              capture_output=True, text=True, env=env)

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

    # 2. search ranks the right skill top-1 (deterministic) + marks fallback
    r = run("--search", "convert text to upper case", "--k", "1")
    if r.returncode != 0 or "uppercase a string" not in r.stdout:
        fails.append(f"search: rc={r.returncode} out={r.stdout!r} err={r.stderr!r}")
    if "JACCARD-FALLBACK" not in r.stdout.upper():
        fails.append(f"search: fallback mode not marked: {r.stdout!r}")

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
                       capture_output=True, text=True, env=env)
    if r.returncode != 2:
        fails.append(f"bad-json should rc=2, got {r.returncode}")

    # 5. archive-by-rename on reset
    r = run("--reset")
    if r.returncode != 0 or "ARCHIVED" not in r.stdout:
        fails.append(f"reset: {r.stdout!r}")
    if not any(n.startswith("sk.json.archived-") for n in os.listdir(tmp)):
        fails.append("reset: no archive file")

    # 6. vector=None on offline store (network never blocks a write)
    db2 = os.path.join(tmp, "sk2.json")
    f2 = os.path.join(tmp, "u.py")
    with open(f2, "w") as f:
        f.write("def solve(s):\n    return s.lower()\n")
    r = subprocess.run([sys.executable, tool, "--db", db2, "--add", "downcase text",
                        "--file", f2, "--family", "text"],
                       capture_output=True, text=True, env=env)
    if r.returncode != 0 or "STORED" not in r.stdout or "vec=none" not in r.stdout:
        fails.append(f"offline-store: rc={r.returncode} out={r.stdout!r}")
    if json.load(open(db2))[0].get("vector") is not None:
        fails.append("offline-store: vector should be None")

    total = 6
    print("SELFTEST:", "OK (%d/%d checks)" % (total, total) if not fails else "FAIL")
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
    ap.add_argument("--when", default="", help="when-to-use text (embedded with the skill)")
    ap.add_argument("--tag", action="append", default=[], help="extra tag (repeatable)")
    ap.add_argument("--search", metavar="QUERY", help="top-k retrieval")
    ap.add_argument("--k", type=int, default=3, help="hits for --search (default 3)")
    ap.add_argument("--no-semantic", action="store_true",
                    help="force Jaccard-only retrieval (control path)")
    ap.add_argument("--embed", action="store_true", help="backfill missing vectors")
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
        add(a.db, a.add, a.file, a.family, a.tag, a.when)
    elif a.search:
        _print_hits(search(a.db, a.search, a.k, no_semantic=a.no_semantic))
    elif a.embed:
        embed_missing(a.db)
    elif a.get:
        for s in _load(a.db):
            if s["id"] == a.get:
                print(s["code"])
                return
        sys.stderr.write(_scrub(f"FAIL-INPUT: no skill id {a.get}\n"))
        sys.exit(2)
    elif a.list:
        db = _load(a.db)
        if not db:
            print("(empty)")
        for s in db:
            v = "vec=%d" % len(s["vector"]) if _vec_ok(s.get("vector")) else "vec=none"
            print(f"{s['id']}  family={s['family']:<14} {v:<11} "
                  f"tags={','.join(s['tags'])}  :: {s['prompt']}")
    elif a.reset:
        reset(a.db)
    else:
        ap.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
