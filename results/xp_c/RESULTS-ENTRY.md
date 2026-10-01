## [DONE 14:12 GPU Oct 1] XP-C — envelope local provider: **KILL** (the local seat does not hold the pure cell contract; guard + cloud arm do)

Lane XP-C, pre-registered in `scratch/scout-2026-10-01-pushwave.md` §3c (`cot-quilt-lab` lane C seam).
CLAIM UNDER TEST: *the pure `z_in -> z_out` cell contract survives a real model as Provider — local GPU
arm vs cloud arm vs stub ground truth.* Seed 2718, temperature 0, 30 real prompts, 3 local replays.

### 0. VERDICT (two lines, no goalpost migration)

**KILL.** Two of three frozen gates fail on the LOCAL arm: **B** (byte-identical across 3 replays at
temp 0 / seed 2718) **FAILED**, and **C** (well-formed envelope rate >= 0.95) **FAILED at 0.9333**.
**A** (malformed-envelope refusal 100%) **PASSED 20/20** — this is a model/seat failure, not a guard
bypass. Three arms ran (stub, local, cloud), so the result is not INCONCLUSIVE.

### 1. Frozen gates (as pre-registered)

| gate | bar | measured | verdict |
|---|---|---|---|
| A — malformed-envelope refusal | 100% (20/20) | **20/20 = 1.000**, every refusal structured | **PASS** |
| B — LOCAL byte-identical, 3 replays, T=0, seed 2718 | 3/3 | **FAIL** — 3 of 30 prompts differ across replays | **FAIL** |
| C — LOCAL well-formed rate | >= 0.95 | **0.9333** (28/30; replays 28, 29, 30) | **FAIL** |

### 2. Per-arm results

| arm | provider | well-formed | determinism | notes |
|---|---|---|---|---|
| STUB | pure function of (prompt, seed) | **30/30 = 1.000** | 3/3 identical | ground truth for the contract |
| LOCAL | `qwen2.5:3b-instruct-q4_K_M`, ollama, GPU | **28/30 = 0.9333** | **FAIL** | both B and C fail here |
| CLOUD | `glm-5.3-flash`, z.ai | **30/30 = 1.000** | n/a (1 pass, not gated) | comparison arm; see §3 endpoint note |

**Cloud endpoint note (pre-registration honoured).** The registered model `glm-5.3-flash` on the z.ai
**pay-as-you-go** endpoint returns `429 code 1113 (Insufficient balance or no resource package)` — booked
`NOT-RUN` with the exact error, no improvisation. The account's live plan is the **coding plan**, and the
coding endpoint (`https://api.z.ai/api/coding/paas/v4/chat/completions`) is the shape this repo already
uses (`g1c_verdict_routing.py`, `px2_gardener.py`); the arm was re-run there and scored **30/30, 0 errors**.

### 3. The finding — the local seat is not replay-safe under lab load

- **Gated battery (3 x 30 prompts):** 3 prompts differ across replays — `cell_a08` (r1,r2 vs r3),
  `cell_a13` (r1 vs r2,r3), `cell_a23` (r1 vs r2,r3).
- `cell_a08` / `cell_a13` are **compliance flakes**: the model intermittently drops the `provider` and
  `seed` keys, which the guard refuses (`output.key_set`). The same flake is what costs the well-formed
  gate (28/30, and it is not even stable across replays: 28, 29, 30).
- `cell_a23` is well-formed in every replay but the bytes differ in replay 1 — a *semantic* flip, not an
  omission.
- **Isolated re-run probe** (`--probe-determinism`, a second 3x30 battery, same prompt/seed/temp, under
  its own guard + receipt): **still not byte-identical** — `cell_a15` answered `"spring"` in replay 1 and
  `"summer"` in replays 2-3. Two independent batteries, two independent flake sets.
- **Counter-probe:** 5 consecutive isolated repeats of each flaky prompt were byte-identical, and cold /
  after-7-other-prompts / immediate-repeat tests were identical too — so the flake is **intermittent and
  load/session-dependent**, not a function of (prompt, seed).
- **Co-tenancy observed:** the guard recorded `min_free_vram_mib` **1860** (gated window) and **1828**
  (probe window) while our seat needs ~2.2 GB on a 6 GB card — another lane was resident on the GPU
  during both windows. The most likely mechanism is serving-stack non-determinism under co-tenancy
  (batch/kernel scheduling), not a seed bug: the same prompt, seed, temperature and model flip a token
  depending on what else is on the box.
- **Consequence for the fleet:** byte-identity at a fixed seed is a property of the *whole serving stack
  in a given window*, not of the model alone. Replay-sensitive lanes (XP-B hook verification, D10/style
  receipts) must **serialize the seat** or pin determinism per cache/window state. G1b's 8-prompt
  byte-identical result for the 7B seat is not contradicted — it was a quieter, shorter window; it is
  simply not sufficient to certify the seat.

### 4. What survived — the envelope contract itself

- The **Guard layer is the strongest part of the build**: 20/20 deliberate malformations refused, each
  with a structured error (`output.not_json`, `output.empty`, `output.not_object`, `output.key_set`,
  `output.type.{cell_id,z_out,seed}`, `output.digest_mismatch`, `output.bad_digest_format`,
  `output.cell_id_mismatch`, `output.provider_mismatch`, `output.seed_mismatch`, `output.empty_z_out`),
  plus **5/5 extra strictness** cases (markdown fences, JSON embedded in prose, `NaN`, bare scalar,
  whitespace-only) and **4/4 malformed input cells** refused by the input schema check.
