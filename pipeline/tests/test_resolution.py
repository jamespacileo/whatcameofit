"""Entities and candidate matches, tested through `thenwhat.claims.entities` and
`resolve_claim` with fake registries and a fake decision backend on a real database.

Scenario names are from openspec entity-resolution and decision-steps.
"""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entities import (
    EntityNotFound,
    add_entity,
    add_search_phrase,
    add_synonym,
    entities_of,
    set_origin_paper,
)
from thenwhat.claims.entry import DuplicateClaim, InvalidField, add_claim
from thenwhat.claims.status import refresh_status
from thenwhat.db.models import Claim, DecisionLog, EntityMatch, EntitySubstance, EvidenceEvent
from thenwhat.decide.core import BackendAnswer, DecisionFailed
from thenwhat.decide.steps import suggest_evidence_stage
from thenwhat.domain import (
    ClaimStatus,
    Decider,
    EntityType,
    EventType,
    ReviewState,
    TrialPhase,
)
from thenwhat.resolve.codes import Listing, give_development_codes
from thenwhat.resolve.service import combination_search, redo_rule_approvals, resolve_claim
from thenwhat.review.decisions import record_decision
from thenwhat.sources.base import SourceRecord, UnsearchableTerm

NOW = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
DOI = "10.1000/example.2018.1"


def trial(nct_id: str, title: str = "A trial", condition: str = "Tooth Agenesis") -> SourceRecord:
    payload = {
        "protocolSection": {
            "identificationModule": {"nctId": nct_id, "briefTitle": title},
            "armsInterventionsModule": {"interventions": [{"name": "EX-1"}]},
            "conditionsModule": {"conditions": [condition]},
        }
    }
    return SourceRecord(
        "clinicaltrials.gov", nct_id, f"https://clinicaltrials.gov/study/{nct_id}", payload, NOW
    )


class FakeTrials:
    """A trial registry that answers each search term from a table."""

    def __init__(self, results: dict[str, list[SourceRecord]]) -> None:
        self.results = results
        self.searched: list[str] = []
        self.conditions: list[str | None] = []

    def search_trials(self, intervention: str, condition: str | None = None) -> list[SourceRecord]:
        self.searched.append(intervention)
        self.conditions.append(condition)
        return self.results.get(intervention, [])

    def search_phrase(self, phrase: str, condition: str | None) -> list[SourceRecord]:
        self.searched.append(phrase)
        self.conditions.append(condition)
        return self.results.get(phrase, []) if condition else []


class FakeDois:
    def __init__(self, known: set[str]) -> None:
        self.known = known

    def work(self, doi: str) -> SourceRecord | None:
        if doi not in self.known:
            return None
        return SourceRecord("crossref", doi, f"https://doi.org/{doi}", {"title": ["A paper"]}, NOW)


class Scoring:
    """A decision backend that gives every candidate the same probability of being a match."""

    name = "fake"

    def __init__(self, match_probability: float = 0.7, stage: str = "animal") -> None:
        self.match_probability = match_probability
        self.stage = stage
        self.states: list[str] = []

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        self.states.append(state)
        if step == "entity_match":
            p = self.match_probability
            choice = "match" if p >= 0.5 else "not_a_match"
            given = {"match": p, "not_a_match": 1 - p}
            return BackendAnswer(choice, {o: given.get(o, 0.0) for o in options})
        others = (1 - 0.7) / (len(options) - 1)
        return BackendAnswer(self.stage, {o: 0.7 if o == self.stage else others for o in options})


class ByCondition:
    """A decision backend that reads the record: a match only when it names tooth agenesis."""

    name = "fake"

    def __init__(self) -> None:
        self.states: list[str] = []

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        self.states.append(state)
        record = state.split("Candidate record", 1)[-1]
        choice = "match" if "Tooth Agenesis" in record else "other_indication"
        return BackendAnswer(
            choice,
            {
                o: 0.96 if o == choice else 0.0 if o == "not_what_is_tested" else 0.02
                for o in options
            },
        )


class Broken:
    name = "broken"

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        raise RuntimeError("no model")


def new_claim(session: Session, slug: str = "tooth-regrowth-ex1", **overrides) -> Claim:
    values = {
        "slug": slug,
        "headline": "Antibody regrows teeth in mice",
        "vertical": "mouth-and-teeth",
        "intervention": "EX-1 antibody",
        "indication": "tooth agenesis",
    }
    return add_claim(session, **(values | overrides))


def resolve(session: Session, claim: Claim, trials=None, dois=None, backend=None, **options):
    return resolve_claim(
        session,
        claim,
        trials=trials or FakeTrials({}),
        dois=dois or FakeDois(set()),
        backend=backend or Scoring(),
        now=NOW,
        **options,
    )


