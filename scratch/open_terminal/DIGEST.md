# Open-Terminal Ecosystem Digest

**Date:** 2026-10-02 (AKDT)
**Lane:** research (read-only; `gh api` only)
**Upstream:** `microsoft/intelligent-terminal` — 2,034 stars, 162 forks, default branch `main`, last push 2026-10-01.
**Our fork:** `SuperInstance/open-terminal` — diverged `+37 / -472`, last push 2026-06-10, MIT.

> Method note: `pushed_at` is a lying signal for forks — clicking "Sync fork" bumps it with zero divergence. I measured real divergence with the compare API (`GET /repos/microsoft/intelligent-terminal/compare/main...OWNER:main`, field `ahead_by`). Of 100 sampled forks, only **13** had any commits ahead of upstream. Passive mirror is the default state of this ecosystem.

---

## INPUT 1 — THE FORK ECOSYSTEM

Of 100 forks sampled, 87 are pure mirrors (0 ahead). Among those, several *look* active but are just freshly synced upstream re-hosts — e.g. `bit-cook/ms-intelligent-terminal` carries upstream's newest commit (`#1064`, 2026-09-30) because it syncs constantly; same for `ZoneCog`, `centis/alternatePane`, `Esomoire-consultancy-Company/sentinelligent-terminal`, `syntax-syndicate`, `TouKenAI`, `ltcolrodriguez-ship-it/GRIMS-TERMINAL`, `bradAGI`. Skip all of those. The diverged set, with `ahead_by`:

`SuperInstance/open-terminal` 37 · `qq192000415-source` 26 · `JesseBrown1980` 20 · `vanzue` 15 · `ashishpatel26` 4 · `Global-Vibez-DSG` 4 · `bmshin94` 4 · `DDKinger/intelligent-terminal-fork` 4 · plus five with 1–3 (`FDa-compliance/...` spam repo 3, `siddhihingne12` 2, `michael-her` 2, `khayashi4337` 1, `TojotheTerror` 1).

### 1. DDKinger/intelligent-terminal-fork — the only remotely interesting network divergence
Four commits, all by **Yuandi** (an active upstream WT/IT contributor), last push 2026-09-22: "Remote session: Browse and resume agent sessions over SSH (#1)", "Add native tmux control-mode process frontend (#2)", "Track Linux agent sessions with tmux hooks in native and SSH panes (#3)", "Update tmux session activity, attachment reuse, tab names and ordering (#4)". **What it does:** extends the agent-session model off-box. Upstream's session view only sees host CLIs and local WSL distros; DDKinger makes SSH/tmux remote sessions first-class — using **tmux control mode (`tmux -CC`) as a structured process frontend** instead of scraping a PTY, and **tmux hooks to track agent activity/status on the remote** without ACP running there, with attachment reuse and tab-name/order sync. **Clever:** control mode turns remote panes into drive-able events; hooks give live agent state for free. **Steal:** this is the fleet primitive. Our fleet spans many machines; remote session discovery + attach + reattach is the single most valuable missing capability in the whole ecosystem, and this is the only fork pushing on it.

### 2. qq192000415-source/intelligent-terminal — the most active divergent community fork
26 ahead, 1 star, own signed installer (`.cer` + `.msix` in Releases), last push 2026-09-02. By "coderyj" / 云端存档. Adds a right-side **Claude / Grok "enhanced input pane"** (`Alt+E` / `Alt+G`, same column, mutually exclusive) shipping curated prompt libraries (Claude: 6 groups / 29 commands; Grok: 7 groups / 61 commands), a **plugin pane** (`Alt+P`) with a "GitHub cloud-backup wizard" and real `git archive`, and a shared notes tab. Code in `src/cascadia/TerminalApp/EnhancedInput/`. **Clever:** it decouples "agent chat" from the ACP agent pane into a dedicated always-available input buddy with a scripted command palette — really a prompt-library/macro surface, plus a marketplace-style plugin host. **Steal:** the `Alt+P` plugin/marketplace pane, and per-model curated prompt libraries as first-class UI. Also a cautionary tale: hard forks inherit installer + permanent merge tax.

