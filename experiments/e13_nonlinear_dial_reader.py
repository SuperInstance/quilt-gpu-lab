#!/usr/bin/env python3
"""E13 — nonlinear-carrier dial read: was E12's KEEP just the linear staging?

CLAIM UNDER TEST (concrete, falsifiable)
  E12 (experiments/e12_room_dial_reader.py) asked whether a frozen I-JEPA
  linearly reads the elephant's dials (mood/volume/presence) off staged lavfi
  rooms, and returned KEEP: R2_still_loro(k=64) = 0.81 / 0.96 / 0.95 for
  mood / volume / presence, all three above the 200-perm shuffle null, tertile
  accuracy 0.97 / 1.00 / 1.00. E12 booked its own biggest hole: the carriers
  were STAGED and each dial drove its own visual axis through a near-affine
  map (mood -> colour temperature + brightness, volume -> contrast + noise
  amount, presence -> count of drawn boxes). E13 asks the falsification
  question E12 could not ask about itself:

      Does the linear dial-read SURVIVE a NONLINEAR carrier->dial mapping,
      or was E12's KEEP an artifact of the linear staging?

  KILL  = the frozen I-JEPA's dial-read is not a property of the embedding
          but of the linear carrier E12 built => E12's KEEP was a staging
          artifact.
  KEEP  = the read survives nonlinear mixing of the dials (still a floor,
          but a floor on a much less friendly carrier).

ARMS (one frozen I-JEPA, ONE label bank, three carriers — a paired comparison)
  All three arms render the SAME 27-cell dial grid (E12's Arm B: m in
  {-0.8,0,+0.8}, v,p in {0.15,0.50,0.85}), from the SAME staged scripts, so
  the dial LABELS (the elephant DialBank's own readings) and the target triples
  are IDENTICAL across arms; only the rendered CARRIER differs. The labels are
  therefore a controlled factor and the arm comparison is paired.
    Arm L  "linear-staging"    : E12's stage_source verbatim (affine per dial).
                                 Replication / positive control. If this arm
                                 does NOT reproduce E12's KEEP, a nonlinear-arm
                                 KILL cannot be attributed to nonlinearity.
    Arm N1 "nonlinear-warp"    : a frozen, monotone-but-strongly-bent warp of
                                 the same three axes — every knob is a
                                 saturating sigmoid of a mix of ALL THREE dials
                                 plus a mild cross-term, and the chroma is
                                 rotated by a frozen angle. Smooth and
                                 order-preserving, but curved: a MILD rung
                                 (booked certificate, not gated).
    Arm N2 "nonlinear-mixture" : PRIMARY. roomgen.py's frozen nonlinear sensor
                                 mixture, read out through FOLDED channel
                                 responses: dial triple -> 8-d roomgen latent
                                 (warmth = mood, tightness = roomgen's
                                 anti-correlation, pacing/volume = volume,
                                 mood2 = presence, three per-room nuisance
                                 dims) -> o = tanh(z @ W + b) * gain (frozen
                                 random W, b, gain from roomgen.SensorMixture,
                                 seed 2719) -> label-free SVD channels -> 12
                                 signed channels -> the 7 lavfi knobs, five of
                                 them through a folded (non-monotone)
                                 sin-response of one channel and two through a
                                 product of two channels. No dial owns an axis,
                                 no knob is monotone in any dial, and the same
                                 triple renders differently for a different room
                                 seed. This is the carrier E12's caveat
                                 ("staged, near-linear carriers") pointed at.

  Constructive honesty about the intervention (this cost a design pass).
  A carrier can be nonlinear and still be trivially decodable (a smooth
  monotone warp of a dial is recovered affinely — that is exactly E12's
  situation). So the intervention is defined by a MEASURED property. The
  carrier family was chosen on CPU before any embedding existed, and the
  candidates were measured on the actual room bank (throwaway design pass,
  --cpu-only):
     carrier                          mean lin LOO-R2   mean curvature
     L   E12 affine                        1.000            0.000
     N1  bent monotone warp                0.903            0.519
     N2  mixture + FOLDED channels         0.900            0.471   <- chosen
     N2' mixture + product channels       -0.180            1.210   <- dials
         (linearity broken, but NOTHING reads them: distance-correlation not
          significant, p 0.14-0.78, and 3-NN LOO-R2 negative — a hard-inverse
          carrier where a KILL would be uninterpretable, so it is REJECTED)
     N2" mixture + deeper fold (amp 2.6-3.0)
                                           0.10..0.30       1.8..4.7
         (also breaks liveness: 3-NN LOO-R2 negative for volume) — REJECTED.
  (N1/N2 rows and the chosen arm's certificate are re-measured live at run
  time in `carrier_certificates`; the table is the design-time reading.)
  The lesson, booked: on a 3-level x 3-dial grid, "nonlinear" and "readable"
  pull against each other; the primary carrier is fixed at the strongest fold
  that still passes the liveness half of the certificate (fold amplitude 2.2,
  phase 0.0). A KEEP is therefore "the read survives a MODERATELY nonlinear,
  demonstrably live carrier", not "survives any nonlinearity" — and the
  rejected stronger folds are the reason that scope statement is needed.

WHY THIS IS A REAL FALSIFICATION (and where it could be unfair)
  A KILL is only evidence if the nonlinear carrier is (i) genuinely nonlinear
  and (ii) still a LIVE dial channel. Otherwise we would be reporting "the
  render was dead" as a fact about the embedding — E12's own warning. E13
  therefore pre-registers a CPU-only CARRIER CERTIFICATE (G0c), computed before
  any embedding exists: a leave-one-room-out ridge read of each TARGET dial
  from the 7 scene knobs, linear vs degree-2, must show (i) a nonlinearity gain
  >= 0.15 and (ii) quad LOO-R2 >= 0.50 for >= 2 of 3 dials. The certificate is
  also reported for Arm L, where it must show gain ~ 0 by construction (a
  discriminative check on the certificate itself: E12's carrier IS affine).

PRE-REGISTERED GATES (fixed before running; this file IS the registration)
  G0a staging fidelity : Spearman(target, elephant_label) >= 0.5 for >= 2/3
      dials on the shared script bank — E12's G0a verbatim. (The labels are
      staged by the SCRIPTS, not by the carrier, so one bank serves all arms.)
  G0b sensitivity      : the same LORO probe on per-still mean luminance must
      reach R2(k=64) >= 0.90 on Arm L (E12's replication carrier; E12 measured
      0.993 there). Per-arm luminance R2 is booked for all three arms. A
      harness that cannot read a signal certainly present in the frames is
      blind, and a KILL from a blind harness is meaningless.
  G0c carrier certificate : as above — validity of the intervention. Pass =
      (mean normalized curvature of the dial response >= 0.20, i.e. the carrier
      is measurably NOT affine; Arm L measures 0.000 by construction, which is
      the certificate's own discriminative check) AND (the 27 knob vectors are
      pairwise distinct AND >= 2 of 3 dials show BOTH a distance-correlation
      above its 200-shuffle null (p <= 0.05) AND a 3-NN LOO-R2 >= 0.20, i.e.
      the dial is genuinely present and recoverable).
  G0d harness self-test   : CPU-only, synthetic (12 rooms, known linear dial
      signal, 2% still noise): the imported probe must reach LORO R2 >= 0.90
      and the shuffled-label control < 0.10. Carrier-free and model-free.
  G1 THE CLAIM (KEEP)  : on the PRIMARY arm (N2)
        >= 2 of 3 dials PASS, PASS_d := R2_still_loro_k64(d) >= 0.30
          AND R2_room_loro(d) >= 0.15
          AND R2_still_loro_k16(d) >= 0.5 * R2_still_loro_k64(d)
          AND R2_still_loro_k64(d) > null95_k64(d)
        AND arm room-separability >= 0.75 (half-split nearest-centroid,
            chance 1/27). [E12 used its Arm A (E9's real frames) for this
            sanity check. E13 has no Arm A: the carrier IS the intervention,
            so the equivalent sanity check is separability of the E13 rooms
            themselves. Deviation pre-registered here.]
  G2 INCONCLUSIVE      : exactly 1 dial PASSes, or mean R2(d@k64) > mean
      null95 — E12's G2 verbatim, applied to the primary arm.
  G3 KILL              : 0 dials PASS and no mean R2 above the null on the
      primary arm, AND Arm L (control) DID keep — the linear staging
      replicated and the nonlinear carrier killed the read.
  INVALID_CONTROL      : Arm L fails E12's own gate. E12's KEEP does not
      replicate in this harness, so a nonlinear-arm failure cannot be blamed
      on nonlinearity. Never reported as a KILL.
  INVALID_STAGING      : G0a fails, or the G0c certificate fails on the
      primary arm (dead or accidentally-linear carrier).
  INVALID_HARNESS      : G0b or G0d fails.
  ABORTED              : guard preflight, model load, no frames, or < 8 rooms.

CONTROLS / BOOKED (never gated)
  C1 raw-pixel probe    : the same LORO ridge on 16x9 grayscale stills (144-d),
      per arm. Watch this one: on E12's linear carrier the raw pixels already
      read mood at R2 0.94. If a nonlinear arm's pixels STILL read the dials,
      the "nonlinearity" is visually cosmetic; if the pixels die while the
      embedding holds, the JEPA is doing the nonlinear work.
  C2 luminance Spearman : per dial, per arm.
  C3 permutation null   : 200 room-level label shuffles in the k=64 space.
  C4 room-identity acc  : half-split nearest-centroid, per arm.
  C5 extra dials        : earnestness/cynicism/joke_landing/panic booked.
  C6 arm deltas         : R2(N2) - R2(L) per dial — the headline number: what
      the nonlinear carrier costs the dial-read.
  C7 carrier knobs      : per-room knob vectors, per-knob ranges / unique
      counts (a constant knob = a dead carrier channel), the certificate's
      curvature / k-NN / distance-correlation / linear-R2 / injectivity numbers
      for EVERY arm (including L, where curvature is 0.000 and the linear read
      is 1.000 by construction — the certificate's own discriminative check),
      and the Arm L mirror check (E13's re-derived linear knobs must reproduce
      e12.stage_source's string byte-for-byte, else Arm L is not E12's carrier).
  C8 kill_scope         : whether the read survives the mild rung (N1) and
      dies only at the mixture (N2), or dies at both.

DATA THE GATE NEEDS
  - ffmpeg ~/.local/bin/ffmpeg + the SAME lavfi chain as E12 (color, eq, noise,
    drawbox) — 3 arms x 27 rooms x 6 s @ 10 fps @ 160x90.
  - facebook/ijepa_vith16_1k fp16 on the RTX 4050 (E9's loader, imported).
  - the elephant package importable (the dial bank = the labels).
  - roomgen.py loadable for the nonlinear mixture's frozen physics; an inline
    torch replica of SensorMixture's constructor is the fallback and the JSON
    records which was used (`carrier_source`).
  - ~3 x 324 = 972 encoder forwards at 224^2 → ~8-12 min GPU, or CPU overnight.
  - GPU free (the guard preflights; this file never allocates without it).

HONESTY / CAVEATS BOOKED WITH THE RESULT
  - Carriers are still STAGED. E13 narrows E12's caveat from "staged,
    near-linear carriers" to "staged, nonlinear carriers". It does NOT test
    natural camera feeds. A KEEP remains a floor from below.
  - The nonlinear map is FROZEN but ARBITRARY: one random draw of (W, b, gain)
    plus one frozen readout family. A KILL from one draw is evidence about that
    draw (reproducible, seed 2718/2719, not universal). A KEEP is the stronger
    result: the read survived a randomly chosen nonlinearity.
  - The N2 readout is deliberately NON-MONOTONE: a folded sin-response is the
    strongest way found to break affine decodability while keeping the dial
    recoverable (products break affine decodability harder but kill recovery —
    measured, see the design-pass table above). A KILL on N2 therefore means "a
    linear probe cannot read a non-monotone carrier", and it must be read
    together with the liveness half of the certificate, which is what rules out
    "the render was dead". The scope of a KEEP is the fold strength that was
    pre-registered; deeper folds exist and are booked as rejected.
  - Arm N1's warp is monotone (bent), so N1 and N2 have comparable measured
    curvature by different mechanisms: N1 is the deterministic rung, N2 adds
    the random mixture, the fold and the per-room nuisance. Both certificates
    are reported; only the PRIMARY arm's is gated.
  - The N2 readout (SVD + logistic + normalisation) uses LABEL-FREE bank
    statistics only — the same status as E12's PCA basis (label-free,
    model-free, fitted before any embedding exists).
  - Per-room nuisance dims make every render unique; leave-one-ROOM-out CV is
    what keeps the probe honest about an unseen room, and the room-level R2 is
    the strict check.

Dev path: `python -m experiments.e13_nonlinear_dial_reader --cpu-only` runs
everything except the encoder (bank, carriers, certificates, mirror check,
harness self-test) with no model and no GPU — the plumbing test E12's
docstring describes, made a first-class mode.

Verdict printed as ONE JSON object on stdout (progress on stderr).
Deterministic (seed 2718). CPU-only probe; GPU only for encoder forwards.
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

# BLAS thread cap — same reason as E12: the probe does thousands of tiny ridge
# solves (grouped CV x lambda grid x 3 arms), and the default thread count turns
# each 35-d solve into a thread storm. Must be set BEFORE numpy loads (and this
# module imports E12, which imports numpy).
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "4")

import numpy as np  # noqa: E402

try:  # belt-and-braces for callers that imported numpy before this module
    from threadpoolctl import threadpool_limits  # noqa: E402
    _BLAS_LIMIT = threadpool_limits(limits=4)
    _BLAS_LIMIT.__enter__()
except Exception:  # threadpoolctl absent — the env vars above still apply
    _BLAS_LIMIT = None

SEED = 2718
LAB = Path(__file__).resolve().parents[1]
ELEPHANT = Path.home() / "projects" / "elephant"
for _p in (str(LAB), str(LAB / "experiments"), str(ELEPHANT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from common import ppms_from_lavfi                            # noqa: E402
from e9_ijepa_stills import (                                 # noqa: E402
    N_STILLS, load_encoder, preflight_guard,
)

# --------------------------------------------------------------------- #
# E12 is imported VERBATIM — no fork of the probe, the loader, or the   #
# staging. E13 changes exactly one thing: the carrier.                  #
#   staging   : stage_transcript, room_from_script, read_room,          #
#               stage_source, _mood_rgb, _boxes, build_dial_grid        #
#   probe     : spearman, r2_columns, pca_basis, loro_predict,          #
#               probe_sweep, room_halfsplit_acc                         #
#   harness   : embed_stills (E9 still sampling + preprocessing +       #
#               forward + luminance/pixel controls)                     #
#   constants : SEED, DIAL_NAMES, EXTRA_DIALS, K_PRIMARY/K_STRICT/      #
#               K_WIDE, R2_FLOOR, R2_ROOM_FLOOR, R2_TOP_PC_FRACTION,    #
#               FIDELITY_FLOOR, SENSITIVITY_FLOOR, ARM_A_ACC_FLOOR,     #
#               W, H, RATE, SECONDS                                     #
# --------------------------------------------------------------------- #
from e12_room_dial_reader import (                            # noqa: E402
    ARM_A_ACC_FLOOR, DIAL_NAMES, EXTRA_DIALS, FIDELITY_FLOOR, GRID_M, GRID_P,
    GRID_V, K_PRIMARY, K_STRICT, K_WIDE, R2_FLOOR, R2_ROOM_FLOOR,
    R2_TOP_PC_FRACTION, RATE, SECONDS, SENSITIVITY_FLOOR, W, H, _boxes,
    _mood_rgb, build_dial_grid, embed_stills, loro_predict, pca_basis,
    probe_sweep, r2_columns, read_room, room_from_script, room_halfsplit_acc,
    spearman, stage_source, stage_transcript,
)

# --------------------------------------------------------------------- #
# Pre-registered constants                                              #
# --------------------------------------------------------------------- #
ARMS = ("L", "N1", "N2")
PRIMARY_ARM = "N2"
ARM_TITLES = {
    "L": "linear-staging (E12's stage_source, verbatim formulas) — "
         "replication / positive control",
    "N1": "nonlinear-warp (frozen sigmoid mixer of all three dials, with "
          "cross-terms and a hue rotation) — mild rung",
    "N2": "nonlinear-mixture (roomgen.SensorMixture: frozen random "
          "tanh(Wz+b)*gain, per-room nuisance, label-free SVD readout) — "
          "PRIMARY",
}
# G0c — carrier certificate (validity of the intervention).
CURV_FLOOR = 0.20        # mean normalized curvature of the dial response (non-affine)
KNN_FLOOR = 0.20         # 3-NN LOO-R2 on the knobs (the dial must be recoverable)
DCORR_P = 0.05           # distance-correlation permutation p (dependence of ANY form)
CERT_LIVE_DIALS_FLOOR = 2  # ...for at least 2 of 3 dials
DCOR_PERMS = 200         # distance-correlation permutation null
# Arm N2's frozen readout: fold amplitude/phase, FIXED BY THE CPU DESIGN PASS
# (the strongest fold that still passes the liveness half of the certificate —
# deeper folds break 3-NN recovery; see the module docstring's design table).
N2_FOLD_AMP = 2.2
N2_FOLD_PHASE = 0.0
N2_KNN = 3
ARM_SEP_FLOOR = ARM_A_ACC_FLOOR  # 0.75, E12's Arm-A floor, applied per arm
N_REPLICATES = int(os.environ.get("E13_REPLICATES", "1"))  # 1 = E12's 27 rooms

# The 7 lavfi knobs every carrier must produce (one schema for all arms, so the
# certificate is comparable and the renderer is shared).
KNOB_NAMES = ("r", "g", "b", "bright", "contrast", "noise", "n_occ")
KNOB_CLIP = ((0.0, 255.0), (0.0, 255.0), (0.0, 255.0),
             (-0.30, 0.30), (0.50, 1.90), (2.0, 62.0), (1.0, 9.0))

LATENT_DIM = 8   # roomgen.LATENT_NAMES length; asserted against W's shape
OBS_DIM = 48     # roomgen.OBS_DIM; asserted against W's shape
N_READOUT_CHANNELS = 12


def log(msg: str) -> None:
    """Progress goes to stderr; stdout is reserved for the JSON verdict."""
    print(f"[e13] {msg}", file=sys.stderr, flush=True)


# --------------------------------------------------------------------- #
# The nonlinear carriers (dial triple -> 7 scene knobs)                  #
# --------------------------------------------------------------------- #
def _sig(x: float) -> float:
    """Logistic — the frozen saturating mixer. Clamped so exp() cannot overflow
    on an extreme argument (all call sites are bounded anyway)."""
    x = float(max(min(float(x), 60.0), -60.0))
    return 1.0 / (1.0 + math.exp(-x))


def knobs_linear(m: float, v: float, p: float) -> np.ndarray:
    """Arm L — E12's stage_source formulas, mirrored knob-for-knob.

    Mirrored (not called) because E13 needs the knob VECTOR, not just the lavfi
    string; the mirror is audited by rendering both and comparing strings (see
    `mirror_check`). Constants are E12's, character for character:
      bright = -0.25 + 0.50*((m+1)/2);  contrast = 0.70 + 0.90*v
      noise  = int(round(2 + 60*v));    n_occ    = 1 + int(round(p*8))
    """
    r, g, b = _mood_rgb(m)
    return np.array([
        float(r), float(g), float(b),
        -0.25 + 0.50 * ((m + 1.0) / 2.0),
        0.70 + 0.90 * v,
        int(round(2 + 60 * v)),
        1 + int(round(p * 8)),
    ], float)


def _dial_feats(m: float, v: float, p: float):
    """Arm N1 — the frozen squashed dial features fed to every knob."""
    a = math.tanh(1.6 * m - 0.5)      # mood
    b = math.tanh(2.2 * v - 1.1)      # volume
    c = math.tanh(2.0 * p - 1.0)      # presence
    return a, b, c


def knobs_warp(m: float, v: float, p: float) -> np.ndarray:
    """Arm N1 — frozen monotone-but-bent warp (the MILD rung).

    Every knob is a saturating sigmoid of a mix of all three dials (strong
    gains -> strong curvature), with one mild cross-term and a frozen chroma
    rotation. Order-preserving in each dial, so this rung preserves the smooth
    structure a held-out room needs; it is not expected to break a linear read
    on its own — that is the point of having N2 above it.
    """
    a, b, c = _dial_feats(m, v, p)
    s_mood = _sig(3.10 * a + 1.20 * b - 0.80 * c - 0.10)
    s_vol = _sig(3.00 * b - 0.90 * a + 0.70 * c + 0.05)
    s_pres = _sig(2.90 * c + 1.10 * a - 0.60 * b - 0.15)
    s_mix = _sig(1.40 * (a + b + c) + 1.60 * (a * b) - 0.30)   # the one cross-term

    warm = np.array([255.0, 170.0, 60.0])
    cold = np.array([60.0, 150.0, 255.0])
    rgb = s_mood * warm + (1.0 - s_mood) * cold
    ang = math.pi * (s_mix - 0.5)                              # frozen hue rotation
    rgb = np.clip(rgb + 90.0 * (0.5 + s_pres)
                  * np.cos(np.array([ang, ang - 2.0943951, ang + 2.0943951])),
                  0.0, 255.0)
    return np.array([
        rgb[0], rgb[1], rgb[2],
        -0.25 + 0.45 * s_mix,
        0.60 + 1.00 * s_vol,
        2 + int(round(58.0 * s_mix * s_pres)),
        1 + int(round(8.0 * s_pres)),
    ], float)


def _inline_mixture_weights(seed: int):
    """Bit-faithful replica of roomgen.SensorMixture's constructor — same PRNG,
    same call order (W, then b, then gain), same shapes and scalings. Used only
    if roomgen.py itself cannot be loaded; the JSON records the difference."""
    import torch
    g = torch.Generator().manual_seed(seed)
    W_ = torch.randn(LATENT_DIM, OBS_DIM, generator=g) / math.sqrt(LATENT_DIM)
    b_ = 0.25 * torch.randn(OBS_DIM, generator=g)
    gain_ = 0.8 + 0.6 * torch.rand(OBS_DIM, generator=g)
    return (W_.numpy().astype(np.float64), b_.numpy().astype(np.float64),
            gain_.numpy().astype(np.float64))


def _load_roomgen():
    """Load roomgen.py directly from disk (importlib, no package __init__), so
    the carrier depends on exactly one file + torch — not on elephant.gpu's
    package import chain. Returns the module, or raises."""
    import importlib.util
    path = ELEPHANT / "gpu" / "roomgen.py"
    if not path.is_file():
        raise FileNotFoundError(path)
    name = "_e13_roomgen"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    # dataclasses resolve their defining module through sys.modules, so the
    # module must be registered BEFORE exec_module. Without this, roomgen's
    # @dataclass definitions raise
    #   AttributeError: 'NoneType' object has no attribute '__dict__'
    # (caught in the plumbing check at write time — which is why the JSON's
    # carrier_source is read, not assumed).
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return mod


def carrier_weights():
    """The frozen nonlinear physics (W, b, gain) of roomgen's sensor mixture.

    roomgen's own docstring is explicit that the mixture is a *fixed* nonlinear
    map, "frozen at construction: the encoder must learn to invert it"; E13
    consumes exactly those matrices. roomgen's per-call channel noise and
    channel dropout are training-time augmentation (stochastic), NOT the
    physics, so they are not used: the carrier must be deterministic for the
    scene to be a function of the dial triple.
    """
    seed = SEED + 1                 # roomgen.build_world's mixture seed
    try:
        rg = _load_roomgen()
        mix = rg.SensorMixture(seed=seed)
        W_ = mix.W.detach().cpu().numpy().astype(np.float64)
        b_ = mix.b.detach().cpu().numpy().astype(np.float64)
        gain_ = mix.gain.detach().cpu().numpy().astype(np.float64)
        src = (f"roomgen.SensorMixture(seed={seed}) via importlib "
               f"({ELEPHANT / 'gpu' / 'roomgen.py'}): frozen W,b,gain; "
               f"channel noise/dropout (training augmentation) unused")
    except Exception as e:  # noqa: BLE001
        W_, b_, gain_ = _inline_mixture_weights(seed)
        src = (f"inline torch replica of roomgen.SensorMixture(seed={seed}) "
               f"[{type(e).__name__}: {e}]"[:280])
    return W_, b_, gain_, src


def _latent(m: float, v: float, p: float, room_seed: int) -> np.ndarray:
    """Dial triple -> roomgen latent (LATENT_NAMES order).

    dials occupy dims 0-4, amplified (1.2-1.6) so the carrier is a LIVE dial
    channel; dims 5-7 are per-room nuisance at 0.5 (smaller than the dial
    signal, but entangled into every observation through the same W). Mood gets
    two dims the way roomgen couples warmth/tightness; volume gets the
    pacing/volume pair; presence drives mood2 alone, hence the larger 1.6.
    """
    z = np.zeros(LATENT_DIM, float)
    z[0] = 1.20 * m                                            # warmth
    z[1] = -0.54 * m                                           # tightness (centred)
    z[2] = 1.20 * (2.0 * v - 1.0)                              # pacing
    z[3] = 1.20 * (2.0 * v - 1.0)                              # volume
    z[4] = 1.60 * (2.0 * p - 1.0)                              # mood2 == presence
    rng = np.random.default_rng((int(room_seed) * 7919 + 13) % (2 ** 63 - 1))
    z[5:] = 0.50 * (2.0 * rng.random(LATENT_DIM - 5) - 1.0)     # topic1/topic2/energy
    return z


def _fold(x: float) -> float:
    """Arm N2's frozen channel response: a folded (non-monotone) sine of a
    signed channel, mapped into (0,1). Non-monotone in the channel, so a linear
    read of the scene parameters cannot invert it, while the fold is still
    injective over the observed channel range (the certificate checks that).
    Amplitude and phase are the pre-registered design-pass constants."""
    return float(np.clip(0.5 * (1.0 + math.sin(N2_FOLD_AMP * x + N2_FOLD_PHASE)),
                         0.0, 1.0))


def _knobs_from_u(u: np.ndarray) -> np.ndarray:
    """12 label-free mixture channels (in (0,1)) -> the 7 lavfi knobs.

    None of the seven is monotone in any dial: the five continuous knobs take a
    folded sin-response of one channel, and noise / occupant count take a
    PRODUCT of two channels, `0.5*(1 + w_i*w_j)` with `w = 2u - 1` (the dial's
    effect on those flips with the other channel). Channels are paired so all
    twelve participate; the occupant count reuses channels 0 and 6, coupling
    the knob set.
    """
    n = len(u)

    def w(i: int) -> float:
        return 2.0 * float(u[i % n]) - 1.0

    def prod(i: int, j: int) -> float:
        return float(np.clip(0.5 * (1.0 + w(i) * w(j)), 0.0, 1.0))

    return np.array([
        40.0 + 215.0 * _fold(w(0)),
        40.0 + 215.0 * _fold(w(1)),
        40.0 + 215.0 * _fold(w(2)),
        -0.25 + 0.45 * _fold(w(3)),
        0.60 + 1.00 * _fold(w(4)),
        2 + int(round(58.0 * prod(10, 11))),
        1 + int(round(8.0 * prod(0, 6))),
    ], float)


def knobs_mixture(bank: list) -> tuple[dict, dict]:
    """Arm N2 — roomgen's frozen nonlinear mixture -> 7 knobs, for the whole bank.

    dial triple -> latent -> o = tanh(z @ W + b) * gain  (frozen random physics)
    -> label-free SVD of the bank's own observation matrix (the dial response
    directions) -> per-channel logistic normalisation (label-free). Labels and
    the encoder never enter; the readout is fixed before any embedding exists,
    the same status as E12's PCA basis.
    """
    W_, b_, gain_, src = carrier_weights()
    if W_.shape != (LATENT_DIM, OBS_DIM) or b_.shape != (OBS_DIM,) \
            or gain_.shape != (OBS_DIM,):
        raise ValueError(f"unexpected mixture shapes: W {W_.shape}, b {b_.shape}, "
                         f"gain {gain_.shape}")
    Z = np.stack([_latent(float(r["target"][0]), float(r["target"][1]),
                          float(r["target"][2]), r["seed"]) for r in bank])
    O = np.tanh(Z @ W_ + b_) * gain_                 # (n_rooms, OBS_DIM)
    Oc = O - O.mean(0)
    _, S, Vt = np.linalg.svd(Oc, full_matrices=False)
    n_dir = int(min(N_READOUT_CHANNELS, Vt.shape[0], len(bank)))
    Q = Oc @ Vt[:n_dir].T                            # (n_rooms, n_dir)
    sd = Q.std(0) + 1e-9
    U = np.array([[_sig(1.8 * Q[i, j] / sd[j]) for j in range(n_dir)]
                  for i in range(len(bank))])
    knobs = {r["name"]: _knobs_from_u(U[i]) for i, r in enumerate(bank)}
    info = {
        "carrier_source": src,
        "latent_dim": int(W_.shape[0]),
        "obs_dim": int(W_.shape[1]),
        "readout_channels": n_dir,
        "svd_singular_values": [round(float(x), 4) for x in S[:n_dir]],
        "channel_std": [round(float(x), 4) for x in sd],
        "readout": (f"folded channel responses: 5 knobs = 0.5*(1+sin("
                    f"{N2_FOLD_AMP}*w+{N2_FOLD_PHASE})), 2 knobs = products of "
                    f"two channels"),
        "note": ("frozen tanh(Wz+b)*gain physics from roomgen; the readout "
                 "(SVD directions + logistic scaling + folded/product channel "
                 "responses) uses label-free bank statistics only, exactly like "
                 "E12's PCA basis. Per-room nuisance dims make the render a "
                 "function of (dial, room seed), not of the dial alone."),
    }
    return knobs, info


def build_arm_knobs(bank: list) -> tuple[dict, dict]:
    """Every arm's knob vector for every room (all CPU, no model)."""
    K = {a: {} for a in ARMS}
    for r in bank:
        m, v, p = (float(r["target"][0]), float(r["target"][1]),
                   float(r["target"][2]))
        K["L"][r["name"]] = knobs_linear(m, v, p)
        K["N1"][r["name"]] = knobs_warp(m, v, p)
    K["N2"], n2_info = knobs_mixture(bank)
    return K, n2_info


