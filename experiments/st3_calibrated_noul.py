#!/usr/bin/env python3
"""ST3 — calibrated noul cell on frozen features (quilt-gpu-lab).

Pre-registration: proposals/runs/ST3-calibrated-noul.md
Commit + push the pre-reg BEFORE firing. --smoke before full. Book honestly.

Design (see pre-reg for fleet citations):
  * frozen MiniLM embeddings, head-only training      (jeff readout unlock)
  * calibration gates: ECE + Brier vs base rate       (proper scoring rules)
  * selective prediction, risk-coverage curves        (canons: distribution)
  * non-circular OOD A/B abstention                   (kept from ST1)
  * shuffled-label control arm must FAIL              (QC-JEV doctrine)
  * plain torch loop — NO TrainingArguments           (transformers 5.17 trap)

Schema: st3-calibrated-noul/v1
"""
import argparse, json, os, sys, time
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import roc_auc_score

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SEEDS = (6611, 6612, 6613, 6614, 6615)
MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# --------------------------------------------------------------------- corpus
def load_corpus(n_syn: int, seed: int, smoke: bool):
    """Mirrors ST1's generator verbatim (make_example -> corrupt/render, real
    gate rows, same rng call order) so corpus + ops stay IDENTICAL to ST1 —
    gates are only comparable on ST1's corpus. Only delta: synth items keep
    their op tag (ST1 discards it) for the OOD-by-op split.
    Label convention (ST1): 1 = corrupted, 0 = honest/clean.
    Item shape: {'text': str, 'label': 0|1, 'op': str, 'real': bool};
    'real' marks real results.json receipts (incl. value_swap real-only ops).
    """
    import random as _random
    sys.path.insert(0, REPO)
    import experiments.st1_quilt_cell_v0 as st1  # noqa: E402
    rng = _random.Random(seed)
    items = []
    for _ in range(n_syn):
        ex = st1.make_example(rng)
        if rng.random() < 0.5:
            op = rng.choice(st1.SYN_OPS)
            ex = st1.corrupt_example(ex, rng, op)
            label, opname = 1, op
        else:
            label, opname = 0, "honest"
        items.append({"text": st1.render(ex, rng.choice(["template", "json"])),
                      "label": label, "op": opname, "real": False})
    real = st1.load_real_receipts()
    if len(real) < 10 and not smoke:
        raise RuntimeError("FAIL-LOUD: <10 real receipts (pre-reg forbids KEEP).")
    for r in real:
        items.append({"text": r["text"], "label": 0, "op": "honest",
                      "real": True})
        ops = list(st1.REAL_OPS)
        rng.shuffle(ops)
        made = 0
        for op in ops:
            if made >= 4:
                break
            c = st1.corrupt_real(r["obj"], rng, op)
            if c is None:
                continue
            items.append({"text": json.dumps(c, sort_keys=True)[:1800],
                          "label": 1, "op": op, "real": True})
            made += 1
    return items

def to_arrays(raw):
    """Normalize loader output -> dict of np arrays: texts, labels, ops, real."""
    items = raw if isinstance(raw, list) else raw.get("items") or raw.get("receipts")
    if items is None:
        raise RuntimeError(f"ST3 WIRE-UP: unexpected corpus shape: {type(raw)}")
    keys = set(items[0].keys())
    if not {"text", "label", "op"} <= keys:
        raise RuntimeError(f"ST3 WIRE-UP: item keys {sorted(keys)} lack text/label/op")
    return {
        "texts":  [it["text"] for it in items],
        "labels": np.array([int(it["label"]) for it in items], dtype=np.int64),
        "ops":    [it["op"] for it in items],
        "real":   np.array([bool(it.get("real", False)) for it in items], dtype=bool),
    }

# -------------------------------------------------------------------- encoder
def get_encoder(device):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL, device=device)

