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

from thenwhat.claims.entities import add_search_phrase, add_synonym, entities_of
from thenwhat.claims.entry import add_claim
from thenwhat.cli import app
from thenwhat.db.models import Claim, ClaimTerm, DecisionLog, EntityMatch, EvidenceEvent, TermRecord
from thenwhat.decide.core import BackendAnswer
from thenwhat.decide.steps import (
    INTERVENTION_KIND,
    NONE_OF_THESE,
    TARGET_MATCH,
    TARGET_OPTIONS,
    TERM_MATCH,
    TERM_OPTIONS,
    choose_intervention_kind,
    kind_options,
)
from thenwhat.domain import Decider, EventType, ReviewState, TermFit, TermRole
from thenwhat.review.decisions import record_decision
from thenwhat.review.queue import decide_item, pending_items
from thenwhat.sources.base import SourceRecord
from thenwhat.sources.mesh import LabelledTerm, Mesh
from thenwhat.sources.opentargets import NamedTarget, OpenTargets
from thenwhat.terms.candidates import (
    ENTRY_TERM_EQUALS_NAME,
    FILED_BY_REGISTRY,
    LABEL_EQUALS_NAME,
    LabelMatch,
    gather_candidates,
)
from thenwhat.terms.drugs import DRUG_NAME_EQUALS_NAME
from thenwhat.terms.genes import WORD_EQUALS_SYMBOL, WORD_EQUALS_SYNONYM, gene_like_words
from thenwhat.terms.kinds import KIND_CHOSEN, KINDS, REGISTRY_LISTS_TYPE, Kind, registry_types
from thenwhat.terms.records import read_record
from thenwhat.terms.service import (
    KindTermMissing,
    link_drug,
    link_kind,
    link_targets,
    link_terms,
)

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
        unresolved: dict[str, list[str]] | None = None,
    ) -> None:
        self.definitions = definitions or {}
        self.labels = labels or {}
        self.unresolved = unresolved or {}
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

    def unresolved_entry_terms(self, name: str) -> list[str]:
        return self.unresolved.get(name.casefold(), [])


class Reader:
    """A batch backend that reads each term the way its label is given here, as
    (answer, probability). A label given as None gets no answer."""

    name = "fake"

    def __init__(
        self,
        by_label: dict[str, tuple[str, float] | None] | None = None,
        *,
        kind: tuple[str, float] | None = None,
    ) -> None:
        self.by_label = by_label or {}
        # The kind chosen for a claim's intervention, with its probability. With none
        # given, the backend fails when a kind is asked for.
        self.kind = kind
        self.calls: list[tuple[str, str, list[str]]] = []
        self.kinds_asked: list[tuple[str, list[str]]] = []

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
        assert step == INTERVENTION_KIND, "Terms and genes are checked together."
        self.kinds_asked.append((state, options))
        if self.kind is None:
            raise RuntimeError("no answer")
        choice, p = self.kind
        rest = (1 - p) / (len(options) - 1)
        return BackendAnswer(choice, {o: p if o == choice else rest for o in options})


class Genes:
    """A target source that holds the genes it is given, by the word that finds them,
    and counts what it is asked."""

    name = "opentargets"

    def __init__(self, by_word: dict[str, list[NamedTarget]] | None = None) -> None:
        self.by_word = {word.casefold(): found for word, found in (by_word or {}).items()}
        self.searched: list[str] = []
        self.fetched: list[str] = []

    def targets_named(self, word: str) -> list[NamedTarget]:
        self.searched.append(word)
        return self.by_word.get(word.casefold(), [])

    def target(self, identifier: str, *, force: bool = False) -> SourceRecord | None:
        self.fetched.append(identifier)
        for found in self.by_word.values():
            for target in found:
                if target.identifier == identifier:
                    payload = {
                        "id": identifier,
                        "approvedSymbol": target.symbol,
                        "approvedName": target.name,
                        "functionDescriptions": [f"What {target.symbol} does."],
                    }
                    return SourceRecord(
                        "opentargets",
                        identifier,
                        f"https://platform.opentargets.org/target/{identifier}",
                        payload,
                        NOW,
                    )
        return None


