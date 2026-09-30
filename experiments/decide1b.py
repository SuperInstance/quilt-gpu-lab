"""DECIDE-1b — diagnose the below-chance balance-edit lane (pre-reg: proposals/runs/DECIDE-1b-diagnosis.md).
Same test set as DECIDE-1 (make_questions(64, seed=202)); no re-sampling, no re-rolls."""
import sys, json, math
import numpy as np, torch
sys.path.insert(0, "tools"); sys.path.insert(0, "experiments")
from decide1 import make_questions, render, edit_text, wilson, DecisionCell  # noqa
from decision_cell import options_of

CKPT = "/home/eileen/scratch/external/jeff-checkpoints/jeff-0.8b"

def pred_letter(res): return res["choice"]
def edit_kind(q, i): return edit_text(q["champ"], q["cands"][i]).split()[0]

def main():
    test = make_questions(64, 202)
    zs = DecisionCell(CKPT, reader="zeroshot")
    rows = []
    for q in test:
        r = zs.decide(*render(q)[:2])
        i = "ABCD".index(pred_letter(r))
        rows.append({"label": "ABCD"[q["label"]], "pred": pred_letter(r),
                     "pred_i": i, "label_i": q["label"],
                     "p": r["probabilities"], "bal_pred": q["bal"][i], "bal_label": q["bal"][q["label"]],
                     "kind_pred": edit_kind(q, i), "kind_label": edit_kind(q, q["label"])})
    res = {"n": len(rows)}
    k = sum(r["pred"] == r["label"] for r in rows)
    res["argmax_acc"] = {"k": k, "acc": k/len(rows), "cp95": wilson(k, len(rows))}
    # P1 argMIN + argmin-balance
    kmin = sum("ABCD"[min(range(4), key=lambda j: r["p"]["ABCD"[j]])] == r["label"] for r in rows)
    res["P1"] = {"argmin_prob_acc": kmin/len(rows), "cp95": wilson(kmin, len(rows)),
                 "pred_is_argmin_balance": sum(r["bal_pred"] == min(q["bal"]) for r, q in zip(rows, test))/len(rows)}
    # P2 census
    def census(key):
        c = {L: 0 for L in "ABCD"}; [c.__setitem__(r[key], c[r[key]]+1) for r in rows]; return c
    res["P2"] = {"pred_letters": census("pred"), "label_letters": census("label"),
                 "pred_kinds": {}, "label_kinds": {}}
    for key in ("pred", "label"):
        c = {}
        for r in rows: c[r["kind_"+("pred" if key=="pred" else "label")]] = c.get(r["kind_"+("pred" if key=="pred" else "label")], 0)+1
        res["P2"][key+"_kinds"] = c
    # P3 shuffle (permute option order, seed 7)
    rng = np.random.default_rng(7)
    stick = follow = 0
    for q, r in zip(test, rows):
        perm = rng.permutation(4)
        inv = [0]*4
        for newpos, oldi in enumerate(perm): inv[oldi] = newpos
        state, orig_q, _ = render(q)
        crit = {"ABCD"[j]: orig_q["criteria"]["ABCD"[inv[j]]] for j in range(4)}
        shuf = {"type": "choice", "criteria": crit, "instructions": orig_q["instructions"]}
        s = zs.decide(state, shuf)
        stick += int(pred_letter(s) == r["pred"])
        follow += int(inv["ABCD".index(pred_letter(s))] == r["pred_i"])
    res["P3"] = {"letter_stickiness": stick/len(rows), "content_following": follow/len(rows), "n": len(rows)}
    # P4 label rank
    ranks = []
    for r in rows:
        order = sorted(range(4), key=lambda j: -r["p"]["ABCD"[j]])
        ranks.append(order.index(r["label_i"]))
    res["P4"] = {"mean_label_rank": float(np.mean(ranks)), "random_mean": 1.5,
                 "rank_hist": {str(i): ranks.count(i) for i in range(4)}}
    res["hardware"] = {"peak_vram_gib": round(torch.cuda.max_memory_allocated()/2**30, 3)}
    json.dump(res, open("results/decide1/decide1b_results.json", "w"), indent=1, default=float)
    print(json.dumps(res, indent=1, default=float))

if __name__ == "__main__":
    main()
