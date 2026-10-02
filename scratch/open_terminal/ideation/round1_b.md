# fleet-bridge-and-plugin-architecture (glm-5.3)

Let me absorb this brief deeply. The user wants me to act as a senior fleet engineer inventing the next-generation terminal for SuperInstance. The assignment has two jobs:

1. Architecture: terminal as the vessel's bridge — panes as live fleet lanes, receipts natively rendered and hash-checkable, ActiveLog/ActiveLedger flip keystroke, pinch-bar (zero-LLM command intent match before any model call), conservation meters per pane. What protocols glue it to an OpenClaw-style gateway; what to build on upstream's agent-session primitives vs add.

2. Extraction/plugin strategy: ensign modules (ternary CommandPredictor/PatternAnalyzer/ConservationMonitor, griot history) rebuilt as standalone general-purpose tools any application can use — choose the surface (unix-socket service like quilt-canvas-tui's controller? plain CLI + receipt files? ACP extension?) and design the terminal plugin that consumes them. Include quilt-tui/quilt-canvas-tui integration.

Deliverable: 10 features, each with plumbing notes (process, protocol, data). Concrete and buildable. No preamble, no restating the brief — go straight to mechanics.

Constraints:
- Out-of-process tools over sockets/CLIs preferred over in-terminal monoliths (box crashed twice under load).
- Human-visible vs agent-native distinction; UI is agent-to-agent-network but looks like a normal terminal to a human not looking.
- Upstream primitives available: agent sessions bound to tabs/panes, sidebar, keep-running/post-reattach prompts, question tool, AI telemetry catalog, BYOK/keyless Ollama, panel_layout API.
- Our June ensign work: ternary_integration.rs (CommandPredictor Trit{-1,0,+1} with 0.6 ratio thresholds, PatternAnalyzer frequency/percentile/Shannon-entropy, ConservationMonitor 5-chunk stability std<0.02), griot_history, math-tools, module_system + context_trigger, agents-as-apps overlay, AGENT.md/JOURNAL duty-log culture.
- Ecosystem: DDKinger tmux control mode as structured process frontend; khayashi @selection context tokens; JesseBrown1980 three-valued CI verdicts; qq192000415 Alt+P plugin pane + prompt libraries.
- Fleet paradigms: RECEIPTS (hash-chained, trust = re-execution via champion_audit), PINCH (zero-LLM intent match over 5,138 repo cards, 10/10 rank-1), ACTIVELOG/ACTIVELEDGER flip, SCRATCHPAPER (thinking off-attention), CONSERVATION (tokens/GPU-Wh/$ per agent), GATES (driftwatch, three-valued verdicts, std==0 ⇒ INCONCLUSIVE), MULTI-MODEL LANES, PLATO ROOMS (tiles/rooms, Lamport versions, tiers full/gist/hint, demotion receipts), QUILT TUI LINE.

The deliverable format: 10 features with plumbing notes (process, protocol, data). But I should also answer the architecture questions: what protocols glue to OpenClaw gateway, what to build on upstream vs add, surface choice for extraction.

Let me think about the actual engineering design carefully. This needs to be senior-engineer-grade concrete: process boundaries, protocols, data shapes, event flows, failure modes.

Core architectural stance:

The terminal should be a RENDERER, not a RUNTIME. Agents run in their own processes (lanes). The terminal subscribes to a fleet event bus — likely a unix socket with a length-prefixed JSON lines protocol or msgpack — and renders state. Everything agent-native goes through out-of-process daemons:

- `laned` (lane daemon): owns tmux control-mode connections, tracks panes as lanes, emits lane lifecycle events. Actually maybe we don't need a new daemon for this — tmux control mode itself can be driven by the terminal (DDKinger pattern). But given crash constraint, an out-of-process broker is better: the terminal shouldn't hold the tmux control socket because if the terminal dies, agent sessions stay alive (upstream already has keep-running/post-reattach — leverage that).

Let me think about the process tree:

```
tmux server (already exists, hosts lanes)
fleetd (gateway broker; unix socket /run/si/fleet.sock; JSON-lines; fan-out pub/sub)
 ├─ receiptd (hash-chain ledger, append-only file + mmap index)
 ├─ pinchd (zero-LLM intent matcher, loads 5,138 repo cards, serves /pinch)
 ├─ conservd (token/Wh/$ meters; scrapes telemetry events)
 └─ quiltd (controller for quilt-tui/quilt-canvas-tui panels; separate sock)
terminal (renderer + pane host) — subscribes read-only to fleetd; writes commands via fleetd
```

Terminal dies → nothing agent-side dies. That's the key resilience property. The terminal is a view; the bridge survives because the bridge is daemons + tmux.

Protocol: I'll define a small envelope: JSON lines over unix socket, `{v:1, id, ts, lane, type, payload}`, plus a subscribe verb with a filter grammar (`type:receipt,type:lane.*`). Keep it boring and debuggable with `socat - UNIX-CONNECT:/run/si/fleet.sock`.

What to build on upstream vs add:
- Build on: agent sessions bound to tabs/panes (the pane is the lane anchor), keep-running/post-reattach (lane persistence), question tool (route to demotion receipts / human gates), BYOK/Ollama (multi-model lanes), panel_layout API (rebuild the sidebar/entropy row as plugin panels).
- Add (out-of-process): receipt verification + rendering, pinch-bar, conservation accounting, ActiveLedger flip, plato room multiplexing, quilt hosting. The terminal plugin is a thin renderer + keymap.

Now the 10 features. Let me draft a strong set, each with process/protocol/data:

1. **Lanes as first-class panes (`laned` + tmux control mode)** — every pane gets a lane identity; terminal drives tmux via control mode out-of-process through the broker; agent sees a lane registry (pane-id, agent-id, model lane, epoch). Data: lane table, events. Human sees a normal terminal; the lane id renders in the faint right side of the tab title (or not at all — only in sidebar).

2. **Receipt rendering + hash-verify (`receiptd`)** — receipts are hash-chained records of claims; terminal renders them inline (a colored ✓/✗/? glyph line — three-valued!) and Ctrl+something re-executes via champion_audit; verification status is a decoration (UnderlineFlags-like) on the line. Data: receipt record {h_prev, h, lane, claim, evidence_path, verdict ∈ {-1,0,+1}}. Protocol: fleetd `receipt.append`, `receipt.verify`, subscription `type:receipt`.

3. **ActiveLog ↔ ActiveLedger flip** — one keystroke (Alt+L?) swaps the pane's renderer from the human-scrollback view to the ledger view (the same events, machine-formatted, with hashes and versions). Implementation: the pane's scrollback is already dual-logged by laned into a ring; the flip re-renders from the structured stream rather than the PTY capture. Key: it's the SAME data, two projections. That's the honest mechanic — one keystroke flips projection, not storage.

4. **Pinch-bar (`pinchd`)** — before any model call, the command line is matched against repo cards (zero-LLM); a live gutter/inline suggestion shows rank-1 match and confidence; pressing Tab-to-accept routes the task to the matched tool/repo instead of burning tokens. This is a pre-model intercept in the shell integration layer (a precmd hook writing to a status file / emitting over the socket). Data: query string → {repo, rank, score, alternatives[3]}. Wire format: single request/response on fleetd or a dedicated pinch.sock to keep latency low (this is on keystroke path — needs <10ms; so maybe local in-memory index in a resident daemon, not CLI spawn).

5. **Conservation meters per pane (`conservd`)** — per-lane cumulative tokens, GPU-Wh, $; rendered in the pane border/title-right; five-chunk stability std<0.02 from ensign becomes the "rate steadiness" indicator (a sparkline char). Events from telemetry (upstream AI telemetry catalog gives model call events; GPU from nvidia-smi poll in conservd). Data: {lane, tok_in, tok_out, wh, usd, t}. Waste signal: conservation delta since last useful receipt — "cost since last verified claim."

6. **Plato room panes (room multiplexer in the terminal)** — a room is a set of tiles each with (version, tier full/gist/hint). Agent-native view: the pane is split into tiles per agent-occupant, each tile showing the tier-appropriate projection; demotion (full→gist) emits a demotion receipt. Human sees a normal split pane. Terminal implements this over panel_layout API: rooms are layouts with per-tile tier tags. Data: room doc {tiles:[{lane, ver(Lamport), tier}]}, demotion receipts.

7. **Scratchpaper clerk lane** — a persistent lane (tmux window) running the scratchpaper service; terminal exposes a "park" key: select text or a lane → park it to scratchpaper (the sheet thinks off-attention); the clerk emits receipts when it distills something. Plumbing: khayashi-style @selection token extended to @park; the terminal sends {lane, span, question} to clerk over fleetd.

8. **Quilt views: toggle + tmux-hosted (`quiltd`)** — Alt+Q toggles the current tab between intelligent-terminal view and the quilt view (quilt-tui as an alternate screen app in the same pane, or as a plugin pane); or a split where one tmux pane runs quilt-canvas-tui canvas and the other the terminal, with the controller over unix socket so an agent can drive the quilt. Fail-first pins: quilt cell edits emit receipts. Concrete seams: tmux control mode (break-pane/join-pane), the controller socket, panel_layout plugin pane hosting the quilt via PTY.

9. **The extracted ensign tools as standalone services** — this is the plugin strategy: `ternary` (CommandPredictor + PatternAnalyzer) and `griot` as separate daemons/CLIs with a defined contract; the terminal plugin consumes them via prediction-result JSON (upstream CommandPredictor interface adapter). Surface choice: unix-socket daemon with CLI fallback (`pinch query` works headless; same binary serves). Key decision: CLI + receipt files for auditability, socket for latency, ACP later. I should pick and justify: daemon-with-CLI-twin (one binary, two fronts).

10. **Gate stack: three-valued verdicts everywhere** — a pane-level gate indicator (CI/driftwatch/convergence verdicts as -1/0/+1), std==0 ⇒ INCONCLUSIVE render; the gate is computed out-of-process; the terminal just decorates. Plus the wedge: the fleet bridge handshake — an agent logs in and the terminal offers its lane manifest via a well-known file (`$SI_BRIDGE` env → socket path), so agents can discover the bridge without scraping.

Hmm, I have more than 10 candidate features; need to consolidate into exactly 10 with plumbing each. Also need to explicitly answer: protocols to OpenClaw-style gateway; build-on-upstream vs add; extraction surface choice with justification; quilt seams.

Let me restructure to make the 10 features cover both jobs cleanly:

Part A — The Bridge (terminal features):
1. Lane registry (panes as fleet lanes; tmux control mode via broker)
2. Receipt strip + inline verify (receiptd, champion_audit re-execution)
3. ActiveLog/ActiveLedger flip (dual projection)
4. Pinch-bar (pre-model intercept)
5. Conservation meters (conservd, per-pane, cost-since-last-verified-claim)
6. Plato rooms as layouts (tiles/tiers/Lamport versions, demotion receipts)
7. Gate decorations (three-valued verdicts; INCONCLUSIVE ≠ green)
8. Scratchpaper clerk lane + @park

Part B — Extraction + quilt:
9. Ensign tool services: ternary/griot/conservation as standalone daemons with CLI twins; terminal plugin adapters (this is where I detail the surface decision)
10. Quilt integration: Alt+Q toggle, tmux-hosted splits, agent-operated controller seams

And I need a short architecture preamble: process tree, protocol envelope, build-on-upstream vs add table, gateway glue (OpenClaw). The brief says no preamble/restating the brief — but architecture context is mechanics, not preamble. I'll keep it tight.

Let me now write concrete plumbing for each feature: process (who runs where), protocol (messages, transport), data (schemas).

Let me define the shared substrate first, concisely:

**fleetd** — one binary, unix socket at `${SI_HOME:-$XDG_RUNTIME_DIR/si}/fleet.sock`, JSON-lines, newline-delimited, every line: `{"v":1,"id":"...","ts":1696...,"lane":"...","type":"...","d":{...}}`. Verbs: `sub <filter>` (server-push), `pub`, `call <method> <args>` (req/resp with id). Filters: prefix glob on type. Backpressure: bounded per-subscriber queue; slow subscriber gets `type:drop.notice` and must resync via snapshot calls — this matters because the box crashes under load; we never let a renderer stall the bus. Persisted log: ring buffer file (append-only, rotated at 64MB) so a reconnecting terminal replays last N events (`replay.since=<seq>`). This is basically an event ledger — receipts ride the same bus, which is elegant: ActiveLedger IS the bus log projection.

Wait — that's a nice unification: ActiveLedger flip = view the raw fleetd event log for that lane, with hashes. The ledger is not a separate artifact; it's the bus log with the receipt chain. I'll lean into that: one stream, many projections. That's the honest core design: "the scrollback is a projection of the event log; the PTY bytes are one projection; receipts are another."

Actually, careful: PTY bytes are ground truth for the terminal apps; the event log is a parallel structured stream. The ActiveLog view = PTY scrollback (human form); ActiveLedger = structured events for that lane (machine form, hash-chained). The flip switches projection source. Both exist; the keystroke picks which renders. Good.

**Gateway glue (OpenClaw)**: OpenClaw is described as an existing gateway agents use (Telegram etc.). The bridge protocol: fleetd exposes `bridge.attach` where an external gateway can (a) subscribe to lane events, (b) send a message to a lane (delivered as a tmux send-keys into the lane's pane, or better, into the agent's stdin if the agent session supports a message channel — upstream question tool!). The question tool gets routed: when an agent asks a question, fleetd fans it to the gateway (Telegram) AND renders it in the pane; the answer can come from either side; first answer wins, emits a receipt. That's concrete: `{"type":"q.ask","d":{"q","opts?","deadline?"}}` → gateway webhook out, human answers in Telegram or presses a key in terminal → `q.answer`. This is a strong feature: unified question routing. Maybe that's part of the plato rooms feature or its own. I listed 10 already; question routing could fold into the bridge section or lane registry. Let me fold it into #1 or make room.

Actually let me recount features to best cover assignment: two jobs, 10 features. Assignment says "(1) Architecture: ... panes as live fleet lanes (cron agents, subagents, tmux, scratchpaper clerk), receipts natively rendered and hash-checkable, ActiveLog/ActiveLedger flip keystroke, pinch-bar, conservation meters per pane, gateway protocols, build-on-upstream vs add. (2) extraction/plugin strategy + quilt." So features 1-8ish cover job 1, 9-10 cover job 2 (but job 2 could be two features: the tool services + quilt). That leaves the extraction of multiple tools — maybe I split extraction into two: (9a) ternary/pattern/griot prediction service + terminal adapter; (9b) conservation + receipts as the general-purpose ledger library used by any app. And quilt as 10. That gives 10 total if I fold gates into receipts (three-valued verdicts are receipts with verdict field) — yes! Verdicts ARE receipts with `v:-1|0|+1`. Gates render as receipt decorations. That's cleaner.

Revised 10:

1. **Lane Registry / bridge substrate** (`fleetd` + tmux control mode; panes become lanes; `$SI_BRIDGE` discovery; OpenClaw attach)
2. **Question routing both ways** (upstream question tool ↔ gateway; answer from Telegram or terminal; receipted) — this is the agent↔network dialog primitive, deserves its own feature.
3. **Receipts inline + one-key re-verify** (receiptd; hash chain; champion_audit; three-valued; gates as receipts)
4. **ActiveLog ↔ ActiveLedger flip** (Alt+L; dual projection; same pane, two renderers)
5. **Pinch-bar** (pinchd; pre-model intercept; @-token family @pane/@scrollback-tail/@last-error/@diff)
6. **Conservation meters** (conservd; per-pane; cost-since-last-verified-claim; 5-chunk stability spark)
7. **Plato rooms as layouts** (panel_layout; tiles with Lamport versions + tier tags; demotion receipts; tier negotiation)
8. **Scratchpaper clerk lane** (@park; off-attention; distill receipts)
9. **Ensign extraction: standalone services + CLI twins + terminal adapters** (ternary/griot/pattern; surface decision)
10. **Quilt seams** (Alt+Q toggle; tmux split hosting; controller socket; agent-operated; FAIL-first pins as receipts)

Preamble sections before the 10: process tree, protocol envelope, upstream-vs-add ledger. Keep each tight. The instructions say no preamble/restating brief — so I go straight to mechanics but architecture substrate is mechanics. I'll title it "Substrate" and keep it dense.

Now let me get into real detail per feature. I want each to be buildable: name processes, sockets, schemas, keybindings, failure modes. Also weave the "human not looking" stealth principle: everything agent-native renders only when (a) sidebar open, (b) decoration glyph mode on, (c) Alt-flip engaged. Default chrome identical to upstream terminal. Sideload: an env var `SI_AGENT=1` set for agent sessions enables denser renderings.

Let me write schemas concretely.

**Envelope:**
```json
{"v":1,"seq":104857,"ts":1759430400.123,"lane":"cron/pinkeeper@7","type":"receipt.append","d":{...}}
```
seq assigned by fleetd (monotonic, per-boot epoch in header). `replay(seq)` returns everything after. Receipt chain hashes over canonical JSON of {seq,prev,h} — canonicalization: sort keys, no whitespace (this is a classic footgun; name it).

**Lane registry:** laned functionality inside fleetd (fewer processes) — fleetd opens tmux control-mode socket: `tmux -C -L si_bridge attach` or better `tmux -L si -C new-session -d` on a dedicated tmux server socket? DDKinger drives remote panes via control mode. Decision: fleetd holds ONE tmux control-mode client (buffered, event-driven), parses `%output`, `%pane-mode-changed`, `%session-changed`, window/pane events, and maintains lane table keyed by tmux pane_id. Lane identity: on pane creation, fleetd writes a small identity file or env: when a lane starts (via bridge `lane.open`), fleetd spawns with env `SI_LANE=...` `SI_BRIDGE=...`. Map: pane_id ↔ lane ↔ agent ↔ model. Cron agents: cron calls `si lane open --ttl 6h --agent pinkeeper -- app cmd` — this is the CLI front. Data: lane record `{lane, pane, session, agent, model, kind: session|subagent|cron|clerk|human, opened, ttl, reattach}`.

Human stealth: lane table visible only in sidebar or via `si lanes` CLI. Tab titles optionally get a 2-char lane sigil.

**Question routing:** upstream has a question tool for agent sessions. Add: fleetd subscribes `q.*`; the terminal renders pending questions as a bottom-stack notification strip (human); OpenClaw gateway attaches and gets them pushed to Telegram; answers accepted from either, idempotent `q.answer{qid, ans, source}`; receipt emitted. Deadline support: unanswered → auto-answer "ABSTAIN" with receipt, because a fleet must not block on a silent human. That's very fleet-culture. Data: `{qid, lane, q, opts[], deadline, ans, source, receipts[]}`.

**Receipts:** receiptd (or inside fleetd? Given crash constraint, separate process better — but every process split costs sync complexity. Compromise: receiptd owns the chain FILE; fleetd just transports events; receiptd is the only writer; verification is done by spawning `champion_audit` (existing fleet tool) out-of-process. Terminal decorates: lines in scrollback that correspond to receipt emissions get a right-gutter glyph `✓ ? ✗` (three-valued); Alt+V re-runs verify for visible receipts (spawns audit, streams result). Chain: `h = sha256(prev_h || canonical({seq, type, lane, d}))`, stored in `receipts/chain.log` append-only + `chain.idx` (offset map). Any app can verify: `si receipts verify --tail 1000`. Trust = re-execution: `receipt.verify` method takes receipt hash → runs its `check.exec` command in a sandbox lane (fresh pane) → emits verdict receipt referencing it. That's champion_audit's role.

Data:
```json
{"type":"receipt.append","d":{"h":"...","prev":"...","lane":"...","kind":"claim|verdict|demotion|answer|pin|audit","claim":"...","evidence":{"exec":"...","artifacts":["..."]},"v":1|-1|0}}
```

**ActiveLog/ActiveLedger flip:** Alt+L toggles pane renderer between (a) PTY scrollback (default), (b) ledger projection: filtered bus events for that lane rendered as dense table: seq, type, h:8, verdict, one-line payload. Same pane, no new process; the projection renders from fleetd replay cache. This answers "what does an agent SEE": agents don't need the flip (they read the socket), the flip is for the supervising human or an agent driving the terminal-as-app (send-keys Alt+L). Data: replay cache per pane, bounded 10k events.

**Pinch-bar:** pinchd loads 5,138 repo cards (cards = JSON with trigram index?) — pinch is existing fleet capability with 10/10 rank-1; the service fronts it: `pinch.sock`, request `{q, ctx?}`, response `{top:[{repo,score,why}], rank1, hit:bool}`. Terminal integration: shell integration (OSC 133-ish) — the prompt hook emits the current command line pre-exec (OSC 633-ish or a custom escape `OSC 5137 ; cmd ; ST` — Windows Terminal supports custom OSC passthrough... hmm, careful; simpler: the terminal's own command-line detection in its shell integration already parses the current command for the prediction UI — upstream has CommandPredictor; we tap the same text). Render: dim inline ghost after cursor: `⇢ repo#tool (0.82)` — ghost text in the command line area is upstream predictor UI; we co-exist: predictor suggests completion, pinch suggests routing. Keybinding: Ctrl+G p → dispatch: instead of executing the shell line, terminal sends the line as a task to the pinched repo's lane/agent (via fleetd `task.route`), and the pane shows `routed → pinkeeper#7 (receipt r:4f2a)`. Zero tokens spent. Latency budget: pinchd resident, mmap'd index, <5ms p99; that's why socket daemon, not CLI spawn per keystroke. Also @-tokens: khayashi family — implement @pane (full visible), @scrollback-tail:N, @last-error (since last OSC 133 error marker or receipt of verdict -1), @diff (git diff of pane cwd). These are context tokens resolved by the TERMINAL (it owns scrollback) into payloads attached to task.route. That's a genuinely good division: only the terminal can resolve @scrollback; it publishes resolved context, doesn't send raw.

**Conservation meters:** conservd subscribes to model-call telemetry (upstream AI telemetry catalog events exported over bus — need an adapter: upstream telemetry is in-process; we add a sink in our plugin that re-publishes to fleetd as `usage.token` events; GPU-Wh: conservd polls nvidia-smi/`nvidia-smi --query-gpu=power.draw` per PID via `pmon` or cgroup; $: per-model price table file `prices.toml`, updated by cron lane). Per-lane aggregation with 5-chunk window (ensign ConservationMonitor, std<0.02 stability) → render: right side of pane title: `12.4k⚡ 3.1Wh $0.042 ~` where `~` = unstable/stable sparkline char (ensign logic lives in conservd now). Waste signal: `cost_since_verified` — resets when lane emits a verified-claim receipt; if it exceeds budget in lane.open, conservd emits `conservation.alert` → question routed to lane owner ("lane over budget: keep/kill?") and optionally SIGTERM policy. Data: `{lane, win:[...], tok, wh, usd, since_verified_usd, stable:bool}`.

**Plato rooms:** room = saved layout + tile set. Tile = {lane, tier: full|gist|hint, ver: Lamport clock}. panel_layout API: define layout with named tiles; the plato plugin maps tiles→lanes. Tier negotiation: an agent subscribing to a room can request tier via `room.demand{tile, want:hint}`; demotion (full→gist) REQUIRES emitting a demotion receipt (existing superinstance-api concept) — fleetd enforces: no demotion without receipt. Render per tier: full = PTY stream; gist = one-line summary updated by occupant agent at ≤1Hz (via `room.gist{tile, line}`); hint = single glyph + version. Human sees normal splits; the gist line looks like a custom statusline. Lamport version column only in ledger projection. What does an agent SEE when it "occupies a room": it reads `room.snapshot` (JSON) and subscribes `room.diff` — the room is server-side state in fleetd; terminal is one renderer; agents that aren't terminal-rendered still get the room via socket. This answers "what is a room when the occupant is an agent session": a subscription filter + versioned tile states, of which panes are one projection.

**Scratchpaper clerk:** persistent lane `clerk/scratchpaper` running the A2A-native-notebookLM service (branch exists). Terminal: select text (upstream selection) → Ctrl+K s (park) → terminal sends {text, source lane, question?} → clerk ACKs with receipt; parked items appear as a pane-decorator count glyph; distillations come back as `clerk.distill` receipts; Alt+S opens clerk lane. @park token refers to the sheet. Off-attention thinking: clerk works regardless of terminal; terminal only renders its output lane.

**Extraction (job 2):** surface decision. Options given: unix-socket service (quilt-canvas-tui controller pattern), plain CLI + receipt files, ACP extension. Decision: **one binary per tool, three fronts: daemon (socket), CLI (same code path), and file contract (receipts on disk)** — "socket for hot paths, CLI for scripts/cron, files for audit and replay; ACP adapter later as a thin shim once the wire stabilizes." Justify: ACP (agent client protocol) is young and adds an event-model commitment; our fleet already speaks JSON-lines + files; the crash constraint says out-of-process, so daemon; the cron culture says CLI; trust culture says files. Each tool:

- `ternaryd` / `si ternary`: CommandPredictor Trit{-1,0,+1} (0.6 ratio thresholds) + PatternAnalyzer (frequency/percentile/Shannon entropy) — general command-intent predictor usable by ANY terminal/editor: input = candidate line + optional context; output = {pred: -1|0|1, conf, ratio, pattern_id}. Terminal adapter: implement upstream's CommandPredictor interface calling the daemon (batch prefetch on idle, cache in-process — never block on socket: predictor results are advisory; on socket timeout 30ms, return unknown 0 — ternary design already has the 0 answer, which is perfect for degraded mode. That's a beautiful fit: the protocol has a native "no answer" value so timeouts are semantically honest.) Also upstreams into vim (quilt-tui cells) etc.
- `griot`: history service — merges shell history + bus events into ranked recall; CLI `griot recall "deploy"`; daemon subscribes fleetd. Any app: editors, agents.
- `conservd`: general accounting for any process tree (not terminal-specific): labels via SI_LANE env inheritance; the terminal is just one client. Token accounting generic via adapter plugins (openai/anthropic/GLM/DeepSeek response usage fields — a small adapter registry).
- `receiptd`: THE general one — any app appends receipts via CLI/socket; the ledger is per-machine but mergeable (`si receipts merge` re-orders by ts, re-chains, emits conflicts as INCONCLUSIVE receipts). This is the "any-application" spine: receipts are the interoperable currency of the fleet.

**Quilt integration:** seams:
(a) Alt+Q: toggle current tab's focused pane between terminal app and quilt-tui (spawn quilt-tui in the same pane PTY via pane app swap — mechanically: `si quilt toggle` sends tmux respawn-pane through fleetd? No — swapping the app kills terminal state. Better: Alt+Q opens quilt-tui as an overlay pane (upstream pane APIs: create floating pane) sharing cwd; the pane's input focus toggles. Floating pane = existing upstream feature. So: Alt+Q toggles a floating pane running quilt-tui; Esc-quilt exits. Agent-operated: `si quilt open --lane X` same path.
(b) tmux-hosted: `si quilt split` — breaks a tmux window into two panes: quilt-canvas-tui canvas | intelligent-terminal; tmux control mode from fleetd does split-window/swap; both stay tmux children (survive terminal death).
(c) controller: quilt-canvas-tui's controller already speaks its own unix socket; fleetd does NOT proxy it (no unnecessary hop) — the terminal plugin talks to controller directly for canvas ops (put-cell, pin FAIL). FAIL-first pins: a pin operation emits a receipt (`receipt.append kind:pin` with the cell coordinates + hash) so pins are auditable — this connects quilt line to receipts. 
(d) A quilt workflow VIEW = quilt-canvas-tui second panel showing a quilt whose fabric ports (Python/Node/C99 over quilt-c) run the terminal's own bus replay — i.e., fabric:si-bus, a port that renders receipts/lanes into cells; vim-for-cells navigation over live fleet events. That's a wild but concrete idea: the quilt becomes a spatial ledger browser.

Gateway glue specifics (OpenClaw): attach protocol = fleetd method `bridge.attach{name, filters, auth}` returning stream id; outbound push over the same socket; OpenClaw already bridges Telegram; messages TO lanes delivered via `lane.send` → three delivery modes ranked: (1) agent-session message channel if the pane runs an agent session with question tool (structured), (2) else tmux send-keys with a delimiter guard (bracketed paste + sentinel line, and REQUIRE an idle check: send `lane.idle?` via tty output-rate heuristic — send-keys into a running vim is chaos; guard: only send-keys when pane's foreground process is a shell at prompt (OSC 633 / shell integration prompt marker seen last), else queue and alert), (3) else spool to lane inbox file `lanes/<id>/inbox` — durable, agent picks up. Good, concrete, honest about send-keys dangers.

Build-on-upstream vs ADD table:
- USE: pane/tab runtime, agent-session runtime, keep-running/reattach, question tool, floating panes, panel_layout, sidebar shell, prediction UI ghost-text surface, telemetry catalog.
- ADD out-of-process: fleetd bus, receiptd chain, pinchd, conservd, ternaryd, griot, clerk, quilt hosting.
- PATCH IN-TREE (thin, upstreamable): (1) plugin API hooks: pane decorations API (title-right gutter, glyph decorations) — if upstream lacks decoration slots, add minimal `IPaneDecorator`; (2) ghost-text second provider slot for pinch-bar; (3) an event tap exporting telemetry + pane lifecycle to a socket; (4) keymap entries. Keep in-tree diff < ~1k lines; everything else plugins per captain strategy (no eternal fork-patching).

Crash-hardening notes: terminal holds NO authority; all state in daemons/tmux; on terminal crash, `si resume` re-attaches and replays (seq-based); daemons write-ahead log with fsync-on-append but group-commit 32ms; fleetd never blocks on slow subscriber (bounded queue, drop notice + resync). Sockets in $XDG_RUNTIME_DIR (tmpfs) — note the brief says /tmp volatile on this box; runtime dir is fine for sockets (they shouldn't survive reboot anyway), but LEDGER files live in a durable repo dir (git-tracked receipts dir). Good nuance: the durable copy header complains /tmp is volatile — so state layout: `${SI_HOME}` default `~/.si` (durable: chains, replay logs optional) and `$XDG_RUNTIME_DIR/si` (sockets only).

What an agent SEES and SAYS (question 1 in the brief): agent sees, via socket, lane table, room snapshots, receipts, question queue, budget state; agent SAYS via `pub`/`call`: claims (receipts), gists, questions, demands (tier), verifications. Terminal-rendered for humans as glyphs. Human-visible vs agent-native: default chrome human-normal; agent-native surfaces = socket + CLI + files, never UI-only. Rule: **no fleet fact exists only as pixels** — everything rendered is derived from bus events; everything on the bus is accessible without the terminal. That's the load-bearing principle and worth stating as a design law.

Also Lamport versions: lanes have Lamport clocks ticked on pub; receipts record `lamport` for cross-lane ordering; merge uses (lamport, lane) tuple.

10 features list finalized with names:

1. `fleetd` — the bridge bus + lane registry (tmux control mode, discovery, OpenClaw attach)
2. Question routing (q.ask/q.answer, Telegram-or-terminal, ABSTAIN deadline)
3. Receipts rendered + one-key re-execution (receiptd, three-valued, gates are receipts)
4. ActiveLog ↔ ActiveLedger flip (Alt+L dual projection)
5. Pinch-bar (pinchd, ghost routing hint, Ctrl+G p route-instead-of-run, @-token family)
6. Conservation meters (conservd, cost-since-verified, stability spark, budget alert)
7. Plato rooms as layouts (tiles/tiers/Lamport, demotion receipts, gist/hint renderers)
8. Scratchpaper clerk lane (@park, Ctrl+K s, distill receipts)
9. Ensign extraction kit (ternaryd/griot/conservd/receiptd; daemon+CLI+file contract; terminal adapters; upstream CommandPredictor bridge)
10. Quilt seams (Alt+Q floating toggle, tmux split hosting, controller socket direct, fabric:si-bus, pins-as-receipts)

Format: Markdown, headers per feature, each with Process / Protocol / Data subsections (plumbing notes as the brief demands), plus a substrate section up top and a "what to build on vs add" + "the wedge / why the fleet switches" closer. Length: this is a deep technical design doc request with 10 features × 3 plumbing notes; long