"""Exact model response hits incur no request and add no usage."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from threading import Barrier

import httpx
from pydantic import BaseModel, Field
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from thenwhat.db.models import LlmUsage
from thenwhat.llm.cache import ModelCache, request_key
from thenwhat.llm.client import Llm, LlmSettings
from thenwhat.llm.decisions import Choice, Decisions, DecisionsSettings


class Answer(BaseModel):
    word: str = Field(serialization_alias="result")


def count_usage(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(LlmUsage)) or 0


def test_structured_calls_reuse_successes_across_instances_and_batch(
    session: Session, tmp_path: Path
) -> None:
    requests = []

    def provider(messages, info) -> ModelResponse:
        requests.append(messages)
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"word": "ok"})])

    model = FunctionModel(provider)
    default = LlmSettings("test:test", Decimal(5), Decimal(1), Decimal(2))
    exhausted = LlmSettings("test:test", Decimal(0), Decimal(1), Decimal(2))
    first = Llm(session, default, model=model, cache=ModelCache(tmp_path))
    again = Llm(session, exhausted, model=model, cache=ModelCache(tmp_path))
    instructions = "Reply."
    prompt = "An input that is never stored verbatim."
    assert first.run(
        "cold", prompt=prompt, instructions=instructions, output_type=Answer
    ) == Answer(word="ok")
    assert again.run(
        "warm", prompt=prompt, instructions=instructions, output_type=Answer
    ) == Answer(word="ok")
    assert count_usage(session) == len(requests) == 1

    second = first.run_many(
        "mixed",
        prompts=[prompt, "New input", "New input"],
        instructions=instructions,
        output_type=Answer,
    )
    assert second == [Answer(word="ok")] * 3
    assert second[1] is not second[2]
    assert len(requests) == count_usage(session) == 2
    assert again.run_many(
        "warm", prompts=["New input", prompt], instructions=instructions, output_type=Answer
    ) == [
        Answer(word="ok"),
        Answer(word="ok"),
    ]
    assert len(requests) == count_usage(session) == 2
    assert prompt.encode() not in (tmp_path / "model-responses-v1/responses.sqlite3").read_bytes()


def test_decisions_reuse_an_exact_batch_and_miss_on_new_question(
    session: Session, tmp_path: Path
) -> None:
    requests = []

    def provider(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "answers": [
                    {
                        "name": "item-1",
                        "type": "choice",
                        "choice": "no",
                        "confidence": 0.9,
                        "probabilities": [
                            {"value": "yes", "probability": 0.1},
                            {"value": "no", "probability": 0.9},
                        ],
                    }
                ],
                "usage": {"input_tokens": 1000},
            },
        )

    def client() -> Decisions:
        return Decisions(
            session,
            DecisionsSettings("gpt-test", Decimal(1), Decimal(1)),
            credential="test-token",
            transport=httpx.MockTransport(provider),
            cache=ModelCache(tmp_path),
            now=lambda: datetime(2026, 11, 17, tzinfo=UTC),
        )

    opts = [("yes", "Same exact record"), ("no", "Evidence differs")]
    answers = client().choose("first", evidence="Same evidence", questions=[Choice("Same?", opts)])
    assert answers == client().choose(
        "replay", evidence="Same evidence", questions=[Choice("Same?", opts)]
    )
    assert answers[0] is not None and answers[0].choice == "no"
    assert count_usage(session) == len(requests) == 1
    client().choose("changed", evidence="Same evidence", questions=[Choice("Related?", opts)])
    assert count_usage(session) == len(requests) == 2


def test_concurrent_callers_share_first_answer(tmp_path: Path) -> None:
    started = Barrier(2)
    key = request_key("test", "one request")
    requests = []

    def fetch() -> str:
        cache = ModelCache(tmp_path)
        started.wait(timeout=5)
        with cache.locked([key]):
            cached = cache.get(key)
            if cached is not None:
                return cached
            requests.append(key)
            cache.put(key, "response")
            return "response"

    with ThreadPoolExecutor(max_workers=2) as pool:
        calls = [pool.submit(fetch) for _ in range(2)]
        assert [call.result(timeout=10) for call in calls] == ["response", "response"]
    assert requests == [key]
