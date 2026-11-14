"""Related papers, the trials and origin paper they lead to, and organisations: tested
through the functions of `thenwhat.resolve` on a real database, with a fake literature
search and decision backend, and recorded Europe PMC and ROR responses.

Scenario names are from openspec related-research and entity-resolution. The papers are
made up: only their shape is OpenAlex's.
"""

from datetime import UTC, date, datetime
from typing import Any

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entities import add_entity, add_search_phrase, entities_of
from thenwhat.claims.entry import add_article, add_claim
from thenwhat.claims.status import refresh_status
from thenwhat.db.models import Claim, DecisionLog, Entity, EntityMatch
from thenwhat.decide.core import BackendAnswer, DecisionFailed
from thenwhat.domain import ClaimStatus, Decider, EntityType, EventType, ReviewState
from thenwhat.events.fetch import fetch_claim
from thenwhat.export.build import build_export
from thenwhat.resolve.organisations import match_organisations
from thenwhat.resolve.papers import choose_origin, find_papers, trials_from_papers
from thenwhat.resolve.reasons import (
    INDICATION_NAMED,
    NAMED_IN_TITLE,
    NAMED_INSTITUTION,
    PUBLISHED_BEFORE_REPORT,
    paper_reasons,
)
from thenwhat.review.decisions import record_decision
from thenwhat.review.queue import decide_item, pending_items
from thenwhat.sources import openalex
from thenwhat.sources.base import AllowanceUsedUp, SourceRecord
from thenwhat.sources.crossref import Notice
from thenwhat.sources.europepmc import EuropePmc
from thenwhat.sources.ror import Ror

NOW = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
SLUG = "tourette-wrist-stimulation"
REPORTED = date(2023, 6, 5)
CONTACT = "ops@thenwhat.test"
NAME_SEARCH = "Wrist-worn stimulation device Tourette syndrome"
PHRASE_SEARCH = "median nerve stimulation Tourette syndrome"


def paper(
    doi: str | None,
    title: str = "Median nerve stimulation for tics",
    *,
    published: str = "2023-06-01",
    kind: str = "article",
    abstract: str = "A made-up abstract about Tourette syndrome.",
    institution: tuple[str, str] | None = ("Example University", "https://ror.org/01example9"),
    work: str = "W1",
    pubmed_id: str | None = None,
) -> SourceRecord:
    """A made-up paper in the shape OpenAlex returns."""
    authorship: dict[str, Any] = {"author": {"display_name": "Ada Example"}, "institutions": []}
    if institution is not None:
        authorship["institutions"] = [{"display_name": institution[0], "ror": institution[1]}]
    payload = {
        "id": f"https://openalex.org/{work}",
        "doi": f"https://doi.org/{doi}" if doi else None,
        "title": title,
        "publication_year": int(published[:4]),
        "publication_date": published,
        "type": kind,
        "primary_location": {"source": {"display_name": "Journal of Examples"}},
        "authorships": [authorship],
        "abstract_inverted_index": {word: [n] for n, word in enumerate(abstract.split())},
        "ids": {"pmid": f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}"} if pubmed_id else {},
    }
    return SourceRecord(
        "openalex", doi or work, f"https://doi.org/{doi}" if doi else payload["id"], payload, NOW
    )


class FakePapers:
    """A literature search that answers each search from a table."""

    def __init__(self, results: dict[str, list[SourceRecord]] | None = None) -> None:
        self.results = results or {}
        self.searched: list[str] = []
        self.looked_up: list[str] = []

    def search_papers(self, words: str, limit: int = 20) -> list[SourceRecord]:
        self.searched.append(words)
        return self.results.get(words, [])[:limit]

    def paper(self, external_id: str) -> SourceRecord | None:
        self.looked_up.append(external_id)
        return next(
            (
                r
                for records in self.results.values()
                for r in records
                if r.external_id == external_id
            ),
            None,
        )


