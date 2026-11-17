"""The trial target set loaded into the store progressively, in slices, with each slice's
stages visible (operator, 2026-11-17). Behavior: openspec change cloudflare-source-of-truth,
design decision 20 and docs/adr/0010.

The set (`active-or-ended-this-year`) is cut into slices of about `SLICE_TRIALS` trials,
in this order of groups: ended this year with results posted, ended this year, under way
with results, under way and updated in the last twelve months, the rest. Within a group
trials go by registry and identifier, so a plan made twice from the same trials is the
same plan. A plan is kept in a local file; made again, it keeps every slice it had and
puts trials new to the set into new slices after them, so a slice's trials never move.

A slice's stages, in order:

- `record`: its trials are stored with their wider record and without people;
- `registry_papers`: each paper its trials' records list is kept as a paper record;
- `pubmed_papers`: PubMed was asked which papers carry its trials' numbers. Off-peak
  nights only, run by the operator; a slice may go to the store before this stage and is
  sent again after it, which changes only what changed;
- `in_store`: its trials, their papers and its own state were pushed and merged;
- `page`: the site lists its trials. Recorded when told, by the trial-page work.

Nothing here judges a trial: a slice says only what is held for its trials.
"""

import json
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from thenwhat.db.models import PaperRecord, RegistryTrial, TrialPaper, WorkEntry
from thenwhat.domain import WorkOutcome
from thenwhat.sources.people import payload_without_people, people_in
from thenwhat.store import records as r
from thenwhat.store.form import Record, key_of, payload_of, payload_record_of, when

SLICE_TRIALS = 2_000
GROUPS = (
    "ended with results",
    "ended",
    "active with results",
    "active updated",
    "active not updated",
)
STAGES = ("record", "registry_papers", "pubmed_papers", "in_store", "page")
UNDER_WAY = ("RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION", "ACTIVE_NOT_RECRUITING")


class SliceRefused(Exception):
    """A slice cannot go on to a stage: what it holds is not what the stage needs."""


@dataclass
class Slice:
    number: int
    group: str
    # Its trials by registry and identifier: `registry|NCT...`.
    trials: list[str]
    # When each stage was done, by stage.
    done: dict[str, str] = field(default_factory=dict)
    # What it holds, counted: trials with results, papers listed, PubMed asked and found,
    # trials in the store.
    counts: dict[str, int] = field(default_factory=dict)
    # The build whose store its `in_store` is true of: a store loaded afresh from another
    # build holds none of the set's trials until the slices are pushed to it again.
    store: str = ""
    # Its next push sends every record of it, whatever the push state says: the store
    # lost it (a restore), so what the state says of its records is stale too.
    whole: bool = False
    # When its trials were last fetched from the registry, as they were when it was last
    # pushed: a later fetch is an update the store does not hold yet.
    trials_at: str = ""

    def forget_store(self) -> None:
        """Its `in_store` belongs to another store: not done for this one."""
        self.done.pop("in_store", None)
        self.counts.pop("in_store", None)
        self.store = ""

    def due(self) -> str | None:
        """The first stage not done, in order; `page` is only ever told."""
        for stage in STAGES[:-1]:
            if stage not in self.done:
                return stage
        return None


@dataclass
class Plan:
    rule: str
    year: int
    slices: list[Slice] = field(default_factory=list)

    def write(self, path: Path) -> None:
        temporary = path.with_name(path.name + ".part")
        temporary.write_text(json.dumps(asdict(self), indent=1))
        temporary.replace(path)

    @classmethod
    def read(cls, path: Path) -> "Plan | None":
        if not path.is_file():
            return None
        value = json.loads(path.read_text())
        return cls(value["rule"], value["year"], [Slice(**one) for one in value["slices"]])


def group_of(
    status: str | None,
    completion: str | None,
    has_results: bool | None,
    updated: date | None,
    *,
    year: int,
    today: date,
) -> str:
    """Which group a trial of the set goes in, by what its record states."""
    ended = status not in UNDER_WAY and str(completion or "").startswith(f"{year:04d}")
    if ended:
        return GROUPS[0] if has_results else GROUPS[1]
    if has_results:
        return GROUPS[2]
    if updated is not None and updated >= today - timedelta(days=365):
        return GROUPS[3]
    return GROUPS[4]


