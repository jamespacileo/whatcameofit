"""Join urls.csv with the link check, the tracker match and the lookup answers.

Gives any row without an id the next one in its group and writes urls.csv back. Writes
.work/extension-test-urls.xlsx (tabs: URLs, Summary, Findings, Key) and
.work/extension-test-urls.csv. Run with: uv run --with openpyxl python assemble.py
"""

import csv
import json
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))  # Also support the sync script's isolated Python mode.
from corpus_cache import load_cache  # noqa: E402

WORK = HERE / ".work"
LIKELY = 0.5
PREFIX = {"Social": "S", "Article": "A", "Negative": "N", "Tracked": "T"}
FIELDS = ["id", "group", "page_type", "url", "outlet", "intervention_condition", "expected_answer", "source_of_row", "notes"]
TEST_BRIEF = {"https://x.com/statnews/status/2120931204035760307", "https://www.kyoto-u.ac.jp/en/research-news/2021-03-31"}

REFUSALS = {
    "unreadable_robots": "refused: site disallows software (robots.txt)",
    "unreadable": "refused: article could not be opened",
    "post": "refused: post platform not readable by address",
    "short": "refused: shortened link",
    "post_unreadable": "refused: post could not be read",
    "busy": "refused: rate limit",
    "failed": "error: lookup failed",
    "budget_exhausted": "refused: monthly budget used",
}


def load(name, default):
    path = WORK / name if not (HERE / name).exists() else HERE / name
    return json.loads(path.read_text()) if path.exists() else default


def number_rows(rows):
    """Give a row without an id the next free number in its group; keep the rest."""
    used = Counter()
    for row in rows:
        m = re.fullmatch(r"([A-Z])(\d+)", row["id"].strip())
        if m:
            used[m.group(1)] = max(used[m.group(1)], int(m.group(2)))
    changed = False
    for row in rows:
        if not row["id"].strip():
            letter = PREFIX.get(row["group"].strip().title(), "X")
            used[letter] += 1
            row["id"] = f"{letter}{used[letter]:03d}"
            changed = True
    return changed


def describe(body):
    if not body:
        return "", "", "", "", ""
    if body.get("error"):
        return REFUSALS.get(body["error"], f"refused: {body['error']}"), "", "", "", ""
    if body.get("article_tracked"):
        return "post links to a tracked article", (body.get("tracked") or [{}])[0].get("slug", ""), "", "", ""
    if body.get("about_a_treatment") is False:
        return "no specific treatment found; registry not searched", "", "", "", ""
    candidates = body.get("candidates") or []
    likely = [c for c in candidates if (c.get("score") or 0) >= LIKELY]
    top = (likely or candidates or [None])[0]
    top_text = ""
    if top:
        phase = "/".join(p.replace("PHASE", "Ph") for p in top.get("phases") or []) or "no phase"
        top_text = f"{top.get('id')} · {phase} · {top.get('state') or '?'} · {round((top.get('score') or 0) * 100)}% · {top.get('title', '')[:90]}"
    said = f"{body.get('treatment') or '?'} for {body.get('condition') or '?'}"
    tracked = ", ".join(t["slug"] for t in body.get("tracked") or [])
    return said, tracked, len(candidates), len(likely), top_text


def verdict(expected, path, answer, likely):
    e = expected.lower()
    if path == "tracked on site":
        return "pass"
    if path.startswith("not run"):
        return "not run"
    if answer.startswith(("refused", "error")) or path.startswith("too little"):
        return "blocked"
    found = answer not in ("", "no specific treatment found; registry not searched")
    if e.startswith("no claim") or "not appear" in e:
        return "fail" if found else "pass"
    if "edge" in e:
        return "review"
    if not found:
        return "fail"
    if answer == "post links to a tracked article":
        return "pass"
    return "pass" if likely else "partial"


def priority(row):
    if row["group"] == "Tracked" and row["url"] not in TEST_BRIEF:
        return "P3"
    if row["url"] in TEST_BRIEF:
        return "P1"
    if row["group"] == "Negative" or "not opened" in row["source_of_row"] or "edge" in row["expected_answer"]:
        return "P2"
    return "P1"


def main():
    rows = list(csv.DictReader((HERE / "urls.csv").open()))
    if number_rows(rows):
        with (HERE / "urls.csv").open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
    cache = load_cache(HERE)
    checked = cache["checked"]
    match = load("match.json", {})
    results = cache["results"]
    notes = load("notes.json", {})
    overrides = load("verdicts.json", {})

    out = []
    for row in rows:
        rid, url = row["id"], row["url"]
        m, c = match.get(url, {}), checked.get(url, {})
        saved = results.get(url, {})
        address, browser, note = saved.get("address"), saved.get("browser"), notes.get(rid, "")
        tracked_slug = m.get("tracked_slug", "")
        if tracked_slug:
            path, (answer, tracked, n, likely, top) = "tracked on site", ("reviewed claim shown (no live search)", tracked_slug, "", "", "")
        elif browser:
            path, (answer, tracked, n, likely, top) = ("server refused; read in browser" if address else "read in browser"), describe(browser["body"])
        elif address:
            path, (answer, tracked, n, likely, top) = "read by address (server)", describe(address["body"])
        elif note.startswith("too little"):
            path, (answer, tracked, n, likely, top) = "too little read in browser", ("too little of this page could be read", "", "", "", "")
        else:
            path, (answer, tracked, n, likely, top) = "not run: " + (note or "no answer yet"), ("", "", "", "", "")
        result = verdict(row["expected_answer"], path, answer, likely)
        if rid in overrides:
            result, why = overrides[rid]
            note = f"{why}; {note}" if note else why
        ms = (browser or address or {}).get("ms")
        out.append({
            "id": rid, "group": row["group"], "page_type": row["page_type"], "url": url, "outlet": row["outlet"],
            "intervention_condition": row["intervention_condition"], "expected_answer": row["expected_answer"],
            "test_result": result, "how_read": path, "lookup_answer": answer, "trial_records": n, "likely_records": likely,
            "top_record": top, "tracked_claim": tracked, "closest_tracked_claim": "" if tracked_slug else m.get("closest_claim", ""),
            "seconds": round(ms / 1000, 1) if ms else "", "address_kind": m.get("address_kind", ""),
            "access": c.get("access", ""), "language": c.get("language", ""), "priority": priority(row),
            "http_status": c.get("http_status", ""), "redirects_to": c.get("redirects_to", ""), "page_title": c.get("page_title", ""),
            "link_checked": c.get("link_checked", ""), "source_of_row": row["source_of_row"],
            "notes": "; ".join(x for x in [note, row["notes"]] if x),
        })
    write_workbook(out)
    print(len(out), "rows", dict(Counter(o["test_result"] for o in out)))


