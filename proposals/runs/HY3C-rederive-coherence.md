# HY3C — re-derive proof: is a cell a cache, or a property of the serving engine?

Lane **HY3-CACHE** (dog-food of `tencent/Hy3` as a caching expert seat). Harvest of the
lane's winner **S5#11 «re-derive test = cache proof»** + Design 3, extended to the engine
question the expert (correctly, per runner constraint (c)) sidestepped.

Pre-registered **2026-10-01 ~15:10 AKDT, BEFORE fire** — before any script is written and
before any GPU run. Frozen gates; the verdict is booked either way. Seed **2718**.
**NO GPU RUN HAS BEEN FIRED.** This file is a proposal/seed only.

## Provenance (why this probe exists)

- Output doc: `superinstance-api/docs/cache-ideas-hy3-2026-10-01.md` (§3 Design 3, §5 verdict).
- XP-C precedent (`quilt-gpu-lab/results/xp_c/RESULTS-ENTRY.md`, DONE 14:12 today): the local
  4050 seat is **not byte-replay-safe under co-tenancy** — 1–3 of 30 prompt cells flipped per
  battery at temp 0 / seed 2718; "byte-identity at a fixed seed is a property of the *whole
  serving stack in a given window*, not of the model alone."
- Hy3's Design 3 defines a **re-derive test**: a cell (room + tiles at a stage) is a *cache*
  IFF a rebuild from `(bookings, tile_versions)` reproduces its content hash; else it is
  *authority*. Design 3's own probe runs the rebuild on **deterministic CPU only**. This
  probe asks the next question: **is re-derivability a property of the content, or of the
  derivation ENGINE + serving window?**

## Claim

*A cell's content may be treated as a CACHE (safe to demote/serve-as-preference) IFF it is
re-derivable — a rebuild from the ledgers reproduces its hash. Re-derivability is a property
of the **derivation engine**: CPU-derivable content is a cache; content derived by the local
**4050** seat is an **authority**, because under co-tenancy the same input does not reproducibly
hash to the same output.* If the GPU arm reproduces perfectly, the claim is KILLED — the local
seat may serve as a re-derivable engine and cells derived on it remain caches.

## Setup (frozen)

- **Ledger fixture:** a synthetic-but-legal cell. `rooms(id=1, stage=2)`, `tiles` with 30 keys,
  each key backed by a `tile_versions` history (2–4 versions). The **derivation function** D
  maps a cell's ledger rows → the cell's content bytes:
  - **D_cpu (control / ground truth):** deterministic pure function of the rows (canonical
    JSON serialization + sha256). No model. This is the harness's own determinism proof.
  - **D_gpu (arm under test):** the local ollama seat summarizes/derives each of the 30 tile
    contents (or the whole cell) → content bytes. Fixed model **`qwen2.5:3b-instruct-q4_K_M`**
    (the XP-C seat, so the two results are comparable), **temperature 0, seed 2718, plain chat**,
    identical prompt text every replay.
- **30 items** (one per tile key; the refusals/binding checks are inherited from the XP-C guard,
  not re-gated here).
- **3 replays** per arm, byte-for-byte comparison of derived content hash.
- **Two windows (cross-window arm):** the 3 GPU replays are split window-1 / window-2, with
  co-tenancy declared (any other resident seat named) and `min_free_vram_mib` recorded per window.

## Frozen gates (no goalpost migration)

| gate | bar | arm |
|---|---|---|
| **G0 — harness determinism** | D_cpu rebuild hash identical across 3 runs (**3/3**) | CPU |
| **A — CPU re-derive** | 30/30 items reproduce byte-identical across 3 runs | CPU |
| **B — 4050 re-derive** | **≥ 0.95** (≥ 29/30) items byte-identical across 3 replays, T=0, seed 2718 | 4050 GPU |
| **C — cross-window** | window-1 vs window-2 identical-hash fraction reported; **CPU arm must be 1.000** (establishes the epoch is the GPU, not the box) | both |

