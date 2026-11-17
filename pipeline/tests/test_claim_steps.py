"""A claim's preparation as steps of the work ledger, at the level of openspec's scenarios
(change one-work-runner): entity-resolution ("A registry search leaves a record", "A
lookup that failed is not a finished search"), claim-extraction ("Preparing many claims",
"What a decision waits for", "Unfinished parts of a published claim are completed"),
work-ledger ("A step can depend on another step") and lead-reading ("Records a page names
are looked up apart from the join"). The sources are faked; the database is real."""

from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from claim_support import (
    NOW,
    SLUG,
    Nothing,
    Registry,
    Sources,
    Substances,
    Targets,
    Vocabulary,
    by_step,
    drafted_by_a_read,
    entry,
    entry_or_none,
    new_claim,
    prepare,
    settings,
    trial,
)
from test_cli_extract import DRAFT, Checks, FakeRetriever
from test_record_readings import ANSWER, OUTCOMES, Scripted, llm, reads, study_with
from thenwhat.claims.corrections import rename_intervention
from thenwhat.claims.entities import add_entity
from thenwhat.claimsteps.inputs import notice_changes
from thenwhat.claimsteps.run import claim_steps, never_searched
from thenwhat.claimsteps.step import named
from thenwhat.db.models import (
    Claim,
    DecisionLog,
    Entity,
    EntityMatch,
    EntitySubstance,
    RegistrySearch,
    SourceArticle,
)
from thenwhat.decide.steps import INTERVENTION_KIND
from thenwhat.domain import ClaimStatus, Decider, EntityType, ReviewState, WorkOutcome
from thenwhat.extract.retrieve import NotNow, NotServed, PasteNeeded, Retrieved
from thenwhat.llm.errors import ModelCannotBeAsked
from thenwhat.measure.events import RunEnd
from thenwhat.review.decisions import record_decision
from thenwhat.sources.base import SourceCannotBeAsked, SourceRecord
from thenwhat.statements.service import StatementChecker
from thenwhat.work.ledger import due_records

SUBSTANCE, TRIALS, PAPERS = "claim_substance", "claim_trials", "claim_papers"
SEARCH = (SUBSTANCE, TRIALS)
LATER = NOW + timedelta(hours=2)


def searches(session: Session, claim: Claim) -> list[RegistrySearch]:
    return list(
        session.scalars(
            select(RegistrySearch)
            .where(RegistrySearch.claim_id == claim.id)
            .order_by(RegistrySearch.id)
        )
    )


def name_of(session: Session, claim: Claim) -> str:
    return session.scalars(select(Entity.name).where(Entity.claim_id == claim.id)).one()


def due_ids(session: Session, name: str) -> set[int]:
    [step] = [step for step in claim_steps(settings()) if step.name == name]
    notice_changes(session, claim_steps(settings()))
    return set(session.scalars(due_records(step, 3, now=NOW).with_only_columns(Claim.id)))


# --- A registry search leaves a record -----------------------------------------------------


