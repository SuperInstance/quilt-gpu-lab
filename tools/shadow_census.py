#!/usr/bin/env python3
"""SHADOW-1: last-definition-wins shadow census (pre-reg proposals/runs/SHADOW-1-shadow-census-prereg-2026-10-10.md).

AST walk over tracked experiments/*.py and tools/*.py:
  S1: module-scope name defined >=2x (def/class/assign) -> later defs shadow earlier.
  S2: module-scope name rebound by later `import X as <name>`.
Parse errors are RED-flagged (G1), never silently skipped. Deterministic output (G4).
"""
import ast, json, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

def tracked_files():
    out = subprocess.run(["git", "ls-files", "experiments", "tools"], cwd=REPO,
                         capture_output=True, text=True, check=True)
    return sorted(p for p in out.stdout.splitlines() if p.endswith(".py"))

def defs_and_imports(path):
    """Return (defs: {name: [lineno...]}, import_aliases: {name: lineno}, parse_error)."""
    defs, aliases = {}, {}
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError as e:
        return defs, aliases, f"SyntaxError: {e}"
    for node in tree.body:  # module scope only
        names = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names = [node.name]
        elif isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            names = [node.target.id]
        elif isinstance(node, ast.Import):
            for a in node.names:
                aliases[a.asname or a.name.split(".")[0]] = node.lineno
        if names:
            for n in names:
                defs.setdefault(n, []).append(node.lineno)
    return defs, aliases, None

def main():
    files = tracked_files()
    report = {"files_scanned": len(files), "parse_errors": [], "shadows": []}
    for rel in files:
        defs, aliases, err = defs_and_imports(REPO / rel)
        if err:
            report["parse_errors"].append({"file": rel, "error": err})
            continue
        for name, lines in sorted(defs.items()):
            if len(lines) >= 2:
                report["shadows"].append({
                    "file": rel, "name": name, "kind": "redefinition",
                    "killed_lines": lines[:-1], "live_line": lines[-1]})
        for name, iline in sorted(aliases.items()):
            if name in defs:
                report["shadows"].append({
                    "file": rel, "name": name, "kind": "import-shadow",
                    "killed_lines": defs[name], "live_line": iline})
    # G4 determinism: stable ordering already; emit
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    print()
    # exit code: 2 if parse errors (G1 RED), else 0 (verdict by human/booking layer)
    return 2 if report["parse_errors"] else 0

if __name__ == "__main__":
    sys.exit(main())
