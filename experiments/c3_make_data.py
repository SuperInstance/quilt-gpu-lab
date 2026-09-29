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

House law: subprocess LIST-FORM ONLY — no shell=True, no os.system, no
shell-string calls. Memory O(chunk): files hashed in 1 MiB chunks, pixels
never loaded into python (ffmpeg writes .rgb directly).

Writes: data/c3/{synth,real}/{train,val}/*.rgb + data/c3/manifest.json.
  python3 experiments/c3_make_data.py           # generate (the fire)
  python3 experiments/c3_make_data.py --check   # re-hash disk vs manifest
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


def real_t0s(duration_s, n_clips):
    """Deterministic even t0 grid over the usable span (no RNG; recorded)."""
    need = FRAMES / float(FPS) + 0.2  # window + decode margin
    usable = max(duration_s - need, 0.0)
    if n_clips == 1:
        return [0.0]
    return [round(k * usable / (n_clips - 1), 3) for k in range(n_clips)]


def real_clip(ffmpeg, src_path, t0, out_path):
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
                     "t0_law": "even grid over (duration - frames/fps - 0.2)",
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
        t0s = {s: real_t0s(probes[s]["duration_s"], per_src) for s in REAL_SOURCES}
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


def main():
    if "--check" in sys.argv:
        check()
    ffmpeg = resolve_bin("C3_FFMPEG", "/home/eileen/.local/bin/ffmpeg", "ffmpeg")
    os.makedirs(DATA, exist_ok=True)
    generate(ffmpeg)


if __name__ == "__main__":
    main()
