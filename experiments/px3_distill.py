#!/usr/bin/env python3
"""PX3 — selectlib judge distillation (pre-reg: proposals/runs/PX3-judge-distillation.md,
FROZEN 2026-09-30 17:16 AKDT, commit 0b5b88d).

--collect : re-run the run_judge.py protocol byte-identically (blind_split/blind_uniform,
            seed 1, budgets 6/12/24, 5 controls fired first) while instrumenting every
            jev call to results/px3_distill/judge_calls.jsonl as
            {field, seed, state_string, raw_response, parsed_label, latency_ms, call_index}.
            Fails loud if >5% of calls error after jev_client's own retries.
--distill : embed unique state strings with LOCAL ollama nomic-embed-text (768-d),
            head = L2 logistic regression (numpy, CPU, deterministic zero init),
            eval (a) within-field 5-fold CV, (b) cross-field split->uniform transfer.
            Books EVERYTHING to results/px3_distill/px3_result.json ONLY.

Key handling: parsed at RUNTIME from the TYPESAFE_AI_KEY= line of /mnt/c/Users/casey/key.txt,
injected via os.environ ONLY. Never echoed, never logged, never written to any artifact.
selectlib-readonly is READ-ONLY: imported, never modified.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]          # quilt-gpu-lab
RO = Path("/home/eileen/projects/selectlib-readonly")
OUT = BASE / "results" / "px3_distill"
KEYFILE = Path("/mnt/c/Users/casey/key.txt")
KEYLINE = "TYPESAFE_AI_KEY"                          # verified actual line name (not TYPESAFEAI_KEY)

BUDGETS = [6, 12, 24]
SEEDS = (1,)
FIELDS = (("BLIND_SPLIT", "blind_split"), ("BLIND_UNIFORM", "blind_uniform"))
EMBED_MODEL = "nomic-embed-text"
OLLAMA = "http://127.0.0.1:11434"
STORED_HEADLINE = {  # JUDGE-RUN.txt, for the reproduction control
    "BLIND_SPLIT":   {"calls": 288, "deltas": [-0.0052, -0.0050, -0.0111], "corr": -0.067},
    "BLIND_UNIFORM": {"calls": 288, "deltas": [0.0000, 0.0000, 0.0000], "corr": -0.184},
}
FOLDS = 5
BOOTSTRAP = 1000
BOOTSTRAP_SEED = 0
L2 = 0.1
ITERS = 3000
LR = 0.5
MAX_ERR_FRAC = 0.05

# Byte-identical instructions string to jev_client.jev_judge
INSTRUCTIONS = ("Does this cell already match what the scene calls for, "
                "or does it need correcting?")


def fail(msg):
    raise SystemExit(f"PX3 FAIL LOUD: {msg}")


def load_key():
    """Parse the TYPESAFE_AI_KEY= line at runtime; set os.environ only."""
    for line in KEYFILE.read_text(encoding="utf-8", errors="strict").splitlines():
        if line.startswith(KEYLINE + "="):
            val = line.split("=", 1)[1].strip()
            if not val:
                fail("key line present but empty")
            os.environ["TYPESAFEAI_KEY"] = val
            return
    fail(f"no {KEYLINE}= line found in keyfile")


def fnv1a64(data: bytes) -> int:
    h = 0xCBF29CE484222325
    for b in data:
        h = ((h ^ b) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h


def state_string(field, y, x):
    """Byte-identical copy of run_judge.py's ask() state construction."""
    w = field.w
    l = [(xx, field.render[y][xx], field.target[y][xx])
         for xx in range(max(0, x - 2), x + 1)]
    r = [(xx, field.render[y][xx], field.target[y][xx])
         for xx in range(x + 1, min(w, x + 3))]

    def desc(side):
        if not side:
            return "nothing on that side"
        return "; ".join(f"col {c} renders {rv:.2f} but the scene calls for {tv:.2f}"
                         for c, rv, tv in side)

    return (f"A cell sits between two regions of a scene.\n"
            f"LEFT of it: {desc(l)}\n"
            f"RIGHT of it: {desc(r)}\n"
            f"The cell itself is at column {x}.")


# ---------------------------------------------------------------- collect