def plan(
    session: Session,
    rule: Any,
    *,
    name: str,
    year: int,
    today: date,
    before: Plan | None = None,
    size: int = SLICE_TRIALS,
) -> Plan:
    """The slices of the set the rule selects. A plan given keeps its slices; trials new
    to the set go into new slices after them, by group and identifier."""
    made = before if before is not None and (before.rule, before.year) == (name, year) else None
    held = {trial for one in made.slices for trial in one.trials} if made else set()
    grouped: dict[str, list[str]] = {group: [] for group in GROUPS}
    for registry, external, status, completion, results, updated in session.execute(
        select(
            RegistryTrial.registry_name,
            RegistryTrial.external_id,
            RegistryTrial.overall_status,
            RegistryTrial.completion_date,
            RegistryTrial.has_results,
            RegistryTrial.last_update_posted,
        )
        .where(rule)
        .order_by(RegistryTrial.registry_name, RegistryTrial.external_id)
    ):
        trial = key_of(registry, external)
        if trial not in held:
            group = group_of(status, completion, results, updated, year=year, today=today)
            grouped[group].append(trial)
    result = made or Plan(name, year)
    number = len(result.slices)
    for group in GROUPS:
        trials = grouped[group]
        for start in range(0, len(trials), size):
            number += 1
            result.slices.append(Slice(number, group, trials[start : start + size]))
    return result


def _trials(session: Session, one: Slice) -> list[RegistryTrial]:
    keys = {tuple(trial.split("|", 1)) for trial in one.trials}
    numbers = sorted({external for _, external in keys})
    found: list[RegistryTrial] = []
    for start in range(0, len(numbers), 1000):
        found += [
            trial
            for trial in session.scalars(
                select(RegistryTrial).where(
                    RegistryTrial.external_id.in_(numbers[start : start + 1000])
                )
            )
            if (trial.registry_name, trial.external_id) in keys
        ]
    return sorted(found, key=lambda trial: (trial.registry_name, trial.external_id))


def record_stage(session: Session, one: Slice, now: datetime) -> None:
    """Its trials are stored with their wider record and name no person; refused when a
    trial is missing or one names a person."""
    trials = _trials(session, one)
    if len(trials) != len(one.trials):
        raise SliceRefused(
            f"Slice {one.number}: {len(one.trials) - len(trials)} of its trials are not stored."
            " Load them (thenwhat backfill load-trials) and run the slice again."
        )
    named = sum(bool(people_in(trial.raw_payload)) for trial in trials)
    if named:
        raise SliceRefused(
            f"Slice {one.number}: {named} trials' records name a person. Run"
            " thenwhat backfill strip-event-people --apply and the slice again."
        )
    one.counts["trials"] = len(trials)
    one.counts["with_results"] = sum(bool(trial.has_results) for trial in trials)
    one.done["record"] = when(now) or ""


def listed_papers(session: Session, one: Slice) -> list[str]:
    """The PubMed numbers its trials' records list as their papers, each once."""
    from thenwhat.backfill.trial_references import references_of

    numbers: dict[str, None] = {}
    for trial in _trials(session, one):
        for paper in references_of(trial.raw_payload).papers:
            numbers.setdefault(paper.pubmed_id)
    return list(numbers)


def registry_papers_stage(
    session: Session, one: Slice, now: datetime, keep: Callable[[list[str]], Any]
) -> None:
    """Each paper its trials' records list is kept as a paper record, by `keep` (the one
    store of paper records, `events.paper_records.keep_papers_by_pubmed_id`, given the
    PubMed numbers all at once, so the index is asked many to a request)."""
    numbers = listed_papers(session, one)
    keep(numbers)
    one.counts["registry_papers"] = len(numbers)
    one.done["registry_papers"] = when(now) or ""