class Reading:
    """A batch backend that gives each paper the probability its title is given here of
    being a study of the claim's intervention for its indication."""

    name = "fake"

    def __init__(self, by_title: dict[str, float] | None = None, default: float = 0.9) -> None:
        self.by_title = by_title or {}
        self.default = default
        self.calls: list[tuple[str, list[str]]] = []
        self.origin: tuple[str, float] | None = None
        self.states: list[str] = []

    def answer_many(
        self, step: str, intro: str, question: str, items: list[str], options: list[str]
    ) -> list[BackendAnswer | None]:
        self.calls.append((step, items))
        return [self._one(item, options) for item in items]

    def _one(self, item: str, options: list[str]) -> BackendAnswer:
        p = next((p for title, p in self.by_title.items() if title in item), self.default)
        other = "other_indication" if "other_indication" in options else options[-1]
        choice = options[0] if p >= 0.5 else other
        rest = [o for o in options if o not in (options[0], other)]
        given = {options[0]: p, other: 1 - p} | {o: 0.0 for o in rest}
        return BackendAnswer(choice, given)

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        self.states.append(state)
        assert step == "origin_paper" and self.origin is not None
        choice, p = self.origin
        rest = (1 - p) / (len(options) - 1)
        return BackendAnswer(choice, {o: p if o == choice else rest for o in options})


class Broken:
    name = "broken"

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        raise RuntimeError("no model")


def new_claim(session: Session, slug: str = SLUG) -> Claim:
    claim = add_claim(
        session,
        slug=slug,
        headline="Wrist device calms tics",
        vertical="mouth-and-teeth",
        intervention="Wrist-worn stimulation device",
        indication="Tourette syndrome",
        summary="A wrist-worn device reduced tics in a trial.",
    )
    add_article(
        session,
        slug,
        url="https://news.example.org/2023/tics",
        outlet="Example News",
        title="t",
        published_date=REPORTED,
    )
    add_search_phrase(session, slug, "Wrist-worn stimulation device", "median nerve stimulation")
    session.refresh(claim)
    return claim


def find(session: Session, claim: Claim, papers: FakePapers, backend=None, **rules: float):
    return find_papers(
        session, claim, papers=papers, backend=backend or Reading(), now=NOW, **rules
    )


def paper_matches(session: Session) -> list[EntityMatch]:
    return list(
        session.scalars(
            select(EntityMatch)
            .where(EntityMatch.source_name == "openalex")
            .order_by(EntityMatch.id)
        )
    )


FOUR = [paper(f"10.1000/p{n}", f"Paper {n}", work=f"W{n}") for n in range(1, 5)]


# --- paper candidates ------------------------------------------------------------


def test_claim_whose_article_gave_no_doi_gets_paper_candidates(session: Session):
    """Scenario: Claim whose article gave no DOI"""
    claim = new_claim(session)
    papers = FakePapers({PHRASE_SEARCH: FOUR})

    added = find(session, claim, papers)

    assert [m.external_id for m in added] == [f"10.1000/p{n}" for n in range(1, 5)]
    assert papers.searched == [NAME_SEARCH, PHRASE_SEARCH]
    [intervention] = entities_of(session, claim)
    assert all(m.entity_id == intervention.id and m.source_name == "openalex" for m in added)
    assert added[0].record_summary == "Paper 1. 2023. article. Journal of Examples"
    assert "abstract" not in (added[0].record_summary or "")


def test_paper_found_by_two_terms_is_one_candidate(session: Session):
    """Scenario: Paper found by two terms"""
    claim = new_claim(session)
    papers = FakePapers({NAME_SEARCH: FOUR[:1], PHRASE_SEARCH: FOUR[:2]})

    added = find(session, claim, papers)

    assert [m.external_id for m in added] == ["10.1000/p1", "10.1000/p2"]
    assert find(session, claim, papers) == []
    assert len(paper_matches(session)) == 2


def test_search_that_finds_nothing_stores_no_candidate(session: Session):
    """Scenario: Search that finds nothing"""
    claim = new_claim(session)
    backend = Reading()

    assert find(session, claim, FakePapers(), backend) == []
    assert paper_matches(session) == []
    assert backend.calls == []


def test_paper_without_a_doi_is_known_by_the_sources_identifier(session: Session):
    claim = new_claim(session)

    [added] = find(session, claim, FakePapers({PHRASE_SEARCH: [paper(None, work="W77")]}))

    assert added.external_id == "W77"


