"""Organisations a claim names (openspec organisations and its entity-resolution delta):
sponsors recorded at fetch, the approval rule, the review queue. Tested on the real test
database with recorded registry fixtures. Scenario names are from those specs."""

import copy
from datetime import UTC, date, datetime
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from thenwhat.claims.entities import entities_of, note_named_organisation
from thenwhat.claims.entry import add_article, add_claim
from thenwhat.db.models import Claim, Entity, EntityArticle, EntityMatch, OrganisationRecord
from thenwhat.domain import Decider, EntityType, NamedBy, ReviewState
from thenwhat.events.fetch import fetch_claim
from thenwhat.resolve.organisations import match_organisations
from thenwhat.review.decisions import record_decision
from thenwhat.review.queue import decide_item, pending_items
from thenwhat.sources.base import SourceRecord

NOW = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
LATER = datetime(2026, 11, 27, 10, 0, tzinfo=UTC)
SLUG = "tooth-regrowth-ex1"


def new_claim(session: Session) -> Claim:
    return add_claim(
        session,
        slug=SLUG,
        headline="Antibody regrows teeth in mice",
        vertical="mouth-and-teeth",
        intervention="EX-1 antibody",
        indication="tooth agenesis",
    )


def organisations(session: Session, claim: Claim) -> list[Entity]:
    return [
        entity
        for entity in entities_of(session, claim)
        if entity.type in (EntityType.INSTITUTION, EntityType.COMPANY)
    ]


# --- sponsors recorded at fetch -------------------------------------------------------


class Trials:
    def __init__(self, studies: dict[str, dict[str, Any]]) -> None:
        self.studies = studies

    def fetch_trial(self, nct_id: str) -> SourceRecord | None:
        study = self.studies.get(nct_id)
        if study is None:
            return None
        url = f"https://clinicaltrials.gov/study/{nct_id}"
        return SourceRecord("clinicaltrials.gov", nct_id, url, study, NOW)


class NoPapers:
    def paper(self, doi: str) -> SourceRecord | None:
        return None

    def paper_by_pubmed_id(self, pubmed_id: str) -> SourceRecord | None:
        return None

    def citing_papers(self, paper: SourceRecord) -> list[SourceRecord]:
        return []


class NoNotices:
    def notices(self, doi: str) -> list:
        return []


