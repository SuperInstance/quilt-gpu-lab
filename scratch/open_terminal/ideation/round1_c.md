# minority-human (ByteDance/Seed-2.0-mini)

### 10 Concrete Buildable Mechanics (Minority Human Supervisor UX)
All run as out-of-process plugins/services per crash-avoidance constraint:
---
1.  **Plato Tier Per-Pane Toggle (Human: `Ctrl+Shift+T`; Agent: API Call)**
    Each agent session pane displays a low-contrast 🪪 badge (human-only visible). Clicking cycles 3 tiers:
    - Full: Raw agent PTY/scrollback (agent default)
    - Gist: 3-line condensed synopsis of last 10 actions via out-of-process `ensign-trim` CLI using ensign's ternary predictor/Shannon entropy logic
    - Hint: Only critical signals (token overspend, drift mismatch, receipt requests) — fades to background unless flagged
    Implementation: Unix socket service hooks into upstream Windows Terminal pane extension SDK; no in-tree terminal changes beyond plugin install. Badge state synced to agent sessions via native agent API.
---
2.  **Receipt Spot-Check Right-Click Menu**
    Hover over a pane's 🪪 badge, right-click > *Audit Receipt* spawns a floating quilt-canvas TUI panel pulling the hash-chained receipt chain for that session's last 5 actions. A `champion_audit` button triggers the out-of-process `conservation-monitor` tool to re-execute the agent's claimed step: green check = match, red alert = drift. Receipts stored as human-readable JSON in `~/.superinstance/receipts/` (no database).
    Uses: Ensign `ConservationMonitor`, quilt-canvas-tui unix socket controller, upstream agent session APIs.
---
3.  **Pinch Bar Alert Widget (Out-of-Process Pinch Service)**
    Tiny unobtrusive top-window bar (human-only visible) that lights up when the `pinch-match` tool (trained on 5k+ repo cards) detects anomalous agent intent (e.g., unapproved GPU training, off-topic actions). Clicking zooms to the offending pane, shows gist-tier context, and includes a one-click *Quarantine Pane* button to detach it to a restricted agent room. Per-session allowlists configurable via `~/.superinstance/pinch.toml`.
    Uses: PINCH fleet primitive, DDKinger's tmux control mode hooks, khayashi's @selection context pattern.
---
4.  **Conservation Meter System Tray Dashboard**
    Native Windows/Linux system tray icon showing aggregated real-time consumption: total tokens, GPU wattage, hourly cost across all agent sessions. Hover shows per-pane breakdown; click opens a quilt-canvas dashboard with an entropy bar (from ensign `math-tools`) of token usage per agent, with alerts when any agent's workload stability std dev < 0.02 (ensign `ConservationMonitor` threshold).
    Implementation: Out-of-process `conservation-tray` CLI tool, pulls session data via upstream telemetry catalog APIs.
---
5.  **Active Ledger Toggle (`Ctrl+Shift+L`)**
    Toggles all agent panes between human-readable terminal output and a structured quilt-tui-rendered machine ledger. The ledger displays action timestamp, agent ID, hash, receipt link, and 3-value verdict (-1/0/+1 from JesseBrown1980's CI work). Humans use for compliance checks; agents use for internal bookkeeping.
    Uses: Upstream `panel_layout` API, quilt-tui cell-based rendering, JesseBrown1980's three-valued verdicts.
---
6.  **Scratchpaper Clerk Auto-Sync Sidebar**
    Toggleable sidebar (`Ctrl+Shift+S`) synced to any selected text in agent panes, or auto-appended agent session logs via `@scratchpad` API call (khayashi's context token pattern). The sidebar is a quilt-canvas markdown editor; humans can annotate, and agents can pull scratchpad context for their workflows. Auto-saves to `~/.superinstance/scratchpad/` as markdown files.
    Uses: SCRATCHPAPER fleet primitive, quilt-canvas-tui, khayashi's context token pattern.
---
7.  **Auto-Arranged Plato Room Layouts**
    Out-of-process `room-manager` service uses upstream `panel_layout` API to auto-array panes into color-coded rooms: blue = GPU training, green = git, red = restricted. Humans can drag-and-drop panes to reorder via quilt-tui's cell navigation, or agents can request room assignment via API. Saved room templates available for fleet deployment.
    Uses: PLATO ROOMS fleet primitive, upstream pane layout APIs, quilt-tui movement controls.
---
8.  **Quilt Workflow Split-Pane Toggle (`Ctrl+Shift+Q`)**
    Toggles a 50/50 split: right pane = normal intelligent-terminal agent session, left pane = quilt-tui workflow canvas showing step-by-step agent activity. The quilt panel is driven by an out-of-process `workflow-sync` service that listens to agent session events; edits to the quilt panel sync back to the agent session. Agents can trigger the toggle via API.
    Uses: QUILT TUI/CANVAS integration requirements, upstream terminal split-pane APIs, unix socket controller.
---
9.  **Attention Conservation Ping Thresholds**
    Out-of-process `attention-scheduler` tool lets humans set alert thresholds (e.g., "ping only on ≥2 critical verdicts" or "only on -1 ternary results"). Desktop notifications sent only when thresholds are crossed; quiet mode (1hr/24hr) disables pings but logs all alerts to the conservation meter. Uses ensign `ternary_integration.rs` logic to score alert severity.
    Uses: Ensign ternary predictor, conservation monitor, human attention conservation directive.
---
10. **Demotion Receipt Audit Trail**
    When an agent is demoted between plato tiers (human/automated), a hash-chained demotion receipt is stored in `~/.superinstance/demotions/`. Humans can view all receipts via the quilt-canvas dashboard, with one-click reversion of demotions. Agents receive receipt notifications in their session logs, including demotion reason (e.g., "token overspend ≥ 10% of quota").
    Uses: PLATO DEMOTION RECEIPTS fleet primitive, hash-chained receipt logic, quilt-canvas dashboard.