#!/usr/bin/env python3
"""CG1b — the CG1 follow-up: is ORACLE_BOUND an elicitation artifact?

CG1 asked a local Qwen2.5-1.5B for a free-text probability and got a flat
yes-bias (0.90-0.97 on every ladder rung; step -0.05 vs canon +0.690). Before
that is treated as settled, two better elicitations:

  mode A (logit)    score = P("YES") / (P("YES") + P("NO")) at the first
                    answer position — no free-text number to parse.
  mode B (anchored) numeric 0-1 with a 2-example calibration shot in the
                    system prompt (one obviously weak, one obviously strong
                    claim) to anchor the scale.

Same ladder (9 rungs) + same 4 evidence states as CG1. Verdict per mode:
STEP (rung5-rung4 >= 0.4) and SATURATION (|mean(6..9)-rung5| <= 0.15).
If both modes still fail the step, ORACLE_BOUND stands as a property of the
model at this scale, not of the prompt. If either mode produces the step, CG1's
verdict was an elicitation artifact and must be retracted.

Run: /home/eileen/venvs/elephant-gpu/bin/python experiments/cg1b_elicitation.py
"""
import json
import os
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
OUT = os.path.join(os.path.dirname(__file__), "..", "results", "cg1")
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
STATES = {
    "mechanism+guarantee": "The registry is append-only by construction: every line is sha256-sealed and editing a line breaks the hash of every later line.",
    "mechanism only": "Each line is sha256-sealed and editing a line breaks the hash.",
    "guarantee only": "The registry is append-only.",
    "neither": "The team is careful with the registry.",
}
Q = ("Is this claim independently verifiable — could a stranger with no access to "
     "this project confirm it is true?")

SYS_PLAIN = "You grade engineering claims."
SYS_ANCHORED = (
    "You grade engineering claims on how independently verifiable they are, from 0 to 1.\n"
    "Calibration examples:\n"
    "  Claim: The team is careful. -> 0.05\n"
    "  Claim: A signed git tag exists, a clean clone reproduces the artifact "
    "byte-for-byte, and a validator that fails closed proves the byte-prefix "
    "property across all commits. -> 0.92\n"
    "Use the full range. Answer with a single number between 0 and 1. Nothing else.")


def build_ids(tok, sys_prompt, desc, answer_prefix="Score:"):
    msgs = [{"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"{Q}\n\nClaim: {desc}\n\n{answer_prefix}"}]
    text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    return tok(text, return_tensors="pt").to("cuda")


def score_logit(tok, model, desc):
    ids = build_ids(tok, SYS_PLAIN, desc, answer_prefix="Answer YES or NO:")
    with torch.no_grad():
        out = model(**ids)
    logits = out.logits[0, -1, :]
    def tok_id(s):
        t = tok(s, add_special_tokens=False)["input_ids"]
        return t[0] if t else None
    yes, no = tok_id("YES"), tok_id("NO")
    if yes is None or no is None:
        return None
    p = torch.softmax(torch.stack([logits[yes], logits[no]]).float(), dim=0)
    return float(p[0])


def score_numeric(tok, model, desc, anchored, n=3, temp=0.3):
    import re
    ids = build_ids(tok, SYS_ANCHORED if anchored else SYS_PLAIN, desc)
    vals = []
    for _ in range(n):
        with torch.no_grad():
            gen = model.generate(**ids, max_new_tokens=6, do_sample=True,
                                 temperature=temp, top_p=0.9,
                                 pad_token_id=tok.eos_token_id)
        txt = tok.decode(gen[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)
        m = re.search(r"(\d+(?:\.\d+)?)", txt)
        if m:
            v = float(m.group(1))
            if 1.0 < v <= 100.0:
                v /= 100.0
            vals.append(max(0.0, min(1.0, v)))
    return sum(vals) / len(vals) if vals else None


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL, torch_dtype=torch.float16, device_map={"": 0}).eval()
    print(f"CG1b — {MODEL}, elicitation hardening (logit + anchored)", flush=True)

    res = {"ladder_logit": [], "ladder_anchored": []}
    for i, d in enumerate(LADDER, 1):
        a = score_logit(tok, model, d)
        b = score_numeric(tok, model, d, anchored=True)
        res["ladder_logit"].append(a)
        res["ladder_anchored"].append(b)
        print(f"  rung {i}: logit={a if a is None else round(a,3)} "
              f"anchored={b if b is None else round(b,3)}", flush=True)

    res["states_logit"] = {k: score_logit(tok, model, v) for k, v in STATES.items()}
    res["states_anchored"] = {k: score_numeric(tok, model, v, anchored=True)
                              for k, v in STATES.items()}
    for k in STATES:
        print(f"  state[{k}]: logit={res['states_logit'][k]} "
              f"anchored={res['states_anchored'][k]}", flush=True)

    def verdict(vals):
        lv = [v for v in vals]
        step = None if (lv[3] is None or lv[4] is None) else lv[4] - lv[3]
        tail = [v for v in lv[5:9] if v is not None]
        sat = None if (not tail or lv[4] is None) else sum(tail) / len(tail) - lv[4]
        return {"step": step, "saturation": sat, "G1_step": step is not None and step >= 0.4,
                "G2_saturation": sat is not None and abs(sat) <= 0.15}

    summary = {"experiment": "CG1b — elicitation hardening of CG1",
               "model": MODEL,
               "modes": {"logit": verdict(res["ladder_logit"]),
                         "anchored": verdict(res["ladder_anchored"])},
               "raw_ladder_logit": res["ladder_logit"],
               "raw_ladder_anchored": res["ladder_anchored"],
               "states_logit": res["states_logit"],
               "states_anchored": res["states_anchored"],
               "wall_clock_s": round(time.time() - t0, 1)}
    verdict_any = any(summary["modes"][m]["G1_step"] and summary["modes"][m]["G2_saturation"]
                      for m in ("logit", "anchored"))
    summary["verdict"] = "ELICITATION_ARTIFACT" if verdict_any else "ORACLE_BOUND_STANDS"
    with open(os.path.join(OUT, "cg1b_results.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps({k: summary[k] for k in ("modes", "verdict", "wall_clock_s")}, indent=2),
          flush=True)
