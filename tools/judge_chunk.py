#!/usr/bin/env python3
"""judge-chunk — chunked batched rule-judge with stimulus-major interleave.

Pattern lifted PROVEN from CM1 round 6 (booked 2026-10-04, receipt
results/cm1/round_006_out.json): a 36-item monolithic judge batch degraded to
pass-rate 0.0 while the SAME items in 3 x 12 stimulus-major chunks scored 0.67
(12-item reference 1.0) — judge-state SIZE is a real failure mode. This tool
makes the chunking recipe grabbable: slice N items into <=k chunks, interleave
round-robin by stimulus so every chunk sees a spread of content (never a
contiguous slab of one group), judge each chunk in ONE batched typesafe
(System One) call with the retry-once / fail-loud pattern, aggregate per-item
gate booleans into pass rates per chunk and overall, and check the r6 cost
bar (sum of chunk walls <= --cost-bar x the monolith-equivalent wall estimate,
default 1.5). One JSON receipt; exit 0 / 1 (cost bar or empty-pass FAIL) /
2 (fail-loud input). Token read at use-time from ~/.config/typesafe/token,
never echoed.

Item format (JSON list):
  [{"id": "c0__S1", "stim": "S1",          # stim groups the interleave
    "report": "...", "draft": "BOOK:..."}, ...]

Gate question per item (jev, noul): "does DRAFT follow RULE for REPORT?"

Usage:
  python tools/judge_chunk.py --items items.json --rule rule.txt \
      [--chunk-size 12] [--model jev-latest] [--cost-bar 1.5] [--out r.json]
  python tools/judge_chunk.py --selftest

Worked example (live 2-item smoke against the real API):
  $ cat > /tmp/jc_items.json <<'EOF'
  [{"id":"a","stim":"s","report":"pantry roof leak, water near feed sacks",
    "draft":"BOOK:farms:high"},
   {"id":"b","stim":"t","report":"guest asks for late checkout at inn",
    "draft":"BOOK:innkeeping:low"}]
  EOF
  $ printf 'RULE: Book REPORTS by domain and urgency.' > /tmp/jc_rule.txt
  $ python tools/judge_chunk.py --items /tmp/jc_items.json \
      --rule /tmp/jc_rule.txt --chunk-size 1
"""
import argparse
import json
import os
import sys
import time
import urllib.request

DEFAULT_ENDPOINT = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-latest"
TOKEN_FILE = os.environ.get(
    "TYPESAFE_TOKEN_FILE", os.path.expanduser("~/.config/typesafe/token"))


def chunk_interleave(items, k):
    """Stimulus-major (CM1-r6 proven structure): interleave items one-at-a-time
    in group round-robin order, then slice consecutive k-sized chunks — each
    chunk sees a spread of stimuli, never a contiguous slab of one stimulus.
    Items without "stim" each form their own group."""
    if k <= 0:
        raise ValueError("chunk-size must be >= 1")
    groups, order = {}, []
    for it in items:
        s = str(it.get("stim", it["id"]))
        if s not in groups:
            groups[s] = []
            order.append(s)
        groups[s].append(it)
    interleaved, gi = [], 0
    while groups:
        s = order[gi % len(order)]
        if s in groups:
            interleaved.append(groups[s].pop(0))
            if not groups[s]:
                del groups[s]
                order.remove(s)
                gi -= 1
        gi += 1
    return [interleaved[i:i + k] for i in range(0, len(interleaved), k)]


def build_state_questions(rule, chunk):
    """One judge batch for a chunk: state = rule + reports+drafts,
    one noul gate question per item."""
    reports = [{"sid": it["id"], "report": it["report"],
                "draft_answer": it["draft"]} for it in chunk]
    state = {"rule": rule, "reports": reports}
    qs = {}
    for it in chunk:
        qs[it["id"] + "_ok"] = {
            "type": "noul",
            "question": "For draft %s (report %s): does the draft answer "
                        "follow the rule?" % (it["id"], it["id"]),
            "instructions": "Answer true only if the draft is exactly what "
                            "the rule yields for that report."}
    return state, qs