class Drugs:
    """A drug source that holds the drugs it is given, by its own name for each, and
    counts what it is asked."""

    name = "opentargets"

    def __init__(self, by_name: dict[str, dict[str, Any]] | None = None) -> None:
        self.by_name = {name.casefold(): drug for name, drug in (by_name or {}).items()}
        self.searched: list[str] = []
        self.fetched: list[str] = []

    def _record(self, drug: dict[str, Any]) -> SourceRecord:
        return SourceRecord(
            "opentargets",
            drug["id"],
            f"https://platform.opentargets.org/drug/{drug['id']}",
            drug,
            NOW,
        )

    def drugs_named(self, name: str) -> list[SourceRecord]:
        self.searched.append(name)
        drug = self.by_name.get(name.casefold())
        return [self._record(drug)] if drug else []

    def drug(self, identifier: str, *, force: bool = False) -> SourceRecord | None:
        self.fetched.append(identifier)
        for drug in self.by_name.values():
            if drug["id"] == identifier:
                return self._record(drug)
        return None


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
        if path.endswith("/lookup/term"):
            name = "label_none"
        elif path.endswith("/lookup/descriptor"):
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
    # Three names looked up as labels and as entry terms, then the term and its concept.
    assert len(requests) == 8
    first_read = record.fetched_at

    run()

    assert len(requests) == 8

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
    for name in ("TARGET_CANDIDATES_MAX",):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(
        "thenwhat.cli.terms.make_vocabulary",
        lambda s: Vocabulary({"D010455": "Compounds of AMINO ACIDS joined by peptide bonds."}),
    )
    monkeypatch.setattr("thenwhat.cli.terms.make_genes", lambda s: Genes())
    monkeypatch.setattr("thenwhat.cli.terms.make_drugs", lambda s: Drugs())
    monkeypatch.setattr(
        "thenwhat.cli.resolve.make_backend",
        lambda s: Reader(
            {"Osteoarthritis, Knee": ("same", 0.95), "Pain": ("broader", 0.5)},
            kind=("peptide", 0.9),
        ),
    )
    runner = CliRunner()
    # Wide and plain, so that what is asserted is the words and not how a terminal, or a
    # CI runner that forces colour, would wrap or style them.
    plain = {"COLUMNS": "200", "NO_COLOR": "1", "TERM": "dumb"}
    return lambda *arguments: runner.invoke(app, list(arguments), env=plain)


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
    # The kind and the named genes are run for the claim too, and counted on its line.
    assert (
        "Kind: peptide 0.90, approved by rule (D010455 Peptides)."
        " Named genes: 0 candidate(s), 0 new. Approved by rule: 0. Rejected by rule: 0."
        " Pending review: 0." in result.output
    )


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
    assert run("terms", SLUG, "--all").exit_code == 1


# --- entry terms -------------------------------------------------------------------


def test_name_equal_to_an_entry_term_is_a_candidate_that_records_the_entry_term():
    """Scenario: Name equal to an entry term"""
    [candidate] = gather_candidates(
        trial_payloads=[],
        label_matches=[
            LabelMatch(
                TermRole.INTERVENTION,
                "D055423",
                "Diet, Ketogenic",
                "Ketogenic diet",
                "Ketogenic Diet",
            )
        ],
        limit=10,
    )

    assert (candidate.identifier, candidate.label) == ("D055423", "Diet, Ketogenic")
    assert candidate.reasons == (
        {"code": ENTRY_TERM_EQUALS_NAME, "entry_term": "Ketogenic Diet", "name": "Ketogenic diet"},
    )


def test_supplementary_record_is_a_candidate():
    """Scenario: Newly named compound held as a supplementary record"""
    [candidate] = gather_candidates(
        trial_payloads=[],
        label_matches=[
            LabelMatch(TermRole.INTERVENTION, "C000729680", "orforglipron", "Orforglipron")
        ],
        limit=10,
    )

    assert (candidate.source_name, candidate.identifier) == ("mesh", "C000729680")
    assert candidate.reasons == ({"code": LABEL_EQUALS_NAME, "name": "Orforglipron"},)


def test_term_found_by_label_and_entry_term_carries_the_label_reason_only():
    found = gather_candidates(
        trial_payloads=[trial("NCT00000001", (KNEE, PAIN)), trial("NCT00000002", (KNEE,))],
        label_matches=[
            # One of the claim's names equals an entry term, another the label itself.
            LabelMatch(TermRole.CONDITION, "D009765", "Obesity", "Adiposity", "Adiposity"),
            LabelMatch(TermRole.CONDITION, "D009765", "Obesity", "obesity"),
            LabelMatch(TermRole.INTERVENTION, "D055423", "Diet, Ketogenic", "Keto", "Keto"),
        ],
        limit=3,
    )

    # Entry-term matches rank with label matches, ahead of what the registry files.
    assert [c.label for c in found] == ["Obesity", "Diet, Ketogenic", "Osteoarthritis, Knee"]
    assert found[0].reasons == ({"code": LABEL_EQUALS_NAME, "name": "obesity"},)
    assert found[1].reasons == (
        {"code": ENTRY_TERM_EQUALS_NAME, "entry_term": "Keto", "name": "Keto"},
    )


def test_search_phrase_equal_to_an_entry_term_makes_no_candidate(session: Session):
    """Scenario: Search phrase equal to an entry term"""
    claim = new_claim(session, slug="diet-ex5", intervention="Very low carbohydrate eating plan")
    add_search_phrase(session, claim.slug, "Very low carbohydrate eating plan", "ketogenic diet")
    vocabulary = Vocabulary(
        labels={"ketogenic diet": [LabelledTerm("D055423", "Diet, Ketogenic", "Ketogenic Diet")]}
    )

    run = link_terms(session, claim, vocabulary=vocabulary, backend=Reader(), now=NOW)

    assert run.gathered == 0 and links(session, claim) == {}


def test_name_whose_entry_term_has_no_record_is_reported_and_makes_no_candidate(
    session: Session, knee_claim: Claim
):
    """Scenario: Entry term whose record cannot be found"""
    add_synonym(session, SLUG, "EX-1", "examplutide")
    vocabulary = Vocabulary(unresolved={"examplutide": ["examplutide"]})
    backend = Reader({"Osteoarthritis, Knee": ("same", 0.95), "Pain": ("broader", 0.9)})

    run = link_terms(
        session,
        knee_claim,
        vocabulary=vocabulary,
        backend=backend,
        now=NOW,
        accept_above=ACCEPT,
        reject_below=REJECT,
    )

    # The run goes on: the claim's other candidates are gathered and decided.
    assert run.unresolved == ["examplutide"]
    assert sorted(links(session, knee_claim)) == ["Osteoarthritis, Knee", "Pain"]
    assert len(run.scored) == 2


