"""The trial target set loaded into the store progressively, in slices
(`store/slices.py`), and its coverage by group and stage."""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any

import httpx
import typer

from thenwhat.backfill.trial_coverage import coverage_of
from thenwhat.cli.backfill import backfill_app
from thenwhat.cli.console import err, out
from thenwhat.cli.session import open_session, settings_or_exit
from thenwhat.cli.store import TARGET_SET, _commit, target_rule
from thenwhat.store.push import (
    BUILD_KEY,
    RELOADED,
    USER_AGENT,
    PushFailed,
    RetryOnBusy,
    check_store,
    pending_path,
    push,
    read_state,
    slices_held,
    slices_in_store,
    target_of,
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
    state_record,
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
    again: Annotated[
        bool,
        typer.Option(
            "--again",
            help="With --push: take every slice as not in the store, as for a store loaded"
            " afresh, and push it again; only what the store lacks is sent.",
        ),
    ] = False,
) -> None:
    """Work the next slices' due stages, in order, saving the plan after each: a run
    stopped part way goes on from there. PubMed is never asked here: its stage reads what
    the operator's off-peak step left, and waits until every trial was asked.

    With --push, every planned slice's state goes first, then each slice worked is pushed
    with its trials, papers and state. A slice is in the store of the build the push state
    names: a push state from another build (a store loaded afresh) makes every slice due
    to be pushed again, as --again does. A store loaded from another build is refused,
    and so is one loaded again (it holds no slice of the set while this device says some
    were sent), until fresh-state and --again."""
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
    with open_session() as session:
        made, path = _plan(session, trial_set, plan_file)
        if do_push and state is not None:
            store = store_of(state, url)
            try:
                shown = _check_store(made, state, store, url, token, again=again)
            except PushFailed as fault:
                err.print(str(fault), markup=False)
                raise typer.Exit(code=1) from None
            resend = forget_lost(made, store, shown, again=again)
            if resend:
                out.print(
                    f"{len(resend)} slices this device had in the store are not in it now;"
                    " they go again whole.",
                    markup=False,
                )
        made.write(path)
        if do_push and state is not None:
            try:
                _push_plan(made, state, url, token)
            except PushFailed as fault:
                err.print(str(fault), markup=False)
                raise typer.Exit(code=1) from None
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
                if (
                    do_push
                    and state is not None
                    and stage in (None, "in_store")
                    and "record" in one.done
                ):
                    _push_slice(session, one, made, state, url, token, again=again)
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


def _client(url: str, token: str) -> httpx.Client:
    return httpx.Client(
        transport=RetryOnBusy(),
        base_url=url,
        headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT},
        timeout=120,
    )


