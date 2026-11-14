"""Subject terms: candidates gathered by rule, the term check, the rules that decide a
link, the stored term records, the command and the review queue.

Scenario names are from openspec knowledge-cards and decision-steps.
"""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from thenwhat.claims.entities import add_synonym, entities_of
from thenwhat.claims.entry import add_claim
from thenwhat.cli import app
from thenwhat.db.models import Claim, ClaimTerm, DecisionLog, EntityMatch, EvidenceEvent, TermRecord
from thenwhat.decide.core import BackendAnswer
from thenwhat.decide.steps import TERM_MATCH, TERM_OPTIONS
from thenwhat.domain import Decider, EventType, ReviewState, TermFit, TermRole
from thenwhat.review.decisions import record_decision
from thenwhat.review.queue import decide_item, pending_items
from thenwhat.sources.base import SourceRecord
from thenwhat.sources.mesh import LabelledTerm, Mesh
from thenwhat.terms.candidates import (
    FILED_BY_REGISTRY,
    LABEL_EQUALS_NAME,
    LabelMatch,
    gather_candidates,
)
from thenwhat.terms.service import link_terms

NOW = datetime(2026, 11, 20, tzinfo=UTC)
SLUG = "knee-pain-ex1"
KNEE = ("D020370", "Osteoarthritis, Knee")
PAIN = ("D010146", "Pain")
FIBROMYALGIA = ("D005356", "Fibromyalgia")
ACCEPT, REJECT = 0.8, 0.05


def trial(
    number: str,
    conditions: tuple[tuple[str, str], ...] = (),
    interventions: tuple[tuple[str, str], ...] = (),
) -> dict[str, Any]:
    """A stored trial record, cut down to its number and the terms it is filed under."""

    def meshes(terms: tuple[tuple[str, str], ...]) -> dict[str, Any]:
        return {"meshes": [{"id": identifier, "term": label} for identifier, label in terms]}

    return {
        "protocolSection": {"identificationModule": {"nctId": number}},
        "derivedSection": {
            "conditionBrowseModule": meshes(conditions)
            | {"ancestors": [{"id": "D007592", "term": "Joint Diseases"}]},
            "interventionBrowseModule": meshes(interventions),
        },
    }


SIX_TRIALS = [
    trial("NCT00000001", (KNEE, PAIN)),
    trial("NCT00000002", (KNEE, PAIN)),
    trial("NCT00000003", (KNEE, PAIN)),
    trial("NCT00000004", (KNEE,)),
    trial("NCT00000005", (KNEE, FIBROMYALGIA)),
    trial("NCT00000006"),
]


# --- candidates gathered by rule ---------------------------------------------------


def test_claim_with_six_trials_keeps_the_terms_half_of_them_carry():
    """Scenario: Claim with trials"""
    # A trial stored with two of its events is still one trial.
    found = gather_candidates(
        trial_payloads=[*SIX_TRIALS, SIX_TRIALS[0]], label_matches=[], limit=10
    )

    assert [(c.role, c.source_name, c.identifier, c.label) for c in found] == [
        (TermRole.CONDITION, "mesh", *KNEE),
        (TermRole.CONDITION, "mesh", *PAIN),
    ]
    assert [c.reasons for c in found] == [
        ({"code": FILED_BY_REGISTRY, "trials": 5, "of": 6},),
        ({"code": FILED_BY_REGISTRY, "trials": 3, "of": 6},),
    ]


def test_claim_with_no_trial_and_a_named_drug_has_the_equal_label_as_a_candidate():
    """Scenario: Claim with no trial and a named drug"""
    found = gather_candidates(
        trial_payloads=[],
        label_matches=[
            LabelMatch(TermRole.INTERVENTION, "D000099194", "Semaglutide", "semaglutide")
        ],
        limit=10,
    )

    [candidate] = found
    assert (candidate.role, candidate.identifier) == (TermRole.INTERVENTION, "D000099194")
    assert candidate.reasons == ({"code": LABEL_EQUALS_NAME, "name": "semaglutide"},)


def test_claim_with_no_trial_and_a_free_text_condition_has_no_candidate():
    """Scenario: Claim with no trial and a free-text condition"""
    assert gather_candidates(trial_payloads=[], label_matches=[], limit=10) == []