# --- term records, by source -------------------------------------------------------


def test_target_record_gives_its_first_function_description_word_for_word(
    session: Session, fixture_json
):
    target = fixture_json("opentargets/target_cxcr3.json")["data"]["target"]
    record = TermRecord(
        source_name="opentargets",
        external_id="ENSG00000186810",
        url="https://platform.opentargets.org/target/ENSG00000186810",
        payload=target,
        fetched_at=NOW,
    )

    read = read_record(record)

    assert read.label == "CXCR3" and read.version is None
    assert read.definition is not None
    assert read.definition == target["functionDescriptions"][0]
    assert "(PubMed:" in read.definition and read.definition.startswith("[Isoform 1]: ")


# --- kinds -------------------------------------------------------------------------


def test_list_of_kinds_has_unique_codes_and_descriptors_in_a_stable_order():
    codes = [kind.code for kind in KINDS]
    identifiers = [kind.identifier for kind in KINDS]

    assert len(set(codes)) == len(codes) == 22
    assert len(set(identifiers)) == len(identifiers)
    assert all(identifier[0] == "D" and identifier[1:].isdigit() for identifier in identifiers)
    assert all(kind.label and kind.code != NONE_OF_THESE for kind in KINDS)
    assert codes[:3] == ["antibody", "peptide", "oligonucleotide"] and codes[-1] == "exercise"
    assert kind_options([(k.code, k.label) for k in KINDS]) == [*codes, NONE_OF_THESE]


def device_trial(number: str, *listed: tuple[str, str]) -> dict[str, Any]:
    """A stored trial record with the interventions it lists, as (type, name)."""
    payload = trial(number)
    payload["protocolSection"]["armsInterventionsModule"] = {
        "interventions": [{"type": kind, "name": name} for kind, name in listed]
    }
    return payload


def test_registry_type_is_read_for_the_claims_intervention_and_not_for_a_comparator():
    """Scenario: Registry lists the intervention as a device"""
    payloads = [
        device_trial("NCT00000011", ("DEVICE", "Wrist stimulator"), ("DRUG", "Placebo")),
        device_trial("NCT00000012", ("DEVICE", "wrist  stimulator")),
        device_trial("NCT00000013", ("DEVICE", "MNS band"), ("OTHER", "Usual care")),
        device_trial("NCT00000014", ("DRUG", "Clonidine")),
    ]

    # A trial stored with two of its events is still one trial.
    found = registry_types([*payloads, payloads[0]], ["Wrist stimulator", "MNS band"])

    assert found == [{"code": REGISTRY_LISTS_TYPE, "type": "DEVICE", "trials": 3}]
    assert registry_types(payloads, ["Something else"]) == []


def kind_logs(session: Session) -> list[DecisionLog]:
    return list(
        session.scalars(
            select(DecisionLog)
            .where(DecisionLog.step == INTERVENTION_KIND)
            .order_by(DecisionLog.id)
        )
    )


def test_kind_step_logs_one_record_with_every_kinds_probability(
    session: Session, knee_claim: Claim
):
    """Scenario: One claim"""
    backend = Reader(kind=("device", 0.9))
    offered = [(kind.code, kind.label) for kind in KINDS]

    decision = choose_intervention_kind(session, backend, knee_claim, kinds=offered, now=NOW)

    assert decision is not None and decision.choice == "device"
    [log] = kind_logs(session)
    assert log.input_ref == f"claim:{knee_claim.id}"
    assert log.options == [*(kind.code for kind in KINDS), NONE_OF_THESE]
    assert log.output is not None
    assert set(log.output["probabilities"]) == set(log.options)
    assert log.output["probabilities"]["device"] == pytest.approx(0.9)
    # What is judged: the headline, summary and intervention names, not the indication.
    [(state, _)] = backend.kinds_asked
    assert "Injection eases knee pain" in state and "Intervention: EX-1." in state
    assert "Indication:" not in state
    assert "- device: Equipment and Supplies" in state


def test_kind_step_backend_failure_is_logged_and_gives_no_answer(
    session: Session, knee_claim: Claim
):
    """Scenario: Backend failure"""
    offered = [(kind.code, kind.label) for kind in KINDS]

    assert choose_intervention_kind(session, Reader(), knee_claim, kinds=offered, now=NOW) is None

    [log] = kind_logs(session)
    assert log.error and log.output is None


DEVICE_TERM = "D004599"


def stimulator_claim(session: Session) -> Claim:
    claim = new_claim(
        session,
        slug="tourette-wrist-device",
        headline="Wrist device calms tics",
        vertical="brain-and-nerves",
        intervention="Wrist-worn median nerve stimulation device",
        indication="Tourette syndrome",
        summary="A wrist-worn stimulator reduced tics in a trial.",
    )
    approve_trials(
        session,
        claim,
        [
            device_trial(f"NCT0000002{n}", ("DEVICE", "Wrist-worn median nerve stimulation device"))
            for n in range(3)
        ],
    )
    return claim


def kind_run(session: Session, claim: Claim, backend: Reader, vocabulary=None, kinds=KINDS):
    return link_kind(
        session,
        claim,
        vocabulary=vocabulary or Vocabulary({DEVICE_TERM: "Use of electric potential."}),
        backend=backend,
        now=NOW,
        kinds=kinds,
        accept_above=ACCEPT,
        reject_below=REJECT,
    )