# --------------------------------------------------------------------- #
# Rendering (one shared renderer: only the KNOBS differ between arms)    #
# --------------------------------------------------------------------- #
def render_scene(knobs: np.ndarray, room_seed: int) -> str:
    """7 knobs -> the lavfi chain. Byte-identical to what E12's stage_source
    emits for the same knobs (audited by `mirror_check`)."""
    r, g, b = (int(np.clip(round(float(knobs[j])), *KNOB_CLIP[j])) for j in range(3))
    bright = float(np.clip(knobs[3], *KNOB_CLIP[3]))
    contrast = float(np.clip(knobs[4], *KNOB_CLIP[4]))
    noise = int(np.clip(round(float(knobs[5])), *KNOB_CLIP[5]))
    n_occ = int(np.clip(round(float(knobs[6])), *KNOB_CLIP[6]))
    parts = [
        f"color=c=0x{r:02x}{g:02x}{b:02x}:s={W}x{H}:r={RATE}:d={SECONDS}",
        f"eq=brightness={bright:+.3f}:contrast={contrast:.2f}",
        f"noise=alls={noise}:allf=t:all_seed={room_seed}",
    ]
    for (x, y) in _boxes(room_seed, n_occ):
        parts.append(f"drawbox=x={x}:y={y}:w=12:h=12:color=white@0.85:t=fill")
    return ",".join(parts)


