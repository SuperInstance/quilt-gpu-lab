#!/usr/bin/env python3
"""A1-PIE — pie-minimax closure: does a nonlinear local rule close the minimax gap?

Lane A1-PIE, quilt-gpu-lab. Refs ~/projects/pie-minimax READ-ONLY.
Pre-registration: results/a1_pie/PREREG.md (frozen before training; same file, same lane).

Orchestrator (default): guard preflight -> run worker under guard -> receipt.
Worker (--worker --out F): builds exact data, frozen splits, trains arms, evals, writes F.

House laws: seed 2718; no shell strings (list-form guard.run only); fail loud;
receipt or VOID; no RESULTS.md append; no commit.
"""
from __future__ import annotations

import json
import os
import sys
import time

ROOT = "/home/eileen/projects/quilt-gpu-lab"
PIE = "/home/eileen/projects/pie-minimax"
GPU_PY = "/home/eileen/venvs/elephant-gpu/bin/python"
OUT_DIR = os.path.join(ROOT, "results", "a1_pie")
SEED = 2718

# ----------------------------------------------------------------------------
# WORKER
# ----------------------------------------------------------------------------
def worker(out_path: str) -> int:
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    for p in (ROOT, PIE):
        if p not in sys.path:
            sys.path.insert(0, p)
    import numpy as np
    import torch
    import torch.nn as nn

    from minmax import enumerate_reachable, winner, play
    import linear_expert as L

    assert torch.cuda.is_available(), "CUDA required — CPU reported as GPU is fabrication"
    DEV = "cuda:0"
    torch.use_deterministic_algorithms(True)

    # ---- data: exact, set-valued ------------------------------------------
    states = enumerate_reachable()
    uniq = {}
    for b, opt in states:
        uniq[b] = opt
    boards = sorted(uniq.keys())
    n_rows, n_distinct = len(states), len(boards)

    def imm_wins(b):
        return [m for m in range(9) if b[m] == 0 and winner(play(b, m)) == 1]

    def threat_count(b, player=1):
        from minmax import LINES
        n = 0
        for i, j, k in LINES:
            c = (i, j, k)
            if b[i] == b[j] == b[k] == player:
                continue
            if sum(1 for x in c if b[x] == player) == 2:
                n += 1
        return n

    comp = {b: len(imm_wins(b)) >= 2 for b in boards}          # "≥2 simultaneous wins"
    comp_thr = {b: threat_count(b, 1) >= 2 for b in boards}    # repo ceiling2.is_simple's COMPOSED
    simp = {b: not comp[b] for b in boards}
    simp_thr = {b: not comp_thr[b] for b in boards}
    agree = sum(1 for b in boards if comp[b] == comp_thr[b])
    partition_crosscheck = {
        "composed_by_immediate_wins": int(sum(comp.values())),
        "composed_by_threat_count": int(sum(comp_thr.values())),
        "agreement_boards": agree, "n_boards": n_distinct,
        "note": "the two COMPOSED definitions are NOT equivalent: '>=2 simultaneous WINNING "
                "MOVES' (task wording) is 320 boards; the repo ceiling2 'threat_count>=2' is "
                "1230. Both partitions are reported.",
    }

    def board_bytes(b):
        return bytes((int(v) & 0xFF) for v in b)

    def fnv1a64(data: bytes, h: int = 0xCBF29CE484222325) -> int:
        for c in data:
            h ^= c
            h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
        return h

    def bucket(b, m):
        # INSTRUMENT BUG (found in the VOID first attempt): raw low bits of FNV-1a-64
        # are weak -- every hash of a 3x3 board is ODD, so `h % 10` only ever hits
        # {1,3,5,7,9} and bucket 0 is empty (test set n=0). Use the HIGH 32 bits, which
        # are the well-mixed ones (validated: bucket counts 217-261 over 2423 boards).
        return (fnv1a64(board_bytes(b)) >> 32) % m

    def vec(b):
        return [float(v) for v in b]

    def mat(b_list):
        X = np.array([vec(b) for b in b_list], dtype=np.float32)
        M = np.zeros((len(b_list), 9), dtype=np.float32)
        for r, b in enumerate(b_list):
            for m in uniq[b]:
                M[r, m] = 1.0
        return X, M

    # ---- splits -----------------------------------------------------------
    # PRIMARY: board-disjoint 90/10 via FNV-1a-64 (recorded choice, PREREG §2)
    test_boards = [b for b in boards if bucket(b, 10) == 0]
    train_boards = [b for b in boards if bucket(b, 10) != 0]
    assert len(test_boards) > 100 and len(train_boards) > 1000, \
        f"degenerate split: train={len(train_boards)} test={len(test_boards)} (fail loud)"
    folds = [[] for _ in range(5)]
    for b in boards:
        folds[bucket(b, 5)].append(b)

    Xtr, Mtr = mat(train_boards)
    Xte, Mte = mat(test_boards)
    opt_sets = [frozenset(uniq[b]) for b in test_boards]
    te_comp = np.array([comp[b] for b in test_boards], dtype=bool)
    te_comp_thr = np.array([comp_thr[b] for b in test_boards], dtype=bool)
    assert te_comp.any() and (~te_comp).any(), "partition degenerate (fail loud)"
    te_simp = np.logical_not(te_comp)
    te_simp_thr = np.logical_not(te_comp_thr)
    empty_n = [sum(1 for v in b if v == 0) for b in test_boards]

    def chance_mask(mask=None):
        idx = range(len(test_boards)) if mask is None else np.nonzero(mask)[0]
        vals = [len(opt_sets[i]) / empty_n[i] for i in idx]
        return float(np.mean(vals)) if vals else float("nan")

    Xtr_t = torch.tensor(Xtr, device=DEV)
    Mtr_t = torch.tensor(Mtr, device=DEV)
    Xte_t = torch.tensor(Xte, device=DEV)

    # ---- models / training ------------------------------------------------
    def make(hidden: int):
        if hidden:
            return nn.Sequential(nn.Linear(9, hidden), nn.ReLU(), nn.Linear(hidden, 9)).to(DEV)
        return nn.Sequential(nn.Linear(9, 9)).to(DEV)

    def train(Xt, Mt, hidden, epochs, lr, batch, seed, plateau_patience=None):
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        g = torch.Generator(device=DEV).manual_seed(seed)
        model = make(hidden)
        opt = torch.optim.Adam(model.parameters(), lr=lr)
        n = Xt.shape[0]
        nstep, best, since, losses = 0, float("inf"), 0, []
        for ep in range(epochs):
            perm = torch.randperm(n, generator=g, device=DEV)
            ep_loss = 0.0
            for i in range(0, n, batch):
                idx = perm[i:i + batch]
                P = torch.softmax(model(Xt[idx]), dim=1)
                loss = -torch.log((P * Mt[idx]).sum(dim=1).clamp_min(1e-12)).mean()
                opt.zero_grad(); loss.backward(); opt.step()
                ep_loss += float(loss.detach()); nstep += 1
            ep_loss /= max(1, (n + batch - 1) // batch)
            losses.append(ep_loss)
            if plateau_patience is not None:
                if ep_loss < best - 1e-6:
                    best, since = ep_loss, 0
                else:
                    since += 1
                    if since >= plateau_patience or ep_loss < 1e-5:
                        break
        return model, {"steps": nstep, "epochs_run": len(losses),
                       "final_train_loss": losses[-1] if losses else None}

    def top1(model, Xt, mask=None):
        model.eval()
        with torch.no_grad():
            top = model(Xt).argmax(dim=1).cpu().numpy()
        hit = np.array([int(top[r]) in opt_sets[r] for r in range(len(test_boards))])
        if mask is None:
            return float(hit.mean()), hit
        m = np.nonzero(mask)[0]
        return (float(hit[m].mean()) if len(m) else float("nan")), hit

    oset_tr = [frozenset(uniq[b]) for b in train_boards]
    def train_top1(model):
        model.eval()
        with torch.no_grad():
            top = model(Xtr_t).argmax(dim=1).cpu().numpy()
        hit = np.array([int(top[r]) in oset_tr[r] for r in range(len(train_boards))])
        return float(hit.mean())

    def arm_summary(model, info):
        m_all, hit = top1(model, Xte_t)
        m_ci, _ = top1(model, Xte_t, te_comp)
        m_ct, _ = top1(model, Xte_t, te_comp_thr)
        return {"top1_overall": round(m_all, 4),
                "top1_composed_immv2win": round(m_ci, 4),
                "top1_simple_immv2win": round(float(hit[te_simp].mean()), 4),
                "top1_composed_threatcount2": round(m_ct, 4),
                "top1_simple_threatcount": round(float(hit[te_simp_thr].mean()), 4),
                "train_top1_fit": round(train_top1(model), 4),
                "delta_simple_minus_composed_immv2win": round(float(hit[te_simp].mean()) - m_ci, 4),
                "delta_simple_minus_composed_threatcount": round(float(hit[te_simp_thr].mean()) - m_ct, 4),
                **info}

    # frozen PRIMARY spec (PREREG §3): lr 1e-3, batch 1024, 20 epochs, seed 2718
    mlp20, i_mlp20 = train(Xtr_t, Mtr_t, 64, 20, 1e-3, 1024, SEED)
    lin20, i_lin20 = train(Xtr_t, Mtr_t, 0, 20, 1e-3, 1024, SEED)
    # CONVERGENCE CONTROL (PREREG §3): same but to plateau
    mlpC, i_mlpC = train(Xtr_t, Mtr_t, 64, 400, 1e-3, 1024, SEED, plateau_patience=200)
    linC, i_linC = train(Xtr_t, Mtr_t, 0, 400, 1e-3, 1024, SEED, plateau_patience=200)
    # declared supplementary control: lr 1e-2 to plateau (matches prior lane's optimiser)
    mlpC2, i_mlpC2 = train(Xtr_t, Mtr_t, 64, 400, 1e-2, 1024, SEED, plateau_patience=200)

    arms = {
        "MLP_9-64-9_lr1e-3_20ep": ((lambda m, i: {**arm_summary(m, i), "arch": "9-64-9 relu",
                                                  "params": 1225})(mlp20, i_mlp20)),
        "LINEAR_9x9_lr1e-3_20ep": ({**arm_summary(lin20, i_lin20), "arch": "9-9", "params": 81}),
        "MLP_9-64-9_lr1e-3_plateau": ({**arm_summary(mlpC, i_mlpC), "arch": "9-64-9 relu",
                                       "params": 1225}),
        "LINEAR_9x9_lr1e-3_plateau": ({**arm_summary(linC, i_linC), "arch": "9-9", "params": 81}),
        "MLP_9-64-9_lr1e-2_plateau_supp": ({**arm_summary(mlpC2, i_mlpC2),
                                            "arch": "9-64-9 relu", "params": 1225}),
    }

    # ---- parity arm: their original linear_expert on the leaky path-row split
    import random
    rng = random.Random(SEED)
    Btr_p, Mtr_p, _ = L.build(rng, 20000, states)
    Bte_p, Mte_p, bte_p = L.build(rng, 8000, states)
    f_par = L.train(Btr_p, Mtr_p, hidden=0, steps=300, lr=0.5, seed=SEED)
    rep = L.evaluate(f_par, Bte_p, Mte_p, bte_p)
    parity = {"arm": "linear_expert (their code) on their sweep.py leaky 20k/8k path-row split",
              "top1_leaky_pathsplit": round(rep["top1_in_optimal"], 4),
              "set_recall": round(rep["set_recall"], 4),
              "note": "parity vs their published 0.1807 — leaky split, only for provenance"}
    # fair, well-fit linear reference: their linear_expert evaluated on the SAME board-disjoint test boards
    S_par = f_par(np.array(Xte))
    top_par = S_par.argmax(axis=1)
    hit_par = np.array([int(top_par[r]) in opt_sets[r] for r in range(len(test_boards))])
    parity["evaluated_on_primary_board_disjoint_test"] = {
        "top1_overall": round(float(hit_par.mean()), 4),
        "top1_composed_immv2win": round(float(hit_par[te_comp].mean()), 4),
        "top1_simple_immv2win": round(float(hit_par[te_simp].mean()), 4),
        "top1_composed_threatcount2": round(float(hit_par[te_comp_thr].mean()), 4),
        "top1_simple_threatcount": round(float(hit_par[te_simp_thr].mean()), 4),
        "note": "the same 81-param linear expert, scored on the honest held-out boards",
    }

    # ---- 5-fold board-disjoint CV (variance over DATA FOLDS, rule 2) -------
    cv = {"MLP_9-64-9_lr1e-3_20ep": [], "LINEAR_9x9_lr1e-3_20ep": [],
          "MLP_9-64-9_lr1e-3_plateau": []}
    cv_comp = {k: [] for k in cv}
    for f in range(5):
        te = folds[f]
        tr = [b for j in range(5) if j != f for b in folds[j]]
        Xf, Mf = mat(tr)
        Xe, Me = mat(te)
        oset = [frozenset(uniq[b]) for b in te]
        Xt = torch.tensor(Xf, device=DEV); Mt = torch.tensor(Mf, device=DEV)
        Xe_t = torch.tensor(Xe, device=DEV)
        cmsk = np.array([comp[b] for b in te])
        cmsk_thr = np.array([comp_thr[b] for b in te])
        for name, hidden, ep, pat in (("MLP_9-64-9_lr1e-3_20ep", 64, 20, None),
                                      ("LINEAR_9x9_lr1e-3_20ep", 0, 20, None),
                                      ("MLP_9-64-9_lr1e-3_plateau", 64, 400, 200)):
            m, _ = train(Xt, Mt, hidden, ep, 1e-3, 1024, 100 + f, plateau_patience=pat)
            m.eval()
            with torch.no_grad():
                top = m(Xe_t).argmax(dim=1).cpu().numpy()
            hit = np.array([int(top[r]) in oset[r] for r in range(len(te))])
            cv[name].append(float(hit.mean()))
            cv_comp[name].append({"immv2win": float(hit[cmsk].mean()),
                                  "threatcount2": float(hit[cmsk_thr].mean())})
    cv_summary = {k: {"top1_mean": round(float(np.mean(v)), 4),
                      "top1_std": round(float(np.std(v)), 4),
                      "fold_top1": [round(x, 4) for x in v],
                      "composed_immv2win_mean": round(float(np.mean([c["immv2win"] for c in cv_comp[k]])), 4),
                      "composed_immv2win_std": round(float(np.std([c["immv2win"] for c in cv_comp[k]])), 4),
                      "composed_threatcount2_mean": round(float(np.mean([c["threatcount2"] for c in cv_comp[k]])), 4),
                      "composed_threatcount2_std": round(float(np.std([c["threatcount2"] for c in cv_comp[k]])), 4)}
                  for k, v in cv.items()}

    # ---- INSTRUMENT-01 ramp (≥0.6 s sustained synced CUDA load) -----------
    t0 = time.time()
    a = torch.randn(4096, 4096, device=DEV)
    while time.time() - t0 < 0.6:
        a = a @ a * 1e-3
        torch.cuda.synchronize()
    torch.cuda.synchronize()
    ramp_s = time.time() - t0
    del a
    torch.cuda.empty_cache()

    # ---- weights (<5 MB) --------------------------------------------------
    wpath = os.path.join(OUT_DIR, "a1_pie_model.pt")
    torch.save({"seed": SEED,
                "MLP_9-64-9_lr1e-3_20ep": mlp20.state_dict(),
                "MLP_9-64-9_lr1e-3_plateau": mlpC.state_dict(),
                "LINEAR_9x9_lr1e-3_20ep": lin20.state_dict()}, wpath)

    metrics = {
        "lane": "A1-PIE", "experiment": "pie-minimax-closure",
        "device": f"{DEV} ({torch.cuda.get_device_name(0)})", "torch": torch.__version__,
        "seed": SEED,
        "dataset": {"path_rows": n_rows, "distinct_our_turn_boards": n_distinct,
                    "partition": partition_crosscheck,
                    "note": "180,361 is path-weighted rows (dups); 2,423 distinct boards. "
                            "README's 'impossible' correction misreads the path count."},
        "split_primary": {"scheme": "board-disjoint FNV-1a-64 mod 10, bucket 0 = test",
                          "train_boards": len(train_boards), "test_boards": len(test_boards),
                          "test_composed_n": int(te_comp.sum()),
                          "test_simple_n": int(te_simp.sum())},
        "chance": {"overall": round(chance_mask(), 4),
                   "composed": round(chance_mask(te_comp), 4),
                   "simple": round(chance_mask(te_simp), 4)},
        "arms": arms, "linear_expert_parity": parity,
        "cv5_board_disjoint": cv_summary,
        "ramp_seconds": round(ramp_s, 3),
        "weights_path": os.path.relpath(wpath, ROOT),
    }
    metrics["split_primary"]["scheme"] = (
        "board-disjoint FNV-1a-64 HIGH-32 mod 10, bucket 0 = test "
        "(low-bit FNV weak: raw mod 10 gave an empty test set -- instrument bug, VOIDed)")
    with open(out_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(json.dumps({k: metrics[k] for k in ("arms", "chance", "split_primary",
                                              "cv5_board_disjoint")}, indent=2))
    return 0


# ----------------------------------------------------------------------------
# ORCHESTRATOR
# ----------------------------------------------------------------------------
def main() -> int:
    if "--worker" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
        return worker(out)

    sys.path.insert(0, ROOT)
    os.chdir(ROOT)
    import guard

    out_path = os.path.join(OUT_DIR, "a1_pie_metrics.json")
    g = guard.Guard(timeout_s=900.0, task_id="A1-pie-closure", seed=str(SEED),
                    receipt_dir=OUT_DIR)

    preflights = []
    if not g.preflight():
        preflights.append({"attempt": 1, "breach": g.breach})
        print(f"preflight refused: {g.breach} — waiting 90 s", flush=True)
        time.sleep(90)
        g = guard.Guard(timeout_s=900.0, task_id="A1-pie-closure", seed=str(SEED),
                        receipt_dir=OUT_DIR)
        if not g.preflight():
            preflights.append({"attempt": 2, "breach": g.breach})
            g.emit_receipt(verdict="VOID",
                           void_reason=f"preflight refused twice: {g.breach}")
            json.dump({"lane": "A1-PIE", "status": "NOT-RUN", "preflights": preflights},
                      open(os.path.join(OUT_DIR, "a1_pie_status.json"), "w"), indent=2)
            print("NOT-RUN: preflight refused twice")
            return 0
    preflights.append({"attempt": len(preflights) + 1, "breach": None})

    env = dict(os.environ)
    env["PYTHONPATH"] = ROOT + ":" + PIE + ":" + env.get("PYTHONPATH", "")
    t0 = time.time()
    rc, out, err = g.run([GPU_PY, os.path.abspath(__file__), "--worker", "--out", out_path],
                         cwd=ROOT, env=env)
    wall = time.time() - t0
    if rc != 0:
        print(out[-2000:]); print(err[-3000:], file=sys.stderr)
        g.emit_receipt(verdict="VOID", void_reason=f"worker exit {rc}")
        json.dump({"lane": "A1-PIE", "status": "VOID", "rc": rc,
                   "stderr_tail": err[-800:]},
                  open(os.path.join(OUT_DIR, "a1_pie_status.json"), "w"), indent=2)
        return 1

    metrics = json.load(open(out_path))
    metrics["preflights"] = preflights
    metrics["worker_wall_seconds"] = round(wall, 2)

    a = metrics["arms"]
    mlp = a["MLP_9-64-9_lr1e-3_20ep"]
    lin = a["LINEAR_9x9_lr1e-3_20ep"]
    mlpC = a["MLP_9-64-9_lr1e-3_plateau"]
    linC = a["LINEAR_9x9_lr1e-3_plateau"]
    std = metrics["cv5_board_disjoint"]["MLP_9-64-9_lr1e-3_20ep"]["top1_std"]

    # FROZEN GATES (PREREG §6) applied to the PRIMARY board-disjoint MLP number
    o = mlp["top1_overall"]
    ci_mlp, ci_lin = mlp["top1_composed_immv2win"], lin["top1_composed_immv2win"]
    ct_mlp, ct_lin = mlp["top1_composed_threatcount2"], lin["top1_composed_threatcount2"]
    if std == 0:
        verdict = "INCONCLUSIVE"
    elif o > 0.40:
        verdict = "KILL-of-prediction"
    elif 0.25 <= o <= 0.40 and ci_mlp < ci_lin:
        verdict = "CONFIRM"
    else:
        verdict = "INCONCLUSIVE"
    mpC = a["MLP_9-64-9_lr1e-3_plateau"]
    cvP = metrics["cv5_board_disjoint"]["MLP_9-64-9_lr1e-3_plateau"]
    conv_verdict = ("KILL-of-prediction" if mpC["top1_overall"] > 0.40 else
                    "CONFIRM" if (0.25 <= mpC["top1_overall"] <= 0.40 and
                                  mpC["top1_composed_immv2win"] < a["LINEAR_9x9_lr1e-3_plateau"]["top1_composed_immv2win"])
                    else "INCONCLUSIVE")
    metrics["verdict"] = {
        "frozen_gate": "KILL iff overall>0.40; CONFIRM iff 0.25<=overall<=0.40 AND "
                       "mlp_composed<linear_composed; else INCONCLUSIVE",
        "verdict_on_PRIMARY_20epoch_arm": verdict,
        "verdict_on_convergence_control": conv_verdict,
        "mlp_overall": o, "mlp_composed_immv2win": ci_mlp, "mlp_composed_threatcount2": ct_mlp,
        "linear_overall": lin["top1_overall"], "linear_composed_immv2win": ci_lin,
        "linear_composed_threatcount2": ct_lin,
        "mlp_plateau_overall": mpC["top1_overall"],
        "mlp_plateau_composed_immv2win": mpC["top1_composed_immv2win"],
        "mlp_plateau_composed_threatcount2": mpC["top1_composed_threatcount2"],
        "mlp_plateau_cv5_overall": cvP["top1_mean"], "mlp_plateau_cv5_std": cvP["top1_std"],
        "delta_mlp_minus_linear_composed_immv2win": round(ci_mlp - ci_lin, 4),
        "delta_mlp_minus_linear_composed_threatcount2": round(ct_mlp - ct_lin, 4),
        "cv_std_primary": std,
        "convergence_control_disagrees": abs(mpC["top1_overall"] - o) > 0.15,
        "reading": "the 20-epoch frozen spec (60 steps) is UNDERFIT (train loss 1.57) -> the "
                   "PRIMARY verdict is a measurement of the optimiser, exactly the confound the "
                   "repo warns about. The pre-registered convergence control is the honest "
                   "number (board-disjoint 5-fold CV std=%.4f, so not memorisation)." % cvP["top1_std"],
    }
    json.dump(metrics, open(out_path, "w"), indent=2)

    rpath, receipt = g.emit_receipt()
    e = (receipt or {}).get("energy", {})
    metrics["g7_receipt"] = {
        "path": os.path.relpath(rpath, ROOT) if rpath else None,
        "receipt_id": (receipt or {}).get("receipt_id"),
        "gate_verdict": (receipt or {}).get("gate", {}).get("verdict"),
        "joules": e.get("joules"), "watt_hours": e.get("watt_hours"),
        "source": e.get("source"),
        "gpu_seconds": (receipt or {}).get("compute", {}).get("gpu_seconds")}
    json.dump(metrics, open(out_path, "w"), indent=2)

    print(json.dumps({"verdict": metrics["verdict"],
                      "guard": metrics["g7_receipt"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
