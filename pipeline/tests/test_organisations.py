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

from thenwhat.claims.entities import entities_of, note_named_organisation, note_sponsor
from thenwhat.claims.entry import add_article, add_claim, articles_of
from thenwhat.db.models import (
    Claim,
    Entity,
    EntityArticle,
    EntityMatch,
    OrganisationRecord,
    PaperRecord,
)
from thenwhat.domain import Decider, EntityType, NamedBy, ReviewState
from thenwhat.events.fetch import event_row, fetch_claim
from thenwhat.events.trial import trial_events
from thenwhat.export.build import build_export
from thenwhat.export.organisations import is_on_website
from thenwhat.resolve.organisations import is_named_exactly, match_organisations
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
        summary="An antibody restored missing teeth in mice.",
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


def chosen_record(fixture_json, path: str) -> SourceRecord:
    return ror_record(
        next(item for item in affiliation_items(fixture_json, path) if item["chosen"])
    )


@pytest.mark.parametrize(
    ("name", "path"),
    [
        # ROR chose another organisation: the name given is none of its names.
        ("CRISPR Therapeutics", "affiliation_crispr_therapeutics.json"),
        ("Ulster University", "affiliation_ulster_university.json"),
        ("Göteborg University", "affiliation_goteborg_university.json"),
        (
            "University College London Hospitals",
            "affiliation_university_college_london_hospitals.json",
        ),
        # A government body's name is reused from country to country: without its
        # country the US agency's name is exactly the Thai agency's.
        ("Food and Drug Administration", "affiliation_food_and_drug_administration.json"),
        # A one-word name must match with its capitals: the journal is not "NeurON".
        ("Neuron", "affiliation_neuron.json"),
        # A newspaper: ROR types the record only as funder and "other".
        ("The New York Times", "affiliation_the_new_york_times.json"),
    ],
)
def test_chosen_record_without_strong_evidence_stays_pending(
    session: Session, fixture_json, name: str, path: str
):
    """Scenario: Registry chooses another organisation. The name stays unidentified and
    no looser match is tried."""
    claim = new_claim(session)
    entity = with_institution(session, claim, name)
    registry = Registry({name: [chosen_record(fixture_json, path)]})

    [match] = match_organisations(session, claim, registry=registry, now=NOW)

    assert match.review_state is ReviewState.PENDING
    assert registry.asked == [name]
    assert (
        session.scalars(
            select(EntityMatch).where(
                EntityMatch.entity_id == entity.id,
                EntityMatch.review_state == ReviewState.APPROVED,
            )
        ).first()
        is None
    )


def test_government_body_named_with_its_country_is_approved(session: Session, fixture_json):
    """Scenario: Government body named with its country"""
    claim = new_claim(session)
    with_institution(session, claim, "U.S. Food and Drug Administration")
    record = chosen_record(fixture_json, "affiliation_us_food_and_drug_administration.json")
    registry = Registry({"U.S. Food and Drug Administration": [record]})

    [match] = match_organisations(session, claim, registry=registry, now=NOW)

    assert (match.review_state, match.reviewed_by) == (ReviewState.APPROVED, Decider.RULE)


def test_journal_name_is_never_approved(session: Session, fixture_json):
    """Scenario: Journal named in the report. "NeurON" is exactly one of the record's
    names, but a paper on record was published in a journal of that name."""
    claim = new_claim(session)
    with_institution(session, claim, "NeurON")
    session.add(
        PaperRecord(
            identifier="10.1000/neuron-paper",
            source_name="europepmc",
            payload={"journalInfo": {"journal": {"title": "Neuron", "isoabbreviation": "Neuron"}}},
            fetched_at=NOW,
        )
    )
    session.flush()
    registry = Registry({"NeurON": [chosen_record(fixture_json, "affiliation_neuron.json")]})

    [match] = match_organisations(session, claim, registry=registry, now=NOW)

    assert match.review_state is ReviewState.PENDING


@pytest.mark.parametrize(
    ("name", "named"),
    [
        ("University of Nottingham", True),
        ("the university of nottingham", True),
        ("University of Nottingham (UoN)", True),
        ("Nottingham University", False),
        ("University of Nottingham Malaysia", False),
        ("Nottingham", False),
    ],
)
def test_a_name_is_one_of_the_record_names_only_when_it_is_equal(
    fixture_json, name: str, named: bool
):
    organisation = chosen_record(fixture_json, "affiliation_university_of_nottingham.json").payload[
        "organization"
    ]
    assert is_named_exactly(name, organisation) is named


def test_a_company_record_name_is_compared_without_its_country_bracket(fixture_json):
    organisation = chosen_record(fixture_json, "affiliation_crispr_therapeutics.json").payload[
        "organization"
    ]
    assert is_named_exactly("Sprint PNS System", organisation)
    assert not is_named_exactly("CRISPR Therapeutics", organisation)


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


# --- the export -----------------------------------------------------------------------

