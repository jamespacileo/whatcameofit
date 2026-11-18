"""The backfill commands: load registry trials, see what is due, and run a step."""

import json
import sqlite3
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from time import monotonic
from typing import Annotated, Any

import typer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from thenwhat.backfill.fingerprint_run import run_fingerprints
from thenwhat.backfill.leads import hit_rates
from thenwhat.backfill.link_evaluation import (
    TENTHS,
    Figures,
    evaluate,
    label_lead,
    label_leads,
    sample_leads,
    spot_check,
)
from thenwhat.backfill.link_funnel import funnel
from thenwhat.backfill.link_load import load_links
from thenwhat.backfill.link_read import LinkRead, ReadClient, held_outlets, retry_outlet
from thenwhat.backfill.link_readers import posts_of
from thenwhat.backfill.link_rekey import (
    refuse_stale_keys,
    refuse_while_steps_run,
    rekey_links,
    survey,
)
from thenwhat.backfill.link_report import IN_SCOPE_KINDS, screening_report
from thenwhat.backfill.link_topics import coverage
from thenwhat.backfill.link_triage import DecisionClient, LinkTriage, Standing
from thenwhat.backfill.mediacloud import MediaCloud
from thenwhat.backfill.registered import link_read_step, make_triage, registered_steps
from thenwhat.backfill.registry_arm_scope import arm_packet, propose_arm_scope
from thenwhat.backfill.registry_claim_plan import plan_registry_claims
from thenwhat.backfill.registry_load import (
    UnknownTrialSet,
    condition_of,
    load_trials,
)
from thenwhat.backfill.registry_scope_evidence import StoredTrial, cache_scope_evidence
from thenwhat.backfill.registry_scope_propose import ReviewPacket, propose_scope, review_packet
from thenwhat.backfill.registry_scope_review import (
    confirm_protocol_evidence,
    load_protocol_evidence,
    load_scope_reviews,
)
from thenwhat.backfill.topics import TOPICS
from thenwhat.backfill.trial_coverage import coverage_of
from thenwhat.backfill.trial_links import CLAIMS_A_READ, at_least, plan_of
from thenwhat.backfill.trial_papers import (
    PER_SECOND_WITH_KEY,
    PER_SECOND_WITHOUT_KEY,
    TrialPapers,
    estimate_for,
)
from thenwhat.backfill.trial_references import count_references
from thenwhat.backfill.trial_sets import (
    NAMES,
    NO_WIDER_RECORD,
    REGISTRY_CLAIMS_2026,
    ROLLING,
    count_sets,
    registry_claims_2026,
    require_wider_record,
    rule_of,
)
from thenwhat.claimsteps.inputs import CLAIM, notice_changes
from thenwhat.claimsteps.step import ClaimStep
from thenwhat.cli import session as cli_session
from thenwhat.cli.console import err, out
from thenwhat.cli.session import settings_or_exit
from thenwhat.clinical.mesh_xml import mesh_xml_vocabulary
from thenwhat.config import Settings, SourceAllowance
from thenwhat.db.models import RegistryTrial
from thenwhat.domain import Decider, LeadVerdict, OutletKind, WorkOutcome
from thenwhat.llm.errors import LlmError, LlmNotConfigured
from thenwhat.measure import spans
from thenwhat.measure.files import FileWriter
from thenwhat.measure.report import measured_cost_of_a_record
from thenwhat.sources.base import SourceError
from thenwhat.sources.clinicaltrials import NCT_ID, ClinicalTrials
from thenwhat.sources.pubmed import PubMed
from thenwhat.work.allowance import Allowances, AllowanceStatus
from thenwhat.work.errors import BackfillError, SourceStop
from thenwhat.work.ledger import count, waiting
from thenwhat.work.outcome import UndeclaredReason, declared
from thenwhat.work.runner import RunReport, measured_run, run_step
from thenwhat.work.spend import (
    PricesNotSet,
    ceiling_check,
    cost_of,
    left_this_month,
    prices_for,
    records_covered,
)
from thenwhat.work.steps import (
    NO_SOURCE,
    ModelSpend,
    Step,
    asks_a_source,
    by_name,
    find_step,
    model_spend_of,
)

backfill_app = typer.Typer(
    help="Work through many records: load trials, see what is due, run a step.",
    no_args_is_help=True,
)

KIND_WORDS = {
    OutletKind.GENERAL_NEWS: "general news",
    OutletKind.TRADE_PRESS: "health or clinical trade press",
    OutletKind.PRESS_RELEASE: "press release",
    OutletKind.UNKNOWN: "an outlet on no list",
}


@contextmanager
def open_session() -> Generator[Session]:
    """One transaction, committed when it ends. Looked up at call time so that tests
    can stand in their own session."""
    with cli_session.open_session() as session:
        yield session


@contextmanager
def refusals() -> Generator[None]:
    """A refused command is explained to the operator and exits with 1."""
    try:
        yield
    except (BackfillError, SourceError, SourceStop) as error:
        err.print(str(error), markup=False)
        raise typer.Exit(code=1) from None


def this_year() -> int:
    """The calendar year, in UTC: the year the rolling set of trials is chosen in. Read
    here, at the command, so the rules that take it read no clock."""
    return datetime.now(UTC).year


def steps_for(settings: Settings) -> list[Step]:
    steps = registered_steps(settings, year=this_year())
    by_name(steps)  # refuses two steps with one name before anything runs
    return steps


def make_allowances(settings: Settings) -> Allowances:
    return Allowances(open_session, settings.allowances())


def make_registry(session: Session, settings: Settings) -> ClinicalTrials:
    return ClinicalTrials(session, contact_email=settings.contact_email)


class NoClient:
    """What a step that asks no source is given: it only has to count, and counts nothing."""

    def __init__(self) -> None:
        self.requests_made = 0


def claim_steps_of(steps: list[Step]) -> list[ClaimStep]:
    return [step for step in steps if isinstance(step, ClaimStep)]


def under_an_allowance(step: Step) -> bool:
    """Whether the step's requests are counted against a source's allowance. A claim's
    preparation asks many sources, each at its own pace, under none."""
    return asks_a_source(step) and step.record_kind != CLAIM


def make_client(step: Step, settings: Settings, allowances: Allowances) -> Any:
    """What a step asks its source through. Refuses here, before any record is
    touched, when the source could not be asked at all."""
    if step.record_kind == CLAIM:
        from thenwhat.cli.claim_steps import claim_sources

        return claim_sources()
    if step.source == NO_SOURCE:
        return NoClient()
    if isinstance(step, LinkTriage):
        # Imported here: the model libraries are slow to load and most commands never
        # need them.
        from thenwhat.cli.resolve import make_backend

        return DecisionClient(make_backend)
    if isinstance(step, LinkRead):
        from thenwhat.cli import extract, resolve

        evidence = None
        if settings.lead_evidence_trial_store is not None:
            from thenwhat.backfill.article_evidence import ArticleEvidence, product_aliases_of

            evidence = ArticleEvidence(
                settings.lead_evidence_trial_store,
                PubMed(
                    contact_email=settings.contact_email,
                    tool=settings.pubmed_tool,
                    api_key=settings.pubmed_api_key,
                    allowances=allowances,
                )
                if settings.research_papers_enabled
                else None,
                extract.make_llm,
                resolve.make_backend,
                product_aliases_of(settings.lead_evidence_alias_file),
            )
            evidence.check_ready()
        return ReadClient(
            retriever=extract.make_retriever(),
            allowances=allowances,
            make_llm=extract.make_llm,
            make_checker=extract.make_checker,
            make_backend=resolve.make_backend,
            match_article=evidence,
        )
    if step.source == MediaCloud.name:
        client = MediaCloud(
            api_key=settings.mediacloud_api_key,
            contact_email=settings.contact_email,
            allowances=allowances,
            collection_ids=settings.mediacloud_collection_ids,
            source_ids=settings.mediacloud_source_ids,
        )
        client.check_ready()
        return client
    if step.source == PubMed.name:
        papers = PubMed(
            contact_email=settings.contact_email,
            tool=settings.pubmed_tool,
            api_key=settings.pubmed_api_key,
            allowances=allowances,
        )
        papers.check_ready()
        return papers
    raise BackfillError(f"No client is set up for the source '{step.source}'.")


