"""Commands that create evidence events: fetching from registries and entry by hand."""

from datetime import UTC, datetime
from typing import Annotated

import typer
from sqlalchemy.orm import Session

from thenwhat.claims.entry import claim_by_slug
from thenwhat.claimsteps.evidence import ClaimFetch
from thenwhat.cli.claim_steps import outcome_line, run_for_claims, unfinished
from thenwhat.cli.console import err, out
from thenwhat.cli.entry import DATE_FORMATS, entry_session
from thenwhat.cli.session import settings_or_exit
from thenwhat.domain import EventType, RegulatoryOutcome, ReviewState, TrialPhase, TrialState
from thenwhat.events.fetch import LiteratureIndex, NoticeRegistry, TrialRegistry
from thenwhat.events.manual import MANUAL_SOURCE, add_manual_event
from thenwhat.sources.clinicaltrials import ClinicalTrials
from thenwhat.sources.crossref import Crossref
from thenwhat.sources.europepmc import EuropePmc

event_app = typer.Typer(help="Enter evidence events by hand.", no_args_is_help=True)


def make_evidence_sources(
    session: Session,
) -> tuple[TrialRegistry, LiteratureIndex, NoticeRegistry]:
    contact = settings_or_exit().contact_email
    return (
        ClinicalTrials(session, contact_email=contact),
        EuropePmc(session, contact_email=contact),
        Crossref(session, contact_email=contact),
    )


def fetch_command(
    claim_slug: Annotated[str, typer.Argument(help="Slug of the claim.")],
) -> None:
    """Read the registries for a claim's approved matches and record what they show, now:
    the step `claim_fetch` of `thenwhat prepare`.

    Trial events from an approved match are approved by rule. A follow-up paper is
    approved by rule when its confidence reaches the review threshold, and waits for
    your review otherwise. A registry that failed puts the claim off, and the command
    exits with 1.
    """
    with entry_session() as session:
        claim = claim_by_slug(session, claim_slug)
        claim_id, slug = claim.id, claim.slug
    [step] = run_for_claims([claim_id], [ClaimFetch.name], alone=True)
    with entry_session() as session:
        created = step.results.get(claim_id)
        if created is not None:
            pending = sum(event.review_state is ReviewState.PENDING for event in created)
            noun = "event" if len(created) == 1 else "events"
            out.print(f"Recorded {len(created)} new {noun} for {slug}; {pending} await review.")
            for event in created:
                out.print(
                    f"  {event.event_date}  {event.review_state.value:8}  {event.summary}",
                    markup=False,
                )
        out.print(f"Status: {claim_by_slug(session, slug).current_status.value}", markup=False)
        line = outcome_line(session, step, claim_id, slug)
        if line is not None:
            err.print(line, markup=False)
        if unfinished(session, [step], claim_id):
            raise typer.Exit(code=1)


@event_app.command("add")
def event_add(
    claim_slug: Annotated[str, typer.Argument(help="Slug of the claim.")],
    type: Annotated[EventType, typer.Option(help="Kind of event.")],
    date_: Annotated[
        datetime, typer.Option("--date", formats=DATE_FORMATS, help="When it happened.")
    ],
    source_url: Annotated[str, typer.Option(help="Link to the source that shows it.")],
    summary: Annotated[str, typer.Option(help="One plain sentence stating the fact.")],
    source_name: Annotated[str, typer.Option(help="Registry or publisher, e.g. jRCT.")] = (
        MANUAL_SOURCE
    ),
    identifier: Annotated[
        str | None, typer.Option("--id", help="Registry identifier or DOI. Needed for trials.")
    ] = None,
    phase: Annotated[
        list[TrialPhase] | None, typer.Option(help="Trial phase. Repeat for a combined phase.")
    ] = None,
    state: Annotated[
        TrialState | None, typer.Option(help="For a trial status change: the state reported.")
    ] = None,
    outcome: Annotated[
        RegulatoryOutcome | None, typer.Option(help="For a regulatory decision.")
    ] = None,
) -> None:
    """Enter an event by hand. It waits for review."""
    with entry_session() as session:
        event = add_manual_event(
            session,
            claim_slug,
            type=type,
            event_date=date_.date(),
            source_url=source_url,
            summary=summary,
            source_name=source_name,
            external_id=identifier,
            trial_phases=phase or [],
            trial_state=state,
            regulatory_outcome=outcome,
            now=datetime.now(UTC),
        )
        out.print(f"Added {event.type.value} event to {claim_slug}. It is pending review.")
