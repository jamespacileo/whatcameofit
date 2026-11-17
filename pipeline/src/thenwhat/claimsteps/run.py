"""The claim steps as the settings give them, and running them: every due part for many
claims, or every part named for one claim whatever its ledger says. Behavior: openspec
claim-extraction, "Preparing many claims" and "Unfinished parts of a published claim are
completed"."""

import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial

from sqlalchemy import ColumnElement, exists, select, tuple_, update
from sqlalchemy.orm import Session

from thenwhat.claimsteps.articles import ClaimArticles, ClaimNamedRecords
from thenwhat.claimsteps.decide import ClaimDecide
from thenwhat.claimsteps.evidence import ClaimFetch, ClaimReadings
from thenwhat.claimsteps.inputs import CLAIM, notice_changes
from thenwhat.claimsteps.search import ClaimPapers, ClaimSubstance, ClaimTrials
from thenwhat.claimsteps.step import ClaimSources, ClaimStep, OpenSession, now_utc
from thenwhat.claimsteps.terms import ClaimTerms
from thenwhat.config import Settings
from thenwhat.db.models import Claim, RegistrySearch, WorkEntry
from thenwhat.domain import WorkOutcome
from thenwhat.work.ledger import due_records
from thenwhat.work.outcome import UndeclaredReason, declared
from thenwhat.work.runner import RunReport, measured_run, run_step

SUBSTANCE = ClaimSubstance.name
TRIALS = ClaimTrials.name


def claim_steps(
    settings: Settings,
    *,
    claims: ColumnElement[bool] | None = None,
    clock: Callable[[], datetime] = now_utc,
    rescore: bool = False,
    redo_rule: bool = False,
    rescore_pending: bool = False,
) -> list[ClaimStep]:
    """Every claim step in the order a run takes them, each for `claims` (by default
    every claim awaiting review, and every approved claim not archived). The decision is
    a step only while drafts are decided by rule. `rescore`, `redo_rule` and
    `rescore_pending` are the per-claim commands' options."""
    reject_below, accept_above = settings.match_reject_below, settings.match_accept_above
    articles = ClaimArticles(
        site_retry_wait=timedelta(hours=settings.lead_site_retry_hours), claims=claims, clock=clock
    )
    substance = ClaimSubstance(claims=claims, clock=clock)
    trials = ClaimTrials(
        reject_below=reject_below,
        accept_above=accept_above,
        approve_drafts_by_rule=settings.approve_drafts_by_rule,
        stage_threshold=settings.review_confidence_threshold,
        no_signal_years=settings.no_signal_years,
        rescore=rescore,
        redo_rule=redo_rule,
        claims=claims,
        clock=clock,
    )
    trials.after = (substance,)
    papers = ClaimPapers(
        papers_enabled=bool(settings.openalex_api_key),
        reject_below=reject_below,
        accept_above=accept_above,
        rescore=rescore,
        claims=claims,
        clock=clock,
    )
    papers.after = (trials,)
    named = ClaimNamedRecords(
        reject_below=reject_below,
        accept_above=accept_above,
        papers_enabled=bool(settings.openalex_api_key),
        claims=claims,
        clock=clock,
    )
    fetch = ClaimFetch(
        threshold=settings.review_confidence_threshold,
        no_signal_years=settings.no_signal_years,
        paper_max_age=timedelta(days=settings.paper_record_max_age_days),
        claims=claims,
        clock=clock,
    )
    fetch.after = (trials,)
    readings = ClaimReadings(at_once=settings.readings_at_once, claims=claims, clock=clock)
    readings.after = (fetch,)
    terms = ClaimTerms(
        reject_below=reject_below,
        accept_above=accept_above,
        term_limit=settings.term_candidates_max,
        target_limit=settings.target_candidates_max,
        rescore_pending=rescore_pending,
        claims=claims,
        clock=clock,
    )
    steps: list[ClaimStep] = [articles, substance, trials, papers, named, fetch, readings, terms]
    if settings.approve_drafts_by_rule:
        decide = ClaimDecide(claims=claims, clock=clock)
        # Its articles too: a draft is not decided before what its articles say is read.
        decide.after = (articles, substance, trials, fetch)
        steps.append(decide)
    return steps


def named_steps(steps: Sequence[ClaimStep], names: Sequence[str]) -> list[ClaimStep]:
    """The steps of these names, in the order given."""
    by_name = {step.name: step for step in steps}
    return [by_name[name] for name in names]


@dataclass(frozen=True, slots=True)
class StepRun:
    """What one step did in a run, and how long it took."""

    step: ClaimStep
    report: RunReport
    seconds: float


def merged(reports: Sequence[RunReport]) -> RunReport:
    together = RunReport(errors=[])
    for report in reports:
        together.done += report.done
        together.nothing_found += report.nothing_found
        together.failed += report.failed
        together.later += report.later
        together.before_work += report.before_work
        together.needs_fix += report.needs_fix
        together.stopped = together.stopped or report.stopped
        together.errors = (together.errors or []) + (report.errors or [])
    together.remaining_due = min(report.remaining_due for report in reports)
    return together


