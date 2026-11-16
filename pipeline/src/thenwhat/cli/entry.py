"""Commands for entering claims, source articles and promises by hand."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from sqlalchemy.orm import Session

from thenwhat.claims.corrections import merge_claims
from thenwhat.claims.csv_import import CsvErrors, import_csv
from thenwhat.claims.entry import (
    EntryError,
    add_article,
    add_claim,
    add_promise,
    edit_claim,
    rename_slug,
)
from thenwhat.cli.console import err, out
from thenwhat.cli.session import open_session
from thenwhat.domain import Decider
from thenwhat.llm.errors import LlmError
from thenwhat.sources.base import SourceError

claim_app = typer.Typer(help="Add and manage claims.", no_args_is_help=True)
article_app = typer.Typer(help="Add source articles to claims.", no_args_is_help=True)
promise_app = typer.Typer(help="Record promised timelines.", no_args_is_help=True)

DATE_FORMATS = ["%Y-%m-%d"]


@contextmanager
def entry_session() -> Generator[Session]:
    """A session in which a refused entry is reported to the operator and exits with 1."""
    try:
        with open_session() as session:
            yield session
    except (EntryError, LlmError, SourceError) as error:
        err.print(str(error), markup=False)
        raise typer.Exit(code=1) from None


@claim_app.command("add")
def claim_add(
    slug: Annotated[str, typer.Argument(help="Short, guessable page address.")],
    headline: Annotated[str, typer.Option(help="What was claimed, in one line.")],
    vertical: Annotated[str, typer.Option(help="Topic area, for example mouth-and-teeth.")],
    intervention: Annotated[str, typer.Option(help="The drug, device or method.")],
    indication: Annotated[str, typer.Option(help="The condition it is claimed to treat.")],
    summary: Annotated[str, typer.Option(help="Summary in your own words.")] = "",
    approach: Annotated[
        str, typer.Option(help="Kind of intervention, for example drug or gene-therapy.")
    ] = "",
) -> None:
    """Add a claim: one intervention for one indication."""
    with entry_session() as session:
        claim = add_claim(
            session,
            slug=slug,
            headline=headline,
            vertical=vertical,
            intervention=intervention,
            indication=indication,
            summary=summary,
            approach=approach,
        )
        out.print(f"Added claim {claim.slug}.", markup=False)


@claim_app.command("edit")
def claim_edit(
    slug: Annotated[str, typer.Argument(help="Slug of the claim to correct.")],
    headline: Annotated[str | None, typer.Option(help="New headline.")] = None,
    summary: Annotated[str | None, typer.Option(help="New summary, in your own words.")] = None,
    intervention: Annotated[str | None, typer.Option(help="New intervention name.")] = None,
    indication: Annotated[str | None, typer.Option(help="New indication.")] = None,
    vertical: Annotated[str | None, typer.Option(help="New vertical.")] = None,
    approach: Annotated[
        str | None, typer.Option(help="New approach; an empty value clears it.")
    ] = None,
) -> None:
    """Correct a claim's headline, summary, intervention, indication, vertical or approach."""
    with entry_session() as session:
        claim = edit_claim(
            session,
            slug,
            headline=headline,
            summary=summary,
            intervention=intervention,
            indication=indication,
            vertical=vertical,
            approach=approach,
        )
        out.print(f"Updated claim {claim.slug}.", markup=False)


@claim_app.command("rename-slug")
def claim_rename_slug(
    slug: Annotated[str, typer.Argument(help="Current slug.")],
    new_slug: Annotated[str, typer.Argument(help="New slug.")],
) -> None:
    """Change a claim's slug. Not possible once the claim has been published."""
    with entry_session() as session:
        claim = rename_slug(session, slug, new_slug)
        out.print(f"Renamed {slug} to {claim.slug}.", markup=False)


