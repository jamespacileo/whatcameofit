"""Looking up the registry trials behind a piece of text, tested through `look_up` with a
scripted model, a fake registry and a fake decision backend on a real database.

Scenario names are from openspec live-lookup. All text here is synthetic.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from thenwhat.claims.entities import add_synonym
from thenwhat.claims.entry import add_claim
from thenwhat.db.models import Claim, Entity, EntityMatch, SourceArticle
from thenwhat.decide.core import BackendAnswer
from thenwhat.llm.client import Llm, LlmSettings
from thenwhat.lookup.service import look_up
from thenwhat.sources.base import SourceRecord

NOW = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
TEXT = "Scientists say EX-1, also called Toothgrow, regrew teeth in people born without them."
READING = {
    "about_a_treatment": True,
    "gist": "An antibody was reported to regrow missing teeth.",
    "intervention": "EX-1",
    "other_names": ["Toothgrow", "the drug"],
    "search_phrases": ["USAG-1 antibody"],
    "indication": "tooth agenesis",
}


def trial(nct_id: str, title: str, condition: str = "Tooth Agenesis") -> SourceRecord:
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
    def __init__(
        self, by_name: dict[str, list[SourceRecord]], by_id: dict[str, SourceRecord] | None = None
    ) -> None:
        self.by_name = by_name
        self.by_id = by_id or {}
        self.searched: list[tuple[str, str | None]] = []

    def search_trials(self, intervention: str, condition: str | None = None) -> list[SourceRecord]:
        self.searched.append((intervention, condition))
        return self.by_name.get(intervention, [])

    def fetch_trial(self, nct_id: str) -> SourceRecord | None:
        return self.by_id.get(nct_id)


class ByCondition:
    """A match only when the record names tooth agenesis."""

    name = "fake"

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        record = state.split("Candidate record", 1)[-1]
        choice = "match" if "Tooth Agenesis" in record else "other_indication"
        return BackendAnswer(choice, {o: 0.96 if o == choice else 0.02 for o in options})


def llm(session: Session, output: dict[str, Any]) -> tuple[Llm, list[str]]:
    prompts: list[str] = []

    def respond(messages, info) -> ModelResponse:
        prompts.append(str(messages))
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, output)])

    settings = LlmSettings("test:scripted", Decimal("10"), Decimal("3"), Decimal("15"))
    model = FunctionModel(respond, model_name="scripted")
    return Llm(session, settings, model=model, now=lambda: NOW), prompts


def find(session: Session, trials: FakeTrials, text: str = TEXT, reading: dict | None = None):
    model, _ = llm(session, reading or READING)
    return look_up(session, model, ByCondition(), trials, text=text, now=NOW)


def stored(session: Session) -> tuple[int, ...]:
    return tuple(
        session.scalar(select(func.count()).select_from(table)) or 0
        for table in (Claim, Entity, EntityMatch, SourceArticle)
    )


def test_trials_for_the_reported_treatment_and_condition_come_first(session: Session):
    """Scenario: Article about a treatment with registered trials"""
    trials = FakeTrials(
        {
            "EX-1": [
                trial("NCT00000002", "EX-1 in lung cancer", condition="Lung Cancer"),
                trial("NCT00000001", "EX-1 in tooth agenesis"),
            ]
        }
    )

    found = find(session, trials)

    assert (found.intervention, found.indication) == ("EX-1", "tooth agenesis")
    assert [(c.external_id, c.answer) for c in found.candidates] == [
        ("NCT00000001", "match"),
        ("NCT00000002", "other_indication"),
    ]
    assert found.candidates[0].score > 0.9 > found.candidates[1].score
    assert found.candidates[0].url == "https://clinicaltrials.gov/study/NCT00000001"
    assert "EX-1 in tooth agenesis" in found.candidates[0].summary


def test_every_name_and_search_phrase_is_searched_within_the_condition(session: Session):
    trials = FakeTrials(
        {"USAG-1 antibody": [trial("NCT00000003", "Anti-USAG-1 in tooth agenesis")]}
    )

    found = find(session, trials)

    # A description the model returned as a name is not searched for.
    assert trials.searched == [
        ("EX-1", "tooth agenesis"),
        ("Toothgrow", "tooth agenesis"),
        ("USAG-1 antibody", "tooth agenesis"),
    ]
    assert found.names == ["EX-1", "Toothgrow"]
    assert [c.external_id for c in found.candidates] == ["NCT00000003"]


def test_a_registry_number_in_the_text_is_looked_up_directly(session: Session):
    """Scenario: Text that states a registry number"""
    stated = trial("NCT01234567", "EX-1 first study in people")
    trials = FakeTrials({}, {"NCT01234567": stated})

    found = find(session, trials, text=f"{TEXT} The study is registered as nct01234567.")

    assert [c.external_id for c in found.candidates] == ["NCT01234567"]
    assert found.registry_numbers == ["NCT01234567"]


def test_text_that_is_not_about_a_treatment_is_not_searched(session: Session):
    """Scenario: Text that is not about a treatment"""
    trials = FakeTrials({})
    reading = {"about_a_treatment": False, "gist": "A report on hospital waiting times."}

    found = find(session, trials, text="Waiting lists grew again this month.", reading=reading)

    assert (found.intervention, found.candidates, trials.searched) == (None, [], [])


def test_a_claim_already_tracked_under_one_of_the_names_is_named(session: Session):
    """Scenario: Treatment already tracked"""
    add_claim(
        session,
        slug="tooth-regrowth-ex1",
        headline="Antibody regrows teeth",
        vertical="dental-regeneration",
        intervention="Anti-USAG-1 antibody",
        indication="tooth agenesis",
        summary="An antibody restored missing teeth.",
    )
    add_synonym(session, "tooth-regrowth-ex1", "Anti-USAG-1 antibody", "toothgrow")

    found = find(session, FakeTrials({}))

    assert found.tracked == ["tooth-regrowth-ex1"]


def test_a_lookup_stores_no_claim_match_or_article(session: Session):
    """Scenario: Nothing is kept"""
    before = stored(session)

    find(session, FakeTrials({"EX-1": [trial("NCT00000001", "EX-1 in tooth agenesis")]}))

    assert stored(session) == before


def test_the_model_is_shown_the_text(session: Session):
    model, prompts = llm(session, READING)

    look_up(session, model, ByCondition(), FakeTrials({}), text=TEXT, now=NOW)

    assert TEXT in prompts[0]
