"""Clinical categories against the database: which records count, reading the tree, the
reports and their commands. Behavior: openspec clinical-classification."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from typer.testing import CliRunner, Result

from thenwhat.claims.corrections import merge_claims
from thenwhat.claims.entry import add_claim
from thenwhat.cli import app
from thenwhat.clinical.service import (
    clinical_of,
    compare,
    coverage,
    prepared_line,
    read_tree,
    stored_vocabulary,
)
from thenwhat.db.models import (
    Claim,
    ClaimTerm,
    Entity,
    EntityMatch,
    EvidenceEvent,
    TermRecord,
)
from thenwhat.domain import Decider, EventType, ReviewState, TermFit, TermRole
from thenwhat.export.records import PostgresRecords
from thenwhat.review.decisions import record_decision
from thenwhat.sources.base import SourceRecord

NOW = datetime(2026, 11, 17, tzinfo=UTC)
YEAR = "http://id.nlm.nih.gov/mesh/2026"

# Identifier to label, tree number and the descriptor directly broader.
TREE: dict[str, tuple[str, str, str | None]] = {
    "D009369": ("Neoplasms", "C04", None),
    "D009371": ("Neoplasms by Site", "C04.588", "D009369"),
    "D012878": ("Skin Neoplasms", "C04.588.805", "D009371"),
    "D017437": ("Skin and Connective Tissue Diseases", "C17", None),
    "D012871": ("Skin Diseases", "C17.800", "D017437"),
    "D011565": ("Psoriasis", "C17.800.859.675", "D012871"),
}


def payload(identifier: str) -> dict[str, Any]:
    label, tree, broader = TREE[identifier]
    term: dict[str, Any] = {
        "@id": f"{YEAR}/{identifier}",
        "label": {"@language": "en", "@value": label},
        "treeNumber": f"{YEAR}/{tree}",
    }
    if broader:
        term["broaderDescriptor"] = f"{YEAR}/{broader}"
    return {"term": term, "concept": None}


class FakeMesh:
    """NLM's service, answering from `TREE` and counting what it was asked."""

    name = "mesh"

    def __init__(self) -> None:
        self.asked: list[str] = []

    def term(self, identifier: str, *, force: bool = False) -> SourceRecord | None:
        self.asked.append(identifier)
        if identifier not in TREE:
            return None
        return SourceRecord(
            "mesh",
            identifier,
            f"https://id.nlm.nih.gov/mesh/{identifier}",
            payload(identifier),
            NOW,
        )

    def descriptor_labelled(self, label: str) -> str | None:
        self.asked.append(label)
        return next((one for one, (own, _, _) in TREE.items() if own == label), None)


def store(session: Session, *identifiers: str) -> None:
    for identifier in identifiers:
        session.add(
            TermRecord(
                source_name="mesh",
                external_id=identifier,
                url=f"https://id.nlm.nih.gov/mesh/{identifier}",
                payload=payload(identifier),
                fetched_at=NOW,
            )
        )
    session.flush()


