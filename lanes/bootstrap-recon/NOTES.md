# Bootstrap-recon lane — service recon notes (2026-09-29)

Agent: lucineer-bootstrap-recon. Keys read from Casey's key.txt — names only here:
`TYPESAFE_AI_KEY`, `MOTHQUANTUM_COM_KEY`. **Values never written to any file.**
Ledger bookings: 163d0bf6 (H3 claim), 4d056078 (Atlas map), + final delivery book.
H3 deliverable: `/home/eileen/projects/quilt-i2i/docs/H3-micromoth-ionq-recon.md`.

## TypeSafe AI — Jev (typed decision model)

- **What it can do:** decisions-not-text. One POST: `state` + up to N typed questions
  (Choice / Score / Noul), answers return typed values + probability distribution +
  confidence. Atomic parallel evaluation, no context rot.
- **Working endpoints (live-verified):**
  - `GET https://api.typesafe.ai/v1/models` → 200: `jev-latest`, `jev-preview` ✅ (key valid)
  - `POST https://api.typesafe.ai/v1/systemone` — the only op endpoint (NOT exercised: metered)
- **Cost/free tier:** $42/Btok input, output free, 64k ctx, 250k tok/s & 1200 req/min.
  **No documented free tier** — every systemone call bills. Treat as metered; keep states small.
- **Docs:** https://docs.typesafe.ai/ (llms.txt index), quickstart, /api, /models.
  SDKs: `pip install typesafe-sdk`, `@ai-sdk/typesafe-ai`, Pydantic AI, LiteLLM. Skill: github.com/typesafe-ai/skills.

## Moth Quantum — Atlas platform (quantum engines-as-a-service)

- **What it can do:** 32 quantum creative engines over HTTP (quantum blur v0/v1/core/midi,
  coin-toss, comet-qrng, deep-fryer, entanglement-shader v0/v1, graph-v1, labyrinth-v1,
  otoc-echo, qdrive, qpixl, qrc-audio/gen/image/midi/train, retrocausal-echo, tamagotchi
  v0/v1, telablur, tessa-image, tomography-api-v2), each `POST …/process` with
  `mode: "emu"` (free local Aer sim) or `"qpu"` (**IBM hardware** — likely credit-metered,
  not exercised). Jobs pipeline: submit → `/jobs/{id}/status` → `/jobs/{id}/result`.
  Assets (10 GB quota), orgs, showcases, key management.
- **Working endpoints (live-verified, free GETs):**
  - `GET /api/v1/me` → 200, Casey's account, role `player` ✅
  - `GET /api/v1/engines` → 200, 32 engines ✅
  - `GET /api/v1/me/storage` → 200, 0 B used / 10 GB quota ✅
  - `GET /openapi.json`, `/docs` → full machine-readable spec (no auth needed to read) ✅
- **Auth:** `Authorization: Bearer moth_…` (Supabase JWT also accepted).
- **Docs:** https://platform.mothquantum.com/docs · https://api.mothquantum.com/openapi.json
- **Open-source kin:** github.com/moth-quantum — MicroMoth (minimal QC framework,
  Python/Lua/C#/Arduino ports), quantum-audio (encode/decode audio↔circuits), Actias, QuantumBrush.

## MicroMoth (embeddable cell substrate)

Minimal quantum framework; `QuantumCircuit.data` = ordered gate tuples
`x/h/rx/rz/cx/crx/swap/m/init`; `simulate(qc, shots, noise_model)` statevector+counts.
Lua port exists — runs in-game/edge. Full mapping to quilt contract in the H3 doc.

## Three concrete next-use ideas

1. **Moth lane — quantum circuit generation, free:** run Atlas `graph-v1` / `labyrinth-v1`
   in `emu` mode (free) to generate relational structures; decode via MicroMoth tuples into
   quilt cells. `qrc-*` engines = quantum reservoir computing for generative audio when the
   Moth/audio lane wakes up.
2. **TypeSafe as typed-agent runner / ledger triage:** Jev Choice+confidence to route new
   handoffs to lanes (confidence-gated: low → human review), Noul for receipt verification
   ("does this receipt_url support the gist?"). Metered — batch questions per call (fan-out
   pattern), states ≤ few k tokens. Good fit for arcade-judge scoring rubrics too.
3. **H3 rung-0 without IonQ spend:** MicroMoth Lua port as the in-game cell substrate;
   Atlas `emu` as cross-check simulator; MicroMoth `noise_model` as the decoherence proxy
   that pre-registers rung-1/2/3 falsification thresholds before any real QPU job.
