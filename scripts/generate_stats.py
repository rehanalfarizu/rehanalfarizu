"""Membuat kartu statistik GitHub (assets/stats.svg dan assets/langs.svg).

Hanya membaca data publik lewat GitHub GraphQL API, jadi tidak bergantung
pada layanan pihak ketiga yang sering kena batas kuota.

Pemakaian:
    GITHUB_TOKEN=... python scripts/generate_stats.py
"""
import json
import os
import urllib.request
from xml.sax.saxutils import escape

USERNAME = os.environ.get("GH_USERNAME", "rehanalfarizu")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")

QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    pullRequests { totalCount }
    issues { totalCount }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar { totalContributions }
    }
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""

BG, TITLE, TEXT, ICON = "#1a1b27", "#70a5fd", "#38bdae", "#bf91f3"
FONT = "Segoe UI, Ubuntu, Helvetica, Arial, sans-serif"


def fetch():
    token = os.environ["GITHUB_TOKEN"]
    body = json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if "errors" in data:
        raise SystemExit(f"GraphQL error: {data['errors']}")
    return data["data"]["user"]


def filter_languages(sizes):
    """Pilih bahasa yang ditampilkan di kartu.

    sizes: dict nama bahasa -> jumlah byte, dijumlah dari semua repo publik.
    Kembalikan dict dengan format yang sama.
    """
    # TODO(human): tentukan bahasa mana yang dibuang atau dibobot ulang.
    return sizes


def stats_card(user):
    repos = user["repositories"]
    cc = user["contributionsCollection"]
    stars = sum(r["stargazerCount"] for r in repos["nodes"])
    rows = [
        ("Total Stars", stars),
        ("Commit (tahun ini)", cc["totalCommitContributions"]),
        ("Pull Request", user["pullRequests"]["totalCount"]),
        ("Issue", user["issues"]["totalCount"]),
        ("Repo Publik", repos["totalCount"]),
    ]
    total = cc["contributionCalendar"]["totalContributions"]
    name = escape(user["name"] or USERNAME)
    lines = "".join(
        f'<circle cx="32" cy="{66 + i*25}" r="4" fill="{ICON}"/>'
        f'<text x="46" y="{71 + i*25}" fill="{TEXT}" font-size="14" font-weight="600">{escape(label)}:</text>'
        f'<text x="250" y="{71 + i*25}" fill="{TEXT}" font-size="14" font-weight="700">{value:,}</text>'
        for i, (label, value) in enumerate(rows)
    )
    circ = 2 * 3.1416 * 42
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="495" height="195" viewBox="0 0 495 195" font-family="{FONT}">
<rect width="495" height="195" rx="8" fill="{BG}"/>
<text x="25" y="36" fill="{TITLE}" font-size="18" font-weight="700">Statistik GitHub {name}</text>
{lines}
<circle cx="400" cy="112" r="42" fill="none" stroke="{TITLE}" stroke-opacity=".2" stroke-width="6"/>
<circle cx="400" cy="112" r="42" fill="none" stroke="{TITLE}" stroke-width="6" stroke-linecap="round"
  stroke-dasharray="{circ:.1f}" stroke-dashoffset="0" transform="rotate(-90 400 112)">
  <animate attributeName="stroke-dashoffset" from="{circ:.1f}" to="0" dur="1.5s" fill="freeze"/>
</circle>
<text x="400" y="118" text-anchor="middle" fill="{TITLE}" font-size="20" font-weight="800">{total:,}</text>
<text x="400" y="175" text-anchor="middle" fill="{TEXT}" font-size="11">kontribusi tahun ini</text>
</svg>'''


def langs_card(user):
    sizes, colors = {}, {}
    for repo in user["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            lang = edge["node"]["name"]
            sizes[lang] = sizes.get(lang, 0) + edge["size"]
            colors[lang] = edge["node"]["color"] or "#888888"
    sizes = filter_languages(sizes)
    top = sorted(sizes.items(), key=lambda kv: kv[1], reverse=True)[:6]
    total = sum(v for _, v in top) or 1
    bar, x = [], 25.0
    for lang, size in top:
        w = 300 * size / total
        bar.append(f'<rect x="{x:.2f}" y="52" width="{w:.2f}" height="10" fill="{colors.get(lang, "#888888")}"/>')
        x += w
    items = "".join(
        f'<circle cx="{30 + (i % 2)*165}" cy="{91 + (i//2)*28}" r="5" fill="{colors.get(lang, "#888888")}"/>'
        f'<text x="{42 + (i % 2)*165}" y="{96 + (i//2)*28}" fill="{TEXT}" font-size="12">{escape(lang)} {100*size/total:.1f}%</text>'
        for i, (lang, size) in enumerate(top)
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="350" height="195" viewBox="0 0 350 195" font-family="{FONT}">
<rect width="350" height="195" rx="8" fill="{BG}"/>
<text x="25" y="36" fill="{TITLE}" font-size="18" font-weight="700">Bahasa Terbanyak</text>
<clipPath id="bar"><rect x="25" y="52" width="300" height="10" rx="5"/></clipPath>
<g clip-path="url(#bar)">{"".join(bar)}</g>
{items}
</svg>'''


def main():
    user = fetch()
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, svg in (("stats.svg", stats_card(user)), ("langs.svg", langs_card(user))):
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as f:
            f.write(svg)
        print("ditulis", name)


if __name__ == "__main__":
    main()
