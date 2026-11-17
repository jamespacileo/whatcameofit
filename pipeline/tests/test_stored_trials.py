"""The stored registry trials as a second way to find a claim's trials, tested through
`stored_trials` and `resolve_claim` on a real database with rows built here, and
through the pure functions that compare names. Every name is invented.

Scenario names are from openspec entity-resolution.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from registry_support import ListedSearch
from thenwhat.claims.entry import add_claim
from thenwhat.db.models import Claim, EntityMatch, RegistryTrial
from thenwhat.decide.core import BackendAnswer
from thenwhat.domain import Decider, ReviewState
from thenwhat.resolve.service import rescore_claim, resolve_claim
from thenwhat.resolve.stored import (
    StoredTrial,
    filed_under,
    filed_under_another_name,
    keys_written,
    parts_of,
    stored_trials,
)
from thenwhat.review.decisions import record_decision
from thenwhat.sources.base import SourceRecord

NOW = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
REGISTRY = "clinicaltrials.gov"


def entry(name: str, *other_names: str, kind: str = "DRUG") -> dict[str, Any]:
    return {"type": kind, "name": name, "otherNames": list(other_names)}


def payload(nct_id: str, title: str, conditions: list[str], interventions: list[dict]) -> dict:
    return {
        "protocolSection": {
            "identificationModule": {"nctId": nct_id, "briefTitle": title},
            "conditionsModule": {"conditions": conditions},
            "armsInterventionsModule": {"interventions": interventions},
        }
    }


def store(
    session: Session,
    nct_id: str,
    *interventions: dict[str, Any],
    title: str = "A trial",
    conditions: tuple[str, ...] = ("Tooth Agenesis",),
    study_id: str | None = None,
) -> RegistryTrial:
    stored = payload(nct_id, title, list(conditions), list(interventions))
    if study_id:
        stored["protocolSection"]["identificationModule"]["orgStudyIdInfo"] = {"id": study_id}
    trial = RegistryTrial(
        registry_name=REGISTRY,
        external_id=nct_id,
        title=title,
        conditions=list(conditions),
        interventions=list(interventions),
        phases=["PHASE3"],
        raw_payload=stored,
        fetched_at=NOW,
    )
    session.add(trial)
    session.flush()
    return trial


def found(session: Session, *names: str, indication: str = "tooth agenesis", **more) -> list[str]:
    return [
        record.external_id for record in stored_trials(session, names, indication, **more).records
    ]


def listing(*interventions: dict[str, Any], nct_id: str = "NCT00000001") -> StoredTrial:
    return StoredTrial(nct_id, "A trial", ["Tooth Agenesis"], list(interventions))


# --- names as a registry entry writes them ---------------------------------------


def test_an_entry_that_packs_several_names_gives_each():
    assert keys_written("Brandex, EX-900; LGX1") >= {"brandex", "ex-900", "lgx1"}
    assert keys_written("Zentalimab (EX-900)") >= {"zentalimab", "ex-900"}
    assert keys_written("Brandex®") == {"brandex"}


def test_a_name_is_never_cut_out_of_a_longer_name():
    assert "zentalimab" not in keys_written("zentalimab pegol")
    assert "ex-900" not in keys_written("EX-9001")


def test_a_combinations_name_gives_its_treatments():
    assert parts_of("zentalimab plus Brandex") == ["zentalimab", "Brandex"]
    assert parts_of("Brandex, cetuximab and standard chemotherapy") == [
        "Brandex",
        "cetuximab",
        "standard chemotherapy",
    ]
    assert parts_of("zentalimab and tirzepatide combination regimen") == [
        "zentalimab",
        "tirzepatide",
    ]
    assert parts_of("zentalimab") == ["zentalimab"]


def test_a_name_filed_under_one_other_name_gives_it():
    trials = [
        listing(entry("EX-900", "Zentalimab"), nct_id="NCT00000001"),
        listing(entry("EX-900 80 mg", "zentalimab", "BTX-1"), nct_id="NCT00000002"),
    ]
    assert filed_under(trials, "zentalimab") == "EX-900"


def test_a_name_filed_under_two_names_gives_none():
    trials = [
        listing(entry("EX-900", "Zentalimab"), nct_id="NCT00000001"),
        listing(entry("Arm A chemotherapy", "zentalimab", "docetaxel"), nct_id="NCT00000002"),
    ]
    assert filed_under(trials, "zentalimab") is None


def test_an_entry_that_joins_products_or_is_not_a_product_says_nothing_of_a_name():
    trials = [
        listing(entry("EX-900", "Zentalimab"), nct_id="NCT00000001"),
        listing(entry("EX-900 tablets", "Zentalimab"), nct_id="NCT00000004"),
        listing(entry("docetaxel + EX-900", "zentalimab"), nct_id="NCT00000002"),
        listing(entry("Infusion pump", "zentalimab", kind="DEVICE"), nct_id="NCT00000003"),
    ]
    assert filed_under(trials, "zentalimab") == "EX-900"


def test_a_name_one_trial_alone_files_under_another_gives_none():
    trials = [listing(entry("Palifermin", "growth factor"))]
    assert filed_under(trials, "growth factor") is None


def test_one_trial_is_enough_when_it_files_the_name_under_a_development_code():
    trials = [listing(entry("EX-900", "Zentalimab"))]
    assert filed_under(trials, "zentalimab") == "EX-900"


# --- Stored trials that list the intervention are candidates ---------------------


def test_stored_trial_that_lists_the_name_among_other_names_is_found(session: Session):
    store(session, "NCT00000001", entry("EX-900", "BTX-1", "Zentalimab"), entry("Placebo"))
    store(session, "NCT00000002", entry("zentalimab  PEGOL"))
    store(session, "NCT00000003", entry("Another drug"))

    assert found(session, "zentalimab") == ["NCT00000001"]


def test_names_are_compared_letter_case_spacing_and_trade_marks_aside(session: Session):
    store(session, "NCT00000001", entry("Atezolizumab", "BRANDEX®"))
    store(session, "NCT00000002", entry("zenta  limab"))

    assert found(session, "Brandex") == ["NCT00000001"]
    assert found(session, "Zenta Limab") == ["NCT00000002"]


def test_a_development_code_and_the_substances_name_find_trials_too(session: Session):
    store(session, "NCT00000001", entry("EX-900"))
    store(session, "NCT00000002", entry("Zentalimab-abcd"))

    assert found(session, "Brandex", codes=["EX-900"], substance="Zentalimab-ABCD") == [
        "NCT00000001",
        "NCT00000002",
    ]


def test_trial_filed_under_the_code_alone_is_found_through_the_trials_that_list_both(
    session: Session,
):
    """Zanzalintinib and XL092: one trial says they are one, another lists the code only."""
    store(session, "NCT00000001", entry("EX-900", "Zentalimab"))
    store(session, "NCT00000002", entry("EX-900"), entry("Regorafenib"))
    store(session, "NCT00000003", entry("EX-900 80 mg", "zentalimab"))

    stored = stored_trials(session, ["zentalimab"], "tooth agenesis")

    assert [record.external_id for record in stored.records] == [
        "NCT00000001",
        "NCT00000002",
        "NCT00000003",
    ]
    assert stored.other_names == ["EX-900"]


def test_a_name_filed_under_two_names_is_found_under_each_two_trials_file_it_under(
    session: Session,
):
    """Nothing is told to whoever scores, but candidates are found: each is scored."""
    store(session, "NCT00000001", entry("EX-900", "Zentalimab"))
    store(session, "NCT00000002", entry("EX-900", "Zentalimab"))
    store(session, "NCT00000003", entry("Arm A chemotherapy", "zentalimab"))
    store(session, "NCT00000004", entry("EX-900"))
    store(session, "NCT00000005", entry("Arm A chemotherapy"))

    stored = stored_trials(session, ["zentalimab"], "tooth agenesis")

    assert [record.external_id for record in stored.records] == [
        "NCT00000001",
        "NCT00000002",
        "NCT00000003",
        "NCT00000004",
    ]
    assert stored.other_names == []


def test_a_combination_finds_the_trials_with_an_entry_for_every_part(session: Session):
    store(session, "NCT00000001", entry("EX-900"), entry("Atezolizumab", "Brandex®"))
    store(session, "NCT00000002", entry("EX-900", "zentalimab"))
    store(session, "NCT00000003", entry("Atezolizumab", "Brandex"))
    store(session, "NCT00000004", entry("EX-900", "Zentalimab"))

    assert found(session, "zentalimab plus Brandex") == ["NCT00000001"]


def test_a_part_that_names_a_kind_of_care_needs_no_entry(session: Session):
    store(session, "NCT00000001", entry("Zentalimab"), entry("Cetuximab"), entry("Oxaliplatin"))
    store(session, "NCT00000002", entry("Zentalimab"), entry("Oxaliplatin"))

    assert found(session, "zentalimab, cetuximab and standard chemotherapy") == ["NCT00000001"]


def test_a_name_no_entry_lists_is_looked_for_in_titles_and_study_identifiers(session: Session):
    store(session, "NCT00000001", entry("CLDN6 CAR-T"), study_id="EXB211-01")
    store(session, "NCT00000002", entry("EX-114"), title="A Study of EX-114 (Zentalimab) in Adults")
    store(session, "NCT00000003", entry("Other"), title="Zentalimabs of the world", study_id="X-1")
    store(session, "NCT00000004", entry("Other"), study_id="zentalimab-01")

    assert found(session, "EXB211") == ["NCT00000001"]
    assert found(session, "zentalimab") == ["NCT00000002"]


def test_a_listed_name_is_not_looked_for_in_titles(session: Session):
    store(session, "NCT00000001", entry("Zentalimab"))
    store(session, "NCT00000002", entry("Placebo"), title="After zentalimab: a follow-up")

    assert found(session, "zentalimab") == ["NCT00000001"]


def test_title_fallback_limits_eligible_trials_after_checking_the_indication(session: Session):
    for i in range(1, 103):
        store(
            session,
            f"NCT{i:08d}",
            title="A trial of testmab",
            conditions=("Psoriasis" if i == 102 else "Hypertension",),
        )
        if i == 20:
            assert len(found(session, "testmab", indication="psoriasis")) == 20
    assert found(session, "testmab", indication="psoriasis") == ["NCT00000102"]
    assert found(session, "testmab", indication="hypertension") == []


def test_a_broad_name_is_narrowed_to_the_indication_and_given_up_when_still_broad(
    session: Session,
):
    for number in range(101):
        store(session, f"NCT1{number:07d}", entry("Commonol"), conditions=("Hypertension",))
    store(session, "NCT00000001", entry("Commonol"))

    assert found(session, "commonol") == ["NCT00000001"]
    assert found(session, "commonol", indication="hypertension") == []


def test_a_name_with_few_stored_trials_keeps_those_for_other_conditions(session: Session):
    """A basket trial names no one condition; whoever scores decides, not the wording."""
    store(session, "NCT00000001", entry("Zentalimab"), conditions=("Solid Tumor",))

    assert found(session, "zentalimab") == ["NCT00000001"]


def test_with_no_stored_trial_nothing_is_found(session: Session):
    stored = stored_trials(session, ["zentalimab"], "tooth agenesis")

    assert stored.records == [] and stored.other_names == []


# --- the same scoring and the same approval rule ---------------------------------


class FakeTrials(ListedSearch):
    """A registry whose search returns what it is told to and that reads a trial in
    full by its identifier."""

    def __init__(self, results: dict[str, list[SourceRecord]], full: dict[str, dict]) -> None:
        self.results = results
        self.full = full
        self.searched: list[str] = []
        self.read: list[str] = []

    def search_trials(self, intervention: str, condition: str | None = None) -> list[SourceRecord]:
        self.searched.append(intervention)
        return self.results.get(intervention, [])

    def search_phrase(self, phrase: str, condition: str | None) -> list[SourceRecord]:
        self.searched.append(phrase)
        return []

    def fetch_trial(self, nct_id: str) -> SourceRecord | None:
        self.read.append(nct_id)
        study = self.full.get(nct_id)
        return record(nct_id, study) if study else None


class NoDois:
    def work(self, doi: str) -> SourceRecord | None:
        return None


class ReadsTheRecord:
    """A backend that calls a record a match only when it is for tooth agenesis."""

    name = "fake"

    def __init__(self) -> None:
        self.states: list[str] = []

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        self.states.append(state)
        text = state.split("Candidate record", 1)[-1]
        choice = "match" if "Tooth Agenesis" in text else "other_indication"
        return BackendAnswer(choice, {o: 0.94 if o == choice else 0.02 for o in options})


def record(nct_id: str, study: dict) -> SourceRecord:
    return SourceRecord(REGISTRY, nct_id, f"https://clinicaltrials.gov/study/{nct_id}", study, NOW)


def zentalimab_claim(session: Session) -> Claim:
    return add_claim(
        session,
        slug="zentalimab-tooth-agenesis",
        headline="Antibody regrows teeth",
        vertical="mouth-and-teeth",
        intervention="zentalimab",
        indication="tooth agenesis",
    )


def trial_matches(session: Session) -> dict[str, EntityMatch]:
    return {
        match.external_id: match
        for match in session.scalars(select(EntityMatch).order_by(EntityMatch.id))
    }


def resolve(session: Session, claim: Claim, trials: FakeTrials, backend: Any, **options: Any):
    return resolve_claim(
        session,
        claim,
        trials=trials,
        dois=NoDois(),
        backend=backend,
        now=NOW,
        records=trials,
        **options,
    )


def test_stored_trial_the_search_did_not_return_is_scored_and_approved_like_any_candidate(
    session: Session,
):
    claim = zentalimab_claim(session)
    interventions = [entry("EX-900", "Zentalimab")]
    store(session, "NCT00000001", *interventions)
    store(session, "NCT00000002", *interventions, conditions=("Hypertension",))
    trials = FakeTrials(
        {},
        {
            "NCT00000001": payload("NCT00000001", "In full", ["Tooth Agenesis"], interventions),
            "NCT00000002": payload("NCT00000002", "In full", ["Hypertension"], interventions),
        },
    )
    backend = ReadsTheRecord()

    resolve(session, claim, trials, backend, accept_above=0.8)

    found = trial_matches(session)
    assert found["NCT00000001"].review_state is ReviewState.APPROVED
    assert found["NCT00000001"].reviewed_by is Decider.RULE
    assert (found["NCT00000001"].record_summary or "").startswith("In full")
    # For another condition it is scored low and waits: being listed approves nothing.
    assert found["NCT00000002"].review_state is ReviewState.PENDING
    assert found["NCT00000002"].score < 0.8


def test_whoever_scores_is_told_the_other_names_and_sees_those_a_record_lists(session: Session):
    claim = zentalimab_claim(session)
    store(session, "NCT00000001", entry("EX-900", "Zentalimab"))
    store(session, "NCT00000002", entry("EX-900"))
    store(session, "NCT00000003", entry("EX-900", "Zentalimab"))
    full = payload("NCT00000002", "Filed under the code", ["Tooth Agenesis"], [entry("EX-900")])
    listed = payload(
        "NCT00000001", "Lists both", ["Tooth Agenesis"], [entry("EX-900", "Zentalimab")]
    )
    trials = FakeTrials(
        {"zentalimab": [record("NCT00000001", listed), record("NCT00000003", listed)]},
        {"NCT00000002": full},
    )
    backend = ReadsTheRecord()

    resolve(session, claim, trials, backend)

    asked = "\n".join(backend.states)
    assert "list beside its name" in asked and "EX-900." in asked and "not proof" in asked
    assert '"other_names":["Zentalimab"]' in asked
    # The name the stored trials file it under is searched for at the registry as well.
    assert "EX-900" in trials.searched
    # Only the trial the search did not return is read in full.
    assert trials.read == ["NCT00000002"]


def test_a_stored_trial_the_registry_no_longer_answers_for_is_not_a_candidate(session: Session):
    claim = zentalimab_claim(session)
    store(session, "NCT00000001", entry("Zentalimab"))
    trials = FakeTrials({}, {})

    added = resolve(session, claim, trials, ReadsTheRecord())

    assert added == [] and trials.read == ["NCT00000001"]


def test_a_candidate_already_decided_is_not_read_or_scored_again(session: Session):
    claim = zentalimab_claim(session)
    interventions = [entry("Zentalimab")]
    store(session, "NCT00000001", *interventions)
    trials = FakeTrials(
        {}, {"NCT00000001": payload("NCT00000001", "T", ["Hypertension"], interventions)}
    )
    resolve(session, claim, trials, ReadsTheRecord(), reject_below=0.05)
    assert trial_matches(session)["NCT00000001"].review_state is ReviewState.REJECTED
    trials.read.clear()

    added = resolve(session, claim, trials, ReadsTheRecord(), reject_below=0.05)

    assert added == [] and trials.read == []


def test_a_combination_claim_gets_the_stored_trial_that_files_a_part_under_its_code(
    session: Session,
):
    claim = add_claim(
        session,
        slug="zentalimab-plus-brandex-tooth-agenesis",
        headline="Two antibodies regrow teeth",
        vertical="mouth-and-teeth",
        intervention="zentalimab plus Brandex",
        indication="tooth agenesis",
    )
    both = [entry("EX-900"), entry("Atezolizumab", "Brandex®")]
    store(session, "NCT00000001", entry("EX-900", "Zentalimab"))
    store(session, "NCT00000003", entry("EX-900", "Zentalimab"))
    store(session, "NCT00000002", *both)
    trials = FakeTrials(
        {}, {"NCT00000002": payload("NCT00000002", "Both", ["Tooth Agenesis"], both)}
    )

    resolve(session, claim, trials, ReadsTheRecord())

    assert set(trial_matches(session)) == {"NCT00000002"}
    assert trials.read == ["NCT00000002"]


# --- Candidates scored without the other names are scored again ------------------


def test_a_record_that_files_the_intervention_under_another_name_is_told_apart():
    filed = payload("NCT00000001", "T", ["Tooth Agenesis"], [entry("EX-900", "Zentalimab")])
    plain = payload("NCT00000002", "T", ["Tooth Agenesis"], [entry("Zentalimab", "EX-900")])
    coded = payload("NCT00000003", "T", ["Tooth Agenesis"], [entry("EX-900")])

    assert filed_under_another_name(filed, ["zentalimab"])
    assert not filed_under_another_name(plain, ["zentalimab"])
    assert not filed_under_another_name(coded, ["zentalimab"])
    assert filed_under_another_name(coded, ["zentalimab"], ["EX-900"])


class Blind:
    """A backend that calls a record a match only where it can see the claim's name."""

    name = "fake"

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        text = state.split("Candidate record", 1)[-1]
        choice = "match" if "Zentalimab" in text else "not_a_match"
        return BackendAnswer(choice, {o: 0.97 if o == choice else 0.01 for o in options})


