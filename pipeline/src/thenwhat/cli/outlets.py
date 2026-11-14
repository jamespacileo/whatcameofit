"""The outlets command: which outlets can be read, and what their pages carry."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from thenwhat.claims.entry import EntryError
from thenwhat.cli.console import err, out
from thenwhat.cli.entry import entry_session
from thenwhat.extract.page import Page
from thenwhat.outlets.readability import Checked, Measured, articles_csv, check_outlets, report


def make_measure():
    """A lookup of one page, compared with the trials approved for its claim.

    Each lookup has its own database session, committed when it ends, so several can run
    at once and a run that is stopped keeps what it has paid for: the registry answers
    it cached and the record of what it spent. All of them share one turn-taker per
    registry, so together they keep to each registry's rate. A lookup that fails is left
    out of the count rather than stopping the whole check.
    """
    from thenwhat.cli.extract import make_llm
    from thenwhat.cli.resolve import make_backend
    from thenwhat.cli.session import open_session, settings_or_exit
    from thenwhat.decide.core import DecisionFailed
    from thenwhat.llm.errors import LlmError
    from thenwhat.lookup.service import look_up
    from thenwhat.sources.base import Pacer, SourceError
    from thenwhat.sources.clinicaltrials import ClinicalTrials
    from thenwhat.sources.europepmc import EuropePmc

    contact = settings_or_exit().contact_email
    registry_turns, paper_turns = Pacer(), Pacer()

    def measure(page: Page, approved: list[str]) -> Measured | None:
        try:
            with open_session() as session:
                found = look_up(
                    session,
                    make_llm(session),
                    make_backend(session),
                    ClinicalTrials(session, contact_email=contact, pacer=registry_turns),
                    text=page.as_text(),
                    now=datetime.now(UTC),
                    page=page,
                    papers=EuropePmc(session, contact_email=contact, pacer=paper_turns),
                )
        except (SourceError, LlmError, DecisionFailed):
            return None
        likely = [candidate.external_id for candidate in found.candidates if candidate.likely]
        return Measured(
            found=bool(set(likely) & set(approved)), first=bool(likely) and likely[0] in approved
        )

    return measure


def _tell(checked: Checked) -> None:
    """One line of progress per article, apart from the record itself."""
    lookup = f", lookup: {checked.lookup}" if checked.lookup else ""
    err.print(f"{checked.outcome}{lookup}  {checked.url}", markup=False, soft_wrap=True)


def outlets_command(
    with_lookup: Annotated[
        bool,
        typer.Option(
            "--with-lookup",
            help="Also run a lookup on each article read and count how often it finds a"
            " trial approved for the article's claim. Slow, and it spends on the model.",
        ),
    ] = False,
    workers: Annotated[
        int,
        typer.Option(
            "--workers",
            min=1,
            max=8,
            help="How many outlets to check at the same time. One outlet is still asked one"
            " article a second, and each registry keeps its own rate.",
        ),
    ] = 4,
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
            session,
            make_retriever(),
            measure=make_measure() if with_lookup else None,
            workers=workers,
            on_article=_tell,
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
