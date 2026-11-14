"""What one ClinicalTrials.gov record says of its trial. Pure. Behavior: openspec trial-facts.

Each fact is one field of the record read by a fixed rule, so a reader who opens the
record finds it there. A field the record does not hold, or holds in an unexpected
shape, gives an absent fact and never an error; nothing is inferred.

Free text that can state a conclusion is never read: the study's descriptions, outcome
descriptions, results group and population descriptions, and every comment on a
comparison. Nor are eligibility criteria, locations, contacts or the responsible
party's name. Registry numbers stay strings exactly as the registry wrote them.
"""

from dataclasses import dataclass
from typing import Any, Literal

from thenwhat.domain import TrialState

TrialStateCode = Literal[
    "not_started", "under_way", "completed", "suspended", "terminated", "withdrawn", "unknown"
]
StudyKind = Literal["interventional", "observational", "expanded_access"]
ParticipantBasis = Literal["actual", "planned"]
Allocation = Literal["randomised", "non_randomised"]
Masking = Literal["none", "single", "double", "triple", "quadruple"]
Comparator = Literal["placebo", "sham", "active", "no_treatment"]
AgeGroup = Literal["child", "adult", "older_adult"]
SponsorKind = Literal["industry", "government", "individual", "network", "other"]
MeasureKind = Literal[
    "mean",
    "median",
    "number",
    "count_of_participants",
    "count_of_units",
    "geometric_mean",
    "least_squares_mean",
    "geometric_least_squares_mean",
    "log_mean",
]
TestKind = Literal["superiority", "non_inferiority", "equivalence"]

# At most this many planned and this many posted primary outcomes are carried.
OUTCOMES_SHOWN = 3

# The registry's recruiting states all become "under_way": a trial is never presented
# as open to participants. Any other registry status is "unknown".
STATES: dict[str, TrialStateCode] = {
    "NOT_YET_RECRUITING": "not_started",
    "RECRUITING": "under_way",
    "ENROLLING_BY_INVITATION": "under_way",
    "ACTIVE_NOT_RECRUITING": "under_way",
    "COMPLETED": "completed",
    "SUSPENDED": "suspended",
    "TERMINATED": "terminated",
    "WITHDRAWN": "withdrawn",
}
# For a trial with no registry record: the state its newest status-change event reports.
REPORTED_STATES: dict[TrialState, TrialStateCode] = {
    TrialState.STARTED: "under_way",
    TrialState.COMPLETED: "completed",
    TrialState.SUSPENDED: "suspended",
    TrialState.TERMINATED: "terminated",
    TrialState.WITHDRAWN: "withdrawn",
}
STUDY_KINDS: dict[str, StudyKind] = {
    "INTERVENTIONAL": "interventional",
    "OBSERVATIONAL": "observational",
    "EXPANDED_ACCESS": "expanded_access",
}
BASES: dict[str, ParticipantBasis] = {"ACTUAL": "actual", "ESTIMATED": "planned"}
# The registry's "NA" (one arm, nothing to allocate) gives no allocation.
ALLOCATIONS: dict[str, Allocation] = {
    "RANDOMIZED": "randomised",
    "NON_RANDOMIZED": "non_randomised",
}
MASKINGS: dict[str, Masking] = {
    "NONE": "none",
    "SINGLE": "single",
    "DOUBLE": "double",
    "TRIPLE": "triple",
    "QUADRUPLE": "quadruple",
}
# In the order the comparators are listed.
COMPARATORS: dict[str, Comparator] = {
    "PLACEBO_COMPARATOR": "placebo",
    "SHAM_COMPARATOR": "sham",
    "ACTIVE_COMPARATOR": "active",
    "NO_INTERVENTION": "no_treatment",
}
# In the order the age groups are listed.
AGE_GROUPS: dict[str, AgeGroup] = {"CHILD": "child", "ADULT": "adult", "OLDER_ADULT": "older_adult"}
# The class INDIV is not here: a person is caught before the class is read (`_sponsor`).
SPONSOR_KINDS: dict[str, SponsorKind] = {
    "INDUSTRY": "industry",
    "NIH": "government",
    "FED": "government",
    "OTHER_GOV": "government",
    "NETWORK": "network",
    "OTHER": "other",
}
MEASURE_KINDS: dict[str, MeasureKind] = {
    "MEAN": "mean",
    "MEDIAN": "median",
    "NUMBER": "number",
    "COUNT_OF_PARTICIPANTS": "count_of_participants",
    "COUNT_OF_UNITS": "count_of_units",
    "GEOMETRIC_MEAN": "geometric_mean",
    "LEAST_SQUARES_MEAN": "least_squares_mean",
    "GEOMETRIC_LEAST_SQUARES_MEAN": "geometric_least_squares_mean",
    "LOG_MEAN": "log_mean",
}
TEST_KINDS: dict[str, TestKind] = {
    "SUPERIORITY": "superiority",
    "NON_INFERIORITY": "non_inferiority",
    "EQUIVALENCE": "equivalence",
}


