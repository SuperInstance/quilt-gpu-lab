#!/usr/bin/env python3
"""checkpoint-guard — reusable embedding-checkpoint save/verify/resume.

Lifted from the proven pattern in experiments/c5_paired_action.py (the
2026-09-30 22:28 crash-after-extraction lesson): expensive GPU work gets
persisted BEFORE the cheap-but-buggy scoring stage, so a scoring bug never
loses GPU work.

Pattern in one line:
    guard = CheckpointGuard(path, key=lambda: fingerprint_of_inputs)
    if (rec := guard.try_resume()) is not None:
        records = rec
    else:
        records = expensive_gpu_extraction(...)
        guard.save(records)

API (stdlib only):
- CheckpointGuard(path, key)  key: a JSON-serializable fingerprint of the
  inputs (clip list, model id, params...). Resume only happens when the
  stored key matches EXACTLY — no stale-checkpoint contamination.
- .try_resume() -> records | None  (None = miss; loud log on why)
- .save(records)   atomic write (tmp + os.replace), fsync'd
- .invalidate()    archive-by-rename to <path>.archived-<epoch> (never delete)
- .verify(records) sanity-check a resumed payload (count > 0, non-empty)

CLI for ad-hoc inspection / invalidation:
    python checkpoint_guard.py --path ckpt.json --info
    python checkpoint_guard.py --path ckpt.json --invalidate

Worked example (run `python checkpoint_guard.py --selftest`):
    from checkpoint_guard import CheckpointGuard
    g = CheckpointGuard("results/emb_ckpt.json", key={"model": "jev-1.13.0", "n": 4})
    records = g.try_resume()
    if records is None:
        records = [{"emb": [0.1, 0.2]}] * 4   # pretend GPU work
        g.save(records)
    # crash here -> rerun resumes; change key -> clean miss, never stale
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

SCHEMA_VERSION = 1


class CheckpointGuard:
    def __init__(self, path: str, key, log=print):
        self.path = path
        self.key = key
        self.log = log

    # -- internals ---------------------------------------------------------
    def _read(self):
        if not os.path.isfile(self.path):
            return None
        try:
            with open(self.path) as f:
                d = json.load(f)
        except Exception as e:  # unreadable checkpoint = full run, loud
            self.log(f"[checkpoint-guard] unreadable ({e!r}) — full run")
            return None
        if d.get("schema") != SCHEMA_VERSION:
            self.log(f"[checkpoint-guard] schema mismatch ({d.get('schema')!r}) — full run")
            return None
        if d.get("key") != _norm(self.key):
            self.log("[checkpoint-guard] key mismatch (inputs changed) — full run, NOT stale")
            return None
        return d.get("records")

    # -- public API --------------------------------------------------------
    def try_resume(self):
        records = self._read()
        if records is None:
            return None
        if not self.verify(records):
            self.log("[checkpoint-guard] failed verification — full run")
            return None
        self.log(f"[checkpoint-guard] RESUME: {len(records)} records from {self.path} — no GPU")
        return records

    @staticmethod
    def verify(records) -> bool:
        return isinstance(records, list) and len(records) > 0 and all(r is not None for r in records)

    def save(self, records):
        if not self.verify(records):
            raise ValueError("refusing to save records that fail verify() (empty/None)")
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        payload = {"schema": SCHEMA_VERSION, "key": _norm(self.key),
                   "records": records, "saved_at": time.time()}
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(payload, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)  # atomic: no torn checkpoints on crash
        self.log(f"[checkpoint-guard] saved {len(records)} records -> {self.path}")

    def invalidate(self):
        if not os.path.isfile(self.path):
            self.log(f"[checkpoint-guard] nothing to invalidate at {self.path}")
            return
        dst = f"{self.path}.archived-{int(time.time())}"
        os.replace(self.path, dst)
        self.log(f"[checkpoint-guard] archived -> {dst} (nothing deleted)")


def _norm(key):
    """Canonical JSON so dicts/lists with different key order still match."""
    return json.loads(json.dumps(key, sort_keys=True, default=str))


# --- CLI ---------------------------------------------------------------
def _selftest():
    import tempfile
    d = tempfile.mkdtemp()
    p = os.path.join(d, "ck.json")
    g = CheckpointGuard(p, key={"m": "x", "n": 2})
    assert g.try_resume() is None, "empty path must miss"
    g.save([{"emb": [1.0]}] * 2)
    r = g.try_resume()
    assert r is not None and len(r) == 2, "resume must hit on match"
    g2 = CheckpointGuard(p, key={"m": "x", "n": 3})
    assert g2.try_resume() is None, "key change must miss (no stale)"
    g3 = CheckpointGuard(p, key={"n": 2, "m": "x"})  # different key order
    assert g3.try_resume() is not None, "key order must not matter"
    g3.invalidate()
    assert g3.try_resume() is None, "post-invalidate must miss"
    bad = CheckpointGuard(p + ".junk", key={"m": "x", "n": 2})
    with open(p + ".junk", "w") as f:
        f.write("{not json")
    assert bad.try_resume() is None, "corrupt file must miss, not crash"
    print("SELFTEST OK")


def main():
    ap = argparse.ArgumentParser(description="checkpoint-guard: save/verify/resume expensive work")
    ap.add_argument("--path", required=True, help="checkpoint JSON path")
    ap.add_argument("--info", action="store_true", help="print record count + key")
    ap.add_argument("--invalidate", action="store_true", help="archive-by-rename the checkpoint")
    ap.add_argument("--selftest", action="store_true", help="run built-in self test")
    a = ap.parse_args()
    if a.selftest:
        _selftest()
        return
    g = CheckpointGuard(a.path, key=None)
    if not os.path.isfile(a.path):
        sys.exit(f"FATAL: no checkpoint at {a.path}")
    with open(a.path) as f:
        d = json.load(f)
    if a.info:
        print(json.dumps({"path": a.path, "records": len(d.get("records", [])),
                          "key": d.get("key"), "saved_at": d.get("saved_at")}, indent=1))
    if a.invalidate:
        g.invalidate()


if __name__ == "__main__":
    main()
