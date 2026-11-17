import sqlite3
from contextlib import closing
from dataclasses import replace
from datetime import date
from unittest.mock import Mock

import pytest

from thenwhat.extract.evidence_search import (
    SearchPlan,
    SearchQuery,
    find_evidence,
    retrieve_candidates,
)
from thenwhat.extract.page import Page
from thenwhat.extract.retrieve import Retrieved
from thenwhat.resolve.registry_fanout import TrialHit


def test_native_plan_keeps_source_boundaries_and_publisher_identifiers(monkeypatch):
    model = Mock()
    model.run.return_value = SearchPlan(
        interventions=["examplemab"],
        indication="plaque psoriasis",
        queries=[
            SearchQuery(source="trial", terms="EXAMPLE-3 psoriasis"),
            SearchQuery(source="trial", terms="example-3 psoriasis"),
            SearchQuery(source="paper", terms="examplemab psoriasis"),
        ],
    )
    pubmed = Mock()
    pubmed.ranked_ids.side_effect = [["98765"], ["12345"]]
    search_trials = Mock(return_value=[TrialHit("NCT00001111", "title_phrase")])
    monkeypatch.setattr("thenwhat.extract.evidence_search.trial_fanout", search_trials)
    article = Retrieved(
        "A headline and body about the two treatments.",
        page=Page(
            text="Article body",
            registry_numbers=("NCT00002222",),
            dois=("10.1001/example.2026.2",),
            pubmed_ids=("98765",),
        ),
    )

    with closing(sqlite3.connect(":memory:")) as store:
        found = find_evidence(
            model,
            article,
            headline="Trial results",
            outlet="Example News",
            published=date(2026, 11, 17),
            trial_store=store,
            pubmed=pubmed,
        )

    assert model.run.call_args.kwargs["output_type"] is SearchPlan
    assert model.run.call_args.kwargs["native_json"] is True
    assert len(found.plan.queries) == 2
    search_trials.assert_called_once()
    assert [branch.candidates[0].identifier for branch in found.branches] == [
        "NCT00001111",
        "98765",
        "12345",
    ]
    assert pubmed.ranked_ids.call_args_list[0].args == ('"10.1001/example.2026.2"[aid]',)
    assert [hit.identifier for hit in found.publisher_identifiers] == [
        "NCT00002222",
        "98765",
        "10.1001/example.2026.2",
    ]


def test_publisher_links_remain_candidates_when_the_plan_has_no_intervention():
    plan = SearchPlan(
        interventions=[],
        indication=None,
        queries=[SearchQuery(source="trial", terms="do not guess a trial")],
    )
    article = Retrieved(
        "Article body",
        page=Page(
            text="Article body",
            registry_numbers=("NCT00002222",),
            dois=("10.1001/example.2026.2",),
        ),
    )
    pubmed = Mock()
    pubmed.ranked_ids.return_value = ["98765"]

    with closing(sqlite3.connect(":memory:")) as store:
        cited, branches = retrieve_candidates(plan, article, trial_store=store, pubmed=pubmed)

    assert [item.identifier for item in cited] == ["NCT00002222", "10.1001/example.2026.2"]
    assert [item.identifier for item in branches[0].candidates] == ["98765"]
    pubmed.ranked_ids.assert_called_once_with('"10.1001/example.2026.2"[aid]', limit=8)


def test_study_names_find_separate_trials_without_a_model_query():
    plan = SearchPlan(interventions=[], indication=None, queries=[])
    article = Retrieved(
        "In the Active TRACK study, examplemab showed a benefit in dermatitis. "
        "FENmock 1 & 2 Phase III pooled data show improvements with mocknib in sclerosis. "
        "Clinicians reported benefit with neurodine in the NeuroMOCK 2 study of depression. "
        "The PULSE was measured in another study."
    )
    with closing(sqlite3.connect(":memory:")) as store:
        store.executescript("""
            CREATE TABLE registry_trial (
                external_id TEXT, acronym TEXT, conditions TEXT, intervention_names TEXT
            );
            INSERT INTO registry_trial VALUES
                ('NCT00000001', 'Active-TRACK', '["Dermatitis"]', 'Examplemab'),
                ('NCT00000002', 'FENmock', '["Multiple sclerosis"]', 'Mocknib'),
                ('NCT00000003', 'FENmock 2', '["Multiple sclerosis"]', 'Mocknib'),
                ('NCT00000004', 'PULSE', '["Alport syndrome"]', 'Anothermab'),
                ('NCT00000005', 'NeuroMOCK', '["Depression"]', 'Neurodine'),
                ('NCT00000006', 'NeuroMOCK 2', '["Depression"]', 'Neurodine');
            """)
        cited, branches = retrieve_candidates(plan, article, trial_store=store, pubmed=None)

    assert cited == []
    [branch] = branches
    assert {hit.identifier: hit.matched_name for hit in branch.candidates} == {
        "NCT00000001": "Active-TRACK",
        "NCT00000002": "FENmock",
        "NCT00000003": "FENmock 2",
        "NCT00000006": "NeuroMOCK 2",
    }


