"""Build three search-results mocks from the freshly built home page.

Each mock is the real home page with the Latest column's content replaced by search
results drawn with the components the Latest list already uses.
"""

import html as H
import json
import re
import shutil
import sys
from pathlib import Path

DIST = Path(sys.argv[1])
OUT = Path(sys.argv[2])
BASE = "/search-results"
QUERY = "tooth regrowth"
WORDS = re.compile(r"\b(tooth|teeth|regrow\w*|regenerat\w*)\b", re.I)

SLUGS = [
    "tooth-regrowth-usag1",
    "lab-grown-teeth-incisor-stem-cells",
    "whole-tooth-pulp-cell-tooth-germ",
    "whole-tooth-bioengineered-germ-dog",
    "whole-tooth-germ-splitting",
    "pulp-regeneration-baby-tooth-stem-cells",
    "enamel-regrowth-calcium-phosphate-gel",
    "enamel-regrowth-short-amelogenin-peptide",
    "dentine-repair-tideglusib",
    "regenerative-fillings-dentine",
    "periodontal-3d-printed-scaffold",
    "periodontal-maresin-resolvin-stem-cells",
]
CLOSE = 5  # how many count as "closest"

TOPIC_NAMES = {"mouth-and-teeth": "Mouth and teeth", "gum-disease": "Gum disease"}
STATUS_ORDER = [
    "Approved", "Phase 3 trial", "Phase 2 trial", "Phase 1 trial", "Trial registered",
    "Preclinical only", "No trial record found", "Failed", "Terminated", "Origin paper retracted",
]

page = (DIST / "index.html").read_text()
lookup = json.loads((DIST / "lookup.json").read_text())
claims = {c["page"].lstrip("/"): c for c in lookup["claims"].values()}

# --- assets ---------------------------------------------------------------
OUT.mkdir(parents=True, exist_ok=True)
for folder in ("_astro", "outlet-icons"):
    target = OUT / folder
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(DIST / folder, target)
for css in (OUT / "_astro").glob("*.css"):
    css.write_text(css.read_text().replace("/_astro/", f"{BASE}/_astro/"))
for name in ("favicon.svg", "favicon.ico", "mark.svg"):
    if (DIST / name).exists():
        shutil.copy(DIST / name, OUT / name)

# --- rows from the built list ---------------------------------------------
rows: dict[str, str] = {}
for match in re.finditer(r'<li class="day-row report-row".*?</li>(?=<li class="day-row|</ol>)', page, re.S):
    row = match.group(0)
    slug = re.search(r'<h4 class="row-title"><a[^>]*href="/([^"]+)"', row)
    if slug and slug.group(1) not in rows:
        rows[slug.group(1)] = row
missing = [s for s in SLUGS if s not in rows]
assert not missing, missing


def highlight_text(fragment: str) -> str:
    """Mark the searched words in text nodes only."""
    parts = re.split(r"(<[^>]+>)", fragment)
    return "".join(p if p.startswith("<") else WORDS.sub(r'<mark class="hit">\1</mark>', p) for p in parts)


def mark_row(row: str, *, compact: bool = False) -> str:
    row = re.sub(r'style="view-transition-name:[^"]*"', "", row)
    row = re.sub(
        r'(<h4 class="row-title">)(.*?)(</h4>)', lambda m: m.group(1) + highlight_text(m.group(2)) + m.group(3), row, flags=re.S
    )
    row = re.sub(
        r'(<span class="row-claim">)(.*?)(</span>)', lambda m: m.group(1) + highlight_text(m.group(2)) + m.group(3), row, flags=re.S
    )
    if compact:
        row = re.sub(r'<div class="row-more">.*?</div></div>', "", row, flags=re.S)
        row = row.replace('class="day-row report-row"', 'class="day-row report-row is-compact"')
    return row


def topic_of(slug: str) -> str:
    return re.search(r'data-topic="([^"]+)"', rows[slug]).group(1)


def track(place: int | None, places: int = 6) -> str:
    if not place:
        return ""
    steps = "".join(f'<span class="step{" here" if i == place else ""}"></span>' for i in range(1, places + 1))
    return (
        f'<span class="track"><span class="steps" role="img" aria-label="Place {place} of {places} on the path '
        f'from preclinical to approved">{steps}</span></span>'
    )


def esc(text: str) -> str:
    return H.escape(text, quote=False)