def mirror_check(bank: list, K: dict) -> dict:
    """Arm L must BE E12's carrier: render E13's mirrored knobs and E12's
    stage_source for the same (m,v,p,seed) and compare strings."""
    bad = []
    for r in bank:
        m, v, p = (float(r["target"][0]), float(r["target"][1]),
                   float(r["target"][2]))
        if render_scene(K["L"][r["name"]], r["seed"]) != stage_source(m, v, p, r["seed"]):
            bad.append(r["name"])
    return {"match": not bad, "n_rooms": len(bank),
            "mismatches": bad[:5],
            "note": ("E13's Arm-L knobs are a mirror of e12.stage_source; a "
                     "mismatch means Arm L is NOT E12's carrier and the "
                     "certificate numbers for L are not comparable.")}


# --------------------------------------------------------------------- #
# Room bank (scripts + the elephant's own labels — one bank, all arms)   #
# --------------------------------------------------------------------- #
def build_bank(n_replicates: int) -> list:
    """E12's 27-cell grid, one staged script per room, labels from the real
    elephant DialBank (never hand-typed). Identical for every arm."""
    grid = build_dial_grid()
    entries = []
    for rep in range(max(int(n_replicates), 1)):
        for r in grid:
            q = dict(r)
            if rep:
                q["name"] = f"{r['name']}_r{rep}"
                q["seed"] = int(r["seed"]) + 100000 * rep
            entries.append(q)
    bank = []
    for r in entries:
        m, v, p = r["target"]
        script = stage_transcript(m, v, p, r["seed"])
        readings = read_room(room_from_script(r["name"], script))
        bank.append({
            "name": r["name"],
            "seed": int(r["seed"]),
            "target": np.array([m, v, p], float),
            "label": np.array([readings.get(d, 0.0) for d in DIAL_NAMES], float),
            "extra": {d: round(float(readings.get(d, 0.0)), 6) for d in EXTRA_DIALS},
        })
    return bank


