"""Mocks D, E and F: claim-focused search that says what matched.

Run after make_mocks.py, from the repository root:
    python3 .impeccable/mocks/search-results/make_match_mocks.py site/dist site/data/published-export.json .impeccable/mocks/search-results

The query is "regrowing teeth". Every claim, report, trial and date is from the
published export, except the one post marked "Example post", which shows how a post
on a social site would be drawn: no post is on record yet.
"""

import html as H
import json
import re
import sys
from pathlib import Path

DIST, EXPORT, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
BASE = "/search-results"
QUERY = "regrowing teeth"
STEMS = ["regrow", "regenerat", "teeth", "tooth"]  # what the index's stemming would match
WORD = re.compile(r"(?<![\w])(" + "|".join(STEMS) + r")\w*", re.I)

page = (DIST / "index.html").read_text()
lookup = json.loads((DIST / "lookup.json").read_text())
export = {c["slug"]: c for c in json.loads(EXPORT.read_text())["claims"]}
topics = lookup["topics"]
places = lookup["places"]
claims = {slug: {**c, "slug": slug} for slug, c in lookup["claims"].items()}

ICON = {
    "report": '<path d="M15 18h-5"/><path d="M18 14h-8"/><path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-4 0v-9a2 2 0 0 1 2-2h2"/><rect width="8" height="4" x="10" y="6" rx="1"/>',
    "trial": '<rect width="8" height="4" x="8" y="2" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="M12 11h4"/><path d="M12 16h4"/><path d="M8 11h.01"/><path d="M8 16h.01"/>',
    "post": '<path d="M22 17a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 2 21.286V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2z"/>',
    "claim": '<path d="m10.5 20.5 10-10a4.95 4.95 0 1 0-7-7l-10 10a4.95 4.95 0 1 0 7 7Z"/><path d="m8.5 8.5 7 7"/>',
}
KIND_WORD = {"report": "Report headline", "post": "Post", "trial": "Trial", "claim": "Treatment or condition"}


def icon(kind: str) -> str:
    return (
        f'<svg class="match-kind" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICON[kind]}</svg>'
    )


def esc(text: str) -> str:
    return H.escape(text or "", quote=False)


def marked(text: str) -> str:
    return WORD.sub(r'<mark class="hit">\1</mark>', esc(text)).replace("</mark>", "</mark>")


MARKING = True


def marked_full(text: str) -> str:
    """Mark the whole word each stem starts."""
    if not MARKING:
        return esc(text)
    return re.sub(r"(?<![\w])((?:" + "|".join(STEMS) + r")\w*)", r'<mark class="hit">\1</mark>', esc(text), flags=re.I)


def hits(text: str) -> set[str]:
    return {m.group(1).lower()[:5] for m in WORD.finditer(text or "")}


def fmt(date: str | None) -> str:
    if not date:
        return ""
    months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    y, m, d = date.split("-")
    return f"{int(d)} {months[int(m) - 1]} {y}"


def balanced(source: str, start: int, tag: str) -> str:
    depth = 0
    for m in re.finditer(rf"<(/?){tag}\b", source[start:]):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return source[start : start + source[start:].find(">", m.start()) + 1]
    raise ValueError(tag)


# The outlet as the list draws it (icon, name linking out, domain), by report address.
outlets: dict[str, str] = {}
for m in re.finditer(r'<span class="outlet">', page):
    fragment = balanced(page, m.start(), "span")
    href = re.search(r'<a href="([^"]+)"', fragment)
    if href:
        outlets.setdefault(href.group(1), fragment)

# Full report rows, by claim page, for F.
rows: dict[str, str] = {}
for match in re.finditer(r'<li class="day-row report-row".*?</li>(?=<li class="day-row|</ol>)', page, re.S):
    slug = re.search(r'<h4 class="row-title"><a[^>]*href="/([^"]+)"', match.group(0))
    if slug:
        rows.setdefault(slug.group(1), re.sub(r'style="view-transition-name:[^"]*"', "", match.group(0)))

# What a post would look like. Not on record: marked so wherever it is drawn.
EXAMPLE_POST = {
    "slug": "tooth-regrowth-usag1",
    "platform": "X",
    "author": "@example_account",
    "title": "Scientists are regrowing teeth with a drug, and human trials have begun",
    "date": "2024-10-08",
}


