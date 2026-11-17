"""How well triage separates link leads that report a treatment from those that do
not, measured on labels given to a sample. Behavior: openspec lead-evaluation.

A label belongs to the lead, not to one triage answer, so it holds for every later
version of triage. A label is a person's or an assistant's and is stored as what it is.
The label that counts for a lead is the person's when there is one, and otherwise the
assistant's: the operator decided on 2026-11-14 that an assistant's labels count, on
condition that the operator spot-checks them (`spot_check`).
"""

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import ColumnElement, Select, and_, case, exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, aliased

from thenwhat.db.models import LinkLead, LinkLeadLabel, LinkShare
from thenwhat.domain import Decider, LeadVerdict, ScreenOutcome
from thenwhat.work.errors import BackfillError

TENTHS = 10
THRESHOLDS = tuple(tenth / TENTHS for tenth in range(1, TENTHS))
DISAGREEMENTS_SHOWN = 10
# A label and a score this far apart are a disagreement worth a person's look.
DISAGREEMENT = 0.5
SPOT_CHECK_DISAGREEMENTS = 20
SPOT_CHECK_RANDOM = 30


class UnknownLabel(BackfillError):
    """The label given is not one of the triage options."""


class UnknownLead(BackfillError):
    """No link lead has the id given."""


class BadLabelFile(BackfillError):
    """A line of a file of labels cannot be used. Nothing in the file is recorded."""


def tenth_of(score: float) -> int:
    """Which tenth of the score range a score is in: 0 for under 0.1, 9 for 0.9 and over."""
    return min(int(score * TENTHS), TENTHS - 1)


def _scored(version: int) -> ColumnElement[bool]:
    """A lead in scope with a score from the current version of triage."""
    return and_(
        LinkLead.screen_outcome == ScreenOutcome.IN_SCOPE,
        LinkLead.triage_score.is_not(None),
        LinkLead.triage_version == version,
    )


def _in_tenth(tenth: int) -> ColumnElement[bool]:
    low = LinkLead.triage_score >= tenth / TENTHS
    if tenth == TENTHS - 1:
        return low
    return and_(low, LinkLead.triage_score < (tenth + 1) / TENTHS)


def _labelled_by(by: Decider) -> ColumnElement[bool]:
    return exists().where(
        LinkLeadLabel.link_lead_id == LinkLead.id, LinkLeadLabel.labelled_by == by
    )


def _labelled() -> ColumnElement[bool]:
    return exists().where(LinkLeadLabel.link_lead_id == LinkLead.id)


def _shared_on(platform: str) -> ColumnElement[bool]:
    return exists().where(LinkShare.link_lead_id == LinkLead.id, LinkShare.platform == platform)


def _counting_labels() -> Select[int, LeadVerdict, Decider]:
    """Each labelled lead once, with the label that counts: the person's when there is
    one, otherwise the assistant's."""
    by_person_first = case((LinkLeadLabel.labelled_by == Decider.HUMAN, 0), else_=1)
    ranked = select(
        LinkLeadLabel.link_lead_id,
        LinkLeadLabel.label,
        LinkLeadLabel.labelled_by,
        func.row_number()
        .over(partition_by=LinkLeadLabel.link_lead_id, order_by=by_person_first)
        .label("place"),
    ).subquery()
    return select(ranked.c.link_lead_id, ranked.c.label, ranked.c.labelled_by).where(
        ranked.c.place == 1
    )


def _distance(score: float | None, label: LeadVerdict) -> float:
    """How far a score is from what the label says it should be."""
    return abs((score or 0.0) - (1.0 if label is LeadVerdict.TREATMENT_REPORT else 0.0))


# --- sampling ------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Sampled:
    """A lead to label. The score is left out on purpose: the label must not lean on it."""

    lead_id: int
    title: str
    outlet: str
    first_shared: date
    url: str


@dataclass(slots=True)
class Sample:
    leads: list[Sampled] = field(default_factory=list)
    # The tenths that held fewer unlabelled leads than were asked for, and how many.
    short: dict[int, int] = field(default_factory=dict)
    per_tenth: int = 0


