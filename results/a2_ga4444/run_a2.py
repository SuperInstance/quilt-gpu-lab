#!/usr/bin/env python3
"""A2-ga4444-4x4 driver: guard preflight -> guarded training runs -> CV gates -> G7 receipt.

Data-gen is already complete (dataset.jsonl, 66,297 boards, differentially verified).
This driver wraps ONLY the GPU training phase, per the brief. No receipt -> run VOID.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, REPO)
import guard  # noqa: E402

PY = "/home/eileen/venvs/elephant-gpu/bin/python"
WORK = os.path.join(HERE, "a2_ga4444.py")
EPOCHS = 120


def cv_stats(per_fold, key):
    import statistics
    vals = [fv["top1"][key] for fv in per_fold.values() if key in fv["top1"]]
    if not vals:
        return None, None, len(vals)
    return round(statistics.mean(vals), 4), round(statistics.pstdev(vals), 4), len(vals)


def main():
    g = guard.Guard(timeout_s=1500.0, task_id="A2-ga4444-4x4", seed="2718",
                    receipt_dir=HERE)
    preflights = []
    if not g.preflight():
        preflights.append({"attempt": 1, "breach": g.breach})
        print(f"preflight refused: {g.breach} — waiting 60 s", flush=True)
        time.sleep(60)
        g = guard.Guard(timeout_s=1500.0, task_id="A2-ga4444-4x4", seed="2718",
                        receipt_dir=HERE)
        if not g.preflight():
            preflights.append({"attempt": 2, "breach": g.breach})
            g.emit_receipt(verdict="VOID",
                           void_reason=f"preflight refused twice: {g.breach}")
            json.dump({"lane": "A2-ga4444-4x4", "status": "NOT-RUN",
                       "preflights": preflights}, open(os.path.join(HERE, "a2_status.json"), "w"), indent=2)
            print("NOT-RUN: preflight refused twice")
            return
    preflights.append({"attempt": len(preflights) + 1, "breach": None})

    env = os.environ.copy()
    env["PYTHONPATH"] = REPO + os.pathsep + env.get("PYTHONPATH", "")
    runs = {}
    for arm in ("mlp", "linear"):
        rc, out, err = g.run([PY, WORK, "--train", "--arm", arm,
                              "--epochs", str(EPOCHS), "--device", "cuda:0"],
                             cwd=HERE, env=env)
        runs[arm] = {"rc": rc, "stdout_tail": out[-800:], "stderr_tail": err[-800:]}
        print(f"[{arm}] rc={rc}")
        if rc != 0:
            print(out[-2000:])
            print(err[-2000:])
            g.emit_receipt(verdict="VOID", void_reason=f"{arm} worker exit {rc}")
            return

    metrics = {arm: json.load(open(os.path.join(HERE, f"smoke_{arm}_metrics.json")))
               for arm in ("mlp", "linear")}
    stats = {}
    for arm in ("mlp", "linear"):
        pf = metrics[arm]["per_fold"]
        stats[arm] = {k: cv_stats(pf, k) for k in
                      ("overall", "COMPOSED_B", "SIMPLE_B", "COMPOSED_A", "SIMPLE_A")}
        stats[arm]["device"] = metrics[arm]["info"]["device_name"]
        stats[arm]["device_used"] = metrics[arm]["info"]["device_used"]

    def m(arm, k):
        return stats[arm][k][0]

    def s(arm, k):
        return stats[arm][k][1]

    d_lin = round(m("linear", "SIMPLE_B") - m("linear", "COMPOSED_B"), 4)
    d_mlp = round(m("mlp", "SIMPLE_B") - m("mlp", "COMPOSED_B"), 4)
    deg = [f"{a}.{k}" for a in stats for k in stats[a]
           if isinstance(stats[a][k], tuple) and stats[a][k][1] == 0 and stats[a][k][1] is not None]

    if deg:
        verdict = "INCONCLUSIVE"
        why = f"std==0 on {deg} (rule 2)"
    elif d_lin <= 0.05:
        verdict = "BREAKS"
        why = f"linear shows no composition penalty (d_lin={d_lin} <= 0.05)"
    elif d_lin > 0.05 and d_mlp <= 0.05 and (m("mlp", "overall") - m("linear", "overall")) >= 0.05:
        verdict = "SCALES"
        why = (f"d_lin={d_lin}>0.05, d_mlp={d_mlp}<=0.05, "
               f"mlp-linear={round(m('mlp','overall')-m('linear','overall'),4)}>=0.05")
    else:
        verdict = "INCONCLUSIVE"
        why = f"gate combination not satisfied (d_lin={d_lin}, d_mlp={d_mlp})"

    gate = {"lane": "A2-ga4444-4x4", "seed": 2718, "epochs": EPOCHS,
            "cv": stats, "d_linear": d_lin, "d_mlp": d_mlp,
            "degenerate": deg, "verdict": verdict, "why": why,
            "preflights": preflights, "runs": {k: v["rc"] for k, v in runs.items()},
            "chance": {arm: {k: round(metrics[arm]["per_fold"]["0"]["chance"].get(k, -1), 4)
                             for k in metrics[arm]["per_fold"]["0"]["chance"]}
                       for arm in ("mlp", "linear")}}
    json.dump(gate, open(os.path.join(HERE, "gate.json"), "w"), indent=2)
    print(json.dumps({k: gate[k] for k in ("d_linear", "d_mlp", "verdict", "why", "cv")}, indent=2))

    rpath, receipt = g.emit_receipt()
    print("RECEIPT:", rpath, receipt.get("receipt_id"))
    json.dump({"lane": "A2-ga4444-4x4", "status": "DONE", "verdict": verdict},
              open(os.path.join(HERE, "a2_status.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
