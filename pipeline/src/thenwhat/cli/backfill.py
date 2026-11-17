"""The backfill commands: load registry trials, see what is due, and run a step."""

from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Any

import typer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from thenwhat.backfill.allowance import Allowances, AllowanceStatus
from thenwhat.backfill.errors import BackfillError, SourceStop
from thenwhat.backfill.leads import hit_rates
from thenwhat.backfill.ledger import count
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
from thenwhat.backfill.registered import registered_steps
from thenwhat.backfill.registry_load import (
    TrialList,
    UnknownTrialSet,
    condition_of,
    load_trials,
)
from thenwhat.backfill.runner import RunReport, run_step
from thenwhat.backfill.spend import (
    PricesNotSet,
    ceiling_check,
    cost_of,
    left_this_month,
    prices_for,
    records_covered,
)
from thenwhat.backfill.steps import (
    NO_SOURCE,
    ModelSpend,
    Step,
    asks_a_source,
    by_name,
    find_step,
    model_spend_of,
)
from thenwhat.backfill.topics import TOPICS
from thenwhat.backfill.trial_sets import count_sets
from thenwhat.cli import session as cli_session
from thenwhat.cli.console import err, out
from thenwhat.cli.session import settings_or_exit
from thenwhat.config import Settings, SourceAllowance
from thenwhat.domain import Decider, LeadVerdict, OutletKind
from thenwhat.measure.report import measured_cost_of_a_record
from thenwhat.sources.base import SourceError
from thenwhat.sources.clinicaltrials import ClinicalTrials

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


def steps_for(settings: Settings) -> list[Step]:
    steps = registered_steps(settings)
    by_name(steps)  # refuses two steps with one name before anything runs
    return steps


def make_allowances(settings: Settings) -> Allowances:
    return Allowances(open_session, settings.allowances())


def make_registry(session: Session, settings: Settings) -> TrialList:
    return ClinicalTrials(session, contact_email=settings.contact_email)


class NoClient:
    """What a step that asks no source is given: it only has to count, and counts nothing."""

    def __init__(self) -> None:
        self.requests_made = 0


