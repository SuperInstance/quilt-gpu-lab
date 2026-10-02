#!/usr/bin/env python3
"""COMPOSITE-2 lane verification (r1 retry) — independent re-check of the
prior attempt's booked phase-1 artifacts. Read-only against results/comp2_corpus/.

Checks (no writes to results/, no regeneration of booked files):
  1. corpus.jsonl row count, per-regime counts, canon fracs, dedup uniqueness
  2. corpus sha256-sequence == booked frozen value
  3. per_item_stub.jsonl row count + key set + null prediction fields
  4. F-gate probe RECOMPUTED from the persisted corpus == booked readings
  5. grammar-verbatim receipt (gen_item_c2 vs COMP1 gen_item) re-run
  6. determinism W1 re-run
  7. arms-blocked check: no predictions/, no guard receipts, no comp2/ dir
"""
from __future__ import annotations
import hashlib, json, sys
from collections import Counter
from pathlib import Path

import numpy as np

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
from experiments.comp2_corpus_gate import (  # noqa: E402
    probe_board, verify_verbatim, determinism_receipt, item_key, KINDS,
)
from experiments.comp1_federation2 import y_of  # noqa: E402

OUT = LAB / "results" / "comp2_corpus"
FROZEN_SHA = "5bc6b78f0a4b59481a4e4cc023db743d29bdd9a6db817116332b9e131bf1a3fa"

rep = {"ok": True, "checks": {}}


def chk(name, cond, detail):
    rep["checks"][name] = {"pass": bool(cond), "detail": detail}
    if not cond:
        rep["ok"] = False
    print(("PASS " if cond else "FAIL ") + name + " — " + str(detail))


# 1. load persisted corpus
items = [json.loads(l) for l in (OUT / "corpus.jsonl").read_text().splitlines() if l.strip()]
n = len(items)
kinds = Counter(it["kind"] for it in items)
canon = float(np.mean([y_of(it) for it in items]))
per_canon = {r: round(float(np.mean([y_of(it) for it in items if it["kind"] == r])), 4) for r in KINDS}
uniq = len({it["sha256"] for it in items})
chk("corpus_n_raw_24600", n == 24600, n)
chk("per_regime_6150", all(kinds[r] == 6150 for r in KINDS), dict(kinds))
chk("dedup_exact_unique", uniq == n, f"unique {uniq}/{n}")
chk("canon_frac_near_half", abs(canon - 0.5) <= 0.06, round(canon, 4))
chk("per_regime_canon_near_half", all(abs(v - 0.5) <= 0.06 for v in per_canon.values()), per_canon)

# 2. sha sequence
seq = hashlib.sha256("".join(it["sha256"] for it in items).encode()).hexdigest()
chk("corpus_sha_seq_matches_booked", seq == FROZEN_SHA, seq)

# split by nibble (COMP1/D5 law)
train = [it for it in items if int(it["sha256"][0], 16) < 12]
held = [it for it in items if int(it["sha256"][0], 16) >= 12]
per_held = {r: sum(1 for it in held if it["kind"] == r) for r in KINDS}
chk("heldout_floor_5600", len(held) >= 5600, len(held))
chk("per_regime_heldout_floor_1350", all(v >= 1350 for v in per_held.values()), per_held)

# 3. per_item_stub
stub = [json.loads(l) for l in (OUT / "per_item_stub.jsonl").read_text().splitlines() if l.strip()]
want_keys = {"key", "sha256", "regime", "label", "split", "p", "correct",
             "margin", "routed_sensor", "cell", "la_trigger", "la_flip"}
chk("stub_rows_24600", len(stub) == 24600, len(stub))
chk("stub_keys", all(set(s.keys()) == want_keys for s in stub), "key set uniform")
chk("stub_pred_fields_null", all(s[k] is None for s in stub for k in
    ("p", "correct", "margin", "routed_sensor", "cell", "la_trigger", "la_flip")), "all null")
chk("stub_key_matches_corpus", {s["key"] for s in stub} == {item_key(it) for it in items}, "keys align")

# 4. F-gate RECOMPUTED from persisted corpus
pb = probe_board(train, held)
booked = {"full": 0.7164, "semantic": 0.8611, "counting-address": 0.6545,
          "negation-scope": 0.6288, "agent-role": 0.7187}
chk("probe_full_reproduces", pb["full"] == booked["full"], f'{pb["full"]} vs {booked["full"]}')
chk("probe_per_regime_reproduces",
    all(pb["per_regime"][r] == booked[r] for r in KINDS),
    {r: pb["per_regime"][r] for r in KINDS})
chk("probe_std_gt0", pb["full_std"] > 0, pb["full_std"])
chk("full_in_band", 0.65 <= pb["full"] <= 0.85, pb["full"])
chk("per_regime_in_band", all(0.60 <= v <= 0.90 for v in pb["per_regime"].values()),
    pb["per_regime"])

# 5/6 receipts
v = verify_verbatim()
d = determinism_receipt()
chk("grammar_verbatim", v["verbatim"] and v["mismatches"] == 0, v)
chk("determinism_W1", d["identical"], {"n": d["n"], "sha": d["sha256_of_sequence"]})

# 7. arms blocked
no_preds = not (LAB / "results" / "comp2" / "predictions").exists()
no_guard = not (LAB / "results" / "comp2" / "guard").exists()
chk("arms_blocked_no_predictions", no_preds, "results/comp2/predictions absent")
chk("arms_blocked_no_guard", no_guard, "results/comp2/guard absent")

(PATH := LAB / "scratch" / "comp2_verify_r1.json").write_text(json.dumps(rep, indent=2))
print("\nOVERALL", "OK" if rep["ok"] else "MISMATCH", "->", PATH)
