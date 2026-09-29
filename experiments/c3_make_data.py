#!/usr/bin/env python3
"""C3 stage 0 — regenerate raw video for the cross-encoder domain probe.

Pre-registered: proposals/runs/C3-data-regen-plan.md (frozen; read it first).
Builds two small raw-clip sets equivalent to the K3c domains so Cosmos-3-Edge
latents can be extracted next (C3b):

  synth — deterministic ffmpeg lavfi patterns (5 pinned families, K-law seeds)
  real  — the Cosmos snapshot's curated real example mp4s (model outputs
          excluded; they are Cosmos's own generations)

Geometry: 16 frames, 256x256, RGB24 rawvideo, 10 fps. 96 train + 32 val per
domain (K-lane n). Deterministic given (ffmpeg build, snapshot files, this
script) — audit by re-run + manifest sha256 diff.

CLIP INJECTIVITY (added after the 2026-09-29 audit):
A clip is only worth generating if the bytes it produces are not already
produced by another clip. Two ways that used to fail silently here:

  1. t0 aliasing. A source at FPS has one frame every 1/FPS seconds, so two
     t0 values inside one frame period decode to the SAME frames. real_t0s()
     used to emit `n_clips` evenly spaced points across a 4.3 s span, which
     for n_clips=48 gives a 0.0915 s step against a 0.1000 s frame period —
     fewer start points than the span has frames, so the grid aliased. 48
     requests yielded 44 distinct clips and the val split became a copy of
     train. Not a seek problem: accurate seek is ffmpeg's default for input
     -ss, and output seeking aliases identically. It is a grid problem.

  2. degenerate source families. `still` (a constant field) and `smpte`
     (7 vertical bars, static) are not injective under (t0, crop origin), so
     N requests yield 1 clip. The synth lane lost 19 of 20 duplicates to
     `still` alone.

The generator now REFUSES both rather than shipping a val split that is
byte-identical to train. It does not silently clamp: the right number of
clips is a pre-registration decision, and a generator that quietly changes
the dataset size is lying about the dataset. See assert_clips_injective().

House law: subprocess LIST-FORM ONLY — no shell=True, no os.system, no
shell-string calls. Memory O(chunk): files hashed in 1 MiB chunks, pixels
never loaded into python (ffmpeg writes .rgb directly).

Writes: data/c3/{synth,real}/{train,val}/*.rgb + data/c3/manifest.json.
  python3 experiments/c3_make_data.py           # generate (the fire)
  python3 experiments/c3_make_data.py --check   # re-hash disk vs manifest
  python3 experiments/c3_make_data.py --audit   # assert a manifest is injective
"""
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import time

LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(LAB, "data", "c3")
MANIFEST = os.path.join(DATA, "manifest.json")
PLAN = "proposals/runs/C3-data-regen-plan.md"

SNAP = ("/home/eileen/.cache/huggingface/hub/models--nvidia--Cosmos3-Edge/"
        "snapshots/344d602b128d1bbdacb43b08d0a3626f46343e29")

# Geometry (frozen in plan; matches K-lane cache geometry exactly)
FRAMES, W, H, FPS = 16, 256, 256, 10
BYTES_PER_CLIP = FRAMES * W * H * 3  # 3,145,728
N_TRAIN, N_VAL = 96, 32
SPLITS = (("train", N_TRAIN, 42), ("val", N_VAL, 1337))  # K-law split seeds
GRADIENTS_SEED = 20260929  # pinned inside the lavfi spec, mirrored here

# Fraction of the usable span given to train; the remainder goes to val. The
# two spans are DISJOINT, so disjointness does not depend on the arithmetic.
TRAIN_SPAN_FRACTION = 0.5

# 5 synth families cycled idx % 5 — every parameter pinned, no free randomness
SYNTH_FAMILIES = [
    ("still", "color=c=gray:duration=6:size=%dx%d:rate=%d" % (W, H, FPS)),
    ("testsrc", "testsrc=duration=6:size=%dx%d:rate=%d" % (W, H, FPS)),
    ("smpte", "smptebars=duration=6:size=%dx%d:rate=%d" % (W, H, FPS)),
    ("testsrc2", "testsrc2=duration=6:size=%dx%d:rate=%d" % (W, H, FPS)),
    ("gradients", "gradients=s=%dx%d:r=%d:d=6:seed=%d:speed=0.05:"
                  "nb_colors=3:c0=0x001133:c1=0x77ccff:c2=0xffee88"
                  % (W, H, FPS, GRADIENTS_SEED)),
]

