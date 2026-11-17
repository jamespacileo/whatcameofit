"""Shared pieces for the tests of a claim's preparation: a claim, the sources its steps
ask, faked, and a run of the steps on the test session."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from backfill_support import same_session
from registry_support import REGISTRY
from thenwhat.claims.entry import add_article, add_claim, find_claim
from thenwhat.claimsteps.run import StepRun, claim_steps, run_claim_steps
from thenwhat.claimsteps.step import ClaimSources, ClaimStep, Research
from thenwhat.config import Settings
from thenwhat.db.models import Claim, LinkLead, WorkEntry
from thenwhat.decide.core import BackendAnswer
from thenwhat.decide.steps import INTERVENTION_KIND, NONE_OF_THESE
from thenwhat.domain import OutletKind, ReadOutcome
from thenwhat.sources.base import SourceRecord, SourceUnavailable, UnsearchableTerm
from thenwhat.sources.clinicaltrials import NotSent, Searched

NOW = datetime(2026, 11, 20, 9, 0, tzinfo=UTC)
SLUG = "ex1-tooth-agenesis"
DOWN = "did not answer after 4 attempts."


def new_claim(session: Session, slug: str = SLUG, *urls: str, intervention: str = "") -> Claim:
    """A claim awaiting review with an article for each address given."""
    claim = add_claim(
        session,
        slug=slug,
        headline="Antibody regrows teeth in mice",
        vertical="mouth-and-teeth",
        intervention=intervention or f"EX-1 antibody {slug}",
        indication="tooth agenesis",
        summary="An antibody restored missing teeth in mice.",
    )
    for number, url in enumerate(urls, 1):
        add_article(
            session,
            slug,
            url=url,
            outlet="Example News",
            title=f"Report {number}",
            published_date=date(2018, 3, number),
        )
    return claim


def drafted_by_a_read(session: Session, slug: str) -> None:
    """Mark the claim as the new claim of a link lead's read."""
    claim = find_claim(session, slug)
    assert claim is not None
    session.add(
        LinkLead(
            url=f"https://news.example.org/{slug}",
            url_key=f"news.example.org/{slug}",
            outlet="news.example.org",
            outlet_kind=OutletKind.GENERAL_NEWS,
            title="words a person wrote when sharing the link",
            first_shared_at=NOW,
            read_outcome=ReadOutcome.NEW_CLAIM,
            claim_id=claim.id,
        )
    )
    session.flush()


def trial(nct_id: str, status: str = "RECRUITING") -> SourceRecord:
    payload = {
        "protocolSection": {
            "identificationModule": {"nctId": nct_id, "briefTitle": "EX-1 in tooth agenesis"},
            "statusModule": {"overallStatus": status, "startDateStruct": {"date": "2024-01"}},
            "conditionsModule": {"conditions": ["Tooth agenesis"]},
        }
    }
    return SourceRecord(
        REGISTRY, nct_id, f"https://clinicaltrials.gov/study/{nct_id}", payload, NOW
    )


def failing(source: str) -> SourceUnavailable:
    return SourceUnavailable(f"{source} {DOWN}")


@dataclass
class Registry:
    """The trial registry, which holds `trials` under every name. It reports `reported`
    records for a term it is given a count for, and fails when `down`."""

    trials: list[SourceRecord] = field(default_factory=list)
    reported: dict[str, int] = field(default_factory=dict)
    cut: set[str] = field(default_factory=set)
    refused: dict[str, str] = field(default_factory=dict)
    down: bool = False
    asked: list[str] = field(default_factory=list)

    def _ask(self, what: str) -> None:
        if self.down:
            raise failing(REGISTRY)
        self.asked.append(what)

    def name_search(self, intervention: str, condition: str | None = None) -> Searched:
        term = intervention
        self._ask(term)
        if term in self.refused:
            raise UnsearchableTerm(term, self.refused[term], REGISTRY)
        if term in self.cut:
            return Searched(REGISTRY, term, [], self.reported[term], condition, cut=True)
        return Searched(
            REGISTRY, term, list(self.trials), self.reported.get(term, len(self.trials))
        )

    def phrase_search(self, phrase: str, condition: str | None) -> Searched | NotSent:
        return self.name_search(phrase, condition)

    def fetch_trial(self, nct_id: str) -> SourceRecord | None:
        self._ask(nct_id)
        return next((record for record in self.trials if record.external_id == nct_id), None)

    def work(self, doi: str) -> SourceRecord | None:
        return None


class Nothing:
    """Europe PMC, the literature, the notices and ROR, with nothing to say. With `down`,
    the literature fails."""

    name = "openalex"

    def __init__(self, down: bool = False) -> None:
        self.down = down

    def trial_numbers(self, *, doi: str | None = None, pubmed_id: str | None = None) -> list[str]:
        return []

    def organisations(self, name: str) -> list[SourceRecord]:
        return []

    def search_papers(self, terms: list[str], condition: str, limit: int = 20) -> list:
        if self.down:
            raise failing("openalex")
        return []

    def search_papers_at(self, terms: list[str], organisation: str, reported: Any = None) -> list:
        return self.search_papers(terms, "")

    def paper(self, external_id: str) -> SourceRecord | None:
        return None