def cmd_collect():
    OUT.mkdir(parents=True, exist_ok=True)
    load_key()
    sys.path.insert(0, str(RO))
    from selectlib import harness, oracle, local_noise, judge
    from selectlib.fields import blind_split, blind_uniform
    from selectlib.controls import noise_error_corr
    import jev_client  # KEY read at import time — env set above

    jsonl = OUT / "judge_calls.jsonl"
    idx = 0
    errors = 0
    per_field_calls = {}
    per_field_rows = {}
    corr_seen = {}
    controls_fired = None
    t0 = time.time()

    with jsonl.open("w", encoding="utf-8") as fh:
        for disp, factory_name in FIELDS:
            factory = {"blind_split": blind_split, "blind_uniform": blind_uniform}[factory_name]
            calls = {"n": 0}

            def ask(field, y, x, _calls=calls, _fh=fh):
                nonlocal idx, errors
                _calls["n"] += 1
                idx += 1
                st = state_string(field, y, x)
                t1 = time.time()
                raw = jev_client.call(st, jev_client.CRIT, INSTRUCTIONS)
                lat = round((time.time() - t1) * 1000.0, 1)
                ans = (raw.get("answers") or {}).get("q")
                p = (ans or {}).get("probabilities") or {}
                if "error" in raw:
                    errors += 1
                    parsed = None
                elif not p:
                    parsed = 0.5  # jev_judge's own fallback, kept for protocol fidelity
                else:
                    parsed = float(p.get("needs_fix", 0.0))
                _fh.write(json.dumps({
                    "field": disp, "seed": SEEDS[0], "state_string": st,
                    "raw_response": raw, "parsed_label": parsed,
                    "latency_ms": lat, "call_index": idx,
                }, ensure_ascii=False) + "\n")
                return 0.5 if parsed is None else parsed

            f0 = factory(seed=SEEDS[0])
            corr_seen[disp] = round(noise_error_corr(f0), 3)
            j = judge(ask)
            r = harness.run([oracle(), j, local_noise()],
                            lambda seed: factory(seed=seed), BUDGETS, seeds=SEEDS)
            if controls_fired is None:
                controls_fired = f"{r.controls_passed}/{r.controls_total}"
                if r.controls_total != 5 or r.controls_passed != 5:
                    fail(f"controls did not all fire: {controls_fired}")
            per_field_calls[disp] = calls["n"]
            per_field_rows[disp] = r.rows  # RAW rows; Result.table() is known-defective
            print(f"  {disp}: {calls['n']} calls, free-stat corr {corr_seen[disp]:+.3f}, "
                  f"{r.verdict()}")
    total = sum(per_field_calls.values())
    if total == 0:
        fail("zero calls made")
    err_frac = errors / total
    if err_frac > MAX_ERR_FRAC:
        fail(f"{errors}/{total} calls errored ({err_frac:.1%}) > {MAX_ERR_FRAC:.0%} budget")

    # per-field, per-budget judge−noise deltas (reproduction control)
    deltas = {}
    for disp, _ in FIELDS:
        deltas[disp] = []
        for b in BUDGETS:
            got = {row["selector"]: row["mae"] for row in per_field_rows[disp]
                   if row["budget"] == b and row["seed"] == SEEDS[0]}
            deltas[disp].append({"budget": b,
                                 "judge": round(got["judge"], 4),
                                 "noise": round(got["local_noise"], 4),
                                 "judge_minus_noise": round(got["judge"] - got["local_noise"], 4),
                                 "oracle": round(got["oracle"], 4)})

    meta = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "model": "jev-1.13.0",
        "base_url": "https://api.typesafe.ai/v1/systemone",
        "budgets": BUDGETS, "seeds": list(SEEDS),
        "controls_fired": controls_fired,
        "calls_per_field": per_field_calls,
        "total_calls": total,
        "errored_calls": errors,
        "error_fraction": round(err_frac, 5),
        "free_stat_corr": corr_seen,
        "per_field_budget_rows": per_field_rows,
        "judge_minus_noise_by_budget": deltas,
        "stored_headline": STORED_HEADLINE,
        "headline_reproduced": all(
            all(abs(d["judge_minus_noise"] - s) <= 5e-4
                for d, s in zip(deltas[disp], STORED_HEADLINE[disp]["deltas"]))
            for disp, _ in FIELDS),
        "jsonl_fnv1a64": f"0x{fnv1a64(jsonl.read_bytes()):016x}",
        "wall_seconds": round(time.time() - t0, 1),
    }
    (OUT / "collect_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"collect done: {total} calls ({errors} errored, {err_frac:.2%}), "
          f"controls {controls_fired}, {meta['wall_seconds']}s")
    print(f"fnv1a64(judge_calls.jsonl) = {meta['jsonl_fnv1a64']}")


# ---------------------------------------------------------------- distill

