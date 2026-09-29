#!/usr/bin/env python3
"""propose.py — the deterministic mutation proposer (v0).

Reads the ledger (training/mutations.json) + the gem table (GEMS.md), scores the
candidate pool by  past-outcome similarity x gem-synergy x falsifiability,
suppresses queued duplicates, and emits a ranked, gate-carrying proposal set.

Deterministic: stdlib only, no LLM, no randomness. Same inputs -> same output.
The candidate spec below IS the reasoning; this file only does the arithmetic
and the bookkeeping. See proposals/PROPOSER.md for the full doctrine.
"""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "training" / "mutations.json"
GEMS = ROOT / "GEMS.md"
OUT = ROOT / "proposals" / "proposals-2026-09-28.json"

# ---------------------------------------------------------------- scoring ---

def outcome_base(rec):
    v = (rec.get("verdict") or "").upper()
    if v.startswith("KEEP") or v.startswith("REPLICATED"):
        return 1.0
    if v.startswith("INCONCLUSIVE"):
        return 0.25
    if v.startswith("QUEUED"):
        return 0.0
    if v.startswith("KILL"):
        return 0.5 if rec.get("diagnostic_validated") else -1.0
    return 0.0


def parse_gem_statuses(path):
    """Pull (name, status) pairs out of GEMS.md's wave table rows."""
    statuses = {}
    if not path.exists():
        return statuses
    for line in path.read_text().splitlines():
        m = re.match(r"^\|\s*\d+\s*\|\s*\*\*(.+?)\*\*.*\|\s*([A-Z_]+)\s*\|\s*$", line)
        if m:
            statuses[m.group(1).strip()] = m.group(2).strip()
    return statuses


STATUS_MULT = {"SEEDED": 1.0, "ASSAYED": 0.75, "MINED": 0.6, "FIRED": 0.5}
MISSING_GEM_MULT = 0.5

# ------------------------------------------------------------ the pool ------
# The spec: each candidate is authored (mutation line, receipts it draws on,
# gem links with synergy weights, falsifiability) and reviewed before scoring.
# polarity: +1 builds on the receipt's mechanism, -1 avoids repeating a killed form.