class Index:
    """The literature index and the notices a fetch reads, with nothing to say."""

    def paper(self, doi: str) -> SourceRecord | None:
        return None

    def paper_by_pubmed_id(self, pubmed_id: str) -> SourceRecord | None:
        return None

    def citing_papers(self, paper: SourceRecord) -> list[SourceRecord]:
        return []

    def notices(self, doi: str) -> list:
        return []


class Substances:
    """The registry of substances, which lists no name, or fails when `down`."""

    name = "gsrs"

    def __init__(self, down: bool = False) -> None:
        self.down = down

    def substances_named(self, name: str) -> list[SourceRecord]:
        if self.down:
            raise failing(self.name)
        return []


class Vocabulary:
    """MeSH, which labels no term, or fails when `down`."""

    name = "mesh"

    def __init__(self, down: bool = False) -> None:
        self.down = down

    def term(self, identifier: str, *, force: bool = False) -> SourceRecord | None:
        return None

    def terms_labelled(self, name: str) -> list:
        if self.down:
            raise failing(self.name)
        return []

    def unresolved_entry_terms(self, name: str) -> list[str]:
        return []


class Targets:
    """Open Targets for genes and drugs, which knows none, or fails for drugs when
    `drugs_down`."""

    name = "opentargets"

    def __init__(self, drugs_down: bool = False) -> None:
        self.drugs_down = drugs_down

    def targets_named(self, word: str) -> list:
        return []

    def target(self, identifier: str, *, force: bool = False) -> SourceRecord | None:
        return None

    def drugs_named(self, name: str) -> list[SourceRecord]:
        if self.drugs_down:
            raise failing(self.name)
        return []

    def drug(self, identifier: str, *, force: bool = False) -> SourceRecord | None:
        return None


class Backend:
    """A decision backend that takes the first option, sure at 0.85, and never names a
    kind for an intervention. It counts its calls."""

    name = "fake"

    def __init__(self) -> None:
        self.calls = 0

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        self.calls += 1
        choice = NONE_OF_THESE if step == INTERVENTION_KIND else options[0]
        rest = 0.15 / (len(options) - 1)
        return BackendAnswer(choice, {o: 0.85 if o == choice else rest for o in options})


def unreadable(session: Session) -> Any:
    raise AssertionError("No model is asked to read in this test.")


def unchecked(session: Session) -> Any:
    raise AssertionError("No statement is checked in this test.")


@dataclass
class Sources:
    """The fakes behind `ClaimSources`, each changeable by a test."""

    registry: Registry = field(default_factory=Registry)
    substances: Substances = field(default_factory=Substances)
    literature: Nothing = field(default_factory=Nothing)
    papers: Nothing | None = None
    vocabulary: Vocabulary = field(default_factory=Vocabulary)
    targets: Targets = field(default_factory=Targets)
    backend: Backend = field(default_factory=Backend)
    make_llm: Any = unreadable
    make_checker: Any = None
    retriever: Any = None
    open_session: Any = None

    def claim_sources(self) -> ClaimSources:
        return ClaimSources(
            make_backend=lambda session: self.backend,
            make_substances=lambda session: self.substances,
            make_brands=lambda session: None,
            make_registries=lambda session: (self.registry, self.registry),
            make_research=lambda session: Research(
                papers=self.papers,
                numbers=self.literature,
                registry=self.registry,
                organisations=self.literature,
            ),
            make_evidence=lambda session: (self.registry, Index(), Index()),
            make_llm=self.make_llm,
            make_checker=self.make_checker or unchecked,
            make_vocabulary=lambda session: self.vocabulary,
            make_genes=lambda session: self.targets,
            make_drugs=lambda session: self.targets,
            retriever=self.retriever,
            open_session=self.open_session,
        )


def settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "database_url": "postgresql+psycopg://unused/unused",
        "match_accept_above": 0.8,
        "match_reject_below": 0.05,
        "approve_drafts_by_rule": True,
    }
    return Settings(**(values | overrides))


def prepare(
    session: Session,
    sources: Sources,
    *,
    at: datetime = NOW,
    names: tuple[str, ...] | None = None,
    **overrides: Any,
) -> list[StepRun]:
    """One run of the claim steps over every claim awaiting review and every approved
    claim not archived, at the time given, on the test session."""
    steps = claim_steps(settings(**overrides), clock=lambda: at)
    if names is not None:
        steps = [step for step in steps if step.name in names]
    if sources.open_session is None:
        sources.open_session = same_session(session)
    return run_claim_steps(
        same_session(session),
        steps,
        sources.claim_sources,
        attempt_limit=3,
        put_off_span=timedelta(days=30),
        now=lambda: at,
    )


def entry(session: Session, step: str, claim: Claim) -> WorkEntry:
    """The claim's entry for the step, which a test expects to exist."""
    found = entry_or_none(session, step, claim)
    assert found is not None, f"{claim.slug} has no entry for {step}"
    return found


def entry_or_none(session: Session, step: str, claim: Claim) -> WorkEntry | None:
    return (
        session.query(WorkEntry)
        .filter(
            WorkEntry.record_kind == "claim",
            WorkEntry.record_id == claim.id,
            WorkEntry.step == step,
        )
        .one_or_none()
    )


def by_step(runs: list[StepRun]) -> dict[str, StepRun]:
    return {run.step.name: run for run in runs}


def step_of(runs: list[StepRun], name: str) -> ClaimStep:
    return by_step(runs)[name].step
