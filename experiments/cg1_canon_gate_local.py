#!/usr/bin/env python3
"""CG1 — does the canon gate leave the oracle? (local 1.5B replication)

Pre-reg: proposals/runs/CG1-canon-gate-local.md
Source canon: quilt-research-canons/research/jev-gate-experiments-2026-09-29.md

Reproduces the canon's gate STRUCTURE on a local model (no API in the loop):
  T1 ladder (9 rungs, composite)   -> the append-only step
  T2 saturation (rungs 6-9 inert)
  T3 tautology (bare shape on a restatement)
  T4 two-axis min() separation + payoff on the canon's own 7 claims
  T5 model agreement (0.5B ladder shape)

Run: /home/eileen/venvs/elephant-gpu/bin/python experiments/cg1_canon_gate_local.py
"""
import json
import os
import re
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

BIG, SMALL = "Qwen/Qwen2.5-1.5B-Instruct", "Qwen/Qwen2.5-0.5B-Instruct"
N_SAMPLES, TEMP = 3, 0.3
OUT = os.path.join(os.path.dirname(__file__), "..", "results", "cg1")

SYS = ("You grade engineering claims. Answer with a single number between 0 and 1. "
       "Nothing else.")

Q_COMPOSITE = ("How likely is it that this claim is independently verifiable — that a "
               "stranger with no access to this project could confirm it is true?")
Q_PRIMED = ("Consider a registry whose entries are sealed. For the claim below, how likely "
            "is it that it is independently verifiable by a stranger with no access to "
            "this project?")
Q_MECH = ("Is there something that would physically have to break for this claim to be "
          "false?")
Q_EXT = "Could a stranger with no access to this project verify this claim?"
Q_BARE = "Is the registry append-only?"

# §3 — the nine monotone rungs (one clause added per rung)
LADDER = [
    "The project has a registry file.",
    "The registry file records one prediction.",
    "The registry file records predictions, each line sha256-sealed.",
    "The registry file records predictions, each line sha256-sealed; editing a line breaks the hash.",
    "The registry file records predictions, each line sha256-sealed, editing a line breaks the hash, and the file is append-only.",
    "The registry file is append-only and a validator proves the byte-prefix property.",
    "The registry file is append-only, a validator proves the byte-prefix property, and the validator fails closed.",
    "The registry file is append-only and the byte-prefix property holds across commits.",
    "The registry file is append-only with byte-prefix across commits, and a second independent implementation reproduces it.",
]

# §4 — four evidence states
STATES = {
    "mechanism+guarantee": "The registry is append-only by construction: every line is sha256-sealed and editing a line breaks the hash of every later line.",
    "mechanism only": "Each line is sha256-sealed and editing a line breaks the hash.",
    "guarantee only": "The registry is append-only.",
    "neither": "The team is careful with the registry.",
}

# §5 — the canon's own claims (paraphrased to their table meaning)
CLAIMS = {
    "M1 cite a mine id + boilerplate": "The artifact cites a mine id and includes the standard boilerplate.",
    "M4 budget cap line in every header": "Every file header contains a line stating the budget cap.",
    "M9 at least half the queue": "At least half of the queue was processed.",
    "M5 at most 1 death per wave": "At most one death occurred per wave.",
    "M6 opens a PR with the right words": "The run opens a pull request containing the expected keywords.",
    "S1 signed tag, clean clone reproduces": "A signed git tag exists, and a clean clone reproduces the artifact byte-for-byte.",
    "S2 release verifier + self-test": "A release verifier script ships alongside the artifact and passes its own self-test.",
}


def parse_score(text):
    m = re.search(r"(\d+(?:\.\d+)?)", text)
    if not m:
        return None
    v = float(m.group(1))
    if 1.0 < v <= 100.0:
        v /= 100.0
    return max(0.0, min(1.0, v))


def load(name):
    tok = AutoTokenizer.from_pretrained(name)
    model = AutoModelForCausalLM.from_pretrained(
        name, torch_dtype=torch.float16, device_map={"": 0})
    model.eval()
    return tok, model


