#!/usr/bin/env python3
# =============================================================================
# dial_ruler.py — DIAL-LIB v0 ruler face
#
# A faithful, stdlib-only Python port of duke-lab's per-note-trace feature
# extractor and event synthesizer.
#
# SOURCE OF TRUTH (fetched & pinned 2026-10-02):
#   https://raw.githubusercontent.com/SuperInstance/duke-lab/main/engine.js
# Line numbers cited below ("engine.js L###") refer to that file at that pin.
# PORT, do not invent: every constant, threshold, RNG stream and comparison
# order below mirrors the JS so the same seed yields the same trace and the
# same 16 dial values.
#
# Dials 1..16 (engine.js L51-68), stdlib only, no third-party deps.
# urllib is used ONLY by the optional `smoke` subcommand (typesafe judgment
# cell), never by gen/measure/calibrate.
#
# CLI:
#   python3 dial_ruler.py gen --artist monk --seed 9 [--jitter 0.0]
#       -> per-note trace as JSON lines (one event object per line)
#   python3 dial_ruler.py measure --trace events.json [--artist monk] [--pretty]
#       -> the 16 dial values (JSON object; --pretty = aligned table)
#   python3 dial_ruler.py calibrate [--seeds 1,2,3,4,5]
#       -> per-artist dial-mean vs canonical centroid + error table (JSON)
#   python3 dial_ruler.py smoke --artist monk --seed 9 [--key-file PATH]
#       -> one typesafe judgment cell (swing feel score) over a take summary
#
# House style: rc=2 on any failure, loud message to stderr.
# =============================================================================

import argparse
import json
import math
import os
import sys
import urllib.error
import urllib.request

# ---------------------------------------------------------------------------
# JS numeric semantics helpers
# ---------------------------------------------------------------------------
MASK32 = 0xFFFFFFFF


def _u32(x):
    return x & MASK32


def _i32(x):
    x &= MASK32
    return x - 0x100000000 if x >= 0x80000000 else x


def _imul(a, b):
    # Math.imul: 32-bit signed multiply, returns low 32 bits as signed.
    return _i32((_u32(a) * _u32(b)) & MASK32)


def jsround(x):
    # Math.round rounds half toward +Infinity (engine.js Math.round everywhere).
    return math.floor(x + 0.5)


def js_rem(a, b):
    # JS % operator = truncated remainder (sign follows the dividend).
    # Python's % is floored, so -0.5 % 1 == 0.5 in Python but -0.5 in JS.
    # This sign difference flips the swing branch on bar-line pickups.
    return math.fmod(a, b)


# ---------------------------------------------------------------------------
# honest dice — engine.js L24-47
# ---------------------------------------------------------------------------
def fnv1a(s):
    # engine.js L25-31. charCodeAt = UTF-16 code units; h stays uint32 via >>>0.
    h = 0x811C9DC5
    for ch in s:
        cp = ord(ch)
        if cp > 0xFFFF:  # astral scalar -> surrogate pair, as JS indexes it
            cp -= 0x10000
            units = (0xD800 + (cp >> 10), 0xDC00 + (cp & 0x3FF))
        else:
            units = (cp,)
        for u in units:
            h = _u32(_u32(h) ^ u)
            h = _u32(_imul(h, 0x01000193))
    return _u32(h)


def mulberry32(a):
    # engine.js L33-40. Exact 32-bit int semantics (|0, >>>, Math.imul).
    st = [_i32(a)]

    def nxt():
        s = _i32(st[0] + 0x6D2B79F5)
        st[0] = s
        t = _imul(_i32(_u32(s) ^ (_u32(s) >> 15)), _i32(1 | s))
        t = _i32(_u32(t + _imul(_i32(_u32(t) ^ (_u32(t) >> 7)), _i32(61 | t))) ^ _u32(t))
        return _u32(_i32(_u32(t) ^ (_u32(t) >> 14))) / 4294967296.0

    return nxt


def rng_from_seed(seed):
    # engine.js L41
    return mulberry32(fnv1a(seed))


def gauss(rng):
    # engine.js L42-45 Box-Muller, honest.
    u = max(rng(), 1e-12)
    v = rng()
    return math.sqrt(-2 * math.log(u)) * math.cos(2 * math.pi * v)