def judge_batch(state, questions, model, endpoint, timeout, log=print):
    """One batched call, retry-once, fail-loud. Returns (answers, wall)."""
    with open(TOKEN_FILE) as f:
        tok = f.read().strip()
    payload = {"model": model, "state": state, "questions": questions}
    for attempt in (1, 2):
        t0 = time.time()
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                endpoint, data=data,
                headers={"Authorization": "Bearer " + tok,
                         "Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                resp = json.loads(r.read().decode("utf-8"))
            answers = resp.get("answers")
            if not isinstance(answers, dict):
                raise ValueError("response has no answers object")
            missing = [q for q in questions if q not in answers]
            if missing:
                raise ValueError("batch missing %d answers" % len(missing))
            return answers, round(time.time() - t0, 2)
        except Exception as e:
            if attempt == 2:
                raise RuntimeError("judge-chunk batch failed twice: %r" % e)
            log("retry after: %r" % e)
            time.sleep(2)


def gate_bool(answers, iid):
    v = answers[iid + "_ok"]
    b = v.get("noul", v) if isinstance(v, dict) else v
    if isinstance(b, bool):
        return b
    if isinstance(b, (int, float)):
        return float(b) >= 0.5
    s = str(b).strip().lower()
    if s in ("true", "1"):
        return True
    if s in ("false", "0"):
        return False
    raise ValueError("ungateable answer for %s: %r" % (iid, v))


def run(items, rule, chunk_size, model, endpoint, timeout, cost_bar, log=print):
    if not items:
        raise ValueError("items list is empty")
    seen = set()
    for it in items:
        for f in ("id", "report", "draft"):
            if f not in it or not str(it[f]).strip():
                raise ValueError("item missing/nonempty field %r: %r" % (f, it))
        if it["id"] in seen:
            raise ValueError("duplicate item id %r" % it["id"])
        seen.add(it["id"])
    if not str(rule).strip():
        raise ValueError("rule is empty")
    chunks = chunk_interleave(items, chunk_size)
    gates, walls, chunk_pr = {}, [], []
    for ci, ch in enumerate(chunks):
        state, qs = build_state_questions(rule, ch)
        answers, wall = judge_batch(state, qs, model, endpoint, timeout, log)
        walls.append(wall)
        for it in ch:
            gates[it["id"]] = gate_bool(answers, it["id"])
        chunk_pr.append(round(sum(gates[i["id"]] for i in ch) / len(ch), 4))
        log("chunk %d/%d: %d items, wall %.2fs, pass %.2f"
            % (ci + 1, len(chunks), len(ch), wall, chunk_pr[-1]))
    wall_sum = round(sum(walls), 2)
    # r6 cost bar: estimate monolith wall as the max single-chunk wall
    # (batched calls are ~flat-latency), scaled by the bar.
    est_mono = max(walls)
    cost_ok = wall_sum <= cost_bar * est_mono
    pr = round(sum(gates.values()) / len(gates), 4)
    return {
        "schema": "judge-chunk/1",
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model": model, "n_items": len(items), "n_chunks": len(chunks),
        "chunk_size": chunk_size,
        "pass_rate": pr, "chunk_pass_rates": chunk_pr, "gates": gates,
        "chunk_walls_s": walls, "chunk_wall_sum_s": wall_sum,
        "est_monolith_wall_s": est_mono, "cost_bar": cost_bar,
        "cost_bar_ok": cost_ok,
        "verdict": "KEEP" if (cost_ok and pr > 0.0) else "FAIL",
    }


def selftest():
    """Offline: chunking math + gate parsing + receipt shape. No network."""
    items = [{"id": "i%d" % i, "stim": "s%d" % (i % 3), "report": "r",
              "draft": "d"} for i in range(12)]
    ch = chunk_interleave(items, 4)
    assert len(ch) == 3 and [len(c) for c in ch] == [4, 4, 4], ch
    # stimulus-major: every chunk holds a spread of stims, never a slab
    for c in ch:
        assert len({x["stim"] for x in c}) == 3, c
    assert sorted(x["id"] for c in ch for x in c) == sorted(
        x["id"] for x in items)
    big = chunk_interleave(items, 12)
    assert len(big) == 1 and len(big[0]) == 12
    assert chunk_interleave(items[:1], 4)[0][0]["id"] == "i0"
    # huge single stimulus group still splits by k (slab is unavoidable there)
    slab = chunk_interleave(
        [{"id": "x%d" % i, "stim": "only", "report": "r", "draft": "d"}
         for i in range(10)], 4)
    assert [len(c) for c in slab] == [4, 4, 2], slab
    for bad in (0, -1):
        try:
            chunk_interleave(items, bad)
            raise SystemExit("selftest FAIL: k=%d accepted" % bad)
        except ValueError:
            pass
    assert gate_bool({"x_ok": {"noul": True}}, "x") is True
    assert gate_bool({"x_ok": {"noul": 0.7}}, "x") is True
    assert gate_bool({"x_ok": {"noul": "false"}}, "x") is False
    try:
        gate_bool({"x_ok": {"noul": "maybe"}}, "x")
        raise SystemExit("selftest FAIL: junk answer accepted")
    except ValueError:
        pass
    for bad_items in ([], [{"id": "", "report": "r", "draft": "d"}],
                      [{"id": "a", "report": "r", "draft": "d"},
                       {"id": "a", "report": "r", "draft": "d"}]):
        try:
            run(bad_items, "rule", 4, "m", "http://x", 1, 1.5)
            raise SystemExit("selftest FAIL: bad items accepted %r" % bad_items)
        except ValueError:
            pass
    st, qs = build_state_questions("R", items[:2])
    assert qs == {"i0_ok": qs["i0_ok"], "i1_ok": qs["i1_ok"]}
    print("selftest OK: chunking, gate parsing, fail-loud inputs, "
          "state/questions shape")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="Chunked batched rule-judge with stimulus-major "
                    "interleave. See module docstring.")
    ap.add_argument("--items", help="items JSON list")
    ap.add_argument("--rule", help="rule text file (or use --rule-str)")
    ap.add_argument("--rule-str", help="rule text inline")
    ap.add_argument("--chunk-size", type=int, default=12)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--cost-bar", type=float, default=1.5)
    ap.add_argument("--out", help="write receipt JSON here (default stdout)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    try:
        if not a.items or not (a.rule or a.rule_str):
            ap.error("--items and (--rule|--rule-str) are required")
        with open(a.items) as f:
            items = json.load(f)
        if not isinstance(items, list):
            raise ValueError("items file must be a JSON list")
        rule = a.rule_str if a.rule_str else open(a.rule).read()
        receipt = run(items, rule, a.chunk_size, a.model, a.endpoint,
                      a.timeout, a.cost_bar)
        out = json.dumps(receipt, indent=1)
        if a.out:
            with open(a.out, "w") as f:
                f.write(out + "\n")
            print("receipt -> %s" % a.out)
        else:
            print(out)
        sys.exit(0 if receipt["verdict"] == "KEEP" else 1)
    except Exception as e:
        print("FAIL-INPUT: %r" % e, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
