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
