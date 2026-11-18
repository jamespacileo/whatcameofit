"""Registry scope candidates must cite real, appropriate source fields."""

import json
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.backfill.registry_arm_scope import (
    OMISSION_PURPOSE,
    ArmScopeAnswer,
    arm_packet,
    ground_arm_answer,
    propose_arm_scope,
)
from thenwhat.backfill.registry_arm_scope import (
    PURPOSE as ARM_PURPOSE,
)
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


def test_arm_proposals_keep_matching_placebos_and_formulations_in_their_correct_roles(
    session: Session, tmp_path: Path
):
    study = record()
    protocol = study["protocolSection"]
    protocol["eligibilityModule"] = {
        "eligibilityCriteria": "Adults with at least one previous treatment."
    }
    tablet_arm = "Tablets with placebo-to-match injection"
    injection_arm = "Injection with placebo-to-match tablets"
    protocol["armsInterventionsModule"] = {
        "armGroups": [
            {
                "label": label,
                "type": "EXPERIMENTAL",
                "interventionNames": ["Drug: Example XR", "Drug: PTM Example XR"],
            }
            for label in (tablet_arm, injection_arm)
        ],
        "interventions": [
            {
                "name": "Example XR",
                "armGroupLabels": [tablet_arm],
                "description": "Example XR tablets",
            },
            {
                "name": "Example XR",
                "armGroupLabels": [injection_arm],
                "description": "Example XR injection",
            },
            {"name": "PTM Example XR", "armGroupLabels": [tablet_arm, injection_arm]},
        ],
    }
    packet = arm_packet(study)

    def citation(kind: str, phrase: str) -> dict:
        source = next(
            index
            for index, field in enumerate(packet.evidence)
            if field.kind == kind and phrase in field.text
        )
        return {"source": source, "text": phrase}

    tablet = citation("intervention_description", "Example XR tablets")
    injection = citation("intervention_description", "Example XR injection")
    selected_pair = {
        "arm": 0,
        "components": [tablet],
        "indication": citation("condition", "Multiple Sclerosis"),
        "population": None,
        "setting": None,
        "formulation": tablet,
        "sequence": None,
        "comparator": [],
        "background": [],
    }
    answer = {"pairs": [selected_pair], "remaining_uncertain": False}
    assert packet.owners(injection["source"]) == {1}
    for invalid in (injection, citation("intervention", "PTM Example XR")):
        bad = {**answer, "pairs": [{**selected_pair, "components": [invalid]}]}
        with pytest.raises(ValueError):
            ground_arm_answer(packet, ArmScopeAnswer.model_validate(bad))
    assert ground_arm_answer(packet, ArmScopeAnswer.model_validate(answer)).pairs[0].regimen == (
        "Example XR tablets",
    )

    missing_arm = {"arm": 1, "slot": "formulation", "evidence": injection}
    calls = []

    def respond(_messages, info):
        calls.append(info)
        body = (
            answer
            if len(calls) == 1
            else {"omissions": [missing_arm], "remaining_uncertain": False}
        )
        return ModelResponse(parts=[TextPart(json.dumps(body))])

    llm = Llm(
        session,
        LlmSettings("openai:fixture", Decimal(10), Decimal(1), Decimal(1)),
        model=FunctionModel(respond, model_name="arm-scope-native-json-fixture"),
        cache=ModelCache(tmp_path),
    )
    proposal = propose_arm_scope(llm, packet, check_omissions=True)
    assert propose_arm_scope(llm, packet, check_omissions=True) == proposal
    assert len(calls) == 2
    assert proposal.remaining_uncertain
    assert len(proposal.pairs) == 1
    assert proposal.omissions[0]["arm"] == 1
    assert list(session.scalars(select(LlmUsage.purpose).order_by(LlmUsage.id))) == [
        ARM_PURPOSE,
        OMISSION_PURPOSE,
    ]


def test_arm_scope_uses_only_positive_eligibility_and_keeps_other_sections_for_review():
    study = record()
    criteria = (
        "Registry overview of entry criteria.\n\n"
        "## Key Inclusion Criteria:\n"
        "Adults with active Multiple Sclerosis.\n\n"
        "Cohort B: Refractory Multiple Sclerosis.\n\n"
        "* Additional inclusion criteria for the dose escalation cohort:\n"
        "Presence of an elevated biomarker.\n\n"
        "**Exclusion Criteria:**\n"
        "History of glaucoma.\n"
    )
    study["protocolSection"]["eligibilityModule"] = {
        "eligibilityCriteria": criteria,
        "studyPopulation": "Participants with prior topical therapy.",
    }
    packet = arm_packet(study)
    assert (
        "".join(field.text for field in packet.evidence if field.kind.startswith("eligibility"))
        == criteria
    )

    def citation(kind: str, phrase: str) -> dict:
        field = next(
            index
            for index, field in enumerate(packet.evidence)
            if field.kind == kind and phrase in field.text
        )
        return {"source": field, "text": phrase}

    pair = {
        "arm": 0,
        "components": [citation("intervention", "Example XR")],
        "indication": citation("eligibility_inclusion", "active Multiple Sclerosis"),
        "population": citation("study_population", "Participants with prior topical therapy"),
        "setting": None,
        "formulation": None,
        "sequence": None,
        "comparator": [],
        "background": [],
    }
    model_answer = {"pairs": [pair], "remaining_uncertain": False}
    grounded = ground_arm_answer(packet, ArmScopeAnswer.model_validate(model_answer))
    assert grounded.pairs[0].indication_quotes == (
        "active Multiple Sclerosis",
        "Participants with prior topical therapy",
    )

    for field in (
        citation("eligibility", "Refractory Multiple Sclerosis"),
        citation("eligibility", "Presence of an elevated biomarker"),
        citation("eligibility_exclusion", "History of glaucoma"),
    ):
        for slot in ("indication", "population", "setting", "background"):
            rejected = {**pair, slot: [field] if slot == "background" else field}
            with pytest.raises(ValueError, match=f"cannot support {slot}"):
                ground_arm_answer(
                    packet, ArmScopeAnswer.model_validate({**model_answer, "pairs": [rejected]})
                )


def test_unlabelled_eligibility_stays_context_until_an_explicit_section():
    study = record()
    study["protocolSection"]["eligibilityModule"] = {
        "eligibilityCriteria": (
            "History and examination.\n"
            "Inclusion: Adults with active disease.\n"
            "Participants meeting any exclusion criteria will be excluded from this study.\n"
            "Concomitant glaucoma.\n"
        ),
    }

    sections = [
        (field.kind, field.text)
        for field in arm_packet(study).evidence
        if field.kind.startswith("eligibility")
    ]
    assert sections == [
        ("eligibility", "History and examination.\n"),
        ("eligibility_inclusion", "Inclusion: Adults with active disease.\n"),
        (
            "eligibility_exclusion",
            "Participants meeting any exclusion criteria will be excluded from this study.\n"
            "Concomitant glaucoma.\n",
        ),
    ]