def embed(st: str) -> list:
    body = json.dumps({"model": EMBED_MODEL, "prompt": st}).encode()
    req = urllib.request.Request(OLLAMA + "/api/embeddings", data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        out = json.loads(r.read())
    e = out.get("embedding")
    if not e:
        fail(f"ollama returned no embedding for a state (keys: {list(out)})")
    return e


def fit_logreg(X, y):
    """L2 logistic regression, numpy, zeros init, full-batch GD. Deterministic."""
    n, d = X.shape
    w = __import__("numpy").zeros(d)
    b = 0.0
    for _ in range(ITERS):
        z = X @ w + b
        p = 1.0 / (1.0 + __import__("numpy").exp(-z))
        gw = X.T @ (p - y) / n + L2 * w
        gb = __import__("numpy").mean(p - y)
        w -= LR * gw
        b -= LR * gb
    return w, b


def predict(X, model):
    import numpy as np
    w, b = model
    return (X @ w + b >= 0).astype(int)


def f1s(y_true, y_pred):
    out = {}
    for cls in (0, 1):
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == cls and p == cls)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != cls and p == cls)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == cls and p != cls)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        out[f"f1_class{cls}"] = round(2 * prec * rec / (prec + rec), 4) if prec + rec else 0.0
        out[f"support_class{cls}"] = int(sum(1 for t in y_true if t == cls))
    return out


def boot_ci(y_true, y_pred):
    import numpy as np
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    n = len(y_true)
    t = np.asarray(y_true); p = np.asarray(y_pred)
    accs = np.empty(BOOTSTRAP)
    for i in range(BOOTSTRAP):
        ii = rng.integers(0, n, n)          # PAIRED resample of (true, pred)
        accs[i] = float(np.mean(t[ii] == p[ii]))
    return {
        "bootstrap_mean": round(float(accs.mean()), 4),
        "bootstrap_std": round(float(accs.std()), 5),
        "ci95": [round(float(np.percentile(accs, 2.5)), 4),
                 round(float(np.percentile(accs, 97.5)), 4)],
        "resamples": BOOTSTRAP, "seed": BOOTSTRAP_SEED,
        "degenerate": bool(accs.std() == 0.0),
    }


def eval_block(y_true, y_pred, n):
    import numpy as np
    agree = float(np.mean(np.asarray(y_true) == np.asarray(y_pred)))
    blk = {"n": n, "agreement": round(agree, 4)}
    blk.update(f1s(y_true, y_pred))
    blk.update(boot_ci(y_true, y_pred))
    blk["label_std"] = round(float(np.std(np.asarray(y_true))), 5)
    return blk