def reasons(slug: str) -> list[dict]:
    """Every thing about a claim that the search words hit, strongest first."""
    c, e = claims[slug], export[slug]
    found = []
    for article in e["articles"]:
        if hits(article["title"]):
            found.append({"kind": "report", "text": article["title"], "url": article["url"], "date": article["published_date"], "outlet": article["outlet"]})
    if slug == EXAMPLE_POST["slug"]:
        found.append({"kind": "post", "text": EXAMPLE_POST["title"], "date": EXAMPLE_POST["date"], "example": True})
    for trial in e["trials"]:
        if hits(trial.get("title") or ""):
            found.append({"kind": "trial", "text": trial["title"], "id": trial["trial_id"]})
    treat = " · ".join([c["names"][0], c["indication"]])
    if hits(treat) or hits(c["headline"]):
        found.append({"kind": "claim", "text": c["headline"] if hits(c["headline"]) else treat})
    found.sort(key=lambda r: (-len(hits(r["text"])), ["report", "post", "trial", "claim"].index(r["kind"])))
    return found


ranked = sorted(
    (s for s in claims if claims[s].get("topic") in ("mouth-and-teeth", "gum-disease") and reasons(s)),
    key=lambda s: (-max(len(hits(r["text"])) for r in reasons(s)), -len(reasons(s)), s),
)[:10]
total = len(ranked)


def trial_line(slug: str) -> list[dict]:
    """The claim's trials, as the list's registry rows name them."""
    out = []
    for event in export[slug]["events"]:
        if event.get("trial_id") and event["type"] == "trial_registered":
            out.append(event)
    return out


def track(place: int | None) -> str:
    if not place:
        return ""
    steps = "".join(f'<span class="step{" here" if i == place else ""}"></span>' for i in range(1, places + 1))
    return f'<span class="track"><span class="steps" role="img" aria-label="Place {place} of {places} on the path from preclinical to approved">{steps}</span></span>'


def reason_line(r: dict, *, compact: bool = True) -> str:
    kind = r["kind"]
    label = KIND_WORD[kind]
    if kind == "report":
        source = f'<span class="match-source">{esc(r["outlet"])} · {fmt(r["date"])}</span>'
        text = f'<a href="{esc(r["url"])}">“{marked_full(r["text"])}”</a>'
    elif kind == "post":
        source = f'<span class="match-source">Post on {EXAMPLE_POST["platform"]} · {EXAMPLE_POST["author"]} · {fmt(r["date"])}</span>'
        text = f"<span>“{marked_full(r['text'])}”</span>"
    elif kind == "trial":
        source = f'<span class="match-source">{esc(r["id"])}</span>'
        text = f"<span>{marked_full(r['text'])}</span>"
    else:
        source = ""
        text = f"<span>{marked_full(r['text'])}</span>"
    example = '<span class="example-tag">Example post, not on record</span>' if r.get("example") else ""
    return f'<li class="match-reason kind-{kind}">{icon(kind)}<span class="match-label">{label}</span><span class="match-text">{text}{source}{example}</span></li>'


def topic_pill(slug: str) -> str:
    t = topics.get(claims[slug]["topic"])
    return f'<span class="row-topic">{esc(t["title"])}</span>' if t else ""


def frame(days_main: str, side: str, note: str, title: str, query: str = QUERY) -> str:
    out = page
    out = re.sub(r"<script\b(?![^>]*application/ld\+json)[^>]*>.*?</script>", "", out, flags=re.S)
    out = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", out, flags=re.S)
    out = out.replace('placeholder="https://… or tooth regrowth"', f'value="{esc(query)}" placeholder="https://… or tooth regrowth"')
    out = re.sub(r'<div class="under-box">.*?</div>', f'<div class="under-box"><p class="holds result-line">{note}</p></div>', out, count=1, flags=re.S)
    start = out.find('<div class="side-group" hidden data-side-topics>')
    out = out[:start] + side + out[start + len(balanced(out, start, "div")) :]
    start = out.find('<div class="days-main">')
    out = out[:start] + f'<div class="days-main search-mode">{days_main}</div>' + out[start + len(balanced(out, start, "div")) :]
    cut, stop = out.find('<h2 class="bar lists-title"'), out.find("</main>")
    out = out[:cut] + "</div></div></div>" + out[stop:]
    out = out.replace("</head>", f'<link rel="stylesheet" href="{BASE}/mock.css"><link rel="stylesheet" href="{BASE}/match.css"></head>')
    out = out.replace('"/_astro/', f'"{BASE}/_astro/').replace('"/outlet-icons/', f'"{BASE}/outlet-icons/')
    return out