def test_a_claim_keeps_at_most_twenty_papers_in_turn_from_each_term(session: Session):
    claim = new_claim(session)
    by_name = [paper(f"10.1/n{n}", work=f"W1{n:02}") for n in range(20)]
    by_phrase = [paper(f"10.1/p{n}", work=f"W2{n:02}") for n in range(20)]

    added = find(session, claim, FakePapers({NAME_SEARCH: by_name, PHRASE_SEARCH: by_phrase}))

    assert len(added) == 20
    assert [m.external_id for m in added[:4]] == ["10.1/n0", "10.1/p0", "10.1/n1", "10.1/p1"]
    assert find(session, claim, FakePapers({NAME_SEARCH: [paper("10.1/new")]})) == []


def test_rejected_papers_leave_room_for_others_and_are_not_added_again(session: Session):
    claim = new_claim(session)
    twenty = [paper(f"10.1/p{n}", f"Paper {n:02}", work=f"W{n}") for n in range(20)]
    low = {"Paper 00": 0.01, "Paper 01": 0.01}
    first = find(
        session, claim, FakePapers({PHRASE_SEARCH: twenty}), Reading(low), reject_below=0.05
    )
    assert [m.review_state for m in first[:3]] == [
        ReviewState.REJECTED,
        ReviewState.REJECTED,
        ReviewState.PENDING,
    ]
    newer = [paper(f"10.1/new{n}", f"New {n}", work=f"W9{n}") for n in range(5)]

    added = find(session, claim, FakePapers({PHRASE_SEARCH: [*twenty[:2], *newer]}))

    # Two were rejected, so two fit; the rejected ones stay rejected and are not re-added.
    assert [m.external_id for m in added] == ["10.1/new0", "10.1/new1"]
    kept = [m for m in paper_matches(session) if m.review_state is not ReviewState.REJECTED]
    assert len(kept) == 20 and len(paper_matches(session)) == 22


def test_allowance_used_up_before_any_paper_is_found_is_the_reason_given(session: Session):
    class UsedUp(FakePapers):
        def search_papers(self, words: str, limit: int = 20) -> list[SourceRecord]:
            raise AllowanceUsedUp("used up")

    with pytest.raises(AllowanceUsedUp):
        find(session, new_claim(session), UsedUp())
    assert paper_matches(session) == []


# --- scoring -----------------------------------------------------------------------


def test_twenty_papers_are_scored_in_one_backend_call_with_a_log_entry_each(session: Session):
    claim = new_claim(session)
    twenty = [paper(f"10.1/p{n}", f"Paper {n}", work=f"W{n}") for n in range(20)]
    backend = Reading()

    added = find(session, claim, FakePapers({PHRASE_SEARCH: twenty}), backend)

    assert [(step, len(items)) for step, items in backend.calls] == [("paper_match", 20)]
    logged = session.scalars(select(DecisionLog).where(DecisionLog.step == "paper_match")).all()
    assert sorted(entry.input_ref for entry in logged) == sorted(
        f"entity_match:{m.id}" for m in added
    )
    assert logged[0].options == [
        "match",
        "other_indication",
        "review_or_commentary",
        "unrelated",
    ]
    assert all(m.score == pytest.approx(0.9) for m in added)
    # The model is shown the abstract; nothing stored holds it.
    assert "A made-up abstract" in backend.calls[0][1][0]
    assert all("made-up abstract" not in str(entry.output) for entry in logged)


def test_papers_that_cannot_be_scored_are_not_kept(session: Session):
    claim = new_claim(session)

    with pytest.raises(DecisionFailed):
        find(session, claim, FakePapers({PHRASE_SEARCH: FOUR}), Broken())
    assert paper_matches(session) == []


# --- reasons -------------------------------------------------------------------------


def reasons_of(record: SourceRecord, **overrides: Any) -> list[str]:
    given: dict[str, Any] = {
        "terms": ["Wrist-worn stimulation device", "median nerve stimulation"],
        "indication": "Tourette syndrome",
        "institutions": [],
        "first_reported": None,
    }
    return paper_reasons(openalex.describe(record), **(given | overrides))


