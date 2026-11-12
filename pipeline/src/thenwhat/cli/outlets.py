"""The outlets command: which outlets can be read, and what their pages carry."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from sqlalchemy.orm import Session

from thenwhat.claims.entry import EntryError
from thenwhat.cli.console import out
from thenwhat.cli.entry import entry_session
from thenwhat.extract.page import Page
from thenwhat.outlets.readability import Measured, articles_csv, check_outlets, report


def make_measure(session: Session):
    """A lookup of one page, compared with the trials approved for its claim. A lookup
    that fails is left out of the count rather than stopping the whole check."""
    from thenwhat.cli.lookup import make_papers, make_tools
    from thenwhat.llm.errors import LlmError
    from thenwhat.lookup.details import STATED
    from thenwhat.lookup.service import LIKELY_FROM, look_up
    from thenwhat.sources.base import SourceError

    llm, backend, trials = make_tools(session)
    papers = make_papers(session)

    def measure(page: Page, approved: list[str]) -> Measured | None:
        try:
            found = look_up(
                session,
                llm,
                backend,
                trials,
                text=page.as_text(),
                now=datetime.now(UTC),
                page=page,
                papers=papers,
            )
        except (SourceError, LlmError):
            return None
        likely = [
            candidate.external_id
            for candidate in found.candidates
            if candidate.score >= LIKELY_FROM or STATED in candidate.agrees
        ]
        return Measured(
            found=bool(set(likely) & set(approved)), first=bool(likely) and likely[0] in approved
        )

    return measure


def outlets_command(
    with_lookup: Annotated[
        bool,
        typer.Option(
            "--with-lookup",
            help="Also run a lookup on each article read and count how often it finds a"
            " trial approved for the article's claim. Slow, and it spends on the model.",
        ),
    ] = False,
    save: Annotated[
        Path | None,
        typer.Option("--save", help="Write the record to this file as well as printing it."),
    ] = None,
    articles: Annotated[
        Path | None,
        typer.Option("--articles", help="Write one row per article address to this CSV file."),
    ] = None,
) -> None:
    """Ask for every tracked article once and record, per outlet, whether its site let the
    article be read and which signals its pages carry. No article text is kept."""
    from thenwhat.cli.extract import make_retriever

    with entry_session() as session:
        outlets = check_outlets(
            session, make_retriever(), measure=make_measure(session) if with_lookup else None
        )
        if not outlets:
            raise EntryError("No article is tracked, so there is no outlet to check.")
    page = report(outlets, checked=datetime.now(UTC).date())
    out.print(page, markup=False, soft_wrap=True)
    if save is not None:
        save.write_text(page)
        out.print(f"Saved to {save}.", markup=False)
    if articles is not None:
        articles.write_text(articles_csv(outlets))
        out.print(f"Wrote one row per article to {articles}.", markup=False)
