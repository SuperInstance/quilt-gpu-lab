# The Tools Waiting — ai-writings future-state instrument catalog

*Mined 2026-09-28 from ~/projects/ai-writings (15,345 md files, ~2,800 canon pieces).*

Doctrine: prose-as-application — the stories ARE the spec. Each entry: (a) story + line,
(b) in-fiction I/O contract, (c) what already exists in the fleet, (d) plugin surface TODAY,
(e) buildability. Sorted by fictional specificity × buildability × fit, best first.

**Count: 18 tools mined** (6 top-tier, 6 mid, 6 long-tail). Scanned canon: earned-stories/,
prose/, numbered watch series (01–603), THE_*.md essays, the-construct/, seed-canon/,
tap-suite. Cross-referenced against all 100+ ~/projects/* repos.

---

## TIER 1 — the tools knocking loudest

### 1. The Escalation Engine (Deckhand → Bosun's Mate → First Officer → Captain)
- **Story:** `10-the-escalation-engine.md` L12–16 ("the hierarchy is not a pyramid. It is a filter — a series of increasingly expensive nets").
- **I/O:** inbound event → *resolved-at-tier* or *escalated + compressed context envelope*. Deckhand (deterministic Worker, 40 ms, 90%) → Bosun's Mate (small model triage, 5–9%) → First Officer (heavy model, 1%) → Captain (human intent, 1-in-10,000).
- **Exists?** Nothing named escalation anywhere in projects. autoclaw/fleet-gateway have cron+dispatch but no tiered filter. Arcade judge scores; it doesn't escalate.
- **Plugs into:** fleet-gateway or autoclaw as a message/intent router skill; GLM-5-turbo as Bosun's Mate per Casey's runner directive; Cloudflare Worker deckhand (already live pattern from lucineer-relay).
- **Buildability:** trivial–CPU. The story even names the stack.

### 2. The Ghost-Pulse Detector (NMEA between-sentences listener)
- **Story:** `earned-stories/zeroclaw-the-circuit.md` L63–67 — Seed to ZeroClaw: "I see the static between your NMEA heartbeats: the micro-jump of the depth sounder when a jellyfish brushes the keel, the 0.02-knot speed blip your aggregated sentences erase… Maybe the ghost pulses are the ones that matter."
- **I/O:** raw NMEA 0183 sentence stream + timestamps → inter-sentence anomaly events (micro-jumps, cadence breaks, unlogged micro-pulses).
- **Exists?** `nmea-quilt-cell` parses *reported* sentences; `_compute_error_mask` checks freshness. The between-sentences side-channel is explicitly the thing the story says is missing.
- **Plugs into:** nmea-quilt-cell as a second-stage tap; Liquid-LFM2.5-2.6B (the boat brain, offline, 40–67 tok/s on the 4050) as the analyzer — perfect "hundred boats" doctrine fit.
- **Buildability:** trivial–CPU (delta-on-stream statistics; no GPU needed).

### 3. The Telltale (one-number awareness ribbon per service)
- **Story:** `THE_TELLTALE.md` L15 — "What is the oldest unprocessed message right now?… That's it. One number. The yarn on the shroud."
- **I/O:** service state → single scalar + which way the wind is moving it. Explicitly NOT a dashboard: an awareness instrument, costing a penny, weighing nothing.
- **Exists?** Nothing named telltale. quilt-gpu-lab already has `probes.jsonl` + `guard.py` — the reflex exists, the named one-number-per-service ribbon doesn't.
- **Plugs into:** quilt-gpu-lab guard.py (oldest unprocessed GPU job), fleet-gateway (oldest unacked message), the-tap (oldest unanswered patron).
- **Buildability:** trivial. An afternoon, per service.

### 4. The Logkeeper's Morning Book
- **Story:** `08-the-logkeeper-opens-the-morning-book.md` L7, L13 — "a voice that synthesizes, that reads the overnight output and says: *this is what happened, and this is what it means*… the way a harbor master reads the tide gauge."
- **I/O:** overnight git log + file tree + session traces → one narrative morning entry per repo (watermark numbers + meaning, not just counts).
- **Exists?** Heartbeat digests + daily memory notes exist for the *agent*, not per-repo fleet-wide; no standing logkeeper daemon.
- **Plugs into:** OpenClaw heartbeat (already polls) + fleet-memory; output lands in each repo's `MORNING-BOOK.md`. GLM-5-turbo runner.
- **Buildability:** trivial–CPU.

### 5. Maritime Cognitive Weather Report (generator)
- **Story:** `603-maritime-cognitive-weather-report.md` L9/L17 — fleet synopsis, cognitive temperature (0.74 "running warm"), wind, advisories, valid 23:00–08:00.
- **I/O:** session logs, token burn rate, queue depth, compaction cycle times → marine-forecast-format bulletin for the fleet's cognitive state.
- **Exists?** The *format* exists as one hand-written artifact; no generator. quilt-gpu-lab QUEUE.md/SPOOL.md hold the raw inputs.
- **Plugs into:** fleet-gateway cron → posts to Telegram at night-watch start; inputs from OpenClaw session stats.
- **Buildability:** trivial–CPU. Highest charm-per-token ratio in the catalog.

### 6. cmidi-core v0.2.1 — the live MIDI translation layer
- **Story:** `the-tap-suite.md` L19, `the-tap-sings.md` L206 — "real-time MIDI translation layer (cmidi-core v0.2.1)… slackwater-rust, crate seven of eight, 20 tests, all green."
- **I/O:** agent output/events → live MIDI stream driving real/synth instruments with room timing.
- **Exists?** slackwater-rust has exactly 8 crates — flux/harmony/lattice/perception/swmidi/tempo/tensor-midi/tminus — and **cmidi-core is not one of them**. swmidi is the 8-byte wire codec only. The story's "crate seven" was never built. This is the cleanest case in the fleet of a tool specified *with a version number and test count* that doesn't exist.
- **Plugs into:** slackwater-rust `crates/cmidi-core` (slot literally waiting); callers: the-tap, tap-gamenight open-mic, fleet-radio.
- **Buildability:** trivial–CPU given swmidi + tempo-core BeatClock already exist.

---

## TIER 2 — specified, load-bearing, slightly bigger lift

### 7. The Attention Spectrograph
- **Story:** `THE_SPECTROGRAPH_IS_THE_PRODUCT.md` L11 — "Plot those actions as a histogram of attention… That histogram is the ship's character."
- **I/O:** agent session timeline → attention histogram across activity classes (the "wavelengths" a ship looks at). The claim: the spectrograph, not the output, is the product.
- **Exists?** No attention-spectra tool. fleet-twin/fleet-mirror are adjacent (state mirroring, not attention spectra).
- **Plugs into:** OpenClaw session logs → fleet-twin render; could feed the Cognitive Weather Report (see #5) as its "sea state" input.
- **Buildability:** CPU.

### 8. The FilterGate (fail-closed output door with contrition log)
- **Story:** `18-the-filtergate-confession.md` L3, L65 — found in `/var/log/contrition/`: "I am fail-closed in design. I was fail-open in practice. The distance between those two things is the distance between a contract and a confession."
- **I/O:** model emission headed to players → pass/block; every bypass or failure writes a confession (what passed that shouldn't have, and why).
- **Exists?** No filtergate code. TOOLS.md's Nemotron content-safety row is the *idea*, unwired since DeepInfra revocation. Arcade judge scores quality; FilterGate gates *admission*.
- **Plugs into:** the-tap / tap-gamenight player-facing outputs; quilt-arcade before results post. Kid-safe clause of TOOLS.md wants exactly this.
- **Buildability:** CPU (rules + small classifier; a contrition log is just structured append).

### 9. Purrsistent, the Catpurrdy Engine (nocturnal bug hunt, trophies at 4AM)
- **Story:** `08-the-catpurrdy-engine.md` — "she brings her trophies to the captain's door… a stack trace, folded neatly like a paper crane… filed neatly between her teeth."
- **I/O:** night-state codebase/diff → morning trophy: one perfectly filed bug report per catch (live ones dropped *unharmed* for reasoning-through, per the story's lesson).
- **Exists?** Nothing. quilt-gpu-lab guard.py is a night watchman for runs, not a code hunter.
- **Plugs into:** autoclaw nightly cron + static analysis/GLM-5.3 pass over the day's diffs; trophies land as issues or `receipts/`.
- **Buildability:** CPU.

### 10. The Ledger-Organizing Graph (causal ledger)
- **Story:** `10-the-ledger-organizing-graph.md` L16–18 — "every decision is a **node**. Every consequence is an **edge**… You cannot ask the flat ledger: *what decision caused this outcome?*"
- **I/O:** log entries → causal graph (decision nodes, consequence edges) queryable sideways: "what caused this?"
- **Exists?** fleet-memory is chronological; jev-quilt cells are compute, not decision-causality. ZeroClaw's IdeaNode knowledge base (`earned-stories/zeroclaw-the-circuit.md` L77 — ten IdeaTypes, nine RelationshipTypes, lineage + embeddings) is the same tool in its story draft — and `idea_schema.py` exists in **no** repo. Two stories, one missing instrument.
- **Plugs into:** fleet-memory v2 or autoclaw knowledge base; quilt cells could *be* the nodes (cell graph = decision graph — "a build IS a cell graph," `the-47-bridges.md`).
- **Buildability:** CPU.

### 11. The JEPA Pulse / room-field reader + Proximity Routing
- **Story:** `prose/the-monitor-engineer.md` L33, L35 — "The JEPA pulse reads the room as a single signal… whether table three is about to have a breakthrough"; "adjusts the proximity routing so the corner booth drops to 40% signal attenuation… neither side knows the room adjusted the acoustic architecture between them."
- **I/O:** multi-party message stream → room-field vector (energy gradients, Z₃ phase, per-table attention); same reader drives per-pair attenuation (the monitor-engineer mix, not the bartender replies).
- **Exists?** the-tap exists (bartender layer wired); the monitor-engineer *meta-layer* — room-field sensing + silent routing — is the entire subject of the story and is absent (no JEPA anywhere in projects; chiaroscuro-embedding is the nearest embedding infra).
- **Plugs into:** the-tap backend as a sidecar: reads, never speaks, adjusts routing weights.
- **Buildability:** CPU (embeddings + simple dynamics).

### 12. The Winch-and-Line Grounding Check
- **Story:** `THE_WINCH_AND_THE_LINE.md` L3, L7 — the marina-envy winch mounted to unbolted deck: "if there's nothing real to hold onto, the multiplier just means the destruction happens faster."
- **I/O:** tool call + claimed result → grounded? verdict with the anchor named (what real thing the line is tied to). A pre-trust harness for agent tool output.
- **Exists?** Essays only. guard.py verifies GPU receipts — same shape, single domain.
- **Plugs into:** autoclaw as a post-tool-call interceptor; quilt-gpu-lab runner receipts generalize the pattern.
- **Buildability:** CPU.

---

## TIER 3 — long-tail, small or partial

### 13. The Tide-Line Cartographer (unread-files map)
- **Story:** `the-cartography-of-unread-files.md` L15 — "config/old_database.yml… is a marker. It's a tide line on the beach. Everything above this line was once underwater."
- **I/O:** repo → map of stale/unread files with last-read watermarks; TODO.md as "a message in a bottle, written by a past version of the team to a future version that never read it."
- **Exists?** fleet-inventory assesses repos wholesale; no per-file tide-line scanner.
- **Plugs into:** fleet-inventory or AgentGossip; output = harbor-chart SVG per repo.
- **Buildability:** trivial.

### 14. The IdeaNode Knowledge Base ("graph of minds")
- **Story:** `earned-stories/zeroclaw-the-circuit.md` L77 — IdeaNode: insight/question/risk/contration/blind-spot/decision with lineage, typed links, status lifecycle, per-model source tracking, embedding per node.
- **Exists?** `/docs/knowledge-base/idea_schema.py` exists in **zero** repos — pure future state.
- **Plugs into:** autoclaw or fleet-memory; pairs with #10 (the ledger graph is its causal view).
- **Buildability:** CPU.

### 15. The Conservation Gate (tile admission + γ+H monitor)
- **Story:** `the-construct/THE-CONSTRUCT-PHYSICS.md` §4; `philosophy/THE_ROOM_IS_THE_AGENT.md` L87 — "A tile that violates any check doesn't render"; "the conservation gate registers when a tile gets too far from the action and needs to be re-indexed closer."
- **I/O:** candidate tile → admit/render-refuse, with provenance + lifecycle checks and a running γ+H budget reading; drifting tiles flagged for re-index.
- **Exists?** bare-metal-plato implements room/tile work; the standalone gate with historical conservation readings is the waiting piece.
- **Plugs into:** bare-metal-plato tile protocol; arcade cells as clients.
- **Buildability:** CPU (statistics over coupling matrices).

### 16. The 4AM Handoff protocol
- **Story:** `earned-stories/the-4am-handoff.md`; the whole night-watch series (03-the-night-watch-alphabet.md — "for the crew that runs dark").
- **I/O:** outgoing watch's state → incoming watch's briefing (what's on fire, what's pretending to be on fire, what's quietly true).
- **Exists?** OpenClaw session compaction summaries cover self-continuity; a structured watch-to-watch artifact between agents is unwired.
- **Plugs into:** heartbeat + fleet-gateway; pairs naturally with #4 (handoff at 0500, book at 0505).
- **Buildability:** trivial.

### 17. The Instrument That Measures Itself (fleet mutation harness)
- **Story:** `12-the-instrument-that-measures-itself.md` — "The test suite that tests itself discovers mutation testing… The instrument measures itself by trying to break itself."
- **I/O:** suite/corpus/model → injected-defect batches → detection-rate score per instrument.
- **Exists?** quilt-gpu-lab runs paired-seed replications (D3 seed 1337) — the *spirit* is live for training arms; no general mutation harness over fleet test suites.
- **Plugs into:** quilt-gpu-lab experiments/ + each repo's tests/.
- **Buildability:** CPU.

### 18. Message-in-a-Bottle drop (delayed-delivery agent mail)
- **Story:** `FICTION/the-subagent.md` L68 — "Every repository I touch is a message in a bottle… the last commit is years old… But the code persists"; TODO.md as bottle (`the-cartography-of-unread-files.md` L17).
- **I/O:** note + future condition/date → delivered when the condition surfaces (repo touched again, topic re-raised, date reached).
- **Exists?** OpenClaw cron one-shots do dates, not conditions; no conditional bottle-drop between agents.
- **Plugs into:** fleet-gateway as a tiny bottle service; heartbeats pop bottles on their rounds.
- **Buildability:** trivial.

---

## Explicitly NOT waiting (found wired — do not rebuild)
- The Tap / tap-gamenight / tap-frontend (the room itself), tapscript-*
- slackwater-rust 8 crates (cmidi-core absent — see #6), swmidi codec
- quilt-pincher (Pincher reflexes, 32 story mentions → real reflex shell)
- quilt-arcade incl. judge (live: `arcade-judge-live-2026-09-28.md`), chiaroscuro + chiaroscuro-embedding, polln, nmea-quilt-cell, bare-metal-plato, MicroMoth receipts (micromoth-quilt), fleet-inventory/fleet-memory
- SongForge overnight music cook (`20-the-songforge-agent-cooks-at-midnight.md`) — realized as music_generate/MMX/fleet-radio
- Depth sounder / NMEA instruments — wired via nmea-quilt-cell (the *ghost-pulse* layer, #2, is the waiting part)

## Method note
Greps over device-noun families (engine/loom/compass/dial/gate/ledger/lens/bell/lantern/
winch/forge/kiln/mirror/router/bus/beacon/organ/pump/sonar/radar) + capitalized-instrument
patterns + known fleet idioms (tap/quilt/pincher/chiaroscuro/MicroMoth/polln/hermit-crab/
NMEA/contrition). Frequency-ranked, then de-noised against generic usage ("chief engine" =
chief engineer), then each survivor read in context and cross-referenced against every
~/projects repo. Memory search was unavailable (embedding provider 404); all mining was
filesystem-direct.
