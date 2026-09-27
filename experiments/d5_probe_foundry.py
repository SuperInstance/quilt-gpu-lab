#!/usr/bin/env python3
"""D5 — overnight probe dataset foundry (proof batch).

Fleet question: D1 (fold readers) and D4 (QLoRA canon reader) need labeled
(claim, evidence, verdict) data at volume, reproducibly, without per-token
API cost. This foundry generates canon vs distortion triples from a SEEDED
template grammar (no model), content-addresses every item (sha256),
deduplicates, and splits train/held-out by hash so downstream eval is honest.

Full-scale recipe (7B-4bit generation) is documented in recipe.json; this
proof batch runs the grammar directly to prove the plumbing: deterministic,
addressable, deduped, hash-split.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

SEED = 2718

# --- seeded RNG (deterministic, no numpy dependency needed) ---------------
def _rng(seed):
    a = seed & 0xFFFFFFFF
    while True:
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = a
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t = (t ^ (t + ((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        yield ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0


# --- grammar primitives (jev-quilt doctrine vocabulary) --------------------
DOCKS = ["wharf-3", "berth-9", "pier-1", "quay-7", "slip-2", "dock-5"]
CARGOS = ["sockeye", "halibut", "cod", "crab", "kelp", "gear"]
COUNT_WORDS = ["two", "three", "four", "five", "six", "seven", "eight", "nine"]
SUBJECTS = ["the fleet", "the barge", "the tender", "the trawler", "the skiff"]
VERBS = ["offloaded", "stowed", "unloaded", "secured", "stacked"]


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_canon(rng, i):
    dock = DOCKS[i % len(DOCKS)]
    cargo = CARGOS[(i // 7) % len(CARGOS)]
    n = COUNT_WORDS[i % len(COUNT_WORDS)]
    subj = SUBJECTS[i % len(SUBJECTS)]
    verb = VERBS[(i // 3) % len(VERBS)]
    claim = f"{subj} {verb} {n} crates of {cargo} at {dock}."
    evidence = f"manifest: {dock} -> {n} crates {cargo}."
    return {"claim": claim, "evidence": evidence, "label": "canon",
            "kind": "counting-address", "dock": dock, "cargo": cargo, "count": n}


def make_distortion(rng, i):
    # adversarial distortion: correct cargo/dock, WRONG count verb
    dock = DOCKS[(i * 3 + 1) % len(DOCKS)]
    cargo = CARGOS[(i * 5 + 2) % len(CARGOS)]
    true_n = COUNT_WORDS[i % len(COUNT_WORDS)]
    wrong_n = COUNT_WORDS[(i + 1) % len(COUNT_WORDS)]
    subj = SUBJECTS[(i + 2) % len(SUBJECTS)]
    verb = VERBS[(i + 1) % len(VERBS)]
    claim = f"{subj} {verb} {wrong_n} crates of {cargo} at {dock}."
    evidence = f"manifest: {dock} -> {true_n} crates {cargo}."
    return {"claim": claim, "evidence": evidence, "label": "distortion",
            "kind": "counting-address", "dock": dock, "cargo": cargo,
            "count_claimed": wrong_n, "count_true": true_n}


def make_semantic(rng, i):
    # semantic canon/distortion: paraphrase vs object mismatch (no counting)
    dock = DOCKS[i % len(DOCKS)]
    cargo = CARGOS[(i // 11) % len(CARGOS)]
    subj = SUBJECTS[(i + 3) % len(SUBJECTS)]
    if i % 2 == 0:
        claim = f"{subj} delivered {cargo} to {dock}."
        evidence = f"{subj} brought a {cargo} shipment to {dock}."
        label = "canon"
    else:
        claim = f"{subj} delivered {cargo} to {dock}."
        other = CARGOS[(i // 11 + 1) % len(CARGOS)]
        evidence = f"{subj} brought a {other} shipment to {dock}."
        label = "distortion"
    return {"claim": claim, "evidence": evidence, "label": label,
            "kind": "semantic", "dock": dock, "cargo": cargo}


def main():
    rng = _rng(SEED)
    next(rng)
    items = []
    # proof batch: 240 total — 120 semantic (60 canon + 60 distortion),
    # 120 counting-address (60 canon + 60 distortion)
    for i in range(60):
        items.append(make_semantic(rng, 2 * i))
        items.append(make_semantic(rng, 2 * i + 1))
        items.append(make_canon(rng, i))
        items.append(make_distortion(rng, i))

    # content-address + dedup (duplicates drop deterministically)
    seen = set()
    deduped = []
    for it in items:
        h = _sha256(json.dumps(it, sort_keys=True))
        if h not in seen:
            seen.add(h)
            it["sha256"] = h
            deduped.append(it)

    # hash-split: train / held-out by first hex nibble of the hash
    train, heldout = [], []
    for it in deduped:
        (heldout if int(it["sha256"][0], 16) >= 12 else train).append(it)

    counts = {}
    for it in deduped:
        key = f"{it['label']}"
        counts[key] = counts.get(key, 0) + 1

    recipe = {
        "model_id": None, "seed": SEED,
        "note": "proof batch uses a seeded template grammar (no model). Full-scale recipe: load a 7B instruct at 4-bit and regenerate with this grammar as the prompt seed bank.",
        "prompt_templates": ["canon counting-address", "distortion counting-address",
                             "semantic paraphrase-canon", "semantic object-mismatch"],
        "counts": counts,
    }

    out_dir = Path("results")
    out_dir.mkdir(exist_ok=True)
    with open("probes.jsonl", "w") as f:
        for it in deduped:
            f.write(json.dumps(it, sort_keys=True) + "\n")
    with open("recipe.json", "w") as f:
        json.dump(recipe, f, indent=2)
    result = {
        "experiment": "D5 probe foundry (proof batch)",
        "seed": SEED,
        "n_generated": len(items),
        "n_deduped": len(deduped),
        "dedup_rate": round(1 - len(deduped) / len(items), 4),
        "counts": counts,
        "train": len(train), "heldout": len(heldout),
        "reproducibility_hash": _sha256(json.dumps([d["sha256"] for d in deduped], sort_keys=True)),
        "verdict": "KEEP" if len(deduped) >= 200 else "INCONCLUSIVE",
    }
    with open("results/d5_probe_foundry.json", "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
