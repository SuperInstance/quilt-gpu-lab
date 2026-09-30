#!/usr/bin/env python3
"""Emit a standalone HTML view of MQ1 (growth-vs-fixed) + CG1/CG1b (canon gate).

Reads results/*.json; writes viz/mq1-cg1.html. No dependencies, inline SVG.
Run: python3 experiments/viz_mq1_cg1.py  (from quilt-gpu-lab root)
"""
import json
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")
VIZ = os.path.join(ROOT, "viz")
CANON_LADDER = [0.030, 0.050, 0.300, 0.240, 0.930, 0.930, 0.940, 0.940, 0.920]

C = {"fixed": "#3b82f6", "grown": "#f59e0b", "canon": "#94a3b8",
     "cg1": "#ef4444", "logit": "#8b5cf6", "anchored": "#10b981",
     "ink": "#0f172a", "grid": "#e2e8f0"}


def svg_lines(series, w=620, h=260, pad=40, ymax=None, title=""):
    """series: list of (label, color, [ (x_index, value), ... ])"""
    xs = [x for _, _, pts in series for x, _ in pts]
    ys = [y for _, _, pts in series for _, y in pts if y is not None]
    if not xs or not ys:
        return "<p><em>no data</em></p>"
    x0, x1 = min(xs), max(xs)
    y0, y1 = 0.0, ymax if ymax else max(ys) * 1.15
    sx = lambda x: pad + (x - x0) / max(1e-9, (x1 - x0)) * (w - 2 * pad)
    sy = lambda y: h - pad - (y - y0) / max(1e-9, (y1 - y0)) * (h - 2 * pad)
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px">']
    out.append(f'<rect x="0" y="0" width="{w}" height="{h}" fill="white"/>')
    for i in range(5):
        gy = pad + i * (h - 2 * pad) / 4
        out.append(f'<line x1="{pad}" y1="{gy:.1f}" x2="{w-pad}" y2="{gy:.1f}" stroke="{C["grid"]}"/>')
    for label, color, pts in series:
        d = " ".join(f"{'M' if i == 0 else 'L'}{sx(x):.1f},{sy(y):.1f}"
                     for i, (x, y) in enumerate(pts) if y is not None)
        out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        for x, y in pts:
            if y is not None:
                out.append(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="3" fill="{color}"/>')
    lx = pad + 6
    for label, color, _ in series:
        out.append(f'<text x="{lx}" y="20" font-size="12" fill="{color}" '
                   f'font-family="ui-sans-serif">{label}</text>')
        lx += 8 + 7 * len(label)
    out.append(f'<text x="{pad}" y="{h-10}" font-size="11" fill="#64748b" '
               f'font-family="ui-sans-serif">{title}</text>')
    out.append("</svg>")
    return "".join(out)


def bar_svg(items, w=620, h=200, pad=40, title=""):
    """items: list of (label, value, color)"""
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px">']
    vmax = max([abs(v) for _, v, _ in items] + [1e-9])
    bw = (w - 2 * pad) / max(1, len(items))
    for i, (label, v, color) in enumerate(items):
        bh = (h - 2 * pad) * (v / vmax if vmax else 0)
        x = pad + i * bw + bw * 0.15
        out.append(f'<rect x="{x:.1f}" y="{h-pad-bh:.1f}" width="{bw*0.7:.1f}" '
                   f'height="{bh:.1f}" fill="{color}" rx="3"/>')
        out.append(f'<text x="{x+bw*0.35:.1f}" y="{h-pad-bh-5:.1f}" font-size="10" '
                   f'text-anchor="middle" fill="{C["ink"]}" font-family="ui-sans-serif">'
                   f'{v:.4f}</text>')
        out.append(f'<text x="{x+bw*0.35:.1f}" y="{h-pad+14:.1f}" font-size="10" '
                   f'text-anchor="middle" fill="#64748b" font-family="ui-sans-serif">'
                   f'{label}</text>')
    out.append(f'<text x="{pad}" y="{h-4}" font-size="11" fill="#64748b" '
               f'font-family="ui-sans-serif">{title}</text>')
    out.append("</svg>")
    return "".join(out)


def load(path):
    p = os.path.join(ROOT, path)
    return json.load(open(p)) if os.path.exists(p) else None


def card(title, verdict, lines, tone="#0f172a"):
    body = "".join(f"<li>{l}</li>" for l in lines)
    return (f'<div class="card"><h3>{title}</h3>'
            f'<div class="verdict" style="border-color:{tone};color:{tone}">{verdict}</div>'
            f'<ul>{body}</ul></div>')


def main():
    os.makedirs(VIZ, exist_ok=True)
    panels, cards = [], []

    shadow = load("results/mq1/mq1_shadow_results.json")
    scalar = load("results/mq1/mq1_scalar_results.json")

    for name, data, note in (("MQ1 shadow (RTX 4050)", shadow, "CUDA, 4000 steps, Adam 1e-3"),
                             ("MQ1 scalar (CPU micrograd-quilt)", scalar,
                              "3000 steps, SGD, quilt tape witness")):
        if not data:
            panels.append(f"<h2>{name}</h2><p><em>run not finished yet</em></p>")
            continue
        s = data["summary"]
        series = []
        for arm, color in (("fixed", C["fixed"]), ("grown", C["grown"])):
            runs = [r for r in data["runs"] if r["arm"] == arm]
            for r in runs:
                pts = [(h["step"], h["val"]) for h in r["history"]]
                series.append((f"{arm} s{r['seed']}", color, pts))
        panels.append(f"<h2>{name} — held-out MSE by step</h2>{svg_lines(series, title=note)}")
        panels.append(bar_svg([("fixed med", s["median_fixed"], C["fixed"]),
                               ("grown med", s["median_grown"], C["grown"])],
                              title=f"median held-out MSE — ratio {s['ratio']:.4f}"))
        lines = [f"fixed seeds: {[round(v,5) for v in s['fixed_vals']]}",
                 f"grown seeds: {[round(v,5) for v in s['grown_vals']]}",
                 f"grafts total: {s.get('total_grafts')}"]
        if "fabric_verdict" in s:
            lines.append(f"gradient fabric: {s['fabric_verdict']} "
                         f"(graft drift {s['graft_drift_median']} vs control "
                         f"{s['control_drift_median']})")
        cards.append(card(name, s["verdict"], lines,
                          tone="#10b981" if s["verdict"] == "TIE" else "#f59e0b"))

    cg1 = load("results/cg1/cg1_results.json")
    cg1b = load("results/cg1/cg1b_results.json")
    if cg1:
        s = cg1["summary"]
        series = [("canon oracle", C["canon"], list(enumerate(CANON_LADDER, 1))),
                  ("local 1.5B (free text)", C["cg1"],
                   [(i, v) for i, v in enumerate(s["ladder"], 1) if v is not None])]
        if cg1b:
            series.append(("local 1.5B (logit)", C["logit"],
                           [(i, v) for i, v in enumerate(cg1b["raw_ladder_logit"], 1)
                            if v is not None]))
            series.append(("local 1.5B (anchored)", C["anchored"],
                           [(i, v) for i, v in enumerate(cg1b["raw_ladder_anchored"], 1)
                            if v is not None]))
        panels.append("<h2>CG1 — evidence ladder: canon oracle vs local oracles</h2>"
                      + svg_lines(series, ymax=1.0,
                                  title="rung 5 = the append-only guarantee (the canon's "
                                        "+0.690 flip)"))
        cards.append(card("Canon gate on a local 1.5B", s["verdict"],
                          [f"gates: {s['gates']}",
                           f"step rung4->5: {round(s['step_rung4_to_5'],3)} (canon +0.690)",
                           f"0.5B ladder: all {set(s['ladder_small'])}"],
                          tone="#ef4444"))
    if cg1b:
        cards.append(card("CG1b — elicitation hardening", cg1b["verdict"],
                          [f"logit step {round(cg1b['modes']['logit']['step'],3)}, "
                           f"anchored step {round(cg1b['modes']['anchored']['step'],3)}",
                           "exploratory (post-hoc): anchored flip lands on the MECHANISM "
                           "rung, not the guarantee rung"],
                          tone="#ef4444"))

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>MQ1 + CG1 — quilt-gpu-lab</title>
<style>
 body{{font-family:ui-sans-serif,system-ui,sans-serif;margin:0;padding:28px;
   background:#f8fafc;color:{C['ink']}}}
 h1{{font-size:22px;margin:0 0 4px}} h2{{font-size:15px;margin:22px 0 6px;color:#334155}}
 .sub{{color:#64748b;font-size:13px;margin-bottom:18px}}
 .cards{{display:flex;gap:14px;flex-wrap:wrap;margin-top:8px}}
 .card{{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;
   max-width:340px;box-shadow:0 1px 2px rgba(15,23,42,.04)}}
 .card h3{{margin:0 0 6px;font-size:13px;color:#475569;font-weight:600}}
 .verdict{{font-weight:700;border-left:3px solid;padding-left:8px;margin:4px 0 8px;
   font-size:15px}}
 .card ul{{margin:0;padding-left:16px}} .card li{{font-size:12px;color:#475569;margin:2px 0}}
 .panel{{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:12px;
   margin-bottom:14px}}
</style></head><body>
<h1>MQ1 growth-vs-fixed &middot; CG1 canon-gate portability</h1>
<div class="sub">Standalone view generated from results/*.json &mdash; no server, no deps.
Read the verdict cards first, then the curves.</div>
<div class="cards">{''.join(cards)}</div>
<div class="panel">{''.join(panels)}</div>
</body></html>"""
    out = os.path.join(VIZ, "mq1-cg1.html")
    open(out, "w").write(html)
    print("wrote", out, f"({len(html)} bytes)")


if __name__ == "__main__":
    main()
