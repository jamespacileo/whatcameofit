"""The lookup command: wiring, messages and exit codes only. The rules are in test_lookup.py."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from thenwhat.cli import app
from thenwhat.decide.core import BackendAnswer
from thenwhat.llm.client import Llm, LlmSettings
from thenwhat.sources.base import SourceRecord

NOW = datetime(2026, 11, 20, tzinfo=UTC)
READING = {
    "about_a_treatment": True,
    "gist": "An antibody was reported to regrow missing teeth.",
    "intervention": "EX-1",
    "indication": "tooth agenesis",
}


class Trials:
    def search_trials(self, intervention: str, condition: str | None = None) -> list[SourceRecord]:
        payload = {
            "protocolSection": {
                "identificationModule": {"nctId": "NCT00000001", "briefTitle": "EX-1 in people"}
            }
        }
        url = "https://clinicaltrials.gov/study/NCT00000001"
        return [SourceRecord("clinicaltrials.gov", "NCT00000001", url, payload, NOW)]

    def fetch_trial(self, nct_id: str) -> SourceRecord | None:
        return None


class Backend:
    name = "fake"

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        rest = 0.2 / (len(options) - 1)
        return BackendAnswer(options[0], {o: 0.8 if o == options[0] else rest for o in options})


@pytest.fixture
def run(session: Session, monkeypatch: pytest.MonkeyPatch):
    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    def respond(messages, info) -> ModelResponse:
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, READING)])

    settings = LlmSettings("test:scripted", Decimal("10"), Decimal("3"), Decimal("15"))
    llm = Llm(session, settings, model=FunctionModel(respond, model_name="scripted"))
    monkeypatch.setattr("thenwhat.cli.entry.open_session", test_session)
    monkeypatch.setattr("thenwhat.cli.lookup.make_tools", lambda s: (llm, Backend(), Trials()))
    runner = CliRunner()
    return lambda *arguments, text="": runner.invoke(
        app, list(arguments), input=text, env={"COLUMNS": "200"}
    )


def test_lookup_of_pasted_text_lists_the_candidates(run):
    result = run("lookup", "--paste", text="Scientists say EX-1 regrew teeth in people.")

    assert result.exit_code == 0, result.output
    assert "Treatment: EX-1" in result.output and "Condition: tooth agenesis" in result.output
    assert "0.80  NCT00000001  https://clinicaltrials.gov/study/NCT00000001" in result.output
    assert "EX-1 in people" in result.output


def test_lookup_with_no_address_and_no_text_explains_and_exits_1(run):
    result = run("lookup")

    assert result.exit_code == 1
    assert "--paste" in result.output