def matches(session: Session) -> list[EntityMatch]:
    return list(session.scalars(select(EntityMatch).order_by(EntityMatch.id)))


# --- entities --------------------------------------------------------------------


def test_entity_of_each_type_can_be_added(session: Session):
    claim = new_claim(session)

    add_entity(session, claim.slug, type=EntityType.COMPANY, name="Example Biopharma")
    add_entity(session, claim.slug, type=EntityType.PAPER, name="A paper", doi=DOI)

    listed = {(e.type, e.name, e.doi) for e in entities_of(session, claim)}
    assert (EntityType.COMPANY, "Example Biopharma", None) in listed
    assert (EntityType.PAPER, "A paper", DOI) in listed


def test_added_synonym_is_used_in_later_registry_searches(session: Session):
    """Scenario: Compound renamed"""
    claim = new_claim(session)
    add_synonym(session, claim.slug, "EX-1 antibody", "TRG-999")
    trials = FakeTrials({})

    resolve(session, claim, trials=trials)

    assert trials.searched == ["EX-1 antibody", "TRG-999"]


def test_synonym_is_not_added_twice(session: Session):
    claim = new_claim(session)
    add_synonym(session, claim.slug, "EX-1 antibody", "TRG-999")

    entity = add_synonym(session, claim.slug, "ex-1 ANTIBODY", " trg-999 ")

    assert entity.synonyms == ["TRG-999"]


def test_synonym_that_makes_two_claims_the_same_is_refused(session: Session):
    new_claim(session)
    new_claim(session, "other-claim", intervention="TRG-999")

    with pytest.raises(DuplicateClaim):
        add_synonym(session, "tooth-regrowth-ex1", "EX-1 antibody", "TRG-999")


def test_synonym_for_an_unknown_entity_is_refused(session: Session):
    claim = new_claim(session)

    with pytest.raises(EntityNotFound):
        add_synonym(session, claim.slug, "No such thing", "x")


def test_second_origin_paper_replaces_the_first(session: Session):
    """Scenario: Second origin paper"""
    claim = new_claim(session)
    add_entity(session, claim.slug, type=EntityType.PAPER, name="First paper")
    add_entity(session, claim.slug, type=EntityType.PAPER, name="Second paper")
    set_origin_paper(session, claim.slug, "First paper")

    set_origin_paper(session, claim.slug, "Second paper")

    origin = [e.name for e in entities_of(session, claim) if e.is_origin_paper]
    assert origin == ["Second paper"]


def test_only_a_paper_can_be_the_origin_paper(session: Session):
    claim = new_claim(session)

    with pytest.raises(EntityNotFound):
        set_origin_paper(session, claim.slug, "EX-1 antibody")


# --- candidate matches -------------------------------------------------------------


def test_each_search_term_contributes_its_trials(session: Session):
    """Scenario: Intervention with two synonyms"""
    claim = new_claim(session)
    add_synonym(session, claim.slug, "EX-1 antibody", "EX-1")
    add_synonym(session, claim.slug, "EX-1 antibody", "TRG-999")
    trials = FakeTrials(
        {
            "EX-1 antibody": [trial("NCT00000001")],
            "EX-1": [trial("NCT00000002")],
            "TRG-999": [trial("NCT00000003")],
        }
    )

    resolve(session, claim, trials=trials)

    assert [(m.source_name, m.external_id) for m in matches(session)] == [
        ("clinicaltrials.gov", "NCT00000001"),
        ("clinicaltrials.gov", "NCT00000002"),
        ("clinicaltrials.gov", "NCT00000003"),
    ]


def test_a_term_the_registry_cannot_search_for_is_reported_and_the_others_still_run(
    session: Session,
):
    claim = new_claim(session)
    add_synonym(session, "tooth-regrowth-ex1", "EX-1 antibody", "TRG-035")

    class Refusing(FakeTrials):
        def search_trials(self, intervention: str, condition: str | None = None):
            if intervention == "EX-1 antibody":
                raise UnsearchableTerm(intervention, "Too complicated query", "clinicaltrials.gov")
            return super().search_trials(intervention, condition)

    trials = Refusing({"TRG-035": [trial("NCT00000002")]})
    reported: list[str] = []

    added = resolve(session, claim, trials=trials, unsearchable=lambda t: reported.append(t.term))

    assert [match.external_id for match in added] == ["NCT00000002"]
    assert reported == ["EX-1 antibody"]
    # Left to itself the failure is raised, never passed over in silence.
    with pytest.raises(UnsearchableTerm):
        resolve(session, claim, trials=trials)


