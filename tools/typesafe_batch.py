#!/usr/bin/env python3
"""typesafe-batch — standalone CLI for batched typesafe (System One) judge calls.

Wraps the proven batched rule-rich judge pattern (experiments/cm1_relay_r4.py,
r5.py): ONE HTTP call carries state + a dict of named questions and returns
all answers at once (~flat latency up to 80 questions). Retry-once with a
short backoff; fail-loud with the real error, never a silent partial.

Usage:
  python tools/typesafe_batch.py --state state.json --questions questions.json
  python tools/typesafe_batch.py --state state.json --questions q.json \
      --model jev-latest --out answers.json

Input formats (JSON):
  state.json     : string OR object (passed through verbatim as "state")
  questions.json : {"qname": {"type": "noul", "question": "...",
                              "instructions": "..."}, ...}
                   (or a bare list of strings -> auto-wrapped as noul
                    questions keyed q0..qn)

Output: the raw API response JSON (with "answers"), plus "_wall_s", written
to stdout or --out file. Exit code 0 on success, 1 on failure (reason on stderr).

Auth: bearer token read at use-time from ~/.config/typesafe/token (override
with TYPESAFE_TOKEN_FILE env). Keys are never echoed.

Worked example (2-question smoke against the real API):
  $ cat > /tmp/tb_state.json <<'EOF'
  "RULE: Book REPORTS by domain and urgency.\nReport: pantry roof leak, water near feed sacks."
  EOF
  $ cat > /tmp/tb_q.json <<'EOF'
  {"domain_ok": {"type": "noul", "question": "Is DOMAIN 'farms' correct?",
                 "instructions": "Answer true only if the rule yields 'farms'."},
   "urgency_ok": {"type": "noul", "question": "Is URGENCY 'high' correct?",
                 "instructions": "Answer true only if the rule yields 'high'."}}
  EOF
  $ python tools/typesafe_batch.py --state /tmp/tb_state.json \
      --questions /tmp/tb_q.json
"""
import argparse
import json
import os
import sys
import time
import urllib.request

DEFAULT_ENDPOINT = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-preview"
TOKEN_FILE = os.environ.get(
    "TYPESAFE_TOKEN_FILE", os.path.expanduser("~/.config/typesafe/token"))


def post_json(url, payload, headers, timeout):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def load_questions(path):
    with open(path) as f:
        qs = json.load(f)
    if isinstance(qs, list):
        out = {}
        for i, q in enumerate(qs):
            out["q%d" % i] = (q if isinstance(q, dict)
                              else {"type": "noul", "question": str(q)})
        return out
    if not isinstance(qs, dict) or not qs:
        raise ValueError("questions must be a non-empty object or list")
    return qs


def tsafe_batch(state, questions, model=DEFAULT_MODEL,
                endpoint=DEFAULT_ENDPOINT, timeout=90, log=print):
    """One batched call. Returns full response dict + _wall_s. Retry once."""
    with open(TOKEN_FILE) as f:
        tok = f.read().strip()
    payload = {"model": model, "state": state, "questions": questions}
    for attempt in (1, 2):
        t0 = time.time()
        try:
            r = post_json(endpoint, payload,
                          {"Authorization": "Bearer " + tok,
                           "Content-Type": "application/json"}, timeout)
            answers = r.get("answers")
            if not isinstance(answers, dict):
                raise ValueError("response has no answers object")
            missing = [k for k in questions if k not in answers]
            if missing:
                raise ValueError("batch missing %d answers: %s"
                                 % (len(missing), missing[:3]))
            r["_wall_s"] = round(time.time() - t0, 2)
            return r
        except Exception as e:
            if attempt == 2:
                raise RuntimeError("typesafe-batch failed twice: %r" % e)
            log("retry after: %r" % e)
            time.sleep(2)


def main():
    ap = argparse.ArgumentParser(
        description="Batched typesafe/System One judge: state + questions -> "
                    "answers in ONE call. See module docstring for formats.")
    ap.add_argument("--state", required=True,
                    help="path to state JSON (string or object)")
    ap.add_argument("--questions", required=True,
                    help="path to questions JSON (dict of named questions, "
                         "or list auto-keyed q0..qn)")
    ap.add_argument("--model", default=DEFAULT_MODEL,
                    help="teacher model (default: %(default)s; "
                         "also jev-latest)")
    ap.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--out", help="write response JSON here (default stdout)")
    a = ap.parse_args()

    try:
        with open(a.state) as f:
            state = json.load(f)
        questions = load_questions(a.questions)
    except Exception as e:
        print("typesafe-batch: input error: %r" % e, file=sys.stderr)
        return 1
    try:
        r = tsafe_batch(state, questions, model=a.model,
                        endpoint=a.endpoint, timeout=a.timeout)
    except Exception as e:
        print("typesafe-batch: FAIL: %r" % e, file=sys.stderr)
        return 1
    out = json.dumps(r, indent=2)
    if a.out:
        with open(a.out, "w") as f:
            f.write(out + "\n")
        print("wrote %s (%d answers, %ss)"
              % (a.out, len(r["answers"]), r["_wall_s"]))
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