def _hours(requests: int, allowance: SourceAllowance) -> str:
    hours = requests * allowance.interval_seconds / 3600
    if hours < 1:
        return f"about {max(round(hours * 60), 1)} minutes"
    return f"about {round(hours):,} hours"


def _allowance_line(source: str, allowance: SourceAllowance, status: AllowanceStatus) -> str:
    period = f"{allowance.period_hours:g} hours"
    line = (
        f"  {source}: {allowance.requests:,} requests in {period}, "
        f"{allowance.interval_seconds:g} seconds apart; "
        f"{status.used:,} used, {status.left:,} left"
    )
    if status.paused_until is not None:
        line += f"; paused until {status.paused_until:%Y-%m-%d %H:%M} UTC"
    return line


def _held_lines(session: Session, step: LinkRead, attempt_limit: int) -> list[str]:
    """How many due leads wait for an outlet the page reader has stopped, outlet by
    outlet. A run leaves them without a request until the time given."""
    held = held_outlets(session, step, attempt_limit, datetime.now(UTC))
    if not held:
        return []
    total = sum(one.leads for one in held)
    lines = [
        f"  held: {total:,} of the due leads are not asked, because the page reader "
        "said their outlet cannot be asked yet"
    ]
    lines += [
        f"    {one.outlet}: {one.leads:,} held until {one.until:%Y-%m-%d %H:%M} UTC" for one in held
    ]
    return lines


def _dollars(amount: Decimal) -> str:
    return f"${amount.quantize(Decimal('0.01'))}"


def _dollars4(amount: Decimal) -> str:
    return f"${amount.quantize(Decimal('0.0001'))}"