def test_trial_found_by_two_terms_is_one_candidate(session: Session):
    """Scenario: Same trial found by two terms"""
    claim = new_claim(session)
    add_synonym(session, claim.slug, "EX-1 antibody", "EX-1")
    same = trial("NCT00000001")

    resolve(session, claim, trials=FakeTrials({"EX-1 antibody": [same], "EX-1": [same]}))

    assert len(matches(session)) == 1


def test_paper_with_a_doi_is_looked_up(session: Session):
    claim = new_claim(session)
    add_entity(session, claim.slug, type=EntityType.PAPER, name="A paper", doi=DOI)
    add_entity(session, claim.slug, type=EntityType.PAPER, name="No DOI given")

    resolve(session, claim, dois=FakeDois({DOI}))

    assert [(m.source_name, m.external_id) for m in matches(session)] == [("crossref", DOI)]


def test_doi_the_registry_does_not_know_gives_no_candidate(session: Session):
    claim = new_claim(session)
    add_entity(session, claim.slug, type=EntityType.PAPER, name="A paper", doi=DOI)

    resolve(session, claim, dois=FakeDois(set()))

    assert matches(session) == []


def test_high_scoring_match_stays_pending(session: Session):
    """Scenario: High-scoring match"""
    claim = new_claim(session)

    resolve(
        session,
        claim,
        trials=FakeTrials({"EX-1 antibody": [trial("NCT00000001")]}),
        backend=Scoring(0.99),
    )

    [match] = matches(session)
    assert (match.score, match.review_state) == (pytest.approx(0.99), ReviewState.PENDING)


def test_low_scoring_match_stays_pending_and_visible(session: Session):
    """Scenario: Low-scoring match"""
    claim = new_claim(session)

    resolve(
        session,
        claim,
        trials=FakeTrials({"EX-1 antibody": [trial("NCT00000001")]}),
        backend=Scoring(0.05),
    )

    [match] = matches(session)
    assert (match.score, match.review_state) == (pytest.approx(0.05), ReviewState.PENDING)


def test_rejected_match_found_again_stays_rejected(session: Session):
    """Scenario: Rejected match found again"""
    claim = new_claim(session)
    trials = FakeTrials({"EX-1 antibody": [trial("NCT00000001")]})
    resolve(session, claim, trials=trials)
    record_decision(matches(session)[0], ReviewState.REJECTED, by=Decider.HUMAN, now=NOW)

    again = resolve(session, claim, trials=trials)

    assert again == []
    assert [m.review_state for m in matches(session)] == [ReviewState.REJECTED]


def test_resolve_returns_only_the_new_candidates(session: Session):
    claim = new_claim(session)
    resolve(session, claim, trials=FakeTrials({"EX-1 antibody": [trial("NCT00000001")]}))

    new = resolve(
        session,
        claim,
        trials=FakeTrials({"EX-1 antibody": [trial("NCT00000001"), trial("NCT00000002")]}),
    )

    assert [m.external_id for m in new] == ["NCT00000002"]


# --- decision steps ----------------------------------------------------------------


def test_candidate_score_is_the_logged_probability_of_a_match(session: Session):
    """Scenario: Scoring a candidate match"""
    claim = new_claim(session)
    backend = Scoring(0.83)

    resolve(
        session,
        claim,
        trials=FakeTrials({"EX-1 antibody": [trial("NCT00000001", "EX-1 in adults")]}),
        backend=backend,
    )

    [match] = matches(session)
    [entry] = session.scalars(select(DecisionLog)).all()
    assert (entry.step, entry.input_ref) == ("entity_match", f"entity_match:{match.id}")
    assert entry.options == ["match", "other_indication", "not_what_is_tested", "not_a_match"]
    assert entry.output is not None
    assert (
        match.score == pytest.approx(entry.output["probabilities"]["match"]) == pytest.approx(0.83)
    )
    assert "EX-1 antibody" in backend.states[0] and "EX-1 in adults" in backend.states[0]


def test_candidate_keeps_what_its_registry_record_says(session: Session):
    claim = new_claim(session)
    add_entity(session, claim.slug, type=EntityType.PAPER, name="The origin paper", doi=DOI)
    record = trial("NCT00000001", "EX-1 in adults with missing teeth")
    record.payload["protocolSection"]["designModule"] = {"phases": ["PHASE1", "PHASE2"]}
    record.payload["protocolSection"]["statusModule"] = {"overallStatus": "ACTIVE_NOT_RECRUITING"}

    resolve(session, claim, trials=FakeTrials({"EX-1 antibody": [record]}), dois=FakeDois({DOI}))

    of_the_trial, of_the_paper = matches(session)
    assert of_the_trial.record_summary == (
        "EX-1 in adults with missing teeth. For: Tooth Agenesis. Tests: EX-1."
        " Phase 1/Phase 2, active not recruiting."
    )
    assert of_the_paper.record_summary == "A paper"
    # The same record field by field, for the site to lay out (openspec registry-record-rows).
    # A recruiting state is never carried as such: the trial is "under way".
    assert of_the_trial.record_facts == {
        "title": "EX-1 in adults with missing teeth",
        "conditions": ["Tooth Agenesis"],
        "interventions": ["EX-1"],
        "phases": ["phase_1", "phase_2"],
        "state": "under_way",
        "participants": None,
    }
    assert of_the_paper.record_facts is None


