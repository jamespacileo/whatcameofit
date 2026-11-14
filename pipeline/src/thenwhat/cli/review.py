"""Review commands: the queue, decisions, failure flags and the evidence stage."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

import typer

from thenwhat.claims.entry import EntryError, find_claim
from thenwhat.claims.mesh_areas import suggestion_line
from thenwhat.cli.console import out
from thenwhat.cli.entry import entry_session
from thenwhat.cli.session import settings_or_exit
from thenwhat.domain import Decider, EvidenceStage, ReviewState
from thenwhat.review.queue import (
    confirm_stage,
    decide_item,
    decide_matches,
    flag_failure,
    pending_items,
    rejected_by_rule,
)

review_app = typer.Typer(help="Approve or reject what awaits review.", no_args_is_help=True)


AS_ASSISTANT = Annotated[
    bool,
    typer.Option(
        "--as-assistant",
        help="Record the decision as an AI assistant's, not yours. The claim is published,"
        " and the data file says no person checked it.",
    ),
]


def _decider(as_assistant: bool) -> Decider:
    return Decider.ASSISTANT if as_assistant else Decider.HUMAN


class ItemKind(StrEnum):
    CLAIM = "claim"
    MATCH = "match"
    EVENT = "event"
    TERM = "term"


@review_app.command("list")
def review_list(
    claim: Annotated[str | None, typer.Option(help="Only this claim.")] = None,
    kind: Annotated[ItemKind | None, typer.Option(help="Only this kind of item.")] = None,
    by_rule: Annotated[
        bool,
        typer.Option(
            "--by-rule",
            help="Show instead the candidate matches a rule rejected for scoring near zero."
            " Approve any of them with `review approve match ID`.",
        ),
    ] = False,
) -> None:
    """Show what awaits review. Use the kind and id shown to approve or reject."""
    with entry_session() as session:
        if by_rule:
            items = rejected_by_rule(session, claim_slug=claim)
            if not items:
                out.print("No candidate match has been rejected by rule.")
                return
        else:
            items = pending_items(session, claim_slug=claim, kind=kind.value if kind else None)
            if not items:
                out.print("The review queue is empty.")
                return
        # One item per block, so a long source link is never cut short.
        for item in items:
            score = "" if item.score is None else f"  score {item.score:.2f}"
            out.print(f"{item.kind} {item.id}  {item.claim_slug}{score}", markup=False)
            out.print(f"  {item.assertion}", markup=False)
            if item.detail:
                out.print(f"  {item.detail}", markup=False)
            if item.kind == ItemKind.CLAIM:
                found = find_claim(session, item.claim_slug)
                if found is not None:
                    out.print(f"  {suggestion_line(session, found)}", markup=False)
            out.print(f"  {item.source_url or 'no source link'}", markup=False)


ITEM_IDS = Annotated[
    list[int] | None,
    typer.Argument(help="One or more ids shown by `review list`."),
]
CLAIM = Annotated[
    str | None,
    typer.Option("--claim", help="For matches: decide this claim's pending candidates by score."),
]
AT_LEAST = Annotated[
    float | None, typer.Option("--at-least", help="With --claim: candidates scored this or more.")
]
BELOW = Annotated[
    float | None, typer.Option("--below", help="With --claim: candidates scored under this.")
]


def _decide(
    kind: ItemKind,
    item_ids: list[int] | None,
    state: ReviewState,
    as_assistant: bool,
    claim: str | None,
    at_least: float | None,
    below: float | None,
) -> None:
    settings = settings_or_exit()
    by = ", decided by the assistant" if as_assistant else ""
    with entry_session() as session:
        if claim is not None:
            if kind is not ItemKind.MATCH or item_ids:
                raise EntryError("--claim decides matches by score; give it without ids.")
            decided = decide_matches(
                session,
                claim,
                state,
                now=datetime.now(UTC),
                at_least=at_least,
                below=below,
                no_signal_years=settings.no_signal_years,
                by=_decider(as_assistant),
            )
            noun = "match" if len(decided) == 1 else "matches"
            out.print(f"{len(decided)} {noun} of {claim} now {state.value}{by}.", markup=False)
            return
        if not item_ids:
            raise EntryError("Give the ids to decide, or --claim with --at-least or --below.")
        for item_id in item_ids:
            decide_item(
                session,
                kind.value,
                item_id,
                state,
                now=datetime.now(UTC),
                no_signal_years=settings.no_signal_years,
                by=_decider(as_assistant),
            )
            out.print(f"{kind.value.capitalize()} {item_id} is now {state.value}{by}.")


@review_app.command("approve")
def review_approve(
    kind: Annotated[ItemKind, typer.Argument(help="claim, match, event or term.")],
    item_ids: ITEM_IDS = None,
    as_assistant: AS_ASSISTANT = False,
    claim: CLAIM = None,
    at_least: AT_LEAST = None,
    below: BELOW = None,
) -> None:
    """Approve one or more items. Also changes an earlier rejection."""
    _decide(kind, item_ids, ReviewState.APPROVED, as_assistant, claim, at_least, below)


@review_app.command("reject")
def review_reject(
    kind: Annotated[ItemKind, typer.Argument(help="claim, match, event or term.")],
    item_ids: ITEM_IDS = None,
    as_assistant: AS_ASSISTANT = False,
    claim: CLAIM = None,
    at_least: AT_LEAST = None,
    below: BELOW = None,
) -> None:
    """Reject one or more items. They are kept, not deleted. Also changes an earlier
    approval, including one made by rule."""
    _decide(kind, item_ids, ReviewState.REJECTED, as_assistant, claim, at_least, below)


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
    as_assistant: AS_ASSISTANT = False,
) -> None:
    """Confirm or correct the stage of evidence at announcement."""
    settings = settings_or_exit()
    with entry_session() as session:
        claim = confirm_stage(
            session,
            claim_slug,
            stage,
            now=datetime.now(UTC),
            no_signal_years=settings.no_signal_years,
            by=_decider(as_assistant),
        )
        out.print(f"Evidence stage of {claim.slug}: {stage.value}.")
