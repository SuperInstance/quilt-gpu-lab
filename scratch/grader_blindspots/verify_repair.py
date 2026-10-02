#!/usr/bin/env python3
"""verify_repair.py — FAIL-first evidence for the repair pins.

For the pristine kernel and for each of the three mutated kernels, stage
the battery world (same staging as selfplay.py) and run ONLY
tests/test_grader_blindspots.py. Expected: pristine GREEN; each mutation
RED on its own pin (and ideally only its own pin).
"""
from __future__ import annotations
import json, subprocess, sys, tempfile, shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE / "repo"
sys.path.insert(0, str(REPO / "tools"))
import selfplay  # noqa

SHAPES = ["phase_sign_flip", "noise_mixing_swap", "comparison_flip"]
NEW_TEST = REPO / "tests" / "test_grader_blindspots.py"
PRISTINE = (REPO / "micromoth.py").read_text()
TARGET = "tests/test_grader_blindspots.py"

def stage(tmp: Path, kernel_src: str | None) -> None:
    for src in REPO.iterdir():
        if src.name in (".git", "experiments", "__pycache__"):
            continue
        dst = tmp / src.name
        shutil.copytree(src, dst) if src.is_dir() else shutil.copy2(src, dst)
    if kernel_src is not None:
        (tmp / "micromoth.py").write_text(kernel_src)

def run(label: str, src: str | None) -> dict:
    with tempfile.TemporaryDirectory() as td:
        stage(Path(td), src)
        p = subprocess.run([sys.executable, "-m", "pytest", TARGET, "-q", "--tb=no",
                            "-p", "no:cacheprovider"], cwd=td, capture_output=True, text=True)
        out = p.stdout + p.stderr
        import re
        failed = sorted(re.findall(r"^(?:FAILED|ERROR) (\S+)", out, re.M))
        res = {"label": label, "rc": p.returncode, "failed": failed,
               "summary": [l for l in out.splitlines() if "passed" in l or "failed" in l][-1:]}
        print(json.dumps(res))
        return res

results = {}
results["pristine"] = run("pristine", PRISTINE)
for shape in SHAPES:
    mut, desc = selfplay.synthesize(PRISTINE, shape, 0)
    results[shape] = run(shape, mut)
    results[shape]["desc"] = desc

# verdict table
print("\n=== VERDICT ===")
ok = results["pristine"]["rc"] == 0
print(f"pristine green: {ok}")
for shape in SHAPES:
    catches = results[shape]["failed"]
    print(f"{shape:<22} RED={len(catches)>0} {catches}")
(HERE / "verify_repair.json").write_text(json.dumps(results, indent=2))
sys.exit(0 if ok and all(results[s]["failed"] for s in SHAPES) else 1)