def two_trials() -> FakeTrials:
    return FakeTrials(
        {
            "EX-1 antibody": [
                trial("NCT00000001", "EX-1 in tooth agenesis"),
                trial("NCT00000002", "EX-1 in lung cancer", condition="Lung Cancer"),
            ]
        }
    )


def test_candidate_scored_under_the_threshold_is_rejected_by_rule(session: Session):
    """Scenario: Candidate scored near zero"""
    claim = new_claim(session)

    resolve(session, claim, trials=two_trials(), backend=ByCondition(), reject_below=0.05)

    for_the_claim, for_another = matches(session)
    assert for_the_claim.review_state is ReviewState.PENDING
    assert (for_another.review_state, for_another.reviewed_by, for_another.reviewed_at) == (
        ReviewState.REJECTED,
        Decider.RULE,
        NOW,
    )
    # A rule's rejection is not a person's answer.
    labels = session.scalars(select(DecisionLog.human_label)).all()
    assert all(label is None for label in labels)


def test_candidate_scored_exactly_at_the_threshold_stays_pending(session: Session):
    claim = new_claim(session)
    found = FakeTrials({"EX-1 antibody": [trial("NCT00000001")]})

    resolve(session, claim, trials=found, backend=Scoring(0.05), reject_below=0.05)

    assert matches(session)[0].review_state is ReviewState.PENDING


def test_without_a_threshold_no_candidate_is_rejected_by_rule(session: Session):
    claim = new_claim(session)

    resolve(session, claim, trials=two_trials(), backend=ByCondition())

    assert [match.review_state for match in matches(session)] == [ReviewState.PENDING] * 2


def test_rescoring_applies_the_rule_to_what_it_scores(session: Session):
    claim = new_claim(session)
    resolve(session, claim, trials=two_trials(), backend=Scoring(0.99))

    resolve(
        session, claim, trials=two_trials(), backend=ByCondition(), rescore=True, reject_below=0.05
    )

    for_the_claim, for_another = matches(session)
    assert for_the_claim.review_state is ReviewState.PENDING
    assert (for_another.review_state, for_another.reviewed_by) == (
        ReviewState.REJECTED,
        Decider.RULE,
    )


def test_registry_search_carries_the_claims_indication(session: Session):
    """Scenario: Broad intervention name"""
    claim = new_claim(session)
    add_synonym(session, claim.slug, "EX-1 antibody", "EX-1")
    trials = FakeTrials({})

    resolve(session, claim, trials=trials)

    assert trials.searched == ["EX-1 antibody", "EX-1"]
    assert trials.conditions == ["tooth agenesis", "tooth agenesis"]


def test_trial_of_the_same_intervention_for_another_condition_scores_low(session: Session):
    """Scenario: Same drug, another condition"""
    claim = new_claim(session)
    backend = ByCondition()
    trials = FakeTrials(
        {
            "EX-1 antibody": [
                trial("NCT00000001", "EX-1 in tooth agenesis"),
                trial("NCT00000002", "EX-1 in lung cancer", condition="Lung Cancer"),
            ]
        }
    )

    resolve(session, claim, trials=trials, backend=backend)

    for_the_claim, for_another = matches(session)
    assert for_the_claim.score == pytest.approx(0.96)
    assert for_another.score == pytest.approx(0.02)
    # The backend was shown the claim's indication and each record's conditions, and asked
    # about both the intervention and the indication.
    assert "Indication: tooth agenesis" in backend.states[1]
    assert "Lung Cancer" in backend.states[1]
    assert "for the claim's indication" in backend.states[1]
    entries = session.scalars(select(DecisionLog).order_by(DecisionLog.id)).all()
    assert [entry.output["choice"] for entry in entries if entry.output] == [
        "match",
        "other_indication",
    ]


def test_paper_is_only_asked_whether_it_is_the_same_paper(session: Session):
    claim = new_claim(session)
    add_entity(session, claim.slug, type=EntityType.PAPER, name="The origin paper", doi=DOI)

    resolve(session, claim, dois=FakeDois({DOI}))

    [entry] = session.scalars(select(DecisionLog)).all()
    assert entry.options == ["match", "not_a_match"]


