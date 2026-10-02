#!/usr/bin/env python3
"""D2-V1 — shared frozen encoders (declared BEFORE the v1 run; EST-FREEZE fold).

Record layout harvested by experiments/d2_v1_worlds.mjs (19 ints/tick):
  [0]x [1]y [2]salC(clean*1000) [3]salD(delivered*1000) [4]fire [5]act(-1..3)
  [6]rb(ring bucket 0..15) [7]rl(ring len) [8]sem(float) [9]eta(int L1 surprise)
  [10..18] win bits 0..8  (9-bit wrapped vision reading)

FROZEN ENCODERS (determinacy read on the FULL declared channel; NEVER the salience
projection — EST-FREEZE proved fire|salience impure, purity 0.833; fire|full-channel
pure, spread 0.000).  Socket input channels FROZEN here for all 6 sockets.
"""
import json
import math
import os

LAB = "/home/eileen/projects/quilt-gpu-lab"
TR = os.path.join(LAB, "results/d2_v1/d2_v1_traces.json")
N_TRAIN = 140


def load():
    d = json.load(open(TR))
    return d


def win9(r):
    return (r[10] | (r[11] << 1) | (r[12] << 2) | (r[13] << 3) | (r[14] << 4)
            | (r[15] << 5) | (r[16] << 6) | (r[17] << 7) | (r[18] << 8))


# ---- determinacy channel phi / psi (the socket's declared I/O), O declared ----
def phi_reflex(r):
    return (r[2], win9(r))                     # FULL CHANNEL: clean salience || 9-bit window


def psi_reflex(r):
    return r[4]


def phi_surprise(r):
    return (win9(r),)                          # current observation


def psi_surprise(r):
    return min(r[9] // 222, 4)                 # integer L1 surprise, 5 declared levels


def phi_vision(r):
    return (r[0], r[1])                        # proprio position drives the wrapped reading


def psi_vision(r):
    return win9(r)


def phi_action(r):
    return (r[2] // 50, win9(r), int(r[8]) // 16, min(r[7], 64) // 8)


def psi_action(r):
    return r[5] + 1                            # 0..4 (hold=-1 -> 0)


def phi_semantic(r):
    return (r[0], r[1])


def psi_semantic(r):
    return min(int(r[8]), 63)                  # wide value space


def phi_episodic(r):
    return (r[0], r[1])                        # cell index


def psi_episodic(r):
    return r[6]                                # visit-ring content bucket


# socket -> (phi, psi, O, twin_feature_builder, twin_target_builder, target_name)
def twin_feats(r, socket):
    if socket == "reflex.orient":              # OPERATIONAL input (delivered salience): the
        return [r[3] / 1000.0] + [float(b) for b in r[10:19]]   # FIX for build A's std==0
    if socket == "world.surprise":
        return [float(b) for b in r[10:19]]
    if socket == "sensors.vision":
        return [r[0] / 15.0, r[1] / 15.0]
    if socket == "policy.action":
        return [r[2] / 1000.0] + [float(b) for b in r[10:19]] + [r[8] / 600.0, min(r[7], 64) / 64.0]
    if socket == "memory.semantic":
        return [r[0] / 15.0, r[1] / 15.0]
    if socket == "memory.episodic":
        return [r[0] / 15.0, r[1] / 15.0]
    raise ValueError(socket)


def twin_target(r, socket):
    if socket == "reflex.orient":
        return r[4]
    if socket == "world.surprise":
        return min(r[9] // 222, 4)
    if socket == "sensors.vision":
        return win9(r)
    if socket == "policy.action":
        return r[5] + 1
    if socket == "memory.semantic":
        return min(int(r[8]), 63)
    if socket == "memory.episodic":
        return r[6]
    raise ValueError(socket)


SOCKETS = [
    {"name": "reflex.orient",   "phi": phi_reflex,   "psi": psi_reflex,   "O": 2,
     "pred": 0.9, "kind": "reflex"},
    {"name": "world.surprise",  "phi": phi_surprise, "psi": psi_surprise, "O": 5,
     "pred": 0.8, "kind": "world.surprise"},
    {"name": "sensors.vision",  "phi": phi_vision,   "psi": psi_vision,   "O": 512,
     "pred": 0.6, "kind": "sensors.vision"},
    {"name": "policy.action",   "phi": phi_action,   "psi": psi_action,   "O": 5,
     "pred": 0.5, "kind": "policy.action"},
    {"name": "memory.semantic", "phi": phi_semantic, "psi": psi_semantic, "O": 64,
     "pred": 0.3, "kind": "memory.semantic"},
    {"name": "memory.episodic", "phi": phi_episodic, "psi": psi_episodic, "O": 16,
     "pred": 0.1, "kind": "memory.episodic"},
]

N_OUT = {"reflex.orient": 2, "world.surprise": 5, "sensors.vision": 512,
         "policy.action": 5, "memory.semantic": 64, "memory.episodic": 16}