def papers_lost(session: Session, one: Slice) -> int:
    """How many papers its trials' records list have no paper record, though its registry
    papers stage is done: a stage whose work was rolled back after the plan said it was
    done. Nought when the stage is not done."""
    if "registry_papers" not in one.done:
        return 0
    numbers = listed_papers(session, one)
    kept = 0
    for start in range(0, len(numbers), 1000):
        kept += (
            session.scalar(
                select(func.count(func.distinct(PaperRecord.pubmed_id))).where(
                    PaperRecord.pubmed_id.in_(numbers[start : start + 1000])
                )
            )
            or 0
        )
    return len(numbers) - kept


def trials_fetched_at(session: Session, one: Slice) -> str:
    """When its trials were last fetched from the registry, the latest of them."""
    return max((when(trial.fetched_at) or "" for trial in _trials(session, one)), default="")


def trials_changed(session: Session, one: Slice) -> bool:
    """Whether a trial of it was fetched from the registry again since the slice was last
    pushed: a registry update the store does not hold yet. False for a slice pushed
    before this was noted, or never pushed."""
    if not one.trials_at or "in_store" not in one.done:
        return False
    return trials_fetched_at(session, one) > one.trials_at


def pubmed_counts(session: Session, one: Slice) -> tuple[int, int, int]:
    """Of a slice's ClinicalTrials.gov trials: how many PubMed was asked about (their
    ledger entry), how many have a paper it found (`trial_paper`), and how many there are."""
    trials = [t for t in _trials(session, one) if t.registry_name == "clinicaltrials.gov"]
    ids = [trial.id for trial in trials]
    asked = found = 0
    for start in range(0, len(ids), 1000):
        part = ids[start : start + 1000]
        asked += (
            session.scalar(
                select(func.count(func.distinct(WorkEntry.record_id))).where(
                    WorkEntry.step == "pubmed_papers",
                    WorkEntry.record_kind == "registry_trial",
                    WorkEntry.record_id.in_(part),
                    WorkEntry.outcome.in_((WorkOutcome.DONE, WorkOutcome.NOTHING_FOUND)),
                )
            )
            or 0
        )
        found += (
            session.scalar(
                select(func.count(func.distinct(TrialPaper.registry_trial_id))).where(
                    TrialPaper.registry_trial_id.in_(part)
                )
            )
            or 0
        )
    return asked, found, len(trials)


def pubmed_stage(session: Session, one: Slice, now: datetime) -> bool:
    """Whether PubMed was asked about every one of its trials, and what it found. The
    asking is the operator's off-peak step (`pubmed_papers`); this only reads what it left:
    a trial asked has its ledger entry, a paper found its `trial_paper`. Done when every
    ClinicalTrials.gov trial of the slice was asked."""
    asked, found, trials = pubmed_counts(session, one)
    one.counts["pubmed_asked"], one.counts["pubmed_found"] = asked, found
    if asked < trials:
        return False
    one.done["pubmed_papers"] = when(now) or ""
    return True


def due_slices(
    session: Session, made: Plan, count: int | None, *, store: str | None
) -> list[Slice]:
    """The next `count` slices with work to do, in order. A slice is due when its record
    or registry papers stage is not done, or the papers that stage kept are not all held;
    with `store` (a push), when it is not in that store, is to go whole, or has a trial
    fetched from the registry since it was put there (only what changed goes); and when
    PubMed's off-peak step has moved on its trials since the slice last looked. A slice
    waiting only on that step, with its ledger where it was, is not due: it would be
    pushed again for nothing and keep the next slices from their turn."""

    def has_work(one: Slice) -> bool:
        if one.due() in ("record", "registry_papers") or papers_lost(session, one):
            return True
        if store is not None and (
            "in_store" not in one.done
            or one.store != store
            or one.whole
            or trials_changed(session, one)
        ):
            return True
        if one.due() != "pubmed_papers":
            return False
        asked, found, _ = pubmed_counts(session, one)
        return (asked, found) != (one.counts.get("pubmed_asked"), one.counts.get("pubmed_found"))

    due: list[Slice] = []
    for one in made.slices:
        if count is not None and len(due) >= count:
            break
        if has_work(one):
            due.append(one)
    return due