def _spend_line(
    session: Session, settings: Settings, spend: ModelSpend, due: int, step_name: str
) -> str:
    """What a model step's due records would cost beside what is left of the month's
    ceiling. The cost of a record is the measured one where a week or more of
    measurements exist for the step, and the step's own estimate otherwise. No cost is
    given while a price is not configured."""
    try:
        prices = prices_for(settings, spend.door)
    except PricesNotSet as missing:
        return f"  calls a model: no cost can be given, {missing}"
    now = datetime.now(UTC)
    measured = measured_cost_of_a_record(session, step_name, today=now.date())
    left = left_this_month(session, settings, now)
    if measured is not None:
        cost = measured.per_record * due
        basis = f"measured over {measured.days} days"
        covered = None if measured.per_record <= 0 else int(left // measured.per_record)
    else:
        cost = cost_of(spend, prices, due)
        basis = "estimated"
        covered = records_covered(spend, prices, left)
    line = (
        f"  calls a model: the due records need about {_dollars(cost)} ({basis}); "
        f"{_dollars(left)} of the month's {_dollars(settings.llm_monthly_budget_usd)} "
        "ceiling is left"
    )
    if covered is None or covered >= due:
        return f"{line}, which covers them all"
    return f"{line}, which covers {covered:,} of the {due:,} due records"


def _requests_for(step: Any, due: int) -> int:
    """The requests this many due records need: a step that asks for many records in
    one request says so itself; any other needs its fixed number a record."""
    if hasattr(step, "requests_for"):
        return step.requests_for(due)
    return due * step.requests_per_record


def _records_for(step: Any, requests: int) -> int:
    """The due records this many requests cover."""
    if hasattr(step, "records_for"):
        return step.records_for(requests)
    return requests // step.requests_per_record


@backfill_app.command("steps")
def steps_command() -> None:
    """List the steps a backfill can run."""
    with refusals():
        for step in steps_for(settings_or_exit()):
            batch = getattr(step, "batch_size", 0)
            asked = (
                f"requests: about {_requests_for(step, batch)} for each {batch} records"
                if hasattr(step, "requests_for")
                else f"requests per record: {step.requests_per_record}"
            )
            out.print(
                f"{step.name}  version {step.version}  records: {step.record_kind}  "
                f"source: {step.source}  {asked}",
                markup=False,
            )


def _waiting_lines(session: Session, step: Step) -> list[str]:
    """The step's records that wait, by class and reason: those put off, with when the
    first is due, and those that need a fix."""
    lines: list[str] = []
    for waits in waiting(session, step):
        try:
            words = declared(step, waits.reason).describe()
        except UndeclaredReason:
            # A reason the step no longer declares: its records still wait for it.
            words = "a reason the step no longer declares"
        if waits.outcome is WorkOutcome.LATER:
            first = f"{waits.first_due_at:%Y-%m-%d %H:%M} UTC" if waits.first_due_at else "now"
            lines.append(
                f"  put off: {waits.records:,} for '{waits.reason}' ({words}); "
                f"the first is due {first}"
            )
        else:
            lines.append(
                f"  need a fix: {waits.records:,} for '{waits.reason}' ({words}); make them "
                f"due with `thenwhat work requeue {step.name} --reason {waits.reason}`"
            )
    return lines


@backfill_app.command("plan")
def plan_command() -> None:
    """Show what each step has done and has left to do, and what the rest would take.

    Sends no request and changes nothing.
    """
    settings = settings_or_exit()
    with refusals():
        allowances = make_allowances(settings)
        steps = steps_for(settings)
        with open_session() as session, session.begin_nested() as unchanged:
            # Claims whose input changed are counted as due, as a run would find them,
            # and the ledger is left as it was.
            notice_changes(session, claim_steps_of(steps))
            for step in steps:
                changed_inputs = getattr(step, "changed_inputs", None)
                counts = count(
                    session,
                    step,
                    settings.backfill_attempt_limit,
                    changed_inputs=changed_inputs(session) if changed_inputs else None,
                )
                total = session.scalar(select(func.count()).select_from(step.model)) or 0
                out.print(f"{step.name} (version {step.version})", markup=False)
                out.print(
                    f"  in scope: {counts.in_scope:,} of {total:,} {step.record_kind} records"
                    f"  done: {counts.done:,}  nothing found: {counts.nothing_found:,}"
                    f"  failed: {counts.failed:,}  due: {counts.due:,}",
                    markup=False,
                )
                if under_an_allowance(step):
                    allowance = allowances.of(step.source)
                    status = allowances.status(session, step.source)
                    requests = _requests_for(step, counts.due)
                    batched = " in batches" if hasattr(step, "requests_for") else ""
                    out.print(
                        f"  the due records need {'about ' if batched else ''}{requests:,} "
                        f"requests{batched}, "
                        f"{_hours(requests, allowance)} at the source's rate",
                        markup=False,
                    )
                    out.print(_allowance_line(step.source, allowance, status), markup=False)
                    if requests > status.left:
                        covered = _records_for(step, status.left)
                        periods = -(-(requests - status.left) // allowance.requests)
                        out.print(
                            f"  the allowance left covers {covered:,} of the {counts.due:,} due "
                            f"records; the rest needs {periods:,} more "
                            f"{'period' if periods == 1 else 'periods'} of "
                            f"{allowance.period_hours:g} hours",
                            markup=False,
                        )
                elif step.record_kind == CLAIM:
                    out.print(
                        "  asks the registries, literature indexes and models a claim's"
                        " preparation needs, each at its own pace",
                        markup=False,
                    )
                else:
                    out.print("  asks no source: the due records need 0 requests", markup=False)
                if isinstance(step, LinkRead):
                    for line in _held_lines(session, step, settings.backfill_attempt_limit):
                        out.print(line, markup=False)
                spend = model_spend_of(step)
                if spend is not None:
                    out.print(
                        _spend_line(session, settings, spend, counts.due, step.name),
                        markup=False,
                    )
                for line in _waiting_lines(session, step):
                    out.print(line, markup=False)
                if counts.needs_attention:
                    out.print(
                        f"  {counts.needs_attention:,} failed "
                        f"{settings.backfill_attempt_limit} times and are skipped: "
                        "they need attention",
                        markup=False,
                    )
            unchanged.rollback()


def _merge(reports: list[RunReport]) -> RunReport:
    merged = RunReport(errors=[])
    for report in reports:
        merged.done += report.done
        merged.nothing_found += report.nothing_found
        merged.failed += report.failed
        merged.later += report.later
        merged.before_work += report.before_work
        merged.needs_fix += report.needs_fix
        merged.stopped = merged.stopped or report.stopped
        merged.errors = (merged.errors or []) + (report.errors or [])
    merged.remaining_due = min(report.remaining_due for report in reports)
    return merged


@backfill_app.command("run")
def run_command(
    step_name: Annotated[str, typer.Argument(help="Name of the step, from `backfill steps`.")],
    limit: Annotated[
        int | None, typer.Option(min=1, help="Process at most this many records.")
    ] = None,
    workers: Annotated[
        int, typer.Option(min=1, max=4, help="How many records to work on at once.")
    ] = 1,
) -> None:
    """Process the records that are due for a step.

    Stops when none is due, at the limit, or when the source's allowance is used up.
    It can be stopped at any point and started again: a finished record is never
    processed twice, and several runs at once never take the same record.
    """
    settings = settings_or_exit()
    with refusals():
        step = find_step(steps_for(settings), step_name)
        if getattr(step, "needs_limit", False) and limit is None:
            raise BackfillError(
                f"`{step.name}` publishes what it makes, so a run says how many records it "
                "may process. Run it again with --limit."
            )
        if step.record_kind == "link_lead":
            # A lead keyed under an earlier form would be compared with addresses in
            # the current one, and miss.
            with open_session() as session:
                refuse_stale_keys(session)
        if step.record_kind == CLAIM:
            # A claim whose input changed since its entry was made is due again.
            with open_session() as session:
                notice_changes(session, claim_steps_of(steps_for(settings)))
        check_ready = getattr(step, "check_ready", None)
        if check_ready is not None:
            with open_session() as session:
                check_ready(session)
        allowances = make_allowances(settings)
        if under_an_allowance(step):
            allowances.of(step.source)
        shares: list[int | None] = [None] * workers
        if limit is not None:
            workers = min(workers, limit)
            whole, extra = divmod(limit, workers)
            shares = [whole + (i < extra) for i in range(workers)]
        clients = [make_client(step, settings, allowances) for _ in range(workers)]

        def now() -> datetime:
            return datetime.now(UTC)

        # Claim steps can finish without a model. Their backends enforce the ceiling
        # at the point a paid call is actually needed.
        calls_a_model = model_spend_of(step) is not None
        before_call = ceiling_check(settings, now) if calls_a_model else None

        tried: set[int] = set()
        # One run for all the workers: its measurements and events name it.
        with measured_run(step.name, limit=limit, workers=workers) as run:

            def work(client: Any, share: int | None) -> RunReport:
                return run_step(
                    open_session,
                    step,
                    client,
                    now=now,
                    attempt_limit=settings.backfill_attempt_limit,
                    limit=share,
                    before_call=before_call,
                    tried=tried,
                    put_off_span=timedelta(days=settings.work_put_off_days),
                    run=run,
                )

            if workers == 1:
                report = work(clients[0], shares[0])
            else:
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    report = _merge(list(pool.map(work, clients, shares)))
        report.not_written = run.not_written
    out.print(
        f"{step.name}: {report.done:,} done, {report.nothing_found:,} found nothing, "
        f"{report.failed:,} failed"
        + (f", {report.later:,} put off" if report.later else "")
        + (f", {report.needs_fix:,} need a fix" if report.needs_fix else "")
        + f"; {report.remaining_due:,} still due.",
        markup=False,
    )
    for error in (report.errors or [])[:10]:
        out.print(f"  failed: {error}", markup=False)
    if report.stopped:
        out.print(f"Stopped: {report.stopped}", markup=False)
    _say_not_written(report)


def _say_not_written(report: RunReport) -> None:
    if report.not_written:
        out.print(
            f"{report.not_written:,} measurements of this run could not be written to"
            " MEASURE_DIR. The work is not affected; `thenwhat measure` counts them once"
            " writing works again.",
            markup=False,
        )


@backfill_app.command("load-trials")
def load_trials_command(
    condition: Annotated[
        str | None,
        typer.Option(
            help="Which trials to load, in the registry's own expression language. "
            "Use this or --trials, not both."
        ),
    ] = None,
    trials: Annotated[
        str | None,
        typer.Option(
            help="A named set of trials: phase-3 (the default) or active-phase-2-3, "
            "interventional trials of a drug or biological, the second those under way "
            "now; interventional, every interventional study; or "
            f"{REGISTRY_CLAIMS_2026}, the registry-claim cohort."
        ),
    ] = None,
    changes_only: Annotated[
        bool,
        typer.Option(
            "--changes-only",
            help="Ask only for trials the registry updated since the last completed load.",
        ),
    ] = False,
) -> None:
    """Load trials from ClinicalTrials.gov in bulk, a thousand per request.

    The trials are kept whether or not any claim refers to them. They are not evidence
    events and never reach the export. Loading again updates each trial in place.
    With --changes-only, only trials updated since the last completed load of the same
    set are asked for; with none completed, every trial is. A load that reaches the
    registry's allowance stops with what it stored, says so, and is not an error.
    """
    settings = settings_or_exit()
    if condition is not None and trials is not None:
        err.print("Give --condition or --trials, not both.")
        raise typer.Exit(code=1)
    if condition is None:
        try:
            condition = condition_of(trials or "phase-3")
        except UnknownTrialSet as unknown:
            err.print(str(unknown))
            raise typer.Exit(code=1) from None
    with refusals():
        steps = steps_for(settings)
        allowances = make_allowances(settings)
        with open_session() as lookups:
            registry = make_registry(lookups, settings)
            allowances.of(registry.name)
            report = load_trials(
                open_session,
                registry,
                steps,
                condition=condition,
                changes_only=changes_only,
                now=lambda: datetime.now(UTC),
            )
    since = f" updated since {report.changes_since}" if report.changes_since else ""
    out.print(
        f"Loaded {report.added + report.updated:,} trials{since} in {report.requests:,} "
        f"requests: {report.added:,} new, {report.updated:,} already stored.",
        markup=False,
    )
    if report.stopped:
        out.print(
            f"Stopped: {report.stopped} Run the same command again later to go on.",
            markup=False,
        )


@backfill_app.command("load-links")
def load_links_command(
    platform: Annotated[str, typer.Argument(help="Link source: hackernews, reddit or gdelt-gal.")],
    file: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=False,
            readable=True,
            help="A local bulk file of posts or article listings from the source.",
        ),
    ],
) -> None:
    """Load article addresses from a bulk file of posts or article listings.

    One link lead is kept per article address, with where and when it was shared. Who
    shared it, the post's text and its comments are never read. No request is sent to
    any platform or outlet, and nothing reaches the export. Loading a file again adds
    nothing, so a load that was stopped is simply run again.
    """
    settings = settings_or_exit()
    with refusals():
        steps = steps_for(settings)
        posts = posts_of(platform, file, communities=settings.chosen_subreddits())
        report = load_links(open_session, platform, posts, steps)
    out.print(
        f"Read {report.read:,} posts from {file.name}: {report.new_leads:,} new link leads, "
        f"{report.added_shares:,} more shares of leads already stored, "
        f"{report.already_stored:,} already stored.",
        markup=False,
    )
    for reason, number in sorted(report.skipped.items()):
        out.print(f"  skipped, {reason.value}: {number:,}", markup=False)


