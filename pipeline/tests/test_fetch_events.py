"""Creating evidence events, tested through `fetch_claim` and `add_manual_event`
with fake registries on a real database. Scenario names are from openspec evidence-events."""

import copy
from datetime import UTC, date, datetime
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entities import add_entity, entities_of, set_origin_paper
from thenwhat.claims.entry import InvalidField, InvalidUrl, MissingField, add_claim
from thenwhat.claims.status import refresh_status
from thenwhat.db.models import Claim, EntityMatch, EvidenceEvent
from thenwhat.domain import (
    ClaimStatus,
    Decider,
    EntityType,
    EventType,
    RegulatoryOutcome,
    ReviewState,
    TrialPhase,
    TrialState,
)
from thenwhat.events.fetch import fetch_claim
from thenwhat.events.manual import DuplicateEvent, add_manual_event
from thenwhat.review.decisions import record_decision
from thenwhat.sources.base import SourceRecord
from thenwhat.sources.crossref import Notice

NOW = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
ORIGIN_DOI = "10.1000/origin"
NCT = "NCT02586935"


# --- fake registries ---------------------------------------------------------------


class Trials:
    def __init__(self, studies: dict[str, dict[str, Any]]) -> None:
        self.studies = studies

    def fetch_trial(self, nct_id: str) -> SourceRecord | None:
        study = self.studies.get(nct_id)
        if study is None:
            return None
        url = f"https://clinicaltrials.gov/study/{nct_id}"
        return SourceRecord("clinicaltrials.gov", nct_id, url, study, NOW)


def paper(doi: str, title: str, authors: list[str], abstract: str = "", on: str = "2020-05-01"):
    payload = {
        "id": doi.rsplit("/", 1)[-1],
        "source": "MED",
        "doi": doi,
        "title": title,
        "abstractText": abstract,
        "firstPublicationDate": on,
        "authorList": {"author": [{"fullName": name} for name in authors]},
    }
    return SourceRecord(
        "europepmc", doi, f"https://europepmc.org/article/MED/{payload['id']}", payload, NOW
    )


ORIGIN = paper(
    ORIGIN_DOI, "An antibody restores teeth in mice", ["Example A", "Sample B"], on="2018-03-01"
)


class Literature:
    def __init__(self, citing: list[SourceRecord], origin: SourceRecord | None = ORIGIN) -> None:
        self.citing = citing
        self.origin = origin

    def paper(self, doi: str) -> SourceRecord | None:
        return self.origin if self.origin and doi.lower() == ORIGIN_DOI else None

    def citing_papers(self, paper: SourceRecord) -> list[SourceRecord]:
        return self.citing


class Notices:
    def __init__(self, notices: dict[str, list[Notice]] | None = None) -> None:
        self.by_doi = notices or {}

    def notices(self, doi: str) -> list[Notice]:
        return self.by_doi.get(doi.lower(), [])


# --- claims with approved or pending matches ------------------------------------------


def new_claim(session: Session) -> Claim:
    return add_claim(
        session,
        slug="tooth-regrowth-ex1",
        headline="Antibody regrows teeth in mice",
        vertical="mouth-and-teeth",
        intervention="EX-1 antibody",
        indication="tooth agenesis",
    )


