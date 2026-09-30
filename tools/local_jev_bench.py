#!/usr/bin/env python3
"""Local judgment-cell bench: can a small local model serve as a zero-cost Jev cell?

Probes (all CPU by default, num_gpu 0, temperature 0):
  1. yes/no graded accuracy   — 16 deterministic arithmetic/logic items with ground truth
  2. determinism              — same 8 prompts x3 runs, exact-match rate
  3. JSON instruction-follow  — 8 items asking for {"verdict","confidence"}; raw parse rate
  4. choice accuracy          — 8 four-way items (A-D)
  5. rubric score calibration — 4 items with obvious 1-5 anchors (tolerance +/-1)
  6. tok/s                    — mean eval_count / eval_duration across all calls

Usage:
  python tools/local_jev_bench.py --model tev1:0.8b
  python tools/local_jev_bench.py --model tev1:4b --gpu
Output: results/local_jev_bench/<model-sanitized>/results.json (+ stdout summary)
"""
import argparse
import json
import re
import time
import urllib.request
from pathlib import Path

OLLAMA = "http://127.0.0.1:11434/api/chat"
RNG_SEED = 20260930


def call(model, prompt, gpu=False, num_predict=96):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0, "num_predict": num_predict}
        + ([] if gpu else [{"num_gpu": 0}]),
    }
    req = urllib.request.Request(
        OLLAMA, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read().decode())
    dt = time.time() - t0
    tok_s = data.get("eval_count", 0) / (data.get("eval_duration", 1) / 1e9)
    return data["message"]["content"], dt, tok_s


def yn_items():
    """16 deterministic yes/no items: is the arithmetic claim true?"""
    out, s = [], RNG_SEED
    for i in range(16):
        s = (s * 1103515245 + 12345) % (2**31)
        a, b = s % 89 + 3, (s // 97) % 89 + 3
        claim_gt = (a + b) > (a * 2 if i % 2 else b + 1)  # mix easy/hard-ish comparisons
        claim = f"{a} + {b} > {a*2 if i%2 else b+1}"
        out.append({"q": f"Is this claim true? {claim}. Answer with exactly Yes or No, nothing else.",
                    "truth": "Yes" if claim_gt else "No"})
    return out


def choice_items():
    out = []
    for i, (q, ans) in enumerate([
        ("What is 7 x 6?", "D: 42 | A: 36 | B: 42 | C: 48"),  # keep simple, unique right
        ("Which is largest? A: 0.5  B: 0.05  C: 5  D: 0.005", "C"),
        ("Capital of Japan? A: Osaka  B: Tokyo  C: Kyoto  D: Sapporo", "B"),
        ("10 - 3 + 2 = ? A: 5  B: 8  C: 9  D: 12", "C"),
        ("Which is a prime? A: 9  B: 15  C: 17  D: 21", "C"),
        ("Half of 90? A: 30  B: 40  C: 45  D: 50", "C"),
        ("Opposite of 'arrive'? A: depart  B: stay  C: wait  D: return", "A"),
        ("5! = ? A: 25  B: 60  C: 120  D: 720", "C"),
    ]):
        out.append({"q": f"{q}\nAnswer with exactly one letter: A, B, C, or D.", "truth": ans.split(":")[0].strip()})
    return out


def first_word(text):
    m = re.search(r"\b(yes|no)\b", text, re.I)
    return m.group(1).capitalize() if m else None


def letter_of(text):
    m = re.search(r"\b([ABCD])\b", text, re.I)
    return m.group(1).upper() if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--gpu", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows, tok_samples = [], []
    r = {"model": args.model, "gpu": args.gpu, "seed": RNG_SEED, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z")}

    # 1. yes/no accuracy
    yn = yn_items()
    ok = 0
    for it in yn:
        txt, dt, ts = call(args.model, it["q"], args.gpu)
        tok_samples.append(ts)
        got = first_word(txt)
        ok += got == it["truth"]
        rows.append({"probe": "yn", "truth": it["truth"], "got": got, "raw": txt[:80]})
    r["yn_accuracy"] = round(ok / len(yn), 4)

    # 2. determinism (8 prompts x3)
    det_ok, det_n = 0, 0
    for it in yn[:8]:
        outs = []
        for _ in range(3):
            txt, dt, ts = call(args.model, it["q"], args.gpu)
            outs.append(txt.strip())
            tok_samples.append(ts)
        det_ok += len(set(outs)) == 1
        det_n += 1
    r["determinism_exact_rate"] = round(det_ok / det_n, 4)

    # 3. JSON instruction-following
    jok = 0
    for it in yn[:8]:
        p = it["q"] + '\n Reply ONLY with JSON: {"verdict": "yes" or "no", "confidence": a number 0 to 1}'
        txt, dt, ts = call(args.model, p, args.gpu)
        tok_samples.append(ts)
        try:
            m = re.search(r"\{.*\}", txt, re.S)
            json.loads(m.group(0))
            jok += 1
        except Exception:
            pass
    r["json_parse_rate"] = round(jok / 8, 4)

    # 4. choice
    ch = choice_items()
    cok = 0
    for it in ch:
        txt, dt, ts = call(args.model, it["q"], args.gpu)
        tok_samples.append(ts)
        cok += letter_of(txt) == it["truth"]
    r["choice_accuracy"] = round(cok / len(ch), 4)

    # 5. rubric score calibration (obvious anchors)
    score_items = [
        ("The statement '2 + 2 = 4'. Rate its correctness 1-5.", 5),
        ("The statement '2 + 2 = 5'. Rate its correctness 1-5.", 1),
        ("The statement 'Paris is the capital of France'. Rate correctness 1-5.", 5),
        ("The statement 'The sun rises in the west'. Rate correctness 1-5.", 1),
    ]
    sok = 0
    for p, anchor in score_items:
        txt, dt, ts = call(args.model, p + " Answer with one digit.", args.gpu)
        tok_samples.append(ts)
        m = re.search(r"[1-5]", txt)
        if m and abs(int(m.group(0)) - anchor) <= 1:
            sok += 1
    r["score_within1_rate"] = round(sok / len(score_items), 4)

    r["tok_s_mean"] = round(sum(tok_samples) / len(tok_samples), 1)
    r["calls"] = len(tok_samples)
    r["rows"] = rows

    out = Path(args.out) if args.out else Path(
        f"results/local_jev_bench/{args.model.replace(':','_').replace('/','_')}/results.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(r, indent=2))

    print(f"== {args.model} ({'GPU' if args.gpu else 'CPU'}) ==")
    print(f"yes/no accuracy : {r['yn_accuracy']}")
    print(f"determinism     : {r['determinism_exact_rate']}")
    print(f"json parse rate : {r['json_parse_rate']}")
    print(f"choice accuracy : {r['choice_accuracy']}")
    print(f"score within+-1 : {r['score_within1_rate']}")
    print(f"tok/s           : {r['tok_s_mean']}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
