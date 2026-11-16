"""Merging a duplicate claim into the kept one, and renaming an intervention
(openspec claims: "Merging duplicate claims", "Renaming an intervention")."""

from datetime import UTC, date, datetime
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.corrections import (
    NO_BRACKETS,
    NO_DOSE,
    NO_MAKER,
    NOT_A_NAME,
    Merged,
    MergeRefused,
    Renamed,
    RenameRefused,
    merge_claims,
    moved_addresses,
    name_refusal,
    rename_intervention,
)
from thenwhat.claims.entities import add_entity, add_synonym, entities_of, set_origin_paper
from thenwhat.claims.entry import (
    ArchiveRefused,
    DuplicateClaim,
    SlugTaken,
    add_article,
    add_claim,
    add_promise,
    archive_claim,
    articles_of,
    promises_of,
    slug_of_claim_covering,
    unarchive_claim,
)
from thenwhat.db.models import (
    Claim,
    ClaimChange,
    Entity,
    EntityArticle,
    EntityMatch,
    EvidenceEvent,
    LinkLead,
    ReportedStatement,
)
from thenwhat.domain import (
    Decider,
    EntityType,
    EventType,
    OutletKind,
    ReadOutcome,
    ReviewState,
    StatementBasis,
    StatementFirmness,
    StatementKind,
    StatementSpeaker,
)
from thenwhat.prepare import plan_claims

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
EARLIER = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)
FIRST = "https://news.example.org/2019/ebola-vaccine"
SECOND = "https://other.example.org/2016/vsv-ebov"


def new_claim(session: Session, slug: str, intervention: str, **overrides) -> Claim:
    values = {
        "slug": slug,
        "headline": "Vaccine protects against Ebola",
        "vertical": "infections",
        "intervention": intervention,
        "indication": "Ebola virus disease",
    }
    return add_claim(session, **(values | overrides))


def article(session: Session, slug: str, url: str, published: date) -> None:
    add_article(
        session, slug, url=url, outlet="Example News", title="A report", published_date=published
    )


def intervention(session: Session, claim: Claim) -> Entity:
    return session.scalars(
        select(Entity).where(Entity.claim_id == claim.id, Entity.type == EntityType.INTERVENTION)
    ).one()


def approved_match(session: Session, entity: Entity, external_id: str) -> EntityMatch:
    match = EntityMatch(
        entity_id=entity.id,
        source_name="clinicaltrials",
        external_id=external_id,
        score=0.95,
        review_state=ReviewState.APPROVED,
        reviewed_at=EARLIER,
        reviewed_by=Decider.HUMAN,
    )
    session.add(match)
    session.flush()
    return match


def statement(session: Session, claim: Claim, text: str) -> ReportedStatement:
    [first] = articles_of(session, claim)[:1]
    row = ReportedStatement(
        claim_id=claim.id,
        source_article_id=first.id,
        text=text,
        text_key=text.casefold(),
        kind=StatementKind.EFFECT,
        firmness=StatementFirmness.FACT,
        speaker=StatementSpeaker.ARTICLE,
        basis=StatementBasis.PEOPLE,
        confidence=0.9,
        decision_ref=f"source_article:{first.id}:statement:0",
        article_read_at=EARLIER,
    )
    session.add(row)
    session.flush()
    return row


@pytest.fixture
def pair(session: Session) -> tuple[Claim, Claim]:
    """A kept claim under its product name and a duplicate under the candidate's code."""
    kept = new_claim(session, "ervebo-ebola", "Ervebo")
    article(session, kept.slug, FIRST, date(2019, 11, 12))
    duplicate = new_claim(session, "vsv-ebov-ebola", "VSV-EBOV")
    add_synonym(session, duplicate.slug, "VSV-EBOV", "rVSV-ZEBOV")
    article(session, duplicate.slug, SECOND, date(2016, 12, 23))
    add_promise(session, duplicate.slug, article_url=SECOND, description="licensed by 2018")
    return kept, duplicate


def merge(session: Session, **options) -> Merged:
    values: dict[str, Any] = {"reason": "one vaccine, two names", "by": Decider.HUMAN, "now": NOW}
    return merge_claims(session, "vsv-ebov-ebola", "ervebo-ebola", **(values | options))


# --- merging ------------------------------------------------------------------------


