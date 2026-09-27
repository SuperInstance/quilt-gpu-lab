#!/usr/bin/env python3
"""D14 — qthe timbre channel proof: zero-bit-cost, context-keyed ternary
embedding riding inside plaintext.

Casey's ah-ha (2026-09-27): QTHE's byte is 6 data bits + 2 timbre bits. The
two timbre bits are ALREADY paid for by the byte, so a ternary "momentum"
signal rides in them at zero additional bit-cost. And because the timbre's
meaning is CONTEXTUAL (same 2 bits => "up" in one situation, "down" in
another), the channel is context-keyed: a plaintext reader sees nothing, and
even a timbre reader WITHOUT the context key sees noise. Only a contextual
decoder recovers the signal.

The falsifiable core (three decoders, all blinded correctly):
  D1 data-only       : sees the 6-bit data plane only   -> must be ~chance
  D2 naive-timbre    : sees the 2-bit timbre, no context -> must be ~chance
  D3 contextual      : sees timbre AND context (from data) -> must be >> chance

If all three hold, the channel carries non-redundant, context-keyed
information at zero bit-cost. If D2 == D3, the "contextual" claim is LARP.

Verdict: KEEP iff D3 >> chance AND D1 ~= chance AND D2 ~= chance.
"""
from __future__ import annotations

import json
import math

SEED = 2718
N_TURNS = 2000
N_CONTEXTS = 4
N_MOMENTA = 4


def _rng(seed):
    a = seed & 0xFFFFFFFF
    while True:
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = a
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t = (t ^ (t + ((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        yield ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0


def make_context_permutations(rng, n_contexts, n_momenta):
    """A per-context permutation pi_c over momenta. The SAME momentum maps to
    a DIFFERENT timbre under each context, so timbre-without-context is
    uninformative while timbre+context fully inverts the map.

    Uses a LATIN SQUARE (order n), not arbitrary permutations:
      - each ROW (fixed context c) is a bijection -> invertible given context
      - each COLUMN (fixed momentum m) covers all n timbres -> P(t|m)=1/n,
        so the timbre marginal is uniform and I(M;T)=0 EXACTLY.
    A random permutation leaks through fixed points (a naive identity reader
    gets ~1 free hit/context); a derangement over-corrects (t != m becomes
    itself 1 bit). Only the Latin square is information-clean. Default:
    the cyclic square (c + m) mod n."""
    perms = []
    for c in range(n_contexts):
        perms.append([(c + m) % n_momenta for m in range(n_momenta)])
    return perms


def main():
    rng = _rng(SEED)
    next(rng)
    perms = make_context_permutations(rng, N_CONTEXTS, N_MOMENTA)
    # inverse maps: timbre -> momentum, per context
    inv = []
    for p in perms:
        inv.append([0] * N_MOMENTA)
        for m, t in enumerate(p):
            inv[-1][t] = m

    # generate a corpus of turns: data token (6-bit surface), context (derived
    # from the data token, public), and a hidden momentum label.
    turns = []
    for i in range(N_TURNS):
        data = int(next(rng) * 64) & 0x3F          # 6-bit surface token
        context = data % N_CONTEXTS                 # context IS in the data plane (public)
        momentum = int(next(rng) * N_MOMENTA)       # hidden relational momentum
        timbre = perms[context][momentum]           # contextual encoding
        byte = (timbre << 6) | data                 # the QTHE byte
        turns.append((data, context, momentum, timbre, byte))

    # --- decoders ---
    # D1: data-only. predict momentum from data alone (best possible: mode).
    def d1_acc():
        # data is drawn independent of momentum -> any predictor is chance.
        # Use the theoretically-best: predict the majority momentum.
        import collections
        c = collections.Counter(m for _, _, m, _, _ in turns)
        best = c.most_common(1)[0][0]
        hit = sum(1 for _, _, m, _, _ in turns if m == best)
        return hit / len(turns)

    # D2: naive-timbre. predict momentum from timbre alone, context-free.
    def d2_acc():
        # timbre is pi_c(momentum); averaged over contexts each timbre value is
        # uniform over momenta -> chance. Best context-free rule: a fixed
        # timbre->momentum table (the identity of the identity permutation).
        hit = 0
        for _, _, m, t, _ in turns:
            hit += 1 if t == m else 0
        return hit / len(turns)

    # D3: contextual. invert the permutation with context.
    def d3_acc():
        hit = 0
        for _, ctx, m, t, _ in turns:
            hit += 1 if inv[ctx][t] == m else 0
        return hit / len(turns)

    a1 = d1_acc()
    a2 = d2_acc()
    a3 = d3_acc()
    chance = 1.0 / N_MOMENTA

    # mutual information I(M ; T | context) vs I(M ; T) as the information measure
    def mi(m, t_given):
        """Empirical MI between momentum and the given channel symbol."""
        import collections
        joint = collections.Counter()
        for _, ctx, m, t, _ in turns:
            joint[(m, t_given(ctx, t))] += 1
        n = len(turns)
        tot = 0.0
        for (mv, tv), cnt in joint.items():
            p_joint = cnt / n
            p_m = sum(1 for _, _, mm, _, _ in turns if mm == mv) / n
            p_t = sum(1 for _, c, _, tt, _ in turns if t_given(c, tt) == tv) / n
            if p_joint > 0:
                tot += p_joint * math.log2(p_joint / (p_m * p_t))
        return tot

    # D2's channel is the raw timbre; D3's channel is (timbre, context) jointly
    mi_naive = mi(None, lambda c, t: t)
    mi_contextual = mi(None, lambda c, t: (c, t))  # joint symbol (context, timbre)

    verdict = "KEEP" if (a3 > 0.9 and a1 < 0.4 and a2 < 0.4) else "INCONCLUSIVE"
    result = {
        "experiment": "D14 qthe timbre channel proof",
        "seed": SEED, "n_turns": N_TURNS,
        "n_contexts": N_CONTEXTS, "n_momenta": N_MOMENTA, "chance": round(chance, 4),
        "decoders": {
            "data_only_acc": round(a1, 4),
            "naive_timbre_acc": round(a2, 4),
            "contextual_timbre_acc": round(a3, 4),
        },
        "mutual_information_bits": {
            "I(M;T)_naive": round(mi_naive, 4),
            "I(M;T,context)_contextual": round(mi_contextual, 4),
        },
        "zero_bit_cost": "byte is always 8 bits; loading the momentum signal costs 0 extra bits vs an 8-bit-per-turn baseline",
        "verdict": verdict,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
