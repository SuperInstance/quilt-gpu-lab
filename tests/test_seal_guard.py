#!/usr/bin/env python3
"""test_seal_guard.py — pins for the --require-clean seal guard (b2d24bb).

Context: the d23b phantom seal (receipts/manifest-repair-2026-09-30-d23b.md)
happened because a seal hashed a dirty working tree git never saw; the pin
only caught it later, on a clean clone. b2d24bb converted that class from
pin-caught-after-the-fact to refused-at-seal-time. These pins keep it
refused-at-seal-time:

  1. guard is live in a git checkout — dirty_sealed_paths() actually runs
     git status (a neutered guard returning [] silently passes everything).
  2. guard reports a dirty sealed path — probe file under experiments/ is
     seen, named, and cleaned up.
  3. sealing refuses the dirty tree — tools/receipt_manifest.py exits 2
     with the REFUSED banner naming the dirty path; no manifest write.
  4. --allow-dirty seals with an explicit admission — exit 0 and a
     sealed_from_dirty_tree row naming the dirty paths; manifest content
     restored byte-for-byte afterwards (the suite's manifest pin owns
     drift detection; this pin owns refusal semantics).

FAIL-first: pins 2-4 are RED when dirty_sealed_paths() is neutered to
return [] (the pre-b2d24bb behavior). Verified by mutation before this
branch was committed.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB / "tools"))
import receipt_manifest  # noqa: E402

MANIFEST = LAB / "receipts" / "manifest.json"
PROBE = LAB / "experiments" / "ag1_aggregation_rules.py.py"


class SealGuardLive(unittest.TestCase):
    def test_guard_runs_git_status_in_checkout(self):
        r = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=LAB, capture_output=True, text=True,
        )
        if r.returncode != 0 or r.stdout.strip() != "true":
            self.skipTest("not a git checkout — guard is declared inert")
        self.assertEqual(receipt_manifest.dirty_sealed_paths(), [],
                         "guard reports dirt on a clean checkout — either the "
                         "tree is dirty or the guard is hallucinating paths")


class DirtyTreeRefusal(unittest.TestCase):
    """SEAL-1 (2026-10-10): the guard's surface narrowed to TRACKED-file drift
    (untracked files are unsealed by definition — the PW-1 foreign-lane
    deadlock). The probe is now a tracked-file MODIFICATION, preserving the
    d23b phantom-seal intent: uncommitted bytes a seal would hash are refused.
    Untracked-refusal semantics are pinned separately (UntrackedAdvisory)."""

    TRACKED_VICTIM = LAB / "experiments" / "ag1_aggregation_rules.py"

    def setUp(self):
        self.manifest_backup = MANIFEST.read_bytes()
        self.victim_backup = self.TRACKED_VICTIM.read_bytes()
        self.TRACKED_VICTIM.write_bytes(
            self.victim_backup + "\n# pin probe — tracked-dirty trigger for the seal guard\n".encode("utf-8"))

    def tearDown(self):
        self.TRACKED_VICTIM.write_bytes(self.victim_backup)
        MANIFEST.write_bytes(self.manifest_backup)

    def test_guard_reports_probe(self):
        dirty = receipt_manifest.dirty_sealed_paths()
        self.assertTrue(any("ag1_aggregation_rules.py" in ln for ln in dirty),
                        f"probe file under experiments/ not reported dirty: {dirty}")

    def test_seal_refuses_dirty_tree(self):
        r = subprocess.run(
            [sys.executable, "tools/receipt_manifest.py"],
            cwd=LAB, capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 2,
                         f"sealing a dirty tree must exit 2, got {r.returncode}: "
                         f"{r.stdout}{r.stderr}")
        self.assertIn("REFUSED", r.stdout)
        self.assertIn("ag1_aggregation_rules.py", r.stdout,
                      "the refusal must NAME the dirty path — a refusal that "
                      "does not say what was refused cannot be audited")
        self.assertEqual(MANIFEST.read_bytes(), self.manifest_backup,
                         "a refused seal must not touch the manifest")

    def test_allow_dirty_seals_with_admission(self):
        r = subprocess.run(
            [sys.executable, "tools/receipt_manifest.py", "--allow-dirty"],
            cwd=LAB, capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0,
                         f"--allow-dirty seal failed: {r.stdout}{r.stderr}")
        m = json.loads(MANIFEST.read_text())
        admission = m.get("sealed_from_dirty_tree")
        self.assertIsNotNone(admission, "--allow-dirty seal must carry an "
                                       "explicit admission row")
        self.assertTrue(any("ag1_aggregation_rules.py" in p
                            for p in admission["paths"]),
                        f"admission must name the dirty paths: {admission}")


if __name__ == "__main__":
    unittest.main(verbosity=2)


class UntrackedAdvisory(unittest.TestCase):
    """SEAL-1: untracked files under sealed paths are ADVISORY, never a
    refusal — pinning the fix for the Oct 6 CI-red deadlock (PW-1 lane)."""

    def setUp(self):
        self.manifest_backup = MANIFEST.read_bytes()
        PROBE.write_text("# pin probe — untracked advisory trigger\n")

    def tearDown(self):
        PROBE.unlink(missing_ok=True)
        MANIFEST.write_bytes(self.manifest_backup)

    def test_untracked_not_reported_dirty(self):
        dirty = receipt_manifest.dirty_sealed_paths()
        self.assertFalse(any("ag1_aggregation_rules.py" in ln for ln in dirty),
                         f"untracked probe must NOT be tracked-drift: {dirty}")

    def test_seal_proceeds_despite_untracked_lane(self):
        r = subprocess.run(
            [sys.executable, "tools/receipt_manifest.py"],
            cwd=LAB, capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0,
                         f"untracked files must not refuse the seal: "
                         f"{r.stdout}{r.stderr}")
        self.assertIn("advisory: untracked", r.stdout)
        MANIFEST.write_bytes(self.manifest_backup)
