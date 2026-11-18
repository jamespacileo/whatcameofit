"""Commands that draft claims from news articles."""

import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from sqlalchemy.orm import Session

from thenwhat.claims.entry import EntryError
from thenwhat.cli.console import err, out
from thenwhat.cli.entry import DATE_FORMATS, entry_session
from thenwhat.cli.session import settings_or_exit
from thenwhat.domain import ReviewState
from thenwhat.extract.retrieve import (
    ArticleRetriever,
    PasteNeeded,
    Retrieved,
    reader_turns,
)
from thenwhat.work.errors import ReaderUnavailable

if TYPE_CHECKING:
    from thenwhat.llm.client import Llm
    from thenwhat.statements.service import StatementChecker, StatementsRun

extract_app = typer.Typer(help="Draft claims from news articles.", no_args_is_help=True)

PASTE_HELP = "Read the article text from standard input instead of fetching it."


def make_llm(session: Session, *, budget_cap: Decimal | None = None) -> "Llm":
    # Imported here: the model library is slow to load and most commands never need it.
    from thenwhat.llm.cache import ModelCache
    from thenwhat.llm.client import Llm, LlmSettings

    settings = settings_or_exit()
    ceiling = settings.llm_monthly_budget_usd
    return Llm(
        session,
        LlmSettings(
            model=settings.llm_model,
            monthly_budget_usd=min(ceiling, budget_cap) if budget_cap is not None else ceiling,
            input_usd_per_mtok=settings.llm_input_usd_per_mtok,
            output_usd_per_mtok=settings.llm_output_usd_per_mtok,
        ),
        cache=ModelCache(settings.llm_cache_dir) if settings.llm_cache_dir is not None else None,
    )


def make_checker(session: Session) -> "StatementChecker":
    """How reported statements are checked: the configured decision backend and the
    statement settings."""
    from thenwhat.cli.resolve import make_backend
    from thenwhat.statements.service import StatementChecker

    settings = settings_or_exit()
    return StatementChecker(
        make_backend(session),
        accept_above=settings.statement_accept_above,
        per_article=settings.statements_per_article,
        copied_run=settings.statement_copied_run,
    )


def statement_lines(run: "StatementsRun") -> list[str]:
    """What became of an article's reported statements, for the operator."""
    refused = sum(run.refused.values())
    reasons = ", ".join(
        f"{reason.value.replace('_', ' ')}: {count}"
        for reason, count in sorted(run.refused.items())
    )
    lines = [
        f"Reported statements: {run.proposed} proposed, {len(run.approved)} approved by rule,"
        f" {len(run.pending)} pending review, {refused} refused by rule"
        + (f" ({reasons})" if reasons else "")
        + "."
    ]
    if run.known:
        lines.append(
            f"{run.known} worded as a statement the article already has, so not added again."
        )
    if run.left_out:
        lines.append(f"{run.left_out} left out: the article has as many statements as it may.")
    return lines


def unchecked_line(run: "StatementsRun", slug: str) -> str | None:
    """Said when statements were proposed and the check could not answer for some."""
    if not run.unchecked:
        return None
    return (
        f"{run.unchecked} reported statement(s) could not be checked and were not stored."
        f" Read the article again for them with `thenwhat statements {slug} --again`."
    )


def make_retriever() -> ArticleRetriever:
    """The page reader, as configured. Refuses, before any request, when its address or
    key is not set: no page is fetched any other way (openspec page-reading)."""
    settings = settings_or_exit()
    for name, value in (
        ("FIRECRAWL_API_URL", settings.firecrawl_api_url),
        ("FIRECRAWL_API_KEY", settings.firecrawl_api_key),
    ):
        if not (value or "").strip():
            err.print(
                f"{name} is not set, so no page can be read. Set the page reader's address"
                " and key, or use --paste where the command offers it.",
                markup=False,
            )
            raise typer.Exit(code=1)
    return ArticleRetriever(
        reader_url=settings.firecrawl_api_url or "",
        reader_key=settings.firecrawl_api_key or "",
        contact_email=settings.contact_email,
        turns=reader_turns(settings.reader_reads_at_once),
        timeout_seconds=settings.reader_timeout_seconds,
    )


def _article_text(url: str, paste: bool) -> Retrieved:
    """The article's text for this run only. It is never stored."""
    if paste:
        text = sys.stdin.read().strip()
        if not text:
            raise EntryError("No article text arrived on standard input.")
        return Retrieved(text)
    try:
        return make_retriever().retrieve(url)
    except PasteNeeded as needed:
        raise EntryError(
            f"{needed} Run the command again with --paste and pipe the text in."
        ) from None
    except ReaderUnavailable as down:
        raise EntryError(str(down)) from None