REPORT = "https://www.nottingham.ac.uk/news/teeth"
NEWSPAPER = "https://www.example-times.co.uk/health/teeth"


def published_claim(session: Session, *, reports: tuple[str, ...] = (REPORT,)) -> Claim:
    claim = new_claim(session)
    for n, url in enumerate(reports, start=1):
        add_article(
            session,
            SLUG,
            url=url,
            outlet="Example",
            title="Teeth regrown",
            published_date=date(2026, 1, n),
        )
    decide_item(session, "claim", claim.id, ReviewState.APPROVED, now=NOW)
    return claim


def article_of(session: Session, claim: Claim, url: str):
    return next(article for article in articles_of(session, claim) if article.url == url)


def registry_trial(session: Session, claim: Claim, study: dict[str, Any]) -> None:
    """Store, approved, the events a fetch of `study` creates, each keeping the record."""
    nct_id = study["protocolSection"]["identificationModule"]["nctId"]
    record = SourceRecord(
        "clinicaltrials.gov", nct_id, f"https://clinicaltrials.gov/study/{nct_id}", study, NOW
    )
    for draft in trial_events(record):
        event = event_row(claim, draft)
        session.add(event)
        session.flush()
        decide_item(session, "event", event.id, ReviewState.APPROVED, now=NOW)


def trial_numbered(study: dict[str, Any], nct_id: str) -> dict[str, Any]:
    changed = copy.deepcopy(study)
    changed["protocolSection"]["identificationModule"]["nctId"] = nct_id
    return changed


def nottingham(fixture_json) -> SourceRecord:
    return ror_record(
        next(
            item
            for item in affiliation_items(fixture_json, "affiliation_university_of_nottingham.json")
            if item["chosen"]
        )
    )


def exported_claim(session: Session):
    [claim] = build_export(session, now=NOW).claims
    return claim


def test_two_spellings_matched_to_one_record_are_one_organisation(session: Session, fixture_json):
    """Scenario: Same organisation under two spellings; Identified university;
    University press release"""
    claim = published_claim(session)
    note_named_organisation(
        session,
        claim,
        article_of(session, claim, REPORT),
        "University of Nottingham",
        EntityType.INSTITUTION,
    )
    registry_trial(
        session,
        claim,
        sponsored_by(
            fixture_json("clinicaltrials/study_NCT02586935.json"),
            "The University of Nottingham",
            "OTHER",
        ),
    )
    note_sponsor(session, claim, "The University of Nottingham", industry=False)
    record = nottingham(fixture_json)
    slightly_less = SourceRecord(
        record.source_name,
        record.external_id,
        record.url,
        record.payload | {"score": 0.97},
        record.fetched_at,
    )
    match_organisations(
        session,
        claim,
        registry=Registry(
            {
                "University of Nottingham": [record],
                "The University of Nottingham": [slightly_less],
            }
        ),
        now=NOW,
    )

    exported = exported_claim(session)

    [organisation] = exported.organisations
    assert organisation.model_dump(mode="json") == {
        "name": "University of Nottingham",
        "identified": True,
        "record": {
            "source": "ror",
            "external_id": "01ee9ar58",
            "url": "https://ror.org/01ee9ar58",
            "name": "University of Nottingham",
            "kinds": ["education", "funder"],
            "country": "United Kingdom",
            "website": "https://www.nottingham.ac.uk/",
            "score": 0.97,
            "read_at": "2026-11-20T10:00:00Z",
        },
        "roles": [
            {"role": "named_in_report", "article_urls": [REPORT], "trial_ids": []},
            {"role": "sponsor", "article_urls": [], "trial_ids": ["NCT02586935"]},
        ],
    }
    # The report is on the university's own website.
    assert [article.published_by for article in exported.articles] == ["https://ror.org/01ee9ar58"]
    export = build_export(session, now=NOW)
    assert ("Research Organization Registry (ROR)", "https://ror.org/") in [
        (source.name, source.url) for source in export.sources
    ]


def test_sponsor_of_three_trials_is_listed_once(session: Session, fixture_json):
    """Scenario: Sponsor of three trials; Name the registry does not know"""
    claim = published_claim(session, reports=(NEWSPAPER,))
    study = sponsored_by(
        fixture_json("clinicaltrials/study_NCT02586935.json"), "Example Pharma Ltd", "INDUSTRY"
    )
    for nct_id in ("NCT00000003", "NCT00000001", "NCT00000002"):
        registry_trial(session, claim, trial_numbered(study, nct_id))
    note_sponsor(session, claim, "Example Pharma Ltd", industry=True)
    note_named_organisation(
        session,
        claim,
        article_of(session, claim, NEWSPAPER),
        "Zzqxv Bio",
        EntityType.COMPANY,
    )
    match_organisations(session, claim, registry=Registry({}), now=NOW)

    exported = exported_claim(session)

    assert [organisation.model_dump(mode="json") for organisation in exported.organisations] == [
        {
            "name": "Zzqxv Bio",
            "identified": False,
            "record": None,
            "roles": [{"role": "named_in_report", "article_urls": [NEWSPAPER], "trial_ids": []}],
        },
        {
            "name": "Example Pharma Ltd",
            "identified": False,
            "record": None,
            "roles": [
                {
                    "role": "sponsor",
                    "article_urls": [],
                    "trial_ids": ["NCT00000001", "NCT00000002", "NCT00000003"],
                }
            ],
        },
    ]
    # A newspaper's report, and organisations not identified: no mark.
    assert [article.published_by for article in exported.articles] == [None]
    assert "Research Organization Registry (ROR)" not in [
        source.name for source in build_export(session, now=NOW).sources
    ]


