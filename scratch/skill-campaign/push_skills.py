#!/usr/bin/env python3
"""Push skill-campaign SKILL.md files to their home repos via gh api --input (payload files, no shell quoting games)."""
import base64, json, subprocess, pathlib, sys

SKILLS = pathlib.Path("/home/eileen/projects/quilt-gpu-lab/scratch/skill-campaign/skills")
REPOS = {
    "quilt-c": "quilt-c",
    "quilt-tui": "quilt-tui",
    "quilt-canvas-tui": "quilt-canvas-tui",
    "superinstance-api": "superinstance-api",
    "A2A-native-notebookLM": "A2A-native-notebookLM",
    "quilt-gpu-lab": "quilt-gpu-lab",
    "git-agent": "git-agent",
    # "i2i-ledger": pending repo discovery
}
MSG = "skill: agent-callable expertise file (SKILL.md) — any agent can call on this repo for expertise (fleet skill campaign 2026-10-02)"

results = {}
for d, repo in REPOS.items():
    f = SKILLS / d / "SKILL.md"
    if not f.exists():
        results[d] = "MISSING FILE"
        continue
    payload = SKILLS / d / "payload.json"
    payload.write_text(json.dumps({
        "message": MSG,
        "content": base64.b64encode(f.read_bytes()).decode(),
    }))
    r = subprocess.run(["gh", "api", "--method", "PUT",
                        f"repos/SuperInstance/{repo}/contents/SKILL.md",
                        "--input", str(payload), "--jq", ".commit.sha"],
                       capture_output=True, text=True, timeout=60)
    if r.returncode == 0:
        results[d] = f"PUSHED {r.stdout.strip()[:12]}"
    else:
        results[d] = f"FAIL {r.stderr.strip()[:200]}"

for k, v in results.items():
    print(f"{k}: {v}")
