"""OpenAI's Decisions API as a decision backend, tested through `decide_many` and `decide`
on a fake transport and a real database. The answer replayed was recorded from the API
(see tests/fixtures/README.md). Scenario names are from openspec decision-steps.
"""

import json
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.db.models import DecisionLog, LlmUsage
from thenwhat.decide.core import DecisionFailed, backend_named, decide, decide_many
from thenwhat.decide.decisions_backend import DecisionsBackend
from thenwhat.decide.steps import TRIAL_OPTIONS, TRIAL_QUESTION
from thenwhat.llm.client import Llm, LlmSettings
from thenwhat.llm.decisions import Decisions, DecisionsSettings

NOW = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
INTRO = "Claim: An antibody was reported to regrow missing teeth.\nIntervention: EX-1."
RECORDS = [
    ("lookup:NCT00000001", "Candidate record (NCT00000001): EX-1 in tooth agenesis"),
    ("lookup:NCT00000002", "Candidate record (NCT00000002): EX-1 in lung cancer"),
    ("lookup:NCT00000003", "Candidate record (NCT00000003): Aspirin after surgery"),
]


class Api:
    def __init__(self, answer: dict | httpx.Response) -> None:
        self.answer = answer
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if isinstance(self.answer, httpx.Response):
            return self.answer
        return httpx.Response(200, json=self.answer)


def backend(
    session: Session,
    api: Api,
    *,
    model: str | None = "example-model",
    price: str | None = "0.10",
    budget: str = "10",
    credential: str | None = "test-credential",
) -> DecisionsBackend:
    settings = DecisionsSettings(model, Decimal(budget), Decimal(price) if price else None)
    decisions = Decisions(
        session,
        settings,
        transport=httpx.MockTransport(api),
        now=lambda: NOW,
        credential=credential,
    )
    return DecisionsBackend(decisions)


def score(session: Session, chosen: DecisionsBackend, records=RECORDS):
    return decide_many(
        session,
        chosen,
        step="lookup_match",
        intro=INTRO,
        question=TRIAL_QUESTION,
        items=records,
        options=TRIAL_OPTIONS,
        now=NOW,
    )


def test_every_record_is_scored_in_one_request(session: Session, fixture_json):
    """Scenario: Many items, one call"""
    api = Api(fixture_json("openai/decisions_three_records.json")["response"])

    decisions = score(session, backend(session, api))

    assert [d.choice for d in decisions] == ["match", "other_indication", "not_a_match"]
    assert decisions[1].probabilities == {
        "match": 0.1,
        "other_indication": 0.88,
        "not_a_match": 0.02,
    }
    # The API's own confidence is kept; it is not the same as the chosen option's probability.
    assert decisions[1].confidence == 0.82
    assert len(api.requests) == 1
    sent = json.loads(api.requests[0].content)
    assert (sent["model"], sent["input"]) == ("example-model", INTRO)
    assert api.requests[0].headers["Authorization"] == "Bearer test-credential"
    first = sent["questions"][0]
    assert (first["type"], first["name"]) == ("choice", "item-1")
    assert first["instructions"].endswith(RECORDS[0][1])
    # Each option carries the question's own account of when it applies.
    assert first["choices"][1] == {
        "value": "other_indication",
        "description": "it tests this intervention for a different condition,"
        " or only in healthy volunteers.",
    }
    logged = list(session.scalars(select(DecisionLog).order_by(DecisionLog.id)))
    assert [(entry.backend, entry.model) for entry in logged] == [
        ("openai-decisions", "example-model")
    ] * 3


def test_sixty_records_are_one_request_not_three(session: Session):
    answers = [
        {
            "type": "choice",
            "name": f"item-{n}",
            "choice": "match",
            "probabilities": [
                {"value": "match", "probability": 0.9},
                {"value": "other_indication", "probability": 0.06},
                {"value": "not_a_match", "probability": 0.04},
            ],
            "confidence": 0.8,
        }
        for n in range(1, 61)
    ]
    api = Api({"answers": answers, "usage": {"input_tokens": 9000}})
    records = [(f"lookup:{n}", f"Candidate record {n}") for n in range(60)]

    assert len(score(session, backend(session, api), records)) == 60
    assert len(api.requests) == 1


def test_a_call_is_recorded_at_the_input_price_and_counts_towards_the_ceiling(
    session: Session, fixture_json
):
    """Scenario: Usage recorded"""
    api = Api(fixture_json("openai/decisions_three_records.json")["response"])

    score(session, backend(session, api))

    usage = session.scalars(select(LlmUsage)).one()
    assert (usage.purpose, usage.model) == ("decision:lookup_match", "example-model")
    assert (usage.input_tokens, usage.output_tokens) == (709, 0)
    assert usage.cost_usd == Decimal("0.000071")
    # The next call is refused once the month's cost has reached the ceiling.
    with pytest.raises(DecisionFailed, match="monthly ceiling"):
        score(session, backend(session, api, budget="0.00005"))
    assert len(api.requests) == 1


def test_a_record_the_api_declines_fails_the_step_and_is_logged(session: Session, fixture_json):
    """Scenario: Unusable answer"""
    answered = fixture_json("openai/decisions_three_records.json")["response"]
    answered["answers"][1] = {"type": "refusal", "name": "item-2"}

    with pytest.raises(DecisionFailed, match="no answer"):
        score(session, backend(session, Api(answered)))

    errors = [
        entry.error for entry in session.scalars(select(DecisionLog).order_by(DecisionLog.id))
    ]
    assert [bool(error) for error in errors] == [False, True, False]


@pytest.mark.parametrize(
    ("settings", "says"),
    [
        ({"model": None}, "DECISIONS_MODEL"),
        ({"price": None}, "DECISIONS_INPUT_USD_PER_MTOK"),
    ],
)
def test_no_call_is_made_while_the_backend_is_not_configured(session: Session, settings, says):
    """Scenario: Not configured"""
    api = Api({})

    with pytest.raises(DecisionFailed, match=says):
        score(session, backend(session, api, **settings))
    assert api.requests == []


def test_a_failed_call_says_its_status_and_nothing_that_was_sent(session: Session):
    api = Api(httpx.Response(429, json={"error": {"message": f"echo of {INTRO}"}}))

    with pytest.raises(DecisionFailed) as failed:
        score(session, backend(session, api))

    assert "status 429" in str(failed.value) and "antibody" not in str(failed.value)


def test_one_question_is_answered_from_its_state(session: Session):
    answer = {
        "type": "choice",
        "name": "item-1",
        "choice": "animal",
        "probabilities": [
            {"value": "animal", "probability": 0.8},
            {"value": "early_human", "probability": 0.2},
        ],
        "confidence": 0.7,
    }
    api = Api({"answers": [answer], "usage": {"input_tokens": 50}})

    decision = decide(
        session,
        backend(session, api),
        step="evidence_stage",
        state="An antibody regrew teeth in mice.",
        options=["animal", "early_human"],
        input_ref="claim:1",
        now=NOW,
    )

    assert (decision.choice, decision.confidence) == ("animal", 0.7)
    assert json.loads(api.requests[0].content)["input"] == "An antibody regrew teeth in mice."


def test_the_configured_name_selects_this_backend(session: Session):
    llm = Llm(session, LlmSettings(None, Decimal("10"), None, None))
    decisions = Decisions(session, DecisionsSettings(None, Decimal("10"), None))

    assert isinstance(backend_named("openai-decisions", llm, decisions), DecisionsBackend)
