"""Claims that `thenwhat prepare` approved and that wait for the audit of their batch,
and the reads the audit settles: those left unresolved because they overlap a claim."""

import json
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Annotated

import typer
from sqlalchemy.orm import Session

from thenwhat.backfill.link_read import (
    Attached,
    LinkRead,
    NotAnOverlap,
    NotAttached,
    dismiss_overlap,
    overlapping_read,
    reads_naming_archived_claims,
    reads_naming_live_claims,
)
from thenwhat.backfill.link_rekey import refuse_stale_keys
from thenwhat.backfill.outlet_hold import LEFT_FOR_LATER
from thenwhat.claims.audit import (
    AuditOpinion,
    judge_claim,
    release_batch,
    sample_batch,
    sample_slugs,
    spot_check_batch,
)
from thenwhat.claims.entry import AuditRefused, awaiting_audit, clear_audit
from thenwhat.claimsteps.run import never_searched
from thenwhat.claimsteps.step import prepared
from thenwhat.cli import backfill
from thenwhat.cli.console import err, out
from thenwhat.cli.entry import entry_session
from thenwhat.cli.session import settings_or_exit
from thenwhat.domain import Decider
from thenwhat.work.errors import BackfillError

audit_app = typer.Typer(no_args_is_help=True, help="Claims held off the site until audited.")


@audit_app.command("list")
def audit_list() -> None:
    """List the claims held off the site until audited, oldest hold first, then the
    reads left unresolved because they overlap an archived claim, then those that
    overlap a claim that is not archived, then the claims awaiting review or published
    that were never searched: no registry search has left a record for them."""
    with entry_session() as session:
        held = awaiting_audit(session)
        for claim in held:
            assert claim.awaiting_audit_at is not None
            archived = "  archived" if claim.archived_at is not None else ""
            out.print(
                f"{claim.slug}  held since {claim.awaiting_audit_at:%Y-%m-%d %H:%M}"
                f"  {claim.current_status.value}{archived}",
                markup=False,
            )
        if held:
            noun = "claim awaits" if len(held) == 1 else "claims await"
            out.print(f"{len(held)} {noun} audit.", markup=False)
        else:
            out.print("No claim awaits audit.")
        _list_archived_overlaps(session)
        _list_live_overlaps(session)
        _list_never_searched(session)


def _list_never_searched(session: Session) -> None:
    """Claims awaiting review or published with no record of a registry search, whatever
    status they hold: a status of no trial found means nothing for them yet. Their
    search is due for `thenwhat prepare`."""
    never = never_searched(session, prepared())
    if not never:
        return
    for slug in never:
        out.print(f"{slug}  never searched", markup=False)
    noun = "claim was" if len(never) == 1 else "claims were"
    out.print(
        f"{len(never)} {noun} never searched: `thenwhat prepare --due` searches them.",
        markup=False,
    )


def _list_archived_overlaps(session: Session) -> None:
    """Reads that drafted no claim because an archived claim has their treatment and
    condition. Fixing and unarchiving the claim, then reading the lead again, joins it."""
    overlaps = reads_naming_archived_claims(session)
    if not overlaps:
        return
    for lead, claim in overlaps:
        out.print(f"lead {lead.id}  overlaps archived {claim.slug}  {lead.url}", markup=False)
    noun = "read overlaps" if len(overlaps) == 1 else "reads overlap"
    out.print(f"{len(overlaps)} {noun} an archived claim and made no claim.", markup=False)


def _list_live_overlaps(session: Session) -> None:
    """Reads that drafted no claim because a claim that is not archived has their
    treatment and condition, though the decision did not say the article reports it.
    Such a read is not tried again: the operator attaches the article to the claim
    (`audit attach`), says it is no report of it (`audit dismiss`), or leaves it."""
    overlaps = reads_naming_live_claims(session)
    if not overlaps:
        return
    for lead, claim in overlaps:
        out.print(
            f"lead {lead.id}  overlaps {claim.slug} ({claim.review_state.value})  {lead.url}",
            markup=False,
        )
    noun = "read overlaps" if len(overlaps) == 1 else "reads overlap"
    out.print(
        f"{len(overlaps)} {noun} a claim that is not archived and made no claim:"
        " attach the article with `thenwhat audit attach <lead>`, or say it is no report"
        " of the claim with `thenwhat audit dismiss <lead> --reason`.",
        markup=False,
    )


