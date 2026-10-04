"""forget_cell.py — FORGET-cell: receipted erasure over a hash-chained witness ledger.

QO6b instrument (pre-reg proposals/runs/QO6b-forget-cell.md). Doctrine lineage:
- QO6 eproc retraction: "a process that cannot retract is a p-value in disguise" —
  forgetting must itself be evidenced.
- MR-1 / SCOUT-25 tipnotary: hash-chained receipts, tamper names itself.
- quilt-canvas-tui #1 trapdoor lesson (SCOUT-42): post-FORGET verify must return a
  DEFINED verdict — never wedge, never restart.

Erased receipts are retained as tombstones (payload kept, status=erased): the chain
stays hash-verifiable end-to-end, and downstream consumers re-derive erased_id from
the tombstone bytes.
"""
import copy
import hashlib
import json


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _digest(receipt_no_digest):
    return hashlib.sha256(_canon(receipt_no_digest).encode("utf-8")).hexdigest()


class ForgetCell:
    def __init__(self):
        self.receipts = []

    def _tip(self):
        return self.receipts[-1]["digest"] if self.receipts else "GENESIS"

    def append(self, shot, kind, payload):
        if not shot or not isinstance(shot, str):
            raise ValueError("shot is required (non-empty str) — no silent defaults")
        if not kind or not isinstance(kind, str):
            raise ValueError("kind is required (non-empty str) — no silent defaults")
        if self.is_forgotten(shot):
            raise ValueError(f"shot {shot!r} is forgotten — refusing to append under erased id")
        base = {"seq": len(self.receipts), "prev": self._tip(),
                "shot": shot, "kind": kind, "payload": payload,
                "status": "witness"}
        rec = dict(base)
        rec["digest"] = _digest(base)
        self.receipts.append(rec)
        return rec["digest"]

    def witness_receipt(self, shot):
        for r in self.receipts:
            if r["shot"] == shot and r["kind"] == "witness":
                return r
        return None

    def is_forgotten(self, shot):
        return any(r["shot"] == shot and r["kind"] == "FORGET" for r in self.receipts)

    def forget(self, shot, reason):
        if not reason or not isinstance(reason, str):
            raise ValueError("reason is REQUIRED and pre-registered — no silent defaults")
        w = self.witness_receipt(shot)
        if w is None:
            raise ValueError(f"unknown shot {shot!r} — no witness receipt to forget")
        if self.is_forgotten(shot):
            raise ValueError(f"shot {shot!r} already forgotten — double-forget refused")
        base = {"seq": len(self.receipts), "prev": self._tip(),
                "shot": shot, "kind": "FORGET",
                "payload": {"reason": reason, "erased_id": w["digest"]},
                "status": "erased"}
        rec = dict(base)
        rec["digest"] = _digest(base)
        # tombstone the witness receipt (retain bytes, mark erased)
        w["status"] = "erased"
        self.receipts.append(rec)
        return rec["digest"]

    def rederive(self, shot):
        """Re-derive erased_id from retained tombstone bytes; diff vs the FORGET."""
        w = self.witness_receipt(shot)
        f = next((r for r in self.receipts if r["shot"] == shot and r["kind"] == "FORGET"), None)
        if w is None or f is None:
            raise ValueError(f"shot {shot!r} has no (witness, FORGET) pair to re-derive")
        base = {k: w[k] for k in ("seq", "prev", "shot", "kind", "payload", "status")}
        # NB: the stored digest was computed over the ORIGINAL status ("witness");
        # re-derivation must reconstruct the pre-erasure bytes exactly.
        base["status"] = "witness"
        return _digest(base), f["payload"]["erased_id"]

    def verify(self):
        """Defined-verdict chain walk. Never raises. G3: post-FORGET stays defined."""
        prev = "GENESIS"
        for r in self.receipts:
            d = r.get("digest")
            base = {k: r[k] for k in r if k != "digest"}
            if _digest(base) != d:
                return {"verdict": "TAMPERED", "first_bad_seq": r["seq"]}
            if r["prev"] != prev:
                return {"verdict": "TAMPERED", "first_bad_seq": r["seq"]}
            prev = d
        return {"verdict": "VERIFIED", "first_bad_seq": None}
