#!/usr/bin/env python3
"""pinch0 card distiller: inventory + raw fetches + tier-A API dumps -> cards.jsonl + lessons.jsonl."""
import json, os, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "_raw")
API = os.path.join(BASE, "_api")

def load_tsv(path):
    rows = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 6:
                rows[p[0]] = {"name": p[0], "archived": p[1] == "true", "size": int(p[2]),
                              "language": p[3], "updated": p[4], "branch": p[5]}
    return rows

def load_meta(path):
    meta = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                p = line.rstrip("\n").split("\t")
                if len(p) >= 3 and p[0] not in meta:
                    meta[p[0]] = {"fork": p[1] == "true", "desc": p[2]}
    except FileNotFoundError:
        pass
    return meta

def read_raw(repo):
    """Return {real_path: text} for fetched raw files."""
    d = os.path.join(RAW, repo)
    out = {}
    if os.path.isdir(d):
        for fn in os.listdir(d):
            p = os.path.join(d, fn)
            try:
                if os.path.getsize(p) > 400_000:
                    continue
                with open(p, encoding="utf-8", errors="replace") as f:
                    real = fn
                    if fn.startswith("experiments_"):
                        real = "experiments/" + fn[len("experiments_"):]
                    elif fn.startswith("src_"):
                        real = "src/" + fn[len("src_"):]
                    out[real] = f.read()
            except OSError:
                continue
    return out

def load_api(repo):
    d = os.path.join(API, repo)
    res = {}
    for key in ("root", "wf", "commits"):
        p = os.path.join(d, f"{key}.json")
        if os.path.exists(p) and os.path.getsize(p) > 2:
            try:
                res[key] = json.load(open(p, encoding="utf-8"))
            except Exception:
                res[key] = None
    return res

def readme_text(raw):
    for k in ("README.md",):
        if k in raw:
            return raw[k]
    return None

def first_meaningful_lines(md, n=3, maxlen=220):
    """Skip title/badges/shields; return up to n lines of real prose."""
    if not md:
        return []
    lines = md.splitlines()
    out = []
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if s.startswith("#") and len(out) == 0:
            t = s.lstrip("#").strip()
            if t and not re.match(r"(?i)^(badges|readme|status|build|test)", t) and "|" not in t:
                continue  # skip the H1 title itself
            continue
        if s.startswith(("[![", "[!", "<", "---", "===", "![", "<!--")):
            continue
        if re.match(r"^\|", s):  # table
            continue
        if re.match(r"(?i)^#+ ", s) and not out:
            continue
        s = re.sub(r"[`*]", "", s)
        out.append(s[:maxlen])
        if len(out) >= n:
            break
    return out

def fenced_cmds(md, limit=3):
    if not md:
        return []
    cmds = []
    for m in re.finditer(r"```[a-z]*\n(.*?)```", md, re.S):
        for ln in m.group(1).splitlines():
            ln = ln.strip().lstrip("$ ").strip()
            if re.match(r"(npm (run|install|ci)|node |npx |pip |python3? |cargo |make |go run |\./)", ln) and len(ln) < 160:
                cmds.append(ln)
            if len(cmds) >= limit:
                return cmds
    return cmds

def pkg_scripts(raw):
    p = raw.get("package.json")
    if not p:
        return None
    try:
        j = json.loads(p)
        return j.get("scripts", {}), j.get("main"), j.get("bin")
    except Exception:
        return None

KIND_RULES = [
    (r"(?i)\.github$", "infra"),
    (r"(?i)(^|[-_])(game|pong|arcade|holdem|chess|sudoku|tetris|maze|snake|cards?)([-_]|$)", "game"),
    (r"(?i)(ledger|canon|receipt|wal|journal|seal|chronicle)", "ledger"),
    (r"(?i)(experiment|[-_]lab|lab[-_]|[-_]lane|lane[-_]|study|probe)", "experiment-lane"),
    (r"(?i)(writings|essay|prose|stories|poem)", "writing"),
    (r"(?i)(worker|relay|gateway|infra|router|proxy|deploy|pipeline|bridge|mesh|vector)", "infra"),
    (r"(?i)(tool|cli|kit|desk|watch|guard|pager|gauge|atlas|util)", "tool"),
]
def classify(repo, inv, meta, raw):
    name = repo
    text = (readme_text(raw) or "")[:2000]
    for pat, kind in KIND_RULES:
        if re.search(pat, name):
            return kind
    if re.search(r"(?i)\bgame\b|playable", text):
        return "game"
    if re.search(r"(?i)\bexperiment\b|\blab\b|\blane\b", text):
        return "experiment-lane"
    if re.search(r"(?i)\btools?\b", text) and re.search(r"(?i)checks?|receipt", text):
        return "tool"
    if inv["language"] in ("Rust", "Python", "TypeScript", "JavaScript", "C") and inv["size"] <= 60:
        return "experiment-lane"
    return "unknown"