@audit_app.command("clear")
def audit_clear(
    slugs: Annotated[
        list[str] | None, typer.Argument(help="Slugs of legacy held claims whose audit passed.")
    ] = None,
    batch: Annotated[
        str | None, typer.Option(help="Release a judged publication audit batch.")
    ] = None,
) -> None:
    """Let audited claims be published from the next export on. A claim that should not
    be published is archived instead. If any slug is not awaiting audit, nothing is cleared."""
    with entry_session() as session:
        if batch is not None:
            if slugs:
                raise AuditRefused("Give a batch or individual slugs.")
            settings = settings_or_exit()
            count = release_batch(
                session,
                batch,
                max_wrong_share=settings.audit_max_wrong_share,
                now=datetime.now(UTC),
            )
            noun = "claim" if count == 1 else "claims"
            out.print(
                f"Cleared {count} {noun} in {batch}. Export and deploy to publish.",
                markup=False,
            )
            return
        if not slugs:
            raise AuditRefused("Give claim slugs or --batch.")
        cleared = clear_audit(session, slugs)
        noun = "claim" if len(cleared) == 1 else "claims"
        out.print(
            f"Cleared {len(cleared)} {noun}. Export and deploy to publish them.", markup=False
        )
        for claim in cleared:
            if claim.archived_at is not None:
                out.print(f"{claim.slug} is archived and stays off the site.", markup=False)


AS_ASSISTANT = Annotated[
    bool,
    typer.Option(
        "--as-assistant",
        help="Record the decision as an AI assistant's, not yours.",
    ),
]


@audit_app.command("sample")
def audit_sample(
    batch: Annotated[str, typer.Option(help="Name of the held draft batch.")],
    whole: Annotated[bool, typer.Option("--all", help="Draw every eligible held claim.")] = False,
    fresh: Annotated[
        bool, typer.Option(help="Draw again after addressing defects or a stale sample.")
    ] = False,
) -> None:
    """Draw or retrieve the batch's publication audit."""
    settings = settings_or_exit()
    with entry_session() as session:
        sample = sample_batch(
            session,
            batch,
            size=settings.audit_sample_size,
            whole=whole,
            fresh=fresh,
            now=datetime.now(UTC),
        )
        typer.echo(
            json.dumps(
                {
                    "batch": batch,
                    "sample": sample.id,
                    "seed": sample.seed,
                    "population": len(sample.population_ids),
                    "claims": sample_slugs(session, sample),
                }
            )
        )


@audit_app.command("judge")
def audit_judge(
    sample: Annotated[int, typer.Argument(help="Recorded audit sample number.")],
    slug: Annotated[str, typer.Argument(help="Claim selected in the sample.")],
    right: Annotated[bool, typer.Option("--right/--wrong", help="Judgement against the evidence.")],
    reviewer: Annotated[str, typer.Option(help="Name or handle for the reviewer.")],
    category: Annotated[str | None, typer.Option(help="Category of a defect.")] = None,
    detail: Annotated[str | None, typer.Option(help="Evidence for a wrong judgement.")] = None,
    as_assistant: AS_ASSISTANT = False,
) -> None:
    """Record a judgement on one sampled claim with the reviewer's role."""
    by = Decider.ASSISTANT if as_assistant else Decider.HUMAN
    with entry_session() as session:
        judge_claim(
            session,
            sample,
            slug,
            AuditOpinion(right, by, reviewer, category, detail),
            now=datetime.now(UTC),
        )
        out.print(f"Recorded {by.value} judgement for {slug} in sample {sample}.", markup=False)


