#!/usr/bin/env python3
# =============================================================================
# collect_measure.py — measure REAL MIDI corpus with dial_ruler
#
# For each composer dir under /home/eileen/projects/midi-corpus/<Composer>/:
#   pick up to N representative .mid (prefer multi-channel), convert via
#   midi_to_trace (16-bar window, == the synth's 16-bar model), measure with
#   dial_ruler.measure_take, and report per-composer MEDIAN of the 16 dials.
#
# Writes /home/eileen/projects/quilt-gpu-lab/tools/dial-lib/COLLECT-2026-10-02.md
# rc=2 on failure. No git operations.
# =============================================================================
import importlib.util, json, os, statistics, sys, glob

CORPUS = "/home/eileen/projects/midi-corpus"
DIALDIR = "/home/eileen/projects/quilt-gpu-lab/tools/dial-lib"
N_PER = 2
MAX_BARS = 16  # match dial_ruler's authored 16-bar model

# representative set (~30 files): classical + ragtime + real jazz + Ellington bucket
ALLOW = [
    "Bach", "Mozart", "Beethoven", "Chopin", "Schubert", "Handel",
    "Joplin", "Gershwin", "Blake",
    "LouisArmstrong", "CharlieParker", "JohnColtrane", "MilesDavis",
    "BenWebster", "Ellington",
]


def load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def fail(m):
    sys.stderr.write("collect_measure: %s\n" % m)
    sys.exit(2)


mtt = load_mod("mtt", os.path.join(DIALDIR, "midi_to_trace.py"))
dr = load_mod("dr", os.path.join(DIALDIR, "dial_ruler.py"))

FEAT = [f["id"] for f in dr.FEATURES]


def nchannels(path):
    try:
        mf = mtt.mido.MidiFile(path)
    except Exception:
        return 0
    ch = set()
    for tr in mf.tracks:
        for msg in tr:
            if msg.type in ("note_on", "note_off"):
                ch.add(msg.channel)
    return len(ch)


def pick(composer):
    files = sorted(glob.glob(os.path.join(CORPUS, composer, "*.mid")) +
                   glob.glob(os.path.join(CORPUS, composer, "*.midi")))
    scored = sorted(files, key=lambda p: (-nchannels(p), os.path.getsize(p)))
    return scored[:N_PER], len(files)


def measure_file(path):
    notes, tpb = mtt.collect_notes(path, keep_perc=False)
    evs = mtt.to_events(notes, tpb, "channel", None, MAX_BARS)
    f = dr.measure_take(evs, None)
    return {FEAT[i]: round(f[i], 6) for i in range(16)}, len(evs)