@backfill_app.command("rekey-links")
def rekey_links_command(
    apply: Annotated[
        bool,
        typer.Option("--apply", help="Do it. Without this, only say what would be done."),
    ] = False,
) -> None:
    """Bring stored link leads to the current form of the address key.

    Needed once after the address key changes; loading and the link steps are refused
    until it is done. Two leads that are one article under the current form become one
    lead with the shares of both, and the one that was scored or read is kept. Sends no
    request and calls no model, and makes no lead due again for a step that does. It
    can be stopped and run again. Stop every load and run first: it is refused while a
    step worked on a link lead in the last ten minutes.
    """
    settings = settings_or_exit()
    with refusals():
        steps = steps_for(settings)
        if not apply:
            with open_session() as session:
                report = survey(session)
            out.print(
                f"{report.checked:,} link leads are keyed under an earlier form: "
                f"{report.unchanged:,} keep their key, {report.rekeyed:,} would get a new "
                f"key, {report.merged:,} would be merged into another lead. Nothing was "
                "changed. Run it again with --apply.",
                markup=False,
            )
            return
        with open_session() as session:
            refuse_while_steps_run(session, datetime.now(UTC))
        report = rekey_links(open_session, steps)
    out.print(
        f"Brought {report.checked:,} link leads up to date: {report.unchanged:,} kept "
        f"their key, {report.rekeyed:,} got a new key, {report.merged:,} were merged into "
        f"another lead ({report.shares_moved:,} shares moved).",
        markup=False,
    )
    for one, other in sorted(set(report.claims_to_compare)):
        out.print(
            f"  claims {one} and {other} each came from a lead of one article: compare them.",
            markup=False,
        )
    if report.merged or report.rekeyed:
        out.print("Run `thenwhat backfill run link_screen` to screen them again.", markup=False)


@backfill_app.command("retry-outlet")
def retry_outlet_command(
    outlet: Annotated[str, typer.Argument(help="The outlet's domain, for example reuters.com.")],
) -> None:
    """Ask the page reader again for an outlet's leads that it refused with 401, or that
    were not asked because of those refusals. Its old refusals lapse after 30 days on
    their own; this is for an outlet known to serve the reader now."""
    settings = settings_or_exit()
    with refusals(), open_session() as session:
        step = find_step(steps_for(settings), LinkRead.name)
        if not isinstance(step, LinkRead):
            raise BackfillError("The step that reads link leads is not among the steps.")
        retried = retry_outlet(session, step, outlet)
    noun = "lead" if retried == 1 else "leads"
    out.print(
        f"{retried:,} {noun} of {outlet} are due to be read again."
        " Run `thenwhat backfill run link_read`.",
        markup=False,
    )


@backfill_app.command("leads")
def leads_command() -> None:
    """Show how many searched trials have a news article, in all and by kind of outlet."""
    settings = settings_or_exit()
    with refusals():
        step = find_step(steps_for(settings), "news_search")
        with open_session() as session:
            rates = hit_rates(session, step)
    if rates.processed == 0:
        out.print("No trial has been searched yet. Run `thenwhat backfill run news_search`.")
        return
    out.print(
        f"{rates.with_a_lead:,} of {rates.processed:,} searched trials "
        f"({rates.share(rates.with_a_lead)}%) have at least one article lead.",
        markup=False,
    )
    for kind in OutletKind:
        number = rates.by_kind[kind]
        out.print(
            f"  {number:,} ({rates.share(number)}%) have one from {KIND_WORDS[kind]}",
            markup=False,
        )


SET_WORDS = {
    "active-since-2025": "phase 2 or 3, under way, record updated on or after 2025-01-01",
    "completed-with-results-since-2025": (
        "completed on or after 2025-01-01 (actual date), results posted"
    ),
    REGISTRY_CLAIMS_2026: "phase 2 or 3, under way or actually completed in 2026",
    ROLLING: (
        "under way now in any phase, or completed, terminated, withdrawn or suspended "
        "with a completion date this year"
    ),
}


def _phase_words(phases: tuple[str, ...]) -> str:
    if not phases:
        return "no phase given"
    if phases == ("NA",):
        return "phase not applicable"
    words = [
        phase.replace("EARLY_PHASE", "early phase ").replace("PHASE", "phase ") for phase in phases
    ]
    # Phases 2 and 3 together read as "phase 2/3".
    if len(words) > 1 and all(word.startswith("phase ") for word in words):
        return "phase " + "/".join(word.removeprefix("phase ") for word in words)
    return " and ".join(words)


@backfill_app.command("trial-sets")
def trial_sets_command() -> None:
    """Count the named sets of stored trials, by phase, with the days they were loaded.

    active-since-2025: phase 2 or 3, recruiting or about to, enrolling by invitation, or
    active and no longer recruiting, with a record the registry updated on or after
    1 January 2025. completed-with-results-since-2025: completed, with an actual
    completion date on or after 1 January 2025 and results posted.
    active-or-ended-this-year, the trial target set: under way now in any phase, or
    listed as completed, terminated, withdrawn or suspended with a completion date in
    the current calendar year; it holds every trial of active-since-2025. A set says
    which trials are in it and nothing of how they turned out. Sends no request and
    changes nothing.
    """
    settings_or_exit()
    with refusals(), open_session() as session:
        report = count_sets(session, year=this_year())
    if report.stored == report.without_wider_record:
        err.print(NO_WIDER_RECORD)
        raise typer.Exit(code=1)
    for counted in report.sets:
        loaded = (
            f"loaded {counted.loaded_first}"
            if counted.loaded_first == counted.loaded_last
            else f"loaded {counted.loaded_first} to {counted.loaded_last}"
        )
        out.print(
            f"{counted.name} ({SET_WORDS[counted.name]}): {counted.total:,} "
            + ("trial" if counted.total == 1 else "trials")
            + (f", {loaded}" if counted.total else ""),
            markup=False,
        )
        for phases, number in sorted(counted.by_phase.items(), key=lambda item: item[0]):
            out.print(f"  {_phase_words(phases)}: {number:,}", markup=False)
    if report.without_wider_record:
        out.print(
            f"{report.without_wider_record:,} of {report.stored:,} stored trials were loaded "
            "before these fields were asked for and may need a refresh.",
            markup=False,
        )


@backfill_app.command("registry-claim-plan")
def registry_claim_plan_command(
    reviewed_scopes: Annotated[
        Path | None,
        typer.Option(
            exists=True,
            dir_okay=False,
            help="Apply evidence-backed scope reviews to the plan.",
        ),
    ] = None,
    mesh_descriptors: Annotated[
        Path | None,
        typer.Option(exists=True, dir_okay=False, help="Read an annual NLM MeSH descriptor file."),
    ] = None,
    arm_evidence: Annotated[
        Path | None,
        typer.Option(exists=True, dir_okay=False, help="Cached protocols cited by scope receipts."),
    ] = None,
) -> None:
    """Print the 2026 registry-claim plan as JSON. Reads stored records only."""
    settings_or_exit()
    with refusals():
        try:
            reviews = load_scope_reviews(reviewed_scopes) if reviewed_scopes is not None else None
            if arm_evidence is not None and reviewed_scopes is None:
                raise ValueError("--arm-evidence requires --reviewed-scopes.")
            evidence = load_protocol_evidence(arm_evidence) if arm_evidence is not None else None
        except (OSError, ValueError) as error:
            raise BackfillError(f"Could not read scope reviews: {error}") from error
        try:
            vocabulary = mesh_xml_vocabulary(mesh_descriptors) if mesh_descriptors else None
        except (OSError, ValueError, SyntaxError) as error:
            raise BackfillError(f"Could not read MeSH descriptors: {error}") from error
        with open_session() as session:
            require_wider_record(session)
            plan = plan_registry_claims(
                session, scope_reviews=reviews, vocabulary=vocabulary, arm_evidence=evidence
            )
    typer.echo(json.dumps({"set": REGISTRY_CLAIMS_2026, **asdict(plan)}, default=sorted))