def test_no_more_than_the_configured_number_are_kept_and_equal_labels_come_first():
    many = tuple((f"D{n:06}", f"Term {n}") for n in range(1, 13))
    found = gather_candidates(
        trial_payloads=[trial("NCT00000001", many), trial("NCT00000002", (many[4],))],
        label_matches=[LabelMatch(TermRole.CONDITION, "D000012", "Term 12", "term 12")],
        limit=3,
    )

    assert [c.label for c in found] == ["Term 12", "Term 5", "Term 1"]
    assert found[0].reasons == (
        {"code": FILED_BY_REGISTRY, "trials": 1, "of": 2},
        {"code": LABEL_EQUALS_NAME, "name": "term 12"},
    )


# --- a claim, its trials, a vocabulary and a backend ---------------------------------


def new_claim(session: Session, slug: str = SLUG, **overrides: Any) -> Claim:
    values: dict[str, Any] = {
        "slug": slug,
        "headline": "Injection eases knee pain",
        "vertical": "bones-joints-and-muscles",
        "intervention": "EX-1",
        "indication": "Knee osteoarthritis pain",
        "summary": "An injection reduced knee pain in a trial.",
    }
    return add_claim(session, **(values | overrides))


def approve_trials(session: Session, claim: Claim, payloads: list[dict[str, Any]]) -> None:
    [entity] = entities_of(session, claim)
    for payload in payloads:
        number = payload["protocolSection"]["identificationModule"]["nctId"]
        match = EntityMatch(
            entity_id=entity.id,
            source_name="clinicaltrials.gov",
            external_id=number,
            score=0.9,
            review_state=ReviewState.APPROVED,
            reviewed_at=NOW,
            reviewed_by=Decider.RULE,
        )
        session.add(match)
        session.flush()
        session.add(
            EvidenceEvent(
                claim_id=claim.id,
                entity_match_id=match.id,
                type=EventType.TRIAL_REGISTERED,
                event_date=date(2024, 7, 1),
                source_name="clinicaltrials.gov",
                source_url=f"https://clinicaltrials.gov/study/{number}",
                external_id=number,
                summary="Trial registered.",
                confidence=1.0,
                raw_payload=payload,
                fetched_at=NOW,
                dedupe_key=f"registered:{number}",
            )
        )
    session.flush()


class Vocabulary:
    """A vocabulary that holds the terms it is given and counts what it is asked."""

    name = "mesh"

    def __init__(
        self,
        definitions: dict[str, str | None] | None = None,
        labels: dict[str, list[LabelledTerm]] | None = None,
    ) -> None:
        self.definitions = definitions or {}
        self.labels = labels or {}
        self.asked: list[str] = []

    def term(self, identifier: str, *, force: bool = False) -> SourceRecord | None:
        self.asked.append(identifier)
        if identifier not in self.definitions:
            return None
        definition = self.definitions[identifier]
        payload = {
            "term": {"@id": f"http://id.nlm.nih.gov/mesh/2026/{identifier}"},
            "concept": {"scopeNote": {"@value": definition}} if definition else None,
        }
        return SourceRecord(
            "mesh", identifier, f"https://id.nlm.nih.gov/mesh/{identifier}", payload, NOW
        )

    def terms_labelled(self, name: str) -> list[LabelledTerm]:
        return self.labels.get(name.casefold(), [])


class Reader:
    """A batch backend that reads each term the way its label is given here, as
    (answer, probability). A label given as None gets no answer."""

    name = "fake"

    def __init__(self, by_label: dict[str, tuple[str, float] | None]) -> None:
        self.by_label = by_label
        self.calls: list[tuple[str, str, list[str]]] = []

    def answer_many(
        self, step: str, intro: str, question: str, items: list[str], options: list[str]
    ) -> list[BackendAnswer | None]:
        self.calls.append((step, intro, items))
        return [self._one(item, options) for item in items]

    def _one(self, item: str, options: list[str]) -> BackendAnswer | None:
        reading = next(given for label, given in self.by_label.items() if f": {label}\n" in item)
        if reading is None:
            return None
        choice, p = reading
        rest = (1 - p) / (len(options) - 1)
        return BackendAnswer(choice, {o: p if o == choice else rest for o in options})

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        raise AssertionError("Terms are checked together.")


