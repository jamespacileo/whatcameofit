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
    sample_leads,
)
from thenwhat.backfill.link_funnel import funnel
from thenwhat.backfill.link_load import load_links
from thenwhat.backfill.link_read import LinkRead, ReadClient
from thenwhat.backfill.link_readers import posts_of
from thenwhat.backfill.link_report import IN_SCOPE_KINDS, screening_report
from thenwhat.backfill.link_triage import DecisionClient, LinkTriage, Standing
from thenwhat.backfill.mediacloud import MediaCloud
from thenwhat.backfill.registered import registered_steps
from thenwhat.backfill.registry_load import (
    PHASE_3_DRUG_OR_BIOLOGICAL,
    TrialList,
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
from thenwhat.cli import session as cli_session
from thenwhat.cli.console import err, out
from thenwhat.cli.session import settings_or_exit
from thenwhat.config import Settings, SourceAllowance
from thenwhat.domain import Decider, LeadVerdict, OutletKind
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
    return Allowances(
        open_session,
        settings.allowances(),
        outlet_interval_seconds=settings.outlet_interval_seconds,
    )


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


def _dollars(amount: Decimal) -> str:
    return f"${amount.quantize(Decimal('0.01'))}"


def _spend_line(session: Session, settings: Settings, spend: ModelSpend, due: int) -> str:
    """What a model step's due records would cost beside what is left of the month's
    ceiling. No cost is given while a price is not configured."""
    try:
        prices = prices_for(settings, spend.door)
    except PricesNotSet as missing:
        return f"  calls a model: no cost can be given, {missing}"
    cost = cost_of(spend, prices, due)
    left = left_this_month(session, settings, datetime.now(UTC))
    line = (
        f"  calls a model: the due records need about {_dollars(cost)}; "
        f"{_dollars(left)} of the month's {_dollars(settings.llm_monthly_budget_usd)} "
        "ceiling is left"
    )
    covered = records_covered(spend, prices, left)
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
                elif step.requests_per_record:
                    pages = counts.due * step.requests_per_record
                    out.print(
                        f"  asks outlets for {pages:,} pages, each outlet at least "
                        f"{settings.outlet_interval_seconds:g} seconds apart",
                        markup=False,
                    )
                else:
                    out.print("  asks no source: the due records need 0 requests", markup=False)
                spend = model_spend_of(step)
                if spend is not None:
                    out.print(_spend_line(session, settings, spend, counts.due), markup=False)
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

        def work(client: Any) -> RunReport:
            return run_step(
                open_session,
                step,
                client,
                now=now,
                attempt_limit=settings.backfill_attempt_limit,
                limit=share,
                before_call=before_call,
            )

        if workers == 1:
            report = work(clients[0])
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                report = _merge(list(pool.map(work, clients)))
    out.print(
        f"{step.name}: {report.done:,} done, {report.nothing_found:,} found nothing, "
        f"{report.failed:,} failed; {report.remaining_due:,} still due.",
        markup=False,
    )
    for error in (report.errors or [])[:10]:
        out.print(f"  failed: {error}", markup=False)
    if report.stopped:
        out.print(f"Stopped: {report.stopped}", markup=False)


@backfill_app.command("load-trials")
def load_trials_command(
    condition: Annotated[
        str,
        typer.Option(
            help="Which trials to load, in the registry's own expression language. "
            "The default is phase 3 interventional trials of a drug or biological."
        ),
    ] = PHASE_3_DRUG_OR_BIOLOGICAL,
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
    """
    settings = settings_or_exit()
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
            )
    since = f" updated since {report.changes_since}" if report.changes_since else ""
    out.print(
        f"Loaded {report.added + report.updated:,} trials{since} in {report.requests:,} "
        f"requests: {report.added:,} new, {report.updated:,} already stored.",
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
) -> None:
    """Draw scored link leads to label, in equal numbers from each tenth of the score
    range and spread across platforms.

    Leads you have already labelled are left out. The scores are not shown, so that a
    label does not lean on them. Label each lead with `thenwhat backfill label-lead`.
    """
    settings = settings_or_exit()
    with refusals(), open_session() as session:
        sample = sample_leads(session, size=size, seed=seed, version=_triage_version(settings))
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
    out.print(
        f"{len(sample.leads):,} leads, {sample.per_tenth} from each tenth of the score range."
    )
    for tenth, found in sorted(sample.short.items()):
        out.print(
            f"  the tenth from {tenth / TENTHS:.1f} is short: it holds only {found} "
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
            "No link lead has a label of yours yet at this version of triage. Draw leads "
            "with `thenwhat backfill sample-leads` and label them with "
            "`thenwhat backfill label-lead`."
        )
        if evaluation.assistant_only:
            out.print(
                f"{evaluation.assistant_only:,} leads have only an assistant's label, "
                "which is not counted."
            )
        return
    out.print(
        f"Triage version {version}: {evaluation.overall.labels:,} leads carry a label of yours.",
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
        out.print("Where your label and the score disagree most:", markup=False)
        for case in evaluation.disagreements:
            out.print(
                f"  {case.lead_id}  score {case.score:.2f}  labelled {case.label.value}  "
                f"{case.title}",
                markup=False,
                soft_wrap=True,
            )
    if evaluation.assistant_only:
        out.print(
            f"{evaluation.assistant_only:,} leads have only an assistant's label. They are "
            "not counted in any figure above.",
            markup=False,
        )


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
    ]
    if found.new_otherwise:
        lines.append(f"  new claim, decided otherwise or pending: {found.new_otherwise:,}")
    lines += [
        f"  needs a vertical, no claim made: {found.needs_vertical:,}",
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
        "(the reads and the vertical decisions; checks of reported statements are "
        "recorded with all statement checks)",
    ]
    for line in lines:
        out.print(line, markup=False)