def test_merge_moves_what_the_articles_reported_to_the_kept_claim(session: Session, pair):
    """Scenario: Duplicate claim merged"""
    kept, duplicate = pair
    said = statement(session, duplicate, "The vaccine protected everyone given it.")
    lead = LinkLead(
        url=SECOND,
        url_key="other.example.org/2016/vsv-ebov",
        outlet="other.example.org",
        outlet_kind=OutletKind.GENERAL_NEWS,
        title="A report",
        first_shared_at=EARLIER,
        read_outcome=ReadOutcome.NEW_CLAIM,
        claim_id=duplicate.id,
        source_article_id=articles_of(session, duplicate)[0].id,
    )
    session.add(lead)
    session.flush()

    done = merge(session)

    assert [a.url for a in articles_of(session, kept)] == [SECOND, FIRST]
    assert [p.description for p in promises_of(session, kept)] == ["licensed by 2018"]
    assert said.claim_id == kept.id
    assert kept.first_reported_date == date(2016, 12, 23)
    assert intervention(session, kept).synonyms == ["VSV-EBOV", "rVSV-ZEBOV"]
    assert (lead.claim_id, lead.read_outcome) == (kept.id, ReadOutcome.ADDED_TO_CLAIM)
    assert (done.articles_moved, done.promises_moved, done.statements_moved) == (1, 1, 1)
    assert done.names_gained == ["VSV-EBOV", "rVSV-ZEBOV"]


def test_merged_claim_is_archived_with_a_pointer_and_who_decided(session: Session, pair):
    """Scenario: Duplicate claim merged; Scenario: Merge decided by an assistant"""
    kept, duplicate = pair

    merge(session, by=Decider.ASSISTANT)

    assert duplicate.archived_at == NOW
    assert duplicate.archive_reason == "merged into ervebo-ebola: one vaccine, two names"
    assert duplicate.merged_into_id == kept.id
    change = session.scalars(select(ClaimChange)).one()
    assert (change.claim_id, change.into_claim_id, change.kind) == (duplicate.id, kept.id, "merge")
    assert (change.decided_by, change.decided_at) == (Decider.ASSISTANT, NOW)
    # The merged claim stands for nothing: the kept one answers for both names.
    assert slug_of_claim_covering(session, "vsv-ebov", "Ebola virus disease") == "ervebo-ebola"
    with pytest.raises(DuplicateClaim, match="ervebo-ebola"):
        new_claim(session, "another", "rVSV-ZEBOV")
    with pytest.raises(ArchiveRefused, match="merged into 'ervebo-ebola'"):
        unarchive_claim(session, duplicate.slug)


def test_matches_and_events_stay_and_the_kept_claims_search_is_due(session: Session, pair):
    """Scenario: Registry evidence is found again, not moved"""
    kept, duplicate = pair
    match = approved_match(session, intervention(session, duplicate), "NCT02503202")
    event = EvidenceEvent(
        claim_id=duplicate.id,
        entity_match_id=match.id,
        type=EventType.TRIAL_REGISTERED,
        event_date=date(2015, 7, 20),
        source_name="clinicaltrials",
        source_url="https://registry.example/NCT02503202",
        external_id="NCT02503202",
        summary="Trial registered",
        confidence=1.0,
        raw_payload={},
        fetched_at=EARLIER,
        dedupe_key="NCT02503202:registered",
        review_state=ReviewState.APPROVED,
        reviewed_at=EARLIER,
        reviewed_by=Decider.HUMAN,
    )
    session.add(event)
    session.flush()

    done = merge(session)

    assert match.entity_id == intervention(session, duplicate).id
    assert event.claim_id == duplicate.id
    assert done.to_find_again == ["clinicaltrials NCT02503202"]
    assert kept.registry_search_due_at == NOW
    assert [plan.slug for plan in plan_claims(session, None, pending=False, due=True)] == [
        "ervebo-ebola"
    ]


def test_named_papers_and_organisations_move_once(session: Session, pair):
    """Scenario: Named entities are not doubled"""
    kept, duplicate = pair
    add_entity(session, kept.slug, type=EntityType.COMPANY, name="Merck")
    add_entity(session, kept.slug, type=EntityType.PAPER, name="The kept paper")
    set_origin_paper(session, kept.slug, "The kept paper")
    merck = add_entity(session, duplicate.slug, type=EntityType.COMPANY, name="merck")
    paper = add_entity(
        session, duplicate.slug, type=EntityType.PAPER, name="Ring trial", doi="10.1/ring"
    )
    set_origin_paper(session, duplicate.slug, "Ring trial")
    identified = approved_match(session, paper, "10.1/ring")
    session.add(
        EntityArticle(entity_id=merck.id, source_article_id=articles_of(session, duplicate)[0].id)
    )
    session.flush()

    done = merge(session)

    names = sorted((e.type.value, e.name) for e in entities_of(session, kept))
    assert names == [
        ("company", "Merck"),
        ("intervention", "Ervebo"),
        ("paper", "Ring trial"),
        ("paper", "The kept paper"),
    ]
    assert done.entities_moved == 1
    # The paper came with the record that says which paper it is; the kept claim keeps
    # its own origin paper.
    assert paper.claim_id == kept.id and identified.entity_id == paper.id
    assert not paper.is_origin_paper
    # The article that named the duplicate's Merck now names the kept claim's.
    [ours] = [e for e in entities_of(session, kept) if e.type is EntityType.COMPANY]
    [link] = session.scalars(select(EntityArticle)).all()
    assert link.entity_id == ours.id


