"""Running the claim steps from a command: the sources they ask, as configured, and a run
of named steps for named claims whatever their ledger says."""

from collections.abc import Generator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from thenwhat.claimsteps.run import StepRun, claim_steps, make_due, named_steps, run_claim_steps
from thenwhat.claimsteps.step import ClaimSources, ClaimStep, named
from thenwhat.cli.console import out
from thenwhat.cli.session import settings_or_exit
from thenwhat.db.models import Claim
from thenwhat.domain import WorkOutcome
from thenwhat.work.ledger import find_entry
from thenwhat.work.outcome import UndeclaredReason, declared


@contextmanager
def open_session() -> Generator[Session]:
    """One transaction, committed when it ends. Looked up at call time, so that tests
    can stand in their own session. What a step found stays readable once its
    transaction has ended, for the command to say."""
    from thenwhat.cli import entry

    with entry.open_session() as session:
        session.expire_on_commit = False
        yield session


def claim_sources() -> ClaimSources:
    """The sources the claim steps ask, as configured. Each is made through the command
    module that owns it, looked up when it is made."""
    from thenwhat.cli import events, extract, resolve, terms

    settings = settings_or_exit()
    reader = bool((settings.firecrawl_api_url or "").strip()) and bool(
        (settings.firecrawl_api_key or "").strip()
    )
    return ClaimSources(
        make_backend=lambda session: resolve.make_backend(session),
        make_substances=lambda session: resolve.make_substances(session),
        make_brands=lambda session: resolve.make_brands(session),
        make_registries=lambda session: resolve.make_registries(session),
        make_research=lambda session: resolve.make_research(session),
        make_evidence=lambda session: events.make_evidence_sources(session),
        make_mesh=lambda session: events.make_mesh(session),
        make_llm=lambda session: extract.make_llm(session),
        make_checker=lambda session: extract.make_checker(session),
        make_vocabulary=lambda session: terms.make_vocabulary(session),
        make_genes=lambda session: terms.make_genes(session),
        make_drugs=lambda session: terms.make_drugs(session),
        # Not configured, no article is read, and no page is fetched any other way.
        retriever=extract.make_retriever() if reader else None,
        open_session=open_session,
    )


def run_steps(steps: Sequence[ClaimStep], *, workers: int = 1) -> list[StepRun]:
    """Run each step over its due claims, as configured."""
    settings = settings_or_exit()

    def now() -> datetime:
        return datetime.now(UTC)

    return run_claim_steps(
        open_session,
        steps,
        claim_sources,
        attempt_limit=settings.backfill_attempt_limit,
        put_off_span=timedelta(days=settings.work_put_off_days),
        now=now,
        workers=workers,
    )


def run_for_claims(
    claim_ids: Sequence[int],
    names: Sequence[str],
    *,
    alone: bool = False,
    rescore: bool = False,
    redo_rule: bool = False,
    rescore_pending: bool = False,
) -> list[ClaimStep]:
    """Run the named steps, in order, for these claims, whatever each claim's ledger
    holds: the operator asked for them. A step whose earlier step has not finished for a
    claim waits for it, unless it is run `alone`. Returns the steps as run."""
    steps = named_steps(
        claim_steps(
            settings_or_exit(),
            claims=named(list(claim_ids)),
            rescore=rescore,
            redo_rule=redo_rule,
            rescore_pending=rescore_pending,
        ),
        names,
    )
    if alone:
        for step in steps:
            step.after = ()
    with open_session() as session:
        make_due(session, steps, claim_ids)
    for run in run_steps(steps):
        if run.report.stopped:
            out.print(f"{run.step.name} stopped: {run.report.stopped}", markup=False)
    return steps


def outcome_line(session: Session, step: ClaimStep, claim_id: int, slug: str) -> str | None:
    """What became of the step for the claim, in one line: None when it finished."""
    claim = session.get(Claim, claim_id)
    entry = find_entry(session, step, claim) if claim is not None else None
    if entry is None or entry.stale:
        return f"{slug}: {step.name} did not run: an earlier step has not finished."
    if entry.outcome is WorkOutcome.DONE:
        return None
    if entry.outcome is WorkOutcome.FAILED:
        return f"{slug}: {step.name} failed: {entry.error}"
    try:
        said = declared(step, entry.reason or "").say(entry.reason_values)
    except UndeclaredReason:
        said = entry.reason or ""
    if entry.outcome is WorkOutcome.NOTHING_FOUND:
        return f"{slug}: {step.name} found nothing: {said}."
    if entry.outcome is WorkOutcome.LATER:
        until = f"{entry.not_before:%Y-%m-%d %H:%M} UTC" if entry.not_before else "later"
        return f"{slug}: {step.name} put off until {until}: {said}."
    return f"{slug}: {step.name} needs a fix: {said}."


def unfinished(session: Session, steps: Sequence[ClaimStep], claim_id: int) -> bool:
    """Whether any of the steps left the claim failed, put off or needing a fix, or did
    not run for it."""
    claim = session.get(Claim, claim_id)
    for step in steps:
        entry = find_entry(session, step, claim) if claim is not None else None
        if (
            entry is None
            or entry.stale
            or entry.outcome
            not in (
                WorkOutcome.DONE,
                WorkOutcome.NOTHING_FOUND,
            )
        ):
            return True
    return False
