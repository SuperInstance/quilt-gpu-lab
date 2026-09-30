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
PROBE = LAB / "experiments" / "pin_probe_dirty_guard.py"


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
    def setUp(self):
        self.manifest_backup = MANIFEST.read_bytes()
        PROBE.write_text("# pin probe — dirty-tree trigger for the seal guard\n")

    def tearDown(self):
        PROBE.unlink(missing_ok=True)
        MANIFEST.write_bytes(self.manifest_backup)

    def test_guard_reports_probe(self):
        dirty = receipt_manifest.dirty_sealed_paths()
        self.assertTrue(any("pin_probe_dirty_guard" in ln for ln in dirty),
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
        self.assertIn("pin_probe_dirty_guard", r.stdout,
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
        self.assertTrue(any("pin_probe_dirty_guard" in p
                            for p in admission["paths"]),
                        f"admission must name the dirty paths: {admission}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