CONV_PATTERNS = [
    (r"(?i)REFUSAL|refusals are|named refusal", "refusal events are first-class receipts"),
    (r"(?i)witness|witnessed|witness chain", "witness-booking (hash-chained receipts) for claims"),
    (r"(?i)falsification|kill switch|kill condition", "every claim carries a falsification condition"),
    (r"(?i)\d+/\d+ checks|checks green|pins green|self-check", "self-checking harness; green is the only accepted color"),
    (r"(?i)pre-registered|preregist", "hypotheses are pre-registered before runs"),
    (r"(?i)PENDING|VERIFIED", "claim weight law: PENDING speculation vs VERIFIED cross-use"),
    (r"(?i)CONFIRMED|REFUTED|SIMULATED", "four-verdict honesty idiom: CONFIRMED/REFUTED/SIMULATED/honest absence"),
    (r"(?i)no laptop paths|hermetic|vendored", "hermetic vendored deps; runs offline"),
    (r"(?i)negative result|failures are findings|FAIL-first", "negative results are first-class findings"),
]
def conventions(md):
    found = []
    if not md:
        return found
    head = md[:6000]
    for pat, conv in CONV_PATTERNS:
        if re.search(pat, head) and conv not in found:
            found.append(conv)
    return found[:4]

def layout_desc(repo, inv, raw, api):
    root = (api or {}).get("root")
    if root:
        dirs = sorted(x["n"] for x in root if x["t"] == "dir")
        files = sorted(x["n"] for x in root if x["t"] == "file")
        parts = []
        if dirs:
            parts.append("dirs: " + ", ".join(dirs[:10]) + ("…" if len(dirs) > 10 else ""))
        if files:
            parts.append("files: " + ", ".join(files[:12]) + ("…" if len(files) > 12 else ""))
        return "; ".join(parts)
    man = [k for k in ("package.json", "pyproject.toml", "Cargo.toml") if k in raw]
    bits = []
    if "package.json" in man:
        bits.append("Node project (package.json)")
    if "pyproject.toml" in man:
        bits.append("Python project (pyproject.toml)")
    if "Cargo.toml" in man:
        bits.append("Rust project (Cargo.toml)")
    if bits:
        return "; ".join(bits) + " (root listing not inspected)"
    return "not inspected (metadata/raw pass only)"

def build_run(repo, inv, raw, md):
    cmds = fenced_cmds(md)
    if cmds:
        return "; ".join(cmds)
    ps = pkg_scripts(raw)
    if ps:
        scripts = ps[0] or {}
        pref = [f"npm run {k}" for k in ("test", "check", "start") if k in scripts]
        if pref:
            return "; ".join(pref)
        return f"node main script ({', '.join(list(scripts)[:3]) or 'none'})" if scripts else "no scripts in package.json"
    if "pyproject.toml" in raw:
        m = re.search(r"\[project\.scripts\]([^\[]*)", raw["pyproject.toml"], re.S)
        if m:
            ent = re.findall(r"^(\w+)\s*=", m.group(1), re.M)
            if ent:
                return f"python entry: {', '.join(ent[:3])}"
        return "python package (pyproject.toml)"
    if "Cargo.toml" in raw:
        return "cargo run / cargo test"
    if inv["language"] == "Python":
        return "python <main file> (single-file)"
    if inv["language"] in ("Rust", "C"):
        return "compile then run (single-file)"
    if inv["language"] == "JavaScript":
        return "node <main file> (single-file)"
    return "not determined"

def ci_desc(repo, api):
    wf = (api or {}).get("wf")
    if wf is None:
        return "not inspected"
    if isinstance(wf, list) and wf:
        return f"GitHub Actions: {', '.join(wf[:5])}"
    return "no workflows found"

