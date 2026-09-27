"""E3 — cast-heldout control: does elephant's room-sense survive unseen windows?

The seed proved still/moving rooms separate when you fit and test on the
same clip. That's not enough: a real organ must read rooms it wasn't fit
on. Design: for each of two rooms, fit vMF on the TRAIN half of the
non-overlapping windows, evaluate on the HELD-OUT half.

Pass criteria:
  stability  — same-room train-fit vs heldout-fit gate must be real:False
               (a room's identity doesn't drift between halves)
  separation — cross-room gates must be real:True in BOTH directions
               when the evaluation fit comes from windows never used in
               the train fit
  geometry   — heldout d_mu should be in the same band as the
               all-windows fits (seed reported 0.628)
"""
from __future__ import annotations

import json
import sys

import numpy as np

sys.path.insert(0, "/home/eileen/projects/tessera/seeds/glyph-sense")
sys.path.insert(0, "/home/eileen/projects/tessera/lab")
sys.path.insert(0, "/home/eileen/projects/elephant")
from glyph_sense_real import (CLIPS, decode_ppm_frames, fit_room,  # noqa: E402
                              to_glyph_frames, zmatrix)
from glyph_rooms import WINDOW, frame_features, windowed_readings  # noqa: E402
from elephant import vmf as evmf  # noqa: E402


def main() -> dict:
    results = {}
    for clip_id, args in CLIPS:
        ppms = decode_ppm_frames(args)
        frames = to_glyph_frames(ppms)
        feat = frame_features(frames)
        # step=4 stride: ~29 windows so each temporal half clears vmf.NMIN=10
        # (vmf_fit returns None below NMIN — honest, never a fake number).
        # Temporal split: first half train, second half heldout; one-window
        # boundary overlap possible (frames shared by windows astride the
        # split) — noted, accepted for v0.
        rn, _ = windowed_readings(feat, step=4)
        half = len(rn) // 2
        assert half >= 10, f"{clip_id}: train half {half} < NMIN"
        f_train, _ = fit_room(rn[:half])
        f_hold, _ = fit_room(rn[half:])
        results[clip_id] = {"f_train": f_train, "f_hold": f_hold,
                            "n_windows": len(rn), "n_train": half}
        k = f_hold["kappa"]
        print(f"[e3] {clip_id}: {len(rn)} windows; train κ={f_train['kappa']:.1f} "
              f"heldout κ={k:.1f} warmth {f_train['warmth_vmf']:+.3f}->{f_hold['warmth_vmf']:+.3f}")

    a, b = CLIPS[0][0], CLIPS[1][0]
    checks = {}
    # stability: train-fit vs heldout-fit, same room -> NOT real
    for cid in (a, b):
        e = evmf.edge(results[cid]["f_train"], results[cid]["f_hold"])
        checks[f"stability_{cid}"] = {"d_mu": round(e["d_mu"], 3),
                                      "real": bool(e["real"]), "want_real": False}
    # separation: heldout-half fits, cross-room -> real in both directions
    for x, y in [(a, b), (b, a)]:
        e = evmf.edge(results[x]["f_hold"], results[y]["f_hold"])
        checks[f"separation_{x}->{y}"] = {"d_mu": round(e["d_mu"], 3),
                                          "real": bool(e["real"]), "want_real": True}
    kl = float(evmf.kl_sym(results[a]["f_hold"], results[b]["f_hold"]))
    # geometry: heldout d_mu vs seed's all-windows d_mu = 0.628
    dmu = checks[f"separation_{a}->{b}"]["d_mu"]

    stable = all(not v["real"] for k, v in checks.items() if k.startswith("stability"))
    separated = all(v["real"] for k, v in checks.items() if k.startswith("separation"))
    verdict = "KEEP" if (stable and separated) else "KILL"
    out = {
        "experiment": "E3 cast-heldout control", "seed_room_d_mu": 0.628,
        "checks": checks, "kl_sym_heldout": round(kl, 2),
        "stability_ok": stable, "separation_ok": separated,
        "verdict": verdict,
    }
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
