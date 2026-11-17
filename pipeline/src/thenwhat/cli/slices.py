"""The trial target set loaded into the store progressively, in slices
(`store/slices.py`), and its coverage by group and stage."""

import importlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

import httpx
import typer

from thenwhat.cli.backfill import backfill_app
from thenwhat.cli.console import err, out
from thenwhat.cli.export import STORE_SQL
from thenwhat.cli.session import open_session, settings_or_exit
from thenwhat.cli.store import TARGET_SET, _commit, target_rule
from thenwhat.store.push import (
    BUILD_KEY,
    USER_AGENT,
    PushFailed,
    RetryOnBusy,
    pending_path,
    push,
    read_state,
    write_state,
)
from thenwhat.store.slices import (
    GROUPS,
    STAGES,
    Plan,
    SliceRefused,
    chosen,
    coverage,
    plan,
    pubmed_stage,
    record_stage,
    registry_papers_stage,
    slice_records,
)

slices_app = typer.Typer(
    help="Load the trial target set into the store in slices, stage by stage.",
    no_args_is_help=True,
)
backfill_app.add_typer(slices_app, name="slices")

SetName = Annotated[str, typer.Option("--set", help="The trial target set, chosen in this year.")]
PlanFile = Annotated[
    Path | None,
    typer.Option(
        "--plan",
        help="The slices' plan and stages, kept on this device; by default"
        " ~/.thenwhat/slices-<set>-<year>.json, outside the repository.",
    ),
]


def plan_path(given: Path | None, name: str, year: int) -> Path:
    if given is not None:
        return given
    folder = Path.home() / ".thenwhat"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"slices-{name}-{year}.json"


def _plan(session, name: str, given: Path | None) -> tuple[Plan, Path]:
    rule, chosen_in = target_rule(name)
    if rule is None:
        err.print(f"No rule for the set {name}.")
        raise typer.Exit(code=1)
    set_name, year = chosen_in.rsplit(":", 1)
    path = plan_path(given, set_name, int(year))
    made = plan(
        session,
        rule,
        name=set_name,
        year=int(year),
        today=datetime.now(UTC).date(),
        before=Plan.read(path),
    )
    return made, path


@slices_app.command("plan")
def plan_command(trial_set: SetName = TARGET_SET, plan_file: PlanFile = None) -> None:
    """Count the slices of the set, their trials and their order. Changes nothing."""
    settings_or_exit()
    with open_session() as session:
        made, path = _plan(session, trial_set, plan_file)
    out.print(
        f"{made.rule} chosen in {made.year}: {sum(len(s.trials) for s in made.slices):,}"
        f" trials in {len(made.slices)} slices, in this order ({path}):",
        markup=False,
    )
    for group in GROUPS:
        ones = [one for one in made.slices if one.group == group]
        if ones:
            out.print(
                f"  {group}: slices {ones[0].number} to {ones[-1].number},"
                f" {sum(len(one.trials) for one in ones):,} trials",
                markup=False,
            )


@slices_app.command("run")
def run_command(
    trial_set: SetName = TARGET_SET,
    plan_file: PlanFile = None,
    slices: Annotated[
        int, typer.Option("--slices", min=1, help="How many slices with a stage due to work.")
    ] = 1,
    stage: Annotated[
        str | None,
        typer.Option(help=f"Only this stage: {', '.join(STAGES[:-1])}. Every due one if left out."),
    ] = None,
    do_push: Annotated[
        bool,
        typer.Option("--push", help="Push each slice that reaches in_store, as its own run."),
    ] = False,
    state: Annotated[
        Path | None,
        typer.Option(
            "--state", envvar="STORE_PUSH_STATE", help="With --push: the build's .pushed.json."
        ),
    ] = None,
    url: Annotated[
        str, typer.Option("--url", envvar="INGEST_URL", help="With --push: the service.")
    ] = "",
    store_sql: Annotated[Path, typer.Option(envvar="STORE_SQL")] = STORE_SQL,
) -> None:
    """Work the next slices' due stages, in order, saving the plan after each: a run
    stopped part way goes on from there. PubMed is never asked here: its stage reads what
    the operator's off-peak step left, and waits until every trial was asked."""
    import os

    from thenwhat.events.paper_records import keep_paper
    from thenwhat.sources.europepmc import EuropePmc

    if stage is not None and stage not in STAGES[:-1]:
        err.print(f"--stage is one of {', '.join(STAGES[:-1])}.")
        raise typer.Exit(code=1)
    settings = settings_or_exit()
    token = os.environ.get("INGEST_TOKEN", "")
    if do_push and (state is None or not state.is_file() or not url or not token):
        err.print("--push needs --state (the build's .pushed.json), INGEST_URL and INGEST_TOKEN.")
        raise typer.Exit(code=1)
    with_state = "CREATE TABLE trial_slice" in (store_sql / "schema.sql").read_text()
    with open_session() as session:
        made, path = _plan(session, trial_set, plan_file)
        made.write(path)
        index = EuropePmc(session, contact_email=settings.contact_email)
        max_age = timedelta(days=settings.paper_record_max_age_days)
        for one in chosen(made, None, slices):
            now = datetime.now(UTC)
            try:
                if one.due() == "record" and stage in (None, "record"):
                    record_stage(session, one, now)
                if one.due() == "registry_papers" and stage in (None, "registry_papers"):
                    registry_papers_stage(
                        session,
                        one,
                        now,
                        lambda number, at=now: keep_paper(
                            session, index, now=at, max_age=max_age, pubmed_id=number
                        ),
                    )
                if (
                    one.due() == "pubmed_papers"
                    and stage in (None, "pubmed_papers")
                    and not pubmed_stage(session, one, now)
                ):
                    out.print(
                        f"Slice {one.number}: PubMed asked about"
                        f" {one.counts.get('pubmed_asked', 0):,} of its trials; the"
                        " stage waits for the off-peak PubMed step.",
                        markup=False,
                    )
                if do_push and stage in (None, "in_store") and "record" in one.done:
                    _push_slice(session, one, made, state, url, token, with_state)
            except (SliceRefused, PushFailed) as fault:
                made.write(path)
                err.print(str(fault), markup=False)
                raise typer.Exit(code=1) from None
            session.commit()
            made.write(path)
            out.print(
                f"Slice {one.number} ({one.group}, {len(one.trials):,} trials):"
                f" {', '.join(sorted(one.done)) or 'nothing done'}.",
                markup=False,
            )
    if not with_state:
        out.print(
            "The store's schema has no trial_slice table yet: slice states are kept on this"
            " device only and not pushed.",
            markup=False,
        )