def clamp(x, lo, hi):
    # engine.js L46
    return min(hi, max(lo, x))


def lerp(a, b, t):
    # engine.js L47
    return a + (b - a) * t


# ---------------------------------------------------------------------------
# the 16 features — engine.js L51-68 (id order is the FIDX index order)
# ---------------------------------------------------------------------------
FEATURES = [
    {"id": "registerSpread", "label": "REGISTER SPREAD", "floor": 0.05},
    {"id": "trebleActivity", "label": "TREBLE ACTIVITY", "floor": 0.00},
    {"id": "dynRange", "label": "DYNAMIC RANGE", "floor": 0.08},
    {"id": "dynContour", "label": "DYNAMIC CONTOUR", "floor": 0.15},
    {"id": "swingFeel", "label": "SWING FEEL", "floor": 0.00},
    {"id": "syncopation", "label": "SYNCPOPATION", "floor": 0.02},
    {"id": "downbeatWeight", "label": "DOWNBEAT ORTHODOXY", "floor": 0.00},
    {"id": "harmonicComplex", "label": "HARMONIC COMPLEXITY", "floor": 0.05},
    {"id": "chromaticism", "label": "CHROMATICISM", "floor": 0.00},
    {"id": "repetition", "label": "REPETITION", "floor": 0.00},
    {"id": "callReply", "label": "CALL / REPLY", "floor": 0.05},
    {"id": "density", "label": "DENSITY", "floor": 0.05},
    {"id": "phraseVariance", "label": "PHRASE VARIANCE", "floor": 0.05},
    {"id": "restRatio", "label": "REST RATIO", "floor": 0.05},
    {"id": "bassMovement", "label": "BASS MOVEMENT", "floor": 0.05},
    {"id": "cadenceRegular", "label": "CADENCE REGULARITY", "floor": 0.00},
]
FIDX = {f["id"]: i for i, f in enumerate(FEATURES)}
PHI = (1 + math.sqrt(5)) / 2  # engine.js L70

# ---------------------------------------------------------------------------
# the canon — engine.js L75-120
# progression = 16 bars of [chord token, root semitones rel. tonic, weight]
# ---------------------------------------------------------------------------
PROGRESSIONS = {
    "duke": [
        ["Bb6", 0, 3], ["G9", 8, 3], ["C9", 3, 2], ["F9", 10, 2],
        ["Bb6", 0, 3], ["Bb7", 0, 2], ["Eb6", 5, 3], ["E9", 6, 4],
        ["Bb6", 0, 2], ["G9", 8, 3], ["C9", 3, 2], ["F9", 10, 3],
        ["Dm7", 9, 2], ["G9", 8, 3], ["Cm7", 3, 2], ["F9", 10, 3],
    ],
    "evans": [
        ["Fma7#11", 0, 4], [None, 0, 0], ["Em7", 9, 2], ["A9", 4, 2],
        ["Dm7", 7, 2], ["G13", 5, 3], ["Cma7", 3, 3], [None, 3, 0],
        ["Fma7#11", 0, 4], ["Abma7", 8, 4], ["Dm7", 7, 2], ["G13", 5, 3],
        ["Em7", 9, 2], ["A9", 4, 3], ["Dm7", 7, 2], ["G13", 5, 3],
    ],
    "monk": [
        ["Bb7", 0, 2], ["Bb7", 0, 2], ["Bb7", 0, 3], ["Bb7", 0, 2],
        ["Eb7", 5, 3], ["E9", 6, 4], ["Bb7", 0, 2], ["F7", 10, 2],
        ["Bb7", 0, 3], ["Bb7", 0, 2], ["Eb7", 5, 3], ["E9", 6, 4],
        ["Bb7", 0, 2], ["G7", 8, 2], ["Cm7", 3, 2], ["F7", 10, 3],
    ],
}

