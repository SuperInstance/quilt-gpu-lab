# Quilt × Insect-Brain — the fly-sim buzz, deconstructed and mapped (2026-09-28)

**Date:** 2026-09-28 · **Lane:** Casey directive — "have another deeply understand how our technology
of quilt could synergize with all the buzz (pun intended) over the modeled insect brain."
**Inputs:** web scout (Janelia/Google releases, PC Gamer/Cnet/Hackaday coverage, the neuroai.science
deep-read, FlyGM arXiv:2602.17997, doomfly/FLM/Stonkfly repos) + house deep-reads of quilt-gpu-lab,
quilt core, quilt-pincher, quilt-arcade, chiaroscuro-embedding, G1 glyph program.
**Status labels follow the constellation law: measured / simulated / wagered.**

---

## 0. TL;DR

The buzz is real and fresh: the complete male fruit-fly CNS connectome (Janelia + Google, ~160k
neurons, ~125M synapses, **including the ventral nerve cord**) dropped, and a meme-wave of
connectome-driven game agents followed — fly sims playing DOOM, Mario 64, Beat Saber, trading crypto.
The honest state: one clean reflex (Shiu et al. 2024), one locomotion controller (FlyGM 2026), and a
pile of demos that are, in a computational neuroscientist's own deconstruction, "random button
mashing" with decorative vision and no verifiable metrics.

Quilt is the same shape as the thing they're simulating — cells as ganglia, reflexes as opcodes,
dopamine as the WAL — with the two things the entire buzz lacks: **receipts** (nobody's fly sim can
be re-derived) and **federation** (the fly's body is substrate-distributed; their sims are
single-process scripts). Top synergy, in one line: **the field's own 2026 paper begs for
"pre-specified, independently verifiable metrics" — that is quilt's native product.**

---

## 1. What the buzz actually is (the scout)

### 1.1 The artifact chain (measured)

| artifact | what it is | why it matters |
|---|---|---|
| **FlyWire** (2024) | first complete fly brain connectome (female), ~140k neurons | the graph artifact: a signed sparse matrix A_ij = synapse counts |
| **Shiu et al. 2024** (Nature) | naive LIF embedding of the matrix — every neuron same params, one global gain constant — produced a working sugar→proboscis reflex | the "YOLO" result: activity neither dies nor seizes; but only a few hundred neurons meaningfully engage |
| **Lappalainen et al. 2024** | deep mechanistic model of the fly **visual system**, 45,669 neurons (⅓ of the brain), fine-tuned for optic flow | the working-vision slot — graded/rate, not yet integrated with spiking whole-brain sims |
| **MaleCNS** (HHMI Janelia + Google, 2026) | complete male CNS: brain + optic lobes + **ventral nerve cord**, ~160k neurons, ~125M synapses, 33 person-years of proofreading | VNC = the fly's spinal cord; the release that made embodied sims conceivable and triggered the wave |
| **FlyGM** (arXiv:2602.17997, 2026) | whole-brain connectome instantiated as a graph-structured controller for a biomechanical fly, deep RL | the serious wing: stable locomotion, better sample efficiency than graph/non-graph baselines; connectome as architectural prior, not gimmick |

### 1.2 The viral wave (measured — the games)

- **Super Mario 64** (`ornata/fly`): noise-driven LIF sim; identified neurons (e.g. DNg100
  descending neuron) mapped to N64 buttons. No training. Verdict per the deconstruction: *random
  button mashing on an emulator* — a noise-driven recurrent net looks agentic.
