# minority-human round2 (ByteDance/Seed-2.0-mini)

---
## (1) Attack My Own Original Round-1 Answer
I concede three critical flaws that fail the captain's rules and skepticism from the ecosystem digest:
1. **Merge-Tax Prone UI Bloat**: I embedded most features (per-pane badges, hardwired ledger toggles, full quilt splits) directly into the terminal's core code, which would require constant rework to sync with upstream Microsoft changes — exactly the pitfall the captain warned against avoiding (we were supposed to extract mods as standalone plugins, not eternal fork patches).
2. **No Sustainable Moat**: I failed to center the submission on the only fleet-exclusive feature Microsoft will never build: hash-chained, re-executable audit receipts. Instead, I spread auditing and conservation across disjoint UI features, which would be obsolete within 6 months as MS adds generic agent audit tools.
3. **Inflexible Agent Communication**: I required agents to use custom terminal APIs instead of standard, human-invisible escape sequences, which limited adoption by existing agent runtimes that expect plain PTY writes.

---
## (2) Steal the Best 2 Ideas from Others
### Top Stolen Ideas
1.  **Invisible OSC Agent Transport (From agent-network-grammar)**: This uses standard terminal DCS/OSC escape sequences that are completely ignored by human users, letting agents send metadata (correlation IDs, budgets, room tags) without changing the visible terminal output. It solves the "looks like a normal terminal" requirement perfectly and lets agents participate without custom SDKs.
2.  **Hash-Chained Receipts + Re-Executable Trust (From skeptic-wedge)**: This is the only sustainable moat feature: it ties audit trails, conservation metering, and three-valued verdicts into a system where trust is verified by re-executing agent claims, aligned with SuperInstance's "champion_audit" ritual. I extended this with khayashi's `@selection`-style context token family for agent-native context resolution.
*Bonus complementary steal*: DDKinger's tmux control mode remote session bridge to fix missing fleet remote session management.

---
## (3) Revised Top-5 Features (Ranked by Moat & Build Priority)
All features follow the captain's rules: out-of-process, invisible to humans unless explicitly activated, uses upstream APIs where possible, and avoids merge tax.

---
### #1 Hash-Chained Receipts + @Receipt Context Tokens (Foundational Moat)
#### Mechanic
- **Out-of-process `receiptd` daemon**: Stores append-only JSONL receipt chains for every agent pane in `~/.si/receipts/<pane_id>.chain`, with each entry containing a hash of the prior entry, agent input/output, tier, budget, and correlation ID.
- **OSC Envelope Integration**: Agents write the standard agent-network-grammar OSC escape (`\u001b]1338;v=1;<corr>;<budget>;<room>;<prev_hash>\u0007`) before their prompt to attach metadata to the receipt.
- **Context Token Resolution**: The terminal parses `@receipt <hash>` (extended from khayashi's `@selection` family) and renders a tiny inline three-valued verdict glyph (✅/❓/❌ from JesseBrown1980's rules) that links to a one-click `champion_audit` re-execution via the `si-receipt verify` CLI.
#### Why It Survives Skeptics
This is the only feature Microsoft will never build: it requires SuperInstance's specific "trust = re-execution" audit culture and custom `champion_audit` sandbox, which no generic terminal will adopt. It is fully out-of-process, requiring only a lightweight terminal plugin to resolve `@receipt` tokens and render verdicts — no core terminal code changes.
#### First Buildable Slice
1.  Minimal `receiptd` daemon that appends JSONL receipts to disk.
2.  Lightweight terminal plugin that parses `@receipt <hash>` and renders inline verdict glyphs.
3.  `si-receipt` CLI tool that verifies a receipt by re-executing the agent's original claim via `champion_audit`.

---
### #2 Invisible OSC Agent-to-Agent Transport (Universal Agent Communication)
#### Mechanic
- **Standard OSC Escape Envelope**: Defined as `\u001b]1338;v=1;<corr>;<budget>;<room>;<prev_hash>\u0007`, ignored by all human terminal users but parsed by the out-of-process `agent-broker` daemon.
- **Routing & Metadata Handling**: The `agent-broker` uses the envelope's metadata to route prompts between panes, apply budget limits, tag context to rooms, and integrate DDKinger's tmux control mode hooks for syncing remote fleet sessions.
#### Why It Survives Skeptics
Microsoft's agent integrations require human-facing chat panes; this transport is entirely invisible to humans, so it does not compete with upstream's UI. It is a generic protocol that works with any agent runtime that can write to a PTY, making it usable by all SuperInstance agents without custom SDKs.
#### First Buildable Slice
1.  OSC envelope parser added to the terminal's existing agent session hook (no core code rewrite, just a lightweight plugin).
2.  Minimal `agent-broker` daemon that routes local pane prompts using the envelope's correlation ID.
3.  `si-send-envelope` CLI tool for agents to inject OSC envelopes into their PTY output.

---
### #3 Fleet Remote Session Bridge (DDKinger Adaptation)
#### Mechanic
- **Out-of-process `tmux-broker` daemon**: Uses tmux control mode (`tmux -CC`) to connect to remote SSH/tmux sessions, exposing them as first-class agent panes in the terminal without error-prone PTY scraping.
- **State Sync**: The broker syncs pane statuses, tab names, and reattach state to the terminal via the upstream agent session API, matching DDKinger's fork's functionality but as an out-of-process service.
#### Why It Survives Skeptics
Microsoft only supports local WSL/host agent sessions; remote fleet session management with structured event hooks is a fleet-specific need no generic terminal will prioritize. It is fully out-of-process, requiring no core terminal code changes.
#### First Buildable Slice
1.  `tmux-broker` daemon that connects to a local tmux server and exposes remote SSH sessions.
2.  Terminal plugin that syncs remote pane names to the terminal's tab bar via the upstream agent session API.
3.  `si-tmux attach <session>` CLI tool to connect to a remote fleet session.

---
### #4 Per-Agent Conservation Metering (Fleet-Specific Cost Tracking)
#### Mechanic
- **Out-of-process `conservd` daemon**: Pulls token usage data from upstream's AI telemetry catalog and GPU wattage data via `nvidia-smi` polling, then meters real-time cost per agent pane.
- **Alerting**: Publishes metering stats to the fleet bus, and a lightweight terminal plugin displays a tiny inline alert glyph (e.g., 🪙) when an agent exceeds its daily token or GPU quota.
#### Why It Surv