def run_claim_steps(
    open_session: OpenSession,
    steps: Sequence[ClaimStep],
    make_sources: Callable[[], ClaimSources],
    *,
    attempt_limit: int,
    put_off_span: timedelta,
    now: Callable[[], datetime],
    workers: int = 1,
    before_call: Callable[[Session], None] | None = None,
) -> list[StepRun]:
    """Run each step over its due claims in turn, `workers` claims at a time. Before each
    step the claims whose input changed are made due again, so a part an earlier step
    changed is done in the same run. A step whose source cannot be asked stops; the
    steps after it still run."""
    runs: list[StepRun] = []
    for step in steps:
        started = time.monotonic()
        with open_session() as session:
            notice_changes(session, steps)
        # The claims a worker failed on or put off in this run, kept from the others.
        tried: set[int] = set()
        with measured_run(step.name, limit=None, workers=workers) as shared:
            work = partial(
                run_step,
                open_session,
                step,
                now=now,
                attempt_limit=attempt_limit,
                before_call=before_call,
                tried=tried,
                run=shared,
                put_off_span=put_off_span,
            )
            clients = [make_sources() for _ in range(workers)]
            if workers == 1:
                report = work(clients[0])
            else:
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    report = merged(list(pool.map(work, clients)))
        report.not_written = shared.not_written
        runs.append(StepRun(step, report, time.monotonic() - started))
    return runs


def make_due(session: Session, steps: Sequence[ClaimStep], claim_ids: Sequence[int]) -> None:
    """Make the claims due for these steps whatever their entries hold, as when the
    operator names a claim to a command: each entry is marked stale and its attempts
    start again when the claim is worked on."""
    session.execute(
        update(WorkEntry)
        .where(
            WorkEntry.record_kind == CLAIM,
            WorkEntry.record_id.in_(claim_ids),
            tuple_(WorkEntry.step, WorkEntry.step_version).in_(
                [(step.name, step.version) for step in steps]
            ),
        )
        .values(stale=True)
        .execution_options(synchronize_session=False)
    )


def search_due(session: Session, steps: Sequence[ClaimStep], attempt_limit: int) -> list[int]:
    """The claims whose registry search is due: due for the substance lookup or the
    trial search."""
    due: set[int] = set()
    for step in steps:
        if step.name in (SUBSTANCE, TRIALS):
            query = due_records(step, attempt_limit).with_only_columns(Claim.id)
            due.update(session.scalars(query))
    return sorted(due)


@dataclass(frozen=True, slots=True)
class Left:
    """A part of a claim's preparation that a run left for later or for a person."""

    slug: str
    step: str
    outcome: WorkOutcome
    said: str
    not_before: datetime | None


def handled_since(session: Session, steps: Sequence[ClaimStep], since: datetime) -> list[Claim]:
    """The claims any of the steps was run for since `since`."""
    return list(
        session.scalars(
            select(Claim)
            .where(
                Claim.id.in_(
                    select(WorkEntry.record_id).where(
                        WorkEntry.record_kind == CLAIM,
                        WorkEntry.step.in_([step.name for step in steps]),
                        WorkEntry.last_attempt_at >= since,
                    )
                )
            )
            .order_by(Claim.slug)
        )
    )


def left_by(session: Session, steps: Sequence[ClaimStep], since: datetime) -> list[Left]:
    """Each part a run since `since` left failed, put off or needing a fix, by claim."""
    by_name = {step.name: step for step in steps}
    rows = session.execute(
        select(Claim.slug, WorkEntry)
        .join(WorkEntry, WorkEntry.record_id == Claim.id)
        .where(
            WorkEntry.record_kind == CLAIM,
            tuple_(WorkEntry.step, WorkEntry.step_version).in_(
                [(step.name, step.version) for step in steps]
            ),
            WorkEntry.stale.is_(False),
            WorkEntry.last_attempt_at >= since,
            WorkEntry.outcome.in_((WorkOutcome.FAILED, WorkOutcome.LATER, WorkOutcome.NEEDS_FIX)),
        )
        .order_by(Claim.slug, WorkEntry.step)
    )
    left: list[Left] = []
    for slug, entry in rows:
        if entry.outcome is WorkOutcome.FAILED:
            said = entry.error or ""
        else:
            try:
                said = declared(by_name[entry.step], entry.reason or "").say(entry.reason_values)
            except UndeclaredReason:
                said = entry.reason or ""
        left.append(Left(slug, entry.step, entry.outcome, said, entry.not_before))
    return left


def never_searched(session: Session, claims: ColumnElement[bool]) -> list[str]:
    """The claims among these that no registry search has left a record for: never
    searched, whatever status they hold. Behavior: openspec entity-resolution, "A claim
    never searched is told apart from one searched"."""
    return list(
        session.scalars(
            select(Claim.slug)
            .where(claims, ~exists().where(RegistrySearch.claim_id == Claim.id))
            .order_by(Claim.slug)
        )
    )
