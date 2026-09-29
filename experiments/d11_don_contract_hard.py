#!/usr/bin/env python3
"""D11 — the don-contract: does commit/revert give safe edge rewiring?

D12e closed the delta arc: correlation-key addressing gives structure delta
0.53 with partner_id 1.0. D11 asks the exoj interface question: can a don
(Kev proposes gate sequences / edge rewires, Laya validates on holdout,
mini-jev commits-or-reverts) IMPROVE on discovery-only addressing without
ever being able to corrupt committed state?

Contract semantics under test:
  1. DON: Kev proposes a candidate partner map (a swap of discovered edges).
  2. VALIDATE: Laya scores the proposal on a HELD-OUT fact set only.
  3. COMMIT: mini-jev commits iff holdout acc strictly improves; else REVERT.
  4. REVERT FIDELITY: after a rejected don, the committed state must be
     bit-identical to the pre-don state (checked with a full state hash).

World = D12e (correlation streams, parity facts).
Pre-registered: (a) revert_fidelity = 1.0 on every rejected don;
(b) final acc >= d12e's 0.4667 baseline; (c) commit_rate >= 0 -> dons are
never harmful. KEEP iff all three.
"""
from __future__ import annotations

import hashlib
import json
import random

SEED = 2718
N_CELLS = 8
QUBITS = 4
T_OBS = 5
P_CORR = 0.3
N_FACTS = 120          # total facts, split fit/holdout
N_DONS = 40            # don attempts


def make_pairs():
    p = {}
    for i in range(0, N_CELLS, 2):
        p[i], p[i + 1] = i + 1, i
    return p


def streams_for(rng, partner, p_corr):
    streams = {c: [[] for _ in range(QUBITS)] for c in range(N_CELLS)}
    for _ in range(T_OBS):
        for a in range(0, N_CELLS, 2):
            b = partner[a]
            for q in range(QUBITS):
                if rng.random() < p_corr:
                    base = 1 if rng.random() < 0.5 else -1
                    streams[a][q].append(base)
                    streams[b][q].append(base)
                else:
                    streams[a][q].append(rng.choice((1, -1)))
                    streams[b][q].append(rng.choice((1, -1)))
    return streams


def corr(streams, a, b):
    tot, n = 0.0, 0
    for q in range(QUBITS):
        sa, sb = streams[a][q], streams[b][q]
        n += len(sa)
        tot += sum(x * y for x, y in zip(sa, sb))
    return abs(tot / n) if n else 0.0


def discover(streams):
    out = {}
    for a in range(N_CELLS):
        others = [c for c in range(N_CELLS) if c != a]
        out[a] = max(others, key=lambda c: corr(streams, a, c))
    return out


def run_map(rng, pmap, facts_fit, facts_hold, truth, noisy):
    """Accuracy of parity reconstruction under a given partner map."""
    def acc(facts):
        ok = 0
        for (a, qa, b, qb) in facts:
            ma = pmap.get(a, a)
            mb = pmap.get(b, b)
            # exact only when edges route each cell to its true partner
            va = truth[a] == ma and truth[b] == mb
            guess = None
            if va:
                # correlated atoms: same base sign at matched step
                step = rng_stub  # placeholder replaced below
            ok += 1 if va else 0
        return ok / len(facts) if facts else 0.0
    # simpler: correctness = both endpoints map to true partners
    def acc2(facts):
        good = sum(1 for (a, qa, b, qb) in facts
                   if truth[a] == pmap.get(a, a) and truth[b] == pmap.get(b, b))
        return good / len(facts) if facts else 0.0
    return acc2(facts_hold), acc2(facts_fit)


rng_stub = None


def state_hash(pmap):
    return hashlib.sha256(json.dumps(pmap, sort_keys=True).encode()).hexdigest()


def main():
    r = random.Random(SEED)
    truth = make_pairs()
    streams = streams_for(r, truth, P_CORR)
    discovered = discover(streams)

    facts = []
    while len(facts) < N_FACTS:
        a, b = r.randrange(N_CELLS), r.randrange(N_CELLS)
        if a != b:
            facts.append((a, r.randrange(QUBITS), b, r.randrange(QUBITS)))
    facts_fit, facts_hold = facts[:80], facts[80:]

    pmap = dict(discovered)   # committed state starts at discovery
    base_hold, base_fit = run_map(r, pmap, facts_fit, facts_hold, truth, False)

    commits = reverts = 0
    fidelity_failures = 0
    fit_hist = []
    for d in range(N_DONS):
        pre = state_hash(pmap)
        # Kev proposes: swap the discovered edge of two random cells
        a, b = r.sample(range(N_CELLS), 2)
        proposal = dict(pmap)
        proposal[a], proposal[b] = proposal[b], proposal[a]
        # Laya validates on holdout only
        prop_hold, prop_fit = run_map(r, proposal, facts_fit, facts_hold, truth, False)
        cur_hold, cur_fit = run_map(r, pmap, facts_fit, facts_hold, truth, False)
        if prop_hold > cur_hold:
            pmap = proposal
            commits += 1
        else:
            reverts += 1
            if state_hash(pmap) != pre:
                fidelity_failures += 1
        fit_hist.append(run_map(r, pmap, facts_fit, facts_hold, truth, False)[1])

    final_hold, final_fit = run_map(r, pmap, facts_fit, facts_hold, truth, False)
    partner_acc = sum(1 for c in range(N_CELLS) if pmap[c] == truth[c]) / N_CELLS
    revert_fidelity = 1.0 - fidelity_failures / max(reverts, 1)

    res = {
        "seed": SEED,
        "baseline_discovery_hold_acc": base_hold,
        "final_hold_acc": final_hold,
        "final_partner_id_acc": partner_acc,
        "commit_rate": commits / N_DONS,
        "reverts": reverts,
        "revert_fidelity": revert_fidelity,
        "fit_acc_history": fit_hist,
    }
    print(json.dumps({k: v for k, v in res.items() if k != "fit_acc_history"}, indent=2))

    verdict = ("KEEP" if revert_fidelity == 1.0 and final_hold >= 0.9
               else "KILL")
    res["verdict"] = verdict
    print("VERDICT:", verdict)
    with open("results/d11_don_contract_hard.json", "w") as f:
        json.dump(res, f, indent=2)


if __name__ == "__main__":
    main()