def links(session: Session, claim: Claim) -> dict[str, ClaimTerm]:
    return {
        term.label: term
        for term in session.scalars(select(ClaimTerm).where(ClaimTerm.claim_id == claim.id))
    }


def term_logs(session: Session) -> list[DecisionLog]:
    return list(
        session.scalars(
            select(DecisionLog).where(DecisionLog.step == TERM_MATCH).order_by(DecisionLog.id)
        )
    )


@pytest.fixture
def knee_claim(session: Session) -> Claim:
    claim = new_claim(session)
    approve_trials(session, claim, SIX_TRIALS)
    return claim


# --- the term check ----------------------------------------------------------------


def test_each_candidate_gets_one_log_record_naming_the_claim_and_the_term(
    session: Session, knee_claim: Claim
):
    """Scenario: Ten candidates for one claim"""
    backend = Reader({"Osteoarthritis, Knee": ("same", 0.95), "Pain": ("broader", 0.6)})
    vocabulary = Vocabulary({"D020370": "A degenerative disease of the knee joint."})

    run = link_terms(
        session,
        knee_claim,
        vocabulary=vocabulary,
        backend=backend,
        now=NOW,
        accept_above=ACCEPT,
        reject_below=REJECT,
    )

    assert run.gathered == 2 and len(run.added) == 2 and run.unscored == []
    logs = term_logs(session)
    assert [log.input_ref for log in logs] == [
        f"claim:{knee_claim.id}:condition:mesh:D020370",
        f"claim:{knee_claim.id}:condition:mesh:D010146",
    ]
    assert all(log.options == TERM_OPTIONS and log.error is None for log in logs)
    # What is judged: the claim's own words with the term's label and definition.
    [(step, intro, items)] = backend.calls
    assert step == TERM_MATCH
    assert "Injection eases knee pain" in intro and "An injection reduced knee pain" in intro
    assert "Intervention: EX-1." in intro and "Indication: Knee osteoarthritis pain." in intro
    assert items[0].endswith(
        "Osteoarthritis, Knee\nDefinition: A degenerative disease of the knee joint."
    )
    assert items[1].endswith("Pain\nDefinition: none given")


def test_backend_failure_leaves_the_candidate_without_a_score(session: Session, knee_claim: Claim):
    """Scenario: Backend failure"""
    backend = Reader({"Osteoarthritis, Knee": ("same", 0.95), "Pain": None})

    run = link_terms(
        session,
        knee_claim,
        vocabulary=Vocabulary(),
        backend=backend,
        now=NOW,
        accept_above=ACCEPT,
        reject_below=REJECT,
    )

    found = links(session, knee_claim)
    assert [term.label for term in run.unscored] == ["Pain"]
    assert found["Pain"].score is None and found["Pain"].fit is None
    assert found["Pain"].review_state is ReviewState.PENDING
    assert found["Osteoarthritis, Knee"].review_state is ReviewState.APPROVED
    failed = term_logs(session)[1]
    assert failed.input_ref.endswith("D010146") and failed.error

    # The next run asks again only about the candidate that has no score.
    backend.by_label["Pain"] = ("broader", 0.9)
    again = link_terms(
        session,
        knee_claim,
        vocabulary=Vocabulary(),
        backend=backend,
        now=NOW,
        accept_above=ACCEPT,
        reject_below=REJECT,
    )

    assert [term.label for term in again.scored] == ["Pain"]
    assert len(backend.calls[-1][2]) == 1
    assert found["Pain"].score == pytest.approx(0.9)


# --- links decided by rule ---------------------------------------------------------