@dataclass(frozen=True, slots=True)
class Participants:
    count: int
    basis: ParticipantBasis


@dataclass(frozen=True, slots=True)
class Sponsor:
    # None when the sponsor is a person: the site holds no personal data.
    name: str | None
    kind: SponsorKind | None


@dataclass(frozen=True, slots=True)
class PlannedOutcome:
    measure: str
    time_frame: str | None


@dataclass(frozen=True, slots=True)
class ResultGroup:
    title: str
    analysed: str | None
    value: str | None
    spread: str | None
    lower: str | None
    upper: str | None


@dataclass(frozen=True, slots=True)
class Comparison:
    # The titles of the groups compared.
    groups: tuple[str, ...]
    p_value: str | None
    method: str | None
    test: TestKind | None


@dataclass(frozen=True, slots=True)
class ResultOutcome:
    title: str
    time_frame: str | None
    unit: str | None
    measure: MeasureKind | None
    # The registry's own words, such as "Standard Deviation".
    spread_kind: str | None
    # Values are carried only for an outcome reported in one row.
    rows: int
    groups: tuple[ResultGroup, ...]
    comparisons: tuple[Comparison, ...]


@dataclass(frozen=True, slots=True)
class Results:
    outcomes: tuple[ResultOutcome, ...]
    outcomes_total: int


@dataclass(frozen=True, slots=True)
class TrialFacts:
    study_kind: StudyKind | None
    participants: Participants | None
    allocation: Allocation | None
    masking: Masking | None
    comparators: tuple[Comparator, ...]
    healthy_volunteers: bool | None
    age_groups: tuple[AgeGroup, ...]
    sponsor: Sponsor | None
    primary_outcomes: tuple[PlannedOutcome, ...]
    primary_outcomes_total: int
    why_stopped: str | None
    results: Results | None


@dataclass(frozen=True, slots=True)
class RegistryTrial:
    """What a registry record says of its trial: its title, its state and its facts."""

    title: str | None
    state: TrialStateCode
    facts: TrialFacts


def is_registry_record(payload: Any) -> bool:
    """Whether a stored payload is a ClinicalTrials.gov record, rather than the details
    an operator entered by hand."""
    return isinstance(payload, dict) and isinstance(payload.get("protocolSection"), dict)


def read_trial(study: dict[str, Any]) -> RegistryTrial:
    protocol = _object(study, "protocolSection")
    status = _object(protocol, "statusModule")
    design = _object(protocol, "designModule")
    design_info = _object(design, "designInfo")
    eligibility = _object(protocol, "eligibilityModule")
    arm_types = {
        _text(arm, "type") for arm in _objects(protocol, "armsInterventionsModule", "armGroups")
    }
    ages = set(_strings(eligibility, "stdAges"))
    healthy = eligibility.get("healthyVolunteers")
    planned = [
        PlannedOutcome(measure, _text(outcome, "timeFrame"))
        for outcome in _objects(protocol, "outcomesModule", "primaryOutcomes")
        if (measure := _text(outcome, "measure"))
    ]
    return RegistryTrial(
        title=_text(_object(protocol, "identificationModule"), "briefTitle"),
        state=_code(STATES, status.get("overallStatus")) or "unknown",
        facts=TrialFacts(
            study_kind=_code(STUDY_KINDS, design.get("studyType")),
            participants=_participants(_object(design, "enrollmentInfo")),
            allocation=_code(ALLOCATIONS, design_info.get("allocation")),
            masking=_code(MASKINGS, _object(design_info, "maskingInfo").get("masking")),
            comparators=_comparators(arm_types),
            healthy_volunteers=healthy if isinstance(healthy, bool) else None,
            age_groups=tuple(code for age, code in AGE_GROUPS.items() if age in ages),
            sponsor=_sponsor(_object(protocol, "sponsorCollaboratorsModule")),
            primary_outcomes=tuple(planned[:OUTCOMES_SHOWN]),
            primary_outcomes_total=len(planned),
            why_stopped=_text(status, "whyStopped"),
            results=_results(study),
        ),
    )


def reported_state(state: TrialState | None) -> TrialStateCode:
    """The state of a trial with no registry record, from the state its newest
    status-change event reports; one with no status change has not started."""
    return "not_started" if state is None else REPORTED_STATES[state]


def _comparators(arm_types: set[str | None]) -> tuple[Comparator, ...]:
    """The kinds of comparator among a trial's arms, in a fixed order.

    Records often class the arm that gets the treatment as an "active comparator" beside
    a placebo arm. That arm is a comparator only when the record also has an
    experimental arm for it to be compared with; otherwise it is left out.
    """
    return tuple(
        code
        for kind, code in COMPARATORS.items()
        if kind in arm_types and (kind != "ACTIVE_COMPARATOR" or "EXPERIMENTAL" in arm_types)
    )