def with_trial(session: Session, claim: Claim, nct_id: str, *, approved: bool = True) -> None:
    intervention = entities_of(session, claim)[0]
    match = EntityMatch(
        entity_id=intervention.id,
        source_name="clinicaltrials.gov",
        external_id=nct_id,
        score=0.9,
    )
    session.add(match)
    session.flush()
    if approved:
        record_decision(match, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
        session.flush()


def fetch(session: Session, claim: Claim, studies: dict[str, dict[str, Any]]) -> None:
    fetch_claim(
        session,
        claim,
        trials=Trials(studies),
        literature=NoPapers(),
        notices=NoNotices(),
        threshold=0.95,
        now=NOW,
    )


def sponsored_by(study: dict[str, Any], name: str, sponsor_class: str) -> dict[str, Any]:
    changed = copy.deepcopy(study)
    module = changed["protocolSection"]["sponsorCollaboratorsModule"]
    module["leadSponsor"] = {"name": name, "class": sponsor_class}
    return changed


def test_industry_sponsor_no_report_named_becomes_a_company(session: Session, fixture_json):
    """Scenario: Industry sponsor not named in any report"""
    claim = new_claim(session)
    study = sponsored_by(
        fixture_json("clinicaltrials/study_NCT02586935.json"), "Example Pharma Ltd", "INDUSTRY"
    )
    with_trial(session, claim, "NCT02586935")

    fetch(session, claim, {"NCT02586935": study})

    [company] = organisations(session, claim)
    assert (company.type, company.name, company.named_by) == (
        EntityType.COMPANY,
        "Example Pharma Ltd",
        [NamedBy.REGISTRY],
    )
    # A second fetch records nothing new.
    fetch(session, claim, {"NCT02586935": study})
    assert [entity.id for entity in organisations(session, claim)] == [company.id]
    assert company.named_by == [NamedBy.REGISTRY]


def test_sponsor_the_report_also_named_is_one_entity_named_by_both(session: Session, fixture_json):
    """Scenario: Sponsor the report also named"""
    claim = new_claim(session)
    article = add_article(
        session,
        SLUG,
        url="https://example.org/news/ex1",
        outlet="Example News",
        title="Teeth regrown",
        published_date=date(2026, 1, 5),
    )
    named = note_named_organisation(
        session,
        claim,
        article,
        "Holland Bloorview Kids Rehabilitation Hospital",
        EntityType.INSTITUTION,
    )
    with_trial(session, claim, "NCT02586935")

    fetch(session, claim, {"NCT02586935": fixture_json("clinicaltrials/study_NCT02586935.json")})

    assert [entity.id for entity in organisations(session, claim)] == [named.id]
    assert named.named_by == [NamedBy.ARTICLE, NamedBy.REGISTRY]


def test_sponsor_who_is_a_person_is_not_recorded(session: Session, fixture_json):
    """Scenario: Sponsor who is a person (a sponsor-investigator classed "other")"""
    claim = new_claim(session)
    with_trial(session, claim, "NCT04951479")

    fetch(
        session,
        claim,
        {"NCT04951479": fixture_json("clinicaltrials/study_NCT04951479_comparison.json")},
    )

    assert organisations(session, claim) == []
    assert "Example Investigator" not in [entity.name for entity in entities_of(session, claim)]


def test_sponsor_of_a_trial_with_no_approved_events_is_not_recorded(session: Session, fixture_json):
    claim = new_claim(session)
    with_trial(session, claim, "NCT02586935", approved=False)

    fetch(session, claim, {"NCT02586935": fixture_json("clinicaltrials/study_NCT02586935.json")})

    assert organisations(session, claim) == []


def test_two_reports_naming_one_institution_give_one_entity_with_both_reports(
    session: Session,
):
    claim = new_claim(session)
    first, second = (
        add_article(
            session,
            SLUG,
            url=f"https://example.org/news/{n}",
            outlet="Example News",
            title="Teeth regrown",
            published_date=date(2026, 1, n),
        )
        for n in (5, 6)
    )
    one = note_named_organisation(session, claim, first, "Kyoto University", EntityType.INSTITUTION)
    two = note_named_organisation(session, claim, second, "kyoto university", EntityType.COMPANY)
    note_named_organisation(session, claim, second, "Kyoto University", EntityType.INSTITUTION)

    assert one is two
    assert one.named_by == [NamedBy.ARTICLE]
    linked = session.scalars(
        select(EntityArticle.source_article_id).where(EntityArticle.entity_id == one.id)
    ).all()
    assert sorted(linked) == sorted([first.id, second.id])


# --- the approval rule ----------------------------------------------------------------


def affiliation_items(fixture_json, path: str) -> list[dict[str, Any]]:
    return fixture_json(f"ror/{path}")["items"]


def ror_record(item: dict[str, Any], fetched_at: datetime = NOW) -> SourceRecord:
    address = item["organization"]["id"]
    return SourceRecord("ror", address.removeprefix("https://ror.org/"), address, item, fetched_at)


class Registry:
    """An organisation registry answering each name with the records given for it."""

    def __init__(self, answers: dict[str, list[SourceRecord]]) -> None:
        self.answers = answers
        self.asked: list[str] = []

    def organisations(self, name: str) -> list[SourceRecord]:
        self.asked.append(name)
        return self.answers.get(name, [])


def with_institution(session: Session, claim: Claim, name: str) -> Entity:
    entity = Entity(claim_id=claim.id, type=EntityType.INSTITUTION, name=name)
    session.add(entity)
    session.flush()
    return entity


def test_registry_choosing_one_record_approves_it_by_rule(session: Session, fixture_json):
    """Scenario: Registry chooses one record"""
    claim = new_claim(session)
    with_institution(session, claim, "University of Nottingham")
    chosen = next(
        item
        for item in affiliation_items(fixture_json, "affiliation_university_of_nottingham.json")
        if item["chosen"]
    )
    registry = Registry({"University of Nottingham": [ror_record(chosen)]})

    [match] = match_organisations(session, claim, registry=registry, now=NOW)

    assert (match.external_id, match.score) == ("01ee9ar58", 1.0)
    assert (match.review_state, match.reviewed_by) == (ReviewState.APPROVED, Decider.RULE)
    kept = session.get(OrganisationRecord, ("ror", "01ee9ar58"))
    assert kept is not None
    assert kept.url == "https://ror.org/01ee9ar58"
    assert kept.fetched_at == NOW
    assert kept.payload["id"] == "https://ror.org/01ee9ar58"


def test_registry_choosing_none_leaves_every_match_pending(session: Session, fixture_json):
    """Scenario: Registry chooses none"""
    claim = new_claim(session)
    entity = with_institution(session, claim, "Nottingham Institute")
    near_misses = [
        item
        for path in ("affiliation_unknown.json", "affiliation_university_of_nottingham.json")
        for item in affiliation_items(fixture_json, path)
        if not item["chosen"]
    ]
    assert len(near_misses) == 3
    registry = Registry({"Nottingham Institute": [ror_record(item) for item in near_misses]})

    added = match_organisations(session, claim, registry=registry, now=NOW)

    assert len(added) == 3
    assert {match.review_state for match in added} == {ReviewState.PENDING}
    assert (
        session.scalars(
            select(EntityMatch).where(
                EntityMatch.entity_id == entity.id,
                EntityMatch.review_state == ReviewState.APPROVED,
            )
        ).first()
        is None
    )


def test_chosen_match_the_operator_rejected_stays_rejected(session: Session, fixture_json):
    """Scenario: Operator rejected the chosen record"""
    claim = new_claim(session)
    with_institution(session, claim, "University of Nottingham")
    chosen = next(
        item
        for item in affiliation_items(fixture_json, "affiliation_university_of_nottingham.json")
        if item["chosen"]
    )
    registry = Registry({"University of Nottingham": [ror_record(chosen)]})
    [match] = match_organisations(session, claim, registry=registry, now=NOW)
    decide_item(session, "match", match.id, ReviewState.REJECTED, now=NOW)

    assert match_organisations(session, claim, registry=registry, now=LATER) == []

    assert (match.review_state, match.reviewed_by) == (ReviewState.REJECTED, Decider.HUMAN)


def test_pending_match_stored_before_the_rule_is_approved_when_chosen_again(
    session: Session, fixture_json
):
    claim = new_claim(session)
    entity = with_institution(session, claim, "University of Nottingham")
    session.add(
        EntityMatch(entity_id=entity.id, source_name="ror", external_id="01ee9ar58", score=1.0)
    )
    session.flush()
    chosen = next(
        item
        for item in affiliation_items(fixture_json, "affiliation_university_of_nottingham.json")
        if item["chosen"]
    )
    registry = Registry({"University of Nottingham": [ror_record(chosen, LATER)]})

    assert match_organisations(session, claim, registry=registry, now=LATER) == []

    match = session.scalars(select(EntityMatch).where(EntityMatch.entity_id == entity.id)).one()
    assert (match.review_state, match.reviewed_by, match.reviewed_at) == (
        ReviewState.APPROVED,
        Decider.RULE,
        LATER,
    )
    kept = session.get(OrganisationRecord, ("ror", "01ee9ar58"))
    assert kept is not None and kept.fetched_at == LATER


# --- the review queue -----------------------------------------------------------------


def test_queue_shows_an_organisation_match_with_the_registry_name_country_and_website(
    session: Session, fixture_json
):
    claim = new_claim(session)
    with_institution(session, claim, "Nottingham")
    near_miss = next(
        item
        for item in affiliation_items(fixture_json, "affiliation_university_of_nottingham.json")
        if not item["chosen"]
    )
    [match] = match_organisations(
        session, claim, registry=Registry({"Nottingham": [ror_record(near_miss)]}), now=NOW
    )
    claim.review_state = ReviewState.APPROVED
    claim.reviewed_at, claim.reviewed_by = NOW, Decider.HUMAN
    session.flush()

    [item] = pending_items(session, claim_slug=SLUG)

    assert (item.kind, item.id) == ("match", match.id)
    assert item.assertion.startswith(
        f"institution 'Nottingham' is organisation {match.external_id}"
    )
    assert item.source_url == f"https://ror.org/{match.external_id}"
    assert item.detail == match.record_summary
    assert item.detail is not None and item.detail.count(". ") == 2


@pytest.mark.parametrize("named_by", [[], ["article", "press"]])
def test_an_entity_is_named_by_an_article_or_a_registry(session: Session, named_by: list[str]):
    claim = new_claim(session)
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            Entity(claim_id=claim.id, type=EntityType.INSTITUTION, name="X", named_by=named_by)
        )
        session.flush()