- `G0` fails → run **VOID** (harness bug, not a model result).
- `C` CPU != 1.000 → the "serving window" framing is unsupported by the harness → **INCONCLUSIVE**.

## Verdict mapping (mechanical)

- **A PASS + B PASS + C(CPU)=1.000** → **KILL** the claim: the local seat IS a re-derivable
  engine; GPU-derived cells may keep cache semantics (demote safe).
- **A PASS + B FAIL + C(CPU)=1.000** → **KEEP**: re-derivability is engine-dependent; GPU-derived
  cells are **authority** (authority-lock), CPU-derived cells are **cache**. The measured B gap
  is the finding and is booked as such.
- **B PASS but `std == 0`-style degenerate** (all 30 identical by construction, e.g. seat
  returned constant text) → **INCONCLUSIVE**, and the constant-output detector must fire.
- Any **constant-output** arm (all 30 items identical to each other, not just across replays)
  → **VOID for B** (the seat collapsed; not a determinism measurement). Detector is frozen here.

## Frozen falsifiers / honesty hooks (pre-registered)

1. **Constant-output detector:** if the 30 GPU-derived contents have < 5 distinct values, B is
   VOID (a degenerate seat is not a deterministic seat).
2. **Binding receipt:** each derived item carries `{cell_id, engine, seed, input_digest, provider}`
   (XP-C envelope discipline); a replay that drops a binding key is counted as a B-miss (omission,
   not fabrication — XP-C's observed failure mode).
3. **Co-tenancy is declared, not hidden:** if another GPU-resident seat holds the card, it is
   named in the receipt; `min_free_vram_mib` recorded per window; the VRAM floor is **1024 MiB**
   (XP-C guard floor). If co-tenancy is present, that is the *claim under test*, not a defect —
   the probe measures the seat **as the fleet actually uses it**.

## Smallest variant (if time-boxed)

Drop D_gpu to **10 items × 3 replays** (bar ≥ 0.95 → ≥ 10/10; report the fraction). The
cross-window arm collapses to the same 10 items in a second window. Everything else frozen as
above. This variant is the *minimum* falsifier of the claim; the full 30 is the published form.

## Guard + receipt (G7) — no receipt → run VOID

- `Guard(task_id="HY3C-rederive-coherence", seed="2718", receipt_dir=results/hy3c/guard)`.
- Preflight: free VRAM ≥ 1024 MiB, temp ≤ 80 °C.
- G7 watt receipt (`g7-watt-receipt@1`, validator `../fleet-seeds/scripts/g7_validate.mjs`)
  sealed over the whole measured window; idle floor not subtracted (fleet convention).
- Code lives in `experiments/hy3c_rederive.py`; the guard + stages + Provider shape is ~600
  lines of stdlib already proven by XP-C's harness (`experiments/xp_c_envelope.py`) — reuse the
  Guard, do not rebuild it.

## Relationship to XP-C (honest scoping — booked up front)

Gate B is **XP-C-adjacent**: both measure byte-replayability of the same 4050 seat. The *new*
content here is not "does the seat flip" (XP-C answered that) — it is the **decision mapping**:
XP-C measured a cell *contract*; this probe measures a **cache/authority decision rule** and its
engine-dependence, plus the CPU control arm that XP-C did not run. If a reviewer judges Gate B
redundant with XP-C, the minimal publishable result is **G0 + A + C(CPU)**: proving the re-derive
test is *well-formed on CPU* is the prerequisite for ever trusting it on GPU, and is itself new.

## Receipts to book either way (tapestry doctrine)

- `results/hy3c/` (per-replay derived hashes, window/co-tenancy metadata, VRAM samples).
- `RESULTS.md` entry + i2i booking (`agent: HY3-CACHE`, `books_to: superinstance-api/cache`,
  gist = KEEP/KILL one-liner, receipt_url = the results file).
- The expert's own verdict (doc §5) is booked alongside: **KEEP Hy3 as standing seat, B+**,
  with the rider "verify platform quotas/prices/columns."

Seed **2718** throughout. No commits — the keeper commits.
