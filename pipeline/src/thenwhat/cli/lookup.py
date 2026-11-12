"""The lookup command: the registry trials behind an article or a post."""

import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated

import typer
from sqlalchemy.orm import Session

from thenwhat.claims.entry import EntryError
from thenwhat.cli.console import out
from thenwhat.cli.entry import entry_session
from thenwhat.extract.retrieve import PasteNeeded

if TYPE_CHECKING:
    from thenwhat.decide.core import Backend
    from thenwhat.extract.page import Page
    from thenwhat.llm.client import Llm
    from thenwhat.lookup.service import Papers, Trials

# Why a record is ranked where it is, in the operator's words.
WHY = {
    "stated": "the article gives this number",
    "paper": "a paper the article links to gives this number",
    "trial_name": "same trial name",
    "participants": "same number of participants",
    "sponsor": "same sponsor",
}


def make_tools(session: Session) -> tuple["Llm", "Backend", "Trials"]:
    from thenwhat.cli.extract import make_llm
    from thenwhat.cli.resolve import make_backend
    from thenwhat.cli.session import settings_or_exit
    from thenwhat.sources.clinicaltrials import ClinicalTrials

    trials = ClinicalTrials(session, contact_email=settings_or_exit().contact_email)
    return make_llm(session), make_backend(session), trials


def make_papers(session: Session) -> "Papers":
    from thenwhat.cli.session import settings_or_exit
    from thenwhat.sources.europepmc import EuropePmc

    return EuropePmc(session, contact_email=settings_or_exit().contact_email)


def _text(url: str | None, paste: bool) -> tuple[str, "Page | None"]:
    """The text for this run only, and the page it came from. Neither is stored."""
    if paste:
        text = sys.stdin.read().strip()
        if not text:
            raise EntryError("No text arrived on standard input.")
        return text, None
    if url is None:
        raise EntryError("Give the address of an article, or use --paste and pipe the text in.")
    from thenwhat.cli.extract import make_retriever

    try:
        retrieved = make_retriever().retrieve(url)
    except PasteNeeded as needed:
        raise EntryError(f"{needed} Run the command again with --paste.") from None
    page = retrieved.page
    return (page.as_text() if page else retrieved.text), page


def lookup_command(
    url: Annotated[
        str | None, typer.Argument(help="Address of a news article. Leave out with --paste.")
    ] = None,
    paste: Annotated[
        bool,
        typer.Option(
            "--paste",
            help="Read the text of the article or post from standard input instead of fetching.",
        ),
    ] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Print the result as JSON.")] = False,
) -> None:
    """Find the registry trials behind an article or a post. The answer is a ranked list
    of candidates for you to check, not a reviewed status. No claim is stored."""
    from thenwhat.lookup.details import STATED
    from thenwhat.lookup.service import LIKELY_FROM, look_up

    with entry_session() as session:
        text, page = _text(url, paste)
        llm, backend, trials = make_tools(session)
        found = look_up(
            session,
            llm,
            backend,
            trials,
            text=text,
            now=datetime.now(UTC),
            page=page,
            papers=make_papers(session) if page else None,
        )

    if as_json:
        out.print(json.dumps(asdict(found), ensure_ascii=False, indent=2), markup=False)
        return
    if found.intervention is None:
        out.print("This text does not report a specific treatment for a condition.")
        if found.gist:
            out.print(f"  {found.gist}", markup=False)
        return
    also = f" (also: {', '.join(found.names[1:])})" if found.names[1:] else ""
    out.print(f"Treatment: {found.intervention}{also}", markup=False)
    if found.known_names:
        out.print(
            f"Also searched under names the text does not give: {', '.join(found.known_names)}",
            markup=False,
        )
    out.print(f"Condition: {found.indication}", markup=False)
    said = [
        f"trial name {found.details.trial_name}" if found.details.trial_name else "",
        f"{found.details.participants} participants" if found.details.participants else "",
        f"run by {found.details.sponsor}" if found.details.sponsor else "",
    ]
    if any(said):
        out.print(f"Of the trial, the text says: {', '.join(s for s in said if s)}", markup=False)
    if found.paper_numbers:
        out.print(
            f"A paper the article links to gives: {', '.join(found.paper_numbers)}", markup=False
        )
    for slug in found.tracked:
        out.print(f"Already tracked as claim {slug}.", markup=False)
    likely = [c for c in found.candidates if c.score >= LIKELY_FROM or STATED in c.agrees]
    other = [c for c in found.candidates if c not in likely]
    if not found.candidates:
        out.print("No trial record was found in the registry searched.")
        return
    out.print(
        f"{len(likely)} likely trial {'record' if len(likely) == 1 else 'records'},"
        f" {len(other)} other found. Likeliest first:"
    )
    for candidate in [*likely, *other[:5]]:
        out.print(
            f"  {candidate.score:.2f}  {candidate.external_id}  {candidate.url}", markup=False
        )
        out.print(f"        {candidate.summary}", markup=False)
        if candidate.agrees:
            why = "; ".join(WHY[reason] for reason in candidate.agrees)
            out.print(f"        Agrees: {why}", markup=False)