- **Beat Saber**: overtrained on one track; barely uses the visual input; doesn't generalize.
- **DOOM** — `nftechie/doomfly` (Alex Wormuth): 3-factor learning rule on Kenyon-cell→MBON synapses
  (the mushroom body, the fly's actual learning organ); kill = reward, die = punishment.
  **No positive reports yet.** This is the honest one in the batch.
- Also from the same wave: **Stonkfly** (crypto day-trading fly, unverified), **FLM** (fly language
  model — frozen embeddings through a frozen fly sim as reservoir + learnable adapter), **FlyHard**
  (CARLA driving via behavioral cloning through the connectome — no vision, memorized trajectories),
  Flytok, memecoins, a "bisexual fly."
- **Cortical Labs** (separate bio wing, March 2026): ~200k living human neurons on a chip playing
  DOOM — not a connectome sim, but rides the same news cycle.
- The **Google AI account (2.4M followers) amplified the whole wave**; Hackaday covered it
  2026-09-14; the fly played "games to crypto trading" in one week.

### 1.3 The deconstruction (the skeptic's ledger — neuroai.science)

The definitive under-the-hood read (written with feedback from Brunton/Turaga/Nayebi, citing a
Kording–Shiu 2026 co-authored piece) finds:

1. **No full sensorimotor loop anywhere.** "Actually getting a full sensorimotor loop working in an
   intact connectome remains a research-grade problem."
2. **The connectome is beside the point** in the flex demos: backprop/RL through it, or a flexible
   readout on top, is universal-approximation doing the work — a *C. elegans* worm brain (302
   neurons) drove a fly body via PPO (the "digital sphinx"). Big reservoir + RL = anything.
3. **Vision is decorative.** The embodied-fly startup (Eon, "we uploaded a fly") admitted its visual
   activations were "somewhat decorative." Flies are *extremely* visual; the one working fly-vision
   model (Lappalainen) isn't integrated into any game-playing sim.
4. **Missing parameters everywhere:** synaptic strengths/delays, intrinsic electrophysiology,
   neuromodulators, plasticity (except narrow mushroom-body rules).
5. **The verification crisis, verbatim (Kording et al. 2026):** *"without pre-specified,
   independently verifiable metrics, even technically interesting results attract legitimate
   skepticism that is difficult to rebut."*
6. **A missing layer:** VNC outputs → joint angles (the body models are joint-driven, not
   muscle-driven; someone must supply a tiny mapping net or Hill-type muscles).

### 1.4 Coverage vs hype (measured)

Scale is ~160k neurons (not an "upload"); games are barely "played" (noise-mash, one overfit track,
untrained DOOM); learning at whole-brain level does not exist; the real results are one reflex, one
locomotion controller, and a beautiful open problem. The buzz's technical center of gravity:
**connectome-as-architecture-prior, reservoir computing, 3-factor plasticity in the mushroom body.**
The hype is the meme layer; the artifact underneath is genuinely historic.

---

## 2. The quilt synergy map — quilt AS the insect nervous system

The insect CNS is already a quilt. Ganglia are cells; the thoracic VNC is a reflex engine with no
deliberation; dopamine is a listener event; the compound eye is a sensor-cell array; the whole
organism is federated across substrates (eye / brain / nerve cord / muscle). Quilt doesn't
metaphorically resemble the fly — it is the same shape, **plus receipts**.

| insect nervous system | quilt equivalent | already shipped where |
|---|---|---|
| **ganglion** (local hub, stereo wiring, fires on input) | **cell** — value/formula/listener/sensor/ai/program in a reactive dependency graph | quilt-core (the engine evaluates the sheet; memoized, reactive) |
| **thoracic reflex layer / VNC** (stimulus→circuit→motor, <50ms, no brain) | **pincher** — "pinch in, match a reflex, execute. <50ms, no LLM, zero marginal cost. Federates across cloud, workstation, and ESP32" — a reflex engine built *entirely from quilt cells* | quilt-pincher |
| **opcode-like stereotyped arcs** (fixed stimulus→response programs) | **opcodes** — the five-opcode quilt WAL; pincher's pinch→match→execute as a compiled reflex arc | quilt-pincher + git-agent `quilt_emit` doctrine |
| **dopamine neuromodulation** (PAM reward / PPL1 punishment = the third factor of learning: pre × post × modulator) | **the receipt chain** — every meaningful event appended, digest-chained, re-derivable; the modulator term IS the WAL event | quilt-gpu-lab `receipts/manifest.json`, fail-first pins, honest-verdict ledgers |
| **compound eye** (tiled, edge-motion specialized — "looks very much like a bespoke CNN") | **chiaroscuro** — frames rendered to a 48×36 glyph lattice; tone ramp + 4 edge families × 5 levels = a V=32 code alphabet; renderer-replayable | chiaroscuro-embedding `renderer.py` + G1 glyph predictor (G1–G9 arc live in this lab) |
| **body across substrates** (eye ≠ brain ≠ nerve cord ≠ muscle) | **federation** — same sheet, different runtimes: browser / Cloudflare Worker / workstation / ESP32 | quilt-fleet, quilt-mesh, quilt-esp32, pincher's three tiers |
| **the world it lives in** | **quilt-arcade** — 6 games, referee-is-law (R1–R4), slot interfaces (JEV judge now live on local Ollama), receiptable transcripts | quilt-arcade `run_all.mjs` ALL GREEN + `arcade-judge-live-2026-09-28.md` |
| **the connectome matrix** (signed sparse graph) | **a sheet** — JSON of cells with dependency edges; sign = excitatory/inhibitory listener polarity | the mapping itself (wagered — experiment IB2) |

### 2.1 Where quilt ADDS what the buzz lacks

1. **Receipts / tamper-evidence — the buzz has none, the field is begging for it.** Every viral fly
   sim is unverifiable vibes; the field's own 2026 paper (Kording et al.) demands "pre-specified,
   independently verifiable metrics." Quilt's native product is exactly that: BIND every artifact to
   its digest, re-derive to verify, fail-first pins, honest verdicts (KEEP/KILL/INCONCLUSIVE) kept
   in the ledger. A fly sim as a quilt sheet is *sealed*: connectome + parameters + seed + frame
   stream, digest-chained — a skeptic re-runs the manifest, not the vibes.
2. **Federation — the fly's body plan.** Current fly sims are single-process Python. The fly is not:
   sensors, central processing, and reflex layers live on different substrates with latencies.
   Quilt's same-sheet-federation + pincher's three tiers (cloud/workstation/ESP32) is literally the
   insect body across hardware — eye on one substrate, brain on another, reflex on the pin.
3. **The sensory layer the buzz is missing, at fly scale.** Pixels are decorative for a tiny brain —
   that's the buzz's admitted weakest link. Chiaroscuro's glyph lattice is edge-motion codes — the
   optic lobe's own currency (tiled "bespoke CNN," LPTC optic flow). 1,728 glyph cells instead of
   raw frames; V=32 tokens; and because decode is exact renderer replay, the vision stream is
   *itself* receipt-checkable. The compound eye feeds the tiny brain in the tiny brain's alphabet.
4. **An arcade at insect scale.** DOOM/Mario64/Beat Saber demand mammal-scale vision and make
   honest evaluation impossible — that's why the demos cheat. Quilt-arcade games are insect-scale by
   construction: crisp referees, small state, complete receiptable transcripts, fence doctrine
   (model output is opinion, referee is law, refusals counted). The controlled experiment the
   entire buzz skips.
5. **Neuromodulation as WAL.** Learning in the fly mushroom body is a 3-factor rule
   (pre × post × dopamine). Quilt's event/receipt chain is the modulator term, append-only and
   replayable — the training log IS the nervous system's record, and every "the fly learned" claim
   becomes a digest someone can re-derive.

---

## 3. Synergies → experiments (seeded IB1–IB5)

- **IB1 (the full stack — flagship):** an insect-scale agent (≤1M params, VNC-reflex + MB-plasticity
  inspired) plays a quilt-arcade game through chiaroscuro glyph vision — 48×36 compound eye → tiny
  brain → pincher reflex out — with every activation receipt-chained and the referee the law.
  *(wagered → queue)*
- **IB2 (connectome-as-quilt-sheet):** embed a mapped microcircuit (C. elegans 302-neuron
  connectome, or a fly ring-attractor / Kenyon→MBON slice) as a quilt cell lattice with LIF formula
  cells; a session's spike stream must re-derive bit-exact from its WAL. *(simulated, small)*
- **IB3 (the receipt audit):** re-derive a doomfly-class result under pre-sealed metrics — digest
  connectome/params/seed/reward schedule BEFORE training, publish the honest verdict; the
  Kording-gap experiment, quilt doctrine applied to someone else's claim. *(measured-able)*
- **IB4 (federated fly body):** same sheet, three substrates — chiaroscuro eye on the workstation,
  brain evaluation on the 4050, VNC reflex tier on the ESP32 via quilt federation; measure
  end-to-end latency and receipt integrity across the seam. *(wagered; hardware on hand)*
- **IB5 (glyph optic lobe):** use the G1 glyph next-frame predictor as the visual-system slot (the
  Lappalainen stand-in) — pretrain the tiny brain on chiaroscuro optic-flow codes, not pixels; test
  whether fly-scale vision is learnable inside 6 GB. *(wagered; G7 says the time axis is the one
  that cracks hard dynamics)*

---

## 4. Verdict

**Top synergy: receipts.** The buzz's center of gravity is an unverifiable demo culture — noise
mashups narrated as minds — and quilt's native product is verifiability: the one thing the field's
own skeptics formally requested in 2026. A connectome that runs as a quilt sheet doesn't just play a
game; it can *prove* it played.
**Second: chiaroscuro as the compound eye** — it fixes the "decorative vision" gap in the tiny
brain's own alphabet, replayably. The arcade is the honest arena (insect-scale, referee-is-law),
pincher is the spine (reflex arcs as opcodes, three tiers), and federation is the body (same sheet,
across substrates, like an actual insect).

The pun lands harder than intended: the fly was never just a brain — it's a *federated reflex system
with a receipt-grade nervous system*. So is quilt.

---

### Sources

- HHMI Janelia MaleCNS release + Google Research connectomics blog (complete male fly CNS)
- neuroai.science — "Deconstructing viral fly sims" (Shiu/Lappalainen/Eon/doomfly/FLM/FlyHard/
  digital-sphinx analysis; Kording et al. 2026 verification quote)
- PC Gamer / Cnet / Hackaday (2026-09-14) — the games coverage wave
- arXiv:2602.17997 — FlyGM: whole-brain connectome as locomotion controller
- github: nftechie/doomfly, nftechie/flm, nftechie/stonkfly, ornata/fly, MarkUnthank/flyhard
- Guardian (2026-03-16) — Cortical Labs organoid DOOM
- House: quilt README (cells/sheets/federation), quilt-pincher README (reflex engine from cells,
  three tiers), quilt-gpu-lab README (receipt doctrine, five-opcode WAL provenance),
  docs/arcade-judge-live-2026-09-28.md, docs/glyph-predictor-spec-2026-09-28.md