def _scope_trial_ids(trials: list[str]) -> tuple[str, ...]:
    identifiers = tuple(dict.fromkeys(identifier.upper().strip() for identifier in trials))
    if not identifiers or not all(NCT_ID.fullmatch(identifier) for identifier in identifiers):
        raise BackfillError("Specify ClinicalTrials.gov trial identifiers in NCT format.")
    return identifiers


def _stored_scope_trials(
    session: Session,
    identifiers: tuple[str, ...],
) -> dict[str, StoredTrial]:
    records = {
        identifier: (record, updated)
        for identifier, record, updated in session.execute(
            select(
                RegistryTrial.external_id,
                RegistryTrial.raw_payload,
                RegistryTrial.last_update_posted,
            ).where(registry_claims_2026(), RegistryTrial.external_id.in_(identifiers))
        )
    }
    missing = [identifier for identifier in identifiers if identifier not in records]
    if missing:
        raise BackfillError(f"Trials absent from the eligible stored set: {', '.join(missing)}.")
    return {identifier: records[identifier] for identifier in identifiers}


@backfill_app.command("registry-scope-evidence")
def registry_scope_evidence_command(
    trials_file: Annotated[
        Path, typer.Argument(exists=True, dir_okay=False, help="One eligible NCT ID per line.")
    ],
    output: Annotated[
        Path, typer.Option("--output", dir_okay=False, help="Private protocol cache on disk.")
    ],
) -> None:
    """Fetch version-matched protocol evidence in bounded batches, or resume the cache."""
    settings = settings_or_exit()
    started = monotonic()
    with refusals(), open_session() as session:
        try:
            identifiers = _scope_trial_ids(trials_file.read_text(encoding="utf-8").split())
            records = _stored_scope_trials(session, identifiers)
            report = cache_scope_evidence(make_registry(session, settings), records, output)
        except (OSError, ValueError) as error:
            raise BackfillError(f"Could not cache registry scope evidence: {error}") from error
    typer.echo(
        json.dumps(
            {
                **asdict(report),
                "pending": len(report.pending_ids),
                "seconds": round(monotonic() - started, 3),
            }
        )
    )


@backfill_app.command("registry-scope-proposals")
def registry_scope_proposals_command(
    trials: Annotated[list[str], typer.Argument(help="Exact ClinicalTrials.gov trial IDs.")],
    run: Annotated[
        bool, typer.Option("--run", help="Request structured candidates using the configured cap.")
    ] = False,
    arm_evidence: Annotated[
        Path | None,
        typer.Option(
            exists=True,
            dir_okay=False,
            help="Read cached protocol records keyed by NCT ID for the arm-specific review.",
        ),
    ] = None,
    check_omissions: Annotated[
        bool, typer.Option(help="In arm-evidence runs, request a second check for omitted scope.")
    ] = False,
) -> None:
    """Print evidence packets for scope review or request candidates for specified trials."""
    settings = settings_or_exit()
    started = monotonic()
    budget = settings.registry_scope_monthly_budget_usd
    with refusals():
        if check_omissions and (arm_evidence is None or not run):
            raise BackfillError("--check-omissions requires --arm-evidence and --run.")
        if run and budget is None:
            raise BackfillError("Set REGISTRY_SCOPE_MONTHLY_BUDGET_USD before a live scope run.")
        identifiers = _scope_trial_ids(trials)
        with open_session() as session:
            records = _stored_scope_trials(session, identifiers)
            try:
                if arm_evidence is None:
                    packets = [review_packet(records[identifier][0]) for identifier in identifiers]
                else:
                    evidence = load_protocol_evidence(arm_evidence)
                    packets = []
                    for identifier in identifiers:
                        record = evidence[identifier]
                        stored, updated = records[identifier]
                        confirm_protocol_evidence(
                            identifier,
                            stored,
                            record,
                            stored_update=str(updated) if updated else None,
                        )
                        packets.append(arm_packet(record))
            except (KeyError, OSError, TypeError, ValueError) as error:
                raise BackfillError(f"Could not prepare a scope packet: {error}") from error
            proposals = []
            failures = {}
            stopped = None
            if run:
                from thenwhat.cli.extract import make_llm

                llm = make_llm(session, budget_cap=budget)
                for packet in packets:
                    try:
                        if isinstance(packet, ReviewPacket):
                            proposal = propose_scope(llm, packet)
                        else:
                            proposal = propose_arm_scope(
                                llm, packet, check_omissions=check_omissions
                            )
                        proposals.append(asdict(proposal))
                    except (SourceStop, LlmNotConfigured) as error:
                        stopped = str(error)
                        break
                    except (LlmError, ValueError) as error:
                        failures[packet.trial_id] = str(error)
    typer.echo(
        json.dumps(
            {
                "packets": [asdict(packet) for packet in packets],
                "proposals": proposals,
                "failures": failures,
                "stopped": stopped,
                "seconds": round(monotonic() - started, 3),
            },
            ensure_ascii=False,
        )
    )


@backfill_app.command("trial-references")
def trial_references_command(
    trial_set: Annotated[
        str | None,
        typer.Option("--set", help="A named set of stored trials. Every set when not given."),
    ] = None,
    domains: Annotated[
        int, typer.Option(min=0, help="How many of the most linked domains to list.")
    ] = 10,
) -> None:
    """Count what the stored registry records of a set themselves list: papers and links.

    A paper the sponsor listed as reporting the study's results is counted apart from
    one the registry linked from PubMed, which the registry says may or may not be about
    the study. Papers listed as background are not the trial's and are only counted.
    A link is counted by its domain and by whether that domain is a listed outlet. Reads
    the stored records only: sends no request and changes nothing.
    """
    settings_or_exit()
    with refusals(), open_session() as session:
        year = this_year()
        names = [trial_set] if trial_set else list(NAMES)
        for name in names:
            rule_of(name, year)
        require_wider_record(session)
        counts = [count_references(session, name, year) for name in names]
    for counted in counts:
        out.print(f"{counted.name}: {counted.trials:,} trials", markup=False)
        out.print(
            f"  list a paper as reporting results (sponsor): {counted.with_sponsor_paper:,} "
            f"trials, {counted.sponsor_papers:,} papers",
            markup=False,
        )
        out.print(
            f"  have a paper linked by the registry from PubMed: "
            f"{counted.with_registry_paper:,} trials, {counted.registry_papers:,} more papers",
            markup=False,
        )
        out.print(
            f"  either: {counted.with_either:,} trials; background papers only: "
            f"{counted.with_background_only:,}",
            markup=False,
        )
        out.print(
            f"  give a link: {counted.with_link:,} trials, {counted.links:,} links; on a "
            f"listed outlet: {counted.with_listed_link:,} trials, {counted.listed_links:,} links",
            markup=False,
        )
        for domain, number in counted.domains.most_common(domains):
            out.print(f"    {domain}: {number:,}", markup=False)