# --------------------------------------------------------------------- #
# Carrier certificate (CPU-only, label-free audit of the intervention)    #
# --------------------------------------------------------------------- #
def _poly2(K: np.ndarray) -> np.ndarray:
    """Degree-2 expansion of a (reduced) knob matrix (ridge's mean-centring
    supplies the intercept)."""
    K = np.asarray(K, float)
    n, k = K.shape
    cols = [K, K ** 2]
    for i in range(k):
        for j in range(i + 1, k):
            cols.append((K[:, i] * K[:, j])[:, None])
    return np.concatenate(cols, axis=1)


def _standardize(A: np.ndarray) -> np.ndarray:
    A = np.asarray(A, float)
    return (A - A.mean(0)) / (A.std(0) + 1e-12)


def _reduced_quadratic(km: np.ndarray, k: int = 4) -> np.ndarray:
    """Degree-2 expansion of the leading k label-free principal directions of
    the knob matrix. With 27 rooms, the full 7-knob quadratic (35 terms) is
    under-determined and its LOO R2 collapses through overfitting; the reduced
    basis (4 + 10 = 14 terms) is the readable version, and is BOOKED rather
    than gated."""
    Z = _standardize(km)
    Zc = Z - Z.mean(0)
    _, _, Vt = np.linalg.svd(Zc, full_matrices=False)
    kk = int(min(k, Vt.shape[0], Zc.shape[1]))
    return _poly2(Zc @ Vt[:kk].T)


