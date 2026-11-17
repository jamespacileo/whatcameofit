"""Trials and papers an upstream verifier matched exactly to an article, handed on with
what the page names: `_article_identifiers`, `candidates_named_in_article` and the
input `claim_named_records` reads. The papers and trials are made up."""

from dataclasses import replace
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from test_named_in_article import DOI, NAMED, TRIAL, named
from test_related_research import NOW, PHRASE_SEARCH, FakePapers, Reading, find, new_claim, paper
from thenwhat.claims.entry import add_article
from thenwhat.claimsteps.articles import ClaimNamedRecords
from thenwhat.claimsteps.inputs import Inputs
from thenwhat.resolve.named import _article_identifiers
from thenwhat.resolve.papers import rescore_papers
from thenwhat.resolve.reasons import NAMED_IN_ARTICLE, VERIFIED_IN_ARTICLE
from thenwhat.work.ledger import fingerprint

BOTH = [NAMED_IN_ARTICLE, VERIFIED_IN_ARTICLE]


def test_identifiers_keep_the_citation_then_the_verified_reason():
    assert _article_identifiers([" nct1 "], ["NCT1", "nct2", ""], uppercase=True) == {
        "NCT1": (NAMED_IN_ARTICLE, VERIFIED_IN_ARTICLE),
        "NCT2": (VERIFIED_IN_ARTICLE,),
    }
    assert list(_article_identifiers(["10.1/B", "10.1/a"], ["10.1/c", "10.1/b"])) == [
        "10.1/b",
        "10.1/a",
        "10.1/c",
    ]
    assert _article_identifiers([], []) == {}


def test_verified_only_records_carry_only_the_verified_reason(session: Session):
    claim = new_claim(session)

    trial, cited = named(
        session,
        claim,
        registry_numbers=[],
        dois=[],
        verified_registry_numbers=[TRIAL.lower()],
        verified_dois=[DOI.upper()],
    )

    assert (trial.external_id, trial.reasons) == (TRIAL, [VERIFIED_IN_ARTICLE])
    assert cited.external_id == DOI and cited.reasons[-1] == VERIFIED_IN_ARTICLE
    assert NAMED_IN_ARTICLE not in cited.reasons


def test_a_record_both_named_and_verified_keeps_both_reasons_through_a_rescore(session: Session):
    claim = new_claim(session)

    trial, cited = named(session, claim, verified_registry_numbers=[TRIAL], verified_dois=[DOI])

    assert trial.reasons == BOTH
    assert cited.reasons[-2:] == BOTH
    rescore_papers(session, claim, papers=NAMED, backend=Reading(default=0.9), now=NOW)
    assert cited.reasons[-2:] == BOTH and cited.reasons.count(VERIFIED_IN_ARTICLE) == 1


def test_a_known_match_keeps_its_score_and_state_and_gains_the_reason_once(session: Session):
    claim = new_claim(session)
    [searched] = find(session, claim, FakePapers({PHRASE_SEARCH: [paper(DOI)]}), accept_above=0.8)
    before = (searched.score, searched.review_state)

    for _ in range(2):
        assert named(session, claim, registry_numbers=[], dois=[], verified_dois=[DOI]) == []

    assert (searched.score, searched.review_state) == before
    assert searched.reasons.count(VERIFIED_IN_ARTICLE) == 1
    assert NAMED_IN_ARTICLE not in searched.reasons


def test_a_verified_doi_waits_when_there_is_no_literature_source(session: Session):
    claim = new_claim(session)
    unasked: list[str] = []

    [trial] = named(
        session,
        claim,
        papers=None,
        registry_numbers=[],
        dois=[DOI],
        verified_registry_numbers=[TRIAL],
        verified_dois=[DOI, "10.1000/OTHER"],
        unasked_dois=unasked,
    )

    assert trial.reasons == [VERIFIED_IN_ARTICLE]
    assert unasked == [DOI, "10.1000/other"]


def test_a_verified_pmid_only_paper_reaches_normal_claim_matching(session: Session):
    claim = new_claim(session)
    original = paper(DOI)
    record = replace(
        original,
        external_id="W12345",
        url="https://openalex.org/W12345",
        payload={**original.payload, "doi": None, "ids": {"pmid": "12345"}},
    )
    source = Mock()
    source.paper.return_value = record

    (matched,) = named(
        session, claim, registry_numbers=[], dois=[], verified_pmids=["12345"], papers=source
    )

    source.paper.assert_called_once_with("pmid:12345")
    assert matched.external_id == "W12345"
    assert matched.reasons[-1] == VERIFIED_IN_ARTICLE


def test_a_verified_pmid_and_a_cited_doi_share_one_claim_match(session: Session):
    claim = new_claim(session)
    source = Mock()
    source.paper.return_value = paper(DOI)

    (matched,) = named(
        session, claim, registry_numbers=[], dois=[DOI], verified_pmids=["12345"], papers=source
    )

    assert matched.external_id == DOI
    assert matched.reasons[-2:] == BOTH


@pytest.mark.parametrize("papers_enabled", [True, False])
def test_the_step_input_is_unchanged_without_matches_and_changes_with_them(
    session: Session, papers_enabled: bool
):
    claim = new_claim(session)
    article = add_article(
        session,
        claim.slug,
        url="https://example.org/news",
        outlet="Example",
        title="News of a study",
        published_date=NOW.date(),
    )
    article.named_dois = [DOI]
    step = ClaimNamedRecords(reject_below=0.2, accept_above=0.8, papers_enabled=papers_enabled)

    without = step.read(Inputs(session, [claim.id]), claim.id)
    assert without == {"named": [DOI], "papers_enabled": papers_enabled}
    article.matched_registry_numbers = ["NCT00000001"]
    with_trial = step.read(Inputs(session, [claim.id]), claim.id)
    article.matched_registry_numbers = ["NCT00000002"]
    other_trial = step.read(Inputs(session, [claim.id]), claim.id)
    assert with_trial["matched"] == ["trial NCT00000001"]
    assert other_trial["matched"] == ["trial NCT00000002"]
    assert len({fingerprint(without), fingerprint(with_trial), fingerprint(other_trial)}) == 3