@backfill_app.command("trial-fingerprints")
def trial_fingerprints_command(
    store: Annotated[
        Path, typer.Argument(help="Bulk store SQLite snapshot.", exists=True, dir_okay=False)
    ],
    output: Annotated[Path, typer.Argument(help="New directory for results and measurements.")],
    word_list: Annotated[
        list[Path],
        typer.Option(
            "--word-list",
            help="Words and names to exclude, one per line. Repeatable.",
            exists=True,
            dir_okay=False,
        ),
    ],
    payloads: Annotated[
        Path | None,
        typer.Option(help="Local store payload objects, if any trial payload is held there."),
    ] = None,
    limit: Annotated[
        int | None, typer.Option(min=1, help="Size of the random sample. Omit for all trials.")
    ] = None,
    acronym_sample: Annotated[
        int, typer.Option(min=0, help="Extra distinct trials with acronyms in a limited run.")
    ] = 0,
    seed: Annotated[int, typer.Option(help="Random sample seed.")] = 83,
    max_other_titles: Annotated[
        int, typer.Option(min=0, help="Maximum other trial titles a fit acronym may appear in.")
    ] = 3,
) -> None:
    """Build trial fingerprints from a local read-only store snapshot."""
    with refusals():
        try:
            output.mkdir()
        except OSError as error:
            raise BackfillError(f"Could not create a new run directory: {error}") from error
        writer = "trial-fingerprints"
        spans.use(spans.Recorder(out=FileWriter(output, writer=writer), writer=writer))
        try:
            with spans.measured("trial_fingerprint.run"):
                summary = run_fingerprints(
                    store,
                    output,
                    word_list,
                    payloads=payloads,
                    limit=limit,
                    acronym_sample=acronym_sample,
                    seed=seed,
                    max_other_titles=max_other_titles,
                    progress=out.print,
                )
        except (OSError, sqlite3.Error, ValueError) as error:
            raise BackfillError(f"Trial fingerprint run failed: {error}") from error
        finally:
            spans.use(None)
        out.print(
            f"Wrote {summary['fingerprints']:,} trial fingerprints and a summary to {output}."
        )


@backfill_app.command("trial-coverage")
def trial_coverage_command() -> None:
    """Count what is held for the trial target set, by group, and what the paper index
    has still to be asked.

    The set is active-or-ended-this-year. For the trials under way, those completed this
    year and those terminated, withdrawn or suspended this year: how many there are, how
    many have results posted, a paper the registry record lists, a paper found in PubMed
    by the trial's number, a published claim that cites them, and a record the registry
    has not updated since before last year. Counts only: no trial is named, and a count
    says nothing of how any trial turned out. Then how many trials PubMed has not been
    asked about, the requests that needs and the off-peak nights, with no key and with
    one. Sends no request and changes nothing.
    """
    settings = settings_or_exit()
    with refusals():
        year = this_year()
        step = TrialPapers(trials_per_request=settings.pubmed_trials_per_request, year=year)
        allowance = make_allowances(settings).of(step.source)
        with open_session() as session:
            require_wider_record(session)
            coverage = coverage_of(session, year)
            due = count(session, step, settings.backfill_attempt_limit).due
        estimate = estimate_for(step, due, allowance)
    out.print(f"{ROLLING}, chosen in {year}", markup=False)
    for group in (*coverage.groups, coverage.total):
        out.print(f"{group.name}: {group.trials:,} trials", markup=False)
        out.print(f"  results posted: {group.with_results:,}", markup=False)
        out.print(f"  a paper the registry record lists: {group.with_listed_paper:,}", markup=False)
        out.print(f"  a paper found in PubMed by number: {group.with_pubmed_paper:,}", markup=False)
        out.print(f"  cited by a published claim: {group.cited_by_published_claim:,}", markup=False)
        out.print(
            f"  record not updated since before {year - 1}: "
            f"{group.not_updated_since_before_last_year:,}",
            markup=False,
        )
    out.print(
        f"PubMed has not been asked about {estimate.trials:,} trials in scope: about "
        f"{estimate.requests:,} requests, {step.batch_size} trials to a search",
        markup=False,
    )
    out.print(
        f"  without a key (NCBI allows {PER_SECOND_WITHOUT_KEY} a second; requests here are "
        f"{allowance.interval_seconds:g} s apart): about {_minutes(estimate.minutes)}, "
        f"{estimate.nights:,} off-peak "
        f"{'night' if estimate.nights == 1 else 'nights'} under the allowance of "
        f"{allowance.requests:,} in {allowance.period_hours:g} hours",
        markup=False,
    )
    out.print(
        f"  with a key (NCBI allows {PER_SECOND_WITH_KEY} a second): about "
        f"{_minutes(estimate.minutes_with_key)} at that rate. To use one, set "
        "PUBMED_API_KEY and a shorter interval for pubmed in SOURCE_ALLOWANCES; the "
        "allowance, not the rate, is what limits a night",
        markup=False,
    )
    out.print(
        "  the step runs off-peak only (weekends, or 21:00 to 05:00 US Eastern): "
        "`thenwhat backfill run pubmed_papers`",
        markup=False,
    )


def _minutes(minutes: float) -> str:
    if minutes < 1:
        return "under a minute"
    whole = round(minutes)
    return f"{whole:,} minute" + ("" if whole == 1 else "s")


def _cost_of_a_read(session: Session, settings: Settings, step: LinkRead) -> tuple[Decimal, str]:
    """What one read costs with every later step counted: the measured cost where a
    week of measurements exists, and the step's own estimate otherwise."""
    measured = measured_cost_of_a_record(session, step.name, today=datetime.now(UTC).date())
    if measured is not None:
        return measured.per_record, f"measured over {measured.days} days"
    try:
        prices = prices_for(settings, step.model_spend.door)
    except PricesNotSet as missing:
        raise BackfillError(f"No cost can be given for a read: {missing}.") from None
    return cost_of(step.model_spend, prices, 1), "estimated"


@backfill_app.command("read-set")
def read_set_command(
    trial_set: Annotated[
        str, typer.Argument(help="A named set of stored trials, from `backfill trial-sets`.")
    ],
    limit: Annotated[
        int | None,
        typer.Option(min=1, help="Read at most this many leads. Without it, only the plan."),
    ] = None,
    strength: Annotated[
        str,
        typer.Option(
            help="The weakest link read for: exact, strong (the default), named or "
            "candidate. A held lead is read only on an exact or strong link."
        ),
    ] = "strong",
) -> None:
    """Plan, and with --limit read, the leads linked to trials of a named set.

    Prints how many leads in scope are linked to the set, where triage left them, how
    many are read, how many would be read, what that is expected to cost and send to
    audit, and what the reads for a set have used of their monthly share. Leads linked
    to the set's phase 3 trials are read first. A lead triage rejected is never read. It
    reads nothing when the expected cost passes what is left of the share. A read here is
    an ordinary read: it drafts or joins a claim, which is prepared and held awaiting
    audit as any backfill batch is.
    """
    settings = settings_or_exit()
    now = datetime.now(UTC)
    with refusals():
        strengths = at_least(strength)
        step = link_read_step(
            settings,
            make_triage(settings).version,
            trial_set=trial_set,
            only_trial_set=True,
            least_strength=strength,
        )
        share = settings.trial_route_monthly_usd
        with open_session() as session:
            plan = plan_of(
                session,
                trial_set,
                strengths,
                pass_above=settings.lead_pass_above,
                reject_below=settings.lead_reject_below,
                read_step=step.name,
                now=now,
            )
            due = count(session, step, settings.backfill_attempt_limit).due
            one, basis = _cost_of_a_read(session, settings, step)
        spent = one * plan.read_this_month
        left = max(share - spent, Decimal(0))
        to_read = due if limit is None else min(due, limit)
        cost = one * to_read
        out.print(
            f"{trial_set}: {plan.leads:,} leads in scope are linked "
            f"({' or '.join(strengths)}) to {plan.trials:,} trials of the set",
            markup=False,
        )
        out.print(
            f"  triage: {plan.passed:,} passed, {plan.held:,} held, {plan.rejected:,} "
            f"rejected, {plan.not_scored:,} not scored; {plan.already_read:,} already read",
            markup=False,
        )
        out.print(
            f"  would be read: {due:,}, those linked to phase 3 trials first"
            + (f"; this run reads at most {to_read:,}" if limit is not None else ""),
            markup=False,
        )
        out.print(
            f"  expected cost: {_dollars(cost)} at {_dollars4(one)} a read ({basis}); "
            f"about {int(to_read * CLAIMS_A_READ):,} claims to audit",
            markup=False,
        )
        out.print(
            f"  reads for this set this month: {plan.read_this_month:,}, about "
            f"{_dollars(spent)} of the route's {_dollars(share)} share; {_dollars(left)} left",
            markup=False,
        )
        if cost > left:
            raise BackfillError(
                f"Nothing was read: the reads are expected to cost {_dollars(cost)} and "
                f"{_dollars(left)} is left of the route's share this month "
                "(TRIAL_ROUTE_MONTHLY_USD). Give a smaller --limit."
            )
        if limit is None:
            out.print("Nothing was read. Give --limit to read.", markup=False)
            return
        with open_session() as session:
            refuse_stale_keys(session)
            step.check_ready(session)
        allowances = make_allowances(settings)
        allowances.of(step.source)
        client = make_client(step, settings, allowances)
        report = run_step(
            open_session,
            step,
            client,
            now=lambda: datetime.now(UTC),
            attempt_limit=settings.backfill_attempt_limit,
            limit=to_read,
            before_call=ceiling_check(settings, lambda: datetime.now(UTC)),
        )
    out.print(
        f"{step.name} for {trial_set}: {report.done:,} done, {report.nothing_found:,} "
        f"found nothing, {report.failed:,} failed"
        + f"; {report.remaining_due:,} still due. Run `thenwhat prepare --pending` next.",
        markup=False,
    )
    if report.stopped:
        out.print(f"Stopped: {report.stopped}", markup=False)
    _say_not_written(report)


