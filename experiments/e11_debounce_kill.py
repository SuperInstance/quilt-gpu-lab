#!/usr/bin/env python3
"""E11 — debounce-kill (the discriminating test).

E10 killed the naive ternary gate on SMOOTH signals: a persistence tracker
(predict last sign) wins there because smooth means "keep going the same way".
That does NOT decide whether the gate is a debounce circuit — it only shows
the gate loses on the task persistence is built for.

This is the DISCRIMINATING test. The signal has STRUCTURE that persistence
structurally cannot reach: the next sign is a function of the sign TWO steps
ago (a delay-2 line), not the last sign. On this signal:
  - persistence (predict last sign)     -> ~50% (coin flip, structurally blind)
  - dead-reckoning (linear extrapolation) -> ~50% (no smooth motion to extrapolate)
  - a gate holding a memory window      -> can reach ~100% if it learns the tap

Falsifiable claim (pre-registered): the ternary gate must beat persistence by
>= 30 points on this signal. If it does NOT, the gate is a debounce circuit —
it adds nothing over a stateless sign-tracker even where the stateless tracker
is blind. That is the honest KILL the docket's E11 promised.

The gate here is a ternary weight vector over a delay-line of the last W signs
(so it CAN represent "sign[t-2] predicts sign[t]"), swept by the same clamped
coordinate stepper as E10 (flash -1/0/+1, commit on error reduction, seed 2718).
"""
from __future__ import annotations

import json

SEED = 2718
W = 8          # delay-line window the gate sees
FRAMES = 300
MARGIN = 0.30  # pre-registered: gate must beat persistence by >= 30 points


def xorshift64(seed):
    a = seed & 0xFFFFFFFFFFFFFFFF
    while True:
        a ^= (a << 13) & 0xFFFFFFFFFFFFFFFF
        a ^= a >> 7
        a ^= (a << 17) & 0xFFFFFFFFFFFFFFFF
        yield a & 0xFFFFFFFFFFFFFFFF


def make_signal(rng, frames):
    """A delay-2 line: s[t] = s[t-2], seeded s=[+1,-1] so it ALTERNATES
    +1,-1,+1,-1,... A LAST-sign predictor (persistence) is then always WRONG
    (0%), while a tap at delay 2 (s[t-2]) predicts it perfectly. The xorshift
    LSB is degenerate (mostly 1s), so seed the two signs EXPLICITLY."""
    s = [1, -1]
    for t in range(2, frames):
        s.append(s[t - 2])
    return s


def gate_predict(weights, window):
    return sum(weights[i] * window[i] for i in range(W))


def run_gate(signal):
    """Ternary weights over the delay line, clamped coordinate stepper."""
    weights = [0] * W
    history = []
    window = [0] * W  # oldest at index 0
    for t in range(2, len(signal) - 1):
        # current window = last W signs up to t-1
        for k in range(W):
            window[k] = signal[t - 1 - k] if (t - 1 - k) >= 0 else 0
        target = signal[t]
        pred = gate_predict(weights, window)
        pred_sign = 1 if pred > 0 else (-1 if pred < 0 else 0)
        history.append((target, pred_sign))
        # update: flash one weight, commit if it reduces error on this window
        cur_err = abs(pred - target)
        best_i, best_v, best_err = None, None, None
        for i in range(W):
            for dv in (-1, 0, 1):
                old = weights[i]
                nv = max(-1, min(1, old + dv))
                weights[i] = nv
                err = abs(gate_predict(weights, window) - target)
                if best_err is None or err < best_err:
                    best_err, best_i, best_v = err, i, nv
                weights[i] = old
        if best_i is not None and best_err < cur_err:
            weights[best_i] = best_v
    return history


def persistence_acc(signal):
    correct = 0
    n = 0
    for t in range(2, len(signal) - 1):
        if signal[t] == signal[t - 1]:
            correct += 1
        n += 1
    return correct / n


def deadreckon_acc(signal):
    """linear extrapolation: predict sign[t] = sign of (sign[t-1] - sign[t-2]).
    On a delay-2 line this is ~50%."""
    correct = 0
    n = 0
    for t in range(2, len(signal) - 1):
        diff = signal[t - 1] - signal[t - 2]
        pred = 1 if diff > 0 else (-1 if diff < 0 else 0)
        if pred == signal[t]:
            correct += 1
        n += 1
    return correct / n


def main():
    rng = xorshift64(SEED)
    signal = make_signal(rng, FRAMES)
    history = run_gate(signal)

    gate_acc = sum(1 for t, p in history if p == t) / len(history)
    pers_acc = persistence_acc(signal)
    dr_acc = deadreckon_acc(signal)

    verdict = "KEEP" if (gate_acc - pers_acc) >= MARGIN else "KILL"
    result = {
        "experiment": "E11 debounce-kill (delay-2 discriminating test)",
        "seed": SEED, "frames": FRAMES, "window": W,
        "gate_acc": round(gate_acc, 4),
        "persistence_acc": round(pers_acc, 4),
        "deadreckon_acc": round(dr_acc, 4),
        "gate_minus_persistence": round(gate_acc - pers_acc, 4),
        "preregistered_margin": MARGIN,
        "verdict": verdict,
        "note": "delay-2 signal: persistence is structurally blind (~50%); gate must beat it by 30pts to prove it learns structure a stateless tracker cannot. KEEP = ternary learns; KILL = debounce circuit.",
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