def new_claim(session: Session, slug: str, vertical: str = "skin-and-hair") -> Claim:
    claim = add_claim(
        session,
        slug=slug,
        headline="Cream clears plaques",
        vertical=vertical,
        intervention=f"EX {slug}",
        indication="Plaque psoriasis",
    )
    record_decision(claim, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    return claim


def with_trial(
    session: Session, claim: Claim, number: str, *terms: str, approved: bool = True
) -> EntityMatch:
    """A trial match with the registry event that holds its record."""
    entity = session.scalars(select(Entity).where(Entity.claim_id == claim.id)).one()
    match = EntityMatch(
        entity_id=entity.id, source_name="clinicaltrials.gov", external_id=number, score=0.9
    )
    session.add(match)
    session.flush()
    event = EvidenceEvent(
        claim_id=claim.id,
        entity_match_id=match.id,
        type=EventType.TRIAL_REGISTERED,
        event_date=date(2024, 7, 1),
        source_name="clinicaltrials.gov",
        source_url=f"https://clinicaltrials.gov/study/{number}",
        external_id=number,
        summary="Trial registered.",
        confidence=1.0,
        raw_payload={
            "protocolSection": {"identificationModule": {"nctId": number}},
            "derivedSection": {
                "conditionBrowseModule": {
                    "meshes": [{"id": term, "term": TREE[term][0]} for term in terms],
                    "ancestors": [],
                }
            },
        },
        fetched_at=NOW,
        dedupe_key=f"registered:{number}",
    )
    session.add(event)
    session.flush()
    if approved:
        record_decision(match, ReviewState.APPROVED, by=Decider.RULE, now=NOW)
        record_decision(event, ReviewState.APPROVED, by=Decider.RULE, now=NOW)
    session.flush()
    return match


def labels(session: Session, claim: Claim) -> list[str]:
    records = PostgresRecords(session)
    placed = clinical_of(records, claim, stored_vocabulary(records))
    return [category.label for category in placed.categories]


# --- which records count -----------------------------------------------------------------


def test_a_trial_that_is_not_approved_gives_no_category(session: Session):
    """Scenario: Candidate trial"""
    store(session, *TREE)
    claim = new_claim(session, "cream-a")
    with_trial(session, claim, "NCT00000001", "D011565", approved=False)

    assert labels(session, claim) == []


def test_a_category_goes_once_its_only_record_is_no_longer_approved(session: Session):
    """Scenario: Match no longer approved"""
    store(session, *TREE)
    claim = new_claim(session, "cream-a")
    with_trial(session, claim, "NCT00000001", "D011565")
    assert labels(session, claim) == ["Psoriasis"]

    for event in session.scalars(select(EvidenceEvent).where(EvidenceEvent.claim_id == claim.id)):
        event.review_state = ReviewState.REJECTED
    session.flush()

    assert labels(session, claim) == []


def test_retained_event_cannot_file_a_rejected_match_on_either_export(session, tmp_path):
    from store_support import assert_same_export

    store(session, *TREE)
    claim = new_claim(session, "cream-a")
    rejected = with_trial(session, claim, "NCT00000001", "D011565", "D012878")
    with_trial(session, claim, "NCT00000002", "D012878")
    event = session.scalars(
        select(EvidenceEvent).where(EvidenceEvent.entity_match_id == rejected.id)
    ).one()
    record_decision(event, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)

    def categories():
        exported = assert_same_export(session, tmp_path, NOW)
        return {
            c["identifier"]: [s["identifier"] for s in c["sources"]]
            for c in exported["claims"][0]["clinical_categories"]
        }

    assert categories()["D011565"] == ["NCT00000001"]
    record_decision(rejected, ReviewState.REJECTED, by=Decider.HUMAN, now=NOW)
    session.flush()
    assert event.review_state == ReviewState.APPROVED
    assert categories() == {"D012878": ["NCT00000002"]}


@pytest.mark.parametrize("latest_first", [False, True])
def test_only_the_current_snapshot_supplies_each_trials_categories(session, tmp_path, latest_first):
    from copy import deepcopy
    from datetime import timedelta

    from store_support import assert_same_export

    store(session, *TREE)
    claim = new_claim(session, "cream-a")
    match = with_trial(session, claim, "NCT00000001", "D012878", "D011565")
    first = session.scalars(
        select(EvidenceEvent).where(EvidenceEvent.entity_match_id == match.id)
    ).one()
    earlier = first.raw_payload
    latest = deepcopy(earlier)
    latest["derivedSection"]["conditionBrowseModule"]["meshes"].pop()
    first.raw_payload = latest if latest_first else earlier
    first.fetched_at = NOW if latest_first else NOW - timedelta(days=1)
    second = EvidenceEvent(
        claim_id=claim.id,
        entity_match_id=match.id,
        type=EventType.TRIAL_RESULTS_POSTED,
        event_date=date(2024, 8, 1),
        source_name=first.source_name,
        source_url=first.source_url,
        external_id=first.external_id,
        summary="Results posted.",
        confidence=1.0,
        raw_payload=earlier if latest_first else latest,
        fetched_at=NOW - timedelta(days=1) if latest_first else NOW,
        dedupe_key="second-snapshot",
    )
    session.add(second)
    record_decision(second, ReviewState.APPROVED, by=Decider.RULE, now=NOW)
    session.flush()
    exported = assert_same_export(session, tmp_path, NOW)
    assert [c["identifier"] for c in exported["claims"][0]["clinical_categories"]] == ["D012878"]


def test_a_merged_claim_keeps_its_own_trials_categories(session: Session):
    """A merge moves no registry match, so the kept claim's categories are its own until
    its registries are searched again (openspec claims, "Merging duplicate claims")."""
    store(session, *TREE)
    kept = new_claim(session, "cream-a")
    duplicate = new_claim(session, "cream-b")
    duplicate.indication = "Psoriasis"
    with_trial(session, kept, "NCT00000001", "D011565")
    with_trial(session, duplicate, "NCT00000002", "D012878")

    merge_claims(
        session,
        duplicate.slug,
        kept.slug,
        reason="same cream",
        by=Decider.HUMAN,
        now=NOW,
        same_treatment_accepted=True,
        different_indication_accepted=True,
    )

    assert labels(session, kept) == ["Psoriasis"]


# --- reading the tree ------------------------------------------------------------------


def test_the_tree_is_read_to_its_top_and_not_asked_for_twice(session: Session):
    claim = new_claim(session, "cream-a")
    with_trial(session, claim, "NCT00000001", "D011565")
    source = FakeMesh()

    run = read_tree(session, source, [claim], mapping={"skin-and-hair": (("D017437", "x"),)})

    assert run.read == 3 and run.retired == [] and run.unknown_headings == []
    assert sorted(source.asked) == ["D011565", "D012871", "D017437"]
    assert labels(session, claim) == ["Psoriasis"]

    again = FakeMesh()
    assert (
        read_tree(session, again, [claim], mapping={"skin-and-hair": (("D017437", "x"),)}).read == 0
    )
    assert again.asked == []


def test_a_descriptor_the_vocabulary_no_longer_holds_is_listed(session: Session):
    """Scenario: Descriptor the vocabulary no longer holds"""
    claim = new_claim(session, "cream-a")
    with_trial(session, claim, "NCT00000001", "D011565")

    run = read_tree(session, FakeMesh(), [claim], mapping={"cancer": (("D000001", "Gone"),)})

    assert run.retired == ["D000001"]


# --- the reports -----------------------------------------------------------------------


def three_claims(session: Session) -> tuple[Claim, Claim, Claim]:
    store(session, *TREE)
    agreeing = new_claim(session, "cream-a")
    with_trial(session, agreeing, "NCT00000001", "D011565")
    disagreeing = new_claim(session, "cream-b")
    disagreeing.indication = "Skin cancer"
    with_trial(session, disagreeing, "NCT00000002", "D012878")
    bare = new_claim(session, "cream-c")
    bare.indication = "Eczema"
    session.flush()
    return agreeing, disagreeing, bare


def test_coverage_counts_claims_by_where_their_categories_come_from(session: Session):
    claims = three_claims(session)
    records = PostgresRecords(session)

    counted = coverage(records, claims, stored_vocabulary(records))

    assert (counted.from_trials, counted.from_papers_only, counted.none, counted.not_read) == (
        2,
        0,
        1,
        0,
    )


def with_condition_term(
    session: Session, claim: Claim, identifier: str, *, fit: TermFit, approved: bool = True
) -> ClaimTerm:
    """The terms step's reading of a MeSH descriptor as the claim's condition."""
    term = ClaimTerm(
        claim_id=claim.id,
        role=TermRole.CONDITION,
        source_name="mesh",
        external_id=identifier,
        label=TREE[identifier][0],
        score=0.93 if approved else 0.55,
        fit=fit,
    )
    session.add(term)
    session.flush()
    if approved:
        record_decision(term, ReviewState.APPROVED, by=Decider.RULE, now=NOW)
        session.flush()
    return term


def test_an_approved_reading_of_the_claims_own_condition_is_a_category(session: Session):
    """Scenarios: Claim with a checked condition term; Term read as broader; Reading not
    approved"""
    store(session, *TREE)
    claim = new_claim(session, "cream-a")
    with_condition_term(session, claim, "D011565", fit=TermFit.EXACT)
    with_condition_term(session, claim, "D012871", fit=TermFit.BROADER)
    with_condition_term(session, claim, "D012878", fit=TermFit.EXACT, approved=False)
    records = PostgresRecords(session)
    vocabulary = stored_vocabulary(records)

    placed = clinical_of(records, claim, vocabulary)

    assert [(c.label, [(s.kind, s.score) for s in c.sources]) for c in placed.categories] == [
        ("Psoriasis", [("term", 0.93)])
    ]
    assert coverage(records, [claim], vocabulary).from_term_only == 1
    result = compare(session, [claim], vocabulary)
    assert (result.agrees, result.agrees_by_term_only) == (1, 1)


def test_a_trial_and_the_claims_own_condition_both_name_a_category(session: Session):
    store(session, *TREE)
    claim = new_claim(session, "cream-a")
    with_trial(session, claim, "NCT00000001", "D011565")
    with_condition_term(session, claim, "D011565", fit=TermFit.EXACT)
    records = PostgresRecords(session)

    placed = clinical_of(records, claim, stored_vocabulary(records))

    assert [[s.kind for s in c.sources] for c in placed.categories] == [["term", "trial"]]
    assert compare(session, [claim], stored_vocabulary(records)).agrees_by_term_only == 0


@pytest.mark.parametrize(("trial_term", "term_only"), [("D012878", 1), ("D012871", 0)])
def test_agreement_counts_only_evidence_in_the_filed_group(session, trial_term, term_only):
    store(session, *TREE)
    claim = new_claim(session, "cream-provenance", vertical="skin-and-hair")
    with_condition_term(session, claim, "D011565", fit=TermFit.EXACT)
    with_trial(session, claim, "NCT00000001", trial_term)

    result = compare(session, [claim], stored_vocabulary(PostgresRecords(session)))

    assert (result.agrees, result.agrees_by_term_only) == (1, term_only)


@pytest.mark.parametrize("parent_available", [True, False])
def test_prepare_places_a_new_condition_term_before_first_export(
    session, tmp_path, parent_available
):
    from claim_support import Sources, Vocabulary, prepare
    from store_support import assert_same_export
    from thenwhat.sources.base import SourceError
    from thenwhat.sources.mesh import LabelledTerm

    class MeshWithCondition(FakeMesh, Vocabulary):
        vocabulary_year = "2026"

        def terms_labelled(self, name):
            return [LabelledTerm("D011565", "Psoriasis")] if name == "Plaque psoriasis" else []

        def unresolved_entry_terms(self, name):
            return []

        def term(self, identifier, *, force=False):
            if identifier == "D900001":
                if not parent_available:
                    raise SourceError("The vocabulary did not answer.")
                broader = {
                    "@id": f"{YEAR}/D900001",
                    "label": "Synthetic parent",
                    "treeNumber": f"{YEAR}/C17.800.859",
                    "broaderDescriptor": f"{YEAR}/D012871",
                }
                return SourceRecord(
                    "mesh", identifier, f"{YEAR}/{identifier}", {"term": broader}, NOW
                )
            record = super().term(identifier, force=force)
            if record is not None and identifier == "D011565":
                record.payload["term"]["broaderDescriptor"] = f"{YEAR}/D900001"
            return record

    claim = new_claim(session, "cream-first-export")
    prepare(session, Sources(vocabulary=MeshWithCondition()))
    approved = session.scalars(select(ClaimTerm).where(ClaimTerm.claim_id == claim.id)).all()
    assert [(t.external_id, t.review_state) for t in approved] == [
        ("D011565", ReviewState.APPROVED)
    ]
    exported = assert_same_export(session, tmp_path, NOW)
    categories = exported["claims"][0]["clinical_categories"]
    if parent_available:
        assert [c["identifier"] for c in categories] == ["D011565"]
        assert any(node["identifier"] == "D900001" for node in exported["clinical"]["nodes"])
    else:
        assert categories is None
        assert exported["clinical"]["claims_not_read"] == 1


def test_the_comparison_counts_every_claim_once(session: Session):
    """Scenarios: Counts; Suggested group differs; Nothing to compare"""
    claims = three_claims(session)

    result = compare(session, claims, stored_vocabulary(PostgresRecords(session)))

    assert (result.agrees, len(result.disagreeing), result.no_category) == (1, 1, 1)
    assert result.claims == 3
    assert result.per_topic == {"skin-and-hair": 1, "cancer": 1}
    row = result.disagreeing[0]
    assert (row.slug, row.vertical, [topic.topic for topic in row.topics]) == (
        "cream-b",
        "skin-and-hair",
        ["cancer"],
    )
    # Nothing was filed anew.
    assert {claim.vertical for claim in claims} == {"skin-and-hair"}


def test_prepare_is_told_how_many_claims_disagree(session: Session, monkeypatch):
    """Scenario: Prepare reports disagreements"""
    claims = three_claims(session)

    assert "the topic mapping's MeSH records are not read" in prepared_line(session, claims)

    monkeypatch.setattr("thenwhat.clinical.service.configuration_problems", lambda vocabulary: [])
    assert prepared_line(session, claims) == (
        "1 of the 3 claims prepared is filed under a group its clinical categories do not"
        " derive; `thenwhat clinical compare --disagreeing` lists them."
    )
    assert prepared_line(session, claims[:1]) == (
        "No claim prepared is filed under a group its clinical categories do not derive."
    )


# --- the commands ------------------------------------------------------------------------


@pytest.fixture
def run(session: Session, monkeypatch: pytest.MonkeyPatch):
    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    monkeypatch.setattr("thenwhat.cli.entry.open_session", test_session)
    monkeypatch.setattr("thenwhat.cli.clinical.make_mesh", lambda session: FakeMesh())

    def invoke(*arguments: str) -> Result:
        return CliRunner().invoke(app, ["clinical", *arguments], env={"COLUMNS": "400"})

    return invoke


def test_tree_reads_what_is_missing_and_says_what_is_stored(run, session: Session):
    claim = new_claim(session, "cream-a")
    with_trial(session, claim, "NCT00000001", "D011565")

    result = run("tree", "cream-a")

    assert result.exit_code == 0, result.output
    # Its own three, and the two of the mapping's descriptors the fake service holds.
    assert "Read 4 MeSH records for 1 claim. 4 descriptors stored, of MeSH 2026." in result.output
    assert "which the stored MeSH vocabulary does not hold." in result.output


def test_tree_refuses_an_unknown_claim(run):
    result = run("tree", "no-such-claim")

    assert result.exit_code == 1 and "no-such-claim" in result.output


def test_categories_lists_one_claims_categories_with_their_sources(run, session: Session):
    store(session, *TREE)
    claim = new_claim(session, "cream-a")
    with_trial(session, claim, "NCT00000001", "D011565")

    result = run("categories", "cream-a")

    assert result.exit_code == 0, result.output
    assert "cream-a: 1 clinical category" in result.output
    assert "Psoriasis (D011565): trial NCT00000001" in result.output


def test_categories_counts_every_claim_and_refuses_an_unknown_one(run, session: Session):
    three_claims(session)

    counted = run("categories")
    refused = run("categories", "no-such-claim")

    assert (
        "3 claims: 2 with a category from a trial, 0 from papers only, 0 only from the"
        " reading of their own condition, 1 with none" in counted.output
    )
    assert refused.exit_code == 1 and "no-such-claim" in refused.output


def test_compare_is_refused_until_the_mappings_descriptors_are_read(run, session: Session):
    result = run("compare")

    assert result.exit_code == 1
    assert "Run `thenwhat clinical tree` first." in result.output


def test_compare_lists_the_disagreeing_claims_as_rows(run, session: Session, monkeypatch):
    three_claims(session)
    monkeypatch.setattr("thenwhat.cli.clinical.configuration_problems", lambda vocabulary=None: [])

    report = run("compare", "--disagreeing", "--uncovered")
    rows = run("compare", "--tsv")

    assert report.exit_code == 0, report.output
    assert (
        "3 claims: 1 filed under a group their categories derive, 1 under another group."
        " Nothing to compare: 1 with no category, 0 whose categories no topic covers,"
        " 0 not yet read." in report.output
    )
    assert (
        "cream-b: filed under Skin and hair; its categories derive Cancer (MeSH: Skin Neoplasms)"
        in (report.output)
    )
    assert rows.output.strip().split("\t") == [
        "cream-b",
        "EX cream-b",
        "Skin cancer",
        "skin-and-hair",
        "cancer",
        "Skin Neoplasms (D012878)",
    ]
