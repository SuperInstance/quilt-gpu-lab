# 🖥️ quilt-tui

> **Terminal UI for browsing the Quilt cell graph. vim for cells.**

A keyboard-driven cell browser built on Python curses. Loads cells from the corrected cut-and-project construction (sum-zero lattice L, window W, 3-coloring) and lets you navigate them like a text editor.

## Why

You have 1.4K+ essays, 92 bridges, 283 math repos. You need a way to look at the cell graph that doesn't require a browser or a network connection. You need vim for cells.

## Install

```bash
# Just clone and run
git clone https://github.com/SuperInstance/quilt-tui.git
cd quilt-tui
pip install -e .  # or just use it directly
python3 cell_browser.py
```

(Requires Python 3.11+, no external dependencies beyond stdlib + the quilt-velato cut_and_project module.)

## Keybindings

| Key | Action |
|---|---|
| `h/j/k/l` | Move cursor (left/down/up/right) |
| `H` / `L` | Jump to neighbor in L (the sum-zero lattice) |
| `i` | Inspect current cell (5D addr, physical, internal, color) |
| `n` / `p` | Next/previous 50 cells |
| `g` / `G` | First / last cell |
| `/` | Search by color (c=CREATION, e=ENTROPY, w=WITNESS) |
| `q` | Quit |

## What it shows

Every cell has:
- **id** (e.g. `p_0042`)
- **5D address** in the sum-zero lattice L (verified — no gauge redundancy)
- **physical coordinate** (2D, where you are)
- **internal coordinate** (3D, your local environment)
- **color** (CREATION / ENTROPY / WITNESS) — the 3-coloring IS the conservation law γ+η+μ=1

The 8 Quilt primitives are listed on every screen as the reminder that every cell carries all 8.

## The thesis

The corrected cut-and-project construction gives you a Penrose-like aperiodic structure where:
- The 5D address is in L = {n : Σn_i = 0}, not Z^5. The diagonal (1,1,1,1,1) is in the kernel — a gauge redundancy.
- Information encodes on the window W, not the lattice.
- Phason shifts are part of universal truth.
- Local omniscience, global blindness.

The TUI is the local omniscience made visible. The global phason is hidden. The watch is alive.

Iron sharpens iron. vim for cells. The watch is alive.