def sample_leads(
    session: Session, *, size: int, seed: str, version: int, only_tenth: int | None = None
) -> Sample:
    """Draw scored leads that nobody has labelled, in equal numbers from each tenth of
    the score range, spread across platforms. The same seed draws the same sample.

    With `only_tenth`, all of them come from that one tenth. Equal numbers leave a tenth
    that holds most of the leads thinly labelled: found on the first real run, where 98%
    of leads were under 0.1 and 20 labels there could not say how many reports it hides."""
    tenths = range(TENTHS) if only_tenth is None else [only_tenth]
    per_tenth = max(size // len(tenths), 1)
    sample = Sample(per_tenth=per_tenth)
    platforms = list(session.scalars(select(LinkShare.platform).distinct().order_by("platform")))
    for tenth in tenths:
        chosen: dict[int, LinkLead] = {}
        drawn = {
            platform: list(
                session.scalars(
                    select(LinkLead)
                    .where(_scored(version), _in_tenth(tenth), ~_labelled(), _shared_on(platform))
                    # A fixed order that the seed shuffles: the same seed, the same draw.
                    .order_by(func.md5(func.concat(seed, ":", LinkLead.id)), LinkLead.id)
                    .limit(per_tenth)
                )
            )
            for platform in platforms
        }
        # One lead from each platform in turn, until the tenth has its number.
        for place in range(per_tenth):
            for platform in platforms:
                if len(chosen) < per_tenth and place < len(drawn[platform]):
                    lead = drawn[platform][place]
                    chosen.setdefault(lead.id, lead)
        if len(chosen) < per_tenth:
            sample.short[tenth] = len(chosen)
        sample.leads.extend(
            Sampled(lead.id, lead.title, lead.outlet, lead.first_shared_at.date(), lead.url)
            for lead in chosen.values()
        )
    # The tenths were drawn in order. Listed that way, a lead's place would give away its
    # score, so the leads are put in an order the seed fixes and the score has no part in.
    sample.leads.sort(
        key=lambda lead: hashlib.sha256(f"{seed}:{lead.lead_id}".encode()).hexdigest()
    )
    return sample


# --- labelling -----------------------------------------------------------------------


def _verdict(label: str) -> LeadVerdict:
    options = [verdict.value for verdict in LeadVerdict]
    if label not in options:
        raise UnknownLabel(f"'{label}' is not a label. Labels: {', '.join(options)}.")
    return LeadVerdict(label)


def label_lead(
    session: Session, lead_id: int, label: str, *, by: Decider, now: datetime
) -> LinkLeadLabel:
    """Record what a lead's headline is, as a person or an assistant says. One label per
    lead from each: a second one from the same kind of labeller replaces the first."""
    verdict = _verdict(label)
    if session.get(LinkLead, lead_id) is None:
        raise UnknownLead(f"No link lead has the id {lead_id}.")
    session.execute(
        insert(LinkLeadLabel)
        .values(link_lead_id=lead_id, label=verdict, labelled_by=by, labelled_at=now)
        .on_conflict_do_update(
            constraint="uq_link_lead_label_lead_by",
            set_={"label": verdict, "labelled_at": now},
        )
    )
    session.flush()
    return session.scalars(
        select(LinkLeadLabel).where(
            LinkLeadLabel.link_lead_id == lead_id, LinkLeadLabel.labelled_by == by
        )
    ).one()


def label_leads(session: Session, lines: Iterable[str], *, by: Decider, now: datetime) -> int:
    """Record the labels of a file: a lead's number and a label on each line, separated
    by a tab, a comma or spaces. All of them or none: a line that cannot be used fails
    the whole file and is named. Blank lines and lines that start with # are passed over.
    Returns how many labels were recorded."""
    options = ", ".join(verdict.value for verdict in LeadVerdict)
    wanted: list[tuple[int, str, int]] = []
    for number, line in enumerate(lines, start=1):
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        parts = text.replace(",", " ").split()
        try:
            if len(parts) != 2:
                raise ValueError
            lead_id = int(parts[0])
            _verdict(parts[1])
        except (ValueError, UnknownLabel):
            raise BadLabelFile(
                f"Line {number} is not a lead's number and a label ({options}): '{text}'. "
                "Nothing was recorded."
            ) from None
        wanted.append((lead_id, parts[1], number))
    known = set(
        session.scalars(select(LinkLead.id).where(LinkLead.id.in_([lead for lead, _, _ in wanted])))
    )
    for lead_id, _, number in wanted:
        if lead_id not in known:
            raise BadLabelFile(
                f"Line {number} names the link lead {lead_id}, which does not exist. "
                "Nothing was recorded."
            )
    for lead_id, label, _ in wanted:
        label_lead(session, lead_id, label, by=by, now=now)
    return len(wanted)


# --- the report ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AtThreshold:
    threshold: float
    # None when no labelled lead is at or above the threshold, or none reports a treatment.
    precision: float | None
    recall: float | None
    # Scored leads at or above the threshold: what a pass threshold here would pass.
    passed: int


@dataclass(frozen=True, slots=True)
class Figures:
    labels: int
    labels_by_tenth: list[int]
    scored_by_tenth: list[int]
    rows: list[AtThreshold]

    @property
    def unlabelled_tenths(self) -> list[int]:
        """Tenths that hold scored leads and no label: the figures leave them out."""
        return [
            tenth
            for tenth in range(TENTHS)
            if self.scored_by_tenth[tenth] and not self.labels_by_tenth[tenth]
        ]


@dataclass(frozen=True, slots=True)
class Disagreement:
    lead_id: int
    title: str
    score: float
    label: LeadVerdict


@dataclass(frozen=True, slots=True)
class Evaluation:
    overall: Figures
    by_platform: dict[str, Figures]
    disagreements: list[Disagreement]
    # Of the labels that count: how many are a person's and how many an assistant's.
    by_person: int
    by_assistant: int
    # Leads both have labelled, and on how many of them the two agree.
    checked: int
    agreed: int


def _figures(session: Session, version: int, only: ColumnElement[bool] | None = None) -> Figures:
    """Precision and recall at each threshold, each tenth weighted by how many scored
    leads it holds: the sample takes equal numbers from each tenth, the leads do not."""
    conditions = [_scored(version)] if only is None else [_scored(version), only]
    scored = [0] * TENTHS
    for score in session.scalars(select(LinkLead.triage_score).where(*conditions)):
        # The query's conditions leave out every lead without a score.
        scored[tenth_of(score or 0.0)] += 1
    labelled = [0] * TENTHS
    positive = [0] * TENTHS
    counting = _counting_labels().subquery()
    for score, label in session.execute(
        select(LinkLead.triage_score, counting.c.label)
        .join(counting, counting.c.link_lead_id == LinkLead.id)
        .where(*conditions)
    ):
        tenth = tenth_of(score or 0.0)
        labelled[tenth] += 1
        positive[tenth] += label is LeadVerdict.TREATMENT_REPORT
    # A labelled lead stands for this many leads of its tenth.
    weight = [scored[t] / labelled[t] if labelled[t] else 0.0 for t in range(TENTHS)]
    reports = [positive[t] * weight[t] for t in range(TENTHS)]
    judged = [labelled[t] * weight[t] for t in range(TENTHS)]
    all_reports = sum(reports)
    rows = []
    for threshold in THRESHOLDS:
        above = range(round(threshold * TENTHS), TENTHS)
        reports_above = sum(reports[t] for t in above)
        judged_above = sum(judged[t] for t in above)
        rows.append(
            AtThreshold(
                threshold,
                reports_above / judged_above if judged_above else None,
                reports_above / all_reports if all_reports else None,
                sum(scored[t] for t in above),
            )
        )
    return Figures(sum(labelled), labelled, scored, rows)


def evaluate(session: Session, *, version: int) -> Evaluation:
    """The evaluation of the current version of triage on the leads that are labelled."""
    platforms = list(session.scalars(select(LinkShare.platform).distinct().order_by("platform")))
    counting = _counting_labels().subquery()
    rows = session.execute(
        select(
            LinkLead.id,
            LinkLead.title,
            LinkLead.triage_score,
            counting.c.label,
            counting.c.labelled_by,
        )
        .join(counting, counting.c.link_lead_id == LinkLead.id)
        .where(_scored(version))
    ).all()
    furthest = sorted(rows, key=lambda row: (-_distance(row.triage_score, row.label), row.id))
    person = LinkLeadLabel.__table__.alias("person")
    assistant = LinkLeadLabel.__table__.alias("assistant")
    checked, agreed = session.execute(
        select(func.count(), func.count().filter(person.c.label == assistant.c.label))
        .select_from(person)
        .join(assistant, assistant.c.link_lead_id == person.c.link_lead_id)
        .where(
            person.c.labelled_by == Decider.HUMAN.value,
            assistant.c.labelled_by == Decider.ASSISTANT.value,
        )
    ).one()
    return Evaluation(
        overall=_figures(session, version),
        by_platform={
            platform: _figures(session, version, _shared_on(platform)) for platform in platforms
        },
        disagreements=[
            Disagreement(row.id, row.title, row.triage_score, row.label)
            for row in furthest[:DISAGREEMENTS_SHOWN]
            if _distance(row.triage_score, row.label) >= DISAGREEMENT
        ],
        by_person=sum(row.labelled_by is Decider.HUMAN for row in rows),
        by_assistant=sum(row.labelled_by is Decider.ASSISTANT for row in rows),
        checked=checked,
        agreed=agreed,
    )


# --- the operator's spot-check -------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ToCheck:
    """A lead only an assistant has labelled, for the operator to label themselves. The
    score is left out, as it is from a sample."""

    lead_id: int
    title: str
    outlet: str
    url: str
    assistants_label: LeadVerdict


@dataclass(frozen=True, slots=True)
class SpotCheck:
    # Where the assistant's label and the score disagree most.
    disagreements: list[ToCheck]
    # A random draw of the rest: where label and score agree, both can still be wrong.
    random: list[ToCheck]


def spot_check(
    session: Session,
    *,
    version: int,
    seed: str,
    disagreements: int = SPOT_CHECK_DISAGREEMENTS,
    random: int = SPOT_CHECK_RANDOM,
) -> SpotCheck:
    """The leads only an assistant has labelled that the operator should look at: the
    strongest disagreements with the score, and a random draw of the others, which the
    same seed draws again. A lead the operator labels leaves the list."""
    persons = aliased(LinkLeadLabel)
    rows = [
        (lead, label)
        for lead, label in session.execute(
            select(LinkLead, LinkLeadLabel.label)
            .join(LinkLeadLabel, LinkLeadLabel.link_lead_id == LinkLead.id)
            .where(
                _scored(version),
                LinkLeadLabel.labelled_by == Decider.ASSISTANT,
                # Asked of a second copy of the labels: the first is the assistant's.
                ~exists().where(
                    persons.link_lead_id == LinkLead.id, persons.labelled_by == Decider.HUMAN
                ),
            )
            .order_by(func.md5(func.concat(seed, ":", LinkLead.id)), LinkLead.id)
        )
    ]

    def shown(lead: LinkLead, label: LeadVerdict) -> ToCheck:
        return ToCheck(lead.id, lead.title, lead.outlet, lead.url, label)

    apart = sorted(
        (pair for pair in rows if _distance(pair[0].triage_score, pair[1]) >= DISAGREEMENT),
        key=lambda pair: (-_distance(pair[0].triage_score, pair[1]), pair[0].id),
    )[:disagreements]
    listed = {lead.id for lead, _ in apart}
    rest = [pair for pair in rows if pair[0].id not in listed][:random]
    return SpotCheck([shown(*pair) for pair in apart], [shown(*pair) for pair in rest])


# --- the gate ------------------------------------------------------------------------


def labels_at_version(session: Session, version: int) -> int:
    """How many leads have a label that counts and a score from this version of triage."""
    return (
        session.scalar(
            select(func.count()).select_from(LinkLead).where(_scored(version), _labelled())
        )
        or 0
    )


def reading_refusal(
    session: Session,
    *,
    version: int,
    min_labels: int,
    pass_above: float | None,
    reject_below: float | None,
) -> str | None:
    """Why no lead may be read yet, or None when triage has been measured: enough leads
    are labelled at the current version, and both thresholds are set."""
    labels = labels_at_version(session, version)
    if labels < min_labels:
        return (
            f"Triage has not been measured yet: {labels} of the {min_labels} labels needed "
            f"exist at version {version} of triage, so {min_labels - labels} more are "
            "needed. Draw leads with `thenwhat backfill sample-leads` and label them with "
            "`thenwhat backfill label-lead` or `label-leads`."
        )
    unset = [
        name
        for name, value in (("LEAD_PASS_ABOVE", pass_above), ("LEAD_REJECT_BELOW", reject_below))
        if value is None
    ]
    if unset:
        return (
            f"{' and '.join(unset)} {'is' if len(unset) == 1 else 'are'} not set. Read "
            "`thenwhat backfill evaluate-leads` and set both thresholds before reading."
        )
    return None
