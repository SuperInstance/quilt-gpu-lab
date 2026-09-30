"""DECIDE-1 — read-sideways decision cell on the 4050 (zero-shot + reader ladder).
Pre-reg: proposals/runs/DECIDE-1-decision-cell.md (incl. AMENDMENT 1 + G4)."""
import sys, json, math, random, time
import numpy as np, torch
sys.path.insert(0, "tools"); sys.path.insert(0, "experiments")
from qg2_scale_lane import TEMPLATES, PAD, exact_balance   # calibrated physics + gate vocabulary
from decision_cell import DecisionCell, options_of

ANG = {0.25: "π/4", 0.5: "π/2", 0.75: "3π/4", 1.0: "π"}
def gtxt(gate):
    n = gate[0]
    if n == "h": return f"H (Hadamard) on qubit {gate[1]}"
    if n == "x": return f"X (NOT) on qubit {gate[1]}"
    if n == "rx": return f"RX({ANG[gate[1]]}) rotation on qubit {gate[2]}"
    if n == "rz": return f"RZ({ANG[gate[1]]}) phase rotation on qubit {gate[2]}"
    if n == "cx": return f"CX (controlled-X) with control qubit {gate[1]} and target qubit {gate[2]}"
    if n == "crx": return f"controlled-RX({ANG[gate[1]]}) with control qubit {gate[2]} and target qubit {gate[3]}"
    if n == "swap": return f"SWAP between qubits {gate[1]} and {gate[2]}"
    raise ValueError(n)

def edit_text(champ, cand):
    """Describe the single edit that turns champ into cand."""
    if len(cand) == len(champ) + 1:
        i = next(i for i in range(len(cand)) if champ[:i] + cand[i+1:] == cand[:i] + cand[i+1:] and cand[:i] + cand[i+1:] == champ)
        return f"insert {gtxt(cand[i])} at step {i+1}"
    if len(cand) == len(champ) - 1:
        i = next(i for i in range(len(champ)) if champ[:i] + champ[i+1:] == cand)
        return f"delete step {i+1} ({gtxt(champ[i])})"
    i = next(i for i in range(len(champ)) if champ[i] != cand[i])
    return f"replace step {i+1} with {gtxt(cand[i])}"

def to_ids(genome):
    GID = {repr(g[0]): i for i, g in enumerate(TEMPLATES)}
    return [GID[repr(g)] for g in genome] + [PAD] * (6 - len(genome))

def bal(genomes):
    t = torch.tensor([to_ids(g) for g in genomes])
    return exact_balance(t).tolist()

def make_questions(n, seed, margin=0.02, tries=200):
    rng = np.random.default_rng(seed)
    out = []
    while len(out) < n:
        for _ in range(tries):
            L = int(rng.integers(2, 5))
            champ = [TEMPLATES[int(rng.integers(0, PAD))][0] for _ in range(L)]
            cands, seen = [], set()
            while len(cands) < 4:
                op = int(rng.integers(0, 3))
                c = [list(g) for g in champ]
                if op == 0 or L >= 6:                     # replace
                    i = int(rng.integers(0, L)); c[i] = list(TEMPLATES[int(rng.integers(0, PAD))][0])
                elif op == 1:                             # insert
                    i = int(rng.integers(0, L + 1)); c.insert(i, list(TEMPLATES[int(rng.integers(0, PAD))][0]))
                else:                                     # delete (keeps >= 2 gates)
                    if L <= 2: continue
                    del c[int(rng.integers(0, L))]
                key = repr(c)
                if key in seen or c == [list(g) for g in champ]: continue
                seen.add(key); cands.append(c)
            if len(cands) < 4: continue
            b = bal(cands)
            order = sorted(range(4), key=lambda i: -b[i])
            if b[order[0]] - b[order[1]] < margin: continue          # ambiguous -> resample
            out.append({"champ": [list(g) for g in champ], "cands": cands, "bal": b, "label": order[0]})
            break
    return out

def render(q):
    state = ("A three-qubit quantum circuit applies these gates, in order, to the state |000>:\n"
             + "\n".join(f"{i+1}. {gtxt(g)}" for i, g in enumerate(q["champ"])))
    crit = {L: edit_text(q["champ"], q["cands"][i]) for i, L in enumerate("ABCD")}
    return state, {"type": "choice", "criteria": crit,
                   "instructions": "Balance is min(P(000), P(111)) of the final state. Which single edit gives the largest balance?"}, "ABCD"[q["label"]]

def control_set(n=16, seed=99):
    rng = np.random.default_rng(seed); out = []
    for _ in range(n):
        a, b = int(rng.integers(1, 99)), int(rng.integers(1, 99))
        while a == b: b = int(rng.integers(1, 99))
        hi = "A" if a > b else "B"
        out.append((f"Two numbers: {a} and {b}.", {"type": "choice", "criteria": {"A": str(a), "B": str(b)},
                    "instructions": "Which number is larger?"}, hi))
    return out

def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 1.0)
    p = k / n; d = 1 + z*z/n
    c = (p + z*z/(2*n)) / d
    h = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return (max(0.0, c-h), min(1.0, c+h))

def run(reader, items, cell, temperature=None):
    k = 0; rows = []
    for state, q, label in items:
        r = cell.decide(state, q, temperature)
        pred = r.get("choice")
        k += int(pred == label)
        rows.append({"label": label, "pred": pred, "correct": pred == label, "lat": r["_latency_ms"],
                     "p": r["probabilities"], "conf": r["confidence"]})
    return {"acc": k/len(items), "k": k, "n": len(items), "cp95": wilson(k, len(items)), "rows": rows}

