"""Which outlets the pipeline can read, and what their pages carry. Behavior: openspec live-lookup.

Every tracked article's address is asked for once, politely, and what came back is counted
per outlet: read, refused, failed, and which of the signals a lookup uses were on the page.
Counts and codes only: no article text is kept, here or in the report.
"""

import csv
import io
import threading
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.db.models import Claim, Entity, EntityMatch, SourceArticle
from thenwhat.domain import ReviewState
from thenwhat.extract.page import BODY_FROM, Page
from thenwhat.extract.retrieve import REFUSED_BY_ROBOTS, ArticleRetriever
from thenwhat.outlets.icons import outlet_domain
from thenwhat.sources.base import SystemTime, Time

# One outlet is asked at most this often.
SECONDS_BETWEEN_REQUESTS = 1.0
REGISTRY = "clinicaltrials.gov"
# What a page can carry that a lookup uses, in the order the report shows them.
SIGNALS = ("headline", "summary", "date", "structured article", "paper link", "registry number")


@dataclass(frozen=True, slots=True)
class Measured:
    """How a lookup did on one article of a claim with approved trials."""

    # An approved trial was among the records that read as trials of the treatment.
    found: bool
    # The first record listed was an approved trial.
    first: bool


@dataclass(frozen=True, slots=True)
class Checked:
    """How one article's address answered. Codes only."""

    url: str
    # "read", "thin", "refused", or how it failed: an HTTP status or "no answer".
    outcome: str
    signals: tuple[str, ...] = ()
    # With a lookup measured: "found first", "found" or "not found". Empty when none was.
    lookup: str = ""


@dataclass(slots=True)
class Outlet:
    domain: str
    articles: int = 0
    # The site served the article with enough text to read.
    read: int = 0
    # The site served a page with too little text: the article is drawn by scripts.
    thin: int = 0
    # robots.txt forbids the fetch, or could not be read.
    refused: int = 0
    # The page did not come back: by HTTP status, or "no answer".
    failed: Counter[str] = field(default_factory=Counter)
    signals: Counter[str] = field(default_factory=Counter)
    measured: int = 0
    found: int = 0
    first: int = 0
    checked: list[Checked] = field(default_factory=list)


def check_outlets(
    session: Session,
    retriever: ArticleRetriever,
    *,
    time: Time | None = None,
    measure: Callable[[Page, list[str]], Measured | None] | None = None,
    workers: int = 1,
    on_article: Callable[[Checked], None] | None = None,
) -> list[Outlet]:
    """Ask for every tracked article once and count, per outlet, how its site answered.

    With `measure`, each article that was read and whose claim has approved trials is also
    put through a lookup, and the outlet's row counts how often an approved trial was found.

    With more than one worker, several outlets are checked at the same time. One outlet is
    still asked one article at a time, a second apart, and `measure` is then called from
    several threads at once. `on_article` is told of each article as it is finished.
    """
    clock = time or SystemTime()
    approved = _approved_trials(session)
    by_outlet: dict[str, list[tuple[str, list[str]]]] = {}
    articles = session.execute(
        select(SourceArticle.url, Claim.slug)
        .join(Claim, Claim.id == SourceArticle.claim_id)
        .order_by(SourceArticle.url)
    ).all()
    for url, slug in articles:
        by_outlet.setdefault(outlet_domain(url), []).append((url, approved.get(slug, [])))
    telling = threading.Lock()

    def one_outlet(domain: str) -> Outlet:
        outlet = Outlet(domain)
        asked_at: float | None = None
        for url, trials in by_outlet[domain]:
            if asked_at is not None and clock.monotonic() - asked_at < SECONDS_BETWEEN_REQUESTS:
                clock.sleep(SECONDS_BETWEEN_REQUESTS - (clock.monotonic() - asked_at))
            checked = _check_article(outlet, retriever, url, trials, measure)
            asked_at = clock.monotonic()
            if on_article is not None:
                with telling:
                    on_article(checked)
        return outlet

    if workers <= 1:
        outlets = [one_outlet(domain) for domain in by_outlet]
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            outlets = list(pool.map(one_outlet, by_outlet))
    return sorted(outlets, key=lambda outlet: (-outlet.articles, outlet.domain))