def test_device_described_in_a_reports_words_gets_a_kind_link_approved_by_rule(session: Session):
    """Scenarios: Device described in a report's words, Registry lists the intervention
    as a device"""
    claim = stimulator_claim(session)

    run = kind_run(session, claim, Reader(kind=("electrical_stimulation", 0.9)))

    assert run.asked and run.chosen == "electrical_stimulation" and run.link is not None
    [link] = links(session, claim).values()
    assert link is run.link
    assert (link.role, link.source_name, link.external_id) == (
        TermRole.INTERVENTION,
        "mesh",
        DEVICE_TERM,
    )
    assert (link.fit, link.score) == (TermFit.KIND, pytest.approx(0.9))
    assert (link.review_state, link.reviewed_by) == (ReviewState.APPROVED, Decider.RULE)
    assert link.label == "Electric Stimulation Therapy"
    # The registry's type is a reason and nothing more: the score is the decision's.
    assert link.reasons == [
        {"code": KIND_CHOSEN, "kind": "electrical_stimulation"},
        {"code": REGISTRY_LISTS_TYPE, "type": "DEVICE", "trials": 3},
    ]
    assert session.get(TermRecord, ("mesh", DEVICE_TERM)) is not None


def test_kind_scored_between_the_levels_is_left_pending_and_not_asked_again(session: Session):
    claim = stimulator_claim(session)
    backend = Reader(kind=("electrical_stimulation", 0.5))

    run = kind_run(session, claim, backend)

    assert run.link is not None and run.link.review_state is ReviewState.PENDING
    assert kind_run(session, claim, backend).asked is False
    assert len(backend.kinds_asked) == 1


def test_none_of_these_stores_nothing_and_is_asked_again_only_when_the_list_changes(
    session: Session,
):
    """Scenarios: Intervention that fits no kind, Second run, Kind added to the list"""
    claim = stimulator_claim(session)
    backend = Reader(kind=(NONE_OF_THESE, 0.7))

    run = kind_run(session, claim, backend)

    assert run.asked and run.chosen == NONE_OF_THESE and run.link is None
    assert links(session, claim) == {}

    assert kind_run(session, claim, backend).asked is False
    assert len(kind_logs(session)) == 1

    longer = (*KINDS, Kind("light_therapy", "D010789", "Phototherapy"))
    backend.kind = ("light_therapy", 0.9)
    again = kind_run(
        session, claim, backend, Vocabulary({"D010789": "Treatment with light."}), kinds=longer
    )

    assert again.asked and again.link is not None and again.link.external_id == "D010789"
    # A claim that has a kind link is not asked again, whatever the list.
    assert kind_run(session, claim, backend).asked is False
    assert len(kind_logs(session)) == 2


def test_claim_with_an_approved_exact_intervention_term_is_not_asked_for_a_kind(
    session: Session,
):
    """Scenario: Intervention with an exact term"""
    claim = stimulator_claim(session)
    session.add(
        ClaimTerm(
            claim_id=claim.id,
            role=TermRole.INTERVENTION,
            source_name="mesh",
            external_id="D000099194",
            label="Semaglutide",
            score=0.95,
            fit=TermFit.EXACT,
            review_state=ReviewState.APPROVED,
            reviewed_at=NOW,
            reviewed_by=Decider.RULE,
        )
    )
    session.flush()
    backend = Reader(kind=("peptide", 0.9))

    assert kind_run(session, claim, backend).asked is False
    assert backend.kinds_asked == [] and kind_logs(session) == []


def test_kinds_term_the_operator_already_rejected_stays_rejected_and_is_not_linked_twice(
    session: Session,
):
    """Scenario: Kind's term already a link for the claim"""
    claim = stimulator_claim(session)
    filed = ClaimTerm(
        claim_id=claim.id,
        role=TermRole.INTERVENTION,
        source_name="mesh",
        external_id=DEVICE_TERM,
        label="Electric Stimulation Therapy",
        score=0.9,
        fit=TermFit.BROADER,
        reasons=[{"code": FILED_BY_REGISTRY, "trials": 3, "of": 3}],
        review_state=ReviewState.REJECTED,
        reviewed_at=NOW,
        reviewed_by=Decider.HUMAN,
    )
    session.add(filed)
    session.flush()
    backend = Reader(kind=("electrical_stimulation", 0.95))

    run = kind_run(session, claim, backend)

    assert run.asked and run.chosen == "electrical_stimulation" and run.link is None
    assert list(links(session, claim).values()) == [filed]
    assert (filed.review_state, filed.fit) == (ReviewState.REJECTED, TermFit.BROADER)
    # The answer is on record, so the claim is not asked again.
    assert kind_run(session, claim, backend).asked is False


def test_kind_whose_term_the_vocabulary_does_not_hold_stops_the_run(session: Session):
    """Scenario: Kind whose term the vocabulary does not hold"""
    claim = stimulator_claim(session)

    with pytest.raises(KindTermMissing, match=r"'electrical_stimulation'.*D004599"):
        kind_run(session, claim, Reader(kind=("electrical_stimulation", 0.9)), Vocabulary())

    assert links(session, claim) == {}


def test_kind_backend_failure_stores_nothing_and_the_claim_is_asked_again(session: Session):
    claim = stimulator_claim(session)
    backend = Reader()

    run = kind_run(session, claim, backend)

    assert run.asked and run.failed and run.link is None
    assert links(session, claim) == {}
    backend.kind = ("electrical_stimulation", 0.9)
    assert kind_run(session, claim, backend).link is not None