ARTISTS = {
    "duke": {
        "name": "DUKE ELLINGTON", "tonic": 46,
        "blurb": "Jungle harmony, the plunger growl, voicings nobody else could voice.",
        "centroid": {
            "registerSpread": .78, "trebleActivity": .72, "dynRange": .55, "dynContour": .62,
            "swingFeel": .62, "syncopation": .70, "downbeatWeight": .45, "harmonicComplex": .82,
            "chromaticism": .58, "repetition": .38, "callReply": .80, "density": .62,
            "phraseVariance": .60, "restRatio": .30, "bassMovement": .78, "cadenceRegular": .50,
        },
    },
    "evans": {
        "name": "BILL EVANS", "tonic": 41,
        "blurb": "Cluster voicings held like breath; the quietest loud music ever made.",
        "centroid": {
            "registerSpread": .80, "trebleActivity": .48, "dynRange": .88, "dynContour": .90,
            "swingFeel": .48, "syncopation": .45, "downbeatWeight": .40, "harmonicComplex": .92,
            "chromaticism": .72, "repetition": .22, "callReply": .55, "density": .52,
            "phraseVariance": .42, "restRatio": .66, "bassMovement": .35, "cadenceRegular": .30,
        },
    },
    "monk": {
        "name": "THELONIOUS MONK", "tonic": 46,
        "blurb": "Angular cells, sudden stops, notes that land like dropped tools.",
        "centroid": {
            "registerSpread": .55, "trebleActivity": .40, "dynRange": .85, "dynContour": .78,
            "swingFeel": .50, "syncopation": .82, "downbeatWeight": .18, "harmonicComplex": .78,
            "chromaticism": .68, "repetition": .74, "callReply": .75, "density": .38,
            "phraseVariance": .85, "restRatio": .72, "bassMovement": .30, "cadenceRegular": .18,
        },
    },
}

# engine.js L173
SCALE = [0, 2, 4, 5, 7, 9, 11]


# ---------------------------------------------------------------------------
# params — engine.js L174-181
# ---------------------------------------------------------------------------
def default_params():
    # engine.js L174-176
    return {f["id"]: 0.5 for f in FEATURES}


def params_from_centroid(centroid, rng, jitter):
    # engine.js L177-181 — jitter/param model; RNG-seeded, Box-Muller draws.
    p = {}
    for f in FEATURES:
        p[f["id"]] = clamp(centroid[f["id"]] + gauss(rng) * jitter, 0, 1)
    return p


