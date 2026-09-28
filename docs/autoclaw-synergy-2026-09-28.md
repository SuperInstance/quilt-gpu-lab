# autoclaw — run receipt, synergy map, rename dossier (2026-09-28)

*Lane note: the flash subagent died on a z.ai rate limit before producing anything; the main session ran the recon instead.*

## What autoclaw actually is (deeper than its README)

The README sells "24/7 knowledge crew" (researcher/teacher/critic/distiller over a SQLite bus → knowledge tiers → VectorDB). The ARCHITECTURE.md reveals the deeper identity: **AutoResearch — an autonomous single-GPU training loop in the modded-nanochat speedrun pattern**: AI agents modify `train.py`, run experiments on a time budget, evaluate **val_bpb** (validation bits-per-byte, vocab-size-independent), and keep improvements. 5-minute training increments. The repo carries **83+ archived experiment dirs** (`data/experiments/exp_0001..exp_0830`) — a real history of the loop running.

**The train.py artifact** (exp_0830): single-file GPT, cherry-picked from nanochat. Config: 12 layers, 6 heads, 768 embd, seq 2048, vocab 32768, window pattern SSSL, flash-attn (kernels-community/flash-attn3 on non-Hopper). `prepare.py` owns MAX_SEQ_LEN, TIME_BUDGET, Tokenizer, dataloader, evaluate_bpb.

## Run receipt (partial, honest)

- `cli`/`healthcheck` bare imports **fail** (module wiring needs the package entry path; `requirements.txt` is empty — deps undeclared). `crew health` not verified on this box yet.
- The **training artifacts are real and inspectable** — this is not vaporware; the loop has history.
- Blockers to a local fire: one-time `kernels` (flash-attn) download + dataset/tokenizer prep via `prepare.py`. All one-time, all fits.

## 4050 fit: YES, easily

~85M params (GPT-2-small class): bf16 weights ~170MB, +optimizer ~1GB, seq 2048 small batch → **well under the ~4.5GB working budget**. The 5-minute-increment speedrun cadence is exactly what a laptop 4050 wants (thermal-friendly bursts, guard-compatible). This is the natural home for the fleet's "train novel models continuously" directive.

## The synergy triangle (Casey's cellular-decomposition loop, embodied)

| Repo | Role | The loop's organ |
|---|---|---|
| **lever-runner** | "The trust compiler. Teach once, run forever." Intent→pre-approved command; LLM never sees the shell; 160 tests; passthrough $0/mo | **Actuation cell** (the hands) |
| **quilt-pincher** | Reflex engine of Quilt cells; pinch→match→execute <50ms, no LLM; .nail reflexes; federates cloud/workstation/ESP32 | **Compiled cellular logic** (the reflexes) |
| **autoclaw** | AutoResearch crew + training loop; writes knowledge, trains models, keeps improvements | **Super-cell that writes new cellular logic** (the teacher/trainer) |

Concrete wiring: autoclaw's Teacher **authors pincher reflexes** (.nail) from what it learns; pincher fires them <50ms forever; when a reflex needs the shell, **lever pulls the pre-approved lever**; autoclaw's Critic is the check that re-engages the big model only on failure. That is verbatim: "the LLM made a cellular logic to do the task; next time the decomposed workflow answers, and the cloud call becomes a check."

## Rename dossier: YES — rename it

The claw family (openclaw/cudaclaw) **grasps and executes**. autoclaw doesn't grasp — it **grows**. Its own architecture doc leads with "AutoResearch"; the claw is vestige. Fleet naming is load-bearing. Candidates:
1. **nursery** — the ecology family (pasture grows animals, forest grows trees, **nursery grows models**). Top pick.
2. **sailing-master** — marine idiom; the officer who taught navigation.
3. **schoolhouse** — plain, warm, the crew's teacher.

## Next plays on this lane
1. One-time setup (kernels + data prep) then fire a 5-minute train increment on the 4050 — first local receipt of the speedrun loop.
2. Author the first pincher .nail reflex FROM an autoclaw lesson (closing the loop for real).
3. The difference-operator transformer seed trains through this path (delta-attention + ternary + sauna/plunge contrastive loss).