PLAIN = paper(
    "10.1/x",
    "A study of something",
    abstract="Nothing relevant.",
    institution=None,
    published="2024-01-01",
)


def test_paper_with_no_sign_carries_no_reasons():
    """Scenario: Paper with no sign"""
    assert (
        reasons_of(PLAIN, institutions=["Example University"], first_reported=date(2020, 1, 1))
        == []
    )


def test_search_phrase_in_the_title_is_a_reason():
    record = paper("10.1/x", "Rhythmic MEDIAN NERVE  stimulation in adults", abstract="None.")

    assert reasons_of(record) == [NAMED_IN_TITLE]


def test_indication_in_the_title_or_abstract_is_a_reason():
    in_abstract = paper("10.1/x", "A study", abstract="Adults with tourette syndrome took part.")
    in_title = paper("10.1/x", "Tics in Tourette syndrome", abstract="None.")

    assert reasons_of(in_abstract, institutions=[]) == [INDICATION_NAMED]
    assert reasons_of(in_title) == [INDICATION_NAMED]


def test_paper_from_the_institution_the_article_named_carries_that_reason():
    """Scenario: Paper from the institution the article named"""
    record = paper("10.1/x", "A study", abstract="None.")

    assert reasons_of(record, institutions=["example university"]) == [NAMED_INSTITUTION]
    assert reasons_of(record, institution_ids=frozenset({"01example9"})) == [NAMED_INSTITUTION]
    assert reasons_of(record, institutions=["Another University"]) == []


def test_publication_on_or_before_the_first_report_is_a_reason():
    record = paper("10.1/x", "A study", abstract="None.", institution=None, published="2023-06-05")

    assert reasons_of(record, first_reported=REPORTED) == [PUBLISHED_BEFORE_REPORT]
    assert reasons_of(record, first_reported=date(2023, 6, 4)) == []


def test_a_stored_candidate_carries_the_reasons_found_for_it(session: Session):
    claim = new_claim(session)
    add_entity(session, SLUG, type=EntityType.INSTITUTION, name="Example University")

    [added] = find(session, claim, FakePapers({PHRASE_SEARCH: [paper("10.1000/p1")]}))

    assert added.reasons == [
        NAMED_IN_TITLE,
        INDICATION_NAMED,
        NAMED_INSTITUTION,
        PUBLISHED_BEFORE_REPORT,
    ]


# --- rules ---------------------------------------------------------------------------

SCORES = {"Paper 1": 0.97, "Paper 2": 0.9, "Paper 3": 0.85, "Paper 4": 0.5}


def test_several_confident_papers_are_all_approved_by_rule(session: Session):
    """Scenarios: Several confident papers; Below the threshold"""
    claim = new_claim(session)

    added = find(
        session, claim, FakePapers({PHRASE_SEARCH: FOUR}), Reading(SCORES), accept_above=0.8
    )

    assert [(m.review_state, m.reviewed_by) for m in added[:3]] == [
        (ReviewState.APPROVED, Decider.RULE)
    ] * 3
    assert (added[3].review_state, added[3].reviewed_by) == (ReviewState.PENDING, None)


def test_high_score_and_no_reason_is_still_approved(session: Session):
    """Scenario: High score and no reason"""
    claim = new_claim(session)

    [added] = find(
        session,
        claim,
        FakePapers({PHRASE_SEARCH: [PLAIN]}),
        Reading(default=0.97),
        accept_above=0.8,
    )

    assert added.reasons == []
    assert added.review_state is ReviewState.APPROVED


def test_paper_scored_near_zero_is_rejected_by_rule_and_an_operator_can_reject_another(
    session: Session,
):
    claim = new_claim(session)

    low, high = find(
        session,
        claim,
        FakePapers({PHRASE_SEARCH: FOUR[:2]}),
        Reading({"Paper 1": 0.01}),
        reject_below=0.05,
        accept_above=0.8,
    )
    decide_item(session, "match", high.id, ReviewState.REJECTED, now=NOW)

    assert (low.review_state, low.reviewed_by) == (ReviewState.REJECTED, Decider.RULE)
    assert (high.review_state, high.reviewed_by) == (ReviewState.REJECTED, Decider.HUMAN)