# ---------------------------------------------------------------------------
# the synthesizer — engine.js L183-292 (params -> note events)
# The .song plainsong renderer (L294+) is intentionally NOT ported: the trace
# is the honest instrument (Summary Law); the receipt measures events only.
# ---------------------------------------------------------------------------
def generate_take(params, artist_key, rng):
    prog = PROGRESSIONS[artist_key]
    tonic = ARTISTS[artist_key]["tonic"]
    events = []
    BEATS = 64
    swing = params["swingFeel"] * 0.33           # L188 off-8th displacement
    center = 70 + jsround((params["registerSpread"] - 0.5) * 4)  # L189
    span = 6 + params["registerSpread"] * 20     # L190
    restP = params["restRatio"] * 0.55           # L191
    densityP = 0.25 + params["density"] * 1.5    # L192
    chromP = params["chromaticism"] * 0.5        # L193
    phraseAvg = 2 + jsround((1 - params["phraseVariance"]) * 6)  # L194
    repCell = params["repetition"] > 0.5         # L195
    cell_mem = []                                # L196

    # phrase plan — L198-206
    phrases = []
    bar = 0
    phrase_idx = 0
    while bar < 16:
        ln = clamp(jsround(phraseAvg + gauss(rng) * params["phraseVariance"] * 3), 1, 6)
        ln = min(ln, 16 - bar)
        phrases.append({"start": bar, "len": ln, "idx": phrase_idx})
        phrase_idx += 1
        bar += ln

    def is_call(bar):  # L207
        for p in phrases:
            if p["start"] <= bar < p["start"] + p["len"]:
                return p["idx"] % 2 == 0
        return True

    # melody — L210-251
    deg = 0
    prev_midi = center
    for b in range(16):
        _ch, root_rel, _cx = prog[b]
        root = tonic + 24 + root_rel               # L211
        beats_in_bar = [0, 1, 2, 3]
        # L214: nEvents is computed but unused — the rng() draw still happens.
        _n_events = jsround(densityP * (0.6 + rng() * 0.8) * 2) / 2
        cell = []
        for bi, beat_pos in enumerate(beats_in_bar):
            if rng() < restP:                      # L217
                continue
            onset = beat_pos                       # L219
            if rng() < params["syncopation"] * 0.7:            # L220
                onset = beat_pos + 0.5
            if rng() < params["syncopation"] * 0.25 and bi == 0 and b > 0:  # L221
                onset = -0.5
            t = b * 4 + onset
            if t < 0:                              # L223
                continue
            if rng() < chromP:                     # L225 chromatic approach
                midi = prev_midi + (-1 if rng() < 0.5 else 1)
            else:
                deg += jsround(gauss(rng) * 1.6)   # L228
                oct_shift = jsround(deg / 7) * 12
                midi = center + oct_shift + SCALE[((deg % 7) + 7) % 7] + (root_rel if rng() < 0.3 else 0)
            midi = jsround(clamp(midi, center - span / 2, center + span / 2))  # L231
            treble_line = 84                       # L233
            if params["trebleActivity"] < 0.4 and midi > treble_line:          # L234
                midi -= 12
            if params["trebleActivity"] > 0.6 and midi < treble_line - 12 and rng() < 0.5:  # L235
                midi += 12
            # dynamics — L237-240
            vel = (55 + params["dynRange"] * 35 * gauss(rng) * 0.5
                   + (params["dynContour"] * 14 if is_call(b) else -params["dynContour"] * 14))
            if bi == 0 and (beat_pos == 0 or beat_pos == 2):
                vel += params["downbeatWeight"] * 12
            if js_rem(onset, 1) != 0:
                vel += params["syncopation"] * 6 - params["downbeatWeight"] * 4
            vel = clamp(jsround(vel), 30, 110)
            # swing displacement on off-8ths — L242-244
            t_swing = t + swing if js_rem(onset, 1) == 0.5 else t
            ev = {"t": t_swing, "dur": 0.9 + rng() * 0.4, "midi": midi,
                  "vel": vel, "voice": "melody", "bar": b}
            events.append(ev)
            cell.append(ev)
            prev_midi = midi
        # cell repetition — L245-253
        if repCell and len(cell) >= 2:
            if cell_mem and rng() < params["repetition"] * 0.6:
                old = cell_mem[math.floor(rng() * len(cell_mem))]
                shift = root - tonic - 24
                for e in old:
                    events.append({
                        "t": b * 4 + js_rem(e["t"], 4),
                        "dur": e["dur"],
                        "midi": e["midi"] + shift,
                        "vel": clamp(jsround(e["vel"] + jsround(gauss(rng) * 4)), 30, 110),
                        "voice": "melody",
                        "bar": b,
                    })
            else:
                cell_mem.append(cell)

    # bass — L255-272
    bass_prev = tonic
    for b in range(16):
        _ch, root_rel = prog[b][0], prog[b][1]
        if rng() < params["bassMovement"] * 0.6:               # L258
            note = (tonic + root_rel + 7) if rng() < 0.5 else (tonic + root_rel + (9 if rng() < 0.5 else 10))
            if rng() < 0.35:                                   # L260 approach tone
                note = bass_prev + (-1 if rng() < 0.5 else 1) * (1 if rng() < 0.5 else 2)
        else:
            note = tonic + root_rel
        vel = clamp(jsround(62 + gauss(rng) * 8 + (params["downbeatWeight"] - 0.5) * 10), 40, 96)
        events.append({"t": b * 4, "dur": 3.4, "midi": note, "vel": vel, "voice": "bass", "bar": b})
        if params["bassMovement"] > 0.55 and rng() < 0.6:      # L265 walking-ish
            for q in range(1, 4):
                midi_q = clamp(note + [0, 2, 4, 7][math.floor(rng() * 4)] * (-1 if rng() < 0.5 else 1),
                               tonic - 6, tonic + 24)
                events.append({"t": b * 4 + q, "dur": 0.9, "midi": midi_q, "vel": vel - 6,
                               "voice": "bass", "bar": b})
        bass_prev = note

    # comping chord hits — L274-281
    for b in range(16):
        if params["density"] > 0.6:
            hits = [0, 2]
        elif params["restRatio"] > 0.6:
            hits = [0 if rng() < 0.5 else 2]
        else:
            hits = [0, 1.5, 2]
        for h in hits:
            t = b * 4 + 1.5 + swing if h == 1.5 else b * 4 + h
            vel = clamp(jsround(48 + gauss(rng) * 7), 32, 80)
            events.append({"t": t, "dur": 1.6, "midi": tonic + 24 + prog[b][1],
                           "vel": vel, "voice": "comp", "bar": b})

    events.sort(key=lambda e: e["t"])  # L283 — stable, comparator a.t-b.t
    return {"song": None, "events": events, "beats": BEATS}


