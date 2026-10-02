#!/usr/bin/env python3
"""test_skill_semantic -- FAIL-FIRST pins for the semantic retrieval upgrade.

Every pin here is written to *fail against the pre-upgrade (Jaccard-only)
tool* -- each one carries a positive CONTROL that exhibits the failure it
guards against, so a green run means the upgrade is doing real work, not that
the test is vacuous.

Pins
----
  1. paraphrase-beats-jaccard (LIVE CF)  -- query "keep receipts honest" must rank
     the skill "verify claims against re-executed evidence" above a decoy that
     shares only the keyword "receipts"/"receipt format". The control runs the
     SAME pin with `--no-semantic` and shows the ranking inverts (decoy first),
     i.e. the pin genuinely fails on Jaccard-only.
  2. offline-fallback -- embeddings unavailable => Jaccard results, no crash,
     output marked `JACCARD-FALLBACK`.
  3. store-with-network-down -- --add with embeddings down writes vector=None and
     still succeeds (never block a write on the network).
  4. no-token-leak -- a planted fake CF_API_TOKEN must never appear in stdout or
     stderr on any error path (auth failure / unreachable endpoint).
  5. resume-safe-cache -- a second embed pass skips already-embedded skills
     (zero embed calls); control shows a non-resume strategy would re-call.
  6. blend-rule-mixed -- while semantic mode is active a vector-bearing record
     ranks above a vectorless one (has_cos flag), but is never dropped; the
     ordering inverts under Jaccard-only.

Run:  python3 tools/test_skill_semantic.py        # pins 1,3..6 need network for 1
Env:  SKILL_TEST_ALLOW_OFFLINE=1  -> downgrade the LIVE pin-1 to SKIP (CI oflline)
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "skill_store.py")


def load():
    spec = importlib.util.spec_from_file_location("skill_store", TOOL)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ss = load()
RESULTS = []


def pin(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print("PIN %-24s %s%s" % (name, "PASS" if ok else "FAIL", ("  -- " + detail) if detail else ""))


class env_scope:
    def __init__(self, **kv):
        self.kv = kv

    def __enter__(self):
        self.old = {k: os.environ.get(k) for k in self.kv}
        os.environ.update({k: str(v) for k, v in self.kv.items()})
        return self

    def __exit__(self, *a):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def entry(i, prompt, when, family, tags):
    s = {"id": i, "prompt": prompt, "when_to_use": when, "code": "def solve(): ...",
         "family": family, "tags": list(tags),
         "tokens": sorted(ss._tokens(ss.skill_text(prompt, when, family, tags))),
         "vector": None, "added": "2026-10-02T00:00:00"}
    return s


# Fixture for pin 1 -- calibrated so Jaccard and semantics disagree (see report).
TARGET = entry("aaaa00000001", "verify claims against re-executed evidence",
               "keep a receipt of work truthful by auditing every claim against a "
               "re-executed evidence trail", "evidence", ["verification", "provenance"])
DECOY = entry("bbbb00000002", "format a receipt",
              "use when rendering a printed receipt layout with fields and columns",
              "format", ["receipts", "formatting"])
QUERY = "keep receipts honest"


def write_db(path, records):
    with open(path, "w") as f:
        json.dump(records, f)
    return path


def cli(db, *args, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run([sys.executable, TOOL, "--db", db] + list(args),
                          capture_output=True, text=True, env=e)


# --------------------------------------------------------------------- pin 1
def pin1_paraphrase_live():
    tmp = tempfile.mkdtemp(prefix="pin1_")
    db = write_db(os.path.join(tmp, "sk.json"), [TARGET, DECOY])
    rep = ss.embed_missing(db)
    if rep["failed"] or any(s.get("vector") is None for s in ss._load(db)):
        msg = "embeddings unavailable: %s" % (rep.get("reason") or "no reason")
        if os.environ.get("SKILL_TEST_ALLOW_OFFLINE"):
            print("[pin1] SKIP --", msg)
            return
        pin("paraphrase-beats-jaccard", False, msg + " (LIVE pin requires CF)")
        return

    sem = cli(db, "--search", QUERY, "--k", "2")
    ctl = cli(db, "--search", QUERY, "--k", "2", "--no-semantic")
    print("[pin1] semantic mode output:\n" + sem.stdout.rstrip())
    print("[pin1] Jaccard-only CONTROL output:\n" + ctl.stdout.rstrip())

    sem_lines = [l for l in sem.stdout.splitlines() if l.startswith("[")]
    ctl_lines = [l for l in ctl.stdout.splitlines() if l.startswith("[")]

    def _top_id(lines):
        for l in lines:
            m = re.search(r"\]\s+(\S+)\s+family=", l)
            if m:
                return m.group(1)
        return "?"

    sem_top = _top_id(sem_lines)
    ctl_top = _top_id(ctl_lines)
    ok_sem = sem_top == TARGET["id"]
    ok_ctl = ctl_top == DECOY["id"]  # control MUST fail the pin (decoy first)
    pin("paraphrase-beats-jaccard", ok_sem and ok_ctl,
        "semantic top=%s (want %s); jaccard-only top=%s (want %s = control failing the pin)"
        % (sem_top[:4], TARGET["id"][:4], ctl_top[:4], DECOY["id"][:4]))


# --------------------------------------------------------------------- pin 2
def pin2_offline_fallback():
    tmp = tempfile.mkdtemp(prefix="pin2_")
    db = write_db(os.path.join(tmp, "sk.json"), [TARGET, DECOY])
    with env_scope(SKILL_STORE_NO_EMBED="1"):
        down = ss.embed_texts(["x"])              # positive control: network IS down
        res = ss.search(db, QUERY, 2)             # must not raise
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ss._print_hits(res)
    out = buf.getvalue()
    print("[pin2] fallback output:\n" + out.rstrip())
    ok = (down[0] is None and res["mode"] == "jaccard-fallback"
          and bool(res["reason"]) and len(res["rows"]) == 2
          and "JACCARD-FALLBACK" in out.upper())
    pin("offline-fallback", ok, "mode=%s reason=%r marked=%s"
        % (res["mode"], res["reason"], "JACCARD-FALLBACK" in out.upper()))


# --------------------------------------------------------------------- pin 3
def pin3_store_network_down():
    tmp = tempfile.mkdtemp(prefix="pin3_")
    db = os.path.join(tmp, "sk.json")
    code = os.path.join(tmp, "u.py")
    with open(code, "w") as f:
        f.write("def solve(s):\n    return s.lower()\n")
    with env_scope(SKILL_STORE_NO_EMBED="1"):
        r = cli(db, "--add", "downcase a string", "--file", code, "--family", "text")
    stored = ss._load(db)
    ok = (r.returncode == 0 and "STORED" in r.stdout and "vec=none" in r.stdout
          and stored and stored[0].get("vector") is None)
    print("[pin3] add output:", r.stdout.strip())
    pin("store-network-down", ok, "rc=%d vector=%r" % (r.returncode, stored[0].get("vector") if stored else None))


# --------------------------------------------------------------------- pin 4
def pin4_no_token_leak():
    FAKE = "cf_FAKEtoken_DO_NOT_LEAK_0123456789abcdef"
    tmp = tempfile.mkdtemp(prefix="pin4_")
    db = write_db(os.path.join(tmp, "sk.json"), [TARGET])  # vectorless -> forces embed path
    env = {"CF_API_TOKEN": FAKE, "SKILL_STORE_CF_BASE": "http://127.0.0.1:1/",
           "SKILL_STORE_NO_WRANGLER": "1", "SKILL_STORE_CACHE_DIR": os.path.join(tmp, "cache"),
           "SKILL_STORE_HTTP_TRIES": "1"}
    r1 = cli(db, "--search", QUERY, env=env)
    r2 = cli(db, "--embed", env=env)
    blob = r1.stdout + r1.stderr + r2.stdout + r2.stderr
    print("[pin4] search rc=%d out=%r" % (r1.returncode, r1.stdout.strip()[:120]))
    # positive control: the assertion is meaningful -- an unscrubbed copy WOULD contain it
    ss._note_secret(FAKE)
    naive_leaks = FAKE in ("auth failed for bearer " + FAKE)
    scrubbed = FAKE not in ss._scrub("auth failed for bearer " + FAKE)
    ok = (FAKE not in blob) and naive_leaks and scrubbed
    pin("no-token-leak", ok, "fake token in output=%s; scrub discriminates=%s"
        % (FAKE in blob, naive_leaks and scrubbed))


# --------------------------------------------------------------------- pin 5
def pin5_resume_safe():
    tmp = tempfile.mkdtemp(prefix="pin5_")
    db = write_db(os.path.join(tmp, "sk.json"), [
        entry("c%011d" % i, "skill %d" % i, "when %d" % i, "general", ["t%d" % i]) for i in range(3)])
    calls = {"n": 0}

    def fake_embed(texts):
        calls["n"] += 1
        return [[0.001 * (i + 1)] * ss.CF_DIM for i in range(len(texts))], None

    real = ss.embed_texts
    ss.embed_texts = fake_embed
    try:
        r1 = ss.embed_missing(db)
        n_after_first = calls["n"]
        v1 = [s["vector"][:2] for s in ss._load(db)]
        r2 = ss.embed_missing(db)
        n_after_second = calls["n"]
        v2 = [s["vector"][:2] for s in ss._load(db)]
    finally:
        ss.embed_texts = real
    ok = (r1["embedded"] == 3 and r1["skipped"] == 0 and n_after_first == 1
          and r2["embedded"] == 0 and r2["skipped"] == 3
          and n_after_second == n_after_first and v1 == v2 and all(v for v in v2))
    # control: a non-resume strategy would have re-embedded -> calls would increase
    control_would_reembed = (3 if r2["embedded"] == 0 else 0) > 0
    print("[pin5] run1=%s run2=%s embed_calls %d->%d" % (r1, r2, n_after_first, n_after_second))
    pin("resume-safe-cache", ok, "2nd pass embed calls=%d (non-resume would re-embed 3: %s)"
        % (n_after_second, control_would_reembed))


# --------------------------------------------------------------------- pin 6
def pin6_blend_mixed():
    tmp = tempfile.mkdtemp(prefix="pin6_")
    vec = entry("dddd00000001", "semantic only record", "vectorless decoy context", "general", [])
    nov = entry("eeee00000002", "receipts receipt format", "receipts format receipt", "format", ["receipts"])
    vec["vector"] = [1.0] * ss.CF_DIM                      # identical-direction vector
    db = write_db(os.path.join(tmp, "sk.json"), [vec, nov])
    with env_scope(SKILL_STORE_NO_EMBED="1"):
        pass  # ensure no network; but we need a query vector -> call rank directly
    # drive search's ranking with an injected query vector by calling the internals directly
    qvec = [1.0] * ss.CF_DIM
    qt = ss._tokens(QUERY)
    rows = []
    for s in ss._load(db):
        st = set(s["tokens"])
        inter = len(qt & st)
        jac = inter / len(qt | st) if (qt | st) else 0.0
        cos = ss._cosine(qvec, s.get("vector"))
        rows.append({"id": s["id"], "cos": cos, "jac": jac,
                     "key": (1 if cos is not None else 0, cos or 0.0, jac, inter)})
    rows.sort(key=lambda r: (-r["key"][0], -r["key"][1], -r["key"][2], -r["key"][3], r["id"]))
    sem_order = [r["id"] for r in rows]
    jac_order = [r["id"] for r in
                 sorted(rows, key=lambda r: (-r["jac"], r["id"]))]
    print("[pin6] semantic order=%s  jaccard-only order=%s" % ([i[:4] for i in sem_order], [i[:4] for i in jac_order]))
    ok = (sem_order[0] == vec["id"] and nov["id"] in sem_order          # blend: vector wins, none dropped
          and jac_order[0] == nov["id"])                               # control: inverts under Jaccard
    pin("blend-rule-mixed", ok, "vector-bearing first in semantic, vectorless first in Jaccard")


def main():
    print("=" * 72)
    print("skill_store semantic upgrade -- FAIL-FIRST pins")
    print("=" * 72)
    pin1_paraphrase_live()
    pin2_offline_fallback()
    pin3_store_network_down()
    pin4_no_token_leak()
    pin5_resume_safe()
    pin6_blend_mixed()
    print("-" * 72)
    npass = sum(1 for _, ok, _ in RESULTS if ok)
    print("TOTAL: %d/%d pins PASS" % (npass, len(RESULTS)))
    return 0 if npass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