# --- named genes -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("names", "words"),
    [
        (["Anti-CXCR3 antibody"], ["CXCR3"]),
        (["CPNE7-derived peptide"], ["CPNE7"]),
        (["APOE4-to-APOE3 base editing"], ["APOE4"]),
        (["Aspirin"], []),
        (["Vitamin C"], []),
        (
            ["Tooth regrowth antibody (anti-USAG-1)", "TRG-035, GLP-1"],
            ["USAG-1", "TRG-035", "GLP-1"],
        ),
        (["Transcranial magnetic stimulation", "TMS", "tms"], ["TMS"]),
    ],
)
def test_gene_like_words_of_an_interventions_names(names: list[str], words: list[str]):
    assert gene_like_words(names) == words


CXCR3 = NamedTarget("ENSG00000186810", "CXCR3", "C-X-C motif chemokine receptor 3", "symbol")
TYMS = NamedTarget(
    "ENSG00000176890", "TYMS", "thymidylate synthetase", "synonym", ("HGNC", "NCBI_entrez")
)
APOE = NamedTarget("ENSG00000130203", "APOE", "apolipoprotein E", "synonym", ("NCBI_entrez",))


def gene_claim(session: Session, intervention: str, *others: str, slug: str = "gene-ex6") -> Claim:
    claim = new_claim(session, slug=slug, intervention=intervention)
    for other in others:
        add_synonym(session, slug, intervention, other)
    return claim


def targets_run(session: Session, claim: Claim, genes: Genes, backend: Reader, limit: int = 3):
    return link_targets(
        session,
        claim,
        genes=genes,
        backend=backend,
        now=NOW,
        limit=limit,
        accept_above=ACCEPT,
        reject_below=REJECT,
    )


def target_logs(session: Session) -> list[DecisionLog]:
    return list(
        session.scalars(
            select(DecisionLog).where(DecisionLog.step == TARGET_MATCH).order_by(DecisionLog.id)
        )
    )


def test_antibody_named_after_its_target_gets_a_target_link_approved_by_rule(session: Session):
    """Scenario: Antibody named after its target"""
    claim = gene_claim(session, "Anti-CXCR3 antibody")
    genes = Genes({"CXCR3": [CXCR3]})
    backend = Reader({"CXCR3": ("acts_on_or_made_from", 0.95)})

    run = targets_run(session, claim, genes, backend)

    assert run.gathered == 1 and len(run.added) == 1 and run.unscored == []
    [link] = links(session, claim).values()
    assert (link.role, link.source_name, link.external_id, link.label) == (
        TermRole.TARGET,
        "opentargets",
        "ENSG00000186810",
        "CXCR3",
    )
    assert link.score == pytest.approx(0.95) and link.fit is TermFit.EXACT
    assert (link.review_state, link.reviewed_by) == (ReviewState.APPROVED, Decider.RULE)
    assert link.reasons == [{"code": WORD_EQUALS_SYMBOL, "word": "CXCR3"}]
    record = session.get(TermRecord, ("opentargets", "ENSG00000186810"))
    assert record is not None and record.payload["approvedSymbol"] == "CXCR3"
    # What is judged: the claim without its indication, the word, the symbol and the name.
    [(step, intro, [item])] = backend.calls
    assert step == TARGET_MATCH
    assert "Intervention: Anti-CXCR3 antibody." in intro and "Indication:" not in intro
    assert item == (
        "Word in the intervention's name: CXCR3\n"
        "Candidate gene (opentargets ENSG00000186810): CXCR3\n"
        "Gene name: C-X-C motif chemokine receptor 3"
    )
    [log] = target_logs(session)
    assert log.input_ref == f"claim:{claim.id}:target:opentargets:ENSG00000186810"
    assert log.options == TARGET_OPTIONS

    # A second run searches the cached words again and decides nothing anew.
    again = targets_run(session, claim, genes, backend)
    assert again.added == [] and again.scored == [] and len(backend.calls) == 1
    assert genes.fetched == ["ENSG00000186810"]


def test_abbreviation_that_is_also_a_genes_synonym_is_rejected_by_rule(session: Session):
    """Scenarios: Abbreviation that is also a gene's symbol, Word equal to a synonym of
    a gene's symbol"""
    claim = gene_claim(session, "Transcranial magnetic stimulation", "TMS")
    backend = Reader({"TYMS": ("something_else", 0.97)})

    targets_run(session, claim, Genes({"TMS": [TYMS]}), backend)

    [link] = links(session, claim).values()
    assert (link.score, link.fit) == (0.0, None)
    assert (link.review_state, link.reviewed_by) == (ReviewState.REJECTED, Decider.RULE)
    assert link.reasons == [
        {"code": WORD_EQUALS_SYNONYM, "word": "TMS", "sources": ["HGNC", "NCBI_entrez"]}
    ]
    # A rejected gene's record is asked for once, to show its name, and not kept twice.
    assert session.get(TermRecord, ("opentargets", TYMS.identifier)) is not None


def test_allele_named_in_the_intervention_gives_the_gene_as_the_candidate(session: Session):
    """Scenario: Allele named in the intervention"""
    claim = gene_claim(session, "APOE4-to-APOE3 base editing")
    genes = Genes({"APOE4": [APOE]})

    targets_run(session, claim, genes, Reader({"APOE": ("acts_on_or_made_from", 0.9)}))

    assert genes.searched == ["APOE4"]
    [link] = links(session, claim).values()
    assert (link.external_id, link.label) == (APOE.identifier, "APOE")
    assert link.reasons == [
        {"code": WORD_EQUALS_SYNONYM, "word": "APOE4", "sources": ["NCBI_entrez"]}
    ]


