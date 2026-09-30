"""DECIDE-1c — instruction-flip confirmatory (pre-reg: proposals/runs/DECIDE-1c-instruction-flip.md).
Identical lane to DECIDE-1b except instructions say 'smallest balance'. Labels unchanged (argmax-balance)."""
import sys, json
import numpy as np, torch
sys.path.insert(0, "tools"); sys.path.insert(0, "experiments")
from decide1 import make_questions, render, edit_text, wilson, DecisionCell  # noqa

CKPT = "/home/eileen/scratch/external/jeff-checkpoints/jeff-0.8b"
FLIP_INSTR = "Balance is min(P(000), P(111)) of the final state. Which single edit gives the smallest balance?"

def main():
    test = make_questions(64, 202)
    zs = DecisionCell(CKPT, reader="zeroshot")
    rows = []
    for q in test:
        state, orig_q, _ = render(q)
        flip_q = dict(orig_q); flip_q["instructions"] = FLIP_INSTR
        r = zs.decide(state, flip_q)
        i = "ABCD".index(r["choice"])
        rows.append({"label_i": q["label"], "pred_i": i, "p": r["probabilities"],
                     "bal": q["bal"], "kind_pred": edit_text(q["champ"], q["cands"][i]).split()[0]})
    n = len(rows)
    k = sum(r["pred_i"] == r["label_i"] for r in rows)
    res = {"n": n, "instructions": FLIP_INSTR}
    res["C2"] = {"argmax_acc": {"k": k, "acc": k/n, "cp95": wilson(k, n)}}
    cons = sum(r["bal"][r["pred_i"]] == max(r["bal"]) for r in rows)
    res["C1"] = {"pred_is_argmax_balance": cons/n, "cp95": wilson(cons, n)}
    kmin = sum(r["bal"][r["pred_i"]] == min(r["bal"]) for r in rows)
    res["exploratory_pred_is_argmin_balance"] = kmin/n
    # C3 shuffle symmetry (permute options under flipped instruction, seed 7)
    rng = np.random.default_rng(7)
    follow = 0
    for q, r in zip(test, rows):
        perm = rng.permutation(4)
        inv = [0]*4
        for newpos, oldi in enumerate(perm): inv[oldi] = newpos
        state, orig_q, _ = render(q)
        crit = {"ABCD"[j]: orig_q["criteria"]["ABCD"[inv[j]]] for j in range(4)}
        flip_q = {"type": "choice", "criteria": crit, "instructions": FLIP_INSTR}
        s = zs.decide(state, flip_q)
        follow += int(inv["ABCD".index(s["choice"])] == r["pred_i"])
    res["C3"] = {"content_following": follow/n, "n": n}
    # kind census
    c = {}
    for r in rows: c[r["kind_pred"]] = c.get(r["kind_pred"], 0) + 1
    res["exploratory_pred_kinds"] = c
    res["gates"] = {"C1_pass": res["C1"]["pred_is_argmax_balance"] >= 0.75,
                    "C2_pass": res["C2"]["argmax_acc"]["acc"] >= 0.75,
                    "C3_pass": res["C3"]["content_following"] >= 0.7}
    print(json.dumps(res, indent=1, default=float))
    with open("results/decide1/decide1c_results.json", "w") as f:
        json.dump(res, f, indent=1, default=float)

if __name__ == "__main__":
    main()