# --- shared page surgery ----------------------------------------------------
def frame(days_main: str, side: str, note: str, title: str) -> str:
    out = page
    out = re.sub(r"<script\b(?![^>]*application/ld\+json)[^>]*>.*?</script>", "", out, flags=re.S)
    out = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", out, flags=re.S)
    out = out.replace('placeholder="https://… or tooth regrowth"', f'value="{QUERY}" placeholder="https://… or tooth regrowth"')
    # The band's "Try" pills give way to the answer line.
    out = re.sub(
        r'<div class="under-box">.*?</div>',
        f'<div class="under-box"><p class="holds result-line">{note}</p></div>',
        out,
        count=1,
        flags=re.S,
    )
    # Replace the side column's topic group.
    start = out.find('<div class="side-group" hidden data-side-topics>')
    end = out.find("</div>", start) + len("</div>")
    out = out[:start] + side + out[end:]
    # Replace the Latest column.
    start = out.find('<div class="days-main">')
    depth = 0
    for m in re.finditer(r"<(/?)div\b", out[start:]):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            end = start + out[start:].find(">", m.start()) + 1
            break
    out = out[:start] + f'<div class="days-main search-mode">{days_main}</div>' + out[end:]
    # Drop the lists under the day-by-day list: the mock is about the column.
    cut = out.find('<h2 class="bar lists-title"')
    stop = out.find("</main>")
    out = out[:cut] + "</div></div></div>" + out[stop:]
    out = out.replace("</head>", f'<link rel="stylesheet" href="{BASE}/mock.css"></head>')
    out = out.replace("<body", '<body data-mock', 1)
    out = out.replace('"/_astro/', f'"{BASE}/_astro/').replace('"/outlet-icons/', f'"{BASE}/outlet-icons/')
    return out


def topic_side(counts: dict[str, int], total: int) -> str:
    items = [
        f'<li><button type="button" class="side-pick" aria-pressed="true">All results <span class="kind-count">{total}</span></button></li>'
    ]
    for topic, n in counts.items():
        items.append(
            f'<li><button type="button" class="side-pick" aria-pressed="false">{TOPIC_NAMES[topic]} '
            f'<span class="kind-count">{n}</span></button></li>'
        )
    return (
        '<div class="side-group"><h3>Results by topic</h3><ul>' + "".join(items) + "</ul>"
        '<p class="side-note">Other topics have no match for these words.</p></div>'
    )


counts: dict[str, int] = {}
for slug in SLUGS:
    counts[topic_of(slug)] = counts.get(topic_of(slug), 0) + 1
total = len(SLUGS)
q = f"“{esc(QUERY)}”"

CLEAR = '<a href="/" class="clear-search">Back to Latest</a>'


def select(label: str, options: list[str]) -> str:
    opts = "".join(f"<option>{o}</option>" for o in options)
    return f'<label class="pick"><span class="visually-hidden">{label}</span><select>{opts}</select></label>'


def head(title: str, aside: str) -> str:
    return (
        f'<div class="days-head"><h2 class="days-title" id="days-title">{title}</h2>'
        f'<p class="checked-on">{aside}</p></div>'
    )


# --- A: the Latest list, in results mode ------------------------------------
def mock_a() -> str:
    close = "".join(mark_row(rows[s]) for s in SLUGS[:CLOSE])
    rest = "".join(mark_row(rows[s]) for s in SLUGS[CLOSE:])
    main = (
        head(f"Results for {q}", f"{total} tracked claims · {CLEAR}")
        + '<div class="filters" role="group" aria-label="Narrow these results">'
        + select("Order", ["Best match", "Newest report", "Oldest report"])
        + select("Status", ["Any status", "Phase 1 trial (1)", "Trial registered (1)", "Preclinical only (8)", "No trial record found (1)", "Origin paper retracted (1)"])
        + "</div>"
        + '<p class="search-key">Matched words are marked. A match is a claim the site tracks, not every study on the subject.</p>'
        + '<div class="day-list">'
        + f'<section class="day-group"><div class="day-head"><h3>Closest matches</h3><span>{CLOSE} claims · the treatment or condition uses your words</span></div><ol>{close}</ol></section>'
        + f'<section class="day-group"><div class="day-head"><h3>Also matching</h3><span>{total - CLOSE} claims · your words appear in the report or the records</span></div><ol>{rest}</ol></section>'
        + "</div>"
    )
    note = f'{total} tracked claims match {q}, listed below in place of Latest. <a href="/">Clear</a>'
    return frame(main, topic_side(counts, total), note, "Search mock A · Results in the Latest list")