CANDIDATES = [
    # ---------------- bpb / nursery domain ----------------
    {
        "key": "looped_free_delta",
        "domain": "bpb",
        "mutation": "Looped free-delta: one shared transformer block re-entered R=2 (weight-tied) at params matched to the D2/D3 free-delta skeleton — does the −0.029 bpb delta win survive weight sharing?",
        "refs": [{"id": "D2", "polarity": 1}, {"id": "D3", "polarity": 1}],
        "gems": [{"name": "Looped free-delta", "synergy": 0.95}],
        "falsifiability": 0.85,
        "queued_overlap": None,
        "queued_duplicate_of": None,
        "gate": {
            "keep_if": "looped-R2 free-delta beats its param-matched non-looped control by >0.005 bpb AND lands within +0.01 bpb of the D3 free-delta arm (the delta advantage survives weight-sharing)",
            "kill_if": "looped-R2 loses to its own control by >0.005 bpb, OR gives back the delta advantage (>+0.01 vs the D3 arm at matched params)",
            "inconclusive": "between the bands — report both numbers, no verdict inflation",
            "budget": "2 arms x 300s TIME_BUDGET (the D2/D3 speedrun protocol), serialized, GPU-checked",
            "eval": "val_bpb on the pinned val shard, paired arms, seed 42 then 1337 on KEEP"
        },
        "expected_cost": "~2x300s GPU + ~1h build/smoke (loop flag on training/delta_free/train.py); GEMS envelope ~3h GPU",
        "receipts_drawn": "D2 (free-delta KEEP −0.0293), D3 (replication −0.0286 @1337); gem: Looped free-delta (depth-as-loop mine, unfired)",
        "why_now": "The one gem in the pool that is both unfired and rides a hardened KEEP; the composition question (delta x weight-sharing) is open in the literature and cheap to falsify at speedrun budget."
    },
    {
        "key": "ternary_free_delta_full",
        "domain": "bpb",
        "mutation": "Ternary free-delta (full skeleton): BitNet-style BitLinear (ternary {−1,0,+1} weights, absmean scale) on the whole free-delta model — if the delta win survives 1.58-bit weights, that is a multiplier-free LM trained on one 6GB GPU.",
        "refs": [{"id": "D2", "polarity": 1}, {"id": "D3", "polarity": 1}],
        "gems": [{"name": "Ternary free-delta", "synergy": 0.9}],
        "falsifiability": 0.7,
        "queued_overlap": {"id": "D4", "note": "D4 queues ternary weights on the DELTA PATH; this candidate extends ternarization to the whole skeleton. Overlap penalty applied; do not fire before D4's result lands."},
        "queued_duplicate_of": None,
        "gate": {
            "keep_if": "paired delta (ternary-free-delta minus ternary-baseline, both ternarized, same 300s-class budget) <= −0.01 bpb (the delta win survives ternary weights) AND ternary-free-delta <= fp16-free-delta + 0.05 (ternarization cost bounded)",
            "kill_if": "the paired delta advantage inverts under ternary weights (>0), or ternarization costs >0.05 bpb",
            "inconclusive": "delta survives but ternary cost lands between +0.02 and +0.05",
            "budget": "2 ternary arms x 300s + quant smoke; overnight-class envelope per GEMS",
            "eval": "val_bpb paired; weight-bit receipt per layer"
        },
        "expected_cost": "overnight-class (GEMS: 'overnight'); 4 runs if the 1337 replication clause fires",
        "receipts_drawn": "D2/D3 (the win to survive ternarization); qthe lineage KEEP streak (D14/D19/D20 in the pre-today ledger); gem: Ternary free-delta (SEEDED)",
        "why_now": "Biggest-payoff gem in the pool (boat-doctrine endpoint), but it overlaps the queued D4 slot — ranked, gated, and explicitly held until D4 reports."
    },
    {
        "key": "budget_ladder_900s",
        "domain": "bpb",
        "mutation": "Budget ladder: re-run the D2 paired comparison at TIME_BUDGET=900 (3x) — does the −0.029 bpb paired win grow, hold, or shrink with training? (The WECO L1 'sustained trend' condition, tested on our own mutation.)",
        "refs": [{"id": "D2", "polarity": 1}, {"id": "D3", "polarity": 1}],
        "gems": [{"name": "The acceptance-gate harness", "synergy": 0.7}],
        "falsifiability": 0.9,
        "queued_overlap": None,
        "queued_duplicate_of": None,
        "gate": {
            "keep_if": "paired delta @900s <= −0.01 bpb (the free-delta advantage sustains at 3x budget)",
            "kill_if": "paired delta @900s >= −0.002 (the win vanishes at scale — it was a short-budget artifact)",
            "inconclusive": "between −0.002 and −0.01: shrinking but alive; report the curve",
            "budget": "2 arms x 900s = 30 min GPU, serialized",
            "eval": "val_bpb paired, seed 42 (1337 clause on KEEP, same as D3)"
        },
        "expected_cost": "~30 min GPU total (2 x 900s), zero new code (env change only)",
        "receipts_drawn": "D2 (−0.029315 @300s), D3 (−0.028642 @300s/1337); gem: acceptance-gate harness (sustained-trend metrology)",
        "why_now": "Cheapest possible hardening of the fleet's first KEEP, and it manufactures the multi-step-trend evidence an eventual L1 claim needs."
    },
    {
        "key": "delta_head_ratio_sweep",
        "domain": "bpb",
        "mutation": "Delta-head ratio sweep: vary the normal/delta head split (1/3, 3/1; D2's is 2/2) at fixed budget.",
        "refs": [{"id": "D2", "polarity": 1}],
        "gems": [],
        "falsifiability": 0.8,
        "queued_overlap": None,
        "queued_duplicate_of": "D4",
        "gate": {"keep_if": "suppressed — already queued as D4", "kill_if": "-", "budget": "-", "eval": "-"},
        "expected_cost": "-",
        "receipts_drawn": "D3's queue line names this exact mutation",
        "why_now": "NOT reproposed: the queue precedes proposals (discipline 4). Listed to show the suppressor working."
    },
    # ---------------- glyph domain ----------------
    {
        "key": "hard_source_starved_probe",
        "domain": "glyph",
        "mutation": "Hard-source starved probe: train the G4 diff-masked model on life+mandelbrot frames ONLY (drop the 4 easy sources) at equal budget — does hard-dynamic changed-cell accuracy scale once easy statics stop diluting every batch?",
        "refs": [{"id": "G4", "polarity": 1}, {"id": "G2", "polarity": 1}, {"id": "G3", "polarity": 1}],
        "gems": [{"name": "Diff-JEPA", "synergy": 0.9}],
        "falsifiability": 0.85,
        "queued_overlap": None,
        "queued_duplicate_of": None,
        "gate": {
            "keep_if": "changed-cell acc: life >= 39.6% (2x G4's 19.8) OR mandelbrot >= 39.2% (2x G4's 19.6) at the same ~300s budget",
            "kill_if": "both < 1.3x G4 (life < 25.7% AND mandelbrot < 25.5%) — hard dynamics are capacity/tokenization-bound, not data-mix-bound, and the diff-target program should pivot to model capacity, not data weighting",
            "inconclusive": "one source clears 1.3x but neither clears 2x",
            "budget": "1 x ~300s run (G4_LOSS_MASK=1, corpus flag to the two hard sources); no model changes",
            "eval": "changed-cell accuracy per source (the G2/G4 diagnostic axis — the metric the arc actually moves), overall accuracy reported but NOT the gate"
        },
        "expected_cost": "~5 min GPU + a corpus-subset flag in g1_dataset.py",
        "receipts_drawn": "G4 (diff-mask tripled/quadrupled dynamics — diagnostic validated), G2 (hard dynamics 5.6%/7.5% unchanged), G3 (framerate lever falsified — data-mix is the next lever in the same family)",
        "why_now": "The G1→G4 arc isolated the gradient signal as the bottleneck and fixed it; this tests the remaining dilution hypothesis with one cheap run and a crisp 2x threshold. Direct heir of gem #1 (predict differences, not states)."
    },
    {
        "key": "entropy_reweighted_loss",
        "domain": "glyph",
        "mutation": "Entropy-reweighted diff loss: keep all 6 sources but weight the loss 4:1 toward high-CE sources' changed cells (life 1.02, mandelbrot 1.96 nats/cell vs smptebars 0.017) — spend the gradient where the entropy is.",
        "refs": [{"id": "G4", "polarity": 1}, {"id": "G2", "polarity": 1}],
        "gems": [{"name": "Diff-JEPA", "synergy": 0.8}],
        "falsifiability": 0.75,
        "queued_overlap": None,
        "queued_duplicate_of": None,
        "gate": {
            "keep_if": "changed-cell acc: life >= 30% AND mandelbrot >= 28% at full corpus, equal budget",
            "kill_if": "neither source beats G4 by >=2 points",
            "inconclusive": "one clears, one doesn't",
            "budget": "1 x ~300s run (loss-weight vector only)",
            "eval": "changed-cell accuracy per source; CE-per-cell table reported"
        },
        "expected_cost": "~5 min GPU + a 6-vector in the loss",
        "receipts_drawn": "G4 (mask >> reweight, but same mechanism family), G2 (per-source CE table is the weighting map)",
        "why_now": "The soft version of the starved probe: if reweighting works, production keeps statics (hybrid-refiner-friendly) while still teaching dynamics."
    },
    {
        "key": "prev_frame_conditioning_channel",
        "domain": "glyph",
        "mutation": "Explicit persistence-init conditioning: add the previous frame's code as a second input embedding (canvas-style init made explicit) so the diff head conditions on WHAT changed from, not just where.",
        "refs": [{"id": "G4", "polarity": 1}, {"id": "G1", "polarity": 1}],
        "gems": [{"name": "Diff-JEPA", "synergy": 0.7}],
        "falsifiability": 0.6,
        "queued_overlap": {"id": "G5", "note": "touches the hybrid-refiner territory G5 queues; penalty applied; fire only after G5 reports"},
        "queued_duplicate_of": None,
        "gate": {
            "keep_if": "both hard sources >= 25% changed-cell acc (vs G4's 19.8/19.6)",
            "kill_if": "no hard source improves >=1.2x over G4",
            "inconclusive": "between",
            "budget": "1 x ~300s run + small input-path build",
            "eval": "changed-cell accuracy per source"
        },
        "expected_cost": "~5 min GPU + ~2h build (input embedding change, smoke required)",
        "receipts_drawn": "G4 (diff-targets work), G1 (persistence is the free statics baseline)",
        "why_now": "Canvas-mine probe at glyph scale — 'start from persistence, refine' as an input conditioning rather than a decode loop."
    },
    {
        "key": "hybrid_refiner_verbatim",
        "domain": "glyph",
        "mutation": "The hybrid refiner composite: predicted frame = copy-last-frame + diff-head corrections on changed cells.",
        "refs": [{"id": "G4", "polarity": 1}],
        "gems": [],
        "falsifiability": 0.9,
        "queued_overlap": None,
        "queued_duplicate_of": "G5",
        "gate": {"keep_if": "suppressed — already queued as G5 (derived by the G1→G4 arc)", "kill_if": "-", "budget": "-", "eval": "-"},
        "expected_cost": "-",
        "receipts_drawn": "G4's receipt names G5 as the composite",
        "why_now": "NOT reproposed: it is the queue. Listed to show the suppressor working."
    },
]