def test_a_threshold_of_zero_turns_the_approval_rule_off(session: Session):
    claim = new_claim(session)

    added = find(session, claim, FakePapers({PHRASE_SEARCH: FOUR}), Reading(default=0.99))

    assert all(m.review_state is ReviewState.PENDING for m in added)


def test_approved_papers_do_not_change_the_status_or_show_as_registry_matches(session: Session):
    """Scenario: Claim with papers and no trial"""
    claim = new_claim(session)
    record_decision(claim, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    before = refresh_status(session, claim, as_of=NOW.date(), now=NOW).status

    find(session, claim, FakePapers({PHRASE_SEARCH: FOUR[:3]}), accept_above=0.8)

    assert refresh_status(session, claim, as_of=NOW.date(), now=NOW).status is before
    # Until papers are exported under their own heading, none is listed as a match.
    [exported] = build_export(session, now=NOW).claims
    assert exported.matches == []


# --- review queue --------------------------------------------------------------------


def test_queue_shows_a_paper_with_its_kind_year_reasons_and_indication_label(session: Session):
    claim = new_claim(session)
    record = paper("10.1000/p1", "Median nerve stimulation for tremor", kind="preprint")
    find(session, claim, FakePapers({PHRASE_SEARCH: [record, PLAIN]}), Reading(default=0.2))

    first, second = pending_items(session, claim_slug=SLUG, kind="match")

    assert "related paper 10.1000/p1" in first.assertion
    assert "for another indication" in first.assertion
    assert first.reasons == (NAMED_IN_TITLE, INDICATION_NAMED, PUBLISHED_BEFORE_REPORT)
    assert "named_in_title, indication_named" in first.assertion
    assert (
        first.detail == "Median nerve stimulation for tremor. 2023. preprint. Journal of Examples"
    )
    assert first.source_url == "https://doi.org/10.1000/p1"
    assert second.reasons == () and "Reasons: none found by rule" in second.assertion


# --- registry numbers of an approved paper -------------------------------------------


class Registry:
    def __init__(self) -> None:
        self.fetched: list[str] = []

    def fetch_trial(self, nct_id: str) -> SourceRecord | None:
        self.fetched.append(nct_id)
        payload = {
            "protocolSection": {
                "identificationModule": {"nctId": nct_id, "briefTitle": "A trial"},
                "conditionsModule": {"conditions": ["Tourette Syndrome"]},
            }
        }
        return SourceRecord(
            "clinicaltrials.gov", nct_id, f"https://clinicaltrials.gov/study/{nct_id}", payload, NOW
        )


def europe_pmc(session: Session, fake_time, answer: dict[str, Any]) -> EuropePmc:
    return EuropePmc(
        session,
        contact_email=CONTACT,
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=answer)),
        time=fake_time,
    )


def approved_paper(session: Session, claim: Claim, doi: str) -> EntityMatch:
    [added] = find(session, claim, FakePapers({PHRASE_SEARCH: [paper(doi)]}), accept_above=0.8)
    assert added.review_state is ReviewState.APPROVED
    return added


def from_papers(session: Session, claim: Claim, numbers: EuropePmc, registry: Registry):
    return trials_from_papers(
        session,
        claim,
        numbers=numbers,
        registry=registry,
        backend=Reading(default=0.7),
        now=NOW,
        accept_above=0.8,
    )


def test_registry_number_of_an_approved_trial_report_becomes_a_trial_candidate(
    session: Session, fake_time, fixture_json
):
    """Scenario: Trial report"""
    claim = new_claim(session)
    approved_paper(session, claim, "10.1056/nejmoa2206038")
    numbers = europe_pmc(session, fake_time, fixture_json("europepmc/paper_nejmoa2206038.json"))
    registry = Registry()

    [candidate] = from_papers(session, claim, numbers, registry)

    assert (candidate.source_name, candidate.external_id) == ("clinicaltrials.gov", "NCT04184622")
    assert candidate.review_state is ReviewState.PENDING
    assert candidate.score == pytest.approx(0.7)
    assert candidate.record_summary == "A trial. For: Tourette Syndrome."
    assert from_papers(session, claim, numbers, registry) == []
    assert registry.fetched == ["NCT04184622"]