@extract_app.command("evidence-search")
def evidence_search_command(
    url: Annotated[str, typer.Argument(help="URL of the news article.")],
    store: Annotated[
        Path, typer.Option(exists=True, dir_okay=False, readable=True, help="Local trial database.")
    ],
    title: Annotated[str, typer.Option(help="Headline when the reader supplies none.")] = "",
    outlet: Annotated[str, typer.Option(help="Name of the publisher.")] = "",
    published: Annotated[
        datetime | None, typer.Option(formats=DATE_FORMATS, help="Article date, YYYY-MM-DD.")
    ] = None,
    queries: Annotated[int, typer.Option(min=1, max=4, help="Maximum queries.")] = 4,
    paste: Annotated[bool, typer.Option("--paste", help=PASTE_HELP)] = False,
    papers: Annotated[bool, typer.Option("--papers/--no-papers")] = True,
    verify: Annotated[bool, typer.Option(help="Score exact article-to-record matches.")] = False,
    trial_aliases: Annotated[
        Path | None,
        typer.Option(
            exists=True, dir_okay=False, readable=True, help="Cited sponsor product aliases."
        ),
    ] = None,
) -> None:
    """Plan searches and retrieve trial or paper candidates for an article."""
    import json
    import sqlite3
    from contextlib import closing

    from pydantic import TypeAdapter, ValidationError

    from thenwhat.cli.resolve import make_backend
    from thenwhat.cli.session import open_session
    from thenwhat.decide.core import DecisionFailed
    from thenwhat.extract.evidence_search import find_evidence
    from thenwhat.extract.evidence_verification import TrialProductAlias, verify_evidence
    from thenwhat.extract.page import published_day
    from thenwhat.llm.errors import LlmError
    from thenwhat.sources.pubmed import PubMed
    from thenwhat.work.allowance import Allowances

    settings = settings_or_exit()
    try:
        aliases = (
            TypeAdapter(list[TrialProductAlias]).validate_json(trial_aliases.read_bytes())
            if trial_aliases is not None and verify
            else []
        )
        article = _article_text(url, paste)
        page = article.page
        when = (
            published.date()
            if published is not None
            else (published_day(page.published) if page else None)
        )
        index = (
            PubMed(
                contact_email=settings.contact_email,
                tool=settings.pubmed_tool,
                api_key=settings.pubmed_api_key,
                allowances=Allowances(open_session, settings.allowances()),
            )
            if papers
            else None
        )
        headline = (page.headline if page else None) or title
        with (
            closing(sqlite3.connect(store.resolve().as_uri() + "?mode=ro", uri=True)) as trials,
            open_session() as session,
        ):
            result = find_evidence(
                make_llm(session),
                article,
                headline=headline,
                outlet=outlet,
                published=when,
                trial_store=trials,
                pubmed=index,
                max_queries=queries,
            )
            payload = result.model_dump(mode="json")
            if verify:
                verification = verify_evidence(
                    session,
                    make_backend(session),
                    article,
                    result,
                    trial_store=trials,
                    pubmed=index,
                    headline=headline,
                    product_aliases=aliases,
                )
                payload["verification"] = verification.model_dump(mode="json")
    except (DecisionFailed, EntryError, LlmError, OSError, ValidationError, sqlite3.Error) as error:
        err.print(str(error), markup=False)
        raise typer.Exit(1) from None
    out.print(json.dumps(payload, indent=2), markup=False)


@extract_app.command("new")
def extract_new(
    url: Annotated[str, typer.Argument(help="Address of the news article.")],
    slug: Annotated[str, typer.Option(help="Short, guessable page address for the claim.")],
    vertical: Annotated[str, typer.Option(help="Topic area, for example mouth-and-teeth.")],
    outlet: Annotated[str, typer.Option(help="Publication that ran the article.")],
    title: Annotated[str, typer.Option(help="Article title.")],
    published: Annotated[
        datetime, typer.Option(formats=DATE_FORMATS, help="Publication date, YYYY-MM-DD.")
    ],
    paste: Annotated[bool, typer.Option("--paste", help=PASTE_HELP)] = False,
) -> None:
    """Draft a new claim from an article. The draft is decided by rule, or stays pending
    until you approve it when the rule is switched off."""
    from thenwhat.extract.service import draft_claim_from_article

    by_rule = settings_or_exit().approve_drafts_by_rule
    unchecked = None
    with entry_session() as session:
        article = _article_text(url, paste)
        now = datetime.now(UTC)
        extracted = draft_claim_from_article(
            session,
            make_llm(session),
            make_checker(session),
            text=article.text,
            archive_url=article.archive_url,
            slug=slug,
            vertical=vertical,
            url=url,
            outlet=outlet,
            title=title,
            published_date=published.date(),
            decide_by_rule_at=now if by_rule else None,
            now=now,
        )
        claim = extracted.claim
        out.print(f"Drafted claim {claim.slug}: {claim.headline}", markup=False)
        if claim.review_state is ReviewState.APPROVED:
            out.print("Approved by rule: it is published with the next export.")
        elif claim.review_state is ReviewState.REJECTED:
            out.print(
                "Rejected by rule: the intervention it names is not a name. Correct it with"
                " `claim edit`, then approve it in review."
            )
        else:
            out.print("It is pending. Correct it with `claim edit`, then approve it in review.")
        for line in statement_lines(extracted.statements):
            out.print(line, markup=False)
        unchecked = unchecked_line(extracted.statements, claim.slug)
    if unchecked:
        # Raised once the session has committed the claim and the decision records.
        err.print(unchecked, markup=False)
        raise typer.Exit(code=1)


@extract_app.command("article")
def extract_article(
    claim_slug: Annotated[str, typer.Argument(help="Slug of a claim that is still pending.")],
    article_url: Annotated[str, typer.Option(help="One of the claim's articles.")],
    paste: Annotated[bool, typer.Option("--paste", help=PASTE_HELP)] = False,
) -> None:
    """Add what one of a claim's articles says: entities, the paper, promises and
    reported statements. `thenwhat prepare` reads a claim's unread articles itself (the
    step `claim_articles`); this reads one now, or takes its pasted text."""
    from thenwhat.extract.service import extract_into_claim

    with entry_session() as session:
        article = _article_text(article_url, paste)
        extracted = extract_into_claim(
            session,
            make_llm(session),
            make_checker(session),
            claim_slug=claim_slug,
            article_url=article_url,
            text=article.text,
            archive_url=article.archive_url,
            now=datetime.now(UTC),
        )
        out.print(f"Added details from the article to {extracted.claim.slug}.", markup=False)
        for line in statement_lines(extracted.statements):
            out.print(line, markup=False)
        unchecked = unchecked_line(extracted.statements, claim_slug)
    if unchecked:
        err.print(unchecked, markup=False)
        raise typer.Exit(code=1)
