#!/usr/bin/env python3
"""C3b stage 0 — curate REAL-world source clips for the C3b real-domain set.

Handoff H1 (quilt-i2i/docs/HANDOFFS.md): C3's "real" domain rested on only the
2 Cosmos snapshot clips. This script determinizes ~20 curated, LICENSED,
real-footage sources into the exact C3 clip geometry so the GPU lane can
extract Cosmos-3-Edge latents next.

The determinization is byte-for-byte the law of experiments/c3_make_data.py's
real_clip(): same argv, same filter chain, same frame-aligned t0 pool law
(frame_starts), same size check, same sha256-in-1MiB-chunks hashing, same
injectivity assertion. Geometry: 16 frames, 256x256, rgb24 rawvideo, 10 fps
=> 3,145,728 bytes per clip.

t0 law for ONE clip per source (this lane's pre-registration, recorded in the
manifest): pool[0] == 0.000 s. Degeneracy guard: if the first-frame-window
clip decodes near-black (mean luma < 8/255 over the whole clip — stock/video
fades-in from black), fall back to the pool MIDPOINT, also frame-aligned and
recorded per clip. No RNG anywhere.

Provenance is non-negotiable: every source's URL, license, and credit live in
results/c3b_clips/sources.json (committed) and are mirrored per-clip into
MANIFEST.json. Source files (webm/mp4) and .rgb outputs stay OUT of git
(.gitignore); a local tarball + MANIFEST is the pick-up point for the GPU lane.

House law: subprocess LIST-FORM ONLY. Memory O(chunk): files hashed in 1 MiB
chunks; luma check loads ONE 3 MiB clip at a time.

Writes: results/c3b_clips/clips/<slug>.rgb + results/c3b_clips/MANIFEST.json
  python3 experiments/c3b_make_clips.py           # determinize + manifest
  python3 experiments/c3b_make_clips.py --check   # re-hash disk vs manifest
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time

LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(LAB, "results", "c3b_clips")
SOURCES_JSON = os.path.join(BASE, "sources.json")
MANIFEST = os.path.join(BASE, "MANIFEST.json")
CLIPS_DIR = os.path.join(BASE, "clips")
SOURCES_DIR = os.path.join(BASE, "sources")

# Geometry — MUST match c3_make_data.py (frozen in the C3 plan)
FRAMES, W, H, FPS = 16, 256, 256, 10
BYTES_PER_CLIP = FRAMES * W * H * 3  # 3,145,728
LUMA_FLOOR = 8.0  # mean R,G,B (0-255) below which t0=0 is called a black fade


def log(msg):
    print("[c3b %s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def resolve_bin(env_var, default_path, name):
    """env override -> lab default -> PATH (same law as c3_make_data.py)."""
    import shutil
    for cand in (os.environ.get(env_var), default_path):
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    found = shutil.which(name)
    if found:
        return found
    sys.exit("[c3b] FATAL: no executable %s (set %s)" % (name, env_var))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def probe_source(ffmpeg, path):
    """Same stderr-regex probe as c3_make_data.py (no ffprobe dependency)."""
    r = subprocess.run(
        [ffmpeg, "-nostdin", "-hide_banner", "-i", path],
        capture_output=True, check=False)
    err = r.stderr.decode("utf-8", "replace")
    dur = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", err)
    vid = re.search(r"Video:.*?,\s*(\d{2,5})x(\d{2,5})", err)
    fps = re.search(r"([\d.]+)\s*fps", err) or re.search(r"([\d.]+)\s*tbr", err)
    if not (dur and vid):
        raise RuntimeError("probe parse failed for %s (rc=%d)\n%s"
                           % (path, r.returncode, err[-400:]))
    seconds = int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3))
    return {"width": int(vid.group(1)), "height": int(vid.group(2)),
            "fps": fps.group(1) if fps else "?",
            "duration_s": round(seconds, 3)}


def frame_starts(duration_s):
    """c3_make_data.py law: frame-aligned t0 values that actually exist."""
    need = FRAMES / float(FPS) + 0.2
    usable = max(duration_s - need, 0.0)
    n = int(usable * FPS) + 1
    return [round(i * (1.0 / FPS), 3) for i in range(n)]


def real_clip(ffmpeg, src_path, t0, out_path):
    """EXACT argv of c3_make_data.py real_clip() — do not 'improve' it."""
    argv = [ffmpeg, "-y", "-loglevel", "error",
            "-ss", "%.3f" % t0, "-i", src_path,
            "-frames:v", str(FRAMES),
            "-vf", ("fps=%d,scale=%d:%d:force_original_aspect_ratio=increase:"
                    "flags=bilinear,crop=%d:%d" % (FPS, W, H, W, H)),
            "-pix_fmt", "rgb24", "-f", "rawvideo", out_path]
    subprocess.run(argv, check=True)
    return argv


def check_file(out_path):
    size = os.path.getsize(out_path)
    if size != BYTES_PER_CLIP:
        raise RuntimeError("%s: %d bytes != %d" % (out_path, size, BYTES_PER_CLIP))
    return sha256_file(out_path)


def mean_brightness(path):
    """Mean of all RGB bytes of ONE clip (3 MiB — O(one clip) by law)."""
    with open(path, "rb") as f:
        data = f.read()
    return sum(data) / float(len(data))


def assert_clips_injective(clips):
    seen = {}
    problems = []
    for c in clips:
        if c["sha256"] in seen:
            problems.append("DUPLICATE: %s == %s" % (c["slug"], seen[c["sha256"]]))
        seen[c["sha256"]] = c["slug"]
    if problems:
        raise RuntimeError("not injective:\n  " + "\n  ".join(problems))
    log("injectivity OK: %d clips, 0 duplicates" % len(clips))


def generate(ffmpeg):
    version = subprocess.run([ffmpeg, "-version"], capture_output=True,
                             check=True).stdout.decode("utf-8").splitlines()[0].strip()
    with open(SOURCES_JSON) as f:
        sources = json.load(f)
    os.makedirs(CLIPS_DIR, exist_ok=True)

    manifest = {
        "schema": "c3b-clips/1",
        "handoff": "H1 (quilt-i2i/docs/HANDOFFS.md)",
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ffmpeg": {"path": ffmpeg, "version": version},
        "geometry": {"frames": FRAMES, "width": W, "height": H, "fps": FPS,
                     "pix_fmt": "rgb24", "bytes_per_clip": BYTES_PER_CLIP},
        "determinization": {
            "law": "experiments/c3b_make_clips.py real_clip() == "
                   "experiments/c3_make_data.py real_clip() argv",
            "vf": ("fps=10,scale=256:256:force_original_aspect_ratio=increase:"
                   "flags=bilinear,crop=256:256"),
            "t0_law": "frame_starts(pool)[0] = 0.000; if mean RGB < %.1f/255 "
                      "(black fade-in), fallback = pool midpoint; no RNG"
                      % LUMA_FLOOR,
        },
        "clips": [],
    }

    for s in sources:
        # FIX 2026-10-04: sources.json "file" values carry the "sources/" prefix
        # (relative to BASE, not SOURCES_DIR) — joining onto SOURCES_DIR
        # double-prefixed and failed loud on the first slug. Join onto BASE.
        src_path = os.path.join(BASE, s["file"])
        if not os.path.isfile(src_path):
            raise RuntimeError("missing source file: %s" % src_path)
        probe = probe_source(ffmpeg, src_path)
        pool = frame_starts(probe["duration_s"])
        if not pool:
            raise RuntimeError("%s: no usable frame starts (%.3fs)"
                               % (s["slug"], probe["duration_s"]))
        out_path = os.path.join(CLIPS_DIR, "%s.rgb" % s["slug"])
        t0, t0_rule = pool[0], "pool[0]"
        argv = real_clip(ffmpeg, src_path, t0, out_path)
        sha = check_file(out_path)
        bright = mean_brightness(out_path)
        if bright < LUMA_FLOOR:
            t0 = pool[len(pool) // 2]
            t0_rule = "pool[mid] (black-fade fallback, mean=%.1f)" % bright
            argv = real_clip(ffmpeg, src_path, t0, out_path)
            sha = check_file(out_path)
            bright = mean_brightness(out_path)
        rec = {
            "slug": s["slug"], "origin": s["origin"], "title": s["title"],
            "source_url": s["url"], "source_page": s["page"],
            "license": s["license"], "artist": s["artist"],
            "source_file": s["file"], "source_sha256": sha256_file(src_path),
            "source_probe": probe, "source_duration_s": s.get("dur_s"),
            "t0_s": t0, "t0_rule": t0_rule,
            "frames": FRAMES, "width": W, "height": H,
            "path": os.path.relpath(out_path, LAB),
            "bytes": BYTES_PER_CLIP, "sha256": sha,
            "mean_brightness_0_255": round(bright, 2),
            "argv": argv,
        }
        manifest["clips"].append(rec)
        log("%-20s t0=%.3f [%s] bright=%5.1f  %dx%d %.1fs"
            % (s["slug"], t0, t0_rule.split()[0], bright,
               probe["width"], probe["height"], probe["duration_s"]))

    assert_clips_injective(manifest["clips"])
    with open(MANIFEST, "w") as f:
        json.dump(manifest, f, indent=1, ensure_ascii=False)
    log("DONE %d clips -> %s" % (len(manifest["clips"]), MANIFEST))


def check():
    if not os.path.isfile(MANIFEST):
        sys.exit("[c3b] FATAL: no manifest at %s" % MANIFEST)
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
    generate(ffmpeg)


if __name__ == "__main__":
    main()
