# Pre-reg claim protocol (2026-10-01, after the D12j race)

Context: the D12j pre-reg (0b2df86) was implemented and fired twice within ~30 minutes — once by a
wheel lane, once by Lucineer — on the same file paths. Git kept everything and the double run became
a two-witness KEEP (see the reconciliation section in RESULTS.md), but the outcome was luck, not design.

## Rules (effective now)

1. Every pre-reg carries an `owner:` line at the top:
   - `owner: farm` — the farm/wheel owns firing. Main session MUST NOT self-fire it.
   - `owner: lucineer` — Lucineer self-fires. Wheel lanes MUST NOT grab it (check owner before
     implementing).
   - `owner: any` — explicitly raceable. Double runs are welcome; both MUST be preserved and the
     result booked as two-witness.
2. Defaults: GPU/lane work → `owner: farm`. Instrument laws and cheap independent probes that benefit
   from a second witness → `owner: any`.
3. Collision recovery (if it happens anyway):
   - Never overwrite a committed artifact in the working tree.
   - Restore the owner's files from their commit; preserve your copy as `<name>-<side>.py` /
     `<name>-<side>.json`.
   - Book a reconciliation section in RESULTS.md; commit message says "reconciliation".
4. `tools/farm_queue_flip.py` already refuses to arm anything whose prereg is not committed
   (exit 2, refuse-loud). Keep that gate.

— Lucineer, 2026-10-01, after spending the morning untangling a race we happened to win twice.