if __name__ == "__main__":
    n_train, n_test = 64, 64
    train = make_questions(n_train, 101); test = make_questions(n_test, 202)
    ctrl = control_set()
    print(f"generated: train {len(train)} test {len(test)} control {len(ctrl)}")
    print("label margin check:", [round(sorted(q['bal'], reverse=True)[0]-sorted(q['bal'], reverse=True)[1],3) for q in test[:6]])
    st, qq, lb = render(test[0]); print("\nsample question:\n", st, "\n", json.dumps(qq, indent=1), "\nlabel:", lb)
    json.dump({"n_train": len(train), "n_test": len(test)}, open("/tmp/decide1_smoke.json","w"))
    if "--smoke-only" in sys.argv: sys.exit(0)

    CKPT = "/home/eileen/scratch/external/jeff-checkpoints/jeff-0.8b"
    import os
    assert os.path.exists(f"{CKPT}/model.safetensors"), "weights not downloaded yet"
    res = {"n_train": len(train), "n_test": len(test), "checkpoint": CKPT}
    zs = DecisionCell(CKPT, reader="zeroshot"); tr = DecisionCell(CKPT, reader="trained")
    train_r = [render(q) for q in train]; test_r = [render(q) for q in test]
    res["G1_control_zeroshot"] = {k: v for k, v in run("zeroshot", ctrl, zs).items() if k != "rows"}
    # base probs at temperature 1 for A/B (renormalising p**(1/T) == softmax(logits/T))
    base_tr = run("zeroshot", train_r, zs, temperature=1.0)
    base_te = run("zeroshot", test_r, zs, temperature=1.0)
    res["A_zeroshot_lane"] = {k: v for k, v in base_te.items() if k != "rows"}
    # B: fit one scalar temperature on the disjoint train split
    def nll(rows, T):
        eps = 1e-12; tot = 0.0
        for r in rows:
            p = np.array(list(r["p"].values()), dtype=float) ** (1.0 / T); p = p / p.sum()
            tot -= math.log(max(p["ABCD".index(r["label"])], eps))
        return tot / len(rows)
    Ts = np.linspace(0.25, 6.0, 24); Tbest = min(Ts, key=lambda T: nll(base_tr["rows"], T))
    res["B_fitted_temperature"] = {"T": float(Tbest), "train_nll": nll(base_tr["rows"], Tbest),
                                   "acc": run("zeroshot", test_r, zs, temperature=float(Tbest))["acc"]}
    # C: fit OUR OWN linear head on frozen last-hidden states (jeff's readout, trained in minutes)
    def hidden(state, q):
        from decision_cell import decision_prompt, SYSTEM
        codes = zs.codes[:len(options_of(q)[0])]
        text = zs.processor.tokenizer.apply_chat_template(
            [{"role": "system", "content": SYSTEM}, {"role": "user", "content": decision_prompt(state, q, codes, zs.prompt_layout)}],
            tokenize=False, add_generation_prompt=True, enable_thinking=False)
        enc = zs.processor(text=[text], padding=True, return_tensors="pt")
        inp = {k: v.to(zs.device) for k, v in enc.items() if k in ("input_ids", "attention_mask")}
        with torch.inference_mode():
            return zs.backbone(**inp, use_cache=False).last_hidden_state[:, -1].float()
    Htr = torch.cat([hidden(*render(q)[:2]) for q in train]); ytr = torch.tensor([q["label"] for q in train]).to(zs.device)
    Hte = torch.cat([hidden(*render(q)[:2]) for q in test]);  yte = torch.tensor([q["label"] for q in test]).to(zs.device)
    head = torch.nn.Linear(Htr.shape[1], 4).to(zs.device); opt = torch.optim.Adam(head.parameters(), lr=3e-3)
    t0 = time.time()
    for _ in range(400):
        opt.zero_grad(); loss = torch.nn.functional.cross_entropy(head(Htr), ytr); loss.backward(); opt.step()
    with torch.inference_mode(): cpred = head(Hte).argmax(-1).cpu()
    ycpu = yte.cpu()
    acc_c = float((cpred == ycpu).float().mean())
    res["C_fitted_head"] = {"acc": acc_c, "k": int((cpred == ycpu).sum()), "n": len(ycpu),
                            "cp95": wilson(int((cpred == ycpu).sum()), len(ycpu)),
                            "fit_seconds": round(time.time() - t0, 2), "train_ce": float(loss)}
    # D: the shipped trained readout (what jeff actually serves)
    res["D_trained_readout_lane"] = {k: v for k, v in run("trained", test_r, tr).items() if k != "rows"}
    res["D_trained_readout_control"] = {k: v for k, v in run("trained", ctrl, tr).items() if k != "rows"}
    res["hardware"] = {"device": zs.device,
                       "peak_vram_gib": round(torch.cuda.max_memory_allocated() / 2**30, 3) if zs.device == "cuda" else None,
                       "median_latency_ms": float(np.median([r["lat"] for r in base_te["rows"]]))}
    res["random_baseline"] = 0.25
    json.dump(res, open("results/decide1/decide1_results.json", "w"), indent=1, default=float)
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=1, default=float)[:2000])
