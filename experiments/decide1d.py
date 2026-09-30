"""DECIDE-1d — instruction-ablation census (pre-reg: proposals/runs/DECIDE-1d-instruction-census.md).
4 new instruction variants x same 64 questions (seed 202). Baselines largest/smallest reused from 1/1b/1c."""
import sys, json
import numpy as np, torch
sys.path.insert(0, "tools"); sys.path.insert(0, "experiments")
from decide1 import make_questions, render, edit_text, wilson, DecisionCell  # noqa

CKPT = "/home/eileen/scratch/external/jeff-checkpoints/jeff-0.8b"
DEF = "Balance is min(P(000), P(111)) of the final state."
VARIANTS = {
    "highest":   f"{DEF} Which single edit gives the highest balance?",
    "lowest":    f"{DEF} Which single edit gives the lowest balance?",
    "neutral":   "Choose one edit.",
    "no_def":    "Which single edit gives the largest balance?",
}

def main():
    test = make_questions(64, 202)
    zs = DecisionCell(CKPT, reader="zeroshot")
    out = {"n": 64, "variants": {}}
    for name, instr in VARIANTS.items():
        rows = []
        for q in test:
            state, orig_q, _ = render(q)
            q2 = dict(orig_q); q2["instructions"] = instr
            r = zs.decide(state, q2)
            rows.append({"pred_i": "ABCD".index(r["choice"]), "bal": q["bal"],
                         "kind": edit_text(q["champ"], q["cands"]["ABCD".index(r["choice"])]).split()[0]})
        n = len(rows)
        kmin = sum(r["bal"][r["pred_i"]] == min(r["bal"]) for r in rows)
        kmax = sum(r["bal"][r["pred_i"]] == max(r["bal"]) for r in rows)
        out["variants"][name] = {
            "pred_is_argmin_balance": kmin / n, "cp95": wilson(kmin, n),
            "argmax_acc": kmax / n,
            "D1_break": (kmin / n) < 0.75, "D2_recover": (kmax / n) >= 0.75,
        }
        kc = {}
        for r in rows: kc[r["kind"]] = kc.get(r["kind"], 0) + 1
        out["variants"][name]["pred_kinds"] = kc
        print(name, out["variants"][name], flush=True)
    out["gates"] = {
        "D1_any_break": any(v["D1_break"] for v in out["variants"].values()),
        "D2_any_recover": any(v["D2_recover"] for v in out["variants"].values()),
    }
    with open("results/decide1/decide1d_results.json", "w") as f:
        json.dump(out, f, indent=1, default=float)
    print(json.dumps(out["gates"]))

if __name__ == "__main__":
    main()
