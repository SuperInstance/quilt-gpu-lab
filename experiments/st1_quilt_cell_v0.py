#!/usr/bin/env python3
"""ST1 — quilt-cell-v0: trained receipt-validity judgment cell.

Pre-registration (FROZEN before fire): proposals/runs/ST1-quilt-cell-v0.md
Casey 2026-09-30 10:56: "keep using the gpu to better our systems."

Trains prajjwal1/bert-tiny on synthetic receipts from our booking schema with
programmatic ground truth (clean vs corrupted), then gates on REAL lab receipts
with injected corruptions + abstention on out-of-domain text (non-circular:
threshold calibrated on OOD half A, gate evaluated on OOD half B).

Usage:
  python experiments/st1_quilt_cell_v0.py            # full run (5 seeds)
  python experiments/st1_quilt_cell_v0.py --smoke    # 1 seed, tiny, fast
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import random
import sys
import time
from pathlib import Path

import numpy as np

LAB = Path(__file__).resolve().parents[1]
RESULTS_DIR = LAB / "results" / "st1_quilt_cell_v0"
SEEDS = [6611, 6612, 6613, 6614, 6615]
TAU_GRID = (0.40, 0.45, 0.50, 0.55, 0.60)
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # amended pre-fire (see pre-reg)
N_TRAIN, N_VAL, N_OOD = 8000, 1000, 120
BATCH, EPOCHS, LR, SEQ = 32, 4, 3e-4, 192
GATES = {"syn_auc_min": 0.95, "real_auc_min": 0.80, "honest_fpr_max": 0.10,
         "ood_abstain_min": 0.90, "min_real_receipts": 10}
RULES = ["antirank-primacy", "frontier-distillation", "claim-ratio",
         "judgment-holonomy", "cell-mesh-relay"]
REAL_OPS = ["verdict_flip", "sign_flip", "tau_off", "seed_drop", "value_swap"]

# ------------------------------------------------------------ synth corpus

def honest_verdict(wins: int, n_pairs: int, mri: float) -> str:
    return "KEEP" if (wins >= math.ceil(0.8 * n_pairs) and mri > 0) else "KILL"

def make_example(rng: random.Random) -> dict:
    n_pairs = rng.randint(4, 12)
    wins = rng.randint(0, n_pairs)
    ex = {
        "receipt": f"{rng.choice(RULES)[:4]}_r{rng.randint(1, 9)}_s{rng.randint(1000, 9999)}",
        "mean_rel_improvement": round(rng.uniform(-0.10, 0.25), 4),
        "wins": wins,
        "n_pairs": n_pairs,
        "tau": rng.choice(TAU_GRID),
        "seeds": f"{rng.randint(1000, 9999)}-{rng.randint(1000, 9999)}",
        "rule": rng.choice(RULES),
    }
    ex["verdict"] = honest_verdict(ex["wins"], ex["n_pairs"],
                                   ex["mean_rel_improvement"])
    return ex

def corrupt_example(ex: dict, rng: random.Random, op: str) -> dict:
    o = json.loads(json.dumps(ex))
    if op == "sign_flip":
        o["mean_rel_improvement"] = -o["mean_rel_improvement"]
    elif op == "wins_over":
        o["wins"] = o["wins"] + rng.randint(1, 3)   # now wins > n_pairs
    elif op == "verdict_flip":
        o["verdict"] = "KILL" if o["verdict"] == "KEEP" else "KEEP"
    elif op == "tau_off":
        o["tau"] = rng.choice([0.30, 0.35, 0.65, 0.70, 0.99])
    elif op == "seed_drop":
        del o["seeds"]
    elif op == "denom_swap":
        o["wins"], o["n_pairs"] = o["n_pairs"], o["wins"]
    return o

SYN_OPS = ["sign_flip", "wins_over", "verdict_flip", "tau_off", "seed_drop",
           "denom_swap"]

def render(ex: dict, style: str) -> str:
    if style == "json":
        return json.dumps(ex, sort_keys=True)
    seeds = ex.get("seeds", "")
    return (f"receipt {ex['receipt']}\nverdict: {ex['verdict']}\n"
            f"mean_rel_improvement: {ex['mean_rel_improvement']:+.4f}\n"
            f"wins: {ex['wins']} of {ex['n_pairs']} pairs\n"
            f"tau: {ex['tau']:.2f} (grid 0.40-0.60)\n"
            f"seeds: {seeds}\nrule: {ex['rule']}")

def synth_pair(rng: random.Random) -> tuple[str, int]:
    """50% corruption rate; both render styles (template + compact JSON)."""
    ex = make_example(rng)
    label = 0
    if rng.random() < 0.5:
        ex = corrupt_example(ex, rng, rng.choice(SYN_OPS))
        label = 1
    return render(ex, rng.choice(["template", "json"])), label

# ------------------------------------------------------------ real gate set

def load_real_receipts() -> list[dict]:
    out = []
    for p in sorted(glob.glob(str(LAB / "results" / "*" / "results.json"))):
        if "st1_quilt_cell_v0" in p:
            continue  # never gate on our own receipt (self-contamination)
        try:
            obj = json.loads(Path(p).read_text())
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        out.append({"path": str(Path(p).relative_to(LAB)),
                    "text": json.dumps(obj, sort_keys=True)[:1800],
                    "obj": obj})
    return out

def numeric_paths(obj, prefix=()):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from numeric_paths(v, prefix + (k,))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from numeric_paths(v, prefix + (i,))
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        yield (prefix, obj)

def set_at_path(obj, path, value):
    cur = obj
    for p in path[:-1]:
        cur = cur[p]
    cur[path[-1]] = value

def get_at_path(obj, path):
    cur = obj
    for p in path:
        cur = cur[p]
    return cur

def corrupt_real(obj: dict, rng: random.Random, op: str):
    o = json.loads(json.dumps(obj))

    def find_key(d, key):
        if isinstance(d, dict):
            for k, v in d.items():
                if k == key:
                    return d, k
            for v in d.values():
                r = find_key(v, key)
                if r:
                    return r
        return None

    if op == "verdict_flip":
        spot = find_key(o, "verdict")
        if spot:
            d, k = spot
            d[k] = "KILL" if str(d[k]).upper() == "KEEP" else "KEEP"
            return o
    elif op == "sign_flip":
        for key in ("mean_rel_improvement", "improvement", "delta"):
            spot = find_key(o, key)
            if spot and isinstance(spot[0][spot[1]], (int, float)) \
               and not isinstance(spot[0][spot[1]], bool):
                d, k = spot
                d[k] = -d[k]
                return o
    elif op == "tau_off":
        spot = find_key(o, "tau") or find_key(o, "threshold")
        if spot and isinstance(spot[0][spot[1]], (int, float)) \
           and not isinstance(spot[0][spot[1]], bool):
            d, k = spot
            d[k] = 0.99
            return o
    elif op == "seed_drop":
        spot = find_key(o, "seeds") or find_key(o, "seed")
        if spot:
            d, k = spot
            del d[k]
            return o
    elif op == "value_swap":
        paths = [p for p, _ in numeric_paths(o)]
        if len(paths) >= 2:
            pa, pb = rng.sample(paths, 2)
            va, vb = get_at_path(o, pa), get_at_path(o, pb)
            if va != vb:
                set_at_path(o, pa, vb)
                set_at_path(o, pb, va)
                return o
    return None

def ood_texts(rng: random.Random) -> list[str]:
    base = ["The quick brown fox jumps over the lazy dog near the riverbank "
            "at dawn while mist settles on the water.",
            "It was the best of times, it was the worst of times, it was the "
            "age of wisdom, it was the age of foolishness."]
    readme = LAB / "README.md"
    lines: list[str] = []
    if readme.exists():
        for line in readme.read_text(errors="replace").splitlines():
            line = line.strip()
            if len(line) > 60 and not line.startswith(("|", "```", "#")):
                lines.append(line)
    pool = base + lines
    return [pool[i % len(pool)] for i in range(N_OOD)]

# ------------------------------------------------------------ training

def fit_and_score(seed: int, train_pairs, score_sets: dict, smoke: bool, log,
                  lr: float = LR, epochs: int = EPOCHS,
                  warmup_ratio: float = 0.0):
    import torch
    from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                              Trainer, TrainingArguments)
    torch.manual_seed(seed)
    np.random.seed(seed % (2**32))
    rng = random.Random(seed)
    idx = list(range(len(train_pairs)))
    rng.shuffle(idx)
    tok = AutoTokenizer.from_pretrained(MODEL_NAME)

    texts = [t for t, _ in train_pairs]
    labels = [l for _, l in train_pairs]
    encs = [tok(texts[i], truncation=True, max_length=SEQ) for i in idx]

    class DS(torch.utils.data.Dataset):
        def __len__(self):
            return len(encs)
        def __getitem__(self, i):
            e = dict(encs[i])
            e["labels"] = int(labels[idx[i]])
            return e

    def collate(feats):
        m = max(len(f["input_ids"]) for f in feats)
        pad = tok.pad_token_id or 0
        return {"input_ids": torch.tensor(
                    [f["input_ids"] + [pad] * (m - len(f["input_ids"]))
                     for f in feats]),
                "attention_mask": torch.tensor(
                    [[1] * len(f["input_ids"])
                     + [0] * (m - len(f["input_ids"])) for f in feats]),
                "labels": torch.tensor([f["labels"] for f in feats])}

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=2)
    epochs_n = 1 if smoke else epochs
    steps_per_epoch = max(1, len(encs) // BATCH)
    warmup_steps = int(warmup_ratio * steps_per_epoch * epochs_n)
    targs = TrainingArguments(
        output_dir=str(Path("/home/eileen/scratch/st1_hf") / f"seed{seed}"),
        per_device_train_batch_size=BATCH,
        num_train_epochs=epochs_n,
        learning_rate=lr,
        warmup_steps=warmup_steps,
        logging_steps=100,
        save_strategy="no",
        report_to=[],
        seed=seed,
    )
    trainer = Trainer(model=model, args=targs,
                      train_dataset=DS(), data_collator=collate)
    t0 = time.time()
    trainer.train()
    log(f"seed {seed}: trained in {time.time()-t0:.0f}s")
    model.eval()
    dev = next(model.parameters()).device

    def probs(texts):
        out = []
        with torch.no_grad():
            for i in range(0, len(texts), 64):
                enc = tok(texts[i:i + 64], truncation=True, max_length=SEQ,
                          padding=True, return_tensors="pt").to(dev)
                out.append(torch.softmax(model(**enc).logits.float(), -1).cpu())
        return torch.cat(out).numpy() if out else np.zeros((0, 2))

    return {name: probs(items) for name, items in score_sets.items()}

def auc(labels, scores) -> float:
    y = np.asarray(labels, bool)
    s = np.asarray(scores, float)
    n_pos, n_neg = int(y.sum()), int((~y).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(s)
    ranks = np.empty(len(s))
    ranks[order] = np.arange(1, len(s) + 1)
    return float((ranks[y].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))

# ------------------------------------------------------------ main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--lr", type=float, default=LR)
    ap.add_argument("--epochs", type=int, default=EPOCHS)
    ap.add_argument("--warmup-ratio", type=float, default=0.0)
    ap.add_argument("--out", default=None, help="results dir override")
    args = ap.parse_args()
    out_dir = Path(args.out) if args.out else RESULTS_DIR
    smoke = args.smoke
    seeds = SEEDS[:1] if smoke else SEEDS
    n_train = 400 if smoke else N_TRAIN
    n_val = 150 if smoke else N_VAL
    n_ood = 30 if smoke else N_OOD

    def log(m):
        print(f"[st1] {m}", flush=True)

    import torch
    log(f"cuda={torch.cuda.is_available()} "
        f"dev={torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu'}")

    real = load_real_receipts()
    log(f"real receipts: {len(real)}")
    if len(real) < GATES["min_real_receipts"]:
        print(f"REFUSED: only {len(real)} real receipts "
              f"(< {GATES['min_real_receipts']}); fail loud per pre-reg",
              flush=True)
        return 2

    # shared corpora (same for every seed; seeds vary init/shuffle only)
    rng = random.Random(seeds[0])
    train_pairs = [synth_pair(rng) for _ in range(n_train)]
    val_pairs = [synth_pair(rng) for _ in range(n_val)]
    ood = ood_texts(rng)
    half = n_ood // 2

    gate_rows = []  # (label, text, path, op)
    for r in real:
        gate_rows.append((0, r["text"], r["path"], "honest"))
        ops = REAL_OPS[:]
        rng.shuffle(ops)
        made = 0
        for op in ops:
            if made >= 4:
                break
            c = corrupt_real(r["obj"], rng, op)
            if c is None:
                continue
            gate_rows.append((1, json.dumps(c, sort_keys=True)[:1800],
                              r["path"], op))
            made += 1
    n_corr = sum(1 for x in gate_rows if x[0] == 1)
    n_hon = len(gate_rows) - n_corr
    log(f"real-gate rows: {len(gate_rows)} ({n_corr} corrupted / {n_hon} honest)")

    gate_texts = [t for _, t, _, _ in gate_rows]
    gate_labels = [l for l, _, _, _ in gate_rows]
    ood_a, ood_b = ood[:half], ood[half:]
    ood_b_conf_pmax = None  # filled per seed

    score_sets = {
        "val": [t for t, _ in val_pairs],
        "gate": gate_texts,
        "ood_a": ood_a,
        "ood_b": ood_b,
    }

    seed_rows = []
    for seed in seeds:
        sc = fit_and_score(seed, train_pairs, score_sets, smoke, log,
                           lr=args.lr, epochs=args.epochs,
                           warmup_ratio=args.warmup_ratio)
        syn_auc = auc([l for _, l in val_pairs], sc["val"][:, 1])
        real_auc = auc(gate_labels, sc["gate"][:, 1])
        honest_p = sc["gate"][np.asarray(gate_labels) == 0][:, 1]
        honest_fpr = float((honest_p > 0.5).mean()) if len(honest_p) else float("nan")
        # abstention: threshold = p90 of max-softmax on OOD half A
        pmax_a = sc["ood_a"].max(axis=1)
        thr = float(np.percentile(pmax_a, 90))
        pmax_b = sc["ood_b"].max(axis=1)
        ood_abstain = float((pmax_b < thr).mean())
        # in-domain coverage: share of real-gate rows judged (not abstained)
        gate_pmax = sc["gate"].max(axis=1)
        coverage = float((gate_pmax >= thr).mean())
        seed_rows.append({
            "seed": seed,
            "syn_auc": round(syn_auc, 4),
            "real_auc": round(real_auc, 4),
            "honest_fpr": round(honest_fpr, 4),
            "ood_threshold": round(thr, 4),
            "ood_abstain": round(ood_abstain, 4),
            "gate_coverage": round(coverage, 4),
        })
        log(f"seed {seed}: {json.dumps(seed_rows[-1])}")

    def mean(k):
        return float(np.mean([r[k] for r in seed_rows]))

    summary = {k: round(mean(k), 4) for k in
               ("syn_auc", "real_auc", "honest_fpr", "ood_abstain",
                "gate_coverage")}
    gates = {
        "GATE1_syn": summary["syn_auc"] >= GATES["syn_auc_min"],
        "GATE2_real": (summary["real_auc"] >= GATES["real_auc_min"]
                       and summary["honest_fpr"] <= GATES["honest_fpr_max"]),
        "GATE3_abstain": summary["ood_abstain"] >= GATES["ood_abstain_min"],
    }
    verdict = "KEEP" if all(gates.values()) else "KILL"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = {
        "experiment": "ST1-quilt-cell-v0",
        "pre_reg": "proposals/runs/ST1-quilt-cell-v0.md",
        "model": MODEL_NAME,
        "smoke": smoke,
        "lr": args.lr,
        "epochs": args.epochs,
        "warmup_ratio": args.warmup_ratio,
        "gates_frozen": GATES,
        "gates": gates,
        "summary_mean": summary,
        "seed_rows": seed_rows,
        "real_gate": {"receipts": len(real), "rows": len(gate_rows),
                      "corrupted": n_corr, "honest": n_hon},
        "n_train": len(train_pairs), "n_val": len(val_pairs),
        "verdict": verdict,
        "ts": time.time(),
    }
    (out_dir / "results.json").write_text(json.dumps(out, indent=2) + "\n")
    log(f"GATES: {json.dumps(gates)}")
    log(f"SUMMARY: {json.dumps(summary)}")
    print(f"[st1] VERDICT: {verdict}", flush=True)
    return 0

if __name__ == "__main__":
    sys.exit(main())