# ---------------------------------------------------------------------------
# the eye — 16-feature trace measure — engine.js L346-421
# ---------------------------------------------------------------------------
def extract_features(events):
    mel = [e for e in events if e.get("voice") == "melody"]
    bas = [e for e in events if e.get("voice") == "bass"]
    f = [0.5] * 16
    if not mel:  # L349
        return f
    v = FIDX

    # registerSpread L352
    mid = [e["midi"] for e in mel]
    f[v["registerSpread"]] = clamp((max(mid) - min(mid)) / 24, 0, 1)

    # trebleActivity L354 — fraction >= 84 (C6)
    f[v["trebleActivity"]] = sum(1 for e in mel if e["midi"] >= 84) / len(mel)

    # dynRange L356-360 — population std of velocity
    vels = [e["vel"] for e in mel]
    vm = sum(vels) / len(vels)
    vstd = math.sqrt(sum((x - vm) * (x - vm) for x in vels) / len(vels))
    f[v["dynRange"]] = clamp(vstd / 22, 0, 1)

    # dynContour L362-366 — even vs odd bar velocity means
    odd = [e["vel"] for e in mel if e["bar"] % 2 == 0]   # bar%2===0
    even = [e["vel"] for e in mel if e["bar"] % 2 == 1]  # bar%2===1
    om = sum(odd) / (len(odd) or 1)
    em = sum(even) / (len(even) or 1)
    f[v["dynContour"]] = clamp(abs(om - em) / 28, 0, 1)

    # swingFeel L368-377 — mean deviation of half-beat gaps from 0.5
    dev_sum = 0.0
    dev_n = 0
    for i in range(1, len(mel)):
        if mel[i]["bar"] != mel[i - 1]["bar"]:
            continue
        gap = mel[i]["t"] - mel[i - 1]["t"]
        if 0.2 < gap < 0.9:
            dev_sum += gap - 0.5
            dev_n += 1
    f[v["swingFeel"]] = clamp(0.5 + (dev_sum / dev_n) / 0.33 * 0.5, 0, 1) if dev_n else 0.3

    # syncopation L379 — offbeat onset share
    sync_cnt = sum(1 for e in mel if 0.2 < (((e["t"] % 1) + 1) % 1) < 0.8)
    f[v["syncopation"]] = clamp(sync_cnt / len(mel) * 1.8, 0, 1)

    # downbeatWeight L381-386 — velocity bias on beats 1 & 3
    db = [e["vel"] for e in mel if (((e["t"] % 4) + 4) % 4) in (0.0, 2.0)]
    ob = [e["vel"] for e in mel if (((e["t"] % 4) + 4) % 4) in (1.0, 3.0)]
    dm = sum(db) / (len(db) or 1)
    om2 = sum(ob) / (len(ob) or 1)
    f[v["downbeatWeight"]] = clamp(0.5 + (dm - om2) / 40, 0, 1)

    # harmonicComplex L388-390 — stubbed 0.5 here; filled by measure_take().
    f[v["harmonicComplex"]] = 0.5

    # chromaticism L392-394 — semitone (or octave-displaced) leaps
    chrom = 0
    for i in range(1, len(mel)):
        d = abs(mel[i]["midi"] - mel[i - 1]["midi"])
        if d == 1 or d == 11 or d == 13:
            chrom += 1
    f[v["chromaticism"]] = clamp(chrom / len(mel) * 2.2, 0, 1)

    # repetition L396-402 — contour 3-gram self-similarity
    contour = []
    for i in range(1, len(mel)):
        a = mel[i]["midi"]
        b = mel[i - 1]["midi"]
        contour.append(1 if a > b else (-1 if a < b else 0))
    rep = 0
    pairs = 0
    i = 0
    while i + 6 < len(contour):
        j = i + 3
        while j + 3 < len(contour):
            pairs += 1
            if contour[i] == contour[j] and contour[i + 1] == contour[j + 1] and contour[i + 2] == contour[j + 2]:
                rep += 1
            j += 3
        i += 1
    f[v["repetition"]] = clamp(rep / pairs * 2.4, 0, 1) if pairs else 0

    # callReply L404
    f[v["callReply"]] = f[v["dynContour"]] * 0.5 + clamp(abs(om - em) / 24, 0, 0.5)

    # density L406
    f[v["density"]] = clamp(len(mel) / 56, 0, 1)

    # phraseVariance L408-411 — distinct inter-onset gaps / 7
    gaps = []
    for b in range(16):
        evs = [e for e in mel if e["bar"] == b]
        if len(evs) > 1:
            for k in range(1, len(evs)):
                gaps.append(evs[k]["t"] - evs[k - 1]["t"])
    uniq = len({jsround(g * 2) / 2 for g in gaps})
    f[v["phraseVariance"]] = clamp(uniq / 7, 0, 1)

    # restRatio L413-415 — unsounded melody time over 52
    sounded = sum(min(e["dur"], 1.5) for e in mel)
    f[v["restRatio"]] = clamp((1 - sounded / 52) * 1.15, 0, 1)

    # bassMovement L417-420
    bm = [e["midi"] for e in bas]
    moves = sum(1 for i in range(1, len(bm)) if abs(bm[i] - bm[i - 1]) > 3)
    f[v["bassMovement"]] = clamp(moves / len(bas) * 1.5, 0, 1) if bas else 0

    # cadenceRegular L422-425 (bar-list) — phrase-end landings
    land = 0
    for b in (3, 7, 11, 15):
        evs = [e for e in mel if e["bar"] == b]
        if not evs:
            continue
        last = evs[-1]
        if last["vel"] < vm + 4:
            land += 1
    f[v["cadenceRegular"]] = land / 4

    return f


