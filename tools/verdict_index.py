#!/usr/bin/env python3
"""VX-1 verdict->instrument index: compile FW-1's 9-booking census into a machine-readable
index with taint queries (wholesale-void as LOOKUP, not archaeology — quilt-matrix 0cb7552 lesson).

Pre-reg: proposals/runs/VX-1-verdict-index.md (f516092, gates frozen before fire).
Index: receipts/verdict_index.json. G1 completeness / G2 round-trip / G3 negative+tamper / G4 cost.
"""
import json, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INDEX = REPO / "receipts" / "verdict_index.json"
NEG = "vx1_negative_control_field"


def build_index():
    # Source of truth: proposals/runs/FW1-field-write-census-{tranche1,tranche2,tranche3}.md
    # + RESULTS.md tranche bookings + W5B2-REPRO booking (YELLOW -> GREEN-with-caveat upgrade).
    bookings = [
        {"id": "QO10", "status": "GREEN",
         "verdict_reads": ["ladder_arm_auc_means", "ensemble_spread", "g1_anchor_constants_qo3_auc", "cv_gen_only_std0_flags"],
         "write_sites": [{"path": "experiments/qo10_projection_ladder.py", "kind": "internal", "note": "in-script per-arm AUC lists; anchor constants are literals"}],
         "coverage": ["repro verdict-level PASS 2026-10-02 14:4x"]},
        {"id": "QO6", "status": "GREEN",
         "verdict_reads": ["E_final", "E_max", "stop_t", "retracted", "sigma", "delta"],
         "write_sites": [{"path": "tools/eproc.py:eprocess()", "kind": "internal", "note": "log_acc/cumsum, deterministic numpy, no RNG"}],
         "coverage": ["deterministic replicate booking ALL_PASS identical", "sigma-refusal exercised", "retraction arm exercised (late E 581)"],
         "rc1b": "eproc witness() claim=INCREASES arm covered by neither test nor booked run; dead-but-non-gating"},
        {"id": "QC-JEV", "status": "GREEN",
         "verdict_reads": ["p_true_probes", "d_ptrue", "argmax_letter_fixed_content_swap"],
         "write_sites": [{"path": "tools/decision_cell.py", "kind": "internal", "note": "logits path; noul-branch scalar fixed pre-scoring 802bae1"}],
         "coverage": ["repro verdict-level PASS 10:1x (not byte-exact, _latency_ms varies)"]},
        {"id": "D12i", "status": "GREEN",
         "verdict_reads": ["monotonicity_inversions", "partner_id_acc"],
         "write_sites": [{"path": "d12i runner", "kind": "internal", "note": "accs loop + T_floor ladder scan; pure-python random seed 2718, deterministic"}],
         "coverage": ["booked deep-equal repro (ext4 scratch)"]},
        {"id": "W5b2", "status": "GREEN",
         "caveat": "GREEN-with-caveat: single booked draw + REPRO-SOFT cross-corpus second draw (input drift under frozen script); verdict KEEP both, margin far from gates",
         "verdict_reads": ["mean_rel", "wins_final_bpb_pairs", "W5b_machinery_evaluate"],
         "write_sites": [{"path": "W5b machinery (build_corpus/TGRU/ternarize/commit_all/assign_hp/get_batch/evaluate)", "kind": "internal", "note": "arm-reset block internal; assign_hp(antirank) change_count coarseness = booked caveat"}],
         "coverage": ["booked run +8.35% 5/5", "W5B2-REPRO verdict-level +13.83% 4/5 (REPRO-SOFT, cross-corpus)"]},
        {"id": "QG7", "status": "GREEN",
         "caveat": "GREEN with booked ensemble caveat: subpopulation verdicts are 4-seed ensembles, never single draws",
         "verdict_reads": ["auc_fresh_gen1_ensemble4", "auc_frozen_oracle"],
         "write_sites": [{"path": "QG7 training loop", "kind": "internal", "note": "best_state dict write NOT verdict-feeding (verdict uses best_auc scalar)"}],
         "coverage": ["4-seed ensemble booking", "frozen oracle sha-pinned in artifact"],
         "rc1b": "best_state restore path dead-but-not-gating; one-test-pin candidate"},
        {"id": "CI-1", "status": "GREEN",
         "verdict_reads": ["control_ladder_expect_red_observed_red", "ladder_verdict_ok", "alphabet_canary_pin", "workflow_exit_code_empty_glob"],
         "write_sites": [{"path": "tools/canary.py + .github/workflows/tests.yml", "kind": "internal", "note": "ladder IN-MEMORY, writes nothing; reads workflow file + CANON_GATES"}],
         "coverage": ["tests/test_canary.py pins", "negative control verified in booking", "Actions run 37112598464 green"]},
        {"id": "VSB-1", "status": "GREEN",
         "verdict_reads": ["two_method_agreement_flag", "per_path_byte_sizes", "is_vendor_classification", "raw_real_vendored_totals", "positional_name_oid_map"],
         "write_sites": [{"path": "tools/vendor_strip_census.py", "kind": "internal", "note": "census_ls_tree/census_cat_file parsing + batch-check positional name->oid map (verdict-feeding)"}],
         "coverage": ["tests/test_vendor_strip_census.py", "full 3539-file booking run EXACT agreement", "detector branch fired in anger (nested-vendor bug caught)"]},
        {"id": "QG7b", "status": "GREEN",
         "verdict_reads": ["pairwise_spearman_matrix", "spearman_mean", "band_gates_hi09_lo05", "selftest_anchors"],
         "write_sites": [{"path": "tools/ensemble_corr_census.py", "kind": "internal", "note": "_avg_ranks/_pearson/spearman deterministic stdlib, no RNG; runs JSON read-only input"}],
         "coverage": ["selftest() nomask-high + anti branches", "committed verdict-level repro results/qg7b_rerun_correlation/repro-20261003-1215/"]},
    ]
    return {"spec": "VX-1", "prereg": "proposals/runs/VX-1-verdict-index.md",
            "bookings": bookings}


