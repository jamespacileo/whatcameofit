"""Registry scope candidates must cite real, appropriate source fields."""

import json
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.backfill.registry_scope_propose import (
    PURPOSE,
    ScopeAnswer,
    ground_answers,
    propose_scope,
    review_packet,
)
from thenwhat.db.models import LlmUsage
from thenwhat.llm.cache import ModelCache
from thenwhat.llm.client import Llm, LlmSettings


def record(formulation: str = "tablets"):
    title = f"Example XR {formulation} in Relapsing Multiple Sclerosis"
    return {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000001", "officialTitle": title},
            "designModule": {"designInfo": {"primaryPurpose": "TREATMENT"}},
            "conditionsModule": {"conditions": ["Multiple Sclerosis"]},
            "armsInterventionsModule": {
                "armGroups": [
                    {
                        "label": "Investigation",
                        "type": "EXPERIMENTAL",
                        "interventionNames": ["Drug: Example XR"],
                    }
                ],
                "interventions": [
                    {"name": "Example XR", "type": "DRUG", "armGroupLabels": ["Investigation"]}
                ],
            },
            "contactsLocationsModule": {"centralContacts": [{"name": "Private contact"}]},
            "outcomesModule": {
                "primaryOutcomes": [
                    {"measure": "Relapse Count", "description": "Unused outcome description"}
                ]
            },
        },
        "resultsSection": {"Unused data": "Private result row"},
    }


def selected(formulation: str = "tablets") -> dict:
    return {
        "pairs": [
            {
                "components": [{"source": 0, "text": f"Example XR {formulation}"}],
                "indication": {"source": 0, "text": "Relapsing Multiple Sclerosis"},
                "assignment": {"source": 3, "text": "Investigation"},
            }
        ],
        "remaining_uncertain": False,
    }


def test_native_json_proposals_reuse_exact_requests_and_preserve_formulations(
    session: Session, tmp_path: Path
):
    calls = []

    def respond(_messages, info):
        calls.append(info)
        return ModelResponse(parts=[TextPart(json.dumps(selected()))])

    model = FunctionModel(respond, model_name="native-json-fixture")
    llm = Llm(
        session,
        LlmSettings("openai:fixture", Decimal(10), Decimal(1), Decimal(1)),
        model=model,
        cache=ModelCache(tmp_path),
    )
    packet = review_packet(record())
    first = propose_scope(llm, packet)
    second = propose_scope(llm, packet)

    assert second == first
    assert len(calls) == 1
    assert first.pairs[0].regimen == ("Example XR tablets",)
    assert first.pairs[0].indication == "Relapsing Multiple Sclerosis"
    assert review_packet(record("injection")).prompt() != packet.prompt()
    assert "Private contact" not in packet.prompt()
    assert "Unused outcome description" not in packet.prompt()
    assert "Private result row" not in packet.prompt()
    assert list(session.scalars(select(LlmUsage.purpose))) == [PURPOSE]


def test_guessed_or_wrong_type_excerpts_fail_and_empty_answers_stay_unresolved():
    packet = review_packet(record())
    for indication in (
        {"source": 0, "text": "Progressive Multiple Sclerosis"},
        {"source": 3, "text": "Investigation"},
        {"source": 0, "text": "Relaps"},
    ):
        raw = selected()
        raw["pairs"][0]["indication"] = indication
        with pytest.raises(ValueError, match="absent from its source"):
            ground_answers(packet, ScopeAnswer.model_validate(raw))

    empty = ground_answers(packet, ScopeAnswer(pairs=[], remaining_uncertain=False))
    assert not empty.pairs
    assert empty.remaining_uncertain
