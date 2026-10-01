#!/usr/bin/env python3
"""G1c — seat-vs-instrument verdict routing.

Two arms answer the SAME 96-prompt certified battery blind:
  Arm I  (jev)   : typesafe System One judgment cells, one noul call per claim,
                   threshold 0.5 (fleet PINCH default) -> SUPPORTED/REFUTED
  Arm II (glm)   : z.ai glm-5.3-flash, the EXACT battery text the local seat
                   (qwen2.5:7b Q4_K_M) saw, temp 0, seed 2718.

Blind protocol: `collect` runs with no access to the key file's truth; the
blind key is read ONLY in `score`, after both arms' answers are on disk.

Gates (frozen): JEV arm is KEEP-material iff overall accuracy >= 0.75.
Routing recommendation = cheapest arm >= 0.75 per class.

Secrets law: TYPESAFE_AI_KEY / ZAI_KEY read at use-time from key.txt, carried
to their own service ONLY (auth header via 0600 curl config), never printed.
Seed 2718. Fail loud. Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BATTERY = Path("/home/eileen/projects/fleet-seeds/docs/g1/battery-96.json")
KEY_PATH = ROOT / "results" / "g1" / "battery-96-key.json"
LOCAL_SCORE = ROOT / "results" / "g1" / "run1" / "score.json"
OUT = ROOT / "results" / "g1c"
KEYFILE = "/mnt/c/Users/casey/key.txt"

SEED = 2718
JEV_ENDPOINT = "https://api.typesafe.ai/v1/systemone"
JEV_MODEL = "jev-preview"
JEV_THRESHOLD = 0.5  # fleet PINCH default (CM1-r4/r5)
# The pay-as-you-go paas endpoint answers 429 code 1113 (Insufficient balance);
# the account's live plan is the CODING plan, so the coding base URL is used.
ZAI_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"
ZAI_MODEL = "glm-5.3-flash"

CLASS_RE = re.compile(r"g1b-(\w+)-\d+")
_PRINT_LOCK = threading.Lock()


def log(msg: str) -> None:
    with _PRINT_LOCK:
        print(msg, flush=True)


# ---------------------------------------------------------------- secrets ----
def read_key(name: str) -> str:
    """Read a secret line at use-time; never prints/persists the value."""
    with open(KEYFILE, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith(name):
                v = line.split("=", 1)[1].strip().strip('"').strip("'")
                if v:
                    return v
                raise RuntimeError(f"{name} present but empty")
    raise RuntimeError(f"{name} not found in keyfile")


# ------------------------------------------------------------------ http -----
def curl_json(url: str, body: dict, header: str, timeout_s: float = 120.0):
    """POST json via curl; auth header rides in a 0600 -K config, never argv."""
    curl = shutil.which("curl") or "/usr/bin/curl"
    fd, cfg = tempfile.mkstemp(prefix="g1c_curl_", suffix=".cfg")
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write('header = "%s"\n' % header.replace("\\", "\\\\").replace('"', '\\"'))
    args = [curl, "-sS", "-X", "POST", url, "-H", "Content-Type: application/json",
            "-K", cfg, "--max-time", str(int(timeout_s)),
            "--data-binary", "@-", "-w", "\n__HTTP__%{http_code}"]
    try:
        p = subprocess.run(args, input=json.dumps(body), capture_output=True,
                           text=True, timeout=timeout_s + 30)
    finally:
        if os.path.exists(cfg):
            os.unlink(cfg)
    out = p.stdout or ""
    code = 0
    m = re.search(r"__HTTP__(\d{3})\s*$", out)
    if m:
        code = int(m.group(1))
        out = out[:m.start()].rstrip("\n")
    return code, out


def post_retry(url, body, header, attempts=4, timeout_s=120.0):
    """Retry on transport error / 429 / 5xx with backoff. Returns (code, body)."""
    delay = 2.0
    last = None
    for i in range(attempts):
        try:
            code, out = curl_json(url, body, header, timeout_s=timeout_s)
        except subprocess.TimeoutExpired as e:
            last = f"timeout: {e}"; code, out = 0, ""
        if code == 200:
            return code, out
        last = f"http {code}: {out[:200]}"
        if code in (401, 403):          # auth failure: do not improvise
            return code, out
        if code == 429 or code >= 500 or code == 0:
            # honour Retry-After if present
            m = re.search(r"retry-after['\"]?\s*[:=]\s*(\d+)", out, re.I)
            wait = int(m.group(1)) if m else delay
            time.sleep(min(wait, 30))
            delay = min(delay * 2, 30)
            continue
        return code, out
    return code, out


# ------------------------------------------------------------- arm I: JEV ----
JEV_Q = {
    "claim_holds": {
        "type": "noul",
        "question": (
            "Does the claim as stated hold, given the evidence supplied with it? "
            "Answer true if the claim is factually correct (computation, sequence, "
            "counting, calendar arithmetic, roster/assignment lookup, or logical "
            "consistency all check out); answer false if it is incorrect."
        ),
        "instructions": (
            "Return a graded confidence in [0,1]. Use near 1.0 only when you have "
            "verified the claim is correct. Use near 0.0 when you have verified it "
            "is incorrect or contradicted. Judge the truth of the claim itself, "
            "not the format of any requested reply."
        ),
    }
}


def claim_state(text: str) -> str:
    """Informative body of the battery prompt (drop the reply-format boilerplate)."""
    return text.split("\nReply with ONLY this JSON")[0].strip()


def run_jev(prompts):
    tok = read_key("TYPESAFE_AI_KEY")  # use-time only
    results = {}

    def one(p):
        body = {"model": JEV_MODEL, "state": claim_state(p["text"]),
                "questions": JEV_Q}
        code, out = post_retry(JEV_ENDPOINT, body,
                               f"Authorization: Bearer {tok}", attempts=4, timeout_s=90)
        rec = {"id": p["id"], "http": code, "state_sent": claim_state(p["text"]),
               "raw": out[:2000]}
        if code != 200:
            rec["error"] = f"http {code}"
            return rec
        try:
            data = json.loads(out)
            noul = float(data["answers"]["claim_holds"]["noul"])
            rec["noul"] = noul
            rec["model"] = data.get("model")
            rec["usage"] = data.get("usage")
            rec["verdict"] = "SUPPORTED" if noul >= JEV_THRESHOLD else "REFUTED"
        except Exception as e:  # noqa: BLE001
            rec["error"] = f"parse: {e!r}"
        return rec

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=6) as ex:
        for i, rec in enumerate(ex.map(one, prompts), 1):
            results[rec["id"]] = rec
            if i % 16 == 0 or i == len(prompts):
                log(f"  jev  {i}/{len(prompts)}  ({time.time()-t0:.0f}s)")
    return results


# ------------------------------------------------------------- arm II: GLM ---
def parse_verdict(text: str):
    m = re.search(r'"verdict"\s*:\s*"(SUPPORTED|REFUTED|INSUFFICIENT)"', text)
    if m:
        return m.group(1)
    m = re.search(r"\b(SUPPORTED|REFUTED|INSUFFICIENT)\b", text)
    return m.group(1) if m else None


def run_glm(prompts):
    tok = read_key("ZAI_KEY")  # use-time only
    results = {}
    lock = threading.Lock()
    state = {"ok": 0, "rate": 0, "fail": 0, "last": None}

    def one(p):
        body = {
            "model": ZAI_MODEL,
            "messages": [{"role": "user", "content": p["text"]}],
            "temperature": 0.0,
            "seed": SEED,
            "max_tokens": 2000,
            "stream": False,
        }
        code, out = post_retry(ZAI_URL, body, f"Authorization: Bearer {tok}",
                               attempts=4, timeout_s=180)
        rec = {"id": p["id"], "http": code, "raw": out[:4000]}
        with lock:
            if code == 200:
                state["ok"] += 1
            elif code == 429:
                state["rate"] += 1
            else:
                state["fail"] += 1
            state["last"] = f"{code}"
        if code != 200:
            rec["error"] = f"http {code}"
            return rec
        try:
            data = json.loads(out)
            if "error" in data:
                rec["error"] = f"api: {str(data['error'])[:200]}"
                return rec
            content = data["choices"][0]["message"]["content"]
            rec["content"] = content[:2000]
            rec["verdict"] = parse_verdict(content)
            rec["usage"] = data.get("usage")
        except Exception as e:  # noqa: BLE001
            rec["error"] = f"parse: {e!r}"
        return rec

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=4) as ex:
        for i, rec in enumerate(ex.map(one, prompts), 1):
            results[rec["id"]] = rec
            if i % 16 == 0 or i == len(prompts):
                log(f"  glm  {i}/{len(prompts)}  ok={state['ok']} 429={state['rate']} "
                    f"fail={state['fail']}  ({time.time()-t0:.0f}s)")
    return results


# ---------------------------------------------------------------- scoring ----
def acc(rows, got_key, truth):
    n = c = 0
    for r in rows:
        g = r.get(got_key)
        t = truth[r["id"]]
        n += 1
        c += (g == t)
    return (c / n if n else 0.0), c, n


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)
        f.write("\n")


def cmd_collect(args):
    bat = json.load(open(BATTERY))
    prompts = bat["prompts"]
    log(f"battery {bat['battery_id']}  n={len(prompts)}  (BLIND: key not read)")
    OUT.mkdir(parents=True, exist_ok=True)

    log("Arm I — typesafe JEV judgment cells (noul, thr=0.5)")
    jev = run_jev(prompts)
    write_json(OUT / "arm_jev_raw.json", jev)

    log("Arm II — z.ai glm-5.3-flash (temp 0, seed 2718)")
    glm = run_glm(prompts)
    write_json(OUT / "arm_glm_raw.json", glm)

    # pre-key completion report (no truth involved)
    for name, res in (("jev", jev), ("glm", glm)):
        ok = sum(1 for r in res.values() if r.get("verdict"))
        err = [r["id"] for r in res.values() if not r.get("verdict")]
        log(f"{name}: answered {ok}/{len(prompts)}"
            + (f"  errors={len(err)} {err[:4]}" if err else ""))
    return 0


def cmd_score(args):
    bat = json.load(open(BATTERY))
    prompts = bat["prompts"]
    key = json.load(open(KEY_PATH))["key"]
    truth = {pid: v["expected"] for pid, v in key.items()}

    jev = json.load(open(OUT / "arm_jev_raw.json"))
    glm = json.load(open(OUT / "arm_glm_raw.json"))
    local = json.load(open(LOCAL_SCORE))
    local_got = {r["id"]: r["got"] for r in local["rows"]}

    rows = []
    for p in prompts:
        pid = p["id"]
        j = jev.get(pid, {})
        g = glm.get(pid, {})
        rows.append({
            "id": pid,
            "class": CLASS_RE.match(pid).group(1),
            "truth": truth[pid],
            "truth_text": key[pid]["truth"],
            "local": local_got.get(pid),
            "jev": j.get("verdict"),
            "jev_noul": j.get("noul"),
            "glm": g.get("verdict"),
            "glm_raw_verdict": g.get("verdict"),
            "glm_error": g.get("error"),
            "jev_error": j.get("error"),
        })

    classes = sorted({r["class"] for r in rows})

    def per_class(got_key):
        out = {}
        for c in classes:
            sub = [r for r in rows if r["class"] == c]
            o, k, n = acc(sub, got_key, truth)
            out[c] = {"n": n, "correct": k, "acc": round(o, 4)}
        return out

    # local rows from run1 scoring (authoritative per-class source)
    local_pc = {}
    for c in classes:
        sub = [r for r in local["rows"] if CLASS_RE.match(r["id"]).group(1) == c]
        local_pc[c] = {"n": len(sub),
                       "correct": sum(1 for r in sub if r["correct"]),
                       "acc": round(sum(1 for r in sub if r["correct"]) / len(sub), 4)}

    def overall(got_key):
        o, k, n = acc(rows, got_key, truth)
        return {"correct": k, "n": n, "acc": round(o, 4)}

    # agreement matrix: local vs jev vs glm vs truth
    mat = {}
    def buckets(a, b):
        d = {}
        for r in rows:
            k = f"{r[a]}||{r[b]}"
            d[k] = d.get(k, 0) + 1
        return d
    for a, b in (("local", "truth"), ("jev", "truth"), ("glm", "truth"),
                 ("local", "jev"), ("local", "glm"), ("jev", "glm")):
        mat[f"{a}_vs_{b}"] = buckets(a, b)

    # unanimity / disagreement breakdown
    def n_agree(r):
        return len({r["local"], r["jev"], r["glm"]} & {"SUPPORTED", "REFUTED"})
    disagree = [r for r in rows if len({r["local"], r["jev"], r["glm"]}
                                       - {"SUPPORTED", "REFUTED"}) >
                len({r["local"], r["jev"], r["glm"]} & {"SUPPORTED", "REFUTED"})] \
        if False else [r for r in rows if n_agree(r) >= 2]

    jev_ov = overall("jev")
    glm_ov = overall("glm")
    local_ov = {"correct": sum(1 for r in local["rows"] if r["correct"]),
                "n": len(local["rows"]),
                "acc": round(local["accuracy"], 4)}

    # routing: cheapest arm >= 0.75 per class. cost order local < jev < glm
    routing = {}
    for c in classes:
        cand = [("local", local_pc[c]["acc"]), ("jev", per_class("jev")[c]["acc"]),
                ("glm", per_class("glm")[c]["acc"])]
        passing = [n for n, a in cand if a >= 0.75]
        routing[c] = {"winner": passing[0] if passing else None,
                      "values": dict(cand)}

    # ---- JEV agreement with truth, but noul vs threshold sweep (calibration) --
    sweep = {}
    jev_nouls = [(r["id"], r["jev_noul"], r["truth"]) for r in rows
                 if r["jev_noul"] is not None]
    for thr in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
        c = sum(1 for _, nu, t in jev_nouls
                if ("SUPPORTED" if nu >= thr else "REFUTED") == t)
        sweep[str(thr)] = round(c / len(jev_nouls), 4) if jev_nouls else None

    report = {
        "schema": "g1c-verdict-routing/v1",
        "seed": SEED,
        "battery": bat["battery_id"],
        "jev_model": JEV_MODEL,
        "jev_threshold": JEV_THRESHOLD,
        "glm_model": ZAI_MODEL,
        "overall": {"local": local_ov, "jev": jev_ov, "glm": glm_ov},
        "per_class": {"local": local_pc, "jev": per_class("jev"),
                      "glm": per_class("glm")},
        "jev_noul_threshold_sweep": sweep,
        "agreement_matrix": mat,
        "routing": routing,
        "answered": {
            "jev": sum(1 for r in jev.values() if r.get("verdict")),
            "glm": sum(1 for r in glm.values() if r.get("verdict")),
            "n": len(prompts),
        },
        "rows": rows,
    }
    write_json(OUT / "score_g1c.json", report)

    # ---- console summary --------------------------------------------------
    log("\n=== G1c route table ===")
    log(f"{'class':8s} {'local':>7s} {'jev':>7s} {'glm':>7s}   winner")
    for c in classes:
        log(f"{c:8s} {local_pc[c]['acc']:7.4f} {per_class('jev')[c]['acc']:7.4f} "
            f"{per_class('glm')[c]['acc']:7.4f}   {routing[c]['winner']}")
    log(f"{'OVERALL':8s} {local_ov['acc']:7.4f} {jev_ov['acc']:7.4f} "
        f"{glm_ov['acc']:7.4f}")
    log(f"\nJEV gate (>=0.75): {'PASS' if jev_ov['acc']>=0.75 else 'FAIL'}")
    log(f"JEV noul sweep: {sweep}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["collect", "score"])
    a = ap.parse_args()
    return cmd_collect(a) if a.phase == "collect" else cmd_score(a)


if __name__ == "__main__":
    sys.exit(main())
