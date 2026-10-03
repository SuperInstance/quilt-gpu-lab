"""VSB-1 tests: two-method agreement, vendor exclusion, empty-repo refusal (G1/G2-adjacent/G3)."""
import json
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent / "tools" / "vendor_strip_census.py"


def _init_repo(tmp: Path, files: dict, commit: bool = True):
    subprocess.run(["git", "init", "-q", str(tmp)], check=True)
    subprocess.run(["git", "-C", str(tmp), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp), "config", "user.name", "t"], check=True)
    for name, content in files.items():
        p = tmp / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
    if commit:
        subprocess.run(["git", "-C", str(tmp), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(tmp), "commit", "-qm", "t"], check=True)


def run_tool(repo: Path, out: Path):
    return subprocess.run([sys.executable, str(TOOL), "--repo", str(repo),
                           "--out", str(out)],
                          capture_output=True, text=True)


def test_two_method_and_vendor_exclusion(tmp_path):
    repo = tmp_path / "r"
    vendored = b"x" * 5000
    real = b"y" * 100
    _init_repo(repo, {"node_modules/pkg/index.js": vendored,
                      "src/main.py": real, "README.md": b"z" * 50})
    out = tmp_path / "census.json"
    r = run_tool(repo, out)
    assert r.returncode == 0, r.stdout + r.stderr
    d = json.loads(out.read_text())
    assert d["g1_two_method_agreement"] is True
    assert d["vendored_bytes"] == 5000 and d["vendored_files"] == 1
    assert d["real_bytes"] == 150 and d["real_files"] == 2
    assert d["top_real"][0]["path"] == "src/main.py"


def test_empty_repo_refusal(tmp_path):
    repo = tmp_path / "empty"
    _init_repo(repo, {}, commit=False)
    r = run_tool(repo, tmp_path / "c.json")
    assert r.returncode == 2
    assert "FAIL-LOUD" in (r.stdout + r.stderr)


def test_nested_vendor_dir_excluded(tmp_path):
    repo = tmp_path / "r2"
    _init_repo(repo, {"experiments/x/target/release/lib.rlib": b"v" * 900,
                      "src/main.py": b"c" * 100})
    out = tmp_path / "c2.json"
    r = run_tool(repo, out)
    assert r.returncode == 0, r.stdout + r.stderr
    d = json.loads(out.read_text())
    assert d["vendored_bytes"] == 900 and d["real_bytes"] == 100
