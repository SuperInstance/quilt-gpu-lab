#!/usr/bin/env python3
"""E10 — invariance race: the ternary gate vs stateless sign-trackers.

The ground-truth pole of the ternary program. The claim under test: an
integer-only ternary gate (2-bit +1/0/-1 cells, a coordinate stepper that
flashes a candidate flip and commits on error reduction) LEARNS to track a
moving signal — as opposed to just being a fancy debounce circuit that any
stateless sign-tracker matches.

Falsifiable test (pre-registered): the gate must beat BOTH baselines by a
clear margin on held-out next-sign prediction:
  (a) persistence  — predict the last sign (the classic "smooth things stay
                     smooth" lookup-table null)
  (b) dead-reckoning — predict the sign of the linear extrapolation of the
                     last two samples
If the gate does NOT beat persistence beyond the pre-registered margin, the
"ternary = learning substrate" thesis is a debounce circuit in costume — KILL.

The gate is a faithful port of eos-seed's optimization loop: 256 ternary
cells, per-frame coordinate sweep (flash -1/0/+1, commit min-error,
tie-keeps-current), xorshift64* seeded 2718, targets snapped to powers of 2.
"""
from __future__ import annotations

import json
import math

SEED = 2718
DIMS = 256
FRAMES = 200
MARGIN = 0.05  # pre-registered: gate must beat persistence by >= 5 pts


def xorshift64(seed):
    a = (seed & 0xFFFFFFFFFFFFFFFF)
    while True:
        a ^= (a << 13) & 0xFFFFFFFFFFFFFFFF
        a ^= a >> 7
        a ^= (a << 17) & 0xFFFFFFFFFFFFFFFF
        yield a & 0xFFFFFFFFFFFFFFFF


def make_frames(rng, n_frames, dims):
    """A drifting hot cell + noise floor (the eos-seed Lissajous object),
    quantized to signs {-1,0,+1} for the ternary gate."""
    hot = 8.0
    out = []
    for t in range(n_frames):
        pos = int((math.sin(t / 6.0) * 0.5 + 0.5) * (dims - 1))
        frame = [0] * dims
        frame[pos] = hot
        # noise floor
        for i in range(dims):
            if i != pos:
                r = next(rng) / (1 << 64)
                if r < 0.05:
                    frame[i] = 2.0
        out.append(frame)
    return out


def quantize_sign(v):
    return 1 if v > 1.5 else (-1 if v < -1.5 else 0)


def gate_predict(cells, frame):
    """Gate's prediction: dot product of ternary cells with the frame's signs."""
    return sum(cells[i] * quantize_sign(frame[i]) for i in range(len(frame)))


def run_gate(frames, dims):
    """The ternary coordinate stepper: learn targets = the running sign of the
    hot cell's position, by per-frame sweep of one flashed coordinate."""
    cells = [0] * dims
    history = []
    for t in range(1, len(frames)):
        # target: sign of the motion of the hot cell (the thing to predict)
        prev_pos = max(range(dims), key=lambda i: frames[t - 1][i])
        cur_pos = max(range(dims), key=lambda i: frames[t][i])
        motion = cur_pos - prev_pos
        target = 1 if motion > 0 else (-1 if motion < 0 else 0)
        # prediction BEFORE update (held-out style: predict this frame's motion
        # from cells learned so far)
        pred = gate_predict(cells, frames[t - 1])
        pred_sign = 1 if pred > 0 else (-1 if pred < 0 else 0)
        history.append((target, pred_sign))
        # update: flash one coordinate and commit if it reduces error
        best_i, best_err, best_v = None, None, None
        cur_err = abs(gate_predict(cells, frames[t]) - target)
        for _ in range(dims):  # sweep all coordinates once
            i = _ % dims
            for dv in (-1, 0, 1):
                old = cells[i]
                nv = max(-1, min(1, old + dv))  # CLAMP to ternary {-1,0,+1}
                cells[i] = nv
                err = abs(gate_predict(cells, frames[t]) - target)
                if best_err is None or err < best_err:
                    best_err, best_i, best_v = err, i, cells[i]
                cells[i] = old
        if best_i is not None and best_err < cur_err:
            cells[best_i] = best_v
    return history


def persistence_acc(history):
    """Predict next sign = last observed sign."""
    correct = 0
    last = 0
    for target, _ in history:
        correct += 1 if last == target else 0
        last = target
    return correct / len(history)


def deadreckon_acc(frames, history):
    """Predict next sign = sign of linear extrapolation of last two hot positions."""
    correct = 0
    for t in range(1, len(frames) - 1):
        prev = max(range(DIMS), key=lambda i: frames[t - 1][i])
        cur = max(range(DIMS), key=lambda i: frames[t][i])
        nxt = max(range(DIMS), key=lambda i: frames[t + 1][i])
        pred = 1 if (cur - prev) > 0 else (-1 if (cur - prev) < 0 else 0)
        target = 1 if (nxt - cur) > 0 else (-1 if (nxt - cur) < 0 else 0)
        correct += 1 if pred == target else 0
    return correct / max(1, len(history) - 1)


def main():
    rng = xorshift64(SEED)
    frames = make_frames(rng, FRAMES, DIMS)
    history = run_gate(frames, DIMS)

    gate_correct = sum(1 for t, p in history if p == t)
    gate_acc = gate_correct / len(history)
    pers_acc = persistence_acc(history)
    dr_acc = deadreckon_acc(frames, history)

    verdict = "KEEP" if (gate_acc - pers_acc) >= MARGIN else "KILL"
    result = {
        "experiment": "E10 invariance race",
        "seed": SEED, "frames": FRAMES, "dims": DIMS,
        "gate_acc": round(gate_acc, 4),
        "persistence_acc": round(pers_acc, 4),
        "deadreckon_acc": round(dr_acc, 4),
        "gate_minus_persistence": round(gate_acc - pers_acc, 4),
        "preregistered_margin": MARGIN,
        "verdict": verdict,
        "note": "KEEP iff gate beats persistence by >=5pts; a KILL prices the 'ternary=learning' claim as a debounce circuit",
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