@claim_app.command("merge")
def claim_merge(
    from_slug: Annotated[str, typer.Argument(help="Slug of the duplicate, which is archived.")],
    into_slug: Annotated[str, typer.Argument(help="Slug of the claim that is kept.")],
    reason: Annotated[
        str, typer.Option("--reason", help="Why they are one claim. Kept, never published.")
    ],
    different_indication_accepted: Annotated[
        bool,
        typer.Option(
            "--different-indication-accepted",
            help="Merge though the two indications are worded differently. Say in the"
            " reason why they are one indication.",
        ),
    ] = False,
    awaiting_audit_accepted: Annotated[
        bool,
        typer.Option("--awaiting-audit-accepted", help="Merge though one of the two awaits audit."),
    ] = False,
    drop_name: Annotated[
        bool,
        typer.Option(
            "--drop-name",
            help="The duplicate's intervention name is a description: do not keep it as"
            " a synonym. Its synonyms are still kept.",
        ),
    ] = False,
    as_assistant: Annotated[
        bool,
        typer.Option(
            "--as-assistant",
            help="Record the merge as decided by an AI assistant, not by the operator.",
        ),
    ] = False,
) -> None:
    """Fold a duplicate claim into the claim that is kept: the same intervention for the
    same indication.

    The duplicate's articles, promises, reported statements, link leads, the names of
    its intervention and the papers, organisations and people its articles named move to
    the kept claim. Its registry matches and evidence events do not: the kept claim's
    registries are due to be searched again under every name it now has, so its status
    lists only events found for it. The duplicate is archived, never deleted, and its
    address leads to the kept claim after the next export.
    """
    with entry_session() as session:
        done = merge_claims(
            session,
            from_slug,
            into_slug,
            reason=reason,
            by=Decider.ASSISTANT if as_assistant else Decider.HUMAN,
            now=datetime.now(UTC),
            different_indication_accepted=different_indication_accepted,
            awaiting_audit_accepted=awaiting_audit_accepted,
            drop_name=drop_name,
        )
        by = ", decided by the assistant" if as_assistant else ""
        out.print(f"Merged {done.merged.slug} into {done.kept.slug}{by}.", markup=False)
        out.print(
            f"Moved {_count(done.articles_moved, 'article')},"
            f" {_count(done.promises_moved, 'promise')},"
            f" {_count(done.statements_moved, 'reported statement')},"
            f" {_count(done.leads_moved, 'link lead')} and"
            f" {done.entities_moved} named papers, organisations or people.",
            markup=False,
        )
        if done.articles_already_there:
            out.print(
                f"{_count(done.articles_already_there, 'article')} the kept claim already"
                " had stayed behind.",
                markup=False,
            )
        if done.names_gained:
            out.print(f"Now also known as: {', '.join(done.names_gained)}.", markup=False)
        if done.to_find_again:
            out.print(
                "Approved records left with the merged claim, to look for after the"
                f" search: {', '.join(done.to_find_again)}.",
                markup=False,
            )
        out.print(
            f"Registry matches and evidence events were not moved. Run `thenwhat prepare"
            f" {done.kept.slug}` (or `thenwhat prepare --due`), then export and deploy:"
            f" /{done.merged.slug} will lead to /{done.kept.slug}.",
            markup=False,
        )


@claim_app.command("import-csv")
def claim_import_csv(
    file: Annotated[
        Path, typer.Argument(exists=True, dir_okay=False, readable=True, help="CSV file.")
    ],
) -> None:
    """Import claims and source articles from a CSV file. All rows, or none."""
    with entry_session() as session, file.open(encoding="utf-8-sig", newline="") as lines:
        try:
            result = import_csv(session, lines)
        except CsvErrors as error:
            raise EntryError(f"Nothing was imported.\n{error}") from error
        out.print(
            f"Imported {_count(result.claims, 'claim')}, {_count(result.articles, 'article')}"
            f" and {_count(result.promises, 'promise')}.",
            markup=False,
        )


@article_app.command("add")
def article_add(
    claim_slug: Annotated[str, typer.Argument(help="Slug of the claim the article reports.")],
    url: Annotated[str, typer.Option(help="Address of the article.")],
    outlet: Annotated[str, typer.Option(help="Publication that ran it.")],
    title: Annotated[str, typer.Option(help="Article title.")],
    published: Annotated[
        datetime, typer.Option(formats=DATE_FORMATS, help="Publication date, YYYY-MM-DD.")
    ],
) -> None:
    """Attach a news article to a claim. Only its reference is stored, never its text."""
    with entry_session() as session:
        article = add_article(
            session,
            claim_slug,
            url=url,
            outlet=outlet,
            title=title,
            published_date=published.date(),
        )
        out.print(f"Added article {article.url} to {claim_slug}.", markup=False)


@promise_app.command("add")
def promise_add(
    claim_slug: Annotated[str, typer.Argument(help="Slug of the claim.")],
    article_url: Annotated[str, typer.Option(help="Article that made the promise.")],
    text: Annotated[str, typer.Option(help='The promised timeline, for example "by 2025".')],
    date_: Annotated[
        datetime | None,
        typer.Option(
            "--date", formats=DATE_FORMATS, help="Use this date instead of reading the text."
        ),
    ] = None,
) -> None:
    """Record a timeline promised in one of a claim's articles."""
    with entry_session() as session:
        promise = add_promise(
            session,
            claim_slug,
            article_url=article_url,
            description=text,
            parsed_date=date_.date() if date_ else None,
        )
        when = promise.parsed_date.isoformat() if promise.parsed_date else "no date"
        out.print(f"Added promise to {claim_slug}: {promise.description} ({when}).", markup=False)


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"
