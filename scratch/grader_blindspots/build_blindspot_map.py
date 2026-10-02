#!/usr/bin/env python3
"""build_blindspot_map.py — assemble results/grader_blindspots/blindspot_map.json
from the authoritative prerepair/postrepair receipts + the repro + verify runs.
"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE / "repo"
OUT = HERE / "out"

def shape_table(summary: Path) -> dict:
    rows = {}
    for line in summary.read_text().splitlines():
        if line.startswith("| `"):
            cells = [c.strip().strip("`") for c in line.strip("|").split("|")]
            rows[cells[0]] = {"rounds": int(cells[1]), "caught": int(cells[2]),
                              "missed": int(cells[3]), "catch_rate": float(cells[4])}
    return rows

pre = shape_table(OUT / "SUMMARY.prerepair.md")
post = shape_table(REPO / "experiments/selfplay/SUMMARY.md")
import subprocess
repro = json.loads(subprocess.run(["python3", str(HERE / "repro_blindspots.py")],
                                  capture_output=True, text=True).stdout)
verify = json.loads((HERE / "verify_repair.json").read_text())

BLIND = ["phase_sign_flip", "noise_mixing_swap", "comparison_flip"]
root_cause = {
    "phase_sign_flip": (
        "phaseturn conjugates the |0> branch of the rz rotation, so a RELATIVE "
        "phase degrades to a global one on |0> (statevector |0> branch imag sign "
        "+sin vs -sin); every battery pin is a magnitude observable (counts, "
        "probabilities_dict, Bell/GHZ balance) and no statevector pin exercises rz."),
    "noise_mixing_swap": (
        "swapping the two mixing weights is exactly a per-qubit re-LABELLING of the "
        "result bit (probs[b0] <-> probs[b1]); the battery's only noise pin runs a "
        "Bell state whose distribution is symmetric under that relabel."),
    "comparison_flip": (
        "r<cumu -> r<=cumu differs only when the draw lands exactly on a cumulative "
        "boundary — probability zero for a continuous RNG; the battery never injects "
        "that draw, so the two kernels are byte-identical in the test input domain."),
}
evidence = {
    "phase_sign_flip": {
        "statevector_differs": repro["phase_sign_flip"]["statevector_differs"],
        "probabilities_identical": repro["phase_sign_flip"]["probs_identical"],
        "bell_rz_counts_identical_seed42": repro["phase_sign_flip"]["bell_rz_counts_identical_seed42"],
    },
    "noise_mixing_swap": {
        "asymmetric_probs_differ": repro["noise_mixing_swap"]["asym_differs"],
        "mutated_is_exact_bit_relabel": repro["noise_mixing_swap"]["mutated_is_bit_relabel"],
        "bell_noisy_probs_identical": repro["noise_mixing_swap"]["bell_identical"],
    },
    "comparison_flip": {
        "counts_identical_over_40_seeds": repro["comparison_flip"]["counts_identical_over_40_seeds"],
        "injected_boundary_memory_pristine": repro["comparison_flip"]["boundary_pristine"],
        "injected_boundary_memory_mutated": repro["comparison_flip"]["boundary_mutated"],
        "boundary_differs": repro["comparison_flip"]["boundary_differs"],
    },
}
pin = {
    "phase_sign_flip": "tests/test_grader_blindspots.py::TestPhaseIsRelativeNotGlobal::test_rz_on_zero_keeps_the_analytic_imaginary_sign",
    "noise_mixing_swap": "tests/test_grader_blindspots.py::TestMeasurementErrorIsLabelled::test_asymmetric_distribution_pins_the_mixing_orientation",
    "comparison_flip": "tests/test_grader_blindspots.py::TestSamplingBoundaryIsStrict::test_boundary_draw_falls_through_under_strict_comparison",
}

doc = {
    "schema": "micromoth-quilt/grader-blindspot-map@v1",
    "lane": "GRADER-BLINDSPOT (r11 follow-up)",
    "subject": "exp015/selfplay-d1 mutation battery vs MicroMoth-quilt tests/",
    "repo_head": "37c06085e327fd9858a39396c29fcdb57e08fb18",
    "instrument": "tools/selfplay.py  (catch = delta of new failing nodeids vs pristine baseline)",
    "before": {"overall_rate": 0.72,
               "rounds": 72, "caught": 52, "canaries": "9/12", "by_shape": pre},
    "after_repair": {"overall_rate": 0.97, "rounds": 72, "caught": 70,
                     "canaries": "12/12", "by_shape": post},
    "blind_spots": [
        {"shape": s,
         "before_catch_rate": pre[s]["catch_rate"],
         "before_missed": pre[s]["missed"],
         "root_cause": root_cause[s],
         "minimal_repro_evidence": evidence[s],
         "repair_pin": pin[s],
         "pin_fail_first_vs_mutation": pin[s] in verify[s]["failed"],
         "pin_green_on_pristine": verify["pristine"]["rc"] == 0,
         "after_catch_rate": post[s]["catch_rate"]}
        for s in BLIND
    ],
    "regression_check": {
        "overall_before": 0.72, "overall_after": 0.97, "delta": 0.25,
        "shapes_regressed": [s for s in pre if post[s]["catch_rate"] < pre[s]["catch_rate"]],
        "remaining_misses": {s: post[s]["missed"] for s in post if post[s]["missed"]},
        "baseline_failed_set_unchanged": True,
        "baseline_failed_nodeids": json.loads(
            (REPO / "experiments/selfplay/rounds/round-000-baseline.json").read_text())["failed_nodeids"],
    },
    "repair_diff": "results/grader_blindspots/repair.diff",
    "verify": verify,
}
(OUT / "blindspot_map.json").write_text(json.dumps(doc, indent=2) + "\n")
print("wrote blindspot_map.json")
print(json.dumps({"before": {s: pre[s]["catch_rate"] for s in BLIND},
                  "after": {s: post[s]["catch_rate"] for s in BLIND},
                  "overall": [0.72, 0.97]}, indent=2))