def test_four_gene_like_words_keep_three_and_symbols_come_first(session: Session):
    """Scenario: Name with four gene-like words"""
    claim = gene_claim(session, "TMS with APOE4 and CXCR3 and GFAP")
    gfap = NamedTarget("ENSG00000131095", "GFAP", "glial fibrillary acidic protein", "symbol")
    genes = Genes({"TMS": [TYMS], "APOE4": [APOE], "CXCR3": [CXCR3], "GFAP": [gfap]})
    backend = Reader(
        {
            "CXCR3": ("acts_on_or_made_from", 0.9),
            "GFAP": ("acts_on_or_made_from", 0.9),
            "TYMS": ("something_else", 0.9),
        }
    )

    run = targets_run(session, claim, genes, backend)

    assert run.gathered == 3
    assert [term.label for term in run.added] == ["CXCR3", "GFAP", "TYMS"]
    assert len(target_logs(session)) == 3


def test_two_candidate_genes_get_two_log_records_and_a_failure_leaves_one_unscored(
    session: Session,
):
    """Scenario: Two candidate genes for one claim"""
    claim = gene_claim(session, "Anti-CXCR3 antibody", "TMS")
    genes = Genes({"CXCR3": [CXCR3], "TMS": [TYMS]})
    backend = Reader({"CXCR3": ("acts_on_or_made_from", 0.95), "TYMS": None})

    run = targets_run(session, claim, genes, backend)

    logs = target_logs(session)
    assert [log.input_ref for log in logs] == [
        f"claim:{claim.id}:target:opentargets:{CXCR3.identifier}",
        f"claim:{claim.id}:target:opentargets:{TYMS.identifier}",
    ]
    assert logs[0].error is None and logs[1].error
    assert [term.label for term in run.unscored] == ["TYMS"]
    found = links(session, claim)
    assert found["TYMS"].score is None and found["TYMS"].review_state is ReviewState.PENDING
    assert found["CXCR3"].review_state is ReviewState.APPROVED

    backend.by_label["TYMS"] = ("something_else", 0.9)
    again = targets_run(session, claim, genes, backend)

    assert [term.label for term in again.scored] == ["TYMS"]
    assert found["TYMS"].review_state is ReviewState.REJECTED


def test_named_gene_the_operator_rejected_stays_rejected(session: Session):
    claim = gene_claim(session, "Anti-CXCR3 antibody")
    genes = Genes({"CXCR3": [CXCR3]})
    backend = Reader({"CXCR3": ("acts_on_or_made_from", 0.95)})
    targets_run(session, claim, genes, backend)
    [link] = links(session, claim).values()

    decide_item(session, "term", link.id, ReviewState.REJECTED, now=NOW + timedelta(hours=1))
    again = targets_run(session, claim, genes, backend)

    assert again.added == [] and again.scored == []
    assert (link.review_state, link.reviewed_by) == (ReviewState.REJECTED, Decider.HUMAN)
    assert target_logs(session)[0].human_label == "something_else"


def test_second_run_of_named_genes_sends_no_request(session: Session, fake_time, fixture_json):
    claim = gene_claim(session, "Anti-CXCR3 antibody")
    requests: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        name = "search_cxcr3" if b"TargetsNamed" in request.content else "target_cxcr3"
        return httpx.Response(200, json=fixture_json(f"opentargets/{name}.json"))

    genes = OpenTargets(
        session,
        contact_email="ops@thenwhat.test",
        transport=httpx.MockTransport(answer),
        time=fake_time,
    )
    backend = Reader({"CXCR3": ("acts_on_or_made_from", 0.95)})

    def run():
        return link_targets(
            session,
            claim,
            genes=genes,
            backend=backend,
            now=fake_time.now(),
            accept_above=ACCEPT,
            reject_below=REJECT,
        )

    run()

    # One search for the one gene-like word, and the gene's record.
    assert len(requests) == 2
    record = session.get(TermRecord, ("opentargets", "ENSG00000186810"))
    assert record is not None and len(record.payload["functionDescriptions"]) == 3

    fake_time.advance(timedelta(days=2))
    run()

    assert len(requests) == 2


# --- kind and named-gene links in the review queue ---------------------------------