def _pairwise_dist(Z: np.ndarray) -> np.ndarray:
    Z = np.asarray(Z, float)
    return np.sqrt(np.maximum(((Z[:, None, :] - Z[None, :, :]) ** 2).sum(-1), 0.0))


def _distcorr(X: np.ndarray, y: np.ndarray) -> float:
    """Distance correlation (Székely) — dependence of ANY form, so it stays
    high for a nonlinear carrier that a linear read cannot invert (which is why
    it, and not a linear R2, is the certificate's dependence test)."""
    Z = _standardize(X)
    yy = np.asarray(y, float).reshape(-1, 1)
    yy = (yy - yy.mean()) / (yy.std() + 1e-12)

    def _dc(M):
        return M - M.mean(0, keepdims=True) - M.mean(1, keepdims=True) + M.mean()

    A, B = _dc(_pairwise_dist(Z)), _dc(_pairwise_dist(yy))
    dcov2 = float((A * B).mean())
    den = math.sqrt(float((A * A).mean()) * float((B * B).mean()))
    return float(math.sqrt(max(dcov2, 0.0)) / math.sqrt(den)) if den > 1e-12 else 0.0


def _dial_curvature(km: np.ndarray, targets: np.ndarray, i: int) -> float:
    """Direct, assumption-free measure of how NON-AFFINE the carrier is in dial
    i: the normalized second difference of the knob response along that dial's
    axis, ||k(hi) - 2k(mid) + k(lo)|| / ||k(hi) - k(lo)||, averaged over the
    nine blocks with the other two dials fixed. An affine carrier measures
    exactly 0.000 (Arm L does; that is the certificate's discriminative check),
    a curved or folded one measures well above it. No fitting, no capacity, no
    cross-validation — it reads the carrier definition itself. Per-room nuisance
    does enter the three renders, so the mean over nine blocks is what makes the
    statistic a dial-axis property rather than a room property.
    """
    tab = {tuple(round(float(x), 6) for x in t): np.asarray(k, float)
           for t, k in zip(np.asarray(targets, float), np.asarray(km, float))}
    others = [j for j in range(3) if j != i]
    levels = [GRID_M, GRID_V, GRID_P]
    vals = []
    for a in levels[others[0]]:
        for b in levels[others[1]]:
            pts = []
            for lv in levels[i]:
                key = [0.0, 0.0, 0.0]
                key[others[0]], key[others[1]], key[i] = a, b, lv
                hit = tab.get(tuple(round(x, 6) for x in key))
                if hit is None:
                    pts = []
                    break
                pts.append(hit)
            if len(pts) == 3:
                span = float(np.linalg.norm(pts[2] - pts[0]))
                if span > 1e-9:
                    vals.append(float(np.linalg.norm(pts[0] - 2.0 * pts[1] + pts[2])) / span)
    return float(np.mean(vals)) if vals else float("nan")


def _knn_loo_r2(km: np.ndarray, ycol: np.ndarray, k: int = N2_KNN) -> float:
    """k-NN (distance-weighted) leave-one-out R2 on the standardized knobs — a
    flexible, low-capacity NONLINEAR read. It answers 'is the dial recoverable
    from the scene parameters at all?', which is the liveness half of the
    certificate (a linear read of the same knobs is reported separately)."""
    Z = _standardize(km)
    y = np.asarray(ycol, float)
    n = len(Z)
    pred = np.zeros(n)
    kk = int(min(max(k, 1), n - 1))
    for i in range(n):
        d = ((Z - Z[i]) ** 2).sum(1)
        d[i] = np.inf
        idx = np.argsort(d)[:kk]
        wgt = 1.0 / (np.sqrt(d[idx]) + 1e-9)
        pred[i] = float((wgt * y[idx]).sum() / wgt.sum())
    den = float(((y - y.mean()) ** 2).sum())
    return 1.0 - float(((y - pred) ** 2).sum()) / max(den, 1e-12)