# Real domain: curated REAL example inputs only (see plan; outputs excluded)
REAL_SOURCES = [
    "example_action_id_av_0_input.mp4",
    "example_action_id_av_1_input.mp4",
]


def log(msg):
    print("[c3_data %s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def resolve_bin(env_var, default_path, name):
    """env override -> lab default -> PATH. Fail loud if nothing resolves."""
    for cand in (os.environ.get(env_var), default_path):
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    found = shutil.which(name)
    if found:
        return found
    sys.exit("[c3_data] FATAL: no executable %s (set %s)" % (name, env_var))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def probe_source(ffmpeg, path):
    """Read-only metadata probe (duration/res/fps) parsed from ffmpeg stderr.
    No ffprobe dependency (the static_ffprobe wrapper rotted — module gone).
    ffmpeg exits 1 here by design (no output file); we parse stderr, fail loud."""
    import re
    r = subprocess.run(
        [ffmpeg, "-nostdin", "-hide_banner", "-i", path],
        capture_output=True, check=False)
    err = r.stderr.decode("utf-8", "replace")
    dur = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", err)
    vid = re.search(r"Video:.*?,\s*(\d{2,5})x(\d{2,5})", err)
    fps = re.search(r"([\d.]+)\s*fps", err) or re.search(r"([\d.]+)\s*tbr", err)
    if not (dur and vid):
        sys.exit("[c3_data] FATAL: probe parse failed for %s (rc=%d)\n%s"
                 % (path, r.returncode, err[-400:]))
    seconds = int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3))
    return {"width": int(vid.group(1)), "height": int(vid.group(2)),
            "fps": fps.group(1) if fps else "?",
            "duration_s": round(seconds, 3)}


def run_ffmpeg(argv):
    subprocess.run(argv, check=True)  # list-form ONLY (house law)


def synth_clip(ffmpeg, idx, split_seed, out_path):
    """K-law: family idx%5, seed split_seed*100003+idx, seek randint(0,40)/10,
    224-crop at (ox,oy) in [0,32)^2 -> bilinear resize 256 (in-filter)."""
    rng = random.Random(split_seed * 100_003 + idx)
    fam_name, spec = SYNTH_FAMILIES[idx % len(SYNTH_FAMILIES)]
    t0 = rng.randrange(0, 40) / 10.0
    ox, oy = rng.randrange(0, 32), rng.randrange(0, 32)
    argv = [ffmpeg, "-y", "-loglevel", "error",
            "-ss", "%.2f" % t0, "-f", "lavfi", "-i", spec,
            "-frames:v", str(FRAMES),
            "-vf", "crop=224:224:%d:%d,scale=%d:%d:flags=bilinear" % (ox, oy, W, H),
            "-pix_fmt", "rgb24", "-f", "rawvideo", out_path]
    run_ffmpeg(argv)
    return {"family": fam_name, "lavfi_spec": spec, "seed": split_seed * 100_003 + idx,
            "t0_s": round(t0, 2), "crop_ox": ox, "crop_oy": oy, "argv": argv}


def frame_period():
    """Seconds between two source frames. Two t0 values closer than this
    decode to the same frames, so any t0 grid must have step >= this."""
    return 1.0 / float(FPS)


def frame_starts(duration_s):
    """The frame-aligned t0 values that actually exist in the usable span.

    Index 0 is t=0; the list is truncated to the number of whole frames that
    fit after the decode margin. This is the hard ceiling on how many distinct
    clips ONE source can yield — the number the old grid silently exceeded.
    """
    need = FRAMES / float(FPS) + 0.2  # window + decode margin
    usable = max(duration_s - need, 0.0)
    n = int(usable * FPS) + 1
    return [round(i * frame_period(), 3) for i in range(n)]


def pick_frames(pool, n_clips, what):
    """Evenly spaced sample of n_clips entries from pool, no RNG, recorded.

    Refuses rather than truncating: an unsatisfiable request is a
    pre-registration error and a human has to resolve it.
    """
    if n_clips > len(pool):
        raise RuntimeError(
            "FATAL: %s asks for %d clips but the source offers only %d distinct "
            "frame starts (%.3fs usable span at %d fps, frame period %.4fs). "
            "The old grid silently aliased here. Supply more or longer sources, "
            "or change the pre-registered count."
            % (what, n_clips, len(pool),
               max(len(pool) - 1, 0) * frame_period(), FPS, frame_period()))
    if n_clips == 1:
        return [pool[0]]
    last = len(pool) - 1
    return [pool[round(k * last / float(n_clips - 1))] for k in range(n_clips)]


