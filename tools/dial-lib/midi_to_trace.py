#!/usr/bin/env python3
# =============================================================================
# midi_to_trace.py — MIDI -> dial_ruler per-note trace (JSON lines)
#
# Emits events in dial_ruler.py's exact trace contract:
#   {"t": <beats>, "dur": <beats>, "midi": int, "vel": int,
#    "voice": "melody"|"bass"|"comp", "bar": int}
#
#   t    = onset time in quarter-note beats  (= onset_tick / ticks_per_beat)
#   dur  = sounding length in beats
#   bar  = floor(t / 4)         (dial_ruler assumes 4/4, bar = t//4)
#   vel  = raw MIDI velocity (0..127)
#   voice= melody / bass / comp, assigned per MIDI channel by register heuristic
#
# Handles type-0 and type-1 files: tracks are merged on ABSOLUTE ticks
# (per-track delta accumulation; all tracks share ticks_per_beat).
# note_on vel>0 = onset; note_off or note_on vel==0 = offset.
# Percussion (channel 9) skipped by default (--keep-perc to include).
#
# voice heuristic (--voice-mode channel, default):
#   * channels with >= max(3, 3% of notes) notes are scored by mean pitch
#   * highest-mean channel -> melody; lowest-mean (distinct) -> bass; rest -> comp
#   * single-channel files: all notes -> melody (documented; bassMovement then 0.0)
# --voice-mode register: <48 -> bass, 48..71 -> comp, >=72 -> melody
#
# House style: rc=2 on any failure, loud message to stderr.
# =============================================================================
import argparse
import json
import sys

try:
    import mido
except ImportError:
    sys.stderr.write("midi_to_trace: mido not installed (pip install mido)\n")
    sys.exit(2)


def fail(msg):
    sys.stderr.write("midi_to_trace: %s\n" % msg)
    sys.exit(2)


def collect_notes(path, keep_perc):
    try:
        mf = mido.MidiFile(path)
    except Exception as e:
        fail("cannot parse MIDI %s: %s" % (path, e))
    tpb = mf.ticks_per_beat or 480
    notes = []  # (onset_tick, off_tick, pitch, vel, channel)
    for track in mf.tracks:
        tick = 0
        open_note = {}  # (channel, pitch) -> (onset_tick, vel)
        for msg in track:
            tick += msg.time
            if msg.type == "note_on" and msg.velocity > 0:
                open_note[(msg.channel, msg.note)] = (tick, msg.velocity)
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                key = (msg.channel, msg.note)
                if key in open_note:
                    o, v = open_note.pop(key)
                    notes.append((o, tick, msg.note, v, msg.channel))
        # unterminated notes: close at last tick seen this track
        for (ch, pitch), (o, v) in open_note.items():
            notes.append((o, tick, pitch, v, ch))
    if not keep_perc:
        notes = [n for n in notes if n[4] != 9]
    if not notes:
        fail("no notes found in %s" % path)
    return notes, tpb


def assign_channels(notes):
    """Return dict channel->voice using register heuristic."""
    from collections import defaultdict
    bych = defaultdict(list)
    for (o, off, pitch, vel, ch) in notes:
        bych[ch].append(pitch)
    n = len(notes)
    thresh = max(3, int(0.03 * n))
    scored = [(sum(p) / len(p), ch) for ch, p in bych.items() if len(p) >= thresh]
    if not scored:
        scored = [(sum(p) / len(p), ch) for ch, p in bych.items()]
    scored.sort()
    voices = {}
    if len(scored) == 1:
        voices[scored[0][1]] = "melody"
        return voices
    voices[scored[-1][1]] = "melody"   # highest mean pitch
    voices[scored[0][1]] = "bass"      # lowest mean pitch
    for _m, ch in scored:
        voices.setdefault(ch, "comp")
    for ch in bych:
        voices.setdefault(ch, "comp")
    return voices


def to_events(notes, tpb, mode, melody_channel, max_bars):
    if mode == "channel":
        voices = assign_channels(notes)
        if melody_channel is not None:
            for ch in list(voices):
                if voices[ch] == "melody":
                    voices[ch] = "comp"
            voices[melody_channel] = "melody"
    events = []
    for (o, off, pitch, vel, ch) in notes:
        t = o / tpb
        dur = (off - o) / tpb
        if dur <= 0:
            dur = 0.25
        if mode == "register":
            voice = "bass" if pitch < 48 else ("comp" if pitch < 72 else "melody")
        else:
            voice = voices.get(ch, "comp")
        bar = int(t // 4)
        if max_bars is not None and bar >= max_bars:
            continue
        events.append({"t": round(t, 4), "dur": round(dur, 4), "midi": int(pitch),
                       "vel": int(vel), "voice": voice, "bar": bar})
    events.sort(key=lambda e: (e["t"], e["voice"]))
    return events


def main(argv=None):
    ap = argparse.ArgumentParser(prog="midi_to_trace.py")
    ap.add_argument("input", help="path to .mid/.midi")
    ap.add_argument("-o", "--output", default="-", help="output path (default stdout)")
    ap.add_argument("--voice-mode", choices=["channel", "register"], default="channel")
    ap.add_argument("--melody-channel", type=int, default=None,
                    help="force this MIDI channel to be 'melody'")
    ap.add_argument("--keep-perc", action="store_true",
                    help="include percussion channel 9 (default: skipped)")
    ap.add_argument("--max-bars", type=int, default=None)
    args = ap.parse_args(argv)

    notes, tpb = collect_notes(args.input, args.keep_perc)
    events = to_events(notes, tpb, args.voice_mode, args.melody_channel, args.max_bars)
    if not events:
        fail("no events emitted for %s" % args.input)
    out = sys.stdout if args.output == "-" else open(args.output, "w", encoding="utf-8")
    for e in events:
        out.write(json.dumps(e) + "\n")
    if out is not sys.stdout:
        out.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