def test_review_listing_many_trials_contributes_no_candidate(
    session: Session, fake_time, fixture_json
):
    """Scenario: Review listing many trials"""
    claim = new_claim(session)
    approved_paper(session, claim, "10.1056/nejmoa2206038")
    review = fixture_json("europepmc/paper_nejmoa2206038.json")
    review["resultList"]["result"][0]["abstractText"] = " ".join(
        f"NCT0000000{n}" for n in range(1, 6)
    )
    registry = Registry()

    assert from_papers(session, claim, europe_pmc(session, fake_time, review), registry) == []
    assert registry.fetched == []


def test_a_number_the_registry_answers_with_a_trial_the_claim_has_adds_nothing(
    session: Session, fake_time, fixture_json
):
    claim = new_claim(session)
    approved_paper(session, claim, "10.1056/nejmoa2206038")
    numbers = europe_pmc(session, fake_time, fixture_json("europepmc/paper_nejmoa2206038.json"))
    [intervention] = entities_of(session, claim)
    session.add(
        EntityMatch(
            entity_id=intervention.id,
            source_name="clinicaltrials.gov",
            external_id="NCT09999999",
            score=0.5,
        )
    )
    session.flush()

    class Renumbered(Registry):
        def fetch_trial(self, nct_id: str) -> SourceRecord | None:
            return super().fetch_trial("NCT09999999")

    assert from_papers(session, claim, numbers, Renumbered()) == []


def test_paper_without_a_doi_is_asked_for_by_its_pubmed_number(
    session: Session, fake_time, fixture_json
):
    claim = new_claim(session)
    indexed = paper(None, work="W77", pubmed_id="35658024")
    unindexed = paper(None, "Another paper", work="W78")
    papers = FakePapers({PHRASE_SEARCH: [indexed, unindexed]})
    find(session, claim, papers, accept_above=0.8)
    asked: list[str] = []

    def answer(request: httpx.Request) -> httpx.Response:
        asked.append(request.url.params["query"])
        return httpx.Response(200, json=fixture_json("europepmc/paper_nejmoa2206038.json"))

    numbers = EuropePmc(
        session, contact_email=CONTACT, transport=httpx.MockTransport(answer), time=fake_time
    )

    def read(source: FakePapers | None) -> list[EntityMatch]:
        return trials_from_papers(
            session,
            claim,
            numbers=numbers,
            registry=Registry(),
            backend=Reading(default=0.7),
            now=NOW,
            papers=source,
            accept_above=0.8,
        )

    # Without the literature source there is no PubMed number to ask by.
    assert read(None) == []
    [candidate] = read(papers)

    assert candidate.external_id == "NCT04184622"
    assert asked == ["EXT_ID:35658024 AND SRC:MED"]
    assert papers.looked_up == ["W77", "W78"]


def test_a_pending_paper_is_not_read_for_registry_numbers(
    session: Session, fake_time, fixture_json
):
    claim = new_claim(session)
    find(session, claim, FakePapers({PHRASE_SEARCH: [paper("10.1056/nejmoa2206038")]}))
    numbers = europe_pmc(session, fake_time, fixture_json("europepmc/paper_nejmoa2206038.json"))

    assert from_papers(session, claim, numbers, Registry()) == []


# --- origin paper --------------------------------------------------------------------

BEFORE = paper("10.1000/before", "The trial report", published="2023-05-29", work="W1")
AFTER = paper("10.1000/after", "A later paper", published="2024-06-01", work="W2")


def with_two_approved_papers(session: Session) -> tuple[Claim, FakePapers]:
    claim = new_claim(session)
    papers = FakePapers({PHRASE_SEARCH: [BEFORE, AFTER]})
    find(session, claim, papers, accept_above=0.8)
    return claim, papers


def origin(session: Session, claim: Claim, papers: FakePapers, backend: Reading):
    return choose_origin(session, claim, papers=papers, backend=backend, now=NOW, accept_above=0.8)


