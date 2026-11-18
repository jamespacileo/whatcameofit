"""Domain vocabulary shared by every package. Terms are defined in GLOSSARY.md.

This module must stay free of database, network and clock imports so that the
pure status rules can depend on it.
"""

from enum import StrEnum


class ReviewState(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Decider(StrEnum):
    HUMAN = "human"
    RULE = "rule"
    # Loaded as already reviewed from a checked-in seed file. Not an operator's decision.
    SEED = "seed"
    # Decided by an AI assistant working through the review queue. Not an operator's
    # decision: the claim is still published, and the export marks it as not checked by
    # a person.
    ASSISTANT = "assistant"


class EntityType(StrEnum):
    INTERVENTION = "intervention"
    PAPER = "paper"
    PERSON = "person"
    INSTITUTION = "institution"
    COMPANY = "company"


class NamedBy(StrEnum):
    """Where an entity's name came from: a source article, a registry record (a trial's
    lead sponsor), or both."""

    ARTICLE = "article"
    REGISTRY = "registry"


class DraftedFrom(StrEnum):
    """What a claim was drafted from: a news article, registry records, or an operator's
    entry. Set once when the claim is drafted and never changed after (openspec claims).
    Empty for a claim stored before it was recorded."""

    ARTICLE = "article"
    REGISTRY = "registry"
    OPERATOR = "operator"


class TermRole(StrEnum):
    """What a subject term is proposed as for a claim."""

    CONDITION = "condition"
    INTERVENTION = "intervention"
    # A gene named in the intervention, proposed as what it acts on or is made from.
    TARGET = "target"
    # A drug source's record of the intervention, found by its own name. Not scored.
    DRUG = "drug"


class TermFit(StrEnum):
    """How a subject term fits the claim: the thing itself, broader than it, or the
    kind of intervention it is. The order is the order a card is chosen in."""

    EXACT = "exact"
    BROADER = "broader"
    KIND = "kind"


class StatementKind(StrEnum):
    """What a reported statement is about (openspec reported-statements)."""

    EFFECT = "effect"
    SAFETY = "safety"
    HOW_IT_WORKS = "how_it_works"
    WHO_IT_COULD_HELP = "who_it_could_help"
    # Compared with an existing treatment.
    COMPARISON = "comparison"
    WHAT_IT_COULD_LEAD_TO = "what_it_could_lead_to"


class StatementFirmness(StrEnum):
    """How firmly the article puts a reported statement."""

    FACT = "fact"
    POSSIBILITY = "possibility"


class StatementSpeaker(StrEnum):
    """Who the article has saying a reported statement: a role, never a name."""

    ARTICLE = "article"
    RESEARCHER = "researcher"
    COMPANY = "company"
    PATIENT = "patient"
    OTHER_EXPERT = "other_expert"


class StatementBasis(StrEnum):
    """What the article says a reported statement rests on. The article's word, not a
    registry's or a paper's."""

    PEOPLE = "people"
    ANIMALS = "animals"
    LABORATORY = "laboratory"
    NOT_SAID = "not_said"


class ReadingKind(StrEnum):
    """What a record reading says of a planned primary outcome (openspec record-readings)."""

    # How long after the start the outcome is measured: a number with a unit.
    FOLLOW_UP = "follow_up"
    # What kind of measure the outcome's title names: a code.
    MEASURE = "measure"


class ReadingField(StrEnum):
    """The field of a planned primary outcome a reading's words are read from."""

    TIME_FRAME = "time_frame"
    MEASURE = "measure"


class MeasureCode(StrEnum):
    """The kinds of measure a reading may give. The site words each one; adding a code
    is a change to its wording table too (docs/adr/0003)."""

    SYMPTOM_SCORE = "symptom_score"
    # How often something happens.
    FREQUENCY = "frequency"
    # A body measurement or a laboratory value.
    BODY_MEASURE = "body_measure"
    # A scan or image finding.
    SCAN_FINDING = "scan_finding"
    # Survival, or time to an event.
    SURVIVAL = "survival"
    SIDE_EFFECTS = "side_effects"
    USE_OF_TREATMENT = "use_of_treatment"
    # A timed or scored test of what the body can do: walking, grip, balance.
    PHYSICAL_TEST = "physical_test"
    QUALITY_OF_LIFE = "quality_of_life"
    OTHER = "other"


class FollowUpUnit(StrEnum):
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    YEARS = "years"


class ReadBy(StrEnum):
    """Who decided a record reading. Always a model, checked by rule: never a person,
    and not one of the review deciders."""

    MODEL = "model"


class EventType(StrEnum):
    FOLLOWUP_PAPER = "followup_paper"
    TRIAL_REGISTERED = "trial_registered"
    TRIAL_STATUS_CHANGE = "trial_status_change"
    TRIAL_RESULTS_POSTED = "trial_results_posted"
    GRANT_AWARDED = "grant_awarded"
    COMPANY_EVENT = "company_event"
    RETRACTION = "retraction"
    REGULATORY_DECISION = "regulatory_decision"


# The event types that are about a trial.
TRIAL_EVENT_TYPES = frozenset(
    {
        EventType.TRIAL_REGISTERED,
        EventType.TRIAL_STATUS_CHANGE,
        EventType.TRIAL_RESULTS_POSTED,
    }
)


class TrialState(StrEnum):
    STARTED = "started"
    COMPLETED = "completed"
    TERMINATED = "terminated"
    WITHDRAWN = "withdrawn"
    SUSPENDED = "suspended"


class TrialPhase(StrEnum):
    """Phases as stored on trial events, whatever spelling the registry uses."""

    EARLY_PHASE_1 = "early_phase_1"
    PHASE_1 = "phase_1"
    PHASE_2 = "phase_2"
    PHASE_3 = "phase_3"
    PHASE_4 = "phase_4"
    NOT_APPLICABLE = "not_applicable"


class RegulatoryOutcome(StrEnum):
    APPROVED = "approved"
    REFUSED = "refused"


class ClaimStatus(StrEnum):
    PRECLINICAL_ONLY = "preclinical_only"
    # First reported from a study in people, with no trial found in the registries checked.
    NO_TRIAL_FOUND = "no_trial_found"
    TRIAL_REGISTERED = "trial_registered"
    PHASE_1 = "phase_1"
    PHASE_2 = "phase_2"
    PHASE_3 = "phase_3"
    APPROVED = "approved"
    FAILED = "failed"
    TERMINATED = "terminated"
    RETRACTED = "retracted"


class EvidenceStage(StrEnum):
    IN_VITRO = "in_vitro"
    ANIMAL = "animal"
    EARLY_HUMAN = "early_human"
    LATE_HUMAN = "late_human"


class WorkOutcome(StrEnum):
    """How a step ended for one record. Nothing found is finished work, not a failure.
    Later and needs a fix are not finished: the first comes back by itself once its time
    has passed, the second waits to be made due (openspec work-ledger)."""

    DONE = "done"
    NOTHING_FOUND = "nothing_found"
    LATER = "later"
    NEEDS_FIX = "needs_fix"
    FAILED = "failed"


class OutletKind(StrEnum):
    """What kind of outlet an article lead is from, set by rule from its domain."""

    GENERAL_NEWS = "general_news"
    TRADE_PRESS = "trade_press"
    PRESS_RELEASE = "press_release"
    UNKNOWN = "unknown"


class ScreenOutcome(StrEnum):
    """What screening found for a link lead, by rule and from stored data alone."""

    IN_SCOPE = "in_scope"
    UNLISTED_OUTLET = "unlisted_outlet"
    ALREADY_TRACKED = "already_tracked"


class LeadVerdict(StrEnum):
    """What a link lead's headline is: the options triage chooses between, and the
    labels a person can give."""

    TREATMENT_REPORT = "treatment_report"
    HEALTH_OTHER = "health_other"
    NOT_HEALTH = "not_health"


class ReadOutcome(StrEnum):
    """What became of a link lead whose article was to be read."""

    ADDED_TO_CLAIM = "added_to_claim"
    NEW_CLAIM = "new_claim"
    CANNOT_BE_READ = "cannot_be_read"
    NEEDS_VERTICAL = "needs_vertical"
    ENOUGH_ARTICLES = "enough_articles"
    # Read, and not about one treatment for one condition: no claim was made.
    NOT_ONE_TREATMENT = "not_one_treatment"
    # Read, on a topic, and about a treatment's business, not what it does: no claim made.
    BUSINESS_NEWS = "business_news"
    # Read, but equal names did not establish the same product and condition.
    IDENTITY_UNRESOLVED = "identity_unresolved"