def _push_slice(session, one, made: Plan, state, url, token, with_state: bool) -> None:
    records, texts = slice_records(session, one, rule=made.rule, year=made.year)
    if not with_state:
        records = [record for record in records if record.kind != "trial_slice"]
    held = read_state(state)
    with httpx.Client(
        transport=RetryOnBusy(),
        base_url=url,
        headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT},
        timeout=120,
    ) as client:
        report = push(
            client,
            records,
            held,
            writer="operator",
            commit=_commit(),
            payload_text=texts.get,
            on_merged=lambda now: write_state(state, now),
            pending=pending_path(state),
            belongs={"build": held.get(BUILD_KEY, ""), "target": url},
        )
    one.counts["in_store"] = len(one.trials)
    one.done["in_store"] = (datetime.now(UTC)).isoformat(timespec="microseconds")
    out.print(
        f"Slice {one.number}: {sum(report.handed.values()):,} records handed over in"
        f" {report.runs} runs; the rest the store held already.",
        markup=False,
    )


@slices_app.command("mark")
def mark_command(
    stage: Annotated[str, typer.Option(help="The stage to record as done: page.")],
    numbers: Annotated[list[int], typer.Argument(help="The slices' numbers.")],
    trial_set: SetName = TARGET_SET,
    plan_file: PlanFile = None,
) -> None:
    """Record a stage done that another piece of work did: `page`, when the site lists
    the slices' trials."""
    if stage != "page":
        err.print("Only the page stage is recorded by hand.")
        raise typer.Exit(code=1)
    settings_or_exit()
    with open_session() as session:
        made, path = _plan(session, trial_set, plan_file)
    now = datetime.now(UTC).isoformat(timespec="microseconds")
    for one in chosen(made, numbers, None):
        one.done["page"] = now
    made.write(path)
    out.print(f"Recorded page for slices {', '.join(map(str, numbers))}.", markup=False)


def coverage_command(trial_set: SetName = TARGET_SET, plan_file: PlanFile = None) -> None:
    """What is held for the set, by group and stage: trials, with results, with a paper
    the registry lists, PubMed asked and found, in the store, on the site. Counts only."""
    settings_or_exit()
    with open_session() as session:
        made, path = _plan(session, trial_set, plan_file)
        # The database's own counts come with pull request 315 (backfill.trial_coverage).
        try:
            coverage_of = importlib.import_module("thenwhat.backfill.trial_coverage").coverage_of
        except (ImportError, AttributeError):
            coverage_of = None
        if coverage_of is not None:
            counted = coverage_of(session, made.year)
            out.print("The database, by the registry's groups (trial_coverage):", markup=False)
            for group in [*counted.groups, counted.total]:
                out.print(
                    f"  {group.name}: {group.trials:,} trials, {group.with_results:,} with"
                    f" results, {group.with_listed_paper:,} with a paper the registry lists,"
                    f" {group.with_pubmed_paper:,} with a paper found by number",
                    markup=False,
                )
    found = coverage(made)
    out.print(f"The slices, by group and stage ({path}):", markup=False)
    for name, counted in [*found.groups.items(), ("all", found.total)]:
        trials = counted["trials"] or 1
        stages = ", ".join(
            f"{stage} {(done := counted[f'trials {stage}']):,} ({100 * done // trials}%)"
            for stage in STAGES
        )
        out.print(
            f"  {name}: {counted['trials']:,} trials in {counted['slices']} slices,"
            f" {counted['with_results']:,} with results, {counted['registry_papers']:,} papers"
            f" listed, PubMed asked {counted['pubmed_asked']:,} and found"
            f" {counted['pubmed_found']:,}; {stages}",
            markup=False,
        )