def test_a_search_that_found_trials_leaves_a_record_replaced_by_the_next(session: Session):
    """Scenario: A search that found trials"""
    claim = new_claim(session)
    trials = [trial(f"NCT{number:08d}") for number in range(37)]

    prepare(session, Sources(Registry(trials)), names=SEARCH)

    [record] = searches(session, claim)
    assert (record.term, record.ran_at, record.reported, record.kept, record.cut) == (
        name_of(session, claim),
        NOW,
        37,
        37,
        False,
    )

    # The search of a later run replaces it.
    record_decision(claim, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    claim.registry_search_due_at = NOW
    prepare(session, Sources(Registry(trials[:2])), names=SEARCH, at=LATER)

    [again] = searches(session, claim)
    assert (again.ran_at, again.reported, again.kept) == (LATER, 2, 2)


def test_a_search_that_found_none_leaves_a_record_of_none(session: Session):
    """Scenario: A search that found none"""
    claim = new_claim(session)

    prepare(session, Sources(), names=SEARCH)

    [record] = searches(session, claim)
    assert (record.term, record.reported, record.kept) == (name_of(session, claim), 0, 0)


def test_a_limit_that_left_records_out_is_recorded(session: Session):
    """Scenario: A limit left records out"""
    claim = new_claim(session)
    name = name_of(session, claim)
    registry = Registry(reported={name: 450}, cut={name})

    prepare(session, Sources(registry), names=SEARCH)

    [record] = searches(session, claim)
    assert (record.term, record.reported, record.kept, record.cut) == (name, 450, 0, True)


def test_a_term_that_was_not_sent_leaves_a_record_of_why(session: Session):
    """Scenario: A term that is not sent"""
    claim = new_claim(session)
    name = name_of(session, claim)

    prepare(session, Sources(Registry(refused={name: "Too complicated query"})), names=SEARCH)

    [record] = searches(session, claim)
    assert (record.term, record.reported, record.not_sent_reason) == (
        name,
        None,
        "Too complicated query",
    )
    assert entry(session, TRIALS, claim).outcome is WorkOutcome.DONE


# --- A lookup that failed is not a finished search -------------------------------------------


def test_a_substance_registry_that_is_down_leaves_the_search_unfinished_and_undecided(
    session: Session,
):
    """Scenarios: The registry of substances is down; The substance lookup did not finish"""
    claim = new_claim(session)
    drafted_by_a_read(session, SLUG)
    sources = Sources(substances=Substances(down=True))

    prepare(session, sources)

    looked_up = entry(session, SUBSTANCE, claim)
    assert looked_up is not None
    assert (looked_up.outcome, looked_up.reason) == (WorkOutcome.LATER, "source_failed")
    # Nothing was searched or decided on a lookup that did not run.
    assert entry_or_none(session, TRIALS, claim) is None and searches(session, claim) == []
    assert claim.review_state is ReviewState.PENDING

    sources.substances.down = False
    prepare(session, sources, at=LATER)

    assert claim.review_state is ReviewState.APPROVED


def test_a_substance_the_registry_does_not_know_is_a_finished_lookup(session: Session):
    """Scenario: The substance is not known"""
    claim = new_claim(session)

    prepare(session, Sources(), names=(SUBSTANCE,))

    assert entry(session, SUBSTANCE, claim).outcome is WorkOutcome.DONE
    assert session.scalars(select(EntitySubstance)).all() == []


def test_papers_that_could_not_be_searched_leave_the_registry_search_finished(
    session: Session,
):
    """Scenario: Papers could not be searched"""
    claim = new_claim(session)
    sources = Sources(papers=Nothing(down=True))

    prepare(session, sources, names=(*SEARCH, PAPERS))

    assert entry(session, TRIALS, claim).outcome is WorkOutcome.DONE
    assert entry(session, PAPERS, claim).outcome is WorkOutcome.LATER
    searched = list(sources.registry.asked)

    sources.papers = Nothing()
    prepare(session, sources, names=(*SEARCH, PAPERS), at=LATER)

    assert entry(session, PAPERS, claim).outcome is WorkOutcome.DONE
    # The search of the registry was not made again.
    assert sources.registry.asked == searched


# --- A claim never searched is told apart from one searched ----------------------------------


def test_a_claim_never_searched_is_told_apart_from_one_searched_with_no_result(
    session: Session,
):
    """Scenarios: A claim with no search record; A claim searched with no result"""
    searched = new_claim(session, "searched-one")
    prepare(session, Sources(), names=SEARCH)
    never = new_claim(session, "never-searched")
    for claim in (searched, never):
        record_decision(claim, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)

    assert never_searched(session, named([searched.id, never.id])) == ["never-searched"]
    # Both hold the status given when no trial is found; only one was searched for it.
    assert never.current_status is searched.current_status is ClaimStatus.NO_TRIAL_FOUND
    assert never.id in due_ids(session, SUBSTANCE)


# --- What a decision waits for ----------------------------------------------------------------


def test_a_claim_whose_terms_failed_is_decided_and_its_terms_are_due_next_run(
    session: Session,
):
    """Scenario: Terms failed and the claim is decided"""
    claim = new_claim(session)
    drafted_by_a_read(session, SLUG)
    sources = Sources(vocabulary=Vocabulary(down=True))

    prepare(session, sources)

    assert claim.review_state is ReviewState.APPROVED
    assert entry(session, "claim_terms", claim).outcome is WorkOutcome.LATER

    sources.vocabulary.down = False
    prepare(session, sources, at=LATER)

    assert entry(session, "claim_terms", claim).outcome is WorkOutcome.DONE


def readable_trial(fixture_json, nct_id: str = "NCT02586935") -> SourceRecord:
    study = study_with(fixture_json, OUTCOMES, trial_id=nct_id)
    return SourceRecord(
        "clinicaltrials.gov", nct_id, f"https://clinicaltrials.gov/study/{nct_id}", study, NOW
    )


def test_a_claim_whose_reading_failed_is_decided_and_the_reading_is_due_next_run(
    session: Session, fixture_json
):
    """Scenario: Readings failed"""
    claim = new_claim(session)
    drafted_by_a_read(session, SLUG)

    def no_model(session: Session):
        raise RuntimeError("the model did not answer")

    prepare(session, Sources(Registry([readable_trial(fixture_json)]), make_llm=no_model))

    assert claim.review_state is ReviewState.APPROVED
    assert entry(session, "claim_readings", claim).outcome is WorkOutcome.FAILED
    assert claim.id in due_ids(session, "claim_readings")


# --- Preparing many claims --------------------------------------------------------------------


def test_an_article_that_cannot_be_read_is_reported_and_the_claim_is_still_searched(
    session: Session,
):
    """Scenario: Article that cannot be read"""
    claim = new_claim(session, SLUG, "https://news.example.org/a")
    drafted_by_a_read(session, SLUG)
    sources = Sources(retriever=FakeRetriever(PasteNeeded("The page reader got too little text.")))

    runs = by_step(prepare(session, sources))

    assert runs["claim_articles"].report.needs_fix == 1
    assert entry(session, "claim_articles", claim).reason == "article_unreadable"
    assert entry(session, TRIALS, claim).outcome is WorkOutcome.DONE
    assert searches(session, claim) != []
    # A draft is not decided before what its articles say is read.
    assert claim.review_state is ReviewState.PENDING


def test_a_run_stopped_after_the_search_fetches_without_searching_again(session: Session):
    """Scenario: A run stopped half way through a claim"""
    claim = new_claim(session)
    registry = Registry([trial("NCT00000001")])

    prepare(session, Sources(registry), names=SEARCH)
    searched = list(registry.asked)
    prepare(session, Sources(registry))

    # The fetch's request for the approved trial, and no search.
    assert registry.asked == [*searched, "NCT00000001"]
    assert entry(session, "claim_fetch", claim).outcome is WorkOutcome.DONE


def test_a_registry_that_cannot_be_asked_leaves_its_claims_due_and_other_steps_run(
    session: Session,
):
    """Scenario: A source is paused"""
    claims = [new_claim(session, slug) for slug in ("first-one", "second-one")]

    runs = by_step(prepare(session, Sources(Registry(down=True))))

    assert (runs[TRIALS].report.later, runs[TRIALS].report.done) == (2, 0)
    assert all(entry(session, TRIALS, claim).reason == "source_failed" for claim in claims)
    # Steps that need other sources still ran.
    assert runs[SUBSTANCE].report.done == runs["claim_terms"].report.done == 2


# --- Unfinished parts of a published claim are completed ------------------------------------


def test_a_published_claim_with_no_terms_has_them_proposed_by_the_next_run(session: Session):
    """Scenario: A published claim with no terms"""
    claim = new_claim(session)
    record_decision(claim, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    sources = Sources(vocabulary=Vocabulary(down=True))
    prepare(session, sources)
    assert entry(session, "claim_terms", claim).outcome is WorkOutcome.LATER

    sources.vocabulary = Vocabulary()
    prepare(session, sources, at=LATER)

    assert entry(session, "claim_terms", claim).outcome is WorkOutcome.DONE


def test_a_trial_approved_after_publishing_is_read_by_the_next_run(session: Session, fixture_json):
    """Scenario: A trial approved after the claim was published"""
    claim = new_claim(session)
    record_decision(claim, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    sources = Sources(Registry([readable_trial(fixture_json)]))
    # Not approved by rule: the trial waits for review.
    prepare(session, sources, match_accept_above=0.0)
    [match] = session.scalars(select(EntityMatch))
    assert match.review_state is ReviewState.PENDING and reads(session) == []

    record_decision(match, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    sources.make_llm = lambda at: llm(at, Scripted(ANSWER))
    prepare(session, sources, at=LATER)

    assert [read.trial_id for read in reads(session)] == ["NCT02586935"]


# --- A step can depend on another step ----------------------------------------------------------


def test_a_claim_renamed_after_it_was_searched_and_decided_is_searched_first(session: Session):
    """Scenario: The earlier step is due again"""
    claim = new_claim(session)
    drafted_by_a_read(session, SLUG)
    prepare(session, Sources(Registry([trial("NCT00000001")])))
    assert claim.review_state is ReviewState.APPROVED

    rename_intervention(
        session, SLUG, name_of(session, claim), "EX-2 antibody", by=Decider.HUMAN, now=NOW
    )

    assert claim.id in due_ids(session, SUBSTANCE)
    for later in (TRIALS, PAPERS, "claim_fetch"):
        assert claim.id not in due_ids(session, later)


# --- What each step does, finished and put off ----------------------------------------------


def test_the_articles_step_reads_an_unread_article_and_puts_off_a_held_outlet(
    session: Session, monkeypatch: pytest.MonkeyPatch
):
    """Task 7.3: claim_articles, finished and put off"""
    from decimal import Decimal

    from pydantic_ai.messages import ModelResponse, ToolCallPart
    from pydantic_ai.models.function import FunctionModel

    from thenwhat.llm.client import Llm, LlmSettings

    def respond(messages, info) -> ModelResponse:
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, DRAFT)])

    model = LlmSettings("test:scripted", Decimal("10"), Decimal("3"), Decimal("15"))
    read = new_claim(session, "read-one", "https://news.example.org/read")
    held = new_claim(session, "held-one", "https://held.example.org/held")

    class Web:
        def retrieve(self, url: str) -> Retrieved:
            if "held" in url:
                raise NotNow(url, "the outlet is stopped", 3600)
            return Retrieved("Synthetic article: an antibody called EX-1 regrew teeth.")

    sources = Sources(
        retriever=Web(),
        make_llm=lambda at: Llm(at, model, model=FunctionModel(respond), now=lambda: NOW),
        make_checker=lambda at: StatementChecker(Checks()),
    )

    prepare(session, sources, names=("claim_articles",))

    assert entry(session, "claim_articles", read).outcome is WorkOutcome.DONE
    [article] = session.scalars(select(SourceArticle).where(SourceArticle.claim_id == read.id))
    assert article.content_hash is not None
    put_off = entry(session, "claim_articles", held)
    assert (put_off.outcome, put_off.reason) == (WorkOutcome.LATER, "outlet_held")


def test_the_fetch_step_records_events_and_is_put_off_when_the_registry_fails(
    session: Session,
):
    """Task 7.3: claim_fetch, finished and put off"""
    fetched, failed = new_claim(session, "fetched-one"), new_claim(session, "failed-one")
    registry = Registry([trial("NCT00000001")])
    prepare(session, Sources(registry), names=SEARCH)

    registry.down = True
    prepare(session, Sources(registry), names=(*SEARCH, "claim_fetch"))
    assert entry(session, "claim_fetch", fetched).outcome is WorkOutcome.LATER

    registry.down = False
    prepare(session, Sources(registry), names=(*SEARCH, "claim_fetch"), at=LATER)
    assert entry(session, "claim_fetch", failed).outcome is WorkOutcome.DONE
    assert fetched.current_status is not None


def test_the_readings_step_stops_with_the_claim_due_at_the_spend_ceiling(
    session: Session, fixture_json
):
    """Task 7.3: claim_readings, finished and put off"""
    from decimal import Decimal

    claim = new_claim(session)
    sources = Sources(Registry([readable_trial(fixture_json)]))
    sources.make_llm = lambda at: llm(at, Scripted(ANSWER), monthly_budget_usd=Decimal(0))
    runs = by_step(prepare(session, sources))

    assert runs["claim_readings"].report.stopped is not None
    assert entry_or_none(session, "claim_readings", claim) is None

    sources.make_llm = lambda at: llm(at, Scripted(ANSWER))
    prepare(session, sources, at=LATER)

    assert entry(session, "claim_readings", claim).outcome is WorkOutcome.DONE
    assert [read.trial_id for read in reads(session)] == ["NCT02586935"]


def test_the_terms_step_keeps_its_paid_decisions_when_its_last_lookup_fails(session: Session):
    """Task 7.3: claim_terms, put off with what it paid for kept, then finished"""
    claim = new_claim(session)
    sources = Sources(targets=Targets(drugs_down=True))

    prepare(session, sources, names=("claim_terms",))

    assert entry(session, "claim_terms", claim).outcome is WorkOutcome.LATER
    asked = session.scalars(select(DecisionLog).where(DecisionLog.step == INTERVENTION_KIND))
    assert len(asked.all()) == 1
    paid = sources.backend.calls

    sources.targets = Targets()
    prepare(session, sources, names=("claim_terms",), at=LATER)

    assert entry(session, "claim_terms", claim).outcome is WorkOutcome.DONE
    # The kind was not asked for again.
    assert sources.backend.calls == paid


# --- Records a page names are looked up apart from the join -------------------------------------


def test_cli_claim_steps_at_the_ceiling_stop_only_work_that_needs_the_model(
    session, monkeypatch, fixture_json
):
    from decimal import Decimal

    from backfill_support import same_session
    from thenwhat.cli import claim_steps as cli

    claim = new_claim(session)
    drafted_by_a_read(session, claim.slug)
    sources = Sources(Registry([readable_trial(fixture_json)]))
    # Set up approved evidence before the run whose ceiling we test.
    prepare(session, sources, names=SEARCH)
    config = settings(llm_monthly_budget_usd=Decimal(0))
    sources.make_llm = lambda s: llm(s, Scripted(ANSWER), monthly_budget_usd=Decimal(0))
    monkeypatch.setattr(cli, "settings_or_exit", lambda: config)
    monkeypatch.setattr(cli, "claim_sources", sources.claim_sources)
    monkeypatch.setattr(cli, "open_session", same_session(session))
    names = {"claim_fetch", "claim_decide", "claim_readings"}
    steps = [s for s in claim_steps(config, claims=named([claim.id])) if s.name in names]
    for s in steps:
        s.after = ()
    runs = by_step(cli.run_steps(steps))
    assert entry(session, "claim_fetch", claim).outcome == WorkOutcome.DONE
    assert entry(session, "claim_decide", claim).outcome == WorkOutcome.DONE
    report = runs["claim_readings"].report
    assert report.ended is RunEnd.SPEND_CEILING
    assert report.remaining_due == 1
    assert entry_or_none(session, "claim_readings", claim) is None


def test_a_cited_doi_is_due_after_configuring_papers_and_requeueing(session):
    from thenwhat.work.ledger import requeue

    claim = new_claim(session, SLUG, "https://news.example.org/a")
    article = session.scalars(select(SourceArticle)).one()
    article.named_registry_numbers = ["NCT00000009"]
    article.named_dois = ["10.1234/example"]
    registry = Registry([trial("NCT00000009")])
    sources = Sources(registry)
    name = "claim_named_records"
    [first] = prepare(session, sources, names=(name,))
    held = entry(session, name, claim)
    assert (held.outcome, held.reason, held.reason_values) == (
        WorkOutcome.NEEDS_FIX,
        "papers_off",
        {"dois": article.named_dois},
    )
    assert session.scalars(select(EntityMatch.external_id)).all() == ["NCT00000009"]
    asked_before = list(registry.asked)
    calls = []

    class Papers(Nothing):
        def paper(self, external_id):
            calls.append(external_id)
            return None

    sources.papers = Papers()
    assert requeue(session, first.step, reason="papers_off") == [claim.id]
    prepare(session, sources, names=(name,), at=LATER)
    assert entry(session, name, claim).outcome == WorkOutcome.DONE
    [unchanged] = prepare(session, sources, names=(name,), at=LATER)
    assert unchanged.report.processed == 0
    assert calls == article.named_dois and registry.asked == asked_before


def test_a_number_the_page_names_is_looked_up_again_when_the_registry_was_down(
    session: Session,
):
    """Scenario: The registry is down when an article is joined"""
    claim = new_claim(session, SLUG, "https://news.example.org/a")
    [article] = session.scalars(select(SourceArticle).where(SourceArticle.claim_id == claim.id))
    article.named_registry_numbers = ["NCT00000009"]
    registry = Registry([trial("NCT00000009")], down=True)

    prepare(session, Sources(registry), names=("claim_named_records",))

    assert entry(session, "claim_named_records", claim).outcome is WorkOutcome.LATER
    assert article.claim_id == claim.id

    registry.down = False
    prepare(session, Sources(registry), names=("claim_named_records",), at=LATER)

    [match] = session.scalars(select(EntityMatch))
    assert match.external_id == "NCT00000009"


def test_a_registry_that_is_paused_stops_the_search_and_counts_nothing_against_the_claim(
    session: Session,
):
    """Scenario: The model goes away during a read, for a source: a provider that cannot
    be asked stops the run, and the claim is neither put off nor failed (openspec
    work-ledger, "A provider that cannot be asked stops the run")."""
    claim = new_claim(session)
    drafted_by_a_read(session, SLUG)
    sources = Sources(registry=Registry(cannot_be_asked=True))

    runs = prepare(session, sources)

    searched = by_step(runs)[TRIALS].report
    assert searched.stopped is not None and "paused" in searched.stopped
    assert (searched.later, searched.failed) == (0, 0)
    # The claim has no entry for the search: it is simply still due, and is not decided.
    assert entry_or_none(session, TRIALS, claim) is None
    assert claim.review_state is ReviewState.PENDING


def test_an_added_paper_doi_reopens_only_the_paper_lookup_once(session):
    claim = new_claim(session)
    sources = Sources(papers=Nothing())
    calls = []

    def lookup(doi):
        calls.append(doi)
        return None

    sources.registry.work = lookup
    prepare(session, sources, names=(*SEARCH, PAPERS))
    assert entry(session, PAPERS, claim).outcome is WorkOutcome.DONE and not calls
    searched = list(sources.registry.asked)
    session.add(Entity(claim_id=claim.id, type=EntityType.PAPER, name="A paper", doi="10.1000/new"))
    results = by_step(prepare(session, sources, names=(*SEARCH, PAPERS), at=LATER))
    assert results[TRIALS].report.processed == 0 and results[PAPERS].report.processed == 1
    unchanged = by_step(prepare(session, sources, names=(*SEARCH, PAPERS), at=LATER))
    assert unchanged[PAPERS].report.processed == 0
    assert calls == ["10.1000/new"] and sources.registry.asked == searched


def test_ready_draft_can_be_decided_at_the_model_ceiling(session: Session, monkeypatch):
    from decimal import Decimal

    from backfill_support import same_session
    from thenwhat.cli import claim_steps as cli

    claim = new_claim(session)
    drafted_by_a_read(session, claim.slug)
    sources = Sources()
    prepare(session, sources, names=("claim_articles", *SEARCH, "claim_fetch"))
    config = settings(llm_monthly_budget_usd=Decimal(0))
    monkeypatch.setattr(cli, "settings_or_exit", lambda: config)
    monkeypatch.setattr(cli, "open_session", same_session(session))
    monkeypatch.setattr(cli, "claim_sources", sources.claim_sources)

    decide = next(step for step in claim_steps(config) if step.name == "claim_decide")
    [run] = cli.run_steps([decide])
    assert run.report.done == 1
    assert claim.review_state is ReviewState.APPROVED


def test_publisher_failure_automatically_retries_the_drafts_article(session: Session):
    url = "https://news.example.org/temporary"
    claim = new_claim(session, SLUG, url)
    drafted_by_a_read(session, claim.slug)
    sources = Sources(retriever=FakeRetriever(NotServed(url, 503)))

    prepare(session, sources, names=("claim_articles",))
    waiting = entry(session, "claim_articles", claim)
    assert waiting.outcome is WorkOutcome.LATER
    assert waiting.attempts == 0
    assert waiting.not_before == NOW + timedelta(hours=6)

    # A new, distinct answer proves the page was actually requested on the next run.
    sources.retriever = FakeRetriever(NotNow(url, "brief wait", 60))
    prepare(session, sources, names=("claim_articles",), at=NOW + timedelta(hours=6))
    assert entry(session, "claim_articles", claim).reason == "outlet_held"


def test_paper_approved_after_prepare_is_checked_for_trial_numbers_and_origin(session: Session):
    from test_related_research import paper as indexed_paper

    class Papers(Nothing):
        def paper(self, external_id):
            return indexed_paper(external_id, published="2017-01-01")

    class Numbers(Nothing):
        def trial_numbers(self, *, doi=None, pubmed_id=None):
            assert doi == "10.1000/review"
            return ["NCT00000001"]

    claim = new_claim(session)
    claim.first_reported_date = NOW.date()
    sources = Sources(papers=Papers(), literature=Numbers())
    prepare(session, sources, names=(*SEARCH, PAPERS))
    entity = session.scalars(select(Entity).where(Entity.type == EntityType.INTERVENTION)).one()
    paper = EntityMatch(
        entity_id=entity.id,
        source_name="openalex",
        external_id="10.1000/review",
        score=0.9,
        record_summary="Trial paper",
    )
    session.add(paper)
    record_decision(paper, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    sources.registry.trials = [trial("NCT00000001")]

    rerun = by_step(prepare(session, sources, names=(*SEARCH, PAPERS)))
    assert rerun[TRIALS].report.done == 0
    assert rerun[PAPERS].report.done == 1
    assert (
        session.scalar(
            select(EntityMatch.id).where(
                EntityMatch.entity_id == entity.id, EntityMatch.external_id == "NCT00000001"
            )
        )
        is not None
    )
    assert (
        session.scalar(
            select(Entity.doi).where(Entity.claim_id == claim.id, Entity.is_origin_paper.is_(True))
        )
        == "10.1000/review"
    )
    assert entry(session, PAPERS, claim).outcome is WorkOutcome.DONE


def test_model_outage_stops_trial_readings_without_deferring_individual_claims(
    session: Session, fixture_json
):
    class Offline:
        calls = 0

        def run_many(self, *args, **kwargs):
            self.calls += 1
            raise ModelCannotBeAsked("key refused")

    claims = [new_claim(session, slug) for slug in ("study-a", "study-b")]
    model = Offline()
    sources = Sources(Registry([readable_trial(fixture_json)]), make_llm=lambda _: model)
    runs = by_step(prepare(session, sources))
    assert runs["claim_readings"].report.stopped == "key refused"
    assert model.calls == 1
    assert all(entry_or_none(session, "claim_readings", claim) is None for claim in claims)


def test_crossref_outage_does_not_block_trial_receipt_or_decision(session: Session):
    class UnavailableDoi(Registry):
        def work(self, doi: str) -> SourceRecord | None:
            raise SourceCannotBeAsked("Crossref is down")

    claim = new_claim(session)
    drafted_by_a_read(session, claim.slug)
    add_entity(session, claim.slug, type=EntityType.PAPER, name="A paper", doi="10.1000/named")
    runs = by_step(prepare(session, Sources(registry=UnavailableDoi())))
    assert searches(session, claim)
    assert runs[PAPERS].report.stopped == "Crossref is down"
    assert claim.review_state is ReviewState.APPROVED


def test_last_source_pause_keeps_earlier_paid_term_decisions(session: Session):
    class UnavailableDrug(Targets):
        def drugs_named(self, name: str) -> list[SourceRecord]:
            raise SourceCannotBeAsked("Open Targets retry limit reached")

    claim = new_claim(session)
    sources = Sources(targets=UnavailableDrug())
    [first] = prepare(session, sources, names=("claim_terms",))
    assert first.report.stopped == "Open Targets retry limit reached"
    assert entry_or_none(session, "claim_terms", claim) is None
    assert session.scalar(select(DecisionLog.id).where(DecisionLog.step == INTERVENTION_KIND))
    paid = sources.backend.calls
    sources.targets = Targets()
    [second] = prepare(session, sources, names=("claim_terms",))
    assert second.report.done == 1
    assert sources.backend.calls == paid


def test_article_named_doi_is_picked_up_when_paper_index_is_enabled(session: Session):
    class Papers(Nothing):
        def __init__(self):
            super().__init__()
            self.asked = []

        def paper(self, external_id):
            self.asked.append(external_id)
            return None

    claim = new_claim(session, SLUG, "https://news.example.org/one")
    article = session.scalars(select(SourceArticle)).one()
    article.named_dois = ["10.1000/named"]
    sources = Sources()
    prepare(session, sources, names=("claim_named_records",))
    assert entry(session, "claim_named_records", claim).outcome is WorkOutcome.NEEDS_FIX
    papers = Papers()
    sources.papers = papers
    [rerun] = prepare(session, sources, names=("claim_named_records",))
    assert rerun.report.done == 1
    assert papers.asked == ["10.1000/named"]


def test_unresolved_mesh_entries_are_retried(session: Session):
    class Unresolved(Vocabulary):
        def unresolved_entry_terms(self, name: str) -> list[str]:
            return [name]

    claim = new_claim(session)
    sources = Sources(vocabulary=Unresolved())
    prepare(session, sources, names=("claim_terms",))
    waiting = entry(session, "claim_terms", claim)
    assert waiting.outcome is WorkOutcome.LATER
    assert waiting.not_before is not None
    sources.vocabulary = Vocabulary()
    [rerun] = prepare(session, sources, names=("claim_terms",), at=waiting.not_before)
    assert rerun.report.done == 1