def entrypoints(repo, inv, raw, md, api):
    eps = []
    cmds = fenced_cmds(md)
    for c in cmds:
        m = re.match(r"(?:node|npx|python3?|\./)\s+(\S+\.(?:mjs|js|py|sh|c|rs))", c)
        if m:
            eps.append(m.group(1))
    ps = pkg_scripts(raw)
    if ps:
        _, main, bin_ = ps
        if main:
            eps.append(str(main))
        if isinstance(bin_, str):
            eps.append(bin_)
        elif isinstance(bin_, dict):
            eps.extend(list(bin_)[:3])
    if "pyproject.toml" in raw:
        m = re.search(r"\[project\.scripts\]\s*\n\s*(\w+)\s*=\s*\"([^\"]+)\"", raw["pyproject.toml"])
        if m:
            eps.append(m.group(2))
    root = (api or {}).get("root") or []
    if not eps:
        for x in root:
            if isinstance(x, dict) and re.match(r"(?i)^(main|index|app|run)\.(py|mjs|js|ts)$", x.get("n", "")):
                eps.append(x["n"])
    return sorted(set(eps))[:4]

# ── curated flagship data (from this crawl's doc reads) ─────────────────────
CURATED = json.load(open(os.path.join(BASE, "curated_flagships.json"), encoding="utf-8"))

def main():
    inv = load_tsv(os.path.join(BASE, "_repos_inventory.tsv"))
    meta = load_meta(os.path.join(BASE, "_repos_meta.tsv"))
    cards, lessons = [], []
    skipped = []
    for repo, r in sorted(inv.items()):
        raw = read_raw(repo)
        api = load_api(repo) if os.path.isdir(os.path.join(API, repo)) else None
        md = readme_text(raw)
        cur = CURATED.get(repo, {})
        docs_read = sorted(raw.keys())
        # purpose
        lines = first_meaningful_lines(md)
        if "purpose" in cur:
            purpose = cur["purpose"]
        elif meta.get(repo, {}).get("desc"):
            purpose = meta[repo]["desc"][:300]
            if lines:
                purpose = purpose + " | " + lines[0][:160]
        elif lines:
            purpose = " | ".join(lines[:2])
        elif meta.get(repo, {}).get("fork"):
            purpose = f"Fork (no README fetched); upstream project mirror, {r['language'] or 'language unknown'}."
        else:
            toks = re.split(r"[-_.]+", repo)
            purpose = f"No README; {r['language'] or 'unknown'} repo, {r['size']}KB — name suggests: {' '.join(t[:40] for t in toks if t)}."
        kind = cur.get("kind") or classify(repo, r, meta, raw)
        lessons_cur = cur.get("lessons", [])
        lessons_auto = []
        for conv in conventions(md):
            lessons_auto.append({"lesson": conv, "source": "README.md"})
        for res in ("RESULTS.md", "LEDGER.md"):
            if res in raw:
                fl = first_meaningful_lines(raw[res], 2)
                for l in fl[:1]:
                    lessons_auto.append({"lesson": l[:220], "source": res})
        # commits as lesson source (tier A only)
        commits = (api or {}).get("commits") or []
        card = {
            "repo": repo,
            "kind": kind,
            "purpose": purpose,
            "setup": {
                "layout": layout_desc(repo, r, raw, api),
                "build_run": build_run(repo, r, raw, md),
                "ci": ci_desc(repo, api),
                "conventions": conventions(md),
                "entrypoints": entrypoints(repo, r, raw, md, api),
            },
            "lessons": [l["lesson"] if isinstance(l, dict) else l for l in (lessons_cur + lessons_auto)][:6],
            "docs_read": docs_read,
            "archived": r["archived"],
        }
        if meta.get(repo, {}).get("fork"):
            card["fork"] = True
        cards.append(card)
        n = 0
        for l in lessons_cur:
            n += 1
            lessons.append({"id": f"{repo}#{n}", "repo": repo, "lesson": l["lesson"], "source": l["source"], "topic": l["topic"]})
        for l in lessons_auto:
            n += 1
            lessons.append({"id": f"{repo}#{n}", "repo": repo, "lesson": l["lesson"], "source": l["source"], "topic": "other"})
    with open(os.path.join(BASE, "cards.jsonl"), "w", encoding="utf-8") as f:
        for c in cards:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    with open(os.path.join(BASE, "lessons.jsonl"), "w", encoding="utf-8") as f:
        for l in lessons:
            f.write(json.dumps(l, ensure_ascii=False) + "\n")
    print(f"cards={len(cards)} lessons={len(lessons)}")

if __name__ == "__main__":
    main()