def side_topics(slugs: list[str]) -> str:
    counts: dict[str, int] = {}
    for s in slugs:
        counts[claims[s]["topic"]] = counts.get(claims[s]["topic"], 0) + 1
    items = [f'<li><button type="button" class="side-pick" aria-pressed="true">All results <span class="kind-count">{len(slugs)}</span></button></li>']
    for slug, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        items.append(f'<li><button type="button" class="side-pick" aria-pressed="false">{esc(topics[slug]["title"])} <span class="kind-count">{n}</span></button></li>')
    return '<div class="side-group"><h3>Results by topic</h3><ul>' + "".join(items) + "</ul></div>"


def head(query: str, count: str) -> str:
    return (
        f'<div class="search-head"><h2 class="search-title">Results for “{esc(query)}”</h2>'
        f'<p class="search-count">{count} · <a href="/">Back to Latest</a></p></div>'
    )


def digest(slug: str, lead: str = "Best match · on record now", extra: str = "") -> str:
    c = claims[slug]
    return (
        '<div class="digest found">'
        f'<div class="standing"><span class="row-label">{lead}</span><span class="label">{esc(c["status"])}</span>{track(c["place"])}'
        + (f'<span class="note">{esc(c["no_signal"])}</span>' if c.get("no_signal") else "")
        + "</div>"
        f'<div class="about"><h3>{marked_full(c["headline"])}</h3><p>{esc(c["meaning"])}</p>'
        f'<p class="changed">{esc(c["names"][0])} · {esc(c["indication"])}. First reported {esc(c["first_reported"] or "")}. <a href="{c["page"]}">See the records</a></p>'
        f"{extra}</div></div>"
    )


def key_counts(slugs: list[str]) -> dict[str, int]:
    counts = {k: 0 for k in KIND_WORD}
    for s in slugs:
        for k in {r["kind"] for r in reasons(s)}:
            counts[k] += 1
    return counts


# --- D: each claim says in one line what matched ------------------------------
def mock_d() -> str:
    best, *others = ranked

    def line(slug: str) -> str:
        c = claims[slug]
        # The headline and the treatment line above carry their own marks.
        rs = [r for r in reasons(slug) if r["kind"] != "claim"]
        shown = "".join(reason_line(r) for r in rs[:2])
        more = f'<li class="match-more">and {len(rs) - 2} more</li>' if len(rs) > 2 else ""
        return (
            '<li class="hit-row">'
            f'<div class="hit-now"><strong class="status-name">{esc(c["status"])}</strong>{track(c["place"])}</div>'
            f'<div class="hit-main"><a class="hit-title" href="{c["page"]}">{marked_full(c["headline"])}</a>'
            f'<p class="hit-meta"><span>{marked_full(c["names"][0] + " · " + c["indication"])}</span>{topic_pill(slug)}<span>First reported {esc(c["first_reported"] or "")}</span></p>'
            f'<ul class="match-reasons">{shown}{more}</ul></div></li>'
        )

    best_reasons = '<ul class="match-reasons in-digest">' + "".join(reason_line(r) for r in reasons(best) if r["kind"] != "claim") + "</ul>"
    main = (
        head(QUERY, f"{total} tracked claims")
        + '<p class="search-key">Every result is a tracked claim. Under each, what your words matched: a report’s headline, a post, a trial, or the treatment and condition.</p>'
        + digest(best, extra=f'<p class="matched-title">Matched</p>{best_reasons}')
        + f'<div class="search-group"><h3>Other matches</h3><span>{total - 1} claims</span></div>'
        + '<ol class="plain hit-list">' + "".join(line(s) for s in others) + "</ol>"
    )
    note = f'{total} tracked claims match “{QUERY}”. The best match leads the list below. <a href="/">Clear</a>'
    return frame(main, side_topics(ranked), note, "Search mock D · What matched, on each claim")