def make_client(step: Step, settings: Settings, allowances: Allowances) -> Any:
    """What a step asks its source through. Refuses here, before any record is
    touched, when the source could not be asked at all."""
    if step.source == NO_SOURCE:
        return NoClient()
    if isinstance(step, LinkTriage):
        # Imported here: the model libraries are slow to load and most commands never
        # need them.
        from thenwhat.cli.resolve import make_backend

        return DecisionClient(make_backend)
    if isinstance(step, LinkRead):
        from thenwhat.cli import extract, resolve

        return ReadClient(
            retriever=extract.make_retriever(),
            allowances=allowances,
            make_llm=extract.make_llm,
            make_checker=extract.make_checker,
            make_backend=resolve.make_backend,
            make_research=resolve.make_research,
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


@backfill_app.command("steps")
def steps_command() -> None:
    """List the steps a backfill can run."""
    with refusals():
        for step in steps_for(settings_or_exit()):
            out.print(
                f"{step.name}  version {step.version}  records: {step.record_kind}  "
                f"source: {step.source}  requests per record: {step.requests_per_record}",
                markup=False,
            )


@backfill_app.command("plan")
def plan_command() -> None:
    """Show what each step has done and has left to do, and what the rest would take.

    Sends no request and changes nothing.
    """
    settings = settings_or_exit()
    with refusals():
        allowances = make_allowances(settings)
        with open_session() as session:
            for step in steps_for(settings):
                counts = count(session, step, settings.backfill_attempt_limit)
                total = session.scalar(select(func.count()).select_from(step.model)) or 0
                out.print(f"{step.name} (version {step.version})", markup=False)
                out.print(
                    f"  in scope: {counts.in_scope:,} of {total:,} {step.record_kind} records"
                    f"  done: {counts.done:,}  nothing found: {counts.nothing_found:,}"
                    f"  failed: {counts.failed:,}  due: {counts.due:,}",
                    markup=False,
                )
                if asks_a_source(step):
                    allowance = allowances.of(step.source)
                    status = allowances.status(session, step.source)
                    requests = counts.due * step.requests_per_record
                    out.print(
                        f"  the due records need {requests:,} requests, "
                        f"{_hours(requests, allowance)} at the source's rate",
                        markup=False,
                    )
                    out.print(_allowance_line(step.source, allowance, status), markup=False)
                    if requests > status.left:
                        covered = status.left // step.requests_per_record
                        periods = -(-(requests - status.left) // allowance.requests)
                        out.print(
                            f"  the allowance left covers {covered:,} of the {counts.due:,} due "
                            f"records; the rest needs {periods:,} more "
                            f"{'period' if periods == 1 else 'periods'} of "
                            f"{allowance.period_hours:g} hours",
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
                if counts.needs_attention:
                    out.print(
                        f"  {counts.needs_attention:,} failed "
                        f"{settings.backfill_attempt_limit} times and are skipped: "
                        "they need attention",
                        markup=False,
                    )


def _merge(reports: list[RunReport]) -> RunReport:
    merged = RunReport(errors=[])
    for report in reports:
        merged.done += report.done
        merged.nothing_found += report.nothing_found
        merged.failed += report.failed
        merged.deferred += report.deferred
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
        check_ready = getattr(step, "check_ready", None)
        if check_ready is not None:
            with open_session() as session:
                check_ready(session)
        allowances = make_allowances(settings)
        if asks_a_source(step):
            allowances.of(step.source)
        clients = [make_client(step, settings, allowances) for _ in range(workers)]
        share = None if limit is None else -(-limit // workers)

        def now() -> datetime:
            return datetime.now(UTC)

        # A step that calls a model stops when the month's ceiling is reached.
        before_call = ceiling_check(settings, now) if model_spend_of(step) else None

        tried: set[int] = set()

        def work(client: Any) -> RunReport:
            return run_step(
                open_session,
                step,
                client,
                now=now,
                attempt_limit=settings.backfill_attempt_limit,
                limit=share,
                before_call=before_call,
                tried=tried,
            )

        if workers == 1:
            report = work(clients[0])
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                report = _merge(list(pool.map(work, clients)))
    out.print(
        f"{step.name}: {report.done:,} done, {report.nothing_found:,} found nothing, "
        f"{report.failed:,} failed"
        + (f", {report.deferred:,} could not be asked for now" if report.deferred else "")
        + f"; {report.remaining_due:,} still due.",
        markup=False,
    )
    for error in (report.errors or [])[:10]:
        out.print(f"  failed: {error}", markup=False)
    if report.stopped:
        out.print(f"Stopped: {report.stopped}", markup=False)


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
            "now; or interventional, every interventional study."
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
                before_request=lambda: allowances.claim(registry.name),
                refused=lambda wait: allowances.refused(registry.name, wait),
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
    platform: Annotated[
        str, typer.Argument(help="Where the links were shared: hackernews or reddit.")
    ],
    file: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=False,
            readable=True,
            help="A bulk file of that platform's posts, already on this machine.",
        ),
    ],
) -> None:
    """Load the article addresses people shared, from a bulk file of posts.

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
    with refusals(), open_session() as session:
        retried = retry_outlet(session, outlet)
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
    completion date on or after 1 January 2025 and results posted. A set says which
    trials are in it and nothing of how they turned out. Sends no request and changes
    nothing.
    """
    settings_or_exit()
    with refusals(), open_session() as session:
        report = count_sets(session)
    if report.stored == report.without_wider_record:
        err.print(
            "No stored trial has the activity and results fields yet. Load the trials "
            "again in full: `thenwhat backfill load-trials --trials interventional`."
        )
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
            "before these fields were asked for and are in neither set until loaded again.",
            markup=False,
        )


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
