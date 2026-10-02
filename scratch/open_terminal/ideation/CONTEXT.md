# Ideation context v2 — open-terminal: agent-to-agent-network terminal (plato in a trenchcoat)
(2026-10-02 08:40 AKDT; durable copy — /tmp is volatile on this box)

## State of the artifact
- SuperInstance/open-terminal = our fork of microsoft/intelligent-terminal (MS's official Windows Terminal fork with native agent integration; ~2k stars; hot).
- SYNC LANDED: branch sync-upstream-20261002, merge commit f928714e, verified vs upstream ahead=38 behind=0. Upstream natives now include: agent sessions bound to tabs/panes, sidebar, keep-running/post-reattach prompts, question tool, AI telemetry catalog, BYOK + keyless Ollama, redesigned panel_layout API.
- Our June "ensign" work survived in-tree on the branch (extraction source): 392-line ternary_integration.rs (CommandPredictor Trit{-1,0,+1} with 0.6 ratio thresholds, PatternAnalyzer frequency/percentile/Shannon-entropy, ConservationMonitor with 5-chunk stability std<0.02), griot_history, math-tools (entropy_bar, agent_disagreement, forecast), module_system + context_trigger, agents-as-apps overlay prototype, AGENT.md/JOURNAL duty-log culture. Known supersessions: upstream owns the agent session/tab/pane runtime; entropy-bar layout row needs re-wire.
- STRATEGY (captain): sync clean to upstream (DONE) → extract ensign mods as STANDALONE GENERAL-PURPOSE TOOLS usable by any application → rebuild as PLUGINS for the original terminal and beyond. No eternal fork-patching.

## The captain's UX directive
- The UI is for AN AGENT TALKING TO AN AGENT NETWORK — not human-to-agent. A modern plato-paradigm (rooms/tiles, Lamport versions, tiers full/gist/hint, demotion receipts) that FEELS like business-as-usual to anyone who just thinks it's a terminal that ticks.
- Integrate quilt-tui (vim-for-cells, corrected cut-and-project in the terminal) and quilt-canvas-tui (canvas-style TUI whose second panel is a quilt; fabric ports Python/Node/C99 over quilt-c; controller+canvas over unix socket; FAIL-first pins): toggle a quilt workflow view, or break one into a tmux panel while the other is the intelligent-terminal — operated by a user OR AN AGENT driving their application through the terminal.

## Ecosystem digest (full: quilt-gpu-lab/scratch/open_terminal/DIGEST.md)
- 87% of 100 sampled forks are passive mirrors. Nobody is building the fleet console.
- DDKinger fork: remote agent sessions over SSH via tmux CONTROL MODE as a structured process frontend + tmux hooks for live agent status — drive remote panes as events, not PTY scrapes. The fleet primitive.
- khayashi: `@selection` context token (pane selection → agent context) — steal the family (@pane, @scrollback-tail, @last-error, @diff).
- JesseBrown1980: three-valued CI verdicts (-1/0/+1) — a gate that can say UNKNOWN instead of lying green.
- qq192000415: Alt+P plugin pane + per-model prompt libraries — plugin-host pattern; hard-fork installer tax noted.

## Who we are (SuperInstance)
130+ repos of agents building tools for themselves; captain→Riker→specialists→deck crew; agents are FIRST-CLASS USERS, humans supervise; most work happens in background lanes (cron agents, subagents); daily surfaces: Telegram, gh, tmux, OpenClaw gateway, canvases.

## Fleet paradigms a terminal could natively embody
1. RECEIPTS: hash-chained; trust = re-execution (champion_audit re-verifies claims).
2. PINCH: zero-LLM intent match over 5,138 repo cards (10/10 rank-1 proven).
3. ACTIVELOG/ACTIVELEDGER: one keystroke flips human-readable front ↔ machine ledger back.
4. SCRATCHPAPER: the sheet that thinks off-attention (JUST BUILT: branch `scratchpaper` on A2A-native-notebookLM).
5. CONSERVATION: tokens/GPU-Wh/$ metered per agent; waste is a first-class signal.
6. GATES: driftwatch/convergence; std==0 ⇒ INCONCLUSIVE; three-valued verdicts fit.
7. MULTI-MODEL LANES: GLM-5.x, DeepSeek flash/pro, DeepInfra roster; local models growing.
8. PLATO ROOMS: tiles/rooms, versions, full/gist/hint tiers, demotion receipts (superinstance-api).
9. QUILT TUI LINE: quilt-tui (cells-as-vim) + quilt-canvas-tui (controller+canvas over unix socket).

## The question (v2)
1. AGENT↔NETWORK UI: what does the terminal become when its primary dialog is agent-to-agent-network (plato rooms/tiles/tiers), while staying indistinguishable from a normal terminal to a human not looking? What does an agent SEE and SAY; what is a "room" when the occupant is an agent session; how do receipts/pinches/conservation render agent-to-agent; what stays human-visible vs agent-native?
2. EXTRACTED TOOLS AS PLUGINS: which ensign ideas deserve plugin-grade general-purpose rebuilds (ternary predictor, conservation monitor, griot history, overlay)? What is the right "any-application" surface — unix-socket service (like quilt-canvas-tui's controller), plain CLI + receipt files, ACP extension, shell integration?
3. QUILT INTEGRATION: toggleable quilt workflow views / tmux-hosted quilt panels beside the intelligent-terminal, driven by user or agent. Concrete seams: tmux control mode, unix sockets, upstream pane APIs.
4. THE WEDGE MS WON'T BUILD: fleet-native primitives (receipts, pinch-bar, plato tiers, conservation, scratchpaper clerk) — what makes this THE bridge for a fleet of agents, and what would make the fleet actually switch its daily driving here?

Constraint note: the box crashed twice today under concurrent GPU-training + heavy-git load; designs should favor OUT-OF-PROCESS tools over sockets/CLIs rather than in-terminal monoliths (also just better architecture).