def test_confident_choice_becomes_the_origin_paper_decided_by_a_rule(session: Session):
    """Scenarios: One paper predates the report; Confident choice"""
    claim, papers = with_two_approved_papers(session)
    backend = Reading()
    backend.origin = ("10.1000/before", 0.9)

    chosen = origin(session, claim, papers, backend)

    assert chosen is not None
    assert (chosen.type, chosen.name, chosen.doi) == (
        EntityType.PAPER,
        "The trial report",
        "10.1000/before",
    )
    assert chosen.is_origin_paper
    confirmed = session.scalars(select(EntityMatch).where(EntityMatch.entity_id == chosen.id)).one()
    assert (confirmed.external_id, confirmed.review_state, confirmed.reviewed_by) == (
        "10.1000/before",
        ReviewState.APPROVED,
        Decider.RULE,
    )
    assert confirmed.score == pytest.approx(0.9)
    [asked] = session.scalars(select(DecisionLog).where(DecisionLog.step == "origin_paper"))
    assert asked.options == ["10.1000/before", "none"]
    assert "10.1000/after" not in backend.states[0]


def test_unsure_choice_leaves_the_claim_without_an_origin_paper_and_is_not_asked_twice(
    session: Session,
):
    """Scenario: Unsure choice"""
    claim, papers = with_two_approved_papers(session)
    backend = Reading()
    backend.origin = ("10.1000/before", 0.5)

    assert origin(session, claim, papers, backend) is None
    assert origin(session, claim, papers, backend) is None

    assert not any(entity.is_origin_paper for entity in entities_of(session, claim))
    assert len(backend.states) == 1


def test_a_choice_of_none_sets_no_origin_paper(session: Session):
    claim, papers = with_two_approved_papers(session)
    backend = Reading()
    backend.origin = ("none", 0.95)

    assert origin(session, claim, papers, backend) is None


def test_claim_that_has_an_origin_paper_is_not_asked_about(session: Session):
    """Scenario: Claim that has an origin paper"""
    claim, papers = with_two_approved_papers(session)
    session.add(
        Entity(claim_id=claim.id, type=EntityType.PAPER, name="Cited paper", is_origin_paper=True)
    )
    session.flush()
    backend = Reading()

    assert origin(session, claim, papers, backend) is None
    assert backend.states == [] and papers.looked_up == []


def test_no_decision_is_asked_when_no_approved_paper_predates_the_report(session: Session):
    claim = new_claim(session)
    papers = FakePapers({PHRASE_SEARCH: [AFTER]})
    find(session, claim, papers, accept_above=0.8)
    backend = Reading()

    assert origin(session, claim, papers, backend) is None
    assert backend.states == []


class EuropePmcIndex:
    """Europe PMC as `fetch` reads it: the origin paper by DOI and the papers citing it."""

    def __init__(self, citing: list[SourceRecord]) -> None:
        self.citing = citing
        self.asked: list[str] = []

    def paper(self, doi: str) -> SourceRecord | None:
        self.asked.append(doi)
        return _indexed(doi, "The trial report", "2023-05-29")

    def citing_papers(self, paper: SourceRecord) -> list[SourceRecord]:
        return self.citing


def _indexed(doi: str, title: str, published: str) -> SourceRecord:
    payload = {
        "id": doi.rsplit("/", 1)[-1],
        "source": "MED",
        "doi": doi,
        "title": title,
        "abstractText": "",
        "firstPublicationDate": published,
        "authorList": {"author": [{"fullName": "Example A"}]},
    }
    return SourceRecord("europepmc", doi, f"https://europepmc.org/article/MED/{doi}", payload, NOW)


class Retractions:
    def __init__(self, by_doi: dict[str, list[Notice]]) -> None:
        self.by_doi = by_doi

    def notices(self, doi: str) -> list[Notice]:
        return self.by_doi.get(doi.lower(), [])


class NoTrials:
    def fetch_trial(self, nct_id: str) -> SourceRecord | None:
        return None


def fetch_evidence(session: Session, claim: Claim, literature: EuropePmcIndex, notices=None):
    return fetch_claim(
        session,
        claim,
        trials=NoTrials(),
        literature=literature,
        notices=notices or Retractions({}),
        threshold=0.95,
        now=NOW,
    )


