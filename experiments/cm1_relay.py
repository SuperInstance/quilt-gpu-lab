#!/usr/bin/env python3
"""CM1 cell-mesh round 1 — frozen per proposals/runs/CM1-cell-mesh-plan.md.
Cells: GEN=qwen2.5:0.5b (Ollama), JUDGE=jev-preview (typesafe graded noul),
PROJECT=nomic-embed-text (Ollama). Arms A (ungated) vs B (gated relay).
Pure stdlib; no ledger calls (parent books after the run)."""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error

LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(LAB, "results", "cm1")
OUT_JSON = os.path.join(OUT_DIR, "round_001_out.json")
JSONL = os.path.join(OUT_DIR, "rounds.jsonl")
OLLAMA = "http://127.0.0.1:11434"
TSAFE = "https://api.typesafe.ai/v1/systemone"
TOKEN_FILE = os.path.expanduser("~/.config/typesafe/token")
PINCH = 0.5

RULE = """Rule: domain = engine if the report mentions engine terms (temp rising/falling, oil, fuel, rpm); else navigation if it mentions motion terms (blob moving, course drift, AIS contact); else deck.
urgency = high if any hazard term (rising, falling, dropping, leak, fire) or two+ domains are implicated; else mid if any motion term; else low."""

STIMULI = [
    ("S1", "Camera frame: three blobs, one moving left at 0.4 units per second. Engine readings steady. Deck clear.", "BOOK:navigation:mid"),
    ("S2", "Engine temp rising 2C per minute. Oil pressure dropping. No camera motion detected.", "BOOK:engine:high"),
    ("S3", "All sensors nominal. Bilge dry. Radio quiet. No motion on any camera.", "BOOK:deck:low"),
    ("S4", "AIS contact closing from starboard, course drift detected. Engine nominal.", "BOOK:navigation:mid"),
    ("S5", "Fuel flow steady at cruise rate. No motion. Bilge dry.", "BOOK:engine:low"),
    ("S6", "Smoke alarm triggered in the engine room, possible fire. Temp rising.", "BOOK:engine:high"),
    ("S7", "Bilge water rising. Engine nominal, no motion on cameras.", "BOOK:deck:high"),
    ("S8", "Course drift 5 degrees starboard over last minute. AIS clear.", "BOOK:navigation:mid"),
    ("S9", "Galley water leak reported. Engine nominal, no motion.", "BOOK:deck:high"),
    ("S10", "RPM steady at 1800. Oil pressure normal. No contacts.", "BOOK:engine:low"),
    ("S11", "Blob moving fast toward vessel bow on camera two. Engine nominal.", "BOOK:navigation:mid"),
    ("S12", "Radio check complete, all quiet. Bilge dry. No AIS contacts, no motion.", "BOOK:deck:low"),
]

ENGINE_TERMS = ["temp rising", "temp falling", "oil", "fuel", "rpm"]
MOTION_TERMS = ["moving", "course drift", "ais contact"]
HAZARD_TERMS = ["rising", "falling", "dropping", "leak", "fire"]
DOMAINS, URGENCIES = ("navigation", "engine", "deck"), ("low", "mid", "high")