### 3. JesseBrown1980/intelligent-terminal — ternary CI art-piece
20 ahead, 1 star, last push 2026-08-08. Commits: "toolchain rule: Rust 1.81 + clippy, integer/ternary only" (repeated ~14×), "CI: three-valued verdicts, so the gate stops lying in both directions", then "star port" commits ("light this stone so it is reachable", "star port sidecar", "serve raw", "hot-path row"). **What it does:** imposes an integer/ternary-only, no-float house rule across the Rust toolchain (build-lint) and rewrites CI to emit three-valued verdicts (-1 / 0 / +1) instead of pass/fail, plus a "star port" sidecar that serves data. **Clever:** three-valued CI verdicts is genuinely good — a gate that can say "unknown/neutral" instead of collapsing ambiguity into a green check; rhymes hard with our ternary/conservation motif. **Steal:** three-valued verdicts as a CI/gate primitive, and "no-float, ternary-only" as an optional Rust lint. Visionary solo piece, real idea inside.

### 4. ashishpatel26/intelligent-terminal — first local-model ACP backend
4 ahead, last push 2026-06-17. Author is a known AI-repo curator. Adds "Ollama provider support" to the ACP layer + "Fix Copilot review findings: Ollama ACP placement and exe search order". **What it does:** makes a local Ollama model a first-class ACP agent backend and fixes executable discovery order across host/WSL. **Clever:** local-model-as-ACP-backend is our offline/edge/boat-brain story, done simply. **Steal:** the ACP provider-registration shape and exe-search-order fix. Mostly **superseded** — upstream now ships BYOK + keyless Ollama in the UI (Input 3) — but it documents the wiring.

### 5. khayashi4337/intelligent-terminal — the single best small idea in the ecosystem
1 ahead, last push 2026-09-01. One commit: **"Add `@selection`: expose the pane's current visual selection to agents."** **What it does:** adds an `@`-mention token that hands the terminal pane's current mouse/keyboard text selection to the agent as context. **Clever:** tiny, high-leverage — it bridges "I can see this in my scrollback" → "the agent can see it too", which upstream does not do. **Steal:** `@selection` and its family (`@pane`, `@scrollback-tail`, `@last-error`, `@file`, `@diff`) as context-reference tokens in the agent input. Cheap to build, immediately sticky.

### 6. bmshin94/intelligent-terminal — fork-onboarding as the product
4 ahead, last push 2026-10-01. "docs: created CLAUDE.md persona guide", "docs: add Korean full analysis summary of Intelligent Terminal", both merged via Claude. **What it does:** documentation/persona only. **Clever:** a `CLAUDE.md` persona makes the fork agent-ready for Claude Code, and a localized deep-analysis doc is exactly the onboarding artifact a fork wants. **Steal:** ship an `AGENTS.md`/`CLAUDE.md` persona + a "what is this" analysis as standard fork artifacts (we already have the AGENT.md ensign pattern — this validates it).

