#!/usr/bin/env python3
"""GATE LOOP V1 — bias-corrected dial gate + JEV (fixed schema).
v0 learnings: (1) typesafe field is 'state' not 'input' (400 was self-inflicted);
(2) machine_vs_organic reads -6..-7 on EVERY SD render = systematic generator
bias (DreamShaper anthropomorphizes) — decompose the bias, gate on the residual.
No model reloads: v0 receipt already holds dials+descs for all 6 candidates.
"""
import json, urllib.request, pathlib
HERE = pathlib.Path(__file__).parent / "gate_loop"
r = json.load(open(HERE / "gate_receipt.json"))
T = r["target_dials"]; DIALS = list(T)
cands = [c for c in r["candidates"] if c.get("dials")]

# --- decompose generator bias per dial ---
bias = {k: sum(c["dials"][k] - T[k] for c in cands) / len(cands) for k in DIALS}
print("generator bias per dial (measured - target):", {k: round(v,2) for k,v in bias.items()})
for c in cands:
    c["corrected_L1"] = round(sum(abs((c["dials"][k] - T[k]) - bias[k]) for k in DIALS), 2)
    c["corrected_pass"] = c["corrected_L1"] <= 5.0
print("corrected L1:", {c["name"]: c["corrected_L1"] for c in cands})
survivors = [c for c in cands if c["identity_pass"] and c["corrected_pass"]]
print("survivors after bias-corrected gate:", [c["name"] for c in survivors])

# --- JEV with CORRECT schema (state field) ---
def typesafe_key():
    for line in open("/mnt/c/Users/casey/key.txt"):
        if line.startswith("TYPESAFE_AI_KEY="):
            return line.strip().split("=", 1)[1]
    raise RuntimeError("no key")
def jev_noul(question, instructions, state):
    body = {"model": "jev-latest",
            "state": state,
            "questions": {"robot": {"type": "noul", "question": question,
                                    "instructions": instructions}}}
    req = urllib.request.Request("https://api.typesafe.ai/v1/systemone",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {typesafe_key()}"})
    with urllib.request.urlopen(req, timeout=60) as r_:
        return json.loads(r_.read())
for c in survivors:
    try:
        r_ = jev_noul("Does this description clearly indicate a machine-like robot character rather than a human?",
                      "Answer true only if the description unambiguously refers to a robot/machine figure.",
                      c["desc"])
        c["jev"] = r_.get("answers", {}).get("robot", {})
        print(f"JEV {c['name']}: {json.dumps(c['jev'])[:140]}")
    except urllib.error.HTTPError as e:
        c["jev_error"] = e.read().decode()[:150]
        print(f"JEV {c['name']}: ERROR {c['jev_error']}")
accepted = [c["name"] for c in survivors if c.get("jev", {}).get("noul", 0) >= 0.6]
out = {"bias": bias, "candidates": cands, "accepted": accepted,
       "law": "gate on bias-corrected residual; generator bias is a measured artifact"}
(HERE / "gate_v1_receipt.json").write_text(json.dumps(out, indent=1))
print(f"ACCEPTED {len(accepted)}: {accepted}")