def log(msg):
    print("[cm1 %s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def post_json(url, payload, headers, timeout):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def gen_cell(messages):
    r = post_json(OLLAMA + "/api/chat",
                  {"model": "qwen2.5:0.5b", "messages": messages,
                   "stream": False, "options": {"temperature": 0}},
                  {"Content-Type": "application/json"}, 180)
    return r.get("message", {}).get("content", ""), r.get("eval_count", 0)


def judge_cell(state_text, draft):
    with open(TOKEN_FILE) as f:
        tok = f.read().strip()
    payload = {
        "model": "jev-preview", "state": state_text,
        "questions": {
            "domain_ok": {"type": "noul",
                          "question": "Does the draft's DOMAIN follow the rule?",
                          "instructions": "Answer true only if the draft's domain is what the rule yields for this report."},
            "urgency_ok": {"type": "noul",
                           "question": "Does the draft's URGENCY follow the rule?",
                           "instructions": "Answer true only if the draft's urgency is what the rule yields for this report."}}}
    for attempt in (1, 2):
        try:
            r = post_json(TSAFE, payload,
                          {"Authorization": "Bearer " + tok,
                           "Content-Type": "application/json"}, 60)
            a = r["answers"]
            return (float(a["domain_ok"]["noul"]), float(a["urgency_ok"]["noul"]),
                    r.get("usage", {}))
        except Exception as e:
            if attempt == 2:
                raise RuntimeError("JUDGE cell failed twice: %r" % e)
            time.sleep(2)


def embed(texts):
    out = []
    for t in texts:
        try:
            r = post_json(OLLAMA + "/api/embed",
                          {"model": "nomic-embed-text", "input": t},
                          {"Content-Type": "application/json"}, 60)
            out.append(r["embeddings"][0])
        except KeyError:
            r = post_json(OLLAMA + "/api/embeddings",
                          {"model": "nomic-embed-text", "prompt": t},
                          {"Content-Type": "application/json"}, 60)
            out.append(r["embedding"])
    return out


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return round(dot / (na * nb), 4) if na and nb else 0.0


def parse_answer(text):
    m = re.search(r"BOOK:(navigation|engine|deck):(low|mid|high)", text, re.I)
    return "BOOK:%s:%s" % (m.group(1).lower(), m.group(2).lower()) if m else "PARSE_FAIL"


def keyword_router(report):
    low = report.lower()
    eng = any(t in low for t in ENGINE_TERMS)
    mot = any(t in low for t in MOTION_TERMS)
    haz = any(t in low for t in HAZARD_TERMS)
    domain = "engine" if eng else ("navigation" if mot else "deck")
    urgency = "high" if (haz or (eng and mot)) else ("mid" if mot else "low")
    return "BOOK:%s:%s" % (domain, urgency)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    t0 = time.time()
    sys_prompt = ("You are a routing cell on a fishing vessel. Apply the rule exactly.\n"
                  + RULE + "\nAnswer with exactly one line: BOOK:<domain>:<urgency> "
                  "where domain in {navigation, engine, deck} and urgency in {low, mid, high}. "
                  "No other text.")
    recs, ev_total, jev_in, jev_out = [], 0, 0, 0
    for sid, report, truth in STIMULI:
        user_msg = "Report: " + report
        # ARM A — ungated
        ta = time.time()
        draft_a, ev1 = gen_cell([{"role": "system", "content": sys_prompt},
                                 {"role": "user", "content": user_msg}])
        ans_a, ta = parse_answer(draft_a), round(time.time() - ta, 2)
        ev_total += ev1
        # ARM B — gated relay
        tb = time.time()
        msgs = [{"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_msg}]
        draft_b, ev2 = gen_cell(msgs)
        ev_total += ev2
        state_text = RULE + "\n\nReport: " + report + "\nDraft answer: " + draft_b.strip()
        g_dom, g_urg, usage = judge_cell(state_text, draft_b)
        jev_in += usage.get("input_tokens", 0)
        jev_out += usage.get("output_tokens", 0)
        path, gates, retries = "DRAFT_PASS", [(g_dom, g_urg)], 0
        ans_b = parse_answer(draft_b)
        if min(g_dom, g_urg) < PINCH:
            msgs += [{"role": "assistant", "content": draft_b},
                     {"role": "user", "content":
                      "Gate scores domain=%.2f urgency=%.2f (threshold %.2f). Re-derive carefully step by step, then answer again with exactly one line BOOK:<domain>:<urgency>."
                      % (g_dom, g_urg, PINCH)}]
            draft_b2, ev3 = gen_cell(msgs)
            ev_total += ev3
            retries = 1
            state2 = state_text + "\nRevised draft: " + draft_b2.strip()
            g2d, g2u, usage = judge_cell(state2, draft_b2)
            jev_in += usage.get("input_tokens", 0)
            jev_out += usage.get("output_tokens", 0)
            gates.append((g2d, g2u))
            if min(g2d, g2u) < PINCH:
                path, ans_b = "PINCHED_FALLBACK", keyword_router(report)
            else:
                path, ans_b = "RETRY_PASS", parse_answer(draft_b2)
        tb = round(time.time() - tb, 2)
        recs.append({"sid": sid, "report": report, "truth": truth,
                     "armA": {"answer": ans_a, "correct": ans_a == truth, "t_s": ta},
                     "armB": {"answer": ans_b, "correct": ans_b == truth,
                              "path": path, "gates": gates, "retries": retries, "t_s": tb}})
        log("%s A=%s%s B=%s%s (%s gates=%s)" %
            (sid, ans_a, "+" if ans_a == truth else "-",
             ans_b, "+" if ans_b == truth else "-", path, gates[-1]))
    # projection cell — local geometry
    canon_e = [embed([t[2]])[0] for t in STIMULI]
    geoms = []
    for i, r in enumerate(recs):
        e = embed([r["armA"]["answer"], r["armB"]["answer"]])
        geoms.append({"sid": r["sid"],
                      "sim_A_canon": cosine(e[0], canon_e[i]),
                      "sim_B_canon": cosine(e[1], canon_e[i])})
    ca = sum(1 for r in recs if r["armA"]["correct"])
    cb = sum(1 for r in recs if r["armB"]["correct"])
    diff = cb - ca
    verdict = ("GATING_WINS" if diff >= 2 else
               "GATING_HURTS" if diff <= -2 else "TIE_NOISE")
    paths = {p: sum(1 for r in recs if r["armB"]["path"] == p)
             for p in ("DRAFT_PASS", "RETRY_PASS", "PINCHED_FALLBACK")}
    out = {"schema": "cm1-round1/1", "plan": "proposals/runs/CM1-cell-mesh-plan.md",
           "created": time.strftime("%Y-%m-%d %H:%M:%S"),
           "cells": {"gen": "qwen2.5:0.5b (ollama, temp 0)",
                     "judge": "jev-preview (typesafe /v1/systemone)",
                     "project": "nomic-embed-text (ollama)"},
           "pinch": PINCH, "n": len(STIMULI),
           "correct_A": ca, "correct_B": cb, "diff": diff, "verdict": verdict,
           "paths": paths, "ollama_eval_total": ev_total,
           "jev_tokens": {"in": jev_in, "out": jev_out},
           "wall_s": round(time.time() - t0, 1),
           "geometry": geoms, "records": recs}
    json.dump(out, open(OUT_JSON, "w"), indent=1)
    with open(JSONL, "a") as f:
        f.write(json.dumps({k: out[k] for k in
                            ("schema", "created", "correct_A", "correct_B",
                             "diff", "verdict", "paths", "jev_tokens")}) + "\n")
    log("A %d/12  B %d/12  diff %d -> %s  paths=%s  jev=%d/%d tok  %.1fs"
        % (ca, cb, diff, verdict, paths, jev_in, jev_out, out["wall_s"]))
    log("DONE")


if __name__ == "__main__":
    main()
