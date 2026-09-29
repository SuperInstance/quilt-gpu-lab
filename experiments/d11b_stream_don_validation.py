#!/usr/bin/env python3
"""D11b: stream-based don validation.

D11 hard-regime failure (T=5, p=0.3, hold acc 0.075) blamed the fact-holdout
signal being too thin (20 facts). Lever not tried in D11: score don proposals
by post-commit CORRELATION GAIN on the atom streams, not holdout facts.

Contract: Kev proposes edge swaps, validation = measured delta in max|corr|
between the two cells' atom streams after committing the swap (cheap, uses ALL
stream data, no held-out facts). mini-jev commits iff strict gain > 0.
Question: does this rescue partner_id / hold acc in the hard regime?
"""
import itertools, json, random

SEED = 2718
N_CELLS = 8
N_QUBITS = 6
T_STEPS = 5          # hard regime from D11
P_COUPLING = 0.3
N_DONS = 40

rng = random.Random(SEED)

def hidden_angles(cell):
    return [rng.random() * 2 * 3.14159 for _ in range(N_QUBITS)]

def atom_stream(angles, msg_angles, coupled):
    # atom k = sign of cos(hidden_k + partner_k) when coupled else sign of cos(hidden_k)
    out = []
    for t in range(T_STEPS):
        if coupled:
            out.append([1 if __import__('math').cos(a + b + 0.1 * t) > 0 else -1
                        for a, b in zip(angles, msg_angles)])
        else:
            out.append([1 if __import__('math').cos(a + 0.1 * t) > 0 else -1
                        for a, angles in [(a, None)] for a in angles])
    return out

def corr(a_stream, b_stream):
    flat_a = [x for row in a_stream for x in row]
    flat_b = [x for row in b_stream for x in row]
    n = len(flat_a)
    if n == 0:
        return 0.0
    agree = sum(1 for x, y in zip(flat_a, flat_b) if x == y)
    return abs(2 * agree / n - 1)

def main():
    # ground-truth pairing: cell i coupled with cell i^1 (derangement)
    true_partner = {i: i ^ 1 for i in range(N_CELLS)}
    angles = {i: hidden_angles(i) for i in range(N_CELLS)}

    # streams: coupled only with TRUE partner at p_coupling per step
    streams = {}
    for i in range(N_CELLL := N_CELLS):
        j = true_partner[i]
        streams[i] = []
        for t in range(T_STEPS):
            coupled = rng.random() < P_COUPLING
            if coupled:
                row = [1 if __import__('math').cos(a + b + 0.1 * t) > 0 else -1
                       for a, b in zip(angles[i], angles[j])]
            else:
                row = [1 if __import__('math').cos(a + 0.1 * t) > 0 else -1
                       for a in angles[i]]
            streams[i].append(row)

    edges = {}  # current addressing: i -> j
    for i in range(N_CELLS):
        edges[i] = rng.choice([j for j in range(N_CELLS) if j != i])

    def partner_id_acc():
        return sum(1 for i in range(N_CELLS) if edges[i] == true_partner[i]) / N_CELLS

    def hold_acc():
        # reconstruction accuracy under current addressing (same metric as D11 hold)
        correct = 0
        total = 0
        for i in range(N_CELLS):
            j = edges[i]
            for t in range(T_STEPS):
                for k in range(N_QUBITS):
                    msg_bit = 1 if __import__('math').cos(angles[j][k] + 0.1 * t) > 0 else -1
                    atom = streams[i][t][k]
                    # coupled atoms agree with true partner stream; check edge delivers it
                    if edges[i] == true_partner[i]:
                        correct += 1 if atom == msg_bit else 0
                    else:
                        correct += 0  # wrong partner: reconstruction fails here (hard regime)
                    total += 1
        return correct / total

    hist_pid = [partner_id_acc()]
    hist_acc = [hold_acc()]
    commits = 0
    reverts = 0
    for don in range(N_DONS):
        i = rng.randrange(N_CELLS)
        j = rng.choice([k for k in range(N_CELLS) if k not in (i, edges[i])])
        # stream-based score: correlation gain between i and proposed j vs current edge
        old = edges[i]
        gain = corr(streams[i], streams[j]) - corr(streams[i], streams[old])
        if gain > 1e-9:
            edges[i] = j
            commits += 1
        else:
            reverts += 1
        hist_pid.append(partner_id_acc())
        hist_acc.append(hold_acc())

    res = {
        "seed": SEED, "regime": f"T={T_STEPS}, p={P_COUPLING}",
        "n_dons": N_DONS, "commits": commits, "reverts": reverts,
        "final_partner_id": hist_pid[-1], "final_hold_acc": hist_acc[-1],
        "pid_history": hist_pid, "acc_history": hist_acc,
        "bars": {"partner_id": 0.9, "hold_acc": 0.9},
    }
    print(json.dumps({k: v for k, v in res.items() if "history" not in k}, indent=2))
    with open("results/d11b_stream_don_validation.json", "w") as f:
        json.dump(res, f, indent=2)

    verdict = "KEEP" if hist_pid[-1] >= 0.9 and hist_acc[-1] >= 0.9 else "KILL"
    print("VERDICT:", verdict)

if __name__ == "__main__":
    main()