def test_origin_paper_set_by_rule_lets_fetch_find_follow_ups_and_a_retraction(session: Session):
    """From a literature search to a status: the claim's article gave no DOI, a paper is
    found and approved by rule, chosen as the origin paper by rule, and its retraction
    then reaches the claim's status through an approved evidence event."""
    claim, papers = with_two_approved_papers(session)
    record_decision(claim, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    follow_up = _indexed("10.1000/later", "A second study by the same group", "2024-02-01")
    literature = EuropePmcIndex([follow_up])
    notice = Notice("retraction", date(2025, 4, 5), "10.1000/retraction-notice")
    retractions = Retractions({"10.1000/before": [notice]})

    # Approved papers alone give fetch nothing to follow, and the status stays put.
    assert fetch_evidence(session, claim, literature, retractions) == []
    before = claim.current_status
    assert before is not ClaimStatus.RETRACTED and literature.asked == []

    backend = Reading()
    backend.origin = ("10.1000/before", 0.9)
    assert origin(session, claim, papers, backend) is not None
    created = fetch_evidence(session, claim, literature, retractions)

    assert literature.asked == ["10.1000/before"]
    by_type = {event.type: event for event in created}
    assert set(by_type) == {EventType.FOLLOWUP_PAPER, EventType.RETRACTION}
    assert by_type[EventType.FOLLOWUP_PAPER].external_id == "10.1000/later"
    retraction = by_type[EventType.RETRACTION]
    assert (retraction.external_id, retraction.reviewed_by) == ("10.1000/before", Decider.RULE)
    assert retraction.source_url == "https://doi.org/10.1000/retraction-notice"
    assert claim.current_status is ClaimStatus.RETRACTED
    # The status rests on the event, and the event on the match a rule approved.
    confirmed = session.get(EntityMatch, retraction.entity_match_id)
    assert confirmed is not None
    assert (confirmed.source_name, confirmed.reviewed_by) == ("openalex", Decider.RULE)

    # The operator removes the origin paper by rejecting its match: the status goes back.
    decide_item(session, "match", confirmed.id, ReviewState.REJECTED, now=NOW)
    assert claim.current_status is before


# --- organisations -------------------------------------------------------------------


def ror_answering(session: Session, fake_time, answers: dict[str, dict[str, Any]]):
    requests: list[httpx.Request] = []

    def route(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=answers[request.url.params["affiliation"]])

    source = Ror(
        session, contact_email=CONTACT, transport=httpx.MockTransport(route), time=fake_time
    )
    return source, requests


def test_university_named_in_the_article_gets_one_candidate_scored_by_the_registry(
    session: Session, fake_time, fixture_json
):
    """Scenarios: University named in the article; Name the registry does not know;
    Claim with a named researcher"""
    claim = new_claim(session)
    add_entity(session, SLUG, type=EntityType.INSTITUTION, name="University of Nottingham")
    add_entity(session, SLUG, type=EntityType.COMPANY, name="Zzqxv Institute of Nowhere Qqxzj")
    add_entity(session, SLUG, type=EntityType.PERSON, name="Ada Example")
    registry, requests = ror_answering(
        session,
        fake_time,
        {
            "University of Nottingham": fixture_json(
                "ror/affiliation_university_of_nottingham.json"
            ),
            "Zzqxv Institute of Nowhere Qqxzj": fixture_json("ror/affiliation_unknown.json"),
        },
    )
    backend = Reading()

    [candidate] = match_organisations(session, claim, registry=registry)

    assert (candidate.source_name, candidate.external_id) == ("ror", "01ee9ar58")
    assert candidate.score == 1.0
    assert candidate.review_state is ReviewState.PENDING
    assert candidate.record_summary == (
        "University of Nottingham. United Kingdom. https://www.nottingham.ac.uk/"
    )
    # One request per institution and company; none for the person, and no model.
    assert [request.url.params["affiliation"] for request in requests] == [
        "University of Nottingham",
        "Zzqxv Institute of Nowhere Qqxzj",
    ]
    assert backend.calls == []
    assert match_organisations(session, claim, registry=registry) == []