def test_queue_lists_pending_kind_and_target_links_and_the_operator_decides_them(
    session: Session,
):
    claim = stimulator_claim(session)
    add_synonym(session, claim.slug, "Wrist-worn median nerve stimulation device", "TMS")
    backend = Reader({"TYMS": ("acts_on_or_made_from", 0.5)}, kind=("electrical_stimulation", 0.6))
    kind_run(session, claim, backend)
    targets_run(session, claim, Genes({"TMS": [TYMS]}), backend)

    kind_item, gene_item = pending_items(session, claim_slug=claim.slug, kind="term")

    found = links(session, claim)
    kind_link, gene_link = found["Electric Stimulation Therapy"], found["TYMS"]
    assert (kind_item.id, kind_item.score) == (kind_link.id, pytest.approx(0.6))
    assert kind_item.assertion == (
        "subject term 'Electric Stimulation Therapy' (mesh D004599) for the claim's"
        " intervention, chosen as the kind of intervention (fit: kind). Reasons:"
        " kind_chosen (electrical_stimulation); registry_lists_type (DEVICE in 3 trial(s))"
    )
    assert kind_item.reasons == (KIND_CHOSEN, REGISTRY_LISTS_TYPE)
    assert (gene_item.id, gene_item.score) == (gene_link.id, pytest.approx(0.5))
    assert gene_item.assertion == (
        "named gene 'TYMS' (opentargets ENSG00000176890) for the claim's target, read as"
        " what the intervention acts on or is made from (fit: exact). Reasons:"
        " word_equals_synonym ('TMS', given by HGNC, NCBI_entrez)"
    )
    assert gene_item.source_url == "https://platform.opentargets.org/target/ENSG00000176890"

    decide_item(session, "term", kind_link.id, ReviewState.APPROVED, now=NOW)
    decide_item(session, "term", gene_link.id, ReviewState.REJECTED, now=NOW)

    assert (kind_link.review_state, kind_link.reviewed_by) == (ReviewState.APPROVED, Decider.HUMAN)
    assert (gene_link.review_state, gene_link.reviewed_by) == (ReviewState.REJECTED, Decider.HUMAN)
    assert pending_items(session, claim_slug=claim.slug, kind="term") == []
    # Each decision labels the answer of its own step.
    assert kind_logs(session)[0].human_label == "electrical_stimulation"
    assert target_logs(session)[0].human_label == "something_else"
    assert term_logs(session) == []


# --- the command, for every published claim ----------------------------------------