def test_person_sponsor_is_no_organisation(session: Session, fixture_json):
    """Scenario: Sponsor-investigator; Person sponsor"""
    claim = published_claim(session)
    registry_trial(session, claim, fixture_json("clinicaltrials/study_NCT04951479_comparison.json"))

    export = build_export(session, now=NOW)

    assert export.claims[0].organisations == []
    assert "Example Investigator" not in export.model_dump_json()


def test_organisation_named_as_a_person_of_the_claim_is_not_exported(session: Session):
    """Scenario: a report's person recorded as an institution"""
    claim = published_claim(session)
    session.add(Entity(claim_id=claim.id, type=EntityType.PERSON, name="Ada Example"))
    note_named_organisation(
        session, claim, article_of(session, claim, REPORT), "Ada Example", EntityType.INSTITUTION
    )
    note_named_organisation(
        session,
        claim,
        article_of(session, claim, REPORT),
        "University of Nottingham",
        EntityType.INSTITUTION,
    )

    exported = exported_claim(session)

    assert [organisation.name for organisation in exported.organisations] == [
        "University of Nottingham"
    ]
    assert "Ada Example" not in exported.model_dump_json()


def test_organisation_whose_registry_name_is_a_person_of_the_claim_is_not_exported(
    session: Session, fixture_json
):
    claim = published_claim(session)
    session.add(Entity(claim_id=claim.id, type=EntityType.PERSON, name="University of Nottingham"))
    given = "The University of Nottingham"
    note_named_organisation(
        session, claim, article_of(session, claim, REPORT), given, EntityType.INSTITUTION
    )
    [match] = match_organisations(
        session, claim, registry=Registry({given: [nottingham(fixture_json)]}), now=NOW
    )
    assert match.review_state is ReviewState.APPROVED

    assert exported_claim(session).organisations == []


@pytest.mark.parametrize(
    ("article", "website", "marked"),
    [
        ("https://news.nottingham.ac.uk/2026/teeth", "https://www.nottingham.ac.uk/", True),
        ("https://WWW.Nottingham.ac.uk/news", "https://nottingham.ac.uk", True),
        ("https://www.example-times.co.uk/health", "https://www.nottingham.ac.uk/", False),
        ("https://notnottingham.ac.uk/news", "https://www.nottingham.ac.uk/", False),
        ("https://nottingham.ac.uk.example.org/", "https://www.nottingham.ac.uk/", False),
        ("https://news.nottingham.ac.uk/", None, False),
    ],
)
def test_article_is_on_an_organisation_website_only_by_its_host(
    article: str, website: str | None, marked: bool
):
    """Scenarios: University press release; Newspaper report; a host that merely ends
    with the same letters"""
    assert is_on_website(article, website) is marked


def test_report_on_the_site_of_an_unidentified_organisation_has_no_mark(session: Session):
    """Scenario: Organisation not identified"""
    claim = published_claim(session)
    note_named_organisation(
        session,
        claim,
        article_of(session, claim, REPORT),
        "University of Nottingham",
        EntityType.INSTITUTION,
    )

    exported = exported_claim(session)

    assert [organisation.identified for organisation in exported.organisations] == [False]
    assert [article.published_by for article in exported.articles] == [None]


def test_organisations_do_not_change_the_status(session: Session, fixture_json):
    """Scenario: Claim gains an industry sponsor"""
    claim = published_claim(session)
    registry_trial(
        session,
        claim,
        sponsored_by(
            fixture_json("clinicaltrials/study_NCT02586935.json"), "Example Pharma Ltd", "INDUSTRY"
        ),
    )
    before = exported_claim(session).status

    note_sponsor(session, claim, "Example Pharma Ltd", industry=True)
    note_named_organisation(
        session,
        claim,
        article_of(session, claim, REPORT),
        "University of Nottingham",
        EntityType.INSTITUTION,
    )
    match_organisations(
        session,
        claim,
        registry=Registry({"University of Nottingham": [nottingham(fixture_json)]}),
        now=NOW,
    )
    after = exported_claim(session)

    assert len(after.organisations) == 2
    assert (after.status.code, after.status.explained_by) == (
        before.code,
        before.explained_by,
    )