def carrier_certificate(knob_matrix: np.ndarray, targets: np.ndarray) -> tuple[dict, dict]:
    """Audit of a carrier — the intervention's own definition, measured.

    (a) NOT AFFINE: mean normalized curvature of the dial response >= CURV_FLOOR.
        Arm L measures 0.000 by construction, so the certificate is
        discriminative by inspection.
    (b) LIVE CHANNEL: the 27 knob vectors are pairwise distinct, and >= 2 of 3
        dials show BOTH a distance-correlation above its 200-shuffle null
        (p <= DCORR_P — dependence of any form) AND a 3-NN LOO-R2 >= KNN_FLOOR
        (the dial is recoverable by a flexible nonlinear read). This is what
        rules out the "the render was dead" explanation of a KILL.
    Booked: the linear LOO-R2 per dial (how affinely decodable the carrier's own
    scene parameters are), the reduced-quadratic LOO-R2, the best single-knob
    Spearman, the curvature and k-NN per dial, and the distance-correlation
    permutation p. Uses the design triple only: never elephant labels, never
    embeddings.
    """
    lin = np.asarray(knob_matrix, float)
    quad = _reduced_quadratic(lin)
    tgt = np.asarray(targets, float)
    g = np.arange(len(lin))
    rng = np.random.default_rng(SEED + 17)
    per = {}
    for i, d in enumerate(DIAL_NAMES):
        y = tgt[:, i:i + 1]
        p_lin, _ = loro_predict(lin, y, g)
        p_quad, _ = loro_predict(quad, y, g)
        r2l = float(r2_columns(y, p_lin)[0])
        r2q = float(r2_columns(y, p_quad)[0])
        dc = _distcorr(lin, tgt[:, i])
        null = np.array([_distcorr(lin, rng.permutation(tgt[:, i]))
                         for _ in range(DCOR_PERMS)])
        per[d] = {
            "curvature": round(_dial_curvature(lin, tgt, i), 4),
            "knn_loo_r2": round(_knn_loo_r2(lin, tgt[:, i]), 4),
            "distcorr": round(dc, 4),
            "distcorr_null95": round(float(np.percentile(null, 95)), 4),
            "distcorr_p": round(float((null >= dc).mean()), 4),
            "lin_loo_r2": round(r2l, 4),
            "quad_loo_r2": round(r2q, 4),
            "nonlin_gain": round(r2q - r2l, 4),
            "best_knob_abs_spearman": round(
                max(abs(spearman(lin[:, j], y[:, 0])) for j in range(lin.shape[1])), 4),
        }
    inj = _injectivity(lin)
    curvs = [per[d]["curvature"] for d in DIAL_NAMES]
    lins = [per[d]["lin_loo_r2"] for d in DIAL_NAMES]
    n_live = int(sum(1 for d in DIAL_NAMES
                     if per[d]["distcorr_p"] <= DCORR_P
                     and per[d]["knn_loo_r2"] >= KNN_FLOOR))
    mean_curv = float(np.nanmean(curvs)) if curvs else float("nan")
    summary = {
        "mean_curvature": round(mean_curv, 4),
        "nonaffine_pass": bool(mean_curv >= CURV_FLOOR),
        "mean_lin_loo_r2": round(float(np.mean(lins)), 4),
        "mean_quad_loo_r2": round(float(np.mean(
            [per[d]["quad_loo_r2"] for d in DIAL_NAMES])), 4),
        "n_dials_live": n_live,
        "live_pass": bool(n_live >= CERT_LIVE_DIALS_FLOOR and inj["injective"]),
        "injectivity": inj,
        "floors": {"curvature": CURV_FLOOR, "knn_loo_r2": KNN_FLOOR,
                   "distcorr_p": DCORR_P, "live_dials": CERT_LIVE_DIALS_FLOOR},
    }
    summary["pass"] = bool(summary["nonaffine_pass"] and summary["live_pass"])
    return per, summary


def _injectivity(km: np.ndarray) -> dict:
    """Are the room knob vectors pairwise distinct? A carrier that renders two
    rooms to the same scene cannot support ANY read of the differing dials, so
    injectivity is the hard half of liveness (the min pairwise distance is the
    margin, on standardized knobs so no single knob's units dominate)."""
    Z = _standardize(km)
    D = _pairwise_dist(Z)
    n = len(Z)
    dmin, dups = float("inf"), 0
    for i in range(n):
        for j in range(i + 1, n):
            d = float(D[i, j])
            dmin = min(dmin, d)
            if d < 1e-9:
                dups += 1
    return {"min_pairwise_distance": round(dmin, 5), "duplicate_pairs": int(dups),
            "injective": bool(dups == 0 and dmin > 1e-6)}


def knob_ranges(knob_matrix: np.ndarray) -> dict:
    km = np.asarray(knob_matrix, float)
    return {KNOB_NAMES[j]: {
        "min": round(float(km[:, j].min()), 3),
        "max": round(float(km[:, j].max()), 3),
        "n_unique": int(len(np.unique(np.round(km[:, j], 4)))),
    } for j in range(km.shape[1])}


def harness_selftest() -> dict:
    """CPU-only, carrier-free, model-free check of the IMPORTED probe path
    (pca_basis -> loro_predict -> pick_lambda -> _ridge_path_pred ->
    r2_columns): a synthetic embedding with a known 3-dial linear signal must
    read at LORO R2 >= 0.90, and shuffled labels must collapse below 0.10."""
    rng = np.random.default_rng(SEED + 5)
    n_rooms, n_still, d = 12, 6, 48
    T = rng.uniform(-1.0, 1.0, (n_rooms, 3))
    A = rng.standard_normal((3, d))
    Xr = T @ A + 0.05 * rng.standard_normal((n_rooms, d))
    X = np.repeat(Xr, n_still, 0) + 0.02 * rng.standard_normal((n_rooms * n_still, d))
    groups = np.repeat(np.arange(n_rooms), n_still)
    Y = np.repeat(T, n_still, 0)
    basis, _ = pca_basis(X, 12)
    z = X @ basis[:, :12]
    pred, _ = loro_predict(z, Y, groups)
    r2_signal = float(r2_columns(Y, pred).min())
    perm = rng.permutation(n_rooms)
    Yp = np.repeat(T[perm], n_still, 0)
    pred_p, _ = loro_predict(z, Yp, groups)
    r2_null = float(r2_columns(Yp, pred_p).max())
    return {"r2_min_signal": round(r2_signal, 4),
            "r2_max_shuffled": round(r2_null, 4),
            "pass": bool(r2_signal >= 0.90 and r2_null < 0.10)}


# --------------------------------------------------------------------- #
# Embedding collection + per-arm probe report                            #
# --------------------------------------------------------------------- #
def collect_arm(arm: str, K: dict, bank: list, model, processor, dev, torch):
    """Render each room through THIS arm's carrier and embed 12 stills (E12's
    embed_stills verbatim: E9 still sampling, preprocessing, forward, and the
    luminance/grayscale-pixel controls)."""
    X, Y, Yt, groups, lum, pix = [], [], [], [], [], []
    for gi, r in enumerate(bank):
        src = render_scene(K[arm][r["name"]], r["seed"])
        frames = ppms_from_lavfi(src, SECONDS, RATE, (W, H))
        if not frames:
            raise RuntimeError(f"no frames from {arm} carrier for {r['name']!r}")
        vecs, l, px = embed_stills(model, processor, dev, frames, r["seed"])
        groups.append(np.full(len(vecs), gi))
        X.append(vecs)
        Y.append(np.repeat(r["label"][None, :], len(vecs), axis=0))
        Yt.append(np.repeat(r["target"][None, :], len(vecs), axis=0))
        lum.append(l)
        pix.append(px)
        if dev == "cuda":
            torch.cuda.empty_cache()
        if (gi + 1) % 9 == 0 or gi == 0:
            log(f"{arm} room {gi + 1}/{len(bank)} {r['name']} "
                f"knobs={np.round(K[arm][r['name']], 2).tolist()}")
    return (np.concatenate(X), np.concatenate(Y), np.concatenate(Yt),
            np.concatenate(groups), np.concatenate(lum), np.concatenate(pix))


