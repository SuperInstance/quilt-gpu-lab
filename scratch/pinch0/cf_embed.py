#!/usr/bin/env python3
"""PINCH0 LANE 2 — embed setup cards via Cloudflare Workers AI bge-m3 (free tier).

Credentials (read at use-time, NEVER echoed / hardcoded / committed):
  1. Live wrangler OAuth token from ~/.wrangler/config/default.toml (auto-refreshed
     by `wrangler whoami` on 401). Scope includes `ai (write)`, account 049ff5e8...
  2. Fallback: CF_API_TOKEN from /mnt/c/Users/casey/key.txt (found INVALID at
     2026-10-02 — 401 "Invalid API Token"; kept only as fallback).

CPU + free-tier cloud only. O(batch) memory. Resume-safe checkpoint per batch.
"""
import json, os, re, struct, subprocess, sys, time, urllib.request, urllib.error

KEYFILE = "/mnt/c/Users/casey/key.txt"
WRANGLER_CFG = os.path.expanduser("~/.wrangler/config/default.toml")
SCRATCH = "/home/eileen/projects/quilt-gpu-lab/scratch/pinch0"
EMBDIR = os.path.join(SCRATCH, "embeddings")
MODEL = "@cf/baai/bge-m3"
DIM = 1024
BATCH = 48
ACCT_CACHE = os.path.join(SCRATCH, ".cf_account")


def _read_kv(path):
    kv = {}
    try:
        with open(path, errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if "=" in line:
                    k, v = line.split("=", 1)
                    kv[k.strip()] = v.strip().strip('"')
    except FileNotFoundError:
        pass
    return kv


def wrangler_token(refresh=False):
    if refresh:
        subprocess.run(["wrangler", "whoami"], capture_output=True, timeout=120)
    return _read_kv(WRANGLER_CFG).get("oauth_token")


def key_token():
    return _read_kv(KEYFILE).get("CF_API_TOKEN")


def token_candidates(force_refresh=False):
    t = wrangler_token(refresh=force_refresh)
    if t:
        yield t
    k = key_token()
    if k:
        yield k


def _req(url, token, data=None, tries=5):
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
            raw = e.read().decode()
            if e.code == 401:
                return 401, raw
            ra = e.headers.get("Retry-After")
            if e.code in (429, 500, 502, 503, 504, 522, 524) and attempt < tries - 1:
                wait = float(ra) if ra and re.fullmatch(r"\d+(\.\d+)?", ra) else min(2 ** attempt, 30)
                time.sleep(wait)
                continue
            return e.code, raw
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < tries - 1:
                time.sleep(min(2 ** attempt, 30))
                continue
            return 0, str(e)
    return 0, "retries exhausted"


def get_token():
    """Return a working token + account id, refreshing OAuth if needed."""
    acct = open(ACCT_CACHE).read().strip() if os.path.exists(ACCT_CACHE) else None
    for force in (False, True):
        for tok in token_candidates(force_refresh=force):
            if acct is None:
                c, j = _req("https://api.cloudflare.com/client/v4/accounts", tok)
                if c != 200 or not (j.get("result") if isinstance(j, dict) else None):
                    continue
                acct = j["result"][0]["id"]
                open(ACCT_CACHE, "w").write(acct)
            url = "https://api.cloudflare.com/client/v4/accounts/%s/ai/run/%s" % (acct, MODEL)
            c, j = _req(url, tok, {"text": ["probe"]})
            if c == 200 and isinstance(j, dict) and j.get("success"):
                return tok, acct
    raise SystemExit("no working Cloudflare credential found (wrangler OAuth + key.txt both failed)")


def embed(texts, token, acct):
    url = "https://api.cloudflare.com/client/v4/accounts/%s/ai/run/%s" % (acct, MODEL)
    c, j = _req(url, token, {"text": texts})
    if c == 401:
        raise AuthError("401")
    if c != 200 or not j.get("success"):
        raise RuntimeError("AI run failed (%s): %s" % (c, json.dumps(j.get("errors") if isinstance(j, dict) else j)[:200]))
    return j["result"]["data"]


class AuthError(Exception):
    pass


def card_text(c):
    s = c.get("setup") or {}
    parts = [c.get("repo", ""), c.get("kind", ""), c.get("purpose", "")]
    parts.append(str(s.get("layout", "")))
    parts.append(str(s.get("build_run", "")))
    ents = s.get("entrypoints") or []
    if ents:
        parts.append("entrypoints: " + ", ".join(map(str, ents)))
    conv = s.get("conventions") or []
    if conv:
        parts.append("conventions: " + ", ".join(map(str, conv)))
    return " | ".join(p for p in parts if p)


def load_cards():
    with open(os.path.join(SCRATCH, "cards.jsonl")) as fh:
        return [json.loads(l) for l in fh if l.strip()]


def run():
    os.makedirs(EMBDIR, exist_ok=True)
    ids_path = os.path.join(EMBDIR, "ids.jsonl")
    vec_path = os.path.join(EMBDIR, "vectors.f32")
    token, acct = get_token()

    cards = load_cards()
    done = 0
    if os.path.exists(ids_path):
        with open(ids_path) as fh:
            done = sum(1 for _ in fh)
    if os.path.exists(vec_path):
        want = done * DIM * 4
        sz = os.path.getsize(vec_path)
        if sz > want:
            with open(vec_path, "r+b") as fh:
                fh.truncate(want)
        elif sz < want:
            raise SystemExit("vector file shorter than index (%d < %d) — abort" % (sz, want))

    failures = []
    n = len(cards)
    i = done
    t0 = time.time()
    while i < n:
        batch = cards[i:i + BATCH]
        texts = [card_text(c) for c in batch]
        try:
            vecs = embed(texts, token, acct)
        except AuthError:
            token, acct = get_token()  # force refresh
            try:
                vecs = embed(texts, token, acct)
            except Exception as e:
                failures.append({"start": i, "error": "auth-retry: %s" % str(e)[:160]})
                i += len(batch)
                continue
        except Exception as e:
            failures.append({"start": i, "error": str(e)[:200]})
            i += len(batch)
            time.sleep(1)
            continue
        if len(vecs) != len(batch):
            failures.append({"start": i, "error": "count mismatch %d!=%d" % (len(vecs), len(batch))})
            i += len(batch)
            continue
        with open(vec_path, "ab") as vf, open(ids_path, "a") as idf:
            for c, v in zip(batch, vecs):
                vf.write(struct.pack("<%df" % DIM, *v))
                idf.write(json.dumps({"repo": c["repo"]}) + "\n")
        i += len(batch)
        if (i // BATCH) % 10 == 0 or i >= n:
            print("embedded %d/%d  (%.0fs)" % (min(i, n), n, time.time() - t0), flush=True)
        time.sleep(0.15)
    if failures:
        with open(os.path.join(EMBDIR, "failures.json"), "w") as fh:
            json.dump(failures, fh, indent=1)
    print("DONE embedded=%d total=%d failures=%d" % (min(i, n), n, len(failures)))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "smoke":
        t, a = get_token()
        v = embed(["smoke test of bge-m3 embedding pipeline for pinch0 lane 2"], t, a)
        print("SMOKE_OK acct=%s... dim=%d n=%d" % (a[:8], len(v[0]), len(v)))
    else:
        run()