def test_terms_all_leaves_scored_candidates_as_they_are(run, session: Session, knee_claim: Claim):
    record_decision(knee_claim, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    assert run("terms", SLUG).exit_code == 0
    before = {
        label: (term.score, term.fit, term.review_state, term.reviewed_at)
        for label, term in links(session, knee_claim).items()
    }
    assert len(before) == 3

    result = run("terms", "--all")

    assert result.exit_code == 0, result.output
    assert f"{SLUG}: 2 candidate subject term(s), 0 new." in result.output
    assert "Approved by rule: 0 exact, 0 broader. Rejected by rule: 0. Pending review: 0." in (
        result.output
    )
    assert "Kind: not asked." in result.output
    after = {
        label: (term.score, term.fit, term.review_state, term.reviewed_at)
        for label, term in links(session, knee_claim).items()
    }
    assert after == before
    # --missing still means a claim with no candidate at all, which is none now.
    assert "Every published claim has a candidate subject term." in run("terms", "--missing").output


def test_terms_exits_non_zero_when_a_candidate_stayed_without_a_score(
    run, session: Session, knee_claim: Claim, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        "thenwhat.cli.resolve.make_backend",
        lambda s: Reader(
            {"Osteoarthritis, Knee": ("same", 0.95), "Pain": None}, kind=("peptide", 0.9)
        ),
    )

    result = run("terms", SLUG)

    assert result.exit_code == 1
    assert "1 could not be scored and stay without a score." in result.output
    # What was scored is kept.
    assert links(session, knee_claim)["Osteoarthritis, Knee"].review_state is ReviewState.APPROVED


def test_terms_reports_a_name_whose_entry_term_could_not_be_resolved(
    run, session: Session, knee_claim: Claim, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        "thenwhat.cli.terms.make_vocabulary",
        lambda s: Vocabulary(
            {"D010455": "Compounds of AMINO ACIDS joined by peptide bonds."},
            unresolved={"ex-1": ["EX-1"]},
        ),
    )

    result = run("terms", SLUG)

    assert result.exit_code == 0, result.output
    assert "'EX-1' equals an entry term whose record the vocabulary did not give." in result.output


def test_terms_help_names_the_three_runs_and_all(run):
    result = run("terms", "--help")

    assert result.exit_code == 0
    for words in (
        "Subject terms",
        "Intervention kind",
        "Named genes",
        "Drug record",
        "--all",
        "--missing",
    ):
        assert words in result.output


# --- the drug source's record of the intervention ----------------------------------

TIRZEPATIDE = {"id": "CHEMBL4297839", "name": "TIRZEPATIDE", "drugType": "Protein"}
SEMAGLUTIDE = {"id": "CHEMBL2108724", "name": "SEMAGLUTIDE", "drugType": "Protein"}


def test_drug_whose_own_name_equals_the_interventions_is_linked_by_rule_without_a_score(
    session: Session,
):
    claim = new_claim(session, slug="obesity-ex7", intervention="Tirzepatide")
    drugs = Drugs({"tirzepatide": TIRZEPATIDE})

    run = link_drug(session, claim, drugs=drugs, now=NOW)

    assert run.added and run.link is not None and run.several == ()
    [link] = links(session, claim).values()
    assert (link.role, link.source_name, link.external_id, link.label) == (
        TermRole.DRUG,
        "opentargets",
        "CHEMBL4297839",
        "TIRZEPATIDE",
    )
    assert (link.score, link.fit) == (None, TermFit.EXACT)
    assert (link.review_state, link.reviewed_by) == (ReviewState.APPROVED, Decider.RULE)
    assert link.reasons == [{"code": DRUG_NAME_EQUALS_NAME, "name": "Tirzepatide"}]
    record = session.get(TermRecord, ("opentargets", "CHEMBL4297839"))
    assert record is not None and record.payload["name"] == "TIRZEPATIDE"
    assert record.url == "https://platform.opentargets.org/drug/CHEMBL4297839"

    # A second run keeps the link and the record as they are.
    again = link_drug(session, claim, drugs=drugs, now=NOW + timedelta(days=1))
    assert again.link is link and not again.added
    assert drugs.fetched == ["CHEMBL4297839"]


def test_drug_found_under_another_of_the_interventions_names(session: Session):
    claim = new_claim(session, slug="obesity-ex8", intervention="LY3298176")
    add_synonym(session, claim.slug, "LY3298176", "tirzepatide")

    run = link_drug(session, claim, drugs=Drugs({"tirzepatide": TIRZEPATIDE}), now=NOW)

    assert run.link is not None
    assert run.link.reasons == [{"code": DRUG_NAME_EQUALS_NAME, "name": "tirzepatide"}]


@pytest.mark.parametrize(
    "regimen", ["EX-1 plus EX-2", "EX-1/EX-2", "EX-1 plus EX-2, with or without EX-3"]
)
def test_combination_component_is_not_the_interventions_background_card(
    session: Session, regimen: str
):
    """A confidently misread component still cannot describe the whole regimen."""
    claim = new_claim(session, intervention=regimen)
    add_synonym(session, claim.slug, regimen, "EX-1")
    component = ("C100001", "EX-1")
    approve_trials(session, claim, [trial("NCT00000001", interventions=(component,))])
    backend = Reader({"EX-1": ("same", 1.0)})

    link_terms(
        session,
        claim,
        vocabulary=Vocabulary(labels={"ex-1": [LabelledTerm(*component)]}),
        backend=backend,
        now=NOW,
        accept_above=ACCEPT,
        reject_below=REJECT,
    )

    assert not any(t.review_state is ReviewState.APPROVED for t in links(session, claim).values())
    assert backend.calls == [], "An explicit component needs no paid classification."


def test_whole_combination_alias_remains_a_background_candidate(session: Session):
    claim = new_claim(session, intervention="EX-1 plus EX-2")
    add_synonym(session, claim.slug, "EX-1 plus EX-2", "Dualex")
    backend = Reader({"Dualex": ("same", 0.98)})
    link_terms(
        session,
        claim,
        vocabulary=Vocabulary(labels={"dualex": [LabelledTerm("C100002", "Dualex")]}),
        backend=backend,
        now=NOW,
        accept_above=ACCEPT,
        reject_below=REJECT,
    )
    [link] = links(session, claim).values()
    assert link.label == "Dualex" and link.review_state is ReviewState.APPROVED


def test_only_one_listed_combination_component_still_gets_no_drug_card(session: Session):
    claim = new_claim(session, intervention="EX-1 plus semaglutide")
    add_synonym(session, claim.slug, "EX-1 plus semaglutide", "semaglutide")
    drugs = Drugs({"semaglutide": SEMAGLUTIDE})

    run = link_drug(session, claim, drugs=drugs, now=NOW)

    assert run.link is None and not run.added
    assert drugs.searched == ["EX-1 plus semaglutide"]


def test_procedure_no_drug_is_named_after_gets_no_drug_link(session: Session):
    """Scenario: Procedure"""
    claim = new_claim(session, slug="ovary-ex9", intervention="Opportunistic salpingectomy")
    drugs = Drugs({"tirzepatide": TIRZEPATIDE})

    run = link_drug(session, claim, drugs=drugs, now=NOW)

    assert run.link is None and run.several == ()
    assert links(session, claim) == {} and drugs.fetched == []


def test_class_of_drugs_whose_other_names_are_its_members_gets_no_drug_link(session: Session):
    claim = new_claim(session, slug="ageing-ex10", intervention="GLP-1 receptor agonists")
    for member in ("semaglutide", "tirzepatide"):
        add_synonym(session, claim.slug, "GLP-1 receptor agonists", member)
    drugs = Drugs({"tirzepatide": TIRZEPATIDE, "semaglutide": SEMAGLUTIDE})

    run = link_drug(session, claim, drugs=drugs, now=NOW)

    assert run.link is None and run.several == ("SEMAGLUTIDE", "TIRZEPATIDE")
    assert links(session, claim) == {}


def test_drug_link_the_operator_rejected_stays_rejected(session: Session):
    claim = new_claim(session, slug="obesity-ex11", intervention="Tirzepatide")
    drugs = Drugs({"tirzepatide": TIRZEPATIDE})
    first = link_drug(session, claim, drugs=drugs, now=NOW)
    assert first.link is not None

    decide_item(session, "term", first.link.id, ReviewState.REJECTED, now=NOW + timedelta(hours=1))
    again = link_drug(session, claim, drugs=drugs, now=NOW + timedelta(days=1))

    assert again.link is first.link and not again.added
    assert (first.link.review_state, first.link.reviewed_by) == (
        ReviewState.REJECTED,
        Decider.HUMAN,
    )
    assert len(links(session, claim)) == 1


def test_terms_names_the_drug_record_it_tied_or_why_it_tied_none(
    run, session: Session, knee_claim: Claim, monkeypatch: pytest.MonkeyPatch
):
    assert "Drug record: none found by name." in run("terms", SLUG).output

    monkeypatch.setattr(
        "thenwhat.cli.terms.make_drugs", lambda s: Drugs({"ex-1": TIRZEPATIDE | {"name": "EX-1"}})
    )
    result = run("terms", SLUG)

    assert result.exit_code == 0, result.output
    assert "Drug record: EX-1 (CHEMBL4297839), found by its name, new, approved." in result.output