def test_an_article_both_claims_have_is_not_doubled(session: Session, pair):
    kept, duplicate = pair
    article(session, duplicate.slug, FIRST, date(2019, 11, 12))
    add_promise(session, duplicate.slug, article_url=FIRST, description="in clinics by 2020")

    done = merge(session)

    assert [a.url for a in articles_of(session, kept)] == [SECOND, FIRST]
    assert (done.articles_moved, done.articles_already_there) == (1, 1)
    assert sorted(p.description for p in promises_of(session, kept)) == [
        "in clinics by 2020",
        "licensed by 2018",
    ]


def test_merge_across_indications_is_refused_unless_accepted(session: Session, pair):
    """Scenario: Different indications"""
    kept, duplicate = pair
    duplicate.indication = "prevention of Ebola virus disease"
    session.flush()

    with pytest.raises(MergeRefused, match="The indications differ"):
        merge(session)
    assert duplicate.archived_at is None and articles_of(session, kept)[0].url == FIRST

    merge(session, different_indication_accepted=True)
    assert duplicate.merged_into_id == kept.id


def test_merge_into_an_archived_claim_is_refused(session: Session, pair):
    """Scenario: Kept claim is archived"""
    kept, _ = pair
    archive_claim(session, kept.slug, reason="wrong trial", now=EARLIER)

    with pytest.raises(MergeRefused, match="'ervebo-ebola' is archived"):
        merge(session)


def test_merge_of_a_claim_awaiting_audit_is_refused_unless_said(session: Session, pair):
    """Scenario: Claim awaiting audit"""
    _, duplicate = pair
    duplicate.awaiting_audit_at = EARLIER
    session.flush()

    with pytest.raises(MergeRefused, match="Awaiting audit: vsv-ebov-ebola"):
        merge(session)

    merge(session, awaiting_audit_accepted=True)
    assert duplicate.merged_into_id is not None
    assert duplicate.awaiting_audit_at is None


def test_a_description_does_not_become_a_synonym(session: Session, pair):
    """Scenario: Duplicate named by a description"""
    kept, duplicate = pair
    intervention(session, duplicate).name = "experimental Ebola vaccine (rVSV)"
    session.flush()

    with pytest.raises(MergeRefused, match="--drop-name"):
        merge(session)

    merge(session, drop_name=True)
    assert intervention(session, kept).synonyms == ["rVSV-ZEBOV"]


def test_merge_needs_a_reason_and_two_claims(session: Session, pair):
    with pytest.raises(MergeRefused, match="Give a reason"):
        merge(session, reason="  ")
    with pytest.raises(MergeRefused, match="into itself"):
        merge_claims(session, "ervebo-ebola", "ervebo-ebola", reason="x", by=Decider.HUMAN, now=NOW)
    merge(session)
    with pytest.raises(MergeRefused, match="already merged into 'ervebo-ebola'"):
        merge(session)


# --- the entry rules for a name -----------------------------------------------------


@pytest.mark.parametrize(
    ("name", "rule"),
    [
        ("targeted thermal therapy (TTT)", NO_BRACKETS),
        ("100 mg daily enteric-coated aspirin", NO_DOSE),
        ("aspirin once daily", NO_DOSE),
        ("treatment for Guillain-Barre syndrome", NOT_A_NAME),
        ("GLP-1 drugs", NOT_A_NAME),
        ("Annexon ANX005", NO_MAKER),
        ("Pfizer's BNT162b2", NO_MAKER),
        ("ANX005", None),
        ("exagamglogene autotemcel", None),
    ],
)
def test_a_name_is_checked_against_the_entry_rules(name: str, rule: str | None):
    assert name_refusal(name, makers=["Annexon"]) == rule


# --- renaming -----------------------------------------------------------------------


def rename(session: Session, old: str, new: str, **options) -> Renamed:
    values: dict[str, Any] = {"by": Decider.HUMAN, "now": NOW}
    return rename_intervention(session, "vsv-ebov-ebola", old, new, **(values | options))