def encode(enc, texts, bs=256):
    emb = enc.encode(list(texts), batch_size=bs, convert_to_numpy=True,
                     normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(emb, dtype=np.float32)

# ----------------------------------------------------------------------- head
class NoulHead(nn.Module):
    def __init__(self, d: int, hidden: int = 0):
        super().__init__()
        self.net = (nn.Sequential(nn.Linear(d, hidden), nn.GELU(), nn.Linear(hidden, 1))
                    if hidden else nn.Linear(d, 1))
    def forward(self, x):
        return self.net(x).squeeze(-1)

def train_head(Xtr, ytr, Xva, yva, lr, epochs, hidden, device, seed):
    torch.manual_seed(seed); np.random.seed(seed % (2**31))
    model = NoulHead(Xtr.shape[1], hidden).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    Xtr_t = torch.from_numpy(Xtr).to(device)
    ytr_t = torch.from_numpy(ytr.astype(np.float32)).to(device)
    Xva_t = torch.from_numpy(Xva).to(device)
    yva_t = torch.from_numpy(yva.astype(np.float32)).to(device)
    lossf = nn.BCEWithLogitsLoss()
    best_state, best_nll = None, float("inf")
    for _ in range(epochs):
        model.train(); opt.zero_grad()
        loss = lossf(model(Xtr_t), ytr_t)
        loss.backward(); opt.step()
        model.eval()
        with torch.no_grad():
            va = lossf(model(Xva_t), yva_t).item()
        if va < best_nll - 1e-5:
            best_nll = va
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
    if best_state is not None:
        model.load_state_dict(best_state)
    return model, best_nll

def fit_temperature(model, Xva, yva, device, iters=300):
    logT = torch.zeros(1, device=device, requires_grad=True)
    Xva_t = torch.from_numpy(Xva).to(device)
    yva_t = torch.from_numpy(yva.astype(np.float32)).to(device)
    opt = torch.optim.Adam([logT], lr=0.05)
    for _ in range(iters):
        opt.zero_grad()
        with torch.no_grad():
            z = model(Xva_t)
        nll = nn.functional.binary_cross_entropy_with_logits(z / logT.exp(), yva_t)
        nll.backward(); opt.step()
    return float(logT.exp().item())

def predict(model, T, X, device):
    model.eval()
    with torch.no_grad():
        z = model(torch.from_numpy(X).to(device)) / T
    p = torch.sigmoid(z).cpu().numpy()
    return p, np.maximum(p, 1.0 - p)  # probs, max-prob confidence

# -------------------------------------------------------------------- metrics
def ece(conf, correct, bins=15):
    idx = np.minimum((np.asarray(conf) * bins).astype(int), bins - 1)
    correct = np.asarray(correct, dtype=np.float64)
    e = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            e += m.mean() * abs(correct[m].mean() - float(np.mean(conf[m])))
    return float(e)

def risk_coverage(conf, correct):
    order = np.argsort(-np.asarray(conf))
    err = 1.0 - np.asarray(correct, dtype=np.float64)[order]
    risk = np.cumsum(err) / np.arange(1, len(err) + 1)
    cov = np.arange(1, len(err) + 1) / len(err)
    return cov, risk

def risk_at(cov, risk, target):
    m = cov >= target
    return float(risk[m][0]) if m.any() else float(risk[-1])

# ------------------------------------------------------------------ selftests
def toy_calibration_selftest(n=20000, seed=7):
    """Known-calibrated synthetic must score ECE ~0 (catches broken ECE math)."""
    rng = np.random.default_rng(seed)
    conf = rng.uniform(0.05, 0.95, n)
    correct = (rng.uniform(0, 1, n) < conf).astype(np.float64)
    e = ece(conf, correct)
    return e, e < 0.05

# ------------------------------------------------------------------ one seed
def run_seed(seed, corpus_raw, enc, device, args):
    d = to_arrays(corpus_raw)
    emb = encode(enc, d["texts"])
    labels, ops, real = d["labels"], np.array(d["ops"]), d["real"]

    syn = ~real
    ood_ops = sorted(set(ops[syn]))[-2:]          # 2 held-out ops = OOD set
    is_ood = syn & np.isin(ops, ood_ops)
    is_ind = syn & ~np.isin(ops, ood_ops)

    rng = np.random.default_rng(seed)
    ind_idx = np.where(is_ind)[0]; rng.shuffle(ind_idx)
    n = len(ind_idx); ntr, nva = int(0.70 * n), int(0.15 * n)
    tr_idx, va_idx, te_idx = ind_idx[:ntr], ind_idx[ntr:ntr + nva], ind_idx[ntr + nva:]
    ood_idx = np.where(is_ood)[0]; rng.shuffle(ood_idx)
    ood_a, ood_b = ood_idx[:len(ood_idx) // 2], ood_idx[len(ood_idx) // 2:]
    real_idx = np.where(real)[0]
    if len(real_idx) < 10 and not args.smoke:
        raise RuntimeError("FAIL-LOUD: <10 real receipts — pre-reg forbids KEEP.")

    out = {"seed": seed, "n_syn": int(syn.sum()), "n_real": int(real.sum()),
           "ood_ops": ood_ops, "arms": {}}
    for arm, hidden in (("linear", 0), ("mlp128", 128)):
        model, va_nll = train_head(emb[tr_idx], labels[tr_idx], emb[va_idx],
                                   labels[va_idx], args.lr, args.epochs, hidden,
                                   device, seed)
        T = fit_temperature(model, emb[va_idx], labels[va_idx], device)
        p_te, c_te = predict(model, T, emb[te_idx], device)
        cov, risk = risk_coverage(c_te, labels[te_idx])
        p_a, c_a = predict(model, T, emb[ood_a], device)
        p_b, c_b = predict(model, T, emb[ood_b], device)
        thr = float(np.percentile(c_a, 90))
        p_r, c_r = predict(model, T, emb[real_idx], device) if len(real_idx) else (None, None)
        rec = {
            "va_nll": va_nll, "temperature": T,
            "syn_auc": float(roc_auc_score(labels[te_idx], p_te)),
            "ece": ece(p_te, labels[te_idx]),
            "brier": float(np.mean((p_te - labels[te_idx]) ** 2)),
            "base_brier": float(np.mean((labels[te_idx].mean() - labels[te_idx]) ** 2)),
            "risk_at_cov90": risk_at(cov, risk, 0.90),
            "risk_at_cov95": risk_at(cov, risk, 0.95),
            "ood_abstain_b": float((c_b < thr).mean()),
            "false_abstain_ind": float((c_te < thr).mean()),
            "abstain_thr_oodA_p90": thr,
        }
        if len(real_idx):
            rec["real_auc"] = float(roc_auc_score(labels[real_idx], p_r))
            rec["honest_fpr"] = float(((p_r >= 0.5) & (labels[real_idx] == 0)).mean())
        out["arms"][arm] = rec
        if arm == "linear":
            out["risk_coverage_linear"] = {
                "cov": [round(float(x), 4) for x in cov[:: max(1, len(cov) // 64)]],
                "risk": [round(float(x), 4) for x in risk[:: max(1, len(risk) // 64)]]}

    # G6 control arm: shuffled labels MUST fail (auc ~0.5) or the harness leaks
    shuf = labels[tr_idx].copy(); rng.shuffle(shuf)
    cm, _ = train_head(emb[tr_idx], shuf, emb[va_idx], labels[va_idx],
                       args.lr, args.epochs, 0, device, seed + 1)
    p_cs, _ = predict(cm, 1.0, emb[te_idx], device)
    out["control_auc"] = float(roc_auc_score(labels[te_idx], p_cs))
    return out

# --------------------------------------------------------------------- gates
def evaluate(seeds_out):
    lin = [s["arms"]["linear"] for s in seeds_out]
    mean = lambda k: float(np.mean([r[k] for r in lin if k in r]))
    gates = {
        "G1_syn_auc_ge_095": mean("syn_auc") >= 0.95,
        "G2_real_auc_ge_080_fpr_le_010": (mean("real_auc") >= 0.80
                                          and mean("honest_fpr") <= 0.10),
        "G3_calibration": (mean("ece") <= 0.05
                           and mean("brier") <= 0.7 * mean("base_brier")),
        "G4_selective": (mean("risk_at_cov90") <= 0.10
                         and mean("risk_at_cov95") <= 0.15),
        "G5_ood_abstain": (mean("ood_abstain_b") >= 0.90
                           and mean("false_abstain_ind") <= 0.20),
        "G6_control_arm": all(0.45 <= s["control_auc"] <= 0.55 for s in seeds_out),
    }
    return gates, ("KEEP" if all(gates.values()) else "KILL")

# ---------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--out", default="results/st3_calibrated_noul")
    ap.add_argument("--seeds", nargs="*", type=int, default=list(DEFAULT_SEEDS))
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--n-syn", type=int, default=8000)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()
    if args.smoke:
        args.seeds, args.n_syn, args.epochs = args.seeds[:1], 400, 5

    t0 = time.time()
    e, ok = toy_calibration_selftest()
    if not ok:
        raise RuntimeError(f"FAIL-LOUD: toy calibration selftest ECE={e:.4f} >= 0.05")
    print(f"[selftest] toy ECE={e:.4f} OK")

    enc = get_encoder(args.device)
    seeds_out = []
    for seed in args.seeds:
        corpus = load_corpus(args.n_syn, seed, args.smoke)
        r = run_seed(seed, corpus, enc, args.device, args)
        seeds_out.append(r)
        lin = r["arms"]["linear"]
        print(f"[seed {seed}] syn_auc={lin['syn_auc']:.4f} ece={lin['ece']:.4f} "
              f"brier={lin['brier']:.4f} risk@90={lin['risk_at_cov90']:.4f} "
              f"ood_abstain={lin['ood_abstain_b']:.3f} "
              f"false_abstain={lin['false_abstain_ind']:.3f} "
              f"control_auc={r['control_auc']:.4f}"
              + (f" real_auc={lin.get('real_auc', float('nan')):.4f}" if r["n_real"] else ""))

    result = {"schema": "st3-calibrated-noul/v1", "smoke": args.smoke,
              "model": MODEL, "frozen_encoder": True, "lr": args.lr,
              "epochs": args.epochs, "n_syn": args.n_syn, "seeds": args.seeds,
              "per_seed": seeds_out, "wall_s": round(time.time() - t0, 1),
              "toy_calibration_ece": e, "notes": []}
    if not args.smoke:
        gates, verdict = evaluate(seeds_out)
        result["gates"] = gates
        result["verdict"] = verdict
        print(f"[ST3] gates: {gates}\n[ST3] VERDICT: {verdict}")
    else:
        result["verdict"] = "SMOKE"
        ca = seeds_out[0]["control_auc"]
        if not 0.30 <= ca <= 0.70:
            result["notes"].append(f"smoke control_auc={ca:.3f} outside loose band")
        print(f"[ST3] smoke OK ({result['wall_s']}s)")

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "results.json"), "w") as f:
        json.dump(result, f, indent=2)
    print(f"[ST3] wrote {os.path.join(args.out, 'results.json')}")

if __name__ == "__main__":
    main()
