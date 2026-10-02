#!/usr/bin/env python
"""av1_glyph_atlas.py — AV1 model A: the algorithmic ascii→image renderer (the honest floor).

Renders an ascii grid back into an image by compositing rasterized glyphs — no learning.
This is "your own unique image on the other side", version 0: deterministic, exists
before any weights. Tonal shaping (phosphor tint, vignette, bloom-ish gain) gives the
render its own look instead of pretending to recover the source frame.

usage:
  python av1_glyph_atlas.py <ascii.txt> <out.png> [--cell 8x12] [--phosphor R,G,B]
                            [--vignette 0.35] [--gain 1.0] [--font PATH]
"""
import argparse, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

DEFAULT_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
]

def find_font(explicit):
    if explicit:
        return Path(explicit)
    for c in DEFAULT_FONT_CANDIDATES:
        if Path(c).exists():
            return Path(c)
    return None  # PIL bitmap fallback

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ascii"); ap.add_argument("out")
    ap.add_argument("--cell", default="8x12"); ap.add_argument("--phosphor", default=None)
    ap.add_argument("--vignette", type=float, default=0.35); ap.add_argument("--gain", type=float, default=1.0)
    ap.add_argument("--font", default=None); ap.add_argument("--grid", default=None,
        help="instead of reading text: raw grid file with one char per luminance (same thing)")
    a = ap.parse_args()

    text = Path(a.ascii).read_text().rstrip("\n").split("\n")
    rows, cols = len(text), max(len(l) for l in text)
    cw, ch = (int(x) for x in a.cell.split("x"))

    font_path = find_font(a.font)
    if font_path:
        # size font so glyph fits the cell box
        f = ImageFont.truetype(str(font_path), ch - 2)
    else:
        f = ImageFont.load_default()

    img = Image.new("L", (cols * cw, rows * ch), 0)
    d = ImageDraw.Draw(img)
    for r, line in enumerate(text):
        for c, ch_glyph in enumerate(line):
            if ch_glyph == " ":
                continue
            d.text((c * cw + 1, r * ch), ch_glyph, font=f, fill=255)

    # bloom-ish: slight blur copy screened under the crisp glyphs (gives ink a glow)
    glow = img.filter(ImageFilter.GaussianBlur(2.2))
    img = Image.blend(glow, img, 0.55).point(lambda p: min(255, int(p * a.gain)))

    out = Image.new("RGB", img.size)
    if a.phosphor:
        pr, pg, pb = (int(x) for x in a.phosphor.split(","))
        px = img.load(); po = out.load()
        for y in range(img.size[1]):
            for x in range(img.size[0]):
                v = px[x, y] / 255.0
                po[x, y] = (int(pr * v), int(pg * v), int(pb * v))
    else:
        out = img.convert("RGB")

    if a.vignette > 0:
        w, h = out.size
        vx = Image.new("L", (w, h), 0)
        ImageDraw.Draw(vx).ellipse((-w * 0.25, -h * 0.25, w * 1.25, h * 1.25), fill=255)
        vx = vx.filter(ImageFilter.GaussianBlur(min(w, h) // 6)).point(lambda p: int(255 - (255 - p) * a.vignette))
        out = Image.composite(out, Image.new("RGB", (w, h), (0, 0, 0)), vx)

    out.save(a.out)
    print(f"{{'ok': true, 'cols': {cols}, 'rows': {rows}, 'size': [{out.size[0]}, {out.size[1]}], 'font': {str(font_path)!r}}}")

if __name__ == "__main__":
    main()
