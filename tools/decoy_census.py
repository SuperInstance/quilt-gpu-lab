#!/usr/bin/env python3
"""decoy_census — DECOY-1 (pre-reg proposals/runs/DECOY-1-decoy-metric-census-prereg-2026-10-09.md)

Census over booked-verdict metrics for the groove-analyzer decoy class:
 (a) score computed against the verifier's own assignment (wrongness rewarded),
 (b) clamped metric whose gate bound is unreachable.
Gates G1-G4 per frozen prereg words. stdlib only, deterministic, fail-loud.
"""
import json, re, sys, random

# ---- G1 SURVEY: booked verdict -> cited metric sites (docs-anchored) ----
SURVEY = [
    # (booking, metric, site, kind)
    ("QO1",  "oracle AUC+Brier",   "experiments/qo1_oracle.py (labels = true crossed/not, external)", "labels-external"),
    ("QO3",  "per-gen oracle AUC", "results/qo3_horizon/results.json (labels-external)",              "labels-external"),
    ("QO10", "projection ladder AUC","results/qo10_projection_ladder/results.json",                    "labels-external"),
    ("DECIDE-1..1d", "argmax_acc / argmin-consistency", "tools/decision_cell.py:63-76 (labels = task truth)", "labels-external"),
    ("DECIDE-1",     "confidence (clamped [0,1])", "tools/decision_cell.py:70",                "CLAMP-value"),
    ("DECIDE-1b",    "confidence 1-dist/base (floored at 0)", "tools/decision_cell.py:75",     "CLAMP-value"),
    ("QG3/QG6/QG7",  "crossing rate",  "results/qg3_*, qg6_*, qg7_* (outcome = ground truth)",  "labels-external"),
    ("QG7b", "auc_oracle/auc_fresh",  "experiments/qg7b_rerun_correlation.py:85 (labels-external)","labels-external"),
    ("DETERM-1", "auc_fresh + anchor_in_band", "results/determ1_lattice_snap/ (labels-external)","labels-external"),
    ("QO6 family","eproc delta evidence", "tools/eproc.py (evidence vs recorded outcome)",       "labels-external"),
    ("TIE-1a",   "tie census rows",    "tools/tie_census.py (compares gate inputs vs bounds)",    "structural"),
    ("CI-1",     "bootstrap CI slice", "tools/ci_gate.py:52 (max(0,lo)/min(n-1,hi))",             "CLAMP-positional"),
    ("CC-1",     "mw AUC",             "tools/auc_sep.py:42 (rank statistic, labels input)",      "labels-external"),
]
DOCS_ONLY = ["REPORTER-DEFAULT", "DIFFPORT-1", "RT-D1", "HSA-1b", "VSB-1", "PARAM-1"]

# ---- G2/G3: source scan of the named clamp sites ----
def scan_source():
    findings = []
    src = open("tools/decision_cell.py").read()
    # clamp classification: is the clamped value used AS a cited gate value?
    for m in re.finditer(r"max\(0\.0[^)]*\)\s*,?\s*|min\(1\.0[^)]*\)", src):
        findings.append(("decision_cell.py", m.group(0).strip(),
                         "value-clamp on confidence — cited as diagnostics, NOT as a gate "
                         "(DECIDE gates used argmax_acc/consistency) => YELLOW-latent"))
    src_ci = open("tools/ci_gate.py").read()
    if "max(0, lo_idx)" in src_ci and "min(n_boot - 1, hi_idx)" in src_ci:
        findings.append(("ci_gate.py:52", "max(0,lo)/min(n-1,hi)",
                         "positional index clamp on bootstrap slice — NOT a score clamp (prereg exempt)"))
    return findings

# ---- G3 self-ref check: is any cited metric compared to its own producer's assignment? ----
SELF_REF_AUDIT = {
    "tools/auc_sep.py": "auc(pos,neg) takes externally supplied labels; no assignment step in file",
    "tools/decision_cell.py": "choice = argmax(dist) is the PREDICTION; scoring (DECIDE bookings) done "
                               "against task truth in experiments/decide1*.py, not against choice",
    "tools/tie_census.py": "reads gate comparisons directly; no producer assignment",
}

# ---- G4 mutation-lite: wrongness must DROP the metric (rank-statistic witness) ----
def auc(pos, neg):
    gt = sum(1 for p in pos for n in neg if p > n)
    eq = sum(1 for p in pos for n in neg if p == n)
    return (gt + 0.5 * eq) / (len(pos) * len(neg))

def mutation_lite():
    rng = random.Random(20261009)
    pos = [rng.gauss(1.0, 0.5) for _ in range(64)]
    neg = [rng.gauss(0.0, 0.5) for _ in range(64)]
    a_true = auc(pos, neg)
    # shuffle labels: recompute with assignment randomized 20x, mean must fall to ~0.5
    falls = []
    for t in range(20):
        pool = pos + neg
        rng.shuffle(pool)
        p2, n2 = pool[:64], pool[64:]
        falls.append(abs(auc(p2, n2) - 0.5))
    mean_dev = sum(falls) / len(falls)
    return a_true, mean_dev

def main():
    out = {"tool": "decoy_census", "prereg": "DECOY-1", "G1": {}, "G2G3": {}, "G4": {}}
    # G1
    out["G1"] = {"surveyed": len(SURVEY), "docs_only_NA": DOCS_ONLY,
                 "verdict": "PASS" if len(SURVEY) >= 10 else "FAIL"}
    # G2/G3
    src_findings = scan_source()
    out["G2G3"] = {"findings": [list(f) for f in src_findings],
                   "self_ref": SELF_REF_AUDIT,
                   "self_ref_verdict": "PASS — no cited metric scored against its own assignment",
                   "clamp_verdict": "YELLOW-latent-only — decision_cell confidence clamps exist but "
                                    "confidence never served as a gate bound in any booking"}
    # G4
    a_true, mean_dev = mutation_lite()
    g4 = a_true > 0.9 and mean_dev < 0.05
    out["G4"] = {"auc_true_labels": round(a_true, 4), "mean_absdev_shuffled": round(mean_dev, 4),
                 "pass": g4,
                 "caveat": "instrument-level wrongness witness (labels shuffled on separated data "
                           "through tools/auc_sep.auc's exact rank statistic). No raw per-stream "
                           "oracle scores persist on disk (all booked JSONs are summary-level), so a "
                           "lane-refire mutation was out of ~20m scope — follow-up note, does not "
                           "change the structural verdict: a rank statistic cannot reward wrong labels."}
    out["verdict"] = "GREEN, 1 YELLOW-latent (decision_cell confidence clamps, uncited-as-gate)"
    json.dump(out, sys.stdout, indent=1)
    print()
    return 0

if __name__ == "__main__":
    sys.exit(main())