def arm_report(arm: str, data: tuple, knob_matrix: np.ndarray,
               targets: np.ndarray) -> dict:
    """E12's probe sweep verbatim on this arm, E12's per-dial gate, plus the
    controls. The gate ladder is E12's G1/G2/G3 applied to this arm."""
    X, Y, Yt, groups, lum, pix = data
    basis, evr = pca_basis(X, K_WIDE)
    rng = np.random.default_rng(SEED)
    sweep, _ = probe_sweep(X, Y, groups, basis, (K_STRICT, K_PRIMARY, K_WIDE), rng)

    zc = X @ basis[:, :K_PRIMARY]
    lum_col = lum.reshape(-1, 1).astype(np.float64)
    pred_lum, _ = loro_predict(zc, lum_col, groups)
    r2_lum = float(r2_columns(lum_col, pred_lum)[0])

    pred_px, _ = loro_predict(pix, Y, groups)
    r2_px = r2_columns(Y, pred_px)

    room_acc = room_halfsplit_acc(zc, groups)
    room_chance = 1.0 / max(len(np.unique(groups)), 1)

    passes = {}
    for i, d in enumerate(DIAL_NAMES):
        r64 = sweep["r2_still_loro"]["64"][d]
        r16 = sweep["r2_still_loro"][str(K_STRICT)][d]
        rroom = sweep["r2_room_loro"]["64"][d]
        n95 = sweep["null95"][d]
        passes[d] = bool(r64 >= R2_FLOOR
                         and rroom >= R2_ROOM_FLOOR
                         and r16 >= R2_TOP_PC_FRACTION * r64
                         and r64 > n95)
    n_pass = int(sum(1 for d in DIAL_NAMES if passes[d]))
    mean_r64 = float(np.mean([sweep["r2_still_loro"]["64"][d] for d in DIAL_NAMES]))
    mean_null95 = float(np.mean([sweep["null95"][d] for d in DIAL_NAMES]))
    room_ok = bool(room_acc >= ARM_SEP_FLOOR)

    # E12's G1/G2/G3 ladder, verbatim in shape.
    if n_pass >= 2 and room_ok:
        ladder = "KEEP"
    elif n_pass >= 1 or mean_r64 > mean_null95:
        ladder = "INCONCLUSIVE"
    else:
        ladder = "KILL"

    per_dial, cert_summary = carrier_certificate(knob_matrix, targets)
    return {
        "title": ARM_TITLES[arm],
        "cells": int(X.shape[0]),
        "emb_dim": int(X.shape[1]),
        "pca_evr_k16": round(float(evr[:K_STRICT].sum()), 4),
        "pca_evr_k64": round(float(evr[:K_PRIMARY].sum()), 4),
        "pca_evr_k256": round(float(evr[:K_WIDE].sum()), 4),
        "r2_still_loro": sweep["r2_still_loro"],
        "r2_room_loro": sweep["r2_room_loro"],
        "room_space_k": sweep.get("room_space_k", {}),
        "spearman_loro_k64": sweep["spearman_loro"],
        "perm_null95_k64": sweep["null95"],
        "perm_p_k64": sweep["perm_p"],
        "lambda_median_k64": sweep.get("lambda_median"),
        "tertile_acc_k64": sweep["tertile_acc"],
        "tertile_p_k64": sweep["tertile_p"],
        "g0b_luminance_r2_k64": round(r2_lum, 4),
        "controls": {
            "raw_pixel_r2_k64": {d: round(float(r2_px[i]), 4)
                                 for i, d in enumerate(DIAL_NAMES)},
            "luminance_spearman": {d: round(spearman(lum, Y[:, i]), 4)
                                   for i, d in enumerate(DIAL_NAMES)},
            "room_identity_acc": round(room_acc, 4),
            "room_identity_chance": round(room_chance, 4),
        },
        "carrier_certificate_dials": per_dial,
        "carrier_certificate": cert_summary,
        "knob_ranges": knob_ranges(knob_matrix),
        "gate": {
            "dial_pass": passes,
            "n_pass": n_pass,
            "mean_r2_k64": round(mean_r64, 4),
            "mean_null95_k64": round(mean_null95, 4),
            "room_sep_ok": room_ok,
            "room_sep_floor": ARM_SEP_FLOOR,
            "ladder": ladder,
        },
    }


# --------------------------------------------------------------------- #
# CPU-only mode (no model, no GPU): the plumbing test                    #
# --------------------------------------------------------------------- #
def cpu_only() -> dict:
    st = harness_selftest()
    bank = build_bank(N_REPLICATES)
    K, n2_info = build_arm_knobs(bank)
    targets = np.stack([r["target"] for r in bank])
    knob_mats = {a: np.stack([K[a][r["name"]] for r in bank]) for a in ARMS}
    certs = {}
    for a in ARMS:
        per, summ = carrier_certificate(knob_mats[a], targets)
        certs[a] = {"per_dial": per, "summary": summ, "knob_ranges": knob_ranges(knob_mats[a])}
    out = {
        "experiment": "E13 nonlinear-carrier dial read",
        "mode": "cpu-only (no model, no GPU)",
        "seed": SEED, "primary_arm": PRIMARY_ARM, "arms": list(ARMS),
        "rooms": len(bank), "replicates": N_REPLICATES,
        "carrier_mixture": n2_info,
        "harness_selftest": st,
        "arm_L_mirror_check": mirror_check(bank, K),
        "carrier_certificates": certs,
        "staging_fidelity_spearman_target_vs_label": {
            d: round(spearman(targets[:, i],
                              np.stack([r["label"] for r in bank])[:, i]), 4)
            for i, d in enumerate(DIAL_NAMES)},
        "sample_lavfi_sources": {
            a: render_scene(K[a][bank[0]["name"]], bank[0]["seed"]) for a in ARMS},
        "note": ("No verdict in CPU-only mode. Watch: the N2 certificate must "
                 "pass (curvature above the floor AND live), while Arm L must "
                 "measure curvature 0.000 with a linear read of 1.000 — that "
                 "pair certifies the intervention happened."),
    }
    print(json.dumps(out, indent=2))
    return out