def cmd_distill():
    import numpy as np
    OUT.mkdir(parents=True, exist_ok=True)
    jsonl = OUT / "judge_calls.jsonl"
    if not jsonl.exists():
        fail("judge_calls.jsonl missing; run --collect first")
    meta_p = OUT / "collect_meta.json"
    if not meta_p.exists():
        fail("collect_meta.json missing; run --collect first")
    meta = json.loads(meta_p.read_text())

    # group unique states per field, in sorted order for reproducible folds
    per_field = {}
    dup_total = dup_agree = 0
    with jsonl.open(encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            if rec["parsed_label"] is None:
                continue
            per_field.setdefault(rec["field"], {}).setdefault(rec["state_string"], []).append(
                rec["parsed_label"])
    states = {}
    for fld, m in per_field.items():
        labs = []
        for st in sorted(m):
            ls = m[st]
            bins = [1 if v >= 0.5 else 0 for v in ls]
            labs.append(bins[0])  # first successful call = train label (pre-reg)
            if len(bins) > 1:
                dup_total += 1
                dup_agree += int(len(set(bins)) == 1)
        states[fld] = {"strings": sorted(m), "labels": labs}

    # embeddings (unique states only)
    Xs, cache = {}, {}
    for fld, s in states.items():
        vecs = []
        for st in s["strings"]:
            if st not in cache:
                cache[st] = embed(st)
            vecs.append(cache[st])
        arr = np.asarray(vecs, dtype=np.float64)
        if arr.shape[1] != 768:
            fail(f"embed dim {arr.shape[1]} != 768")
        Xs[fld] = arr

    def train_scale(Xtr):
        mu = Xtr.mean(axis=0)
        sd = Xtr.std(axis=0)
        sd[sd == 0] = 1.0
        return mu, sd

    results = {"within_field": {}, "cross_field": {}}
    # (a) within-field 5-fold CV
    for fld, s in states.items():
        X, y = Xs[fld], np.asarray(s["labels"])
        idx = np.arange(len(y))
        yt, yp = [], []
        for k in range(FOLDS):
            te = idx[idx % FOLDS == k]
            tr = idx[idx % FOLDS != k]
            mu, sd = train_scale(X[tr])
            model = fit_logreg((X[tr] - mu) / sd, y[tr])
            pr = predict((X[te] - mu) / sd, model)
            yt.extend(int(v) for v in y[te]); yp.extend(int(v) for v in pr)
        results["within_field"][fld] = eval_block(yt, yp, len(yt))

    # (b) cross-field: train split -> test uniform (the real claim)
    tr, te = "BLIND_SPLIT", "BLIND_UNIFORM"
    mu, sd = train_scale(Xs[tr])
    model = fit_logreg((Xs[tr] - mu) / sd, np.asarray(states[tr]["labels"]))
    yte = states[te]["labels"]
    ypr = [int(v) for v in predict((Xs[te] - mu) / sd, model)]
    results["cross_field"] = eval_block(yte, ypr, len(yte))

    # instrument stability from duplicate asks
    stability = round(dup_agree / dup_total, 4) if dup_total else None

    # reproduction control vs JUDGE-RUN.txt
    repro = {"calls_per_field": meta["calls_per_field"],
             "calls_per_field_match": meta["calls_per_field"] ==
             {d: STORED_HEADLINE[d]["calls"] for d, _ in FIELDS},
             "controls": meta["controls_fired"],
             "free_stat_corr": meta["free_stat_corr"],
             "judge_minus_noise_by_budget": meta["judge_minus_noise_by_budget"],
             "stored_headline_deltas": {d: STORED_HEADLINE[d]["deltas"] for d, _ in FIELDS},
             "headline_reproduced": meta["headline_reproduced"]}

    # branch ruling (pre-reg table + degeneracy guard)
    xf = results["cross_field"]
    A = xf["agreement"]
    if xf["label_std"] == 0.0 or xf.get("degenerate"):
        ruling = "INCONCLUSIVE"
        ruling_why = ("cross-field test labels single-class or bootstrap std==0; "
                      "agreement cannot distinguish the student from a constant "
                      "(non-degeneracy house rule)")
    elif A >= 0.85:
        ruling = "WIN"
        ruling_why = f"cross-field agreement {A} >= 0.85"
    elif A >= 0.70:
        ruling = "PARTIAL"
        ruling_why = f"cross-field agreement {A} in [0.70, 0.85)"
    else:
        ruling = "KILL"
        ruling_why = f"cross-field agreement {A} < 0.70"

    result = {
        "experiment": "PX3-judge-distillation",
        "pre_reg": "proposals/runs/PX3-judge-distillation.md (FROZEN, commit 0b5b88d)",
        "ts": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "provenance": {
            "judge_model": meta["model"], "judge_base_url": meta["base_url"],
            "field_seeds": meta["seeds"], "budgets": meta["budgets"],
            "embed_model": EMBED_MODEL, "ollama": OLLAMA, "embed_dim": 768,
            "head": f"logistic-regression numpy L2={L2} lr={LR} iters={ITERS} zero-init (deterministic)",
            "jsonl_fnv1a64": meta["jsonl_fnv1a64"],
            "total_calls": meta["total_calls"], "errored_calls": meta["errored_calls"],
            "error_fraction": meta["error_fraction"],
            "unique_states_per_field": {k: len(v["strings"]) for k, v in states.items()},
        },
        "reproduction_vs_JUDGE-RUN.txt": repro,
        "instrument_stability_dup_agreement": stability,
        "dup_states_checked": dup_total,
        "evals": results,
        "ruling": ruling,
        "ruling_why": ruling_why,
    }
    (OUT / "px3_result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"distill done -> {OUT / 'px3_result.json'}")
    print(f"headline reproduced vs JUDGE-RUN.txt: {repro['headline_reproduced']}")
    print(f"ruling: {ruling} ({ruling_why})")
    for fld, blk in results["within_field"].items():
        print(f"  within {fld}: agreement {blk['agreement']} n={blk['n']} "
              f"f1={blk['f1_class0']}/{blk['f1_class1']} ci95={blk['ci95']}")
    print(f"  cross-field: agreement {xf['agreement']} n={xf['n']} "
          f"f1={xf['f1_class0']}/{xf['f1_class1']} ci95={xf['ci95']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["collect", "distill"])
    a = ap.parse_args()
    try:
        (cmd_collect if a.mode == "collect" else cmd_distill)()
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)


if __name__ == "__main__":
    main()