@backfill_app.command("links")
def links_command() -> None:
    """Show what the loaded link leads are, by where they were shared: how many are on
    a listed outlet, already tracked, and linked to stored claims and trials.

    Sends no request and changes nothing.
    """
    settings_or_exit()
    with refusals(), open_session() as session:
        report = screening_report(session)
    if report.screened == 0:
        out.print(
            "No link lead has been screened yet. Load a file with "
            "`thenwhat backfill load-links`, then run `thenwhat backfill run link_screen`."
        )
        return
    for place in report.places:
        where = (
            place.platform
            if place.community == place.platform
            else f"{place.platform} / {place.community}"
        )
        out.print(
            f"{where}: {place.loaded:,} link leads loaded, {place.screened:,} screened",
            markup=False,
        )
        kinds = ", ".join(f"{place.in_scope[kind]:,} {KIND_WORDS[kind]}" for kind in IN_SCOPE_KINDS)
        out.print(
            f"  in scope: {place.in_scope_total:,} ({place.share(place.in_scope_total)}%): {kinds}",
            markup=False,
        )
        out.print(
            f"  on an unlisted outlet: {place.unlisted:,} ({place.share(place.unlisted)}%)"
            f"  already tracked: {place.already_tracked:,}",
            markup=False,
        )
        out.print(
            f"  linked to a claim: {place.linked_to_claim:,}"
            f"  linked to a registry trial: {place.linked_to_trial:,}",
            markup=False,
        )
    if report.unlisted_domains:
        out.print("The unlisted domains with the most link leads:", markup=False)
        for domain, number in report.unlisted_domains:
            out.print(f"  {domain}  {number:,}", markup=False)


def _triage_version(settings: Settings) -> int:
    return find_step(steps_for(settings), LinkTriage.name).version


@backfill_app.command("sample-leads")
def sample_leads_command(
    size: Annotated[int, typer.Option(min=10, help="How many leads to draw, in tens.")] = 200,
    seed: Annotated[str, typer.Option(help="The same seed draws the same sample.")] = "1",
    tenth: Annotated[
        float | None,
        typer.Option(
            min=0.0,
            max=0.9,
            help="Draw every lead from the one tenth of the score range that starts here, "
            "for example 0.0. Use it where one tenth holds most of the leads.",
        ),
    ] = None,
) -> None:
    """Draw scored link leads to label, in equal numbers from each tenth of the score
    range and spread across platforms.

    Leads you have already labelled are left out. The scores are not shown, so that a
    label does not lean on them. Label each lead with `thenwhat backfill label-lead`.
    """
    settings = settings_or_exit()
    with refusals(), open_session() as session:
        sample = sample_leads(
            session,
            size=size,
            seed=seed,
            version=_triage_version(settings),
            only_tenth=None if tenth is None else round(tenth * TENTHS),
        )
    if not sample.leads:
        out.print(
            "No scored link lead is waiting for a label. Run `thenwhat backfill run "
            "link_triage` first."
        )
        return
    for lead in sample.leads:
        out.print(
            f"{lead.lead_id}\t{lead.first_shared:%Y-%m-%d}\t{lead.outlet}\t{lead.title}\t{lead.url}",
            markup=False,
            soft_wrap=True,
        )
    where = (
        f"{sample.per_tenth} from each tenth of the score range"
        if tenth is None
        else f"all from the tenth of the score range that starts at {tenth:.1f}"
    )
    out.print(f"{len(sample.leads):,} leads, {where}.")
    for short, found in sorted(sample.short.items()):
        out.print(
            f"  the tenth from {short / TENTHS:.1f} is short: it holds only {found} "
            "unlabelled leads",
            markup=False,
        )


@backfill_app.command("label-lead")
def label_lead_command(
    lead_id: Annotated[int, typer.Argument(help="The lead's number, from `sample-leads`.")],
    label: Annotated[
        str,
        typer.Argument(
            help="What the headline is: "
            + ", ".join(verdict.value for verdict in LeadVerdict)
            + "."
        ),
    ],
    as_assistant: Annotated[
        bool,
        typer.Option(
            "--as-assistant",
            help="Record the label as an assistant's. It is never counted as a person's.",
        ),
    ] = False,
) -> None:
    """Record what a link lead's headline is: the answer triage is measured against.

    The label belongs to the lead, so it holds for every later version of triage.
    """
    settings_or_exit()
    by = Decider.ASSISTANT if as_assistant else Decider.HUMAN
    with refusals(), open_session() as session:
        label_lead(session, lead_id, label, by=by, now=datetime.now(UTC))
    whose = "an assistant's label" if as_assistant else "your label"
    out.print(f"Lead {lead_id} is labelled {label}, as {whose}.", markup=False)


def _percent(share: float | None) -> str:
    return "  n/a" if share is None else f"{round(100 * share):>4}%"


def _figures_lines(figures: Figures) -> list[str]:
    lines = ["  pass at or above   precision   recall   leads passed"]
    lines += [
        f"  {row.threshold:>16.1f}   {_percent(row.precision):>9}   {_percent(row.recall):>6}"
        f"   {row.passed:>12,}"
        for row in figures.rows
    ]
    by_tenth = "  ".join(
        f"{tenth / TENTHS:.1f}: {number}" for tenth, number in enumerate(figures.labels_by_tenth)
    )
    lines.append(f"  labels in each tenth, by its lower edge: {by_tenth}")
    if figures.unlabelled_tenths:
        edges = ", ".join(f"{tenth / TENTHS:.1f}" for tenth in figures.unlabelled_tenths)
        lines.append(
            f"  no label yet in the tenths from {edges}: they hold scored leads and are "
            "left out of precision and recall"
        )
    return lines