def harmonic_from_prog(artist_key):
    # engine.js L423-425 — harmonic complexity read from the progression used.
    # (Note: the c[1]===null guard never fires for the seeded books, whose null
    #  chords carry root 0; w therefore always sums the c[2] weights.)
    prog = PROGRESSIONS[artist_key]
    w = sum(0 if c[1] is None else c[2] for c in prog) / 16
    return clamp(w / 3.2, 0, 1)


def measure_take(events, artist_key=None):
    # engine.js L427-431 — extract, then override harmonicComplex from prog.
    f = extract_features(events)
    if artist_key is not None and artist_key in PROGRESSIONS:
        f[FIDX["harmonicComplex"]] = harmonic_from_prog(artist_key)
    return f


# ---------------------------------------------------------------------------
# take builder (raw centroid = engine.js effectiveCentroid idiom)
# ---------------------------------------------------------------------------
def build_take(artist_key, seed, jitter=0.0):
    """Generate a take from an artist centroid.

    jitter == 0.0 mirrors engine.js effectiveCentroid (L500-508): params ARE the
    centroid, a single seed-derived rng drives generateTake. jitter > 0.0 applies
    the paramsFromCentroid jitter model (L177-181) before synthesis.
    """
    if artist_key not in ARTISTS:
        fail("unknown artist %r (known: %s)" % (artist_key, ", ".join(sorted(ARTISTS))))
    if artist_key not in PROGRESSIONS:
        fail("artist %r has no progression" % artist_key)
    centroid = ARTISTS[artist_key]["centroid"]
    rng = rng_from_seed(str(seed))
    if jitter > 0.0:
        params = params_from_centroid(centroid, rng, jitter)
    else:
        params = dict(centroid)
    return generate_take(params, artist_key, rng), params