def test_rename_keeps_a_real_old_name_as_a_synonym_and_makes_the_search_due(session: Session, pair):
    """Scenario: Intervention renamed"""
    _, claim = pair

    done = rename(session, "vsv-ebov", "rVSV-ZEBOV-GP", by=Decider.ASSISTANT)

    entity = intervention(session, claim)
    assert (entity.name, entity.synonyms) == ("rVSV-ZEBOV-GP", ["rVSV-ZEBOV", "VSV-EBOV"])
    assert done.kept_as_synonym and done.old_slug is None
    assert claim.slug == "vsv-ebov-ebola"
    assert claim.registry_search_due_at == NOW
    change = session.scalars(select(ClaimChange)).one()
    assert (change.kind, change.old_name, change.new_name) == (
        "rename",
        "VSV-EBOV",
        "rVSV-ZEBOV-GP",
    )
    assert change.decided_by is Decider.ASSISTANT and change.former_slug is None


def test_rename_drops_an_old_name_that_is_a_description(session: Session, pair):
    """Scenario: Old name is a description"""
    _, claim = pair
    intervention(session, claim).name = "treatment for Ebola"
    session.flush()

    with pytest.raises(RenameRefused, match="--old-is-description"):
        rename(session, "treatment for Ebola", "rVSV-ZEBOV")

    done = rename(session, "treatment for Ebola", "rVSV-ZEBOV", old_is_description=True)

    entity = intervention(session, claim)
    # The new name was a synonym, and is now the name alone.
    assert (entity.name, entity.synonyms) == ("rVSV-ZEBOV", [])
    assert not done.kept_as_synonym


@pytest.mark.parametrize(
    ("new_name", "said"),
    [
        ("rVSV-ZEBOV (Ervebo-like)", "no brackets"),
        ("rVSV-ZEBOV 2 ml", "no dose"),
        ("Merck V920", "who makes it"),
        ("the Ebola vaccine", "not a name"),
    ],
)
def test_rename_to_a_name_that_breaks_an_entry_rule_is_refused(
    session: Session, pair, new_name: str, said: str
):
    """Scenario: New name breaks an entry rule"""
    _, claim = pair
    add_entity(session, claim.slug, type=EntityType.COMPANY, name="Merck")

    with pytest.raises(RenameRefused, match=said):
        rename(session, "VSV-EBOV", new_name)
    assert intervention(session, claim).name == "VSV-EBOV"


def test_rename_onto_another_claims_intervention_points_to_merge(session: Session, pair):
    """Scenario: New name is another claim's"""
    with pytest.raises(RenameRefused, match="thenwhat claim merge vsv-ebov-ebola ervebo-ebola"):
        rename(session, "VSV-EBOV", "ervebo")


def test_rename_names_the_wrong_old_name(session: Session, pair):
    with pytest.raises(RenameRefused, match="is called 'VSV-EBOV', not 'Ervebo'"):
        rename(session, "Ervebo", "V920")


def test_reslug_gives_a_published_claim_a_new_address_and_keeps_the_old_one(session: Session, pair):
    """Scenario: Slug made again"""
    _, claim = pair
    claim.published_at = EARLIER
    session.flush()

    done = rename(session, "VSV-EBOV", "V920", reslug=True)

    assert (claim.slug, done.old_slug) == ("v920-ebola-virus-disease", "vsv-ebov-ebola")
    assert [(slug, to.slug) for slug, to in moved_addresses(session)] == [
        ("vsv-ebov-ebola", "v920-ebola-virus-disease")
    ]
    # The old address stays taken: no new claim can have it.
    with pytest.raises(SlugTaken):
        new_claim(session, "vsv-ebov-ebola", "Something else", indication="another condition")


def test_reslug_onto_another_claims_slug_is_refused(session: Session, pair):
    new_claim(session, "v920-ebola-virus-disease", "Unrelated", indication="unrelated")

    with pytest.raises(SlugTaken, match="v920-ebola-virus-disease"):
        rename_intervention(
            session, "vsv-ebov-ebola", "VSV-EBOV", "V920", by=Decider.HUMAN, now=NOW, reslug=True
        )
    assert intervention(session, find(session, "vsv-ebov-ebola")).name == "VSV-EBOV"


def find(session: Session, slug: str) -> Claim:
    return session.scalars(select(Claim).where(Claim.slug == slug)).one()


def test_a_former_slug_follows_its_claim_through_a_merge(session: Session, pair):
    kept, claim = pair
    claim.published_at = EARLIER
    session.flush()
    rename(session, "VSV-EBOV", "V920", reslug=True)

    merge_claims(
        session,
        "v920-ebola-virus-disease",
        "ervebo-ebola",
        reason="one vaccine",
        by=Decider.HUMAN,
        now=NOW,
    )

    assert [(slug, to.slug) for slug, to in moved_addresses(session)] == [
        ("v920-ebola-virus-disease", "ervebo-ebola"),
        ("vsv-ebov-ebola", "ervebo-ebola"),
    ]
    assert kept.archived_at is None
