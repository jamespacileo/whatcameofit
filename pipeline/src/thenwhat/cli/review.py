"""Review commands: the queue, decisions, failure flags and the evidence stage."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

import typer

from thenwhat.cli.console import out
from thenwhat.cli.entry import entry_session
from thenwhat.cli.session import settings_or_exit
from thenwhat.domain import EvidenceStage, ReviewState
from thenwhat.review.queue import confirm_stage, decide_item, flag_failure, pending_items

review_app = typer.Typer(help="Approve or reject what awaits review.", no_args_is_help=True)


class ItemKind(StrEnum):
    CLAIM = "claim"
    MATCH = "match"
    EVENT = "event"


@review_app.command("list")
def review_list(
    claim: Annotated[str | None, typer.Option(help="Only this claim.")] = None,
    kind: Annotated[ItemKind | None, typer.Option(help="Only this kind of item.")] = None,
) -> None:
    """Show what awaits review. Use the kind and id shown to approve or reject."""
    with entry_session() as session:
        items = pending_items(session, claim_slug=claim, kind=kind.value if kind else None)
        if not items:
            out.print("The review queue is empty.")
            return
        # One item per block, so a long source link is never cut short.
        for item in items:
            score = "" if item.score is None else f"  score {item.score:.2f}"
            out.print(f"{item.kind} {item.id}  {item.claim_slug}{score}", markup=False)
            out.print(f"  {item.assertion}", markup=False)
            out.print(f"  {item.source_url or 'no source link'}", markup=False)


def _decide(kind: ItemKind, item_id: int, state: ReviewState) -> None:
    settings = settings_or_exit()
    with entry_session() as session:
        decide_item(
            session,
            kind.value,
            item_id,
            state,
            now=datetime.now(UTC),
            no_signal_years=settings.no_signal_years,
        )
        out.print(f"{kind.value.capitalize()} {item_id} is now {state.value}.")


@review_app.command("approve")
def review_approve(
    kind: Annotated[ItemKind, typer.Argument(help="claim, match or event.")],
    item_id: Annotated[int, typer.Argument(help="The id shown by `review list`.")],
) -> None:
    """Approve an item. Also changes an earlier rejection."""
    _decide(kind, item_id, ReviewState.APPROVED)


@review_app.command("reject")
def review_reject(
    kind: Annotated[ItemKind, typer.Argument(help="claim, match or event.")],
    item_id: Annotated[int, typer.Argument(help="The id shown by `review list`.")],
) -> None:
    """Reject an item. It is kept, not deleted. Also changes an earlier approval,
    including one made by rule."""
    _decide(kind, item_id, ReviewState.REJECTED)


@review_app.command("flag-failure")
def review_flag_failure(
    claim_slug: Annotated[str, typer.Argument(help="Slug of the claim.")],
    trial: Annotated[str, typer.Option(help="Registry identifier of the trial that failed.")],
    event: Annotated[int, typer.Option(help="Id of the approved event that reports the result.")],
    source_url: Annotated[str, typer.Option(help="Link showing the primary endpoint was missed.")],
) -> None:
    """Record that a trial missed its primary endpoint. The only way to a failed status."""
    settings = settings_or_exit()
    with entry_session() as session:
        flag_failure(
            session,
            claim_slug,
            trial_id=trial,
            event_id=event,
            source_url=source_url,
            now=datetime.now(UTC),
            no_signal_years=settings.no_signal_years,
        )
        out.print(
            f"Trial {trial} of {claim_slug} is flagged as having missed its primary endpoint."
        )


@review_app.command("stage")
def review_stage(
    claim_slug: Annotated[str, typer.Argument(help="Slug of the claim.")],
    stage: Annotated[EvidenceStage, typer.Argument(help="Evidence at the time of announcement.")],
) -> None:
    """Confirm or correct the stage of evidence at announcement."""
    with entry_session() as session:
        claim = confirm_stage(session, claim_slug, stage)
        out.print(f"Evidence stage of {claim.slug}: {stage.value}.")
