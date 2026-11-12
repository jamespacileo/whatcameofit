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
from thenwhat.extract.page import Page
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


def trial(
    nct_id: str,
    title: str,
    condition: str = "Tooth Agenesis",
    *,
    acronym: str | None = None,
    enrolled: int | None = None,
    sponsor: str | None = None,
) -> SourceRecord:
    payload = {
        "protocolSection": {
            "identificationModule": {"nctId": nct_id, "briefTitle": title, "acronym": acronym},
            "armsInterventionsModule": {"interventions": [{"name": "EX-1"}]},
            "conditionsModule": {"conditions": [condition]},
            "designModule": {"enrollmentInfo": {"count": enrolled}},
            "sponsorCollaboratorsModule": {"leadSponsor": {"name": sponsor}},
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
        self.by_trial_name: dict[str, list[SourceRecord]] = {}
        self.searched: list[tuple[str, str | None]] = []

    def search_trials(self, intervention: str, condition: str | None = None) -> list[SourceRecord]:
        self.searched.append((intervention, condition))
        return self.by_name.get(intervention, [])

    def fetch_trial(self, nct_id: str) -> SourceRecord | None:
        return self.by_id.get(nct_id)

    def named_trials(self, name: str) -> list[SourceRecord]:
        return self.by_trial_name.get(name, [])


class FakePapers:
    def __init__(self, by_paper: dict[str, list[str]]) -> None:
        self.by_paper = by_paper
        self.asked: list[str] = []

    def trial_numbers(self, *, doi: str | None = None, pubmed_id: str | None = None) -> list[str]:
        self.asked.append(doi or f"pubmed:{pubmed_id}")
        return self.by_paper.get(self.asked[-1], [])


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


def find(
    session: Session,
    trials: FakeTrials,
    text: str = TEXT,
    reading: dict | None = None,
    page: Page | None = None,
    papers: FakePapers | None = None,
):
    model, _ = llm(session, reading or READING)
    return look_up(
        session, model, ByCondition(), trials, text=text, now=NOW, page=page, papers=papers
    )


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


def test_names_the_model_knows_widen_the_search_and_are_reported_apart(session: Session):
    """Scenario: Registry lists the treatment under a name the text does not give"""
    by_code = trial("NCT00000004", "TRG-035 in tooth agenesis")
    trials = FakeTrials({"TRG-035": [by_code]})
    reading = {**READING, "search_phrases": [], "known_names": ["TRG-035", "the antibody"]}

    found = find(session, trials, reading=reading)

    assert [name for name, _ in trials.searched] == ["EX-1", "Toothgrow", "TRG-035"]
    assert (found.names, found.known_names) == (["EX-1", "Toothgrow"], ["TRG-035"])
    assert [c.external_id for c in found.candidates] == ["NCT00000004"]


def test_each_part_of_a_combination_is_searched(session: Session):
    """Scenario: Combination of two treatments"""
    trials = FakeTrials({"EX-2": [trial("NCT00000005", "EX-1 with EX-2 in tooth agenesis")]})
    reading = {**READING, "intervention": "EX-1 and EX-2", "other_names": [], "search_phrases": []}

    found = find(session, trials, reading=reading)

    assert [name for name, _ in trials.searched] == ["EX-1 and EX-2", "EX-1", "EX-2"]
    assert found.names == ["EX-1 and EX-2"]
    assert [c.external_id for c in found.candidates] == ["NCT00000005"]


def test_a_registry_number_in_the_text_is_looked_up_directly(session: Session):
    """Scenario: Text that states a registry number"""
    stated = trial("NCT01234567", "EX-1 first study in people")
    trials = FakeTrials({}, {"NCT01234567": stated})

    # A model may hand the number back as if it were another name of the treatment.
    reading = {**READING, "other_names": ["Toothgrow", "NCT01234567"], "search_phrases": []}

    found = find(
        session, trials, text=f"{TEXT} The study is registered as nct01234567.", reading=reading
    )

    assert [c.external_id for c in found.candidates] == ["NCT01234567"]
    assert found.registry_numbers == ["NCT01234567"]
    assert found.names == ["EX-1", "Toothgrow"]
    assert "NCT01234567" not in [name for name, _ in trials.searched]


def test_the_trial_of_a_paper_the_page_links_to_is_looked_up(session: Session):
    """Scenario: Page that links to the paper it reports"""
    reported = trial("NCT07654321", "EX-1 in tooth agenesis, second study")
    trials = FakeTrials({}, {"NCT07654321": reported})
    papers = FakePapers({"10.1234/example.2026.0042": ["NCT07654321"]})
    page = Page(text=TEXT, dois=("10.1234/example.2026.0042",), pubmed_ids=("31234567",))

    found = find(session, trials, page=page, papers=papers)

    assert papers.asked == ["10.1234/example.2026.0042", "pubmed:31234567"]
    assert found.paper_numbers == ["NCT07654321"]
    assert [(c.external_id, c.agrees) for c in found.candidates] == [("NCT07654321", ["paper"])]


def test_a_registry_number_in_a_link_on_the_page_counts_as_stated(session: Session):
    """Scenario: Text that states a registry number"""
    linked = trial("NCT01234567", "EX-1 first study in people", condition="Healthy Volunteers")
    searched = trial("NCT00000001", "EX-1 in tooth agenesis")
    trials = FakeTrials({"EX-1": [searched]}, {"NCT01234567": linked})

    found = find(session, trials, page=Page(text=TEXT, registry_numbers=("NCT01234567",)))

    # The record the article itself points to is first, whatever its score.
    assert [(c.external_id, c.agrees) for c in found.candidates] == [
        ("NCT01234567", ["stated"]),
        ("NCT00000001", []),
    ]
    assert found.candidates[0].score < 0.5


def test_the_trial_the_text_names_is_searched_for_and_ranked_first(session: Session):
    """Scenario: Text that names the trial"""
    first = trial("NCT00000001", "EX-1 in tooth agenesis")
    named = trial("NCT00000009", "EX-1 in adults with tooth agenesis", acronym="REGROW-2")
    trials = FakeTrials({"EX-1": [first]})
    trials.by_trial_name = {"REGROW-2": [named]}

    found = find(session, trials, reading={**READING, "trial_name": "REGROW-2"})

    assert found.details.trial_name == "REGROW-2"
    assert [(c.external_id, c.agrees) for c in found.candidates] == [
        ("NCT00000009", ["trial_name"]),
        ("NCT00000001", []),
    ]


def test_a_record_that_agrees_with_size_and_sponsor_is_ranked_above_its_siblings(
    session: Session,
):
    """Scenario: Text that gives the trial's size and who ran it"""
    trials = FakeTrials(
        {
            "EX-1": [
                trial("NCT00000001", "EX-1 in tooth agenesis", enrolled=40, sponsor="Example Bio"),
                trial(
                    "NCT00000002",
                    "EX-1 in tooth agenesis",
                    enrolled=118,
                    sponsor="Kyoto University",
                ),
                # Agreeing details never lift a record that is not a trial for the condition.
                trial(
                    "NCT00000003",
                    "EX-1 in lung cancer",
                    "Lung Cancer",
                    enrolled=120,
                    sponsor="Kyoto University",
                ),
            ]
        }
    )
    reading = {**READING, "participants": 120, "sponsor": "Kyoto University"}

    found = find(session, trials, reading=reading)

    assert [(c.external_id, c.agrees) for c in found.candidates] == [
        ("NCT00000002", ["participants", "sponsor"]),
        ("NCT00000001", []),
        ("NCT00000003", ["participants", "sponsor"]),
    ]


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
        vertical="mouth-and-teeth",
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