def split_frame_pool(duration_s, source, n_train, n_val):
    """Disjoint per-split t0 pools for one source.

    The pool of frame starts is partitioned, not re-gridded: a clip chosen for
    val cannot be a clip chosen for train because they draw from different
    lists. Step safety and split disjointness both fall out of that.
    """
    pool = frame_starts(duration_s)
    cut = int(len(pool) * TRAIN_SPAN_FRACTION)
    tr_pool, va_pool = pool[:cut], pool[cut:]
    return (pick_frames(tr_pool, n_train, "real/%s train" % source),
            pick_frames(va_pool, n_val, "real/%s val" % source))


def real_clip(ffmpeg, src_path, t0, out_path):
    """-ss is an INPUT option, so ffmpeg's accurate_seek is on by default: it
    decodes from the preceding keyframe and discards forward to t0. Fast seek
    (-noaccurate_seek) is never passed. This was checked, not assumed — moving
    -ss to an output option changes which bytes come out for ~half the grid
    but does not change how many DISTINCT clips come out. The duplicate count
    is set by the grid, not the seek. t0 must be frame-aligned; see
    frame_starts()."""
    argv = [ffmpeg, "-y", "-loglevel", "error",
            "-ss", "%.3f" % t0, "-i", src_path,
            "-frames:v", str(FRAMES),
            "-vf", ("fps=%d,scale=%d:%d:force_original_aspect_ratio=increase:"
                    "flags=bilinear,crop=%d:%d" % (FPS, W, H, W, H)),
            "-pix_fmt", "rgb24", "-f", "rawvideo", out_path]
    run_ffmpeg(argv)
    return {"argv": argv}


def check_file(out_path):
    size = os.path.getsize(out_path)
    if size != BYTES_PER_CLIP:  # fail loud — wrong frame count / short read
        raise RuntimeError("%s: %d bytes != %d" % (out_path, size, BYTES_PER_CLIP))
    return sha256_file(out_path)


def assert_clips_injective(clips):
    """The assertion this whole file exists to enforce.

    Two properties, both of which the 2026-09-29 dataset violated:
      A. within a split, every clip has distinct bytes
      B. no val clip is byte-identical to a train clip
    A duplicate is not a nuisance here: a val clip that IS a train clip makes
    the val AUC a measurement of nothing. Raises with the offending paths so
    the failure is actionable.
    """
    problems = []
    for split in sorted({c["split"] for c in clips}):
        seen = {}
        for c in clips:
            if c["split"] != split:
                continue
            if c["sha256"] in seen:
                problems.append("DUPLICATE in %s/%s: %s == %s"
                                % (c["domain"], split, c["path"], seen[c["sha256"]]))
            else:
                seen[c["sha256"]] = c["path"]
    train = {c["sha256"] for c in clips if c["split"] == "train"}
    for c in clips:
        if c["split"] == "val" and c["sha256"] in train:
            problems.append("LEAK: val clip is a train clip: %s" % c["path"])
    if problems:
        raise RuntimeError(
            "FATAL: dataset is not injective — %d problem(s), first 5:\n  %s"
            % (len(problems), "\n  ".join(problems[:5])))
    log("injectivity OK: %d clips, 0 intra-split duplicates, 0 val/train leaks"
        % len(clips))


def assert_family_injective(ffmpeg, tmpdir):
    """Pre-flight the synth families. A family that does not change when t0 or
    the crop origin changes cannot manufacture distinct clips — it will emit
    the same bytes forever. `still` and `smpte` both fail this."""
    probe = os.path.join(tmpdir, "family_probe.rgb")
    ok = True
    for name, spec in SYNTH_FAMILIES:
        shas = set()
        for ss, (ox, oy) in ((("0.00"), (10, 10)), ("2.00", (10, 10)),
                             (("4.00"), (10, 10)), ("0.00", (4, 17)),
                             ("0.00", (21, 3))):
            run_ffmpeg([ffmpeg, "-y", "-loglevel", "error",
                        "-ss", ss, "-f", "lavfi", "-i", spec,
                        "-frames:v", str(FRAMES),
                        "-vf", "crop=224:224:%d:%d,scale=%d:%d:flags=bilinear"
                               % (ox, oy, W, H),
                        "-pix_fmt", "rgb24", "-f", "rawvideo", probe])
            shas.add(check_file(probe))
        if len(shas) < 5:
            ok = False
            log("DEGENERATE FAMILY %r: %d distinct bytes from 5 (t0, crop) probes"
                % (name, len(shas)))
        else:
            log("family %-9s injective (5/5 distinct)" % name)
    if not ok:
        raise RuntimeError(
            "FATAL: a synth family is not injective under (t0, crop). It would "
            "produce the same clip N times and inflate the train set. Replace it "
            "with a time- and position-varying source, or accept the collapse "
            "explicitly in the pre-registration.")
    if os.path.isfile(probe):
        os.unlink(probe)


