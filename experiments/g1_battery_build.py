"""g1_battery_build.py — build the G1 certified 96-prompt witness-claim battery.

Deterministic expansion of the moth-seal certified master seed
(docs/g1/battery-96-seed.json, label g1-battery-96-master, certified-direct,
832 bits consumed, health-passed) into 96 witness-claim prompts: 6 classes x 16.

Class mix: ARITH, SEQ, XREF (cross-reference tables), CONTRA (consistency pair),
COUNT (occurrence counting), DATE (date arithmetic). Every prompt ends with a
strict JSON answer contract; ground truth is computed at build time and written
to a SIDE-CAR key file (never inside the battery -> blind scoring).

Registration law: battery JSON lands in fleet-seeds docs/g1/ and is committed +
pushed BEFORE the first seat run (pre-registration receipt).

Usage:
  python3 experiments/g1_battery_build.py \
    --seed ~/projects/fleet-seeds/docs/g1/battery-96-seed.json \
    --battery ~/projects/fleet-seeds/docs/g1/battery-96.json \
    --key results/g1/battery-96-key.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import random
from pathlib import Path

CLASSES = ("arith", "seq", "xref", "contra", "count", "date")
PER_CLASS = 16
CONTRACT = ('Reply with ONLY this JSON and nothing else: '
            '{"claim_id":"<id>","verdict":"SUPPORTED"|"REFUTED"|"INSUFFICIENT",'
            '"reason":"<max 25 words>"}')

FIRST = ["Alma", "Bo", "Cira", "Dov", "Eno", "Fay", "Gus", "Hana", "Ivo", "June",
         "Kip", "Lena", "Mose", "Nell", "Omar", "Pia", "Quin", "Rosa", "Sven", "Tova"]
DEPTS = [("D1", "Harbor Ops", "Juneau"), ("D2", "Rigging", "Sitka"),
         ("D3", "Dispatch", "Anchorage"), ("D4", "Refit", "Kodiak"),
         ("D5", "Provisioning", "Homer")]
FILLER = ("the logbook", "a kettle", "two coils", "the barometer", "spare lanyards",
          "a gaff", "the tide table", "oilskin mitts", "a compass", "bait jars")


def rng_for(master: tuple, cid: str) -> random.Random:
    h = hashlib.sha256(f"g1b96|{master}|{cid}".encode()).digest()
    return random.Random(int.from_bytes(h, "big"))


def p_arith(rng, cid):
    a, b = rng.randint(11, 97), rng.randint(11, 97)
    op = rng.choice("+-x")
    true = a + b if op == "+" else a - b if op == "-" else a * b
    delta = rng.choice([0, 0, 1, -1, 10, -10])
    claimed = true + delta
    text = (f"Claim: {a} {op} {b} = {claimed}.\n"
            f"Evidence: none supplied — verify by computation.\n{CONTRACT}")
    return text, {"expected": "SUPPORTED" if delta == 0 else "REFUTED",
                  "truth": f"{a} {op} {b} = {true}"}


def p_seq(rng, cid):
    s, d = rng.randint(3, 40), rng.randint(2, 9)
    terms = [s + d * i for i in range(8)]
    true_next = s + d * 8
    j = rng.choice([0, 0, 1, -1, 2, -2])
    shown = ", ".join(map(str, terms))
    text = (f"Claim: the next term of the sequence [{shown}] is {true_next + j}.\n"
            f"Evidence: the sequence itself.\n{CONTRACT}")
    return text, {"expected": "SUPPORTED" if j == 0 else "REFUTED",
                  "truth": f"next = {true_next}"}


def p_xref(rng, cid):
    emps = rng.sample(FIRST, 6)
    rows = {n: rng.choice(DEPTS) for n in emps}
    who = rng.choice(emps)
    did, dname, city = rows[who]
    corrupt = rng.random() < 0.5
    if corrupt:
        field = rng.choice([0, 1, 2])
        other = rng.choice([d for d in DEPTS if d[0] != did])
        did, dname, city = (other[0], dname, city) if field == 0 else \
                           (did, other[1], city) if field == 1 else \
                           (did, dname, other[2])
    roster = "\n".join(f"  {n} — badge {rng.randint(100, 999)}" for n in emps)
    assigns = "\n".join(f"  {n} → department {rows[n][0]} ({rows[n][1]}, {rows[n][2]})"
                        for n in emps)
    text = (f"Roster:\n{roster}\n\nAssignments:\n{assigns}\n\n"
            f"Claim: {who} works in department {did} ({dname}), stationed in {city}, "
            f"per the assignments list.\n{CONTRACT}")
    return text, {"expected": "REFUTED" if corrupt else "SUPPORTED", "truth": f"{who}->{rows[who]}"}


def p_contra(rng, cid):
    box = rng.sample(FILLER, 5)
    claims = [f"The locker contains exactly these items: {', '.join(box)}."]
    # G1d fix: B's item choice DERIVES the truth — B ("X is NOT on the list") is
    # true iff X is absent from A's list; consistent = both true.
    if rng.random() < 0.5:
        drop = rng.choice(box)
        claims[0] = f"The locker contains exactly these items: {', '.join(i for i in box if i != drop)}."
        b_item = drop                      # B refers to the omitted item -> B true
    else:
        b_item = rng.choice(box)           # B names a listed item -> B false
    claims.append(f"The {b_item} is NOT on the locker list.")
    a_list = set(claims[0].split("items: ", 1)[1].rstrip(".").split(", "))
    consistent = b_item not in a_list
    text = (f"Statement A: {claims[0]}\nStatement B: {claims[1]}\n\n"
            f"Claim: Statements A and B are mutually consistent (both can be true).\n{CONTRACT}")
    return text, {"expected": "SUPPORTED" if consistent else "REFUTED",
                  "truth": f"B {'true' if consistent else 'false'} given A (item {'absent' if consistent else 'present'})"}


def p_count(rng, cid):
    target = rng.choice(FILLER)
    k = rng.randint(3, 8)
    pool = [f for f in FILLER if f != target]
    parts = []
    # G1d fix: target appears EXACTLY k times (old code scattered target via
    # rng.choice(FILLER), so the true count was random and labels lied)
    for _ in range(k):
        parts.append(target)
        parts.append(rng.choice(pool))
        parts.append(rng.choice(pool))
    rng.shuffle(parts)
    paragraph = ("Manifest states: " + "; ".join(parts) + ".")
    j = rng.choice([0, 0, 1, -1])
    claimed = k + j
    text = (f"{paragraph}\n\nClaim: the manifest lists '{target}' exactly {claimed} times.\n{CONTRACT}")
    return text, {"expected": "SUPPORTED" if j == 0 else "REFUTED", "truth": f"{target} x{k}"}


def p_date(rng, cid):
    base = dt.date(2026, 1, 1) + dt.timedelta(days=rng.randint(0, 200))
    n = rng.randint(10, 90)
    true = base + dt.timedelta(days=n)
    j = rng.choice([0, 0, 1, -1, 2, -3])
    claimed = true + dt.timedelta(days=j)
    text = (f"Claim: {n} days after {base.isoformat()} is {claimed.isoformat()}.\n"
            f"Evidence: none supplied — verify by calendar arithmetic.\n{CONTRACT}")
    return text, {"expected": "SUPPORTED" if j == 0 else "REFUTED",
                  "truth": f"true date {true.isoformat()}"}


BUILDERS = {"arith": p_arith, "seq": p_seq, "xref": p_xref,
            "contra": p_contra, "count": p_count, "date": p_date}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", required=True)
    ap.add_argument("--battery", required=True)
    ap.add_argument("--key", required=True)
    a = ap.parse_args()

    seed_doc = json.loads(Path(a.seed).read_text())
    chosen = seed_doc["chosen"]["selected"]
    master = tuple(chosen)
    assert len(master) == 4 and seed_doc["mode"] == "certified", "seed doc must be the certified master"

    prompts, key = [], {}
    for ci, cls in enumerate(CLASSES):
        for k in range(PER_CLASS):
            cid = f"g1b-{cls}-{ci:02d}{k:02d}"
            rng = rng_for(master, cid)
            text, verdict = BUILDERS[cls](rng, cid)
            prompts.append({"id": cid, "text": text, "max_tokens": 2000, "temperature": 0})
            key[cid] = verdict

    cert_str = (f"moth-seal comet-qrng-v1 certified-direct | label={seed_doc['label']} | "
                f"ts={seed_doc['ts']} | chosen={list(master)} | "
                f"sha256={seed_doc['rawResultSha256'][:16]}… | "
                f"healthPassed={seed_doc['certifiedBits']['healthPassed']}")
    battery = {
        "battery_id": "g1-battery-96@1",
        "certified": True,
        "seed": {
            "source": ("moth-seal comet-qrng-v1 master seed, certified-direct stream, "
                       "label g1-battery-96-master (fleet-seeds docs/g1/battery-96-seed.json); "
                       "prompts are a deterministic documented expansion: per-prompt "
                       "rng = sha256('g1b96'|master|prompt_id) via "
                       "quilt-gpu-lab experiments/g1_battery_build.py"),
            "cert": cert_str,
            "value": ",".join(map(str, master)),
        },
        "prompts": prompts,
    }
    Path(a.battery).write_text(json.dumps(battery, indent=1) + "\n")
    Path(a.key).parent.mkdir(parents=True, exist_ok=True)
    Path(a.key).write_text(json.dumps({"master_seed": list(master), "key": key}, indent=1) + "\n")
    exp = {}
    for v in key.values():
        exp[v["expected"]] = exp.get(v["expected"], 0) + 1
    print(f"battery: {len(prompts)} prompts -> {a.battery}")
    print(f"key: {len(key)} entries -> {a.key}")
    print("verdict balance:", exp)
    print("master seed:", list(master))


if __name__ == "__main__":
    main()