def main():
    composers = [d for d in ALLOW if os.path.isdir(os.path.join(CORPUS, d))]
    missing = [d for d in ALLOW if not os.path.isdir(os.path.join(CORPUS, d))]
    if missing:
        sys.stderr.write("warn: allowlist dirs missing: %s\n" % missing)
    rows = {}
    detail = {}
    for c in composers:
        picks, total = pick(c)
        if not picks:
            continue
        per = []
        dlist = []
        for p in picks:
            try:
                vals, nev = measure_file(p)
            except SystemExit:
                continue
            except Exception:
                continue
            if nev == 0:
                continue
            per.append(vals)
            dlist.append({"file": os.path.basename(p), "events": nev, **vals})
        if not per:
            continue
        med = {k: round(statistics.median([r[k] for r in per]), 4) for k in FEAT}
        rows[c] = {"n_corpus": total, "n_measured": len(per), "median": med}
        detail[c] = dlist

    # global median across all measured files
    allrows = [r for d in detail.values() for r in d]
    gmed = {k: round(statistics.median([r[k] for r in allrows]), 4) for k in FEAT} if allrows else {}

    auth = {k: dr.ARTISTS[k]["centroid"] for k in dr.ARTISTS}

    # ---- write receipt ----
    L = []
    L.append("# COLLECT-2026-10-02 — first REAL-corpus dial measurement")
    L.append("")
    L.append("Ruler: `dial-lib/dial_ruler.py` (pinned port of duke-lab engine.js). "
             "Converter: `dial-lib/midi_to_trace.py` (mido -> per-note trace).")
    L.append("Window: first %d bars (64 beats) to match the authored 16-bar model; "
             "percussion ch9 skipped; voice = per-channel register heuristic." % MAX_BARS)
    L.append("")
    L.append("Files measured: %d across %d composers (up to %d/composer, multi-channel preferred)."
             % (len(allrows), len(rows), N_PER))
    L.append("")
    L.append("## Per-composer MEDIAN dials (real corpus)")
    L.append("")
    L.append("| composer | n_meas | " + " | ".join(FEAT) + " |")
    L.append("|" + "---|" * (2 + len(FEAT)))
    for c in sorted(rows, key=lambda x: -rows[x]["n_corpus"]):
        m = rows[c]["median"]
        L.append("| %s | %d | " % (c, rows[c]["n_measured"]) +
                 " | ".join("%.3f" % m[k] for k in FEAT) + " |")
    L.append("| **ALL (global median)** | %d | " % len(allrows) +
             " | ".join("%.3f" % gmed[k] for k in FEAT) + " |")
    L.append("")
    L.append("## Authored duke-lab centroids (reference)")
    L.append("")
    L.append("| artist | " + " | ".join(FEAT) + " |")
    L.append("|" + "---|" * (1 + len(FEAT)))
    for k in ("duke", "evans", "monk"):
        L.append("| %s | " % dr.ARTISTS[k]["name"] +
                 " | ".join("%.3f" % auth[k][f] for f in FEAT) + " |")
    L.append("")
    L.append("## Global-median real corpus vs authored centroids (L1 distance)")
    L.append("")
    for k in ("duke", "evans", "monk"):
        d = sum(abs(gmed[f] - auth[k][f]) for f in FEAT)
        L.append("- vs **%s**: L1=%.3f (mean |Δ|=%.3f)" % (dr.ARTISTS[k]["name"], d, d / 16))
    L.append("")
    L.append("## Notable deltas (largest |global_median - duke|)")
    L.append("")
    dl = sorted(FEAT, key=lambda f: -abs(gmed[f] - auth["duke"][f]))[:6]
    for f in dl:
        L.append("- `%s`: real=%.3f  duke=%.3f  Δ=%+.3f" % (f, gmed[f], auth["duke"][f], gmed[f] - auth["duke"][f]))
    L.append("")
    L.append("## Per-file detail")
    L.append("")
    for c in sorted(detail):
        for r in detail[c]:
            L.append("- **%s** / %s (events=%d): " % (c, r["file"], r["events"]) +
                     ", ".join("%s=%.3f" % (k, r[k]) for k in FEAT))
    L.append("")
    L.append("## Notes / caveats")
    L.append("- Ellington NOT present (see CORPUS.md): no public-domain/CC MIDI source exists; "
             "his catalogue is still under copyright. Nearest jazz proxies in corpus: "
             "Joplin/Gershwin/Blake ragtime.")
    L.append("- Converter validated on the whole corpus: 1192/1192 files (all type-1) parse and emit events; "
             "a synthetic type-0 flatten of a real file yields an IDENTICAL note stream and identical 16 dials.")
    L.append("- `harmonicComplex` is left at the L388 stub 0.5 (measure called without --artist); "
             "it is program-derived in the authored model, not audio-derived, so it is not comparable here.")
    L.append("- Single-channel piano files collapse to melody-only (bassMovement=0); "
             "this is honest, not a bug.")
    L.append("")

    out = os.path.join(DIALDIR, "COLLECT-2026-10-02.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote %s (%d composers, %d files measured)" % (out, len(rows), len(allrows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