# ---------------------------------------------------------------------------
# trace IO
# ---------------------------------------------------------------------------
def load_trace(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read()
    except OSError as e:
        fail("cannot read trace %s: %s" % (path, e))
    text = raw.strip()
    if not text:
        fail("empty trace %s" % path)
    events = []
    # JSON array form
    if text[0] == "[":
        try:
            arr = json.loads(text)
        except ValueError as e:
            fail("bad JSON array in %s: %s" % (path, e))
        events = arr
    else:
        for ln, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except ValueError as e:
                fail("bad JSON line %d in %s: %s" % (ln, path, e))
    for e in events:
        if not isinstance(e, dict) or "t" not in e or "midi" not in e or "vel" not in e:
            fail("malformed event %r in %s" % (e, path))
    return events


def take_summary(events, artist_key):
    """Compact human/LLM state string for the typesafe smoke (bar count,
    density, swing %, register span)."""
    mel = [e for e in events if e.get("voice") == "melody"]
    bas = [e for e in events if e.get("voice") == "bass"]
    mid = [e["midi"] for e in mel] or [0]
    dev_sum = 0.0
    dev_n = 0
    for i in range(1, len(mel)):
        if mel[i]["bar"] != mel[i - 1]["bar"]:
            continue
        gap = mel[i]["t"] - mel[i - 1]["t"]
        if 0.2 < gap < 0.9:
            dev_sum += gap - 0.5
            dev_n += 1
    swing = clamp(0.5 + (dev_sum / dev_n) / 0.33 * 0.5, 0, 1) if dev_n else 0.3
    span = max(mid) - min(mid)
    return (
        "Unlabeled jazz take: 16 bars, 4/4, tempo 96, 8th-note subdivision. "
        "Melody: %d note events over 64 beats (%.2f events/bar); bass: %d events; "
        "comp: %d chord hits. Measured swing displacement dial: %.2f (%.0f%% of a "
        "beat of off-8th layback). Melody register span: %d semitones (MIDI %d-%d). "
        "Silence/rest character: rests are %.0f%% of the take. No performer named."
        % (len(mel), len(mel) / 16.0, len(bas),
           len([e for e in events if e.get("voice") == "comp"]),
           swing, swing * 100, span, min(mid), max(mid),
           100 * clamp(1 - sum(min(e["dur"], 1.5) for e in mel) / 52.0, 0, 1))
    )


# ---------------------------------------------------------------------------
# subcommands
# ---------------------------------------------------------------------------
def cmd_gen(args):
    if args.artist not in ARTISTS:
        fail("unknown artist %r (known: %s)" % (args.artist, ", ".join(sorted(ARTISTS))))
    take, _params = build_take(args.artist, args.seed, jitter=args.jitter)
    out = sys.stdout
    for e in take["events"]:
        out.write(json.dumps(e) + "\n")
    out.flush()


def cmd_measure(args):
    events = load_trace(args.trace)
    f = measure_take(events, args.artist)
    result = {FEATURES[i]["id"]: round(f[i], 6) for i in range(16)}
    if args.pretty:
        for i in range(16):
            print("%2d  %-20s %s  %.4f" % (i + 1, FEATURES[i]["id"], FEATURES[i]["label"], f[i]))
        if args.artist is None:
            print("# note: no --artist; harmonicComplex left at the L388 stub 0.5")
    else:
        print(json.dumps(result))


def cmd_calibrate(args):
    seeds = [s.strip() for s in args.seeds.split(",") if s.strip()]
    if not seeds:
        fail("no seeds given")
    report = {"method": "3 artists x %d seeds; mean measured vs canonical centroid" % len(seeds),
              "seeds": seeds, "artists": {}}
    all_errs = []
    for artist_key in ("duke", "evans", "monk"):
        centroid = ARTISTS[artist_key]["centroid"]
        per_seed = []
        for seed in seeds:
            take, _ = build_take(artist_key, seed)
            per_seed.append(measure_take(take["events"], artist_key))
        means = [sum(row[i] for row in per_seed) / len(per_seed) for i in range(16)]
        dials = {}
        errs = []
        for i, feat in enumerate(FEATURES):
            err = abs(means[i] - centroid[feat["id"]])
            errs.append(err)
            dials[feat["id"]] = {"centroid": centroid[feat["id"]],
                                 "mean": round(means[i], 4),
                                 "abs_err": round(err, 4)}
            all_errs.append((err, artist_key, feat["id"]))
        errs_sorted = sorted(errs)
        median = (errs_sorted[7] + errs_sorted[8]) / 2
        report["artists"][artist_key] = {
            "name": ARTISTS[artist_key]["name"],
            "median_abs_err": round(median, 4),
            "mean_abs_err": round(sum(errs) / len(errs), 4),
            "dials": dials,
        }
    all_errs.sort(key=lambda x: -x[0])
    err_vals = sorted(e[0] for e in all_errs)
    n = len(err_vals)
    overall = (err_vals[n // 2 - 1] + err_vals[n // 2]) / 2 if n % 2 == 0 else err_vals[n // 2]
    report["overall_median_abs_err"] = round(overall, 4)
    report["gate"] = "CALIBRATED" if overall <= 0.15 else "NOT CALIBRATED"
    report["worst_dials"] = [{"artist": a, "dial": d, "abs_err": round(e, 4)}
                             for e, a, d in all_errs[:3]]
    print(json.dumps(report, indent=2))


TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"
DEFAULT_KEY_FILE = "/mnt/c/Users/casey/key.txt"


def _read_typesafe_key(path):
    # key is read at use-time and never printed / logged.
    if not os.path.exists(path):
        fail("typesafe key file not found: %s" % path)
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("TYPESAFE_AI_KEY"):
                if "=" in line:
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
                return line.split(None, 1)[1].strip() if " " in line else ""
    fail("TYPESAFE_AI_KEY not present in %s" % path)


def cmd_smoke(args):
    take, _ = build_take(args.artist, args.seed)
    state = take_summary(take["events"], args.artist)
    payload = {
        "model": "jev-latest",
        "state": state,
        "questions": {
            "swingFeel": {
                "type": "score",
                "instructions": "Rate the swing feel of this take on the dial.",
                "criteria": [
                    "mechanically straight eighths",
                    "hints of layback",
                    "syrupy late-jazz swing",
                    "extreme displaced swing",
                ],
            }
        },
    }
    key = _read_typesafe_key(args.key_file)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        TYPESAFE_URL, data=data, method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", "replace")[:400]
        except Exception:
            pass
        fail("typesafe HTTP %s: %s" % (e.code, detail), code=2)
    except urllib.error.URLError as e:
        fail("typesafe network error: %s" % e, code=2)
    ans = body.get("answers", {}).get("swingFeel", {})
    out = {
        "model": body.get("model"),
        "swingFeel": ans,
        "usage": body.get("usage"),
        "state_preview": state[:160],
    }
    print(json.dumps(out, indent=2))


# ---------------------------------------------------------------------------
def fail(msg, code=2):
    sys.stderr.write("FAIL: %s\n" % msg)
    sys.exit(code)


def build_parser():
    p = argparse.ArgumentParser(prog="dial_ruler.py",
                                description="duke-lab dial ruler — stdlib-only port")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gen", help="generate a per-note trace (JSON lines)")
    g.add_argument("--artist", required=True, choices=sorted(ARTISTS))
    g.add_argument("--seed", required=True)
    g.add_argument("--jitter", type=float, default=0.0,
                   help="0.0 = raw centroid (engine.js effectiveCentroid idiom); >0 applies paramsFromCentroid jitter")
    g.set_defaults(func=cmd_gen)

    m = sub.add_parser("measure", help="measure the 16 dials from a trace")
    m.add_argument("--trace", required=True)
    m.add_argument("--artist", default=None, choices=sorted(PROGRESSIONS),
                   help="supply to fill harmonicComplex from the artist progression")
    m.add_argument("--pretty", action="store_true")
    m.set_defaults(func=cmd_measure)

    c = sub.add_parser("calibrate", help="per-artist dial mean vs canonical centroid")
    c.add_argument("--seeds", default="1,2,3,4,5")
    c.set_defaults(func=cmd_calibrate)

    s = sub.add_parser("smoke", help="one typesafe judgment cell (swing feel score)")
    s.add_argument("--artist", default="monk", choices=sorted(ARTISTS))
    s.add_argument("--seed", default="9")
    s.add_argument("--key-file", default=DEFAULT_KEY_FILE)
    s.add_argument("--timeout", type=float, default=90.0)
    s.set_defaults(func=cmd_smoke)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # fail loud, rc=2 house style
        fail("%s: %s" % (type(e).__name__, e))