### 7. Global-Vibez-DSG/intelligent-terminal — agent-fork sprawl, in the wild
4 ahead, last push 2026-06-27, commits by `copilot-swe-agent[bot]`: "feat: add cross-product integration scaffolding for globalvibezdsg.com" + review-feedback fixes. **What it does:** bot-forks a terminal to scaffold a company website integration. **Clever:** nothing technically. **Steal:** nothing — but read it as demand: people reach for "fork the terminal into an app shell". A sanctioned overlay/plugin path (see qq fork's `Alt+P`) beats a fork.

### 8. michael-her/intelligent-terminal — code search wiring
2 ahead, last push 2026-08-10: "chore: zoekt config" (+merge). Adds a **zoekt** (trigram code-search) config. **Steal:** treat code search (zoekt/ripgrep) as a first-class agent *context source*, not just a user tool.

### 9. TojotheTerror/intelligent-terminal — safety docs
1 ahead, last push 2026-06-27: "CODEX-28 add repository safety docs and local safeguards". Docs + guardrails. **Steal:** ship explicit repository-safety / local-safeguard docs with the terminal rather than bolting them on after an incident.

### 10. siddhihingne12/intelligent-terminal — noise
2 ahead, trivial (`colors.txt` entries, bug-report template validation). Listed only for completeness.

**Near-misses worth noting:** `vanzue` (15 ahead) is *all* upstream-author commits ("Kai Tao (from Dev Box)": dependabot/toolchain/license-whitespace) — an upstream maintainer's CI-staging fork, not a community divergence, so it doesn't count. `FDa-compliance/06085marrujo...` (3 ahead) is a template/spam repo, ignored. `SuperInstance/open-terminal` is ours — Input 2.

---

## INPUT 2 — WHAT OUR FORK'S ENSIGN WAS

`SuperInstance/open-terminal` is a fork of `microsoft/intelligent-terminal` (+37 / −472 as of today). `AGENT.md` self-describes it as the **"Ensign Terminal"** — a fleet *room* with a duty log (`memory/JOURNAL.md`, "First Watch — Ensign Takes Post", 2026-06-08) and listed fleet neighbors (`tminus-dispatcher`, `fleet-bridge`, `symphony-runtime`, `composite-headspace`, `i2i-bottle-agent`). README tagline: *"The first terminal that doesn't wait for you to ask. Your terminal already knows your workflow's mathematics. We wired up the gauges."* Marketing pillars: math-aware command analysis, **Griot** command history, and a **zero-cost promise** (no overhead when a feature isn't used).

### The core: ternary integration in one file
The only *code* commit of substance is `484f8ed` (2026-06-04), a single **392-line** file `tools/wta/src/ternary_integration.rs` — "feat: add ternary agent integration — CommandPredictor, PatternAnalyzer, ConservationMonitor":

- **CommandPredictor** — maps command history to `Trit { Avoid(-1), Unknown(0), Choose(+1) }`; per-command counts; `predict()` chooses/avoids at a 0.6 ratio threshold; `top_recommendations(n)` ranks by choose-ratio; `conservation_check()` splits history into 5 chunks and requires the avoid-ratio std-dev `< 0.02`.
- **PatternAnalyzer** — frequency map; `is_anomalous()` = bottom-5% percentile (unseen = anomalous); `denoise()` = 3-window majority filter; `stats()` returns unique count, total, Shannon entropy.
- **ConservationMonitor** — wraps the predictor, records `(N, avoid_ratio, std)` per scale and prints a `CONSERVED ✓ / VIOLATED ✗` report. Its doc-comment states 5 "laws": avoidance discovers hidden structure; avoidance dominates choice; strategy species coexist; population > individual; avoidance ratio is conserved across scales (std < 0.01).

### The scaffolding around it
- **INTEGRATION.md** maps the three modules onto a **NATURAL (shell) / FLUID (ternary) / MACHINE (render)** three-layer architecture: `CommandPredictor → forecast/predictor.rs` ghost-text; `PatternAnalyzer → context_trigger/triggers.rs` (pure `<1µs` predicates gating model calls); `ConservationMonitor → forecast/anomaly.rs` (KL/Wasserstein suspicion when the law drifts). State is "session-persistent, serializes to disk".
- **CAPABILITY.toml** reframes it as a **conservation-budget API**: `ConservationMonitor` tracks a `γ+H=C` resource budget; `sample(cpu,mem) → ConservationReport`; `is_healthy()`; `suggest_commands()` / `compose_suggestions()` over `SuggestedCommand{command, rationale, priority, category}` with `CommandCategory{Cleanup, Productive, Diagnostic, Maintenance}`; integrations to `open-iterator`/`open-parallel`/`open-tui`/`open-mind`.
- **AGENTS_AS_APPS.md** — "the terminal IS the agent's interface": an `agent_overlay` renderer (`src/renderer/agent_overlay.rs`) draws a **Conservation Budget** bar, a **Fleet Health** panel (● active / ○ idle, health bars), and a **Spectral Ranking** (dominant eigenvalue of the agent interaction matrix) as a non-intrusive overlay; agents authenticate via **lattice-crypto** (post-quantum challenge/response).
- **docs/TRENDING_HARNESS.md** — a feature-gated (`--features trending`) harness that clones → analyzes → decomposes → integration-plans *any GitHub repo*, exporting `TrendingRepo`, `RepoAnalysis`, `ModuleProposal`, `IntegrationPlan`. "The terminal doesn't just run code. It becomes what it consumes."
- Supporting theory: `THREE_LAYER_ARCHITECTURE.md`, `TRIPARTITE-MAP.md` (HARDCODE/MODEL/CACHE), `INDUCTION-ANALYSIS.md`, `docs/CORRECTED_MODEL.md`, `docs/HARNESS_ARCHITECTURE.md`, `docs/METAL_LIBRARY_INTEGRATION.md`.

### Novel vs superseded (honest call)
**Superseded by upstream's native integration:**
- *Command prediction / ghost text* — our predictor is a toy n-gram choose/avoid ratio with no LLM and no shell-integration signal; upstream ships agent-native suggestions, command palette prompts, and per-tab prompt history. Superseded.
- *Session persistence* — "serialize FLUID state to disk" is subsumed by upstream's ACP `session/list`, hooks fallback, keep-running and reattach (Input 3).
- *Multi-agent orchestration* — upstream ships the `wta-master` agent pool with per-identity session multiplexing, `delegate_task_in_new_workspace`, and background tabs; our "fleet overlay" is a renderer with no control plane. Superseded as a *mechanism*.
- *Agent auth* — lattice-crypto was never shipped and is unnecessary; upstream uses ACP + Windows Credential Manager.

**Still genuinely novel / worth keeping:**
- **Conservation / ternary framing as a resource-and-workflow budget** — γ+H=C enforced in the UI, "avoidance ratio conserved across scales" as a stability/anomaly detector. Upstream has *no* notion of a compute/budget envelope per agent or per window. This is a real differentiator **if grounded in something measurable** (token spend, GPU budget, fleet capacity).
- **Fleet-level view** — spectral ranking of the agent interaction matrix (coordination health) and a fleet-health panel. Upstream's session view is per-machine and counts sessions; nothing measures cross-agent coordination.
- **Ambient-telemetry overlay as a UI concept** — upstream's agent pane is chat-shaped, not "non-intrusive gauges the agent also reads" shaped. The *form factor* is distinct.
- **Zero-cost promise** — feature-gated, no overhead when unused. Still the right discipline.
- **Trending / absorption harness** — clone→analyze→decompose→integrate any repo, feature-gated. Upstream absorbs nothing; this is buildable and uniquely ours.
- **Griot command history** — overlaps upstream's per-CLI history filtering mechanically, but "Griot" as a *narrating memory* is a distinct voice.

**Bottom line:** the ensign was trying to be a *math-aware, conservation-governed, fleet-conscious* terminal overlay. What actually shipped was a promising spec set plus one 392-line Rust module — there's no evidence the ternary modules were ever compiled into the live terminal path. The vision components (budget enforcement, fleet coordination metrics, absorption harness) are the parts upstream does *not* cover and remain the salvageable core.

---

## INPUT 3 — WHAT UPSTREAM NATIVELY SHIPS (Oct 2026 baseline)

`microsoft/intelligent-terminal` is a real, deeply-integrated ACP terminal, not a demo. From README + `AGENTS.md` + `doc/specs/*` + `doc/intelligent-terminal-telemetry.md`.

### Architecture (`AGENTS.md`)
`WindowsTerminal.exe` hosts `TerminalProtocolComServer` (COM, discovered via `WT_COM_CLSID`) + `SharedWta → wta-master → agent CLI pool` (ACP over stdio); **one `wta-helper` pane per tab**; helper↔master ACP over a named pipe; session-scoped MCP tools. **WTA** (`tools/wta/`, Rust) is the orchestrator. `wta-master` pools agent CLI processes keyed by *(agent identity, execution source, command)*; helpers with the same key multiplex sessions through one process. Installed, policy-allowed native host agents (except Gemini) initialize in the background at master startup and stay resident. Agent panes are ordinary `ConptyConnection` panes hosting `wta-helper` — **C++ never speaks ACP**.

### Native agent features (README)
- **Agent Status Bar** — bottom bar: pane toggle (`Ctrl+Shift+.`), error-detection icon (`Ctrl+Alt+.`), agent management (`Ctrl+Shift+/`); token usage/cost readout.
- **Agent Pane** — docked, tab-bound, context on shell output across PowerShell/Bash-WSL; spins up background tasks in new tabs; command suggestions are **run / copy / dismiss** and never auto-run without approval; `Alt+V` clipboard-image paste; `Up`/`Down` prompt recall; per-pane `/model` override; an "Agent focus" indicator marks the pane the agent controls.
- **Slash commands** — `/agent`, `/clear`, `/config`, `/fix [hint]`, `/help`, `/model`, `/move [l|r|u|d]`, `/new`, `/restart`, `/sessions`, `/stop`.
- **Agent Management** — active agents, status, past sessions, resume; tracked sessions show provider icons in the pane/tab; vertical rows have their own icons.
- **Error Detection + Autofix** — failure → status-bar indicator → agent pane pre-loaded with error context; opt-in auto-suggest; `/fix`.
- **Command Palette agent mode** — `?<prompt>` starts a background agent tab with active-pane context; `Alt+Shift+/` prompt mode.
- **Multi-agent** — `Alt+Shift+B` opens an interactive **delegate-agent** tab (no startup prompt); `>` toggles the AI assistant; `?`/`&` entry points; delegate agent is separate from the pane agent.
- **BYOK** — any OpenAI-compatible Chat Completions endpoint via Copilot or OpenCode (base URL / model / key); keys in Windows Credential Manager; keyless local **Ollama** supported.
- **Providers** — Copilot (default), Claude, Codex, Gemini, OpenCode; `custom:<name>`. Profiles can pin an agent; WSL profiles list agents inside the distro.

### Tab/pane binding
Per-tab agent pane; each eligible tab **pre-warms one stashed helper** (skipped if WTA unavailable, policy blocks all agents, no active terminal, or a dragged-in pane exists). Toggling **stashes/restores** — it does *not* destroy the helper, ACP session, or chat history. Per-tab events carry tab+window identity and route to the owning tab (no broadcast). Agent panes are not persisted into the window layout; `/move` moves one tab's pane without changing the global setting. Terminal mutation requested by an agent goes through a **confirmation-gated session MCP action path**.

### Sidebar
"Sidebar" = the **vertical tab layout** (`SidebarEnabled`), with: sidebar tab search; a dedicated **Agent sessions view** with an agent filter and row counts; selectable **rich-tab fields** (paths, branch names — values not collected in telemetry); keyboard navigation (Tab + ↑↓); and **Keep tab running** exposed through the sidebar menu. Telemetry: `SidebarSearchOpened`, `SidebarAgentFilterApplied`, `SidebarTabPinned` (the keep-running action), `SidebarRowFieldsChanged`.

### Keep-running / detach / reattach
`App.KeepRunningMarked` (fields `KeepId`, `TotalTabCount`, `KeepRunningTabCount`, `HasAgentPane`) marks a tab to stay alive; `App.KeepRunningDetached` = the marked tab survived the window closing; `App.KeepRunningReattached` transfers the retained tab into a new window with `Outcome ∈ {live, failed}`. On reattach, **the same ACP session stays bound**; `WTA.AgentPromptSent` carries a `Reattached` flag. Hard limits: **in-process only** — cannot survive process exit, no `gone` outcome, failed transfers can be retried.

### Question tool / user input
The session MCP exposes `run_command_in_current_shell`, `create_workspace`, `delegate_task_in_new_workspace`, and **`request_user_input`**; `WTA.SessionMcpToolCalled` buckets these tool names. In the session-status model (`hybrid-agent-session-tracking.md`), a user-input tool (`AskUserQuestion`) transitions a session to **Attention** (not "Working") — and the OpenCode question-tool *waiting* status was just fixed (#1063). So: agents can ask the human a question, and the session view surfaces an attention state.

### Sessions / history / resilience
ACP `session/list` is the **sole authoritative history source** (reconcile, not just seed; titles come from `session/list`, not disk). **Hooks own status, "born-bound" binds, a watcher fills the gap** (hybrid tracking, Class A = native host vs Class B = WSL/other) with per-CLI status detection and per-CLI history filtering. `restore-after-close` and `connection-resilience` specs: **fail closed, never auto-resume**; helper death → master cleans up, Terminal does not respawn; explicit `/restart`/resume only.

### Telemetry catalog (`doc/intelligent-terminal-telemetry.md`)
**34 AI/agent event definitions** (14 App, 16 WTA, 1 Settings Model, 3 Settings Editor) with typed business fields and documented measurement caveats. Highlights: `AppCreated` (13 fields, per-window provider/policy/sidebar snapshot), `AgentSessionStarted` (23 fields), `AgentPaneOpened`, `CommandPaletteAgentPrompt{Entered,Dispatched}`, the four `Sidebar*` + three `KeepRunning*` events, `DelegateInvoked`, `ErrorDetected`; WTA `AcpInitializeComplete` / `AcpNewSessionComplete` / `AcpLoadSessionComplete` / `AgentColdStartComplete` / `AgentPromptSent` (incl. `Reattached`, `UserPromptOrdinal`) / `AgentResponseFirstToken` / `AgentResponseComplete` / `ErrorDetected` / `ErrorFixOffered` / `ErrorFixAccepted` / `AgentSlashCommandUsed` / `SessionsViewOpened` / `SessionResumeInvoked` / `SessionMcpToolCalled` / `HookOperationCompleted`; Model `AgentProviderChanged`; Editor ACP model probes. Governance: local transport layer, no cloud API calls, session context in memory only, telemetry to Microsoft with opt-out.

### Spec library (partial)
`Multi-window-agent-pane`, `hybrid-agent-session-tracking`, `agent-history-sidebar-keyboard`, `restore-after-close`, `connection-resilience`, `session-history-via-acp`, `agent-failure-handling`, `llm-agent-event-integration`, `per-cli-history-filtering`, `byok-agent-support`, `agent-oobe-design`, `acp-1.0-conductor-migration`, `Yolo-mode`, `WTA-terminal-action-proposals`, `rtl-investigation`, `portable-mode-spec`.

**The free Oct-2026 baseline a fork inherits:** an ACP agent pane bound per tab with a pooled, session-multiplexing agent process; delegate/background tabs; per-tab prompt history + slash commands; a sidebar with an agent-sessions view, filters, rich tab fields, and keyboard nav; keep-running/detach/reattach (in-process); error detection + autofix; command-palette agent entry; BYOK/Ollama; Copilot/Claude/Codex/Gemini/OpenCode; a fully instrumented telemetry surface; and a large spec library documenting all of it. **None of this needs rebuilding — a fork starts here, not from Windows Terminal.**

---

## SYNTHESIS HINTS — where the wedges are

1. **There is no remote / fleet control plane.** Upstream is strictly single-machine (host CLIs + local WSL distros); keep-running is in-process and cannot survive process exit or cross hosts. A fleet-of-agents company needs session *discovery across N machines*, attach/reattach to an agent running on a remote box (SSH/mux), and one global "which agent is where, doing what" view. Only DDKinger's `tmux -CC` fork touches this. **Wedge: remote agent-session transport and a fleet session registry.**

2. **There is no cross-agent coordination or observability.** The session view is per-tab/per-machine and counts sessions; nothing measures contention, dependency graphs, fan-out, or collective health. **Wedge: a fleet overlay — agent interaction graph, token/GPU accounting, and a coordination metric (our spectral-ranking idea, grounded in real data).** This is where the ensign's math is still genuinely novel.

3. **There is no resource/energy/conservation budget enforcement.** Upstream *displays* token usage/cost per pane but never budgets, throttles, attributes, or admits on a shared pool. Systems with finite GPU/token budgets need admission control. **Wedge: an enforced γ+H=C-style conservation budget with admission/scheduling across agents, surfaced in the status bar — turn the ensign's math into policy.**

4. **Context-reference primitives are missing.** Upstream shares "shell output context" opaquely; `@selection` exists only as a lone fork commit. There are no `@pane` / `@scrollback-tail` / `@last-error` / `@file` / `@diff` tokens and no way to pin artifacts. **Wedge: first-class context tokens + a context shelf — cheap, sticky, immediately useful; the best ROI in the whole survey.**

5. **Absorption and headless operation are unsolved.** Upstream absorbs nothing and is a Windows-only, heavy C++/XAML build; nothing lets a fleet turn an arbitrary repo/tool into a terminal-usable module, and nothing drives agent sessions headlessly for automation/CI. **Wedges: the `trending` absorption harness (ours alone), and a headless/CI agent-terminal mode (drive sessions without a GUI).** Both are things a fleet-of-agents company desperately needs and Microsoft has no reason to build.

---

*Receipt: research lane, read-only, `gh api` only for open-terminal + upstream; local writes to `quilt-gpu-lab` only.*