def generate(ffmpeg):
    t_start = time.time()
    for name in (ffmpeg,):
        if not (os.path.isfile(name) and os.access(name, os.X_OK)):
            sys.exit("[c3_data] FATAL: not executable: %s" % name)
    missing = [s for s in REAL_SOURCES if not os.path.isfile(os.path.join(SNAP, "assets", s))]
    if missing:
        sys.exit("[c3_data] FATAL: snapshot sources missing: %s" % missing)

    version = subprocess.run([ffmpeg, "-version"], capture_output=True,
                             check=True).stdout.decode("utf-8").splitlines()[0].strip()
    probes, src_sha = {}, {}
    for s in REAL_SOURCES:
        p = os.path.join(SNAP, "assets", s)
        probes[s] = probe_source(ffmpeg, p)
        src_sha[s] = sha256_file(p)
        log("real source %s: %s" % (s, probes[s]))

    # Pre-flight the synth lane before spending an hour rendering it.
    probe_dir = os.path.join(DATA, ".probe")
    os.makedirs(probe_dir, exist_ok=True)
    try:
        assert_family_injective(ffmpeg, probe_dir)
    finally:
        shutil.rmtree(probe_dir, ignore_errors=True)

    manifest = {
        "schema": "c3-data-regen/1",
        "plan": PLAN,
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ffmpeg": {"path": ffmpeg, "version": version},
        "prober": {"path": ffmpeg, "mode": "ffmpeg-stderr-regex"},
        "cosmos_snapshot": {"path": SNAP, "commit": os.path.basename(SNAP),
                            "assets_sha256": src_sha, "probes": probes},
        "geometry": {"frames": FRAMES, "width": W, "height": H, "fps": FPS,
                     "pix_fmt": "rgb24", "bytes_per_clip": BYTES_PER_CLIP},
        "domains": {
            "synth": {"families": [f for f, _ in SYNTH_FAMILIES],
                      "post": "crop=224:224:ox:oy,scale=256:256:flags=bilinear",
                      "n_train": N_TRAIN, "n_val": N_VAL,
                      "seed_law": "split_seed*100003+idx (K-law)"},
            "real": {"sources": REAL_SOURCES,
                     "post": "fps=10,cover-scale,center-crop 256x256",
                     "t0_law": "frame-aligned, per-split DISJOINT pools "
                               "partitioned at %g of the usable span"
                               % TRAIN_SPAN_FRACTION,
                     "excluded": "model-output mp4s (Cosmos generations)"},
        },
        "clips": [],
    }

    total = 0
    for split, n, split_seed in SPLITS:
        # synth domain — one clip per idx, family cycled idx % 5 (K-law)
        d = os.path.join(DATA, "synth", split)
        os.makedirs(d, exist_ok=True)
        for idx in range(n):
            out_path = os.path.join(d, "synth_%s_%03d.rgb" % (split, idx))
            rec = synth_clip(ffmpeg, idx, split_seed, out_path)
            rec.update({"domain": "synth", "split": split, "idx": idx,
                        "path": os.path.relpath(out_path, LAB),
                        "bytes": BYTES_PER_CLIP, "sha256": check_file(out_path)})
            manifest["clips"].append(rec)
            total += 1
            if (idx + 1) % 16 == 0:
                log("synth/%s %d/%d (%.0fs)" % (split, idx + 1, n, time.time() - t_start))
        # real domain — deterministic t0 grid, sources interleaved by idx
        d = os.path.join(DATA, "real", split)
        os.makedirs(d, exist_ok=True)
        per_src = n // len(REAL_SOURCES)
        if per_src * len(REAL_SOURCES) != n:
            sys.exit("[c3_data] FATAL: n=%d not divisible by %d sources"
                     % (n, len(REAL_SOURCES)))
        # Each split draws from its own disjoint half of the frame pool.
        side = 0 if split == "train" else 1
        t0s = {s: split_frame_pool(probes[s]["duration_s"], s, per_src,
                                   N_VAL // len(REAL_SOURCES))[side]
               for s in REAL_SOURCES}
        for idx in range(n):
            src_name = REAL_SOURCES[idx % len(REAL_SOURCES)]
            k = idx // len(REAL_SOURCES)
            out_path = os.path.join(d, "real_%s_%03d.rgb" % (split, idx))
            rec = real_clip(ffmpeg, os.path.join(SNAP, "assets", src_name),
                            t0s[src_name][k], out_path)
            rec.update({"domain": "real", "split": split, "idx": idx,
                        "source": src_name, "source_k": k,
                        "t0_s": t0s[src_name][k],
                        "path": os.path.relpath(out_path, LAB),
                        "bytes": BYTES_PER_CLIP, "sha256": check_file(out_path)})
            manifest["clips"].append(rec)
            total += 1
            if (idx + 1) % 16 == 0:
                log("real/%s %d/%d (%.0fs)" % (split, idx + 1, n, time.time() - t_start))

    manifest["totals"] = {"clips": total,
                          "bytes": total * BYTES_PER_CLIP,
                          "seconds": round(time.time() - t_start, 1)}
    if total != (N_TRAIN + N_VAL) * 2:
        raise RuntimeError("expected %d clips, wrote %d" % ((N_TRAIN + N_VAL) * 2, total))
    # The dataset is not written until it is proven to be injective.
    assert_clips_injective(manifest["clips"])
    with open(MANIFEST, "w") as f:
        json.dump(manifest, f, indent=1)
    log("DONE %d clips, %.1f MiB -> %s (%.1fs)"
        % (total, total * BYTES_PER_CLIP / 2**20, MANIFEST, time.time() - t_start))


def check():
    """Re-hash disk vs manifest — the reproducibility audit (no generation)."""
    if not os.path.isfile(MANIFEST):
        sys.exit("[c3_data] FATAL: no manifest at %s" % MANIFEST)
    with open(MANIFEST) as f:
        manifest = json.load(f)
    bad = 0
    for rec in manifest["clips"]:
        p = os.path.join(LAB, rec["path"])
        ok = (os.path.isfile(p) and os.path.getsize(p) == rec["bytes"]
              and sha256_file(p) == rec["sha256"])
        if not ok:
            bad += 1
            log("MISMATCH %s" % rec["path"])
    log("check: %d/%d clips verified%s"
        % (len(manifest["clips"]) - bad, len(manifest["clips"]),
           "" if not bad else " — %d MISMATCHES" % bad))
    sys.exit(1 if bad else 0)


def audit(manifest_path=MANIFEST):
    """Assert an EXISTING manifest is injective. Read-only.

    This is the check that would have caught the 2026-09-29 dataset, and it
    runs against a manifest on disk without regenerating a byte of it.
    """
    if not os.path.isfile(manifest_path):
        sys.exit("[c3_data] FATAL: no manifest at %s" % manifest_path)
    with open(manifest_path) as f:
        manifest = json.load(f)
    try:
        assert_clips_injective(manifest["clips"])
    except RuntimeError as e:
        sys.exit("[c3_data] FATAL: %s" % e)
    for s in REAL_SOURCES:
        p = os.path.join(SNAP, "assets", s)
        if not os.path.isfile(p):
            continue
        dur = probe_source(resolve_bin("C3_FFMPEG", "/home/eileen/.local/bin/ffmpeg",
                                       "ffmpeg"), p)["duration_s"]
        pool = frame_starts(dur)
        usable = (len(pool) - 1) * frame_period()
        per_src = N_TRAIN // len(REAL_SOURCES)
        log("%s: %.3fs usable span -> %d distinct frame starts (period %.4fs); "
            "%d requested per split" % (s, usable, len(pool), frame_period(), per_src))
        if per_src > len(pool) // 2:
            log("   INFEASIBLE: train needs %d but only %d frame starts are in "
                "the train half" % (per_src, len(pool) // 2))
    sys.exit(0)


def main():
    if "--check" in sys.argv:
        check()
    if "--audit" in sys.argv:
        audit()
    ffmpeg = resolve_bin("C3_FFMPEG", "/home/eileen/.local/bin/ffmpeg", "ffmpeg")
    os.makedirs(DATA, exist_ok=True)
    generate(ffmpeg)


if __name__ == "__main__":
    main()