def test_exact_broader_and_wrongly_filed_terms_are_decided_by_rule(session: Session):
    """Scenarios: Exact term, Broader term, Term the registry filed wrongly, Confident
    exact term, Wrongly filed term"""
    claim = new_claim(
        session,
        slug="hepatitis-b-ex2",
        headline="Drug clears hepatitis B",
        vertical="infections",
        indication="Chronic hepatitis B",
    )
    chronic = ("D019694", "Hepatitis B, Chronic")
    liver = ("D008107", "Liver Diseases")
    parkinson = ("D010300", "Parkinson Disease")
    approve_trials(session, claim, [trial("NCT00000007", (chronic, liver, parkinson))])
    backend = Reader(
        {
            "Hepatitis B, Chronic": ("same", 0.95),
            "Liver Diseases": ("broader", 0.9),
            "Parkinson Disease": ("something_else", 0.97),
        }
    )

    link_terms(
        session,
        claim,
        vocabulary=Vocabulary(),
        backend=backend,
        now=NOW,
        accept_above=ACCEPT,
        reject_below=REJECT,
    )

    found = links(session, claim)
    exact, broader, wrong = (found[label] for _, label in (chronic, liver, parkinson))
    assert (exact.fit, exact.score) == (TermFit.EXACT, pytest.approx(0.95))
    assert (broader.fit, broader.score) == (TermFit.BROADER, pytest.approx(0.9))
    assert (wrong.fit, wrong.score) == (None, 0.0)
    assert [t.review_state for t in (exact, broader, wrong)] == [
        ReviewState.APPROVED,
        ReviewState.APPROVED,
        ReviewState.REJECTED,
    ]
    assert all(t.reviewed_by is Decider.RULE and t.reviewed_at == NOW for t in found.values())
    assert exact.reasons == [{"code": FILED_BY_REGISTRY, "trials": 1, "of": 1}]


def test_score_between_the_two_levels_waits_for_review(session: Session, knee_claim: Claim):
    backend = Reader({"Osteoarthritis, Knee": ("same", 0.6), "Pain": ("broader", 0.5)})

    link_terms(
        session,
        knee_claim,
        vocabulary=Vocabulary(),
        backend=backend,
        now=NOW,
        accept_above=ACCEPT,
        reject_below=REJECT,
    )

    assert {t.review_state for t in links(session, knee_claim).values()} == {ReviewState.PENDING}


def test_link_the_operator_rejected_stays_rejected(session: Session, knee_claim: Claim):
    backend = Reader({"Osteoarthritis, Knee": ("same", 0.95), "Pain": ("broader", 0.9)})
    link_terms(
        session,
        knee_claim,
        vocabulary=Vocabulary(),
        backend=backend,
        now=NOW,
        accept_above=ACCEPT,
        reject_below=REJECT,
    )
    knee = links(session, knee_claim)["Osteoarthritis, Knee"]
    assert knee.review_state is ReviewState.APPROVED

    decide_item(session, "term", knee.id, ReviewState.REJECTED, now=NOW + timedelta(hours=1))
    again = link_terms(
        session,
        knee_claim,
        vocabulary=Vocabulary(),
        backend=backend,
        now=NOW + timedelta(days=1),
        accept_above=ACCEPT,
        reject_below=REJECT,
    )

    assert again.added == [] and again.scored == []
    assert len(backend.calls) == 1
    assert (knee.review_state, knee.reviewed_by) == (ReviewState.REJECTED, Decider.HUMAN)
    # The operator's rejection is the label for the answer the term was given.
    assert term_logs(session)[0].human_label == "something_else"


# --- term records ------------------------------------------------------------------


def test_second_run_makes_no_request_and_an_old_record_is_fetched_again(
    session: Session, fake_time, fixture_json
):
    claim = new_claim(session, slug="obesity-ex3", indication="Obesity")
    add_synonym(session, claim.slug, "EX-1", "examplutide")
    requests: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        path = request.url.path
        if path.endswith("/lookup/descriptor"):
            name = "label_obesity" if request.url.params["label"] == "Obesity" else "label_none"
        elif path.endswith("/D009765.json"):
            name = "descriptor_obesity"
        else:
            name = "concept_obesity"
        return httpx.Response(200, json=fixture_json(f"mesh/{name}.json"))

    vocabulary = Mesh(
        session,
        contact_email="ops@thenwhat.test",
        transport=httpx.MockTransport(answer),
        time=fake_time,
    )
    backend = Reader({"Obesity": ("same", 0.95)})

    def run() -> None:
        link_terms(
            session,
            claim,
            vocabulary=vocabulary,
            backend=backend,
            now=fake_time.now(),
            accept_above=ACCEPT,
            reject_below=REJECT,
        )

    run()

    [link] = links(session, claim).values()
    assert (link.role, link.external_id, link.review_state) == (
        TermRole.CONDITION,
        "D009765",
        ReviewState.APPROVED,
    )
    assert link.reasons == [{"code": LABEL_EQUALS_NAME, "name": "Obesity"}]
    record = session.get(TermRecord, ("mesh", "D009765"))
    assert record is not None
    assert record.url == "https://id.nlm.nih.gov/mesh/D009765"
    assert record.payload["concept"]["scopeNote"]["@value"].startswith("A status with BODY")
    # Three names looked up, then the term and its concept.
    assert len(requests) == 5
    first_read = record.fetched_at

    run()

    assert len(requests) == 5

    fake_time.advance(timedelta(days=91))
    run()

    assert [r.url.path for r in requests[-2:]] == [
        "/mesh/2026/D009765.json",
        "/mesh/2026/M0015159.json",
    ]
    assert record.fetched_at - first_read > timedelta(days=90)