def taint_query(index, term):
    """Return booking ids whose verdict_reads or write-site notes mention `term` (case-insensitive substring)."""
    hits = []
    t = term.lower()
    for b in index["bookings"]:
        hay = " ".join(b["verdict_reads"] + [w.get("note", "") + " " + w["path"] for w in b["write_sites"]]).lower()
        if t in hay:
            hits.append(b["id"])
    return hits


def selftest():
    fails = []
    idx = json.loads(INDEX.read_text())
    t0 = time.time()
    # G1 completeness: exactly the 9 bookings, statuses match FW-1 tranches
    expect = {"QO10": "GREEN", "QO6": "GREEN", "QC-JEV": "GREEN", "D12i": "GREEN",
              "W5b2": "GREEN", "QG7": "GREEN", "CI-1": "GREEN", "VSB-1": "GREEN", "QG7b": "GREEN"}
    got = {b["id"]: b["status"] for b in idx["bookings"]}
    if got != expect:
        fails.append(f"G1 status/scope mismatch: {got}")
    if not any("caveat" in b for b in idx["bookings"] if b["id"] in ("W5b2", "QG7")):
        fails.append("G1 W5b2/QG7 caveat records missing")
    # G2 round-trip: FW-1 lesson-class fields return the bookings FW-1 says rest on them
    rt = [
        ("positional", {"VSB-1"}),          # batch-check name->oid map -> VSB-1 only
        ("e_final", {"QO6"}),               # E trajectory -> QO6
        ("spearman", {"QG7b"}),
        ("partner_id_acc", {"D12i"}),
        ("alphabet_canary", {"CI-1"}),
        ("mean_rel", {"W5b2"}),
        ("auc_fresh_gen1", {"QG7"}),
        ("d_ptrue", {"QC-JEV"}),
        ("ladder_arm_auc", {"QO10"}),
    ]
    for term, want in rt:
        hits = set(taint_query(idx, term))
        if hits != want:
            fails.append(f"G2 taint({term!r}) = {sorted(hits)}, want {sorted(want)}")
    # G3 negative control + tamper
    if taint_query(idx, NEG) != []:
        fails.append("G3 negative control returned non-empty")
    tampered = json.loads(json.dumps(idx))
    tampered["bookings"] = [b for b in tampered["bookings"] if b["id"] != "QO6"]  # drop a booking
    if taint_query(tampered, "e_final") == taint_query(idx, "e_final"):
        # booking removal must change the taint result (index tamper visible to round-trip)
        fails.append("G3 tamper (booking removal) invisible to round-trip diff")
    if {b["id"] for b in tampered["bookings"]} == expect.keys():
        fails.append("G3 tamper copy did not actually change scope")
    # G4 cost: CPU-only; assert wall time < 5 s for selftest
    dt = time.time() - t0
    if dt > 5.0:
        fails.append(f"G4 selftest took {dt:.2f}s > 5s")
    return fails, dt


def main():
    if "--build" in sys.argv:
        INDEX.write_text(json.dumps(build_index(), indent=2) + "\n")
        print(f"built {INDEX}")
        return 0
    fails, dt = selftest()
    print(f"VX-1 selftest: {dt*1000:.0f} ms")
    for f in fails:
        print("FAIL:", f)
    # CLI taint arm
    terms = [a for a in sys.argv[1:] if not a.startswith("--")]
    if terms:
        idx = json.loads(INDEX.read_text())
        for t in terms:
            print(f"taint({t!r}) -> {taint_query(idx, t)}")
    if fails:
        return 1
    print("ALL GATES PASS (G1-G4)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