def slice_records(
    session: Session, one: Slice, *, rule: str, year: int
) -> tuple[list[Record], dict[str, str]]:
    """What a slice puts in the store: its trials with their payloads, the paper records
    its trials' records list, the papers found by its trials' numbers (`trial_paper`,
    without their abstracts), and its own state (`trial_slice`); and the text of each
    payload too large to travel in its record, by checksum."""
    found: list[Record] = []
    texts: dict[str, str] = {}
    for trial in _trials(session, one):
        payload = payload_of(r.registry_payload(trial))
        if not payload.inline:
            texts[payload.sha256] = payload.text
        found.append(payload_record_of(payload))
        found.append(r.registry_trial_record(trial, payload_sha256=payload.sha256))
    numbers = listed_papers(session, one)
    for start in range(0, len(numbers), 1000):
        for paper in session.scalars(
            select(PaperRecord).where(PaperRecord.pubmed_id.in_(numbers[start : start + 1000]))
        ):
            found.append(r.paper_source_record(paper))
    trials = {trial.id: trial for trial in _trials(session, one)}
    ids = sorted(trials)
    for start in range(0, len(ids), 1000):
        for paper in session.scalars(
            select(TrialPaper)
            .where(TrialPaper.registry_trial_id.in_(ids[start : start + 1000]))
            .order_by(TrialPaper.id)
        ):
            payload = payload_of(payload_without_people(paper.raw_payload))
            if not payload.inline:
                texts[payload.sha256] = payload.text
            trial = trials[paper.registry_trial_id]
            key = key_of(trial.registry_name, trial.external_id, paper.source_name, paper.pubmed_id)
            found.append(payload_record_of(payload))
            found.append(
                Record(
                    "trial_paper",
                    key,
                    {
                        "registry_name": trial.registry_name,
                        "trial_id": trial.external_id,
                        "source_name": paper.source_name,
                        "pubmed_id": paper.pubmed_id,
                        "payload_sha256": payload.sha256,
                        "fetched_at": when(paper.fetched_at),
                    },
                )
            )
    found.append(state_record(one, rule=rule, year=year))
    return found, texts


REQUIRED_COUNTS = ("with_results", "in_store")


def state_record(one: Slice, *, rule: str, year: int) -> Record:
    """A slice's state as the store keeps it (`trial_slice`), for the page of progress."""
    counted = ("registry_papers", "pubmed_asked", "pubmed_found")
    body = {
        "rule": rule,
        "year": int(year),
        "number": int(one.number),
        "grp": one.group,
        "trials": len(one.trials),
        # The store holds these as numbers from the plan on (NOT NULL): 0 until counted.
        **{name: int(one.counts.get(name, 0)) for name in REQUIRED_COUNTS},
        # A stage's own count stays out until the stage is worked: the store keeps none.
        **{name: int(one.counts[name]) for name in counted if name in one.counts},
        **{f"{stage}_at": at for stage, at in one.done.items() if at},
    }
    return Record("trial_slice", key_of(rule, year, one.number), body)


@dataclass
class Coverage:
    """By group, and over the set: trials, and how many are at each stage."""

    groups: dict[str, Counter[str]]

    @property
    def total(self) -> Counter[str]:
        found: Counter[str] = Counter()
        for counted in self.groups.values():
            found.update(counted)
        return found


def coverage(made: Plan) -> Coverage:
    groups = {group: Counter() for group in GROUPS}
    for one in made.slices:
        counted = groups[one.group]
        counted["trials"] += len(one.trials)
        counted["slices"] += 1
        for name in ("with_results", "registry_papers", "pubmed_asked", "pubmed_found"):
            counted[name] += one.counts.get(name, 0)
        for stage in STAGES:
            if stage in one.done:
                counted[f"trials {stage}"] += len(one.trials)
    return Coverage(groups)


def chosen(made: Plan, numbers: Iterable[int] | None, count: int | None) -> list[Slice]:
    """The slices to work: those named, else the next `count` with a stage due."""
    if numbers is not None:
        wanted = set(numbers)
        return [one for one in made.slices if one.number in wanted]
    due = [one for one in made.slices if one.due() is not None]
    return due if count is None else due[:count]
