import os, json, html, datetime, urllib.request
from collections import Counter

TOKEN = os.environ["GH_TOKEN"]
LOGIN = os.environ.get("GH_LOGIN", "fer-gc05")

BG, BORDER = "#0d1117", "#30363d"
GREEN, TEXT, MUTED, TRACK = "#00ff41", "#c9d1d9", "#8b949e", "#161b22"
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"


def gql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(json.dumps(data["errors"], indent=2))
    return data["data"]


MAIN_Q = """
query($login:String!){
  user(login:$login){
    createdAt
    pullRequests{ totalCount }
    issues{ totalCount }
    repositoriesContributedTo(first:1, contributionTypes:[COMMIT,ISSUE,PULL_REQUEST,REPOSITORY]){ totalCount }
    repositories(first:100, ownerAffiliations:OWNER, isFork:false){
      nodes{ stargazerCount primaryLanguage{ name } }
    }
  }
}"""

YEAR_Q = """
query($login:String!,$from:DateTime!,$to:DateTime!){
  user(login:$login){
    contributionsCollection(from:$from, to:$to){
      totalCommitContributions
      restrictedContributionsCount
    }
  }
}"""

user = gql(MAIN_Q, {"login": LOGIN})["user"]
repos = user["repositories"]["nodes"]

stars = sum(r["stargazerCount"] for r in repos)
prs = user["pullRequests"]["totalCount"]
issues = user["issues"]["totalCount"]
contributed = user["repositoriesContributedTo"]["totalCount"]

# Commits de todos los años desde que creaste la cuenta
commits = 0
start_year = int(user["createdAt"][:4])
for y in range(start_year, datetime.date.today().year + 1):
    c = gql(YEAR_Q, {
        "login": LOGIN,
        "from": f"{y}-01-01T00:00:00Z",
        "to": f"{y}-12-31T23:59:59Z",
    })["user"]["contributionsCollection"]
    commits += c["totalCommitContributions"] + c["restrictedContributionsCount"]

# Lenguajes por cantidad de repos
langs = Counter(r["primaryLanguage"]["name"] for r in repos if r["primaryLanguage"])
total_l = sum(langs.values()) or 1
top = langs.most_common(5)


def svg_wrap(title, body, w=420, h=200):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{html.escape(title)}">
  <rect x="0.5" y="0.5" rx="10" width="{w-1}" height="{h-1}" fill="{BG}" stroke="{BORDER}"/>
  <text x="24" y="38" font-family="{FONT}" font-size="16" font-weight="700" fill="{GREEN}">&gt; {html.escape(title)}</text>
  <line x1="24" y1="50" x2="{w-24}" y2="50" stroke="{BORDER}"/>
{body}
</svg>"""


# Tarjeta 1: stats
rows = [
    ("commits", commits),
    ("pull_requests", prs),
    ("issues", issues),
    ("stars", stars),
    ("contributed_to", contributed),
]
body = ""
for i, (label, value) in enumerate(rows):
    y = 80 + i * 24
    body += (
        f'  <text x="24" y="{y}" font-family="{FONT}" font-size="13" fill="{GREEN}">[+]</text>\n'
        f'  <text x="56" y="{y}" font-family="{FONT}" font-size="13" fill="{MUTED}">{label}</text>\n'
        f'  <text x="396" y="{y}" text-anchor="end" font-family="{FONT}" font-size="13" font-weight="700" fill="{TEXT}">{value:,}</text>\n'
    )
stats_svg = svg_wrap("stats", body)

# Tarjeta 2: top lenguajes
body = ""
opacities = [1, 0.8, 0.62, 0.46, 0.32]
bar_x, bar_w = 130, 190
top_pct = top[0][1] / total_l * 100 if top else 1
for i, (name, count) in enumerate(top):
    y = 80 + i * 24
    pct = count / total_l * 100
    w = max(4, bar_w * pct / top_pct)
    body += (
        f'  <text x="24" y="{y}" font-family="{FONT}" font-size="13" fill="{MUTED}">{html.escape(name)}</text>\n'
        f'  <rect x="{bar_x}" y="{y-10}" width="{bar_w}" height="10" rx="2" fill="{TRACK}"/>\n'
        f'  <rect x="{bar_x}" y="{y-10}" width="{w:.1f}" height="10" rx="2" fill="{GREEN}" fill-opacity="{opacities[i]}"/>\n'
        f'  <text x="396" y="{y}" text-anchor="end" font-family="{FONT}" font-size="13" fill="{TEXT}">{pct:.0f}%</text>\n'
    )
langs_svg = svg_wrap("top_langs", body)

os.makedirs("assets", exist_ok=True)
open("assets/stats.svg", "w", encoding="utf-8").write(stats_svg)
open("assets/langs.svg", "w", encoding="utf-8").write(langs_svg)
print("OK:", commits, prs, issues, stars, contributed, top)