def main():
    ledger = json.loads(LEDGER.read_text())
    recs = {m["id"]: m for m in ledger["mutations"]}
    gem_status = parse_gem_statuses(GEMS)

    def past_similarity(refs):
        if not refs:
            return 0.0
        total = 0.0
        for r in refs:
            rec = recs.get(r["id"])
            if rec is None:
                raise SystemExit(f"unknown ledger ref: {r['id']}")
            total += outcome_base(rec) * r.get("polarity", 1)
        return total / len(refs)

    def gem_synergy(cand):
        if not cand["gems"]:
            return 0.5  # no gem linkage: neutral-weak
        vals = []
        for g in cand["gems"]:
            st = gem_status.get(g["name"])
            mult = STATUS_MULT.get(st, MISSING_GEM_MULT)
            vals.append(g["synergy"] * mult)
        m = sum(vals) / len(vals)
        if cand.get("queued_overlap"):
            m *= 0.8
        return m

    ranked = {"bpb": [], "glyph": []}
    suppressed = []
    for c in CANDIDATES:
        if c.get("queued_duplicate_of"):
            suppressed.append({
                "key": c["key"], "domain": c["domain"],
                "duplicate_of": c["queued_duplicate_of"],
                "reason": f"already queued as {c['queued_duplicate_of']} in the ledger — the queue precedes proposals",
            })
            continue
        past = past_similarity(c["refs"])
        gem = gem_synergy(c)
        score = past * gem * c["falsifiability"]
        entry = {
            "key": c["key"],
            "domain": c["domain"],
            "mutation": c["mutation"],
            "score": round(score, 4),
            "factors": {"past_outcome_similarity": round(past, 4),
                        "gem_synergy": round(gem, 4),
                        "falsifiability": c["falsifiability"]},
            "gate": c["gate"],
            "expected_cost": c["expected_cost"],
            "receipts_drawn": c["receipts_drawn"],
            "receipt_ledger_refs": [r["id"] for r in c["refs"]],
            "gems": [g["name"] for g in c["gems"]] or None,
            "gem_status_verified": {g["name"]: gem_status.get(g["name"], "NOT_FOUND_IN_GEMS.md") for g in c["gems"]},
            "queued_overlap": c.get("queued_overlap"),
            "why_now": c["why_now"],
        }
        ranked[c["domain"]].append(entry)

    for d in ranked:
        ranked[d].sort(key=lambda e: -e["score"])

    next_ids = {}
    for d, prefix in (("bpb", "D"), ("glyph", "G")):
        nums = [int(m["id"][1:]) for m in ledger["mutations"] if m["domain"] == d]
        next_ids[d] = f"{prefix}{max(nums) + 1}"
    for d in ranked:
        for i, e in enumerate(ranked[d]):
            e["rank"] = i + 1
            e["proposed_id"] = next_ids[d] if i == 0 else None
            e["status"] = "PROPOSED_AWAITING_REVIEW"

    out = {
        "meta": {
            "what": "Ranked self-proposed mutations + pre-registered gates. NOTHING FIRED — proposals wait for human review (acceptance discipline: gate pre-registered, budget capped, ~90% expected rejection is the design).",
            "generated": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "proposer": "propose.py v0 (deterministic; spec: proposals/PROPOSER.md)",
            "inputs": {
                "ledger": str(LEDGER.relative_to(ROOT)),
                "ledger_sha256": hashlib.sha256(LEDGER.read_bytes()).hexdigest(),
                "gems": str(GEMS.relative_to(ROOT)),
                "gems_sha256": hashlib.sha256(GEMS.read_bytes()).hexdigest(),
            },
            "scoring": "score = past_outcome_similarity(refs) x gem_synergy(status-weighted) x falsifiability; KILL-with-validated-diagnostic counts +0.5 (G4); queued duplicates suppressed; queued overlaps penalized 0.8",
            "queue_first": "Ledger QUEUED records fire before any proposal: D4 (delta-head ratio / delta-path ternary), G5 (hybrid refiner). D5/G6 are NEW slots beyond the queue.",
        },
        "proposed": {
            "D": {"next_id": next_ids["bpb"], "ranked": ranked["bpb"]},
            "G": {"next_id": next_ids["glyph"], "ranked": ranked["glyph"]},
        },
        "suppressed_queued_duplicates": suppressed,
        "review_gate": [
            "1. Gates above survive human review UNCHANGED before firing (no post-hoc threshold edits).",
            "2. Budget cap goes in the firing command; the run cannot exceed it.",
            "3. Verdict + receipt append to RESULTS.md and gem-hits.md; mutations.json gets the next record.",
        ],
    }

    OUT.write_text(json.dumps(out, indent=2) + "\n")

    # console report
    print(f"proposer v0 — ledger: {len(recs)} mutations, gems parsed: {len(gem_status)}")
    for d, label in (("bpb", "nursery"), ("glyph", "glyph")):
        print(f"\n== {label} lane (next id {next_ids[d]}) ==")
        for e in ranked[d]:
            star = " <-- PROPOSED" if e["proposed_id"] else ""
            print(f"  #{e['rank']} [{e['score']:.3f}] {e['key']}{star}")
            print(f"      past={e['factors']['past_outcome_similarity']} gem={e['factors']['gem_synergy']} fals={e['factors']['falsifiability']}")
            print(f"      KEEP: {e['gate']['keep_if'][:100]}...")
    print(f"\nsuppressed (queued duplicates): {[s['key'] + '->' + s['duplicate_of'] for s in suppressed]}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
