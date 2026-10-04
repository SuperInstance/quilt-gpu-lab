#!/usr/bin/env python3
"""GraphQL batch root-listing for repos lacking README.
Usage: graphql_roots.py <repos.txt>   (one repo name per line)
Writes _api/<repo>.root.json for each (same shape as REST contents: [{n,t,s}])."""
import json, os, subprocess, sys, time

BASE = os.path.dirname(os.path.abspath(__file__))
API = os.path.join(BASE, "_api")
BATCH = 60

def run_batch(names):
    parts = []
    for i, n in enumerate(names):
        parts.append(
            f'r{i}: repository(owner: "SuperInstance", name: {json.dumps(n)}) '
            f'{{ object(expression: "HEAD:") {{ ... on Tree {{ entries {{ name type }} }} }} }}'
        )
    q = "query { " + " ".join(parts) + " }"
    for attempt in range(4):
        p = subprocess.run(["gh", "api", "graphql", "-f", f"query={q}"],
                           capture_output=True, text=True, timeout=120)
        if p.returncode == 0:
            return json.loads(p.stdout)
        err = p.stderr.lower()
        if "rate limit" in err or "try again" in err:
            time.sleep(60 * (attempt + 1))
            continue
        sys.stderr.write(f"BATCH ERR: {p.stderr[:300]}\n")
        return None
    return None

def main():
    repos = [l.strip() for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
    os.makedirs(API, exist_ok=True)
    done = 0
    for s in range(0, len(repos), BATCH):
        chunk = repos[s:s + BATCH]
        data = run_batch(chunk)
        if not data or "data" not in data:
            continue
        for i, n in enumerate(chunk):
            node = data["data"].get(f"r{i}")
            if node and node.get("object") and node["object"].get("entries"):
                entries = [{"n": e["name"], "t": e["type"], "s": 0} for e in node["object"]["entries"]]
                with open(os.path.join(API, f"{n}.root.json"), "w", encoding="utf-8") as f:
                    json.dump(entries, f)
                done += 1
        time.sleep(1)
    print(f"graphql_roots done: {done}/{len(repos)}")

if __name__ == "__main__":
    main()
