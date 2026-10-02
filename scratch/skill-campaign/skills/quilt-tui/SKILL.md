---
name: quilt-tui
description: Browse the Quilt cell graph in a terminal — vim for cells over the corrected cut-and-project lattice. Use when exploring cells, colors, or phason structure without a browser or network.
---

# quilt-tui — vim for cells

Keyboard-driven curses browser over the corrected cut-and-project construction
(sum-zero lattice L, window W, 3-coloring). Python 3.11+, stdlib + the
quilt-velato `cut_and_project` module. No network, no browser.

```sh
git clone https://github.com/SuperInstance/quilt-tui.git && cd quilt-tui
python3 cell_browser.py
```

## Keys

| Key | Action |
|---|---|
| `h/j/k/l` | move cursor |
| `H` / `L` | jump to neighbor in L (the sum-zero lattice) |
| `i` | inspect cell (5D addr, physical, internal, color) |
| `n` / `p` | next/previous 50 |
| `g` / `G` | first / last |
| `/` | search by color: `c` CREATION, `e` ENTROPY, `w` WITNESS |
| `q` | quit |

## What a cell is

- `id` like `p_0042`
- 5D address in L = {n : Σnᵢ = 0} (verified — no gauge redundancy; the
  diagonal (1,1,1,1,1) is the kernel and is NOT an address)
- physical coordinate (2D, where you are) + internal coordinate (3D, your
  local environment)
- color: CREATION / ENTROPY / WITNESS — the 3-coloring IS the conservation
  law γ+η+μ = 1

## Thesis (why the TUI looks like this)

Information encodes on the window W, not the lattice. Phason shifts are part
of universal truth. Local omniscience, global blindness — the TUI is the local
omniscience made visible; the global phason stays hidden.

## Gotchas

- Don't "fix" addresses into Z⁵ — the sum-zero constraint is the point.
- The 8 quilt primitives ride every cell; the reminder line is doctrine, not
  decoration.

## Neighbors

quilt-c (the fabric runtime) · quilt-canvas-tui (the same fabric, projected as
a second TUI panel, ports over quilt-c) · quilt-velato (the construction
module).