def write_workbook(out):
    cols = list(out[0].keys())
    bold = Font(bold=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "URLs"
    ws.append(cols)
    for o in out:
        ws.append(list(o.values()))
    for cell in ws[1]:
        cell.font = bold
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = ws.dimensions
    widths = {"id": 7, "group": 9, "page_type": 26, "url": 46, "outlet": 20, "intervention_condition": 36, "expected_answer": 28,
              "test_result": 10, "how_read": 22, "lookup_answer": 40, "top_record": 50, "tracked_claim": 26,
              "closest_tracked_claim": 26, "notes": 50, "page_title": 40, "redirects_to": 30}
    for i, name in enumerate(cols, 1):
        ws.column_dimensions[get_column_letter(i)].width = widths.get(name, 10)
    last = len(out) + 1
    t = get_column_letter(cols.index("test_result") + 1)
    choices = DataValidation(type="list", formula1='"pass,partial,fail,blocked,review,not run"', allow_blank=True)
    ws.add_data_validation(choices)
    choices.add(f"{t}2:{t}{last}")
    for word, color in [("pass", "C6EFCE"), ("partial", "FFEB9C"), ("fail", "FFC7CE"), ("blocked", "D9D9D9"), ("review", "DDEBF7")]:
        ws.conditional_formatting.add(f"{t}2:{t}{last}", CellIsRule(operator="equal", formula=[f'"{word}"'], fill=PatternFill("solid", fgColor=color)))

    s = wb.create_sheet("Summary")
    s.append(["Extension test corpus", f"built {datetime.now(UTC).date().isoformat()}"])
    s.append([])
    words = ["pass", "partial", "fail", "blocked", "review", "not run"]
    s.append(["Group", "URLs", *words])
    for group in ["Social", "Article", "Negative", "Tracked"]:
        r = s.max_row + 1
        s.append([group, f"=COUNTIF(URLs!B:B,A{r})", *[f'=COUNTIFS(URLs!B:B,A{r},URLs!{t}:{t},"{w}")' for w in words]])
    s.append(["Total", *[f"=SUM({get_column_letter(c)}4:{get_column_letter(c)}7)" for c in range(2, 9)]])
    for cell in s[3]:
        cell.font = bold
    s.column_dimensions["A"].width = 14

    f = wb.create_sheet("Findings")
    for record in csv.reader((HERE / "findings.csv").open()):
        f.append(record)
    for cell in f[1]:
        cell.font = bold
    for letter, width in zip("ABC", (44, 28, 110)):
        f.column_dimensions[letter].width = width
    for row in f.iter_rows(min_row=2):
        row[2].alignment = Alignment(wrap_text=True, vertical="top")

    k = wb.create_sheet("Key")
    for record in [
        ("Column", "Meaning"),
        ("test_result", "pass: answer matches expected_answer. partial: treatment found but no record scored likely. fail: wrong kind of answer. blocked: page could not be read or was refused. review: edge case, a person should judge. not run: no automated path."),
        ("how_read", "tracked on site: the published lookup.json tracks the address, so the popup shows the reviewed claim. read by address (server): sent to the lookup service by address, as the site's address box does. read in browser: page opened in a browser, read the way the extension reads it, and the text sent to the service. too little read: the extension would have nothing to search on."),
        ("lookup_answer", "What the lookup service reported: treatment for condition, a refusal, or that no specific treatment was found."),
        ("trial_records / likely_records", f"Registry records returned, and those at or above {int(LIKELY * 100)}% match confidence (the popup lists these)."),
        ("top_record", "First record the popup would list: NCT number, phase, state, match confidence, title."),
        ("closest_tracked_claim", "For an untracked address, the tracked claim whose names share words with it (the address box's suggestion)."),
        ("access / http_status", "One plain request on the check date: open, paywall, sign-in wall likely, blocks bots."),
        ("priority", "P1 core page types and the test-brief rows; P2 negative, edge and unopened rows; P3 tracked seed claims."),
        ("Adding rows", "Source of truth is extension/test-corpus/urls.csv in the repository. Edits made here are overwritten by the next sync."),
    ]:
        k.append(record)
    k["A1"].font = bold
    k["B1"].font = bold
    k.column_dimensions["A"].width = 28
    k.column_dimensions["B"].width = 120
    for row in k.iter_rows(min_row=2):
        row[1].alignment = Alignment(wrap_text=True, vertical="top")

    WORK.mkdir(exist_ok=True)
    wb.save(WORK / "extension-test-urls.xlsx")
    with (WORK / "extension-test-urls.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols)
        writer.writeheader()
        writer.writerows(out)


main()