@audit_app.command("spot-check")
def audit_spot_check(
    batch: Annotated[str, typer.Option(help="Batch with assistant judgements.")],
    size: Annotated[
        int | None, typer.Option(min=1, help="Number to draw for the operator.")
    ] = None,
) -> None:
    """Draw an operator spot-check and report the recorded differences."""
    with entry_session() as session:
        typer.echo(json.dumps(asdict(spot_check_batch(session, batch, size=size))))


LEAD_IDS = Annotated[
    list[int],
    typer.Argument(help="Numbers of the leads, as `thenwhat audit list` gives them."),
]


@audit_app.command("attach")
def audit_attach(lead_ids: LEAD_IDS, as_assistant: AS_ASSISTANT = False) -> None:
    """Attach the article of each listed read to the claim it overlaps, as the read would
    have had it found them the same. The page reader is asked for the page again, under
    the rules of any read, and the headline and publication date are the page's own.
    Only an approved claim that is not archived is given an article; a lead that cannot
    be attached is said so, left as it was, and the others are carried on with."""
    settings = settings_or_exit()
    by = Decider.ASSISTANT if as_assistant else Decider.HUMAN
    attached = refused = left = 0
    with backfill.refusals():
        step = next(one for one in backfill.steps_for(settings) if isinstance(one, LinkRead))
        with backfill.open_session() as session:
            # A lead keyed under an earlier form would miss an article the claim has.
            refuse_stale_keys(session)
        allowances = backfill.make_allowances(settings)
        allowances.of(step.source)
        client = backfill.make_client(step, settings, allowances)
        for lead_id in lead_ids:
            # A transaction for each lead: what was attached stays attached when a later
            # lead ends the command.
            with backfill.open_session() as session:
                try:
                    lead, claim = overlapping_read(session, lead_id)
                except NotAnOverlap as not_one:
                    refused += 1
                    err.print(str(not_one), markup=False)
                    continue
                answer = step.attach(session, lead, claim, client, by=by)
                if isinstance(answer, Attached):
                    attached += 1
                    article = answer.article
                    how = "attached to" if answer.added else "joined to the article of"
                    out.print(
                        f"lead {lead_id}  {how} {claim.slug}  {article.published_date}"
                        f"  {article.outlet}: {article.title}",
                        markup=False,
                    )
                elif isinstance(answer, NotAttached):
                    refused += 1
                    err.print(f"lead {lead_id}  not attached: {answer.reason}", markup=False)
                else:
                    left += 1
                    out.print(f"lead {lead_id}  left for later: {answer.reason}", markup=False)
    noun = "article" if attached == 1 else "articles"
    whose = ", decided by the assistant" if as_assistant else ""
    out.print(
        f"Attached {attached} {noun}{whose}; {refused} not attached, {left} left for later."
        + (" Export and deploy to publish them." if attached else ""),
        markup=False,
    )
    if refused:
        raise typer.Exit(code=1)
    if left:
        raise typer.Exit(code=LEFT_FOR_LATER)


@audit_app.command("dismiss")
def audit_dismiss(
    lead_ids: LEAD_IDS,
    reason: Annotated[
        str,
        typer.Option(help="Why the article is no report of the claim. Kept, never published."),
    ],
    as_assistant: AS_ASSISTANT = False,
) -> None:
    """Say that the article of each listed read is no report of the claim it overlaps.
    Nothing is attached: the lead keeps its outcome, is not read again and is no longer
    listed. A lead that is not such a read is said so and the others are carried on with."""
    by = Decider.ASSISTANT if as_assistant else Decider.HUMAN
    dismissed = refused = 0
    with entry_session() as session:
        for lead_id in lead_ids:
            try:
                _, claim = dismiss_overlap(
                    session, lead_id, reason=reason, by=by, now=datetime.now(UTC)
                )
            except BackfillError as not_one:
                refused += 1
                err.print(str(not_one), markup=False)
                continue
            dismissed += 1
            out.print(f"lead {lead_id}  not a report of {claim.slug}", markup=False)
    noun = "read" if dismissed == 1 else "reads"
    whose = ", decided by the assistant" if as_assistant else ""
    out.print(f"Dismissed {dismissed} {noun}{whose}.", markup=False)
    if refused:
        raise typer.Exit(code=1)