def add_match(session: Session, entity, source: str, external_id: str, approved: bool = True):
    match = EntityMatch(entity_id=entity.id, source_name=source, external_id=external_id, score=0.9)
    session.add(match)
    session.flush()
    if approved:
        record_decision(match, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
        session.flush()
    return match


def with_trial(session: Session, claim: Claim, approved: bool = True):
    intervention = entities_of(session, claim)[0]
    return add_match(session, intervention, "clinicaltrials.gov", NCT, approved)


def with_origin_paper(session: Session, claim: Claim, approved: bool = True):
    origin = add_entity(session, claim.slug, type=EntityType.PAPER, name="Origin", doi=ORIGIN_DOI)
    set_origin_paper(session, claim.slug, "Origin")
    return add_match(session, origin, "crossref", ORIGIN_DOI, approved)


def fetch(session: Session, claim: Claim, *, trials=None, literature=None, notices=None, **options):
    options.setdefault("threshold", 0.95)
    return fetch_claim(
        session,
        claim,
        trials=trials or Trials({}),
        literature=literature or Literature([]),
        notices=notices or Notices(),
        now=NOW,
        **options,
    )


def events(session: Session, type: EventType | None = None) -> list[EvidenceEvent]:
    query = select(EvidenceEvent).order_by(EvidenceEvent.event_date, EvidenceEvent.id)
    return [event for event in session.scalars(query) if type is None or event.type is type]


@pytest.fixture
def study(fixture_json) -> dict[str, Any]:
    return copy.deepcopy(fixture_json("clinicaltrials/study_NCT02586935.json"))


# --- trial events ------------------------------------------------------------------


def test_pending_match_produces_no_trial_events(session: Session, study):
    """Scenario: Pending match"""
    claim = new_claim(session)
    with_trial(session, claim, approved=False)

    fetch(session, claim, trials=Trials({NCT: study}))

    assert events(session) == []


def test_trial_event_from_an_approved_match_is_approved_by_rule(session: Session, study):
    """Scenario: Trial event from an approved match"""
    claim = new_claim(session)
    match = with_trial(session, claim)

    created = fetch(session, claim, trials=Trials({NCT: study}))

    assert len(created) == 3
    for event in events(session):
        assert (event.review_state, event.reviewed_by, event.reviewed_at) == (
            ReviewState.APPROVED,
            Decider.RULE,
            NOW,
        )
        assert event.entity_match_id == match.id
        assert event.raw_payload == study and event.fetched_at == NOW
    assert events(session)[0].trial_phases == [TrialPhase.PHASE_2.value]


def test_fetch_updates_the_claims_status(session: Session, study):
    claim = new_claim(session)
    with_trial(session, claim)

    fetch(session, claim, trials=Trials({NCT: study}))

    assert claim.current_status is ClaimStatus.PHASE_2
    assert claim.status_updated_at == NOW


def test_threshold_above_one_sends_every_event_to_review(session: Session, study):
    claim = new_claim(session)
    with_trial(session, claim)

    fetch(session, claim, trials=Trials({NCT: study}), threshold=1.01)

    assert {event.review_state for event in events(session)} == {ReviewState.PENDING}
    assert claim.current_status is ClaimStatus.PRECLINICAL_ONLY


def test_second_fetch_with_no_registry_change_creates_nothing(session: Session, study):
    """Scenario: Second fetch with no registry change"""
    claim = new_claim(session)
    with_trial(session, claim)
    fetch(session, claim, trials=Trials({NCT: study}))

    again = fetch(session, claim, trials=Trials({NCT: study}))

    assert again == []
    assert len(events(session)) == 3


def test_trial_the_registry_no_longer_has_is_skipped(session: Session):
    claim = new_claim(session)
    with_trial(session, claim)

    assert fetch(session, claim, trials=Trials({})) == []


# --- follow-up papers ----------------------------------------------------------------


def follow_ups(session: Session, citing: list[SourceRecord]) -> list[EvidenceEvent]:
    claim = new_claim(session)
    with_origin_paper(session, claim)
    fetch(session, claim, literature=Literature(citing))
    return events(session, EventType.FOLLOWUP_PAPER)


def test_citing_paper_from_the_same_group_is_a_follow_up(session: Session):
    """Scenario: Citing paper from the same group"""
    citing = paper("10.1000/later", "Further tooth results", ["Sample B", "Newcomer C"])

    [event] = follow_ups(session, [citing])

    assert (event.external_id, event.summary) == ("10.1000/later", "Further tooth results")
    assert (event.event_date, event.source_name) == (date(2020, 5, 1), "europepmc")
    assert event.source_url == "https://europepmc.org/article/MED/later"
    assert event.raw_payload == citing.payload


def test_independent_paper_naming_the_intervention_is_a_follow_up(session: Session):
    """Scenario: Independent paper naming the intervention"""
    citing = paper(
        "10.1000/independent",
        "Replication in ferrets",
        ["Stranger D"],
        abstract="We gave the ex-1 antibody to ferrets.",
    )

    assert len(follow_ups(session, [citing])) == 1


def test_unrelated_citing_paper_is_not_a_follow_up(session: Session):
    """Scenario: Unrelated citing paper"""
    citing = paper(
        "10.1000/review", "A review of dental biology", ["Stranger D"], abstract="Teeth."
    )

    assert follow_ups(session, [citing]) == []


def test_claim_without_an_origin_paper_gets_no_follow_ups(session: Session):
    """Scenario: Claim without an origin paper"""
    claim = new_claim(session)
    citing = paper("10.1000/later", "Further tooth results", ["Sample B"])

    fetch(session, claim, literature=Literature([citing]))

    assert events(session) == []


def test_origin_paper_with_only_a_pending_match_gets_no_follow_ups(session: Session):
    claim = new_claim(session)
    with_origin_paper(session, claim, approved=False)
    citing = paper("10.1000/later", "Further tooth results", ["Sample B"])

    fetch(session, claim, literature=Literature([citing]))

    assert events(session) == []


def test_follow_up_paper_is_pending_whatever_its_confidence(session: Session):
    """Scenario: Follow-up paper"""
    both = paper("10.1000/both", "EX-1 antibody in dogs", ["Sample B"])
    one = paper("10.1000/one", "Further tooth results", ["Sample B"])

    created = follow_ups(session, [both, one])

    assert {event.review_state for event in created} == {ReviewState.PENDING}
    by_id = {event.external_id: event.confidence for event in created}
    assert by_id["10.1000/both"] > by_id["10.1000/one"]


def test_rejected_event_found_again_stays_rejected(session: Session):
    """Scenario: Rejected event found again"""
    citing = paper("10.1000/later", "Further tooth results", ["Sample B"])
    claim = new_claim(session)
    with_origin_paper(session, claim)
    fetch(session, claim, literature=Literature([citing]))
    [event] = events(session)
    record_decision(event, ReviewState.REJECTED, by=Decider.HUMAN, now=NOW)

    again = fetch(session, claim, literature=Literature([citing]))

    assert again == []
    assert [e.review_state for e in events(session)] == [ReviewState.REJECTED]


# --- retractions ---------------------------------------------------------------------


def test_origin_paper_retracted_creates_a_retraction_event(session: Session):
    """Scenario: Origin paper retracted"""
    claim = new_claim(session)
    with_origin_paper(session, claim)
    notice = Notice("retraction", date(2022, 4, 5), "10.1000/retraction-notice")

    fetch(session, claim, notices=Notices({ORIGIN_DOI: [notice]}))

    [event] = events(session, EventType.RETRACTION)
    assert (event.external_id, event.event_date) == (ORIGIN_DOI, date(2022, 4, 5))
    assert event.source_url == "https://doi.org/10.1000/retraction-notice"
    assert "An antibody restores teeth in mice" in event.summary
    assert event.review_state is ReviewState.APPROVED
    assert claim.current_status is ClaimStatus.RETRACTED


def test_correction_notice_is_not_a_retraction(session: Session):
    claim = new_claim(session)
    with_origin_paper(session, claim)
    notice = Notice("correction", date(2019, 1, 1), "10.1000/correction")

    fetch(session, claim, notices=Notices({ORIGIN_DOI: [notice]}))

    assert events(session, EventType.RETRACTION) == []


def test_retraction_of_a_follow_up_paper_is_recorded_without_changing_status(session: Session):
    claim = new_claim(session)
    with_origin_paper(session, claim)
    citing = paper("10.1000/later", "Further tooth results", ["Sample B"])
    notice = Notice("retraction", date(2023, 1, 9), "10.1000/notice")

    fetch(
        session,
        claim,
        literature=Literature([citing]),
        notices=Notices({"10.1000/later": [notice]}),
    )

    [event] = events(session, EventType.RETRACTION)
    assert event.external_id == "10.1000/later"
    assert claim.current_status is ClaimStatus.PRECLINICAL_ONLY


# --- manual events -------------------------------------------------------------------

REGULATOR = "https://regulator.example/notices/1"
JRCT = "https://jrct.example/latest-detail/jRCT2051240089"


def manual(session: Session, **overrides: Any) -> EvidenceEvent:
    claim = new_claim(session)
    values: dict[str, Any] = {
        "type": EventType.REGULATORY_DECISION,
        "event_date": date(2026, 3, 1),
        "source_url": REGULATOR,
        "summary": "Regulator approved the product.",
        "regulatory_outcome": RegulatoryOutcome.APPROVED,
    }
    return add_manual_event(session, claim.slug, now=NOW, **(values | overrides))


def test_regulatory_approval_entered_by_hand_is_stored_pending(session: Session):
    """Scenario: Regulatory approval entered by hand"""
    event = manual(session)

    assert (event.review_state, event.type) == (ReviewState.PENDING, EventType.REGULATORY_DECISION)
    assert event.fetched_at == NOW
    assert event.raw_payload["summary"] == "Regulator approved the product."
    assert event.raw_payload["source_url"] == REGULATOR


def test_refusal_is_recorded_with_its_outcome(session: Session):
    """Scenario: Refusal recorded"""
    event = manual(session, regulatory_outcome=RegulatoryOutcome.REFUSED)

    assert event.regulatory_outcome is RegulatoryOutcome.REFUSED


def test_regulatory_decision_without_an_outcome_is_refused(session: Session):
    """Scenario: Regulatory decision without an outcome"""
    with pytest.raises(MissingField, match="outcome"):
        manual(session, regulatory_outcome=None)


def test_event_without_a_source_link_is_refused(session: Session):
    """Scenario: Event without a source link"""
    with pytest.raises(InvalidUrl):
        manual(session, source_url="")


def test_trial_in_a_registry_with_no_client_counts_once_approved(session: Session):
    """Scenario: Trial in a registry with no client"""
    event = manual(
        session,
        type=EventType.TRIAL_REGISTERED,
        source_url=JRCT,
        source_name="jRCT",
        summary="Phase 1 trial registered in Japan.",
        external_id="jRCT2051240089",
        trial_phases=[TrialPhase.PHASE_1],
        regulatory_outcome=None,
    )
    claim = session.get(Claim, event.claim_id)
    assert claim is not None and event.review_state is ReviewState.PENDING

    record_decision(event, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    refresh_status(session, claim, as_of=NOW.date(), now=NOW)

    assert claim.current_status is ClaimStatus.TRIAL_REGISTERED
    assert (event.source_name, event.external_id) == ("jRCT", "jRCT2051240089")


def test_trial_event_without_an_identifier_is_refused(session: Session):
    """Scenario: Trial event without an identifier"""
    with pytest.raises(MissingField, match="identifier"):
        manual(
            session,
            type=EventType.TRIAL_REGISTERED,
            source_url=JRCT,
            trial_phases=[TrialPhase.PHASE_1],
            regulatory_outcome=None,
        )


def test_trial_event_without_a_phase_is_refused(session: Session):
    with pytest.raises(MissingField, match="phase"):
        manual(
            session,
            type=EventType.TRIAL_REGISTERED,
            source_url=JRCT,
            external_id="jRCT2051240089",
            regulatory_outcome=None,
        )


def test_status_change_must_say_which_state(session: Session):
    with pytest.raises(MissingField, match="state"):
        manual(
            session,
            type=EventType.TRIAL_STATUS_CHANGE,
            source_url=JRCT,
            external_id="jRCT2051240089",
            trial_phases=[TrialPhase.PHASE_1],
            regulatory_outcome=None,
        )


def test_details_that_do_not_belong_to_the_event_type_are_refused(session: Session):
    with pytest.raises(InvalidField):
        manual(session, trial_state=TrialState.STARTED)


def test_same_manual_event_entered_twice_is_refused(session: Session):
    event = manual(session)

    with pytest.raises(DuplicateEvent):
        add_manual_event(
            session,
            "tooth-regrowth-ex1",
            type=EventType.REGULATORY_DECISION,
            event_date=event.event_date,
            source_url=REGULATOR,
            summary="Entered again.",
            regulatory_outcome=RegulatoryOutcome.APPROVED,
            now=NOW,
        )
