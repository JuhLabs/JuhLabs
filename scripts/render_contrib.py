#!/usr/bin/env python3
"""Render the contribution calendar as an animated SVG: a pulse travels through
every contribution day in date order, drawing a trace behind it, and each
square ignites as the pulse reaches it. A small rotating Actions Ring rides on
the pulse head (JuhRadial MX). Dark and light variants; loops every 12 s.

    GITHUB_TOKEN=... python3 scripts/render_contrib.py dist/
"""
import json
import math
import os
import sys
import urllib.request

USER = "JuhLabs"
CELL, GAP, X0, Y0 = 12, 3, 28, 34
STEP = CELL + GAP
T, DRAW = 12.0, 0.85          # cycle seconds, fraction spent drawing
W, H = X0 + 53 * STEP + 16, Y0 + 7 * STEP + 34

THEMES = {
    "dark": dict(empty="#161b22", ramp=["#0b3d55", "#0e6b91", "#1ea9df", "#7fe0ff"], text="#a9b3c2",
                 accent="#38bdf8", core="#ffffff", trace="#38bdf8"),
    "light": dict(empty="#ebedf0", ramp=["#bfe9fb", "#7fd3f5", "#22a9e0", "#0a5f85"], text="#57606a",
                  accent="#0a7fb3", core="#ffffff", trace="#0ea5e9"),
}
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace"


def calendar():
    query = '{ user(login:"%s"){ contributionsCollection{ contributionCalendar{ totalContributions weeks{ contributionDays{ date contributionCount weekday } } } } } }' % USER
    req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps({"query": query}).encode(),
                                 headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                                          "User-Agent": "JuhLabs-profile", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return cal["totalContributions"], cal["weeks"]


def render(theme, total, weeks):
    t = THEMES[theme]
    cells, active, months = [], [], []
    peak = max((d["contributionCount"] for w in weeks for d in w["contributionDays"]), default=1) or 1
    seen_month = None
    for wi, week in enumerate(weeks):
        for day in week["contributionDays"]:
            x, y = X0 + wi * STEP, Y0 + day["weekday"] * STEP
            n = day["contributionCount"]
            month = day["date"][:7]
            if day["weekday"] == 0 or wi == 0:
                if month != seen_month:
                    seen_month = month
                    months.append((x, day["date"]))
            if n > 0:
                level = min(3, int(math.ceil(n / peak * 4)) - 1)
                active.append((x + CELL / 2, y + CELL / 2, x, y, t["ramp"][max(0, level)], n, day["date"]))
            else:
                cells.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" fill="{t["empty"]}"/>')

    # Cumulative path length through the active cells, in date order.
    cum, total_len = [0.0], 0.0
    for (ax, ay, *_), (bx, by, *_) in zip(active, active[1:]):
        total_len += math.hypot(bx - ax, by - ay)
        cum.append(total_len)
    total_len = total_len or 1.0

    css = [f".m{{font:10px {MONO};fill:{t['text']}}} .cap{{font:11px {MONO};fill:{t['text']}}} .brand{{font:600 11px {MONO};fill:{t['accent']}}}",
           ".cell{transform-box:fill-box;transform-origin:center}",
           f"#trace{{stroke-dasharray:{total_len:.1f};animation:draw {T}s linear infinite}}",
           f"@keyframes draw{{0%{{stroke-dashoffset:{total_len:.1f};opacity:.9}}{DRAW*100:.0f}%{{stroke-dashoffset:0;opacity:.9}}{DRAW*100+4:.0f}%{{opacity:.9}}100%{{stroke-dashoffset:0;opacity:0}}}}",
           f"#head{{animation:head {T}s linear infinite}} @keyframes head{{0%,{DRAW*100:.0f}%{{opacity:1}}{DRAW*100+3:.0f}%,100%{{opacity:0}}}}"]
    rects = []
    for i, (cx, cy, x, y, color, n, date) in enumerate(active):
        p = DRAW * 100 * cum[i] / total_len
        pop, settle, hold, fade = min(p + 1.2, 88), min(p + 4.5, 89), 89, 100
        css.append(f"@keyframes k{i}{{0%,{p:.2f}%{{opacity:.28;transform:scale(1)}}{pop:.2f}%{{opacity:1;transform:scale(1.65)}}"
                   f"{settle:.2f}%{{opacity:1;transform:scale(1)}}{hold}%{{opacity:1}}{fade}%{{opacity:.28}}}}")
        css.append(f".a{i}{{animation:k{i} {T}s linear infinite}}")
        rects.append(f'<rect class="cell a{i}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" fill="{color}"><title>{date}: {n} contributions</title></rect>')

    path_d = " ".join(("M" if i == 0 else "L") + f"{cx:.1f},{cy:.1f}" for i, (cx, cy, *_) in enumerate(active)) or "M0,0"
    ring = "".join(f'<path d="M0,-11 A11,11 0 0 1 {11*math.sin(math.pi/4):.2f},{-11*math.cos(math.pi/4):.2f}" transform="rotate({k*45})" '
                   f'fill="none" stroke="{t["accent"]}" stroke-width="2" stroke-linecap="round" opacity="{0.35 + 0.65*(k%2)}"/>' for k in range(8))
    labels = "".join(f'<text class="m" x="{x}" y="22">{__import__("datetime").date.fromisoformat(d).strftime("%b")}</text>' for x, d in months)
    caption = f'<text class="cap" x="{X0}" y="{H-12}">{total} contributions in the last year, lit in the order they happened</text>'
    brand = f'<text class="brand" x="{W-16}" y="{H-12}" text-anchor="end">JuhLabs</text>'
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Contribution calendar, animated">',
        "<style>" + "\n".join(css) + "</style>",
        f'<defs><filter id="glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="3.5"/></filter></defs>',
        labels, *cells,
        f'<path id="trace" d="{path_d}" fill="none" stroke="{t["trace"]}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>',
        *rects,
        f'<g id="head"><g><animateMotion dur="{T}s" repeatCount="indefinite" calcMode="linear" keyPoints="0;1;1" keyTimes="0;{DRAW};1"><mpath href="#trace"/></animateMotion>'
        f'<circle r="8" fill="{t["accent"]}" opacity=".8" filter="url(#glow)"/>'
        f'<g><animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="3s" repeatCount="indefinite"/>{ring}</g>'
        f'<circle r="3" fill="{t["core"]}"/></g></g>',
        caption, brand, "</svg>"]) + "\n"


def main(out_dir):
    total, weeks = calendar()
    os.makedirs(out_dir, exist_ok=True)
    for theme in THEMES:
        with open(os.path.join(out_dir, f"contrib-{theme}.svg"), "w", encoding="utf-8") as f:
            f.write(render(theme, total, weeks))
    print(f"contrib: total={total} weeks={len(weeks)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dist")
