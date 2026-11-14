"""How well triage separates link leads that report a treatment from those that do
not, measured on labels the operator gives a sample. Behavior: openspec lead-evaluation.

A label belongs to the lead, not to one triage answer, so it holds for every later
version of triage. Only a person's labels enter the figures and open the gate to
reading; an assistant's are counted apart.
"""

from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import ColumnElement, and_, exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from thenwhat.backfill.errors import BackfillError
from thenwhat.db.models import LinkLead, LinkLeadLabel, LinkShare
from thenwhat.domain import Decider, LeadVerdict, ScreenOutcome

TENTHS = 10
THRESHOLDS = tuple(tenth / TENTHS for tenth in range(1, TENTHS))
DISAGREEMENTS_SHOWN = 10


class UnknownLabel(BackfillError):
    """The label given is not one of the triage options."""


class UnknownLead(BackfillError):
    """No link lead has the id given."""


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


def _shared_on(platform: str) -> ColumnElement[bool]:
    return exists().where(LinkShare.link_lead_id == LinkLead.id, LinkShare.platform == platform)


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


def sample_leads(session: Session, *, size: int, seed: str, version: int) -> Sample:
    """Draw unlabelled scored leads in equal numbers from each tenth of the score range,
    spread across platforms. The same seed draws the same sample."""
    per_tenth = max(size // TENTHS, 1)
    sample = Sample(per_tenth=per_tenth)
    platforms = list(session.scalars(select(LinkShare.platform).distinct().order_by("platform")))
    for tenth in range(TENTHS):
        chosen: dict[int, LinkLead] = {}
        drawn = {
            platform: list(
                session.scalars(
                    select(LinkLead)
                    .where(
                        _scored(version),
                        _in_tenth(tenth),
                        ~_labelled_by(Decider.HUMAN),
                        _shared_on(platform),
                    )
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
    return sample


# --- labelling -----------------------------------------------------------------------


def label_lead(
    session: Session, lead_id: int, label: str, *, by: Decider, now: datetime
) -> LinkLeadLabel:
    """Record what a lead's headline is, as a person or an assistant says. One label per
    lead from each: a second one from the same kind of labeller replaces the first."""
    options = [verdict.value for verdict in LeadVerdict]
    if label not in options:
        raise UnknownLabel(f"'{label}' is not a label. Labels: {', '.join(options)}.")
    if session.get(LinkLead, lead_id) is None:
        raise UnknownLead(f"No link lead has the id {lead_id}.")
    session.execute(
        insert(LinkLeadLabel)
        .values(link_lead_id=lead_id, label=LeadVerdict(label), labelled_by=by, labelled_at=now)
        .on_conflict_do_update(
            constraint="uq_link_lead_label_lead_by",
            set_={"label": LeadVerdict(label), "labelled_at": now},
        )
    )
    session.flush()
    return session.scalars(
        select(LinkLeadLabel).where(
            LinkLeadLabel.link_lead_id == lead_id, LinkLeadLabel.labelled_by == by
        )
    ).one()


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
    # Leads with an assistant's label and no person's: counted, never in the figures.
    assistant_only: int


def _figures(session: Session, version: int, only: ColumnElement[bool] | None = None) -> Figures:
    """Precision and recall at each threshold, each tenth weighted by how many scored
    leads it holds: the sample takes equal numbers from each tenth, the leads do not."""
    conditions = [_scored(version)] if only is None else [_scored(version), only]
    scored = [0] * TENTHS
    for score in session.scalars(select(LinkLead.triage_score).where(*conditions)):
        scored[tenth_of(score or 0.0)] += 1
    labelled = [0] * TENTHS
    positive = [0] * TENTHS
    for score, label in session.execute(
        select(LinkLead.triage_score, LinkLeadLabel.label)
        .join(LinkLeadLabel, LinkLeadLabel.link_lead_id == LinkLead.id)
        .where(*conditions, LinkLeadLabel.labelled_by == Decider.HUMAN)
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
    """The evaluation of the current version of triage on the leads a person has labelled."""
    platforms = list(session.scalars(select(LinkShare.platform).distinct().order_by("platform")))
    rows = session.execute(
        select(LinkLead.id, LinkLead.title, LinkLead.triage_score, LinkLeadLabel.label)
        .join(LinkLeadLabel, LinkLeadLabel.link_lead_id == LinkLead.id)
        .where(_scored(version), LinkLeadLabel.labelled_by == Decider.HUMAN)
    ).all()

    def distance(row) -> float:
        return abs(row.triage_score - (1.0 if row.label is LeadVerdict.TREATMENT_REPORT else 0.0))

    furthest = sorted(rows, key=lambda row: (-distance(row), row.id))[:DISAGREEMENTS_SHOWN]
    assistant_only = session.scalar(
        select(func.count())
        .select_from(LinkLead)
        .where(_labelled_by(Decider.ASSISTANT), ~_labelled_by(Decider.HUMAN))
    )
    return Evaluation(
        overall=_figures(session, version),
        by_platform={
            platform: _figures(session, version, _shared_on(platform)) for platform in platforms
        },
        disagreements=[
            Disagreement(row.id, row.title, row.triage_score, row.label)
            for row in furthest
            if distance(row) >= 0.5
        ],
        assistant_only=assistant_only or 0,
    )


# --- the gate ------------------------------------------------------------------------


def labels_at_version(session: Session, version: int) -> int:
    """How many leads have a person's label and a score from this version of triage."""
    return (
        session.scalar(
            select(func.count())
            .select_from(LinkLead)
            .where(_scored(version), _labelled_by(Decider.HUMAN))
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
    carry a person's label at the current version, and both thresholds are set."""
    labels = labels_at_version(session, version)
    if labels < min_labels:
        return (
            f"Triage has not been measured yet: {labels} of the {min_labels} labels needed "
            f"exist at version {version} of triage, so {min_labels - labels} more are "
            "needed. Draw leads with `thenwhat backfill sample-leads` and label them with "
            "`thenwhat backfill label-lead`."
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