def test_rescoring_replaces_scores_of_pending_candidates_the_search_still_returns(
    session: Session,
):
    claim = new_claim(session)
    found = {
        "EX-1 antibody": [
            trial("NCT00000001", "EX-1 in lung cancer", condition="Lung Cancer"),
            trial("NCT00000002", "EX-1 in bladder cancer", condition="Bladder Cancer"),
        ]
    }
    resolve(session, claim, trials=FakeTrials(found), backend=Scoring(0.99))
    pending, decided = matches(session)
    record_decision(decided, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    session.flush()

    added = resolve(session, claim, trials=FakeTrials(found), backend=ByCondition(), rescore=True)

    assert added == []
    assert pending.score == pytest.approx(0.02)
    # A candidate someone has decided keeps the score it was decided on.
    assert decided.score == pytest.approx(0.99)


def test_without_rescoring_existing_candidates_keep_their_scores(session: Session):
    claim = new_claim(session)
    found = {"EX-1 antibody": [trial("NCT00000001", condition="Lung Cancer")]}
    resolve(session, claim, trials=FakeTrials(found), backend=Scoring(0.99))

    resolve(session, claim, trials=FakeTrials(found), backend=ByCondition())

    assert matches(session)[0].score == pytest.approx(0.99)


def test_confident_decision_still_leaves_the_candidate_pending(session: Session):
    """Scenario: Confident decision"""
    claim = new_claim(session)

    resolve(
        session,
        claim,
        trials=FakeTrials({"EX-1 antibody": [trial("NCT00000001")]}),
        backend=Scoring(0.99),
    )

    assert matches(session)[0].review_state is ReviewState.PENDING


def test_failed_scoring_stores_no_candidates(session: Session):
    claim = new_claim(session)

    with pytest.raises(DecisionFailed):
        resolve(
            session,
            claim,
            trials=FakeTrials({"EX-1 antibody": [trial("NCT00000001")]}),
            backend=Broken(),
        )

    assert matches(session) == []


def test_suggested_stage_is_logged_and_the_claims_stage_stays_empty(session: Session):
    """Scenario: Suggested but unconfirmed stage"""
    claim = new_claim(session)

    decision = suggest_evidence_stage(session, Scoring(stage="animal"), claim, now=NOW)

    [entry] = session.scalars(select(DecisionLog)).all()
    assert decision.choice == "animal"
    assert (entry.step, entry.input_ref, entry.human_label) == (
        "evidence_stage",
        f"claim:{claim.id}",
        None,
    )
    assert entry.options == ["in_vitro", "animal", "early_human", "late_human"]
    assert claim.evidence_stage is None


# --- approval by rule (openspec auto-publish) ---------------------------------------


def test_confident_candidate_is_approved_by_rule(session: Session):
    """Scenario: Confident candidate"""
    claim = new_claim(session)

    resolve(session, claim, trials=two_trials(), backend=ByCondition(), accept_above=0.8)

    for_the_claim, for_another = matches(session)
    assert (for_the_claim.review_state, for_the_claim.reviewed_by) == (
        ReviewState.APPROVED,
        Decider.RULE,
    )
    # Read as another indication: never approved by rule, whatever its score.
    assert for_another.review_state is ReviewState.PENDING
    labels = session.scalars(select(DecisionLog.human_label)).all()
    assert all(label is None for label in labels)


class InTheTrialNotTested:
    """A backend that reads every record as a trial the intervention is in without being
    what it tests, while still giving a match some weight."""

    name = "fake"

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        given = {"not_what_is_tested": 0.5, "match": 0.45, "not_a_match": 0.05}
        return BackendAnswer("not_what_is_tested", {o: given.get(o, 0.0) for o in options})


def test_a_trial_the_intervention_is_in_but_does_not_test_is_never_approved_by_rule(
    session: Session,
):
    """Scenario: Comparator or background treatment"""
    claim = new_claim(session)

    resolve(session, claim, trials=two_trials(), backend=InTheTrialNotTested(), accept_above=0.4)

    assert [match.score for match in matches(session)] == [pytest.approx(0.45)] * 2
    assert {match.review_state for match in matches(session)} == {ReviewState.PENDING}
    asked = session.scalars(select(DecisionLog).where(DecisionLog.step == "entity_match")).first()
    assert asked is not None and "not_what_is_tested" in asked.options


def test_candidate_between_the_thresholds_stays_pending(session: Session):
    """Scenario: Between the thresholds"""
    claim = new_claim(session)
    found = FakeTrials({"EX-1 antibody": [trial("NCT00000001")]})

    resolve(session, claim, trials=found, backend=Scoring(0.4), reject_below=0.05, accept_above=0.8)

    assert matches(session)[0].review_state is ReviewState.PENDING


def test_without_an_accept_threshold_nothing_is_approved_by_rule(session: Session):
    """Scenario: High-scoring match"""
    claim = new_claim(session)
    found = FakeTrials({"EX-1 antibody": [trial("NCT00000001")]})

    resolve(session, claim, trials=found, backend=Scoring(0.99))

    assert matches(session)[0].review_state is ReviewState.PENDING


# --- search phrases --------------------------------------------------------------


def test_trial_found_only_by_a_search_phrase_becomes_a_candidate(session: Session):
    """Scenario: Trial found only by a search phrase"""
    device = "Wrist-worn median nerve stimulation device"
    claim = new_claim(
        session, slug="tics-wrist-stimulation", intervention=device, indication="Tourette syndrome"
    )
    add_search_phrase(session, claim.slug, device, "median nerve stimulation")
    trials = FakeTrials(
        {
            device: [trial("NCT00000011", "A nausea band")],
            "median nerve stimulation": [trial("NCT00000012", "Stimulation for tics")],
        }
    )

    resolve(session, claim, trials=trials)

    assert [match.external_id for match in matches(session)] == ["NCT00000011", "NCT00000012"]
    assert trials.searched == [device, "median nerve stimulation"]


def test_a_combination_is_also_searched_for_all_its_treatments_together(session: Session):
    """Scenario: A combination"""
    claim = new_claim(
        session,
        slug="aspirin-avelumab",
        intervention="aspirin plus avelumab",
        indication="Triple-negative breast cancer",
    )
    together = "(aspirin) AND (avelumab)"
    trials = FakeTrials({together: [trial("NCT00000021", "Aspirin and avelumab")]})

    resolve(session, claim, trials=trials)

    assert trials.searched == ["aspirin plus avelumab", together]
    assert [match.external_id for match in matches(session)] == ["NCT00000021"]


@pytest.mark.parametrize(
    ("name", "search"),
    [
        (
            "UV1 vaccine plus pembrolizumab with GM-CSF",
            "(UV1 vaccine) AND (pembrolizumab) AND (GM-CSF)",
        ),
        ("emtricitabine/tenofovir", "(emtricitabine) AND (tenofovir)"),
        ("nivolumab + ipilimumab", "(nivolumab) AND (ipilimumab)"),
        ("semaglutide", None),
        ("EX-1 antibody", None),
    ],
)
def test_combination_search(name: str, search: str | None):
    assert combination_search(name) == search


def test_a_search_phrase_is_kept_apart_from_the_names(session: Session):
    claim = new_claim(session)

    entity = add_search_phrase(session, claim.slug, "EX-1 antibody", "tooth regrowth antibody")
    add_search_phrase(session, claim.slug, "EX-1 antibody", "Tooth  regrowth antibody")

    assert entity.search_phrases == ["tooth regrowth antibody"]
    assert entity.synonyms == []


def test_a_generic_word_is_refused_as_a_search_phrase(session: Session):
    claim = new_claim(session)

    with pytest.raises(InvalidField):
        add_search_phrase(session, claim.slug, "EX-1 antibody", "the device")


# --- development codes -------------------------------------------------------------


def substance(identifier: str, name: str, *listed: tuple[str, str]) -> SourceRecord:
    """A substance as the registry of substances returns it: its names, each with a kind."""
    payload = {
        "substance": {"uuid": identifier, "_name": name, "approvalID": "UNII000001"},
        "names": [{"name": listed_name, "type": kind} for listed_name, kind in listed],
    }
    return SourceRecord("gsrs", identifier, f"https://gsrs.test/{identifier}", payload, NOW)


class FakeSubstances:
    """A registry of substances that answers each exact name from a table."""

    name = "gsrs"

    def __init__(self, by_name: dict[str, list[SourceRecord]]) -> None:
        self.by_name = by_name
        self.asked: list[str] = []

    def substances_named(self, name: str) -> list[SourceRecord]:
        self.asked.append(name)
        return self.by_name.get(name, [])


EX1 = substance(
    "s-1", "Exampletinib", ("exampletinib", "of"), ("Toothgrow", "bn"), ("ABC-123", "cd")
)


def test_development_codes_are_kept_with_their_source_and_searched_in_the_indication(
    session: Session,
):
    """Scenario: Trial filed under a development code"""
    claim = add_claim(
        session,
        slug="tooth-regrowth",
        headline="Drug regrows teeth",
        vertical="mouth-and-teeth",
        intervention="exampletinib",
        indication="tooth agenesis",
    )
    registry = FakeSubstances({"exampletinib": [EX1]})
    trials = FakeTrials({"ABC-123": [trial("NCT00000007", "ABC-123 in adults")]})
    backend = Scoring(0.9)

    answer = give_development_codes(session, claim, substances=registry)
    added = resolve_claim(
        session, claim, trials=trials, dois=FakeDois(set()), backend=backend, now=NOW
    )

    assert answer is not None and answer.listing is Listing.ONE_SUBSTANCE
    assert answer.codes == ["ABC-123"]
    [intervention] = entities_of(session, claim)
    kept = session.get(EntitySubstance, intervention.id)
    assert kept is not None
    assert (kept.source_name, kept.external_id, kept.codes) == ("gsrs", "s-1", ["ABC-123"])
    assert kept.payload == EX1.payload and kept.fetched_at == NOW
    # The code is not a name: it is not shown as one, and is searched like a phrase.
    assert intervention.synonyms == [] and intervention.search_phrases == []
    assert trials.searched == ["exampletinib", "ABC-123"]
    assert trials.conditions[-1] == "tooth agenesis"
    assert [match.external_id for match in added] == ["NCT00000007"]
    # The backend is told the code, so a record that gives only the code can be read.
    assert "development codes: ABC-123" in backend.states[0]


def test_a_brand_is_also_searched_by_its_substances_name(session: Session):
    """Scenario: A brand name and its substance"""
    claim = add_claim(
        session,
        slug="toothgrow-tooth-agenesis",
        headline="Drug regrows teeth",
        vertical="mouth-and-teeth",
        intervention="Toothgrow",
        indication="tooth agenesis",
    )
    registry = FakeSubstances({"Toothgrow": [EX1]})
    trials = FakeTrials({"Exampletinib": [trial("NCT00000008", "Exampletinib in adults")]})

    give_development_codes(session, claim, substances=registry)
    added = resolve_claim(
        session, claim, trials=trials, dois=FakeDois(set()), backend=Scoring(0.9), now=NOW
    )

    assert trials.searched == ["Toothgrow", "Exampletinib", "ABC-123"]
    assert [match.external_id for match in added] == ["NCT00000008"]


def test_an_intervention_the_registry_does_not_list_gets_no_code(session: Session):
    """Scenario: Intervention the substance registry does not list"""
    claim = add_claim(
        session,
        slug="tooth-regrowth",
        headline="Device regrows teeth",
        vertical="mouth-and-teeth",
        intervention="Tooth regrowth device",
        indication="tooth agenesis",
    )
    registry = FakeSubstances({})

    answer = give_development_codes(session, claim, substances=registry)

    assert answer is not None and answer.listing is Listing.NOT_LISTED
    assert answer.codes == []
    assert registry.asked == ["Tooth regrowth device"]
    assert session.scalars(select(EntitySubstance)).all() == []


def test_names_listed_under_two_substances_give_no_code(session: Session):
    """Scenario: Names listed under more than one substance"""
    claim = add_claim(
        session,
        slug="tooth-regrowth",
        headline="Drug regrows teeth",
        vertical="mouth-and-teeth",
        intervention="exampletinib",
        indication="tooth agenesis",
    )
    add_synonym(session, claim.slug, "exampletinib", "Toothgrow")
    salt = substance("s-2", "Exampletinib mesylate", ("Toothgrow", "bn"), ("XYZ-9", "cd"))
    registry = FakeSubstances({"exampletinib": [EX1], "Toothgrow": [salt]})

    answer = give_development_codes(session, claim, substances=registry)

    assert answer is not None and answer.listing is Listing.SEVERAL_SUBSTANCES
    assert answer.codes == []
    assert session.scalars(select(EntitySubstance)).all() == []


def test_a_substance_no_longer_listed_loses_its_codes(session: Session):
    claim = add_claim(
        session,
        slug="tooth-regrowth",
        headline="Drug regrows teeth",
        vertical="mouth-and-teeth",
        intervention="exampletinib",
        indication="tooth agenesis",
    )
    give_development_codes(session, claim, substances=FakeSubstances({"exampletinib": [EX1]}))

    give_development_codes(session, claim, substances=FakeSubstances({}))

    assert session.scalars(select(EntitySubstance)).all() == []


# --- a rule's approvals scored again (openspec entity-resolution) -------------------


class NowAnother:
    """A backend for the question as asked now: it reads every record as the claim's
    intervention studied for something else."""

    name = "fake"

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        return BackendAnswer(
            "other_indication",
            {
                o: 0.9 if o == "other_indication" else 0.0 if o == "not_what_is_tested" else 0.05
                for o in options
            },
        )


def approved_trial(session: Session, claim: Claim) -> tuple[EntityMatch, EvidenceEvent]:
    """One trial approved by rule, with the event of its registration read from it."""
    found = FakeTrials({"EX-1 antibody": [trial("NCT00000001", "EX-1 in tooth agenesis")]})
    resolve(session, claim, trials=found, backend=ByCondition(), accept_above=0.8)
    [match] = matches(session)
    event = EvidenceEvent(
        claim_id=claim.id,
        entity_match_id=match.id,
        type=EventType.TRIAL_REGISTERED,
        event_date=date(2020, 1, 1),
        source_name="clinicaltrials.gov",
        source_url="https://clinicaltrials.gov/study/NCT00000001",
        external_id="NCT00000001",
        trial_phases=[TrialPhase.PHASE_2.value],
        summary="Trial registered.",
        confidence=1.0,
        raw_payload={},
        fetched_at=NOW,
        dedupe_key="NCT00000001:registered",
    )
    record_decision(event, ReviewState.APPROVED, by=Decider.RULE, now=NOW)
    session.add(event)
    session.flush()
    refresh_status(session, claim, as_of=NOW.date(), now=NOW)
    return match, event


def redo(session: Session, claim: Claim, backend, **options):
    found = FakeTrials({"EX-1 antibody": [trial("NCT00000001", "EX-1 in tooth agenesis")]})
    return redo_rule_approvals(
        session, claim, trials=found, backend=backend, now=NOW, accept_above=0.8, **options
    )


def test_a_rule_approval_scored_again_and_no_longer_confident_loses_its_events(session: Session):
    """Scenario: A rule's approval no longer stands"""
    claim = new_claim(session)
    match, event = approved_trial(session, claim)
    assert claim.current_status is ClaimStatus.TRIAL_REGISTERED

    redone = redo(session, claim, NowAnother())

    assert (redone.scored, redone.pending, redone.rejected) == (1, ["NCT00000001"], [])
    assert (match.review_state, match.reviewed_by) == (ReviewState.PENDING, None)
    assert (event.review_state, event.reviewed_by) == (ReviewState.REJECTED, Decider.RULE)
    assert claim.current_status is ClaimStatus.NO_TRIAL_FOUND


def test_a_rule_approval_that_still_scores_high_keeps_its_events(session: Session):
    """Scenario: A rule's approval stands"""
    claim = new_claim(session)
    match, event = approved_trial(session, claim)

    redone = redo(session, claim, ByCondition())

    assert (redone.scored, redone.withdrawn) == (1, [])
    assert (match.review_state, match.reviewed_by) == (ReviewState.APPROVED, Decider.RULE)
    assert event.review_state is ReviewState.APPROVED
    assert claim.current_status is ClaimStatus.TRIAL_REGISTERED


def test_a_persons_approval_is_not_scored_again(session: Session):
    """Scenario: A decision by a person or an assistant"""
    claim = new_claim(session)
    match, event = approved_trial(session, claim)
    record_decision(match, ReviewState.APPROVED, by=Decider.ASSISTANT, now=NOW)
    session.flush()

    redone = redo(session, claim, NowAnother())

    assert (redone.scored, redone.withdrawn) == (0, [])
    assert match.review_state is ReviewState.APPROVED and match.score == pytest.approx(0.96)
    assert event.review_state is ReviewState.APPROVED


def test_an_event_an_assistant_approved_is_left_and_reported(session: Session):
    """Scenario: An event decided by a person or an assistant"""
    claim = new_claim(session)
    match, event = approved_trial(session, claim)
    record_decision(event, ReviewState.APPROVED, by=Decider.ASSISTANT, now=NOW)
    session.flush()

    redone = redo(session, claim, NowAnother())

    assert redone.pending == ["NCT00000001"] and redone.events_kept == [event.id]
    assert (event.review_state, event.reviewed_by) == (ReviewState.APPROVED, Decider.ASSISTANT)


def test_a_rule_approval_the_search_no_longer_returns_stays_and_is_reported(session: Session):
    """Scenario: An approved trial the search no longer returns"""
    claim = new_claim(session)
    match, event = approved_trial(session, claim)

    redone = redo_rule_approvals(
        session, claim, trials=FakeTrials({}), backend=NowAnother(), now=NOW, accept_above=0.8
    )

    assert (redone.scored, redone.withdrawn, redone.not_returned) == (0, [], ["NCT00000001"])
    assert match.review_state is ReviewState.APPROVED and event.review_state is ReviewState.APPROVED


def test_a_scoring_that_fails_leaves_every_approval_as_it_was(session: Session):
    claim = new_claim(session)
    match, event = approved_trial(session, claim)

    with pytest.raises(DecisionFailed):
        redo(session, claim, Broken())

    assert (match.review_state, match.reviewed_by) == (ReviewState.APPROVED, Decider.RULE)
    assert event.review_state is ReviewState.APPROVED