def _participants(enrolment: dict[str, Any]) -> Participants | None:
    count = enrolment.get("count")
    basis = _code(BASES, enrolment.get("type"))
    if basis is None or not isinstance(count, int) or isinstance(count, bool) or count < 0:
        return None
    return Participants(count, basis)


def _sponsor(module: dict[str, Any]) -> Sponsor | None:
    """The lead sponsor, or None when the record names none.

    A sponsor is a person when the registry classes it as an individual or when the
    responsible party is a sponsor-investigator: the registry often classes such a
    person as "other". A person's name is not carried, and nor is any affiliation.
    """
    lead = module.get("leadSponsor")
    if not isinstance(lead, dict):
        return None
    if (
        lead.get("class") == "INDIV"
        or _object(module, "responsibleParty").get("type") == "SPONSOR_INVESTIGATOR"
    ):
        return Sponsor(name=None, kind="individual")
    name, kind = _text(lead, "name"), _code(SPONSOR_KINDS, lead.get("class"))
    return None if name is None and kind is None else Sponsor(name, kind)


def _results(study: dict[str, Any]) -> Results | None:
    """Posted results for primary outcomes, or None when the record posts none."""
    posted = [
        measure
        for measure in _objects(study, "resultsSection", "outcomeMeasuresModule", "outcomeMeasures")
        if measure.get("type") == "PRIMARY"
        and measure.get("reportingStatus") == "POSTED"
        and _text(measure, "title")
    ]
    if not posted:
        return None
    return Results(
        outcomes=tuple(_outcome(measure) for measure in posted[:OUTCOMES_SHOWN]),
        outcomes_total=len(posted),
    )


def _outcome(measure: dict[str, Any]) -> ResultOutcome:
    categories = [
        category
        for row_class in _objects(measure, "classes")
        for category in _objects(row_class, "categories")
    ]
    groups: tuple[ResultGroup, ...] = ()
    comparisons: tuple[Comparison, ...] = ()
    if len(categories) == 1:
        titles: dict[str, str] = {}  # group id to title, in the record's order
        for group in _objects(measure, "groups"):
            group_id, title = _text(group, "id"), _text(group, "title")
            if group_id and title:
                titles[group_id] = title
        values = _by_group(_objects(categories[0], "measurements"))
        denoms = _objects(measure, "denoms")
        analysed = _by_group(_objects(denoms[0], "counts")) if denoms else {}
        groups = tuple(
            ResultGroup(
                title=title,
                analysed=_text(analysed.get(group_id, {}), "value"),
                value=_text(values.get(group_id, {}), "value"),
                spread=_text(values.get(group_id, {}), "spread"),
                lower=_text(values.get(group_id, {}), "lowerLimit"),
                upper=_text(values.get(group_id, {}), "upperLimit"),
            )
            for group_id, title in titles.items()
        )
        comparisons = tuple(
            Comparison(
                groups=tuple(
                    titles[group_id]
                    for group_id in _strings(analysis, "groupIds")
                    if group_id in titles
                ),
                p_value=_text(analysis, "pValue"),
                method=_text(analysis, "statisticalMethod"),
                test=_code(TEST_KINDS, analysis.get("nonInferiorityType")),
            )
            for analysis in _objects(measure, "analyses")
        )
    return ResultOutcome(
        title=measure["title"],
        time_frame=_text(measure, "timeFrame"),
        unit=_text(measure, "unitOfMeasure"),
        measure=_code(MEASURE_KINDS, measure.get("paramType")),
        spread_kind=_text(measure, "dispersionType"),
        rows=len(categories),
        groups=groups,
        comparisons=comparisons,
    )


# --- tolerant reads: a missing or oddly shaped field reads as absent ------------------


def _object(value: Any, *path: str) -> dict[str, Any]:
    """The object at `path` inside `value`, or an empty one."""
    for key in path:
        value = value.get(key) if isinstance(value, dict) else None
    return value if isinstance(value, dict) else {}


def _objects(value: Any, *path: str) -> list[dict[str, Any]]:
    """The objects in the list at `path` inside `value`, skipping anything else."""
    items = _object(value, *path[:-1]).get(path[-1])
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _strings(value: dict[str, Any], key: str) -> list[str]:
    items = value.get(key)
    return [item for item in items if isinstance(item, str)] if isinstance(items, list) else []


def _text(value: dict[str, Any], key: str) -> str | None:
    """The registry's text as written, or None when it is missing or blank."""
    text = value.get(key)
    return text if isinstance(text, str) and text.strip() else None


def _code[T](codes: dict[str, T], value: Any) -> T | None:
    return codes.get(value) if isinstance(value, str) else None


def _by_group(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Registry entries keyed by the group they belong to; the first entry wins."""
    found: dict[str, dict[str, Any]] = {}
    for entry in entries:
        group_id = entry.get("groupId")
        if isinstance(group_id, str):
            found.setdefault(group_id, entry)
    return found
