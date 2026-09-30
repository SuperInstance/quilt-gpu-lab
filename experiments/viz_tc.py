#!/usr/bin/env python3
"""Standalone visual: the 384-byte tile codec showdown (TC1 + TC2). Inline SVG, no deps."""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
t1 = json.load(open(os.path.join(ROOT, "results", "tc1", "tc1_results.json")))
t2 = json.load(open(os.path.join(ROOT, "results", "tc2", "tc2_results.json")))
rows = [("A  deterministic text fields", t1["arms"]["A_deterministic"]["top1"], t1["arms"]["A_deterministic"].get("cos"), "#4a7fb5"),
        ("B  int8 (384-d vector)", t2["arms"]["B_int8_full"]["top1"], t2["arms"]["B_int8_full"].get("cos"), "#7a6fb0"),
        ("C  MSE-trained 96-d bottleneck", t2["arms"]["C_mse_96d"]["top1"], t2["arms"]["C_mse_96d"].get("cos"), "#b5645f"),
        ("E  retrieval-trained 96-d", t2["arms"]["E_retrieval_96d"]["top1"], None, "#2e8b57"),
        ("F  hybrid (MSE + retrieval)", t2["arms"]["F_hybrid_96d"]["top1"], t2["arms"]["F_hybrid_96d"].get("cos"), "#3aa06a")]
W, H, L, R = 900, 150 + 46 * len(rows) + 190, 300, 620
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="ui-sans-serif,system-ui,sans-serif">',
       f'<rect width="{W}" height="{H}" fill="#0f1115"/>',
       '<text x="40" y="52" fill="#e8ecf1" font-size="24" font-weight="600">The 384-byte tile: same budget, different codec</text>',
       f'<text x="40" y="80" fill="#8b98a8" font-size="14">{t1["n_tiles"]} real tiles mined from our own docs &#183; gte-small 384-d &#183; query = question, index = codec representation &#183; bars = top-1 retrieval</text>']
y = 130
for name, v, c, col in rows:
    bw = (R - L) * v
    svg += [f'<text x="40" y="{y+18}" fill="#c9d4e0" font-size="15">{name}</text>',
            f'<rect x="{L}" y="{y+2}" width="{R-L}" height="22" rx="4" fill="#1b2029"/>',
            f'<rect x="{L}" y="{y+2}" width="{bw:.1f}" height="22" rx="4" fill="{col}"/>',
            f'<text x="{L+bw+10:.0f}" y="{y+19}" fill="#e8ecf1" font-size="15" font-weight="600">{v:.4f}</text>']
    if c is not None:
        svg.append(f'<text x="{L+bw+80:.0f}" y="{y+19}" fill="#8b98a8" font-size="13">cos {c:.4f}</text>')
    y += 46
by = y + 30
svg += [f'<rect x="40" y="{by}" width="{W-80}" height="130" rx="8" fill="#161b23" stroke="#26303d"/>',
        f'<text x="60" y="{by+28}" fill="#7fd1a8" font-size="16" font-weight="600">The objective, not the budget</text>',
        f'<text x="60" y="{by+52}" fill="#c9d4e0" font-size="14">Same 96 floats: {t2["arms"]["C_mse_96d"]["top1"]:.4f} under MSE &#8594; {t2["arms"]["E_retrieval_96d"]["top1"]:.4f} under InfoNCE (+0.32).</text>',
        f'<text x="60" y="{by+76}" fill="#c9d4e0" font-size="14">And it beats the deterministic text codec ({t1["arms"]["A_deterministic"]["top1"]:.4f}) by +0.16 at identical bytes.</text>',
        f'<text x="60" y="{by+100}" fill="#e0b07a" font-size="14">Latent bug, fixture-proven: a UTF-8 codepoint split at a field boundary &#8594; decode_binary returns None &#8594; whole tile lost ({100*t1["arms"]["A_deterministic"]["decode_fail_rate"]:.2f}% of our corpus).</text>',
        '</svg>']
os.makedirs(os.path.join(ROOT, "viz"), exist_ok=True)
p = os.path.join(ROOT, "viz", "tile-codec.html")
open(p, "w").write("<!doctype html><meta charset=utf-8><title>384-byte tile codec</title>" + "".join(svg))
print("wrote", p, os.path.getsize(p), "bytes")