@backfill_app.command("evaluate-leads")
def evaluate_leads_command() -> None:
    """Show how well triage separates leads that report a treatment from those that do
    not, on the leads you have labelled.

    Precision is the share of leads at or above a threshold that report a treatment;
    recall is the share of all such leads that are at or above it. Each tenth of the
    score range counts by how many scored leads it holds. Sends no request.
    """
    settings = settings_or_exit()
    with refusals(), open_session() as session:
        version = _triage_version(settings)
        evaluation = evaluate(session, version=version)
    if evaluation.overall.labels == 0:
        out.print(
            "No link lead has a label yet at this version of triage. Draw leads with "
            "`thenwhat backfill sample-leads` and label them with `thenwhat backfill "
            "label-lead` or `label-leads`."
        )
        return
    out.print(
        f"Triage version {version}: {evaluation.overall.labels:,} leads carry a label that "
        f"counts: {evaluation.by_person:,} yours, {evaluation.by_assistant:,} an assistant's.",
        markup=False,
    )
    if evaluation.by_assistant:
        checked = (
            f"You have labelled {evaluation.checked:,} of the leads an assistant labelled "
            f"and agree on {evaluation.agreed:,}."
            if evaluation.checked
            else "You have checked none of the assistant's labels yet."
        )
        out.print(
            f"{checked} See what to check with `thenwhat backfill spot-check-leads`.",
            markup=False,
        )
    for line in _figures_lines(evaluation.overall):
        out.print(line, markup=False)
    for platform, figures in evaluation.by_platform.items():
        if figures.labels:
            out.print(f"{platform}: {figures.labels:,} labels", markup=False)
            for line in _figures_lines(figures):
                out.print(line, markup=False)
    if evaluation.disagreements:
        out.print("Where the label and the score disagree most:", markup=False)
        for case in evaluation.disagreements:
            out.print(
                f"  {case.lead_id}  score {case.score:.2f}  labelled {case.label.value}  "
                f"{case.title}",
                markup=False,
                soft_wrap=True,
            )


@backfill_app.command("label-leads")
def label_leads_command(
    file: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=False,
            readable=True,
            help="A file with a lead's number and a label on each line.",
        ),
    ],
    as_assistant: Annotated[
        bool,
        typer.Option(
            "--as-assistant",
            help="Record the labels as an assistant's. They are never stored as a person's.",
        ),
    ] = False,
) -> None:
    """Record the labels in a file: a lead's number and a label on each line, separated
    by a tab, a comma or spaces.

    All of them or none: a line that cannot be used fails the whole file and is named.
    Blank lines and lines that start with # are passed over.
    """
    settings_or_exit()
    by = Decider.ASSISTANT if as_assistant else Decider.HUMAN
    with refusals(), open_session() as session:
        number = label_leads(session, file.read_text().splitlines(), by=by, now=datetime.now(UTC))
    whose = "an assistant's" if as_assistant else "yours"
    out.print(f"Recorded {number:,} labels from {file.name}, as {whose}.", markup=False)


@backfill_app.command("spot-check-leads")
def spot_check_leads_command(
    seed: Annotated[str, typer.Option(help="The same seed draws the same random leads.")] = "1",
) -> None:
    """List the leads that only an assistant has labelled and that you should look at:
    where its label and the score disagree most, and a random draw of the rest.

    The assistant's label is shown and the score is not. Label a lead yourself with
    `thenwhat backfill label-lead` and your label counts in place of the assistant's.
    """
    settings = settings_or_exit()
    with refusals(), open_session() as session:
        found = spot_check(session, version=_triage_version(settings), seed=seed)
    if not found.disagreements and not found.random:
        out.print("No lead has only an assistant's label: there is nothing to check.")
        return
    for heading, leads in (
        ("Where the assistant's label and the score disagree most:", found.disagreements),
        ("A random draw of the other leads an assistant labelled:", found.random),
    ):
        if not leads:
            continue
        out.print(heading, markup=False)
        for lead in leads:
            out.print(
                f"  {lead.lead_id}\t{lead.assistants_label.value}\t{lead.outlet}\t{lead.title}"
                f"\t{lead.url}",
                markup=False,
                soft_wrap=True,
            )


@backfill_app.command("topics")
def topics_command(
    topic: Annotated[
        str | None, typer.Argument(help="A topic's name. Leave out for every topic.")
    ] = None,
) -> None:
    """Show how far each of the operator's topics is covered: where the link leads that
    name it stand, and what each claim for it holds.

    A topic is a name and its words, kept in `backfill/topics.py`. A lead whose title
    names one is read first, and is read when triage held it. Sends no request and
    changes nothing.
    """
    settings = settings_or_exit()
    lines: list[str] = []
    with refusals(), open_session() as session:
        for name in [topic] if topic else list(TOPICS):
            found = coverage(session, name, reject_below=settings.lead_reject_below)
            lines.append(f"{found.topic}: {found.named:,} link leads name it")
            lines += [f"  {label}: {count:,}" for label, count in found.standing.items() if count]
            lines += [
                f"  read, {outcome}: {count:,}" for outcome, count in sorted(found.read.items())
            ]
            lines.append(f"  claims: {len(found.claims)}")
            for claim in found.claims:
                where = "published" if claim.published else claim.review_state
                lines.append(
                    f"    {claim.slug} ({where}, {claim.status}): {claim.articles} article(s), "
                    f"{claim.trials} trial(s), {claim.papers} paper(s), {claim.cards} card(s)"
                )
    for line in lines:
        out.print(line, markup=False)


@backfill_app.command("funnel")
def funnel_command() -> None:
    """Show where the link leads stand, from loading to a claim, and what the model
    calls for them have cost.

    Sends no request and changes nothing.
    """
    settings = settings_or_exit()
    with refusals(), open_session() as session:
        found = funnel(
            session, pass_above=settings.lead_pass_above, reject_below=settings.lead_reject_below
        )
    standing = found.standing
    lines = [
        f"loaded: {found.loaded:,}",
        f"in scope after screening: {found.in_scope:,}",
        f"scored by triage: {found.scored:,}",
    ]
    if standing[Standing.UNDECIDED]:
        lines.append(
            f"  undecided: {standing[Standing.UNDECIDED]:,} (set LEAD_PASS_ABOVE and "
            "LEAD_REJECT_BELOW to pass any)"
        )
    else:
        lines.append(
            f"  passed: {standing[Standing.PASSED]:,}  held: {standing[Standing.HELD]:,}"
            f"  rejected: {standing[Standing.REJECTED]:,}"
        )
    lines += [
        f"read by the model: {found.read:,}",
        f"  added to a claim that existed: {found.added_to_claim:,}",
        f"  new claim, approved by rule: {found.new_approved_by_rule:,}",
        f"  new claim, rejected by rule: {found.new_rejected_by_rule:,}",
        f"  new claim, awaiting `thenwhat prepare --pending`: {found.new_awaiting_preparation:,}",
    ]
    if found.new_otherwise:
        lines.append(f"  new claim, decided otherwise: {found.new_otherwise:,}")
    lines += [
        f"  needs a vertical, no claim made: {found.needs_vertical:,}",
        f"  claim identity unresolved, no claim joined or made: {found.identity_unresolved:,}",
        f"  not about one treatment for one condition, no claim made: {found.not_one_treatment:,}",
        f"  on a topic, business news about a treatment, no claim made: {found.business_news:,}",
        f"held, the claim has enough articles: {found.enough_articles:,}",
        f"could not be read: {sum(found.cannot_be_read.values()):,}",
    ]
    lines += [f"  {reason}: {number:,}" for reason, number in found.cannot_be_read.items()]
    if found.put_off:
        lines.append(f"put off, to be asked for again: {sum(found.put_off.values()):,}")
        lines += [f"  {reason}: {number:,}" for reason, number in found.put_off.items()]
    if found.undated_outlets:
        lines.append("outlets whose pages gave no publication date:")
        lines += [f"  {outlet}  {number:,}" for outlet, number in found.undated_outlets]
    lines += [
        f"model cost recorded for triage: {_dollars(found.triage_cost_usd)}",
        f"model cost recorded for reading: {_dollars(found.reading_cost_usd)} "
        "(the reads, treatment-kind, claim-identity and vertical decisions; statement checks are "
        "recorded with all statement checks)",
    ]
    for line in lines:
        out.print(line, markup=False)
