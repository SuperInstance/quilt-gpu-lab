# VOYAGER-SKILLLIB — RESULTS ENTRY

Lane **VOYAGER-SKILLLIB** (prereg: `proposals/runs/VOYAGER-SKILLLIB-prereg.md`,
frozen 2026-10-02 00:0x AKDT). Harness `experiments/skill_library.py`.
Generator `qwen2.5:3b-instruct-q4_K_M`, embedder `nomic-embed-text` (768-d), both
local ollama, CPU-only, zero metered spend. Verifier = **pure code** (restricted
exec + SIGALRM + oracle-generated test cases) — **no LLM judge**.

## Verdict

| gate | frozen bar | result | verdict |
|---|---|---|---|
| (a) retrieval | top-1 family-hit ≥ 0.60 and ≥ +0.20 over chance | **hit 0.750** vs chance 0.250 (**+0.500**); same-family mean cos **0.9619** > cross **0.9033** | **PASS** |
| (b) reuse | augmented pass@k8 > scratch by ≥ 0.10, ≥1 flip | scratch **1.000** = augmented **1.000**, delta +0.000, flips 0 | **FAIL** |
| (c) purity | only verified entries, ever | smoke store 11/11 verified; full store 39/39 verified; wrong-program negative control rejected; unverified append raises | **PASS** |

## Gate (b) detail — the gate was too lenient, not the mechanism dead

Task-level pass@8 saturates because 3 of 4 held-out tasks are easy for a 3B model.
**Per-sample** pass counts tell the real story
(`results/skill_library_full.log`):

- `rev_all_words` (hard, needs word-order AND char reversal): scratch **1/8** →
  augmented **8/8** (the stored `rev_each_word` exemplar teaches the idiom).
- `cap_first_only`, `prod_digits`: 8/8 both arms (no headroom).
- `cumsum`: scratch **8/8** → augmented **5/8** — an **exemplar-hurt** case: the
  retrieved `sort_desc` skill is the wrong analogy and biases the model.

So retrieval+reuse is a large win on the one task with headroom, a wash on easy
tasks, and a *loss* when the nearest neighbour is a bad analogy. Re-booking
gate (b) at **per-sample pass rate**, or with harder held-out tasks, would be the
honest next move (not done here; prereg is prereg).

## Smoke run (`results/skill_library_smoke.log`)

11 seed tasks → **10 verified + stored** (`title_case` correctly *rejected*: the
3B model dropped the double-space, 5/6 tests — the verifier doing its job).
Later prompt `rev_all_words` → top-1 `rev_each_word` (sim 0.9855, family HIT) →
verbatim reuse **0/8 FAIL** (as preregicted) → augmented reuse **8/8 PASS** →
scratch 0/8 FAIL. Purity re-audit 11 entries / 0 unverified. **SMOKE PASS.**

## Single biggest risk to the full Voyager loop on 6 GB

**The verifier, not the VRAM.** 6 GB fits a 3–7B generator and a 137 MB embedder
with room to spare; the loop's wall clock here is CPU/serial generation. The real
brittleness is that an *executable* verifier is easy for closed-form text/arithmetic
tasks and nearly impossible for open-ended ones — with a weak verifier the library
silently fills with plausible-but-wrong skills, and gate (c) (purity) stays green
while the accumulated "capability" rots. Voyager got a free verifier from
Minecraft's deterministic state; a game env is a **verifier substrate**, which is
the true reason to add one back.

**NO COMMIT.**