def test_rescore_scores_again_a_rule_rejection_whose_record_files_it_under_another_name(
    session: Session,
):
    claim = zentalimab_claim(session)
    without_names = [{"type": "DRUG", "name": "EX-900"}]
    trials = FakeTrials(
        {
            "zentalimab": [
                record(
                    "NCT00000001", payload("NCT00000001", "A", ["Tooth Agenesis"], without_names)
                ),
                record(
                    "NCT00000002", payload("NCT00000002", "B", ["Tooth Agenesis"], without_names)
                ),
            ]
        },
        {},
    )
    resolve(session, claim, trials, Blind(), reject_below=0.05, accept_above=0.8)
    assert {m.review_state for m in trial_matches(session).values()} == {ReviewState.REJECTED}
    # The search now returns the other names: one record lists the claim's name, one does not.
    listed = [entry("EX-900", "Zentalimab")]
    trials.results["zentalimab"] = [
        record("NCT00000001", payload("NCT00000001", "A", ["Tooth Agenesis"], listed)),
        record("NCT00000002", payload("NCT00000002", "B", ["Tooth Agenesis"], without_names)),
    ]

    again = rescore_claim(
        session,
        claim,
        trials=trials,
        backend=Blind(),
        now=NOW,
        records=trials,
        reject_below=0.05,
        accept_above=0.8,
    )

    found = trial_matches(session)
    assert [match.external_id for match in again] == ["NCT00000001"]
    assert found["NCT00000001"].review_state is ReviewState.APPROVED
    assert found["NCT00000001"].reviewed_by is Decider.RULE
    assert found["NCT00000002"].review_state is ReviewState.REJECTED


def test_rescore_leaves_a_rejection_a_person_made(session: Session):
    claim = zentalimab_claim(session)
    listed = [entry("EX-900", "Zentalimab")]
    study = payload("NCT00000001", "A", ["Tooth Agenesis"], listed)
    trials = FakeTrials({"zentalimab": [record("NCT00000001", study)]}, {})
    resolve(session, claim, trials, Blind())
    match = trial_matches(session)["NCT00000001"]
    record_decision(match, ReviewState.REJECTED, by=Decider.HUMAN, now=NOW)
    session.flush()

    again = rescore_claim(session, claim, trials=trials, backend=Blind(), now=NOW, accept_above=0.8)

    assert again == []
    assert trial_matches(session)["NCT00000001"].reviewed_by is Decider.HUMAN