def _push(records, texts, state: Path, url: str, token: str, drop: set[str] | None = None):
    """Push records with the state's rules, after taking `drop`'s keys out of the state,
    so that those records are sent again whatever the state said of them."""
    held = read_state(state)
    for key in drop or ():
        held.pop(key, None)
    with _client(url, token) as client:
        return push(
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


def _push_plan(made: Plan, state: Path, url: str, token: str) -> None:
    """Every planned slice's state, so the store's totals of the set are whole from the
    start; sent again, only what changed goes."""
    records = [state_record(one, rule=made.rule, year=made.year) for one in made.slices]
    report = _push(records, {}, state, url, token)
    out.print(
        f"The plan's {len(made.slices)} slices: {report.handed['trial_slice']:,} states handed"
        " over; the rest the store held already.",
        markup=False,
    )


def forget_lost(made: Plan, store: str, shown: set[int] | None, *, again: bool) -> set[int]:
    """Take out of the store every slice not in it for this push: all with `again`, those
    marked in another store, and those this device marks in this store that the store
    does not show in it (`shown`, from its progress), which a restore took back. Those go
    again whole: what the state says of their records is as stale as their mark. Their
    numbers."""
    lost = {
        one.number
        for one in made.slices
        if one.store == store and shown is not None and one.number not in shown
    }
    for one in made.slices:
        if again or one.store != store or one.number in lost:
            one.forget_store()
        if one.number in lost:
            one.whole = True
    return lost


def _check_store(
    made: Plan, state: Path, store: str, url: str, token: str, *, again: bool
) -> set[int] | None:
    """Before a push: refuse a store loaded from another build than the state's, and a
    store loaded again (it holds no slice of the set) while this device's state or plan
    says slices were sent, unless every slice is to go again. The numbers of the set's
    slices the store shows in it, or None when it does not say."""
    held = read_state(state)
    with _client(url, token) as client:
        progress, took_since = check_store(client, held)
    if took_since:
        write_state(state, held)
    if progress is None:
        out.print("The store gave no progress; its build and slices are not compared.")
        return None
    sent = any(key.startswith("trial_slice\t") for key in held) or any(
        one.store == store for one in made.slices
    )
    if not again and sent and slices_held(progress, made.rule, made.year) == 0:
        raise PushFailed(RELOADED)
    return slices_in_store(progress, made.rule, made.year)


def store_of(state: Path, url: str) -> str:
    """The store a slice's `in_store` is true of: the build its push state holds, at the
    store it pushes to."""
    return f"{read_state(state).get(BUILD_KEY, '')}@{target_of(url)}"


def _push_slice(
    session, one, made: Plan, state: Path, url: str, token: str, *, again: bool = False
) -> None:
    """A slice's trials, papers and state, as one run or a few. Its trials are sent every
    time, whatever the state says of them, so the merge says how many the store took:
    the slice is in the store only when the store resolved every one of its trials, and
    its state says so in the run after. With `again`, every record of the slice is sent."""
    records, texts = slice_records(session, one, rule=made.rule, year=made.year)
    keys = {f"{r.kind}\t{r.key}" for r in records}
    trials = {f"{r.kind}\t{r.key}" for r in records if r.kind == "registry_trial"}
    report = _push(records, texts, state, url, token, drop=keys if again or one.whole else trials)
    resolved = report.resolved["registry_trial"]
    one.counts["in_store"] = min(resolved, len(one.trials))
    if resolved >= len(one.trials):
        one.done["in_store"] = datetime.now(UTC).isoformat(timespec="microseconds")
        one.store = store_of(state, url)
        one.whole = False
    else:
        one.done.pop("in_store", None)
        out.print(
            f"Slice {one.number}: the store took {resolved:,} of its {len(one.trials):,}"
            " trials; it is not marked in the store.",
            markup=False,
        )
    # The slice's state, with what the store said, in a run of its own.
    _push([state_record(one, rule=made.rule, year=made.year)], {}, state, url, token)
    out.print(
        f"Slice {one.number}: {sum(report.handed.values()):,} records handed over in"
        f" {report.runs} runs, {resolved:,} of its trials in the store.",
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
        # The database's own counts, by the registry's groups (`backfill.trial_coverage`).
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
    url, token = os.environ.get("INGEST_URL", ""), os.environ.get("INGEST_TOKEN", "")
    if not (url and token):
        out.print(
            "In the store: set INGEST_URL and INGEST_TOKEN to read it from the store's own"
            " slices (GET /progress); the counts above are this device's plan.",
            markup=False,
        )
        return
    with _client(url, token) as client:
        answer = client.get("/progress")
    if answer.status_code != 200:
        err.print(f"The service did not give its progress: {answer.status_code}", markup=False)
        raise typer.Exit(code=1)
    for one_set in _sets(answer.json()):
        if (one_set.get("rule"), one_set.get("year")) != (made.rule, made.year):
            continue
        stages = one_set.get("stages") or {}
        out.print(
            f"In the store, from its slices: {one_set.get('total_slices', '?')} slices,"
            f" {one_set.get('total_trials', '?'):,} trials; "
            + ", ".join(
                f"{stage} {(stages.get(stage) or {}).get('trials', 0):,}" for stage in STAGES
            ),
            markup=False,
        )


def _sets(value: Any) -> list[dict[str, Any]]:
    """The sets of a `GET /progress` answer, whatever it is wrapped in."""
    if isinstance(value, dict):
        for key in ("sets", "progress"):
            if isinstance(value.get(key), list):
                return value[key]
        return [value]
    return value if isinstance(value, list) else []