def test_enrollment_recheck_replaces_a_different_size_sibling(monkeypatch):
    from thenwhat.decide.core import Decision
    from thenwhat.extract.evidence_verification import EvidenceVerdict, _recheck_enrollment, _Trial

    earlier = EvidenceVerdict(
        kind="nct", identifier="NCT00001111", choice="exact", p_exact=0.85, accepted=True
    )
    larger = EvidenceVerdict(
        kind="nct", identifier="NCT00002222", choice="exact", p_exact=0.60, accepted=False
    )
    trials = [
        _Trial(earlier.identifier, "Smaller study", 200),
        _Trial(larger.identifier, "Larger study", 1090),
    ]
    check = Mock(return_value=[Decision("yes", {"yes": 0.91, "no": 0.09}, 0.91, 1)])
    monkeypatch.setattr("thenwhat.extract.evidence_verification.decide_many", check)

    updated = _recheck_enrollment(Mock(), Mock(), "Trial of 1,100", 1100, trials, [earlier, larger])

    assert check.call_count == 1
    assert check.call_args.kwargs["items"] == [("nct:NCT00002222", "Larger study")]
    assert not updated[0].accepted
    assert updated[1].accepted
    assert updated[1].p_exact == 0.91


def test_cohort_recheck_requires_a_second_protocol_cue_after_an_exact_match(monkeypatch):
    from thenwhat.extract.evidence_verification import (
        EvidenceVerdict,
        _recheck_reported_cohort,
        _Trial,
    )

    exact = EvidenceVerdict(
        kind="nct", identifier="NCT00001111", choice="exact", p_exact=0.99, accepted=True
    )
    sibling = EvidenceVerdict(
        kind="nct", identifier="NCT00002222", choice="unsupported", p_exact=0.01, accepted=False
    )
    trials = [
        _Trial(exact.identifier, "An exact study", 200, labels=("ACTIVE TRACK",)),
        _Trial(sibling.identifier, "An earlier study", 130, products=("examplemab",)),
    ]
    check = Mock()
    monkeypatch.setattr("thenwhat.extract.evidence_verification.decide_many", check)

    result = _recheck_reported_cohort(
        Mock(),
        Mock(),
        headline="ACTIVE TRACK reports results",
        article="The phase 3 ACTIVE TRACK trial showed improved clearance with examplemab.",
        trials=trials,
        verdicts=[exact, sibling],
    )

    check.assert_not_called()
    assert result == [exact, sibling]


def test_a_sponsor_backed_rename_only_enriches_matching_product_and_sponsor():
    from thenwhat.extract.evidence_verification import (
        TrialProductAlias,
        _Trial,
        _with_product_aliases,
    )

    alias = TrialProductAlias.model_validate(
        {
            "sponsor": "Example Oncology",
            "registered_name": "EX-204",
            "reported_name": "Examplemab",
            "source_url": "https://www.example.com/press/renamed-study-product",
        }
    )
    trial = _Trial(
        "NCT00001111", "A Phase 1 trial", 200, products=("EX-204",), sponsor="Example Oncology Inc."
    )
    article = " examplemab clinical trial reports outcomes "
    enriched = _with_product_aliases(trial, article, [alias])

    assert enriched.products == ("EX-204", "Examplemab")
    assert str(alias.source_url) in enriched.text
    assert _with_product_aliases(trial, " a trial for examplemabine ", [alias]) == trial
    separate = replace(trial, sponsor="Example Oncology Partners")
    assert _with_product_aliases(separate, article, [alias]) == separate


def test_paper_mappings_keep_only_accepted_identifiers(monkeypatch):
    from thenwhat.decide.core import Decision
    from thenwhat.extract.evidence_search import Candidate, EvidenceSearch
    from thenwhat.extract.evidence_verification import verify_evidence
    from thenwhat.sources.pubmed import Paper

    pubmed = Mock()
    pubmed.papers_by_ids.return_value = [
        Paper("1", (), {"title": "Exact trial findings"}, "10.5555/Accepted"),
        Paper("2", (), {"title": "A different publication"}, "10.5555/background"),
        Paper("3", (), {"title": "An independently reported trial"}, None),
    ]
    answers = [
        Decision("exact", {"exact": 0.91}, 0.91, 1),
        Decision("background", {"exact": 0.05}, 0.95, 1),
        Decision("exact", {"exact": 0.90}, 0.90, 1),
    ]
    monkeypatch.setattr(
        "thenwhat.extract.evidence_verification.decide_many", Mock(return_value=answers)
    )
    found = EvidenceSearch(
        plan=SearchPlan(interventions=["examplemab"], indication="example", queries=[]),
        planning_seconds=0,
        publisher_identifiers=[
            Candidate(kind="pmid", identifier=pmid, strategy="publisher")
            for pmid in ("1", "2", "3")
        ],
        branches=[],
    )
    with closing(sqlite3.connect(":memory:")) as store:
        verified = verify_evidence(
            Mock(),
            Mock(),
            Retrieved("Study description"),
            found,
            trial_store=store,
            pubmed=pubmed,
            headline="Fictional results",
            require_papers=True,
        )

    assert {v.identifier for v in verified.verdicts if v.accepted} == {"1", "3"}
    assert verified.paper_dois == {"1": "10.5555/accepted"}


def test_article_matching_can_require_pubmed_to_finish():
    from thenwhat.sources.pubmed import PeakHours

    pubmed = Mock()
    pubmed.ranked_ids.side_effect = PeakHours("off-peak only")
    plan = SearchPlan(
        interventions=["examplemab"],
        indication="example",
        queries=[SearchQuery(source="paper", terms="examplemab")],
    )
    with closing(sqlite3.connect(":memory:")) as store, pytest.raises(PeakHours):
        retrieve_candidates(
            plan,
            Retrieved("Study description"),
            trial_store=store,
            pubmed=pubmed,
            require_papers=True,
        )