# --- B: grouped by where each stands ---------------------------------------
def mock_b() -> str:
    groups: dict[str, list[str]] = {}
    for slug in SLUGS:
        groups.setdefault(claims[slug]["status"], []).append(slug)
    ordered = [s for s in STATUS_ORDER if s in groups] + [s for s in groups if s not in STATUS_ORDER]
    jump = " · ".join(
        f'<a href="#g-{i}"><strong>{esc(s)}</strong> {len(groups[s])}</a>' for i, s in enumerate(ordered)
    )
    sections = "".join(
        f'<section class="day-group" id="g-{i}"><div class="day-head"><h3>{esc(s)}</h3>'
        f'<span>{len(groups[s])} claim{"s" if len(groups[s]) > 1 else ""}</span></div><ol>'
        + "".join(mark_row(rows[slug], compact=True) for slug in groups[s])
        + "</ol></section>"
        for i, s in enumerate(ordered)
    )
    main = (
        head(f"Results for {q}", f"{total} tracked claims · {CLEAR}")
        + f'<nav class="stand-jump" aria-label="Where the matches stand"><span class="stand-jump-label">On record now</span> {jump}</nav>'
        + '<p class="search-key">Grouped by status, from the furthest point on the path to preclinical, then ended. A group is a description of records, not a ranking of treatments.</p>'
        + f'<div class="day-list">{sections}</div>'
    )
    note = f'{total} tracked claims match {q}: 2 have a trial in people on record. <a href="/">Clear</a>'
    return frame(main, topic_side(counts, total), note, "Search mock B · Grouped by status")


# --- C: best match first, the rest compact -----------------------------------
def compact_line(slug: str) -> str:
    c = claims[slug]
    name = esc(c["names"][0]) if c.get("names") else ""
    return (
        '<li class="hit-row">'
        f'<div class="hit-now"><strong class="status-name">{esc(c["status"])}</strong>{track(c["place"])}</div>'
        f'<div class="hit-main"><a class="hit-title" href="/{slug}">{highlight_text(esc(c["headline"]))}</a>'
        f'<span class="hit-meta"><span>{highlight_text(name)} · {highlight_text(esc(c["indication"]))}</span>'
        f'<span class="row-topic">{TOPIC_NAMES[topic_of(slug)]}</span></span></div>'
        f'<span class="hit-when">{esc(c["first_reported"] or "")}</span>'
        "</li>"
    )


def mock_c() -> str:
    best = claims[SLUGS[0]]
    digest = (
        '<div class="digest found best">'
        '<div class="standing"><span class="row-label">Best match · on record now</span>'
        f'<span class="label">{esc(best["status"])}</span>{track(best["place"])}</div>'
        f'<div class="about"><h3>{highlight_text(esc(best["headline"]))}</h3>'
        f'<p>{esc(best["meaning"])}</p>'
        f'<p class="changed">{esc(best["names"][0])} · {esc(best["indication"])}. First reported {esc(best["first_reported"])}. '
        f'<a href="/{SLUGS[0]}">See the records</a></p></div></div>'
    )
    best_row = mark_row(rows[SLUGS[0]])
    main = (
        head(f"Results for {q}", f"{total} tracked claims · {CLEAR}")
        + digest
        + f'<ol class="best-report">{best_row}</ol>'
        + f'<div class="day-head hits-head"><h3>Other matches</h3><span>{total - 1} claims</span></div>'
        + '<ol class="hit-list">' + "".join(compact_line(s) for s in SLUGS[1:]) + "</ol>"
        + '<p class="search-more">Every claim on the subject: <a href="/topic/mouth-and-teeth">Mouth and teeth, 18 claims</a> · <a href="/topic/gum-disease">Gum disease, 8 claims</a></p>'
    )
    note = f'Best match for {q} is shown first, below. <a href="/">Clear</a>'
    return frame(main, topic_side(counts, total), note, "Search mock C · Best match first")


INDEX = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Search results mocks</title><link rel="stylesheet" href="/search-results/_astro/{css}"></head>
<body style="background:var(--ground);padding:2rem;font-family:var(--face)"><main style="max-width:44rem;margin:auto">
<h1>Search results: three mocks</h1><p>Query: “tooth regrowth”, real rows from the published export.</p>
<ul style="line-height:2">
<li><a href="a.html"><strong>A · Results in the Latest list.</strong></a> Same rows, same column; grouped Closest / Also matching; topic facets on the left.</li>
<li><a href="b.html"><strong>B · Grouped by status.</strong></a> Compact report rows under status headings, with a jump line of counts.</li>
<li><a href="c.html"><strong>C · Best match first.</strong></a> Digest panel and its report row, then the rest as one-line matches.</li>
</ul></main></body></html>"""

(OUT / "a.html").write_text(mock_a())
(OUT / "b.html").write_text(mock_b())
(OUT / "c.html").write_text(mock_c())
css = next(p.name for p in (OUT / "_astro").glob("global.*.css"))
(OUT / "index.html").write_text(INDEX.replace("{css}", css))
print("ok", counts)
