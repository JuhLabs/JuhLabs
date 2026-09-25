#!/usr/bin/env python3
"""Render the two profile stats cards as SVG with live numbers.

Same layout and colours as the original hand-made PNG cards (800x364, navy
card, cyan diamond and title, grey labels, white mono values), but the numbers
come from the GitHub API so they never go stale. Runs in the daily workflow
and publishes to the `output` branch next to the contribution snake.

    GITHUB_TOKEN=... python3 scripts/render_cards.py dist/
"""
import datetime
import json
import os
import sys
import urllib.request

USER = "JuhLabs"
REPO = "juhradial-mx"
BG, BORDER, ACCENT, LABEL, VALUE = "#0e1420", "#1a435c", "#38bdf8", "#a9b3c2", "#f1f5f9"
SANS = "-apple-system, 'Segoe UI', Inter, Roboto, Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace"


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}", headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "JuhLabs-profile-cards",
        **({"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"} if os.environ.get("GITHUB_TOKEN") else {}),
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp), resp.headers


def paged_count(path, keep=lambda item: True):
    count, page = 0, 1
    while True:
        items, _ = api(f"{path}{'&' if '?' in path else '?'}per_page=100&page={page}")
        count += sum(1 for item in items if keep(item))
        if len(items) < 100:
            return count
        page += 1


def esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;")


def card(title, subtitle, rows):
    y0 = 118 if subtitle else 118
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="364" viewBox="0 0 800 364" role="img" aria-label="{esc(title)}">',
        f'<rect x="1" y="1" width="798" height="362" rx="18" fill="{BG}" stroke="{BORDER}" stroke-width="2"/>',
        f'<rect x="47" y="51" width="14" height="14" transform="rotate(45 54 58)" fill="{ACCENT}"/>',
        f'<text x="82" y="67" font-family="{SANS}" font-size="28" font-weight="700" fill="{ACCENT}">{esc(title)}</text>',
    ]
    if subtitle:
        lines.append(f'<text x="46" y="107" font-family="{SANS}" font-size="21" fill="{LABEL}">{esc(subtitle)}</text>')
        y0 = 170
    for i, (label, value) in enumerate(rows):
        y = y0 + i * 46
        lines.append(f'<text x="46" y="{y}" font-family="{SANS}" font-size="24" fill="{LABEL}">{esc(label)}</text>')
        lines.append(f'<text x="754" y="{y}" text-anchor="end" font-family="{MONO}" font-size="24" font-weight="600" fill="{VALUE}">{esc(value)}</text>')
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def main(out_dir):
    user, _ = api(f"/users/{USER}")
    repo, _ = api(f"/repos/{USER}/{REPO}")
    repos, _ = api(f"/users/{USER}/repos?per_page=100&type=owner")
    stars_earned = sum(r["stargazers_count"] for r in repos if not r["fork"])
    external = paged_count(f"/repos/{USER}/{REPO}/contributors",
                           lambda c: c.get("type") == "User" and c["login"] != USER)
    since = datetime.datetime.strptime(user["created_at"][:10], "%Y-%m-%d").strftime("%b %Y")

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "card-github.svg"), "w", encoding="utf-8") as f:
        f.write(card("GitHub", None, [
            ("Stars earned", stars_earned),
            ("Public repositories", user["public_repos"]),
            ("Followers", user["followers"]),
            ("Member since", since),
        ]))
    with open(os.path.join(out_dir, "card-juhradial.svg"), "w", encoding="utf-8") as f:
        f.write(card(REPO, "Logi Options+ alternative for Linux", [
            ("Stars", repo["stargazers_count"]),
            ("Forks", repo["forks_count"]),
            ("External contributors", external),
            ("Stack", "Rust · Python"),
        ]))
    print(f"cards: stars_earned={stars_earned} repo_stars={repo['stargazers_count']} forks={repo['forks_count']} external={external} followers={user['followers']}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dist")