# --- E: the matching evidence nested under each claim, filterable by kind ------
def evidence_rows(slug: str) -> str:
    out = []
    for r in reasons(slug):
        if r["kind"] == "report":
            outlet = outlets.get(r["url"], f'<span class="outlet">{esc(r["outlet"])}</span>')
            out.append(
                f'<li class="ev-row ev-report"><p class="row-source"><span class="row-label">{icon("report")}News report</span>{outlet}<span class="when">{fmt(r["date"])}</span></p>'
                f'<p class="ev-title"><a href="{esc(r["url"])}">“{marked_full(r["text"])}”</a></p></li>'
            )
        elif r["kind"] == "post":
            out.append(
                f'<li class="ev-row ev-post"><p class="row-source"><span class="row-label">{icon("post")}Post on {EXAMPLE_POST["platform"]}</span>'
                f'<span class="outlet-plain">{EXAMPLE_POST["author"]}</span><span class="when">{fmt(r["date"])}</span><span class="example-tag">Example post, not on record</span></p>'
                f'<p class="ev-title">“{marked_full(r["text"])}”</p></li>'
            )
    for event in trial_line(slug):
        names = {"phase_1": "Phase 1", "phase_2": "Phase 2", "phase_3": "Phase 3", "phase_4": "Phase 4", "early_phase_1": "Early Phase 1"}
        phases = ", ".join(names[p] for p in event.get("trial_phases") or [] if p in names) or "no phase given"
        out.append(
            f'<li class="ev-row ev-trial"><p class="row-source"><span class="row-label">{icon("trial")}Registry record</span>'
            f'<a href="{esc(event["source_url"])}">{esc(event["trial_id"])}</a><span class="when">{fmt(event["event_date"])}</span></p>'
            f'<p class="ev-title">Trial registered, {esc(phases)}</p></li>'
        )
    return "".join(out)


def mock_e() -> str:
    counts = key_counts(ranked)

    def block(slug: str, first: bool) -> str:
        c = claims[slug]
        rs = reasons(slug)
        claim_hit = next((r for r in rs if r["kind"] == "claim"), None)
        return (
            f'<li class="claim-hit{" is-first" if first else ""}">'
            f'<div class="row-now"><span class="row-label">{"Best match · " if first else ""}On record now</span><strong class="status-name">{esc(c["status"])}</strong>{track(c["place"])}</div>'
            f'<div class="claim-main"><a class="claim-title" href="{c["page"]}">{marked_full(c["headline"])}</a>'
            f'<p class="hit-meta"><span>{(marked_full if claim_hit else esc)(c["names"][0] + " · " + c["indication"])}</span>{topic_pill(slug)}<span>First reported {esc(c["first_reported"] or "")}</span></p>'
            f'<ol class="evidence">{evidence_rows(slug)}</ol></div></li>'
        )

    options = [f"Anything ({total})"] + [f"{KIND_WORD[k]}s ({n})" if k != "claim" else f"{KIND_WORD[k]} ({n})" for k, n in counts.items() if n]
    filters = (
        '<div class="filters" role="group" aria-label="Narrow these results">'
        '<label class="pick"><span class="visually-hidden">Matched in</span><select>'
        + "".join(f"<option>Matched in: {o}</option>" if i == 0 else f"<option>{o}</option>" for i, o in enumerate(options))
        + "</select></label></div>"
    )
    main = (
        head(QUERY, f"{total} tracked claims")
        + filters
        + '<p class="search-key">Each claim is shown with the reports, posts and trial records on it. Your words are marked where they matched.</p>'
        + '<ol class="plain claim-hits">' + "".join(block(s, i == 0) for i, s in enumerate(ranked)) + "</ol>"
    )
    note = f'{total} tracked claims match “{QUERY}”, shown below with the reports and records on each. <a href="/">Clear</a>'
    return frame(main, side_topics(ranked), note, "Search mock E · Evidence under each claim")