# --- the review queue --------------------------------------------------------------


def test_queue_lists_a_pending_term_link_and_the_operator_can_approve_it(
    session: Session, knee_claim: Claim
):
    backend = Reader({"Osteoarthritis, Knee": ("same", 0.95), "Pain": ("broader", 0.5)})
    link_terms(
        session,
        knee_claim,
        vocabulary=Vocabulary(),
        backend=backend,
        now=NOW,
        accept_above=ACCEPT,
        reject_below=REJECT,
    )

    [item] = pending_items(session, claim_slug=SLUG, kind="term")

    pain = links(session, knee_claim)["Pain"]
    assert (item.kind, item.id, item.score) == ("term", pain.id, pytest.approx(0.5))
    assert item.assertion == (
        "subject term 'Pain' (mesh D010146) for the claim's condition, read as broader."
        " Reasons: filed_by_registry (3 of 6 trials)"
    )
    assert item.source_url == "https://id.nlm.nih.gov/mesh/D010146"
    assert item.reasons == (FILED_BY_REGISTRY,)

    decide_item(session, "term", pain.id, ReviewState.APPROVED, now=NOW)

    assert (pain.review_state, pain.reviewed_by) == (ReviewState.APPROVED, Decider.HUMAN)
    assert pending_items(session, claim_slug=SLUG, kind="term") == []
    assert term_logs(session)[1].human_label == "broader"


# --- the command -------------------------------------------------------------------


@pytest.fixture
def run(session: Session, monkeypatch: pytest.MonkeyPatch):
    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    monkeypatch.setattr("thenwhat.cli.entry.open_session", test_session)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")
    for name in ("MATCH_ACCEPT_ABOVE", "MATCH_REJECT_BELOW", "TERM_CANDIDATES_MAX"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr("thenwhat.cli.terms.make_vocabulary", lambda s: Vocabulary())
    monkeypatch.setattr(
        "thenwhat.cli.resolve.make_backend",
        lambda s: Reader({"Osteoarthritis, Knee": ("same", 0.95), "Pain": ("broader", 0.5)}),
    )
    runner = CliRunner()
    return lambda *arguments: runner.invoke(app, list(arguments), env={"COLUMNS": "200"})


def test_terms_proposes_and_decides_a_claims_subject_terms(
    run, session: Session, knee_claim: Claim
):
    result = run("terms", SLUG)

    assert result.exit_code == 0, result.output
    assert f"{SLUG}: 2 candidate subject term(s), 2 new." in result.output
    assert "Approved by rule: 1 exact, 0 broader. Rejected by rule: 0. Pending review: 1." in (
        result.output
    )
    assert "approved 0.95  condition  exact  D020370  Osteoarthritis, Knee" in result.output


def test_terms_missing_covers_published_claims_without_a_candidate(
    run, session: Session, knee_claim: Claim
):
    record_decision(knee_claim, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    new_claim(session, slug="draft-ex4", intervention="EX-4")
    session.flush()

    result = run("terms", "--missing")

    assert result.exit_code == 0, result.output
    assert SLUG in result.output and "draft-ex4" not in result.output
    assert "Every published claim has a candidate subject term." in run("terms", "--missing").output


def test_terms_refuses_without_claims_or_missing(run):
    result = run("terms")

    assert result.exit_code == 1
    assert "Name the claims" in result.output