def _check_article(
    outlet: Outlet,
    retriever: ArticleRetriever,
    url: str,
    trials: list[str],
    measure: Callable[[Page, list[str]], Measured | None] | None,
) -> Checked:
    """Ask for one article, count the answer in its outlet's row, and return its own row."""
    outlet.articles += 1
    probe = retriever.probe(url)
    page = probe.page
    if probe.robots == REFUSED_BY_ROBOTS:
        outlet.refused += 1
        checked = Checked(url, "refused")
    elif page is None:
        failure = str(probe.status) if probe.status else "no answer"
        outlet.failed[failure] += 1
        checked = Checked(url, failure)
    else:
        thin = len(page.as_text()) < BODY_FROM
        if thin:
            outlet.thin += 1
        else:
            outlet.read += 1
        signals = _signals(page)
        outlet.signals.update(signals)
        lookup = ""
        measured = measure(page, trials) if measure is not None and trials else None
        if measured is not None:
            outlet.measured += 1
            outlet.found += measured.found
            outlet.first += measured.first
            lookup = "found first" if measured.first else "found" if measured.found else "not found"
        checked = Checked(url, "thin" if thin else "read", tuple(signals), lookup)
    outlet.checked.append(checked)
    return checked


def report(outlets: list[Outlet], *, checked: date) -> str:
    """The record as a Markdown page."""
    measured = any(outlet.measured for outlet in outlets)
    columns = ["Outlet", "Articles", "Read", "Thin", "Refused", "Failed", *SIGNALS]
    if measured:
        columns += ["Lookups", "Trial found", "Trial first"]
    total = Outlet("All outlets")
    for outlet in outlets:
        for name in ("articles", "read", "thin", "refused", "measured", "found", "first"):
            setattr(total, name, getattr(total, name) + getattr(outlet, name))
        total.failed.update(outlet.failed)
        total.signals.update(outlet.signals)

    def row(outlet: Outlet) -> str:
        failed = ", ".join(f"{status} ×{count}" for status, count in sorted(outlet.failed.items()))
        cells = [
            outlet.domain,
            outlet.articles,
            outlet.read,
            outlet.thin,
            outlet.refused,
            failed or 0,
            *(outlet.signals[signal] for signal in SIGNALS),
        ]
        if measured:
            cells += [outlet.measured, outlet.found, outlet.first]
        return f"| {' | '.join(str(cell) for cell in cells)} |"

    lines = [
        "# Which outlets can be read",
        "",
        f"Checked {checked.isoformat()} with `thenwhat outlets`, over every tracked article."
        " Regenerate it with that command; do not edit it by hand.",
        "",
        "- **Read:** the site served the article. **Thin:** it served a page with too little"
        " text to read, usually because scripts draw the article.",
        "- **Refused:** the site's robots.txt forbids the fetch, or could not be read, so the"
        " article was not asked for. **Failed:** the page did not come back, by HTTP status.",
        "- The signal columns count the pages that carried each thing a lookup uses.",
    ]
    if measured:
        lines.append(
            "- **Lookups:** articles read whose claim has approved trials. **Trial found:** an"
            " approved trial was among the likely records. **Trial first:** it was listed first."
        )
    lines += [
        "",
        f"| {' | '.join(columns)} |",
        f"|{'|'.join(' --- ' for _ in columns)}|",
        *(row(outlet) for outlet in outlets),
        row(total),
        "",
    ]
    return "\n".join(lines)


def articles_csv(outlets: list[Outlet]) -> str:
    """One row per article address: how it answered, what its page carried, and how a
    lookup did when one was measured."""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["outlet", "url", "outcome", "signals", "lookup"])
    for outlet in sorted(outlets, key=lambda outlet: outlet.domain):
        for checked in outlet.checked:
            writer.writerow(
                [
                    outlet.domain,
                    checked.url,
                    checked.outcome,
                    "; ".join(checked.signals),
                    checked.lookup,
                ]
            )
    return out.getvalue()


def _signals(page: Page) -> list[str]:
    carried = (
        page.headline,
        page.summary,
        page.published,
        page.body and len(page.body) >= BODY_FROM,
        page.dois or page.pubmed_ids,
        page.registry_numbers,
    )
    return [signal for signal, present in zip(SIGNALS, carried, strict=True) if present]


def _approved_trials(session: Session) -> dict[str, list[str]]:
    """Per claim, the registry trials approved, by rule or in review."""
    approved: dict[str, list[str]] = {}
    rows = session.execute(
        select(Claim.slug, EntityMatch.external_id)
        .join(Entity, Entity.claim_id == Claim.id)
        .join(EntityMatch, EntityMatch.entity_id == Entity.id)
        .where(
            EntityMatch.source_name == REGISTRY,
            EntityMatch.review_state == ReviewState.APPROVED,
        )
        .order_by(Claim.slug, EntityMatch.external_id)
    )
    for slug, number in rows:
        approved.setdefault(slug, []).append(number)
    return approved