# --- F: an exact headline or trial ID leads with the thing itself ---------------
def mock_f_headline() -> str:
    query = "Regrowing Teeth"
    slug = "whole-tooth-pulp-cell-tooth-germ"
    others = [s for s in ranked if s != slug][:5]
    lead = (
        '<div class="exact-lead"><p class="exact-says">A tracked report has this headline.</p>'
        f'<ol class="plain best-report">{rows[slug]}</ol></div>'
    )

    def line(s: str) -> str:
        c = claims[s]
        r = reasons(s)[0]
        return (
            '<li class="hit-row">'
            f'<div class="hit-now"><strong class="status-name">{esc(c["status"])}</strong>{track(c["place"])}</div>'
            f'<div class="hit-main"><a class="hit-title" href="{c["page"]}">{marked_full(c["headline"])}</a>'
            f'<ul class="match-reasons">{reason_line(r)}</ul></div></li>'
        )

    main = (
        head(query, "1 report, and 5 other claims with these words")
        + lead
        + f'<div class="search-group"><h3>Other claims with these words</h3><span>{len(others)} claims</span></div>'
        + '<ol class="plain hit-list">' + "".join(line(s) for s in others) + "</ol>"
    )
    note = f'A tracked report is headlined “{query}”. It leads the list below. <a href="/">Clear</a>'
    return frame(main, "", note, "Search mock F · An exact headline", query)


def mock_f_trial() -> str:
    global MARKING
    MARKING = False  # an identifier is matched whole; there are no words to mark
    query = "NCT01814436"
    slug = "pulp-regeneration-baby-tooth-stem-cells"
    event = trial_line(slug)[0]
    c = claims[slug]
    record = (
        '<ol class="plain"><li class="day-row record-row exact-record">'
        f'<p class="row-source"><span class="row-label">Registry record</span><a href="{esc(event["source_url"])}">{esc(event["trial_id"])}</a><span class="when">{fmt(event["event_date"])}</span></p>'
        f'<p class="row-what"><strong>Trial registered (no phase).</strong> <a href="{c["page"]}">{esc(c["names"][0])}</a> · {esc(c["indication"])}</p>'
        "</li></ol>"
    )
    main = (
        f'<div class="search-head"><h2 class="search-title">{query}</h2><p class="search-count">A trial on record · <a href="/">Back to Latest</a></p></div>'
        + '<p class="exact-says">This trial is on record for one tracked claim.</p>'
        + record
        + digest(slug, lead="The claim it belongs to · on record now")
        + f'<ol class="plain best-report">{rows[slug]}</ol>'
        + '<p class="search-more">No other tracked claim names this trial. A trial on record is not a treatment option.</p>'
    )
    note = f'{query} is on record for one tracked claim, shown below. <a href="/">Clear</a>'
    return frame(main, "", note, "Search mock F · A trial ID", query)


(OUT / "d.html").write_text(mock_d())
(OUT / "e.html").write_text(mock_e())
(OUT / "f-headline.html").write_text(mock_f_headline())
(OUT / "f-trial.html").write_text(mock_f_trial())
css = next(p.name for p in (OUT / "_astro").glob("global.*.css"))
(OUT / "index.html").write_text(f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Search results mocks</title><link rel="stylesheet" href="{BASE}/_astro/{css}"></head>
<body style="background:var(--ground);padding:2rem 1rem;font-family:var(--face)"><main style="max-width:46rem;margin:auto">
<h1>Search results mocks</h1>
<h2>Round 1: layout (C chosen and built)</h2>
<ul style="line-height:2">
<li><a href="a.html">A · Results in the Latest list</a></li>
<li><a href="b.html">B · Grouped by status</a></li>
<li><a href="c.html">C · Best match first</a> (built)</li>
</ul>
<h2>Round 2: what matched, still claim first</h2>
<p>Query “{QUERY}”, real claims, reports and trials from the published export. One post is an example of how a post would be drawn and says so: none is on record yet.</p>
<ul style="line-height:1.6">
<li><a href="d.html"><strong>D · What matched, on each claim.</strong></a> C as built, with one or two “matched” lines under each claim: an icon, the kind in words, the matched text with your words marked, and its source.</li>
<li><a href="e.html"><strong>E · Evidence under each claim.</strong></a> Each claim carries its reports, posts and registry records as small rows in the Latest list’s style; one field narrows to what matched (headlines, posts, trials, treatment).</li>
<li><a href="f-headline.html"><strong>F · Exact match leads.</strong></a> When the words are a report’s headline, that report’s row leads, then other claims. <a href="f-trial.html">And a trial ID</a>: the registry record leads, then the claim it belongs to. Combines with D or E for everything else.</li>
</ul></main></body></html>""")
print("ok", total, ranked)
