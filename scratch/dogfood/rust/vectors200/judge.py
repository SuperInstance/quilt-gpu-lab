#!/usr/bin/env python3
"""Judge the granite 200-vector batch with the canonical Z[omega] reference.

Parses reply_<k>.txt lines of the form:
  i add:A B mul:A B conj:A B norm:N
Reports per-op accuracy. Any vector line that fails to parse counts as wrong
for every op on that vector.  Independent recomputation (never trust the model).
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import canonical_ref as ref  # noqa: E402

LINE = re.compile(
    r"^\s*(\d+)\s+add:\s*(-?\d+)\s+(-?\d+)\s+"
    r"mul:\s*(-?\d+)\s+(-?\d+)\s+"
    r"conj:\s*(-?\d+)\s+(-?\d+)\s+"
    r"norm:\s*(-?\d+)")
OPS = ["add", "mul", "conj", "norm"]


def main():
    vecs = {v["i"]: v for v in json.loads((HERE / "vectors.json").read_text())}
    parsed = {}
    raw_lines = 0
    cands = [q for q in HERE.glob("reply_*.txt")
             if not q.name.endswith("reasoning.txt")]
    for p in sorted(cands, key=lambda q: int(q.stem.split("_")[1])):
        for ln in p.read_text().splitlines():
            if not ln.strip():
                continue
            raw_lines += 1
            m = LINE.match(ln)
            if m:
                g = [int(x) for x in m.groups()]
                parsed[g[0]] = {
                    "add": (g[1], g[2]), "mul": (g[3], g[4]),
                    "conj": (g[5], g[6]), "norm": g[7]}
    ok = {op: 0 for op in OPS}
    miss = {op: [] for op in OPS}
    n_parsed = 0
    for i, v in vecs.items():
        a, b = v["z"]
        c, d = v["w"]
        want = {
            "add": ref.add((a, b), (c, d)),
            "mul": ref.mul((a, b), (c, d)),
            "conj": ref.conj((a, b)),
            "norm": ref.norm((a, b)),
        }
        got = parsed.get(i)
        if got is not None:
            n_parsed += 1
        for op in OPS:
            g = None if got is None else got[op]
            if g == want[op]:
                ok[op] += 1
            else:
                miss[op].append({"i": i, "z": [a, b], "w": [c, d],
                                 "got": g, "want": list(want[op]) if op != "norm" else want[op]})
    n = len(vecs)
    out = {
        "vectors": n, "lines_seen": raw_lines, "vectors_parsed": n_parsed,
        "per_op": {op: {"correct": ok[op], "of": n,
                        "pct": round(100.0 * ok[op] / n, 1)} for op in OPS},
        "all_four_correct": sum(1 for i in vecs if all(
            (parsed.get(i) or {}).get(op) == (
                ref.add((vecs[i]["z"][0], vecs[i]["z"][1]), (vecs[i]["w"][0], vecs[i]["w"][1]))
                if op == "add" else
                ref.mul((vecs[i]["z"][0], vecs[i]["z"][1]), (vecs[i]["w"][0], vecs[i]["w"][1]))
                if op == "mul" else
                ref.conj((vecs[i]["z"][0], vecs[i]["z"][1]))
                if op == "conj" else
                ref.norm((vecs[i]["z"][0], vecs[i]["z"][1])))
            for op in OPS)),
        "misses": miss,
    }
    (HERE / "judge_result.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in
                      ("vectors", "lines_seen", "vectors_parsed", "per_op",
                       "all_four_correct")}, indent=1))
    for op in OPS:
        print(f"  {op}: {ok[op]}/{n} = {out['per_op'][op]['pct']}%")


if __name__ == "__main__":
    main()
