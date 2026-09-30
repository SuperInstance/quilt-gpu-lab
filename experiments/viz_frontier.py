#!/usr/bin/env python3
"""Standalone visual: the tile-codec compression frontier (TC3). Inline SVG, no deps."""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(os.path.join(ROOT, "results", "tc3", "tc3_results.json")))
pts = sorted([(int(k.split('_')[-1][:-1]), v["top1"]) for k, v in d["arms"].items() if k.startswith("E_retrieval")])
text = d["text_reference_top1"]; int8 = d["arms"]["B_int8_384B"]["top1"]
W, H, L, R, T, B = 960, 560, 110, 900, 110, 470
xs = [48, 96, 192, 384]
xpos = lambda b: L + (R - L) * (xs.index(b) / (len(xs) - 1))
ypos = lambda v: B - (B - T) * (v - 0.60) / (0.95 - 0.60)
s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="ui-sans-serif,system-ui,sans-serif">',
     f'<rect width="{W}" height="{H}" fill="#0f1115"/>',
     '<text x="50" y="48" fill="#e8ecf1" font-size="24" font-weight="600">The 384-byte tile: how low can the budget go?</text>',
     f'<text x="50" y="76" fill="#8b98a8" font-size="14">{d["n_tiles"]} real tiles &#183; retrieval-trained codec (InfoNCE) vs the deterministic 384-byte text codec &#183; bars measured on the 4050</text>']
for gv in (0.6, 0.7, 0.8, 0.9):
    y = ypos(gv)
    s += [f'<line x1="{L}" y1="{y:.0f}" x2="{R}" y2="{y:.0f}" stroke="#1e242e" stroke-width="1"/>',
          f'<text x="{L-12}" y="{y+5:.0f}" fill="#5f6c7b" font-size="13" text-anchor="end">{gv:.1f}</text>']
ty = ypos(text)
s += [f'<line x1="{L}" y1="{ty:.0f}" x2="{R}" y2="{ty:.0f}" stroke="#e0b07a" stroke-width="2" stroke-dasharray="7 5"/>',
      f'<text x="{R-6}" y="{ty-9:.0f}" fill="#e0b07a" font-size="13" text-anchor="end">deterministic text fields = {text:.4f} (needs all 384 bytes)</text>']
path = " ".join(f'{"M" if i==0 else "L"}{xpos(b):.0f},{ypos(v):.0f}' for i, (b, v) in enumerate(pts))
s.append(f'<path d="{path}" fill="none" stroke="#3aa06a" stroke-width="3"/>')
for b, v in pts:
    bow = 26 if v > text else -14
    s += [f'<circle cx="{xpos(b):.0f}" cy="{ypos(v):.0f}" r="6" fill="#3aa06a"/>',
          f'<text x="{xpos(b):.0f}" y="{ypos(v)-bow:.0f}" fill="#7fd1a8" font-size="15" font-weight="600" text-anchor="middle">{v:.4f}</text>']
ib = ypos(int8)
s += [f'<line x1="{L}" y1="{ib:.0f}" x2="{R}" y2="{ib:.0f}" stroke="#7a6fb0" stroke-width="2" stroke-dasharray="3 5"/>',
      f'<text x="{L+6}" y="{ib-8:.0f}" fill="#a89bd6" font-size="13">int8 full vector = {int8:.4f}</text>']
for b in xs:
    s.append(f'<text x="{xpos(b):.0f}" y="{B+30}" fill="#8b98a8" font-size="15" text-anchor="middle">{b} bytes</text>')
s += [f'<line x1="{L}" y1="{B}" x2="{R}" y2="{B}" stroke="#39424f" stroke-width="1"/>',
      f'<text x="{L}" y="{B+62}" fill="#c9d4e0" font-size="15">Crosses the text codec at <tspan fill="#7fd1a8" font-weight="700">96 bytes</tspan> &#8212; a quarter of the budget &#8212; then plateaus (192B and 384B are within noise).</text>',
      f'<text x="{L}" y="{B+86}" fill="#e0b07a" font-size="15">48 bytes is a real cliff: &#8722;0.19 top-1. The byte budget was never the constraint &#8212; the objective was.</text>',
      '</svg>']
open(os.path.join(ROOT, "viz", "tile-frontier.html"), "w").write("<!doctype html><meta charset=utf-8><title>tile codec frontier</title>" + "".join(s))
print("wrote viz/tile-frontier.html")