- Strict parsing is load-bearing: duplicate keys refused, `NaN`/`Infinity` refused, any trailing content
  refused — there is no lenient path.
- The **binding** checks are what make an envelope a receipt rather than decoration: `z_in_digest` must
  digest the *dispatched* `z_in`, and `cell_id`/`provider`/`seed` must match the dispatch. The 3B model
  never faked a digest; it failed by **omission** — exactly the failure mode the guard is built for.
- **Cloud held the contract 30/30** — the contract is realizable; the 3B local seat is the weak link at
  this prompt. Stub (ground truth) 30/30 and byte-identical.

### 5. Prompt honesty note (recorded before the gated run)

Prompt **v1** (no literal shape example) scored **0/5** on a 5-prompt plumbing probe: the 3B model
returned `{"z_out": ...}` only, or a *string* seed. Prompt **v2** adds one literal shape example and the
seed-is-a-number rule → **6/6** on a 6-prompt probe. The gated run and the cloud arm both use the frozen
v2 prompt, **plain chat** (no JSON-mode crutch), same text for every arm. Both probes are recorded in the
artifact (`prompt_version`, `prompt_notes`). This is a prompt-clarity fix made *before* the gated run, not
a post-hoc goalpost move — and it did **not** rescue the local arm.

### 6. Receipts / energy / artefacts

- G7 receipts (all `g7-watt-receipt@1`, validator exit 0, `source: measured`, idle floor not subtracted):
  - `g7-wr-xp-c-envelope-local-1790891436` — gate **PASS**, 6232.28 J = 1.7312 Wh (attempt-1 window, see §7.1)
  - `g7-wr-xp-c-envelope-local-1790892000` — gate **PASS**, 6654.98 J = 1.8486 Wh (gated local battery)
  - `g7-wr-xp-c-envelope-local-1790892402` — gate **PASS**, 8231.12 J = 2.2864 Wh (isolated determinism probe)
- Total **5.87 Wh = $0.00135** @ $0.23/kWh. Guard: no breach, no timeout, max temp **74 C**, min free VRAM
  1828-1860 MiB (co-tenancy, above the 1024 MiB floor). CPU: refusal battery + stub arm, no GPU.
- Artefacts: `results/xp_c/xp_c_results.json` (all numbers), `results/xp_c/local/raw_runs.json` (gated
  battery, per-replay digests + raws), `results/xp_c/determinism_probe_isolated.json`,
  `results/xp_c/local/probe_raw_runs.json`, `results/xp_c/guard/` (3 receipts + summary + ledger).
- Code: `experiments/xp_c_envelope.py` (Guard layer, stages/pipeline, cells, arms, gates, verdict),
  `experiments/xp_c_providers.py` (Provider interface + stub/local/cloud).
- Secrets: `ZAI_KEY` read at use-time, sent only in an `Authorization` header via a 0600 curl config file
  (never argv/URL/log). Machine scan of every artifact: `zai_key_present_in_artifacts: false`.

### 7. Lane defects booked (fail loud, mine)

1. **`makedirs` bug (mine).** The local worker wrote to `results/xp_c/local/` without creating the
   directory: attempts 1 and 2 of the first driver run each executed a full 3x30 battery on the GPU and
   then died on the artifact write (`FileNotFoundError`, rc=1). The guard receipt for those windows is
   PASS *and* the arm was booked NOT-RUN — both are true: the calls happened, the artifact did not.
   Fixed (`os.makedirs`), re-run via `--resume`; the extra energy is in the receipt total above.
2. **`raws_run1` misnamed (mine).** It held the *last* replay's raws, not replay 1 (verified:
   `sha256(raws_run1[i]) == per_replay[2].digests[i]`). Documented inside the artifact; code renamed to
   `raws_last_replay`. No data changed.
3. **Not a defect:** `Guard.run()`'s single-use stop-event was fixed by the XP-B finding-4 patch (landed
   13:42 today, before this run). `local_phase` uses a fresh Guard per attempt as belt-and-braces.
   The probe's first `diffs` block also printed the wrong list index; the recomputed block in
   `determinism_probe_isolated.json` is authoritative (no new model traffic).

### 8. What XP-C means for the queue

- **KEEP the seam**: Guard + stages + Provider is ~600 lines of stdlib, and three arms plug into it with
  no contract change. `cot-quilt-lab` lane C's interface is buildable as specified.
- **KILL the claim as stated for the LOCAL seat**: at 3B, temp 0, seed 2718, on this box, the pure cell
  contract is neither byte-reproducible (1-3 of 30 prompts flip per battery) nor >= 0.95 well-formed.
- **XP-C2 (proposed):** (a) re-run the determinism gate in a *serialized* window with co-tenancy declared
  and the seat unloaded between replays; (b) test `qwen2.5:7b-instruct-q4_K_M` (G1b's byte-identical seat)
  and schema-constrained decoding (ollama `format: json` / grammar) against the >= 0.95 gate; (c) price the
  cloud arm per 1k envelopes — it already holds the contract at 30/30.