def ask(tok, model, question, desc, n=N_SAMPLES, temp=TEMP):
    msgs = [{"role": "system", "content": SYS},
            {"role": "user", "content": f"{question}\n\nClaim: {desc}\n\nScore:"}]
    text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    ids = tok(text, return_tensors="pt").to(model.device)
    scores, raw = [], []
    for _ in range(n):
        with torch.no_grad():
            gen = model.generate(**ids, max_new_tokens=6, do_sample=True,
                                 temperature=temp, top_p=0.9,
                                 pad_token_id=tok.eos_token_id)
        out = tok.decode(gen[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)
        raw.append(out.strip().replace("\n", " ")[:20])
        s = parse_score(out)
        if s is not None:
            scores.append(s)
    return {"mean": sum(scores) / len(scores) if scores else None,
            "scores": scores, "raw": raw, "unparsed": n - len(scores)}


def two_axis(tok, model, desc):
    mech = ask(tok, model, Q_MECH, desc)
    ext = ask(tok, model, Q_EXT, desc)
    both = [s for s in ([mech["mean"], ext["mean"]]) if s is not None]
    return {"mech": mech, "ext": ext,
            "decomposed": min(both) if both else None,
            "composite": ask(tok, model, Q_COMPOSITE, desc),
            "bare": ask(tok, model, Q_BARE, desc)}


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    tok, model = load(BIG)
    print(f"CG1 — instrument: {BIG} (fp16, cuda), n={N_SAMPLES} @ T={TEMP}", flush=True)

    # T1/T2 — ladder
    ladder = []
    for i, desc in enumerate(LADDER, 1):
        r = ask(tok, model, Q_COMPOSITE, desc)
        ladder.append({"rung": i, "desc": desc, "mean": r["mean"],
                       "scores": r["scores"], "unparsed": r["unparsed"]})
        print(f"  rung {i}: {r['mean']}", flush=True)
    lv = [r["mean"] for r in ladder]
    step = (lv[4] - lv[3]) if all(v is not None for v in lv[3:5]) else None
    sat_tail = [v for v in lv[5:9] if v is not None]
    sat_delta = (sum(sat_tail) / len(sat_tail) - lv[4]) if sat_tail and lv[4] is not None else None

    # T3/T4 — states × shapes
    states = {}
    for name, desc in STATES.items():
        states[name] = two_axis(tok, model, desc)
        st = states[name]
        print(f"  state[{name}]: composite={st['composite']['mean']} "
              f"min={st['decomposed']} bare={st['bare']['mean']}", flush=True)

    # T4 payoff — the canon's own claims
    payoff = {}
    for name, desc in CLAIMS.items():
        r = two_axis(tok, model, desc)
        payoff[name] = {"composite": r["composite"]["mean"], "mech": r["mech"]["mean"],
                        "ext": r["ext"]["mean"], "decomposed": r["decomposed"]}
        print(f"  claim[{name}]: composite={r['composite']['mean']} min={r['decomposed']}",
              flush=True)

    # T5 — model agreement on the ladder (0.5B)
    del model
    torch.cuda.empty_cache()
    tok_s, model_s = load(SMALL)
    ladder_small = []
    for i, desc in enumerate(LADDER, 1):
        r = ask(tok_s, model_s, Q_COMPOSITE, desc)
        ladder_small.append(r["mean"])
    print(f"  0.5B ladder: {[round(v,3) if v is not None else None for v in ladder_small]}",
          flush=True)
    del model_s
    torch.cuda.empty_cache()

    # gates
    g1 = step is not None and step >= 0.4
    g2 = sat_delta is not None and abs(sat_delta) <= 0.15
    bare_go = states["guarantee only"]["bare"]["mean"]
    comp_go = states["guarantee only"]["composite"]["mean"]
    g3 = bare_go is not None and comp_go is not None and bare_go >= 0.75 and comp_go <= 0.5
    mg = states["mechanism+guarantee"]["decomposed"]
    go = states["guarantee only"]["decomposed"]
    g4 = mg is not None and go is not None and mg >= 0.7 and go <= 0.5
    verdict = "EXTERNALIZES" if all([g1, g2, g3, g4]) else (
        "ORACLE_BOUND" if not g1 else "PARTIAL")

    summary = {
        "experiment": "CG1 — canon gate on a local model",
        "instrument": BIG, "second_oracle": SMALL,
        "n_samples": N_SAMPLES, "temp": TEMP,
        "ladder": lv, "step_rung4_to_5": step, "saturation_delta": sat_delta,
        "states": {k: {"composite": v["composite"]["mean"], "min": v["decomposed"],
                       "bare": v["bare"]["mean"], "mech": v["mech"]["mean"],
                       "ext": v["ext"]["mean"]} for k, v in states.items()},
        "payoff": payoff, "ladder_small": ladder_small,
        "gates": {"G1_step": g1, "G2_saturation": g2, "G3_tautology": g3,
                  "G4_min_separates": g4},
        "verdict": verdict,
        "wall_clock_s": round(time.time() - t0, 1),
    }
    with open(os.path.join(OUT, "cg1_results.json"), "w") as f:
        json.dump({"summary": summary, "detail": {
            "ladder": ladder,
            "states": {k: {"composite": v["composite"], "mech": v["mech"],
                           "ext": v["ext"], "bare": v["bare"]}
                       for k, v in states.items()}}}, f, indent=2)
    print(json.dumps(summary, indent=2), flush=True)