# --------------------------------------------------------------------- #
# Main                                                                  #
# --------------------------------------------------------------------- #
def main() -> dict:
    if "--cpu-only" in sys.argv:
        return cpu_only()

    ok, reason, guard_info = preflight_guard()
    if not ok:
        out = {"experiment": "E13 nonlinear-carrier dial read", "verdict": "ABORTED",
               "reason": reason, "guard_preflight": guard_info}
        print(json.dumps(out, indent=2))
        return out

    base = {"experiment": "E13 nonlinear-carrier dial read", "seed": SEED,
            "primary_arm": PRIMARY_ARM, "arms": list(ARMS),
            "arm_titles": ARM_TITLES, "dial_names": DIAL_NAMES,
            "extra_dials": EXTRA_DIALS, "k_primary": K_PRIMARY,
            "guard_preflight": guard_info, "replicates": N_REPLICATES}

    # G0d — cheapest gate first; if the probe path is broken nothing else is
    # interpretable (and it costs nothing, model-free).
    selftest = harness_selftest()
    log(f"harness self-test: {selftest}")

    # Bank + carriers + certificates — all CPU, all before the model.
    bank = build_bank(N_REPLICATES)
    log(f"bank: {len(bank)} rooms (replicates={N_REPLICATES})")
    try:
        K, n2_info = build_arm_knobs(bank)
    except Exception as e:  # noqa: BLE001
        out = dict(base)
        out.update({"verdict": "ABORTED", "harness_selftest": selftest,
                    "reason": f"carrier construction failed: {e}"})
        print(json.dumps(out, indent=2))
        return out
    mirror = mirror_check(bank, K)
    targets = np.stack([r["target"] for r in bank])
    labels = np.stack([r["label"] for r in bank])
    knob_mats = {a: np.stack([K[a][r["name"]] for r in bank]) for a in ARMS}
    certificates = {}
    for a in ARMS:
        per, summ = carrier_certificate(knob_mats[a], targets)
        certificates[a] = {"per_dial": per, "summary": summ,
                           "knob_ranges": knob_ranges(knob_mats[a])}
    log(f"carrier certificates: "
        + "; ".join(f"{a}: mean_curv={certificates[a]['summary']['mean_curvature']} "
                    f"live={certificates[a]['summary']['n_dials_live']}/3 "
                    f"nonaffine={certificates[a]['summary']['nonaffine_pass']} "
                    f"pass={certificates[a]['summary']['pass']}" for a in ARMS))

    # G0a — staging fidelity (script -> elephant dial bank), E12's G0a.
    fid = {d: round(spearman(targets[:, i], labels[:, i]), 4)
           for i, d in enumerate(DIAL_NAMES)}
    fid_pass = bool(sum(1 for d in DIAL_NAMES if fid[d] >= FIDELITY_FLOOR) >= 2)
    # C5 — the extra dials are booked (read by the same bank, never gated).
    extra_stats = {d: {"min": round(float(min(r["extra"][d] for r in bank)), 4),
                       "max": round(float(max(r["extra"][d] for r in bank)), 4),
                       "std": round(float(np.std([r["extra"][d] for r in bank])), 4)}
                   for d in EXTRA_DIALS}

    if not selftest["pass"]:
        out = dict(base)
        out.update({"verdict": "INVALID_HARNESS", "harness_selftest": selftest,
                    "reason": "G0d: the imported probe failed the synthetic self-test"})
        print(json.dumps(out, indent=2))
        return out
    if not fid_pass:
        out = dict(base)
        out.update({"verdict": "INVALID_STAGING", "harness_selftest": selftest,
                    "staging_fidelity_spearman_target_vs_label": fid,
                    "carrier_certificates": certificates,
                    "arm_L_mirror_check": mirror,
                    "reason": "G0a: the staged scripts did not move >= 2/3 dials"})
        print(json.dumps(out, indent=2))
        return out
    if len(bank) < 8:
        out = dict(base)
        out.update({"verdict": "ABORTED", "harness_selftest": selftest,
                    "reason": f"only {len(bank)} rooms — grouped CV would be meaningless"})
        print(json.dumps(out, indent=2))
        return out

    import torch
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    log(f"loading I-JEPA ({dev})...")
    try:
        model_used, model, processor, load_notes = load_encoder(dev)
    except Exception as e:  # noqa: BLE001
        out = dict(base)
        out.update({"verdict": "ABORTED", "harness_selftest": selftest,
                    "reason": f"model load failed: {e}"})
        print(json.dumps(out, indent=2))
        return out
    log(f"using {model_used}")

    reports = {}
    try:
        for a in ARMS:
            log(f"arm {a}: rendering + embedding {len(bank)} rooms x {N_STILLS} stills")
            data = collect_arm(a, K, bank, model, processor, dev, torch)
            reports[a] = arm_report(a, data, knob_mats[a], targets)
            log(f"arm {a}: r2_still_loro(k64)="
                f"{reports[a]['r2_still_loro']['64']} ladder={reports[a]['gate']['ladder']}")
    except Exception as e:  # noqa: BLE001
        out = dict(base)
        out.update({"verdict": "ABORTED", "harness_selftest": selftest,
                    "reason": f"frame/embed/probe failed: {e}"})
        print(json.dumps(out, indent=2))
        return out

    primary = reports[PRIMARY_ARM]
    control = reports["L"]
    sens_pass = bool(control["g0b_luminance_r2_k64"] >= SENSITIVITY_FLOOR)
    cert_primary_ok = bool(certificates[PRIMARY_ARM]["summary"]["pass"])
    control_keeps = bool(control["gate"]["ladder"] == "KEEP")

    kill_scope = None
    if primary["gate"]["ladder"] == "KILL":
        kill_scope = ("dies only at the random nonlinear mixture (N2): the read "
                      "survives the deterministic bent warp (N1)"
                      if reports["N1"]["gate"]["ladder"] == "KEEP"
                      else "dies at BOTH nonlinear rungs (N1 bent warp and N2 "
                           "mixture)")

    if not sens_pass:
        verdict = "INVALID_HARNESS"
        reason = ("G0b: the luminance sensitivity control on Arm L (E12's own "
                  "carrier) fell below the floor — the probe is blind here")
    elif not cert_primary_ok:
        verdict = "INVALID_STAGING"
        reason = ("G0c: the PRIMARY carrier failed its certificate (not "
                  "nonlinear, or not a live dial channel) — the arm tested "
                  "nothing, so this is NOT a KILL")
    elif not control_keeps:
        verdict = "INVALID_CONTROL"
        reason = ("Arm L (E12's carrier) did not reproduce E12's KEEP, so a "
                  "nonlinear-arm failure cannot be attributed to nonlinearity")
    else:
        verdict = primary["gate"]["ladder"]
        reason = "primary arm verdict (E12's gate, E12's thresholds)"

    deltas = {d: round(primary["r2_still_loro"]["64"][d]
                       - control["r2_still_loro"]["64"][d], 4) for d in DIAL_NAMES}

    out = dict(base)
    out.update({
        "model": model_used, "load_notes": load_notes, "device": dev,
        "rooms": len(bank), "stills_per_room": N_STILLS,
        "cells_per_arm": int(primary["cells"]),
        "label_stats": {d: {"min": round(float(labels[:, i].min()), 4),
                            "max": round(float(labels[:, i].max()), 4),
                            "std": round(float(labels[:, i].std()), 4)}
                        for i, d in enumerate(DIAL_NAMES)},
        "extra_dial_stats": extra_stats,
        "harness_selftest": selftest,
        "staging_fidelity_spearman_target_vs_label": fid,
        "g0a_staging_fidelity_pass": fid_pass,
        "arm_L_mirror_check": mirror,
        "carrier_mixture": n2_info,
        "carrier_certificates": certificates,
        "carrier_design_pass": {
            "note": ("measured on this bank in the --cpu-only design pass, before "
                     "any embedding existed; the fold strength is fixed from it"),
            "fold_amp": N2_FOLD_AMP, "fold_phase": N2_FOLD_PHASE,
            "knn_k": N2_KNN,
            "measured": {
                "L_affine": {"mean_lin_loo_r2": 1.0, "mean_curvature": 0.0},
                "N2_folded_chosen": {"mean_lin_loo_r2": 0.900,
                                     "mean_curvature": 0.471},
                "N2_product_rejected": {"mean_lin_loo_r2": -0.18,
                                        "mean_curvature": 1.21,
                                        "why": "dials unreadable (dCorr p 0.14-0.78, "
                                               "3-NN R2 negative)"},
                "N2_deep_fold_rejected": {"mean_lin_loo_r2": "0.10..0.30",
                                          "mean_curvature": "1.8..4.7",
                                          "why": "breaks liveness (3-NN R2 negative)"},
            },
        },
        "arms": reports,
        "gate_deltas_primary_minus_linear": deltas,
        "gates": {
            "g0d_harness_selftest": selftest["pass"],
            "g0a_staging_fidelity": {"floor": FIDELITY_FLOOR, "pass": fid_pass,
                                     "measured": fid},
            "g0b_sensitivity_arm_L": {"floor": SENSITIVITY_FLOOR,
                                      "measured": control["g0b_luminance_r2_k64"],
                                      "pass": sens_pass,
                                      "per_arm": {a: reports[a]["g0b_luminance_r2_k64"]
                                                  for a in ARMS}},
            "g0c_carrier_certificate_primary": certificates[PRIMARY_ARM]["summary"],
            "g1_primary": primary["gate"],
            "arm_L_control_keeps": control_keeps,
            "arm_L_ladder": control["gate"]["ladder"],
            "arm_N1_ladder": reports["N1"]["gate"]["ladder"],
            "arm_N2_ladder": reports["N2"]["gate"]["ladder"],
        },
        "kill_scope": kill_scope,
        "verdict": verdict,
        "verdict_reason": reason,
        "data_needed": [
            "ffmpeg ~/.local/bin/ffmpeg (lavfi: color, eq, noise, drawbox) — "
            "same chain as E12",
            "facebook/ijepa_vith16_1k fp16 on the RTX 4050 (E9 loader, imported)",
            "elephant package importable (dial bank = labels)",
            "roomgen.py loadable (nonlinear mixture physics); inline replica "
            "fallback recorded in carrier_source",
            f"3 arms x {len(bank)} rooms x {N_STILLS} stills ≈ "
            f"{3 * len(bank) * N_STILLS} forwards — ~8-12 min GPU, or CPU overnight",
            "GPU free (guard preflight in-process)",
        ],
        "note": (
            "E13 falsifies E12's KEEP against a NONLINEAR carrier. One frozen "
            "I-JEPA, one label bank (the elephant's own DialBank readings of the "
            "staged scripts), three carriers over the same 27-cell grid: L = "
            "E12's linear staging (positive control), N1 = frozen bent sigmoid "
            "warp (deterministic rung), N2 = roomgen's frozen nonlinear mixture "
            "tanh(Wz+b)*gain with per-room nuisance and folded channel responses "
            "(PRIMARY). KEEP = N2 passes E12's gate verbatim (>=2/3 dials: R2 "
            "k64 >= 0.30, room-level >= 0.15, top-16 PCs retain >=50%, above the "
            "200-perm null) AND room separation >= 0.75. KILL = N2 fails that "
            "gate while Arm L still keeps, i.e. the linear staging replicated "
            "and the nonlinear carrier killed the read — E12's KEEP was a "
            "staging artifact. INVALID_STAGING (dead or accidentally-linear "
            "carrier), INVALID_CONTROL (E12's KEEP did not replicate), "
            "INVALID_HARNESS and ABORTED are never KILLs. SCOPE, pre-registered: "
            "the intervention is a MEASURED moderate nonlinearity (fold "
            "amplitude 2.2; mean curvature 0.471 on N2 vs 0.000 on L; knob-space "
            "linear LOO-R2 falls 1.000 -> 0.900) that is certified live "
            "(injective knobs, distance-correlation p<=0.01, 3-NN recovery). "
            "Deeper folds and product-style carriers break linearity harder but "
            "also break recoverability (3-NN R2 negative), so they were "
            "REJECTED at design time: a KILL there would have been "
            "uninterpretable. A KEEP therefore means 'the read survives a "
            "demonstrably live, moderately nonlinear carrier', not 'survives "
            "any nonlinearity'. Other caveats: carriers are still staged; the "
            "nonlinear map is one frozen random draw (seed 2718/2719); see the "
            "module docstring for the full booking."),
    })
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
