"""Papers that carry a trial's registry number: PubMed's client replaying recorded
answers, and the step that stores what it finds. Scenario names are from openspec
trial-coverage. The recordings were taken on 2026-11-17 with a generic client name; the
abstracts are replaced and the authors removed (tests/fixtures/README.md)."""

import json
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backfill_support import NOW, same_session
from thenwhat.backfill.allowance import Allowances
from thenwhat.backfill.errors import SourcePaused, SourceStop
from thenwhat.backfill.ledger import count
from thenwhat.backfill.runner import run_step
from thenwhat.backfill.trial_papers import TrialPapers
from thenwhat.config import SourceAllowance
from thenwhat.db.models import RegistryTrial, TrialPaper
from thenwhat.sources.base import MissingContact
from thenwhat.sources.pubmed import (
    PEAK_HOURS,
    IndexUnavailable,
    MissingTool,
    Paper,
    PeakHours,
    PubMed,
    TooManyPapers,
    is_off_peak,
    read_papers,
    search_term,
)

FIXTURES = Path(__file__).parent / "fixtures" / "pubmed"
ALLOWED = {
    "pubmed": SourceAllowance(requests=1000, period_hours=24, interval_seconds=0.5),
    PEAK_HOURS: SourceAllowance(requests=100, period_hours=24, interval_seconds=0),
}
# Trials of the recorded sample: two with a paper each, one with two, one with none.
WITH_ONE, WITH_TWO, WITH_NONE = "NCT04992299", "NCT02788227", "NCT05032820"
# The one paper of the sample whose record carries three numbers.
THREE_NUMBERS = "NCT01547741"


class Service:
    """NCBI as recorded: a search answers with PubMed numbers, a fetch with records."""

    def __init__(self, status: int = 200, search: dict | str | None = None) -> None:
        self.status = status
        # What a search answers instead of the recording: a body, or text that is not one.
        self.search = search
        self.requests: list[httpx.Request] = []

    def fields(self, place: int) -> dict[str, str]:
        sent = parse_qs(self.requests[place].content.decode())
        return {name: values[0] for name, values in sent.items()}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.status != 200:
            return httpx.Response(self.status, json={"error": "API rate limit exceeded"})
        if request.url.path.endswith("esearch.fcgi") and self.search is not None:
            if isinstance(self.search, str):
                return httpx.Response(200, text=self.search)
            return httpx.Response(200, json=self.search)
        if request.url.path.endswith("esearch.fcgi"):
            return httpx.Response(
                200, json=json.loads((FIXTURES / "esearch_completed_sample.json").read_text())
            )
        return httpx.Response(200, text=(FIXTURES / "efetch_completed_sample.xml").read_text())


def pubmed(session: Session, fake_time, service: Service, **options) -> PubMed:
    options.setdefault("contact_email", "ops@thenwhat.test")
    options.setdefault("tool", "thenwhat")
    options.setdefault("api_key", None)
    return PubMed(
        allowances=Allowances(same_session(session), ALLOWED, fake_time),
        transport=httpx.MockTransport(service),
        time=fake_time,
        **options,
    )


# --- the client --------------------------------------------------------------------------


def test_one_search_carries_many_numbers_and_each_papers_record_is_read_back(
    session: Session, fake_time
):
    """Scenario: Fifty trials in one request"""
    service = Service()
    client = pubmed(session, fake_time, service)

    papers, fetched_at = client.papers_carrying([WITH_ONE, WITH_TWO, WITH_NONE])

    assert client.requests_made == len(service.requests) == 2
    search, fetch = service.fields(0), service.fields(1)
    assert [request.method for request in service.requests] == ["POST", "POST"]
    assert service.requests[0].url.path.endswith("/entrez/eutils/esearch.fcgi")
    assert search["term"] == f"{WITH_ONE}[si] OR {WITH_TWO}[si] OR {WITH_NONE}[si]"
    assert (search["db"], search["tool"], search["email"]) == (
        "pubmed",
        "thenwhat",
        "ops@thenwhat.test",
    )
    assert "api_key" not in search
    assert fetch["retmode"] == "xml" and fetch["id"].startswith("42802734,")
    assert len(papers) == 12 and fetched_at == fake_time.now()
    by_number = {number: paper for paper in papers for number in paper.trial_numbers}
    assert by_number[WITH_ONE].pubmed_id == "42802734"
    assert len(by_number[THREE_NUMBERS].trial_numbers) == 3


def test_what_is_kept_of_a_paper_has_no_abstract_and_no_author():
    papers = read_papers((FIXTURES / "efetch_completed_sample.xml").read_text())

    kept = json.dumps([paper.raw for paper in papers])
    assert "Abstract replaced" not in kept and "Removed" not in kept
    assert set(papers[0].raw) == {
        "pmid",
        "title",
        "journal",
        "year",
        "publication_types",
        "databanks",
    }
    assert papers[0].raw["journal"] == "Mindfulness" and papers[0].raw["year"] == "2026"
    assert papers[0].raw["databanks"] == [
        {"name": "ClinicalTrials.gov", "accession_numbers": ["NCT04992299"]}
    ]


def test_a_number_under_another_databank_is_not_a_trial_number():
    xml = """<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>1</PMID><Article>
      <DataBankList><DataBank><DataBankName>ISRCTN</DataBankName><AccessionNumberList>
      <AccessionNumber>NCT00000001</AccessionNumber></AccessionNumberList></DataBank>
      <DataBank><DataBankName>ClinicalTrials.gov</DataBankName><AccessionNumberList>
      <AccessionNumber>nct00000002</AccessionNumber><AccessionNumber>NCT0000</AccessionNumber>
      </AccessionNumberList></DataBank></DataBankList></Article></MedlineCitation>
      </PubmedArticle></PubmedArticleSet>"""

    assert read_papers(xml)[0].trial_numbers == ("NCT00000002",)


def test_the_key_is_sent_when_there_is_one(session: Session, fake_time):
    service = Service()

    pubmed(session, fake_time, service, api_key="synthetic-key").papers_carrying([WITH_ONE])

    assert service.fields(0)["api_key"] == "synthetic-key"


@pytest.mark.parametrize(
    ("options", "refusal", "names"),
    [
        ({"contact_email": ""}, MissingContact, "CONTACT_EMAIL"),
        ({"tool": ""}, MissingTool, "PUBMED_TOOL"),
        ({"tool": "then what"}, MissingTool, "PUBMED_TOOL"),
    ],
)
def test_no_request_is_sent_without_what_the_usage_policy_asks(
    session: Session, fake_time, options, refusal, names
):
    service = Service()

    with pytest.raises(refusal, match=names):
        pubmed(session, fake_time, service, **options).papers_carrying([WITH_ONE])

    assert service.requests == []


def test_too_many_requests_pauses_the_source_for_every_process(session: Session, fake_time):
    service = Service(status=429)
    client = pubmed(session, fake_time, service)

    with pytest.raises(SourcePaused):
        client.papers_carrying([WITH_ONE])
    with pytest.raises(SourcePaused):
        client.papers_carrying([WITH_ONE])

    assert len(service.requests) == 1


def test_a_large_job_stops_at_peak_hours_and_goes_on_off_peak(session: Session, fake_time):
    """NCBI asks that more than 100 requests run at the weekend or at night, Eastern.
    The count is shared: workers and a restarted run are one job."""
    service = Service()
    # Thursday 1 January 2026, 12:00 UTC: seven in the morning in New York.
    assert not is_off_peak(fake_time.now())
    for _ in range(50):
        # Each run has its own client, as each worker and each restart does.
        pubmed(session, fake_time, service).papers_carrying([WITH_ONE])
    assert len(service.requests) == 100

    with pytest.raises(PeakHours, match="more than 100 requests"):
        pubmed(session, fake_time, service).papers_carrying([WITH_ONE])
    assert len(service.requests) == 100

    fake_time.advance(timedelta(days=2))  # Saturday
    assert is_off_peak(fake_time.now())
    pubmed(session, fake_time, service).papers_carrying([WITH_ONE])
    assert len(service.requests) == 102


def test_requests_sent_off_peak_are_not_counted_as_peak_requests(session: Session, fake_time):
    service = Service()
    fake_time.advance(timedelta(days=2))  # Saturday
    for _ in range(60):
        pubmed(session, fake_time, service).papers_carrying([WITH_ONE])

    fake_time.advance(timedelta(days=3, hours=1))  # Tuesday, in peak hours
    assert not is_off_peak(fake_time.now())
    pubmed(session, fake_time, service).papers_carrying([WITH_ONE])

    assert len(service.requests) == 122


@pytest.mark.parametrize(
    ("service", "refusal", "says"),
    [
        (Service(status=503), IndexUnavailable, "status 503"),
        (Service(status=404), IndexUnavailable, "status 404"),
        (Service(search="<html>busy</html>"), IndexUnavailable, "a form this client"),
        (Service(search={"esearchresult": {"ERROR": "busy"}}), IndexUnavailable, "a form this"),
        (
            Service(search={"esearchresult": {"count": "20000", "idlist": ["1"]}}),
            TooManyPapers,
            "PUBMED_TRIALS_PER_REQUEST",
        ),
    ],
)
def test_an_outage_or_an_answer_not_understood_stops_the_run(
    session: Session, fake_time, service, refusal, says
):
    """Scenario: The index is down"""
    trials(session, *(f"NCT0000000{number}" for number in range(1, 6)))
    step = TrialPapers(trials_per_request=5)

    report = run_step(
        same_session(session),
        step,
        pubmed(session, fake_time, service),
        now=lambda: NOW,
        attempt_limit=3,
    )

    # One request, not one for each trial of the batch, and nothing counted against them.
    assert len(service.requests) == 1
    assert issubclass(refusal, SourceStop) and says in (report.stopped or "")
    assert (report.failed, report.remaining_due) == (0, 5)
    assert count(session, step, 3).due == 5


def test_the_plan_counts_requests_by_the_batch():
    step = TrialPapers(trials_per_request=50)

    assert (step.requests_for(26_469), step.requests_for(1), step.requests_for(0)) == (1060, 2, 0)
    assert step.records_for(100) == 2500


def test_off_peak_is_the_weekend_or_nine_at_night_to_five_in_the_morning_eastern():
    def utc(day: int, hour: int) -> datetime:
        return datetime(2026, 11, day, hour, tzinfo=NOW.tzinfo)

    # Tuesday 17 November 2026; New York is five hours behind UTC.
    assert not is_off_peak(utc(17, 15))  # 10:00
    assert not is_off_peak(utc(18, 1))  # 20:00 on Tuesday
    assert is_off_peak(utc(18, 2))  # 21:00 on Tuesday
    assert is_off_peak(utc(17, 9))  # 04:00
    assert not is_off_peak(utc(17, 10))  # 05:00
    assert is_off_peak(utc(21, 15))  # Saturday morning


def test_the_search_term_tags_each_number_for_the_supplied_field():
    assert search_term(["NCT00000001", "NCT00000002"]) == "NCT00000001[si] OR NCT00000002[si]"


# --- the step ----------------------------------------------------------------------------


class Papers:
    """A paper index that answers from a list, and counts."""

    name = "pubmed"

    def __init__(self, papers: Sequence[Paper]) -> None:
        self.papers = list(papers)
        self.requests_made = 0
        self.asked: list[list[str]] = []

    def papers_carrying(self, numbers: Sequence[str]) -> tuple[list[Paper], datetime]:
        self.requests_made += 1
        self.asked.append(list(numbers))
        return [p for p in self.papers if set(p.trial_numbers) & set(numbers)], NOW


def paper(pubmed_id: str, *numbers: str) -> Paper:
    return Paper(pubmed_id, numbers, {"pmid": pubmed_id, "title": f"Paper {pubmed_id}"})


def trials(session: Session, *numbers: str, **fields) -> list[RegistryTrial]:
    defaults = {
        "registry_name": "clinicaltrials.gov",
        "title": "A trial",
        "conditions": ["condition"],
        "interventions": [],
        "phases": ["PHASE3"],
        "overall_status": "RECRUITING",
        "last_update_posted": date(2025, 6, 1),
        "raw_payload": {},
        "fetched_at": NOW,
    }
    rows = [RegistryTrial(external_id=number, **(defaults | fields)) for number in numbers]
    session.add_all(rows)
    session.flush()
    return rows


def work(session: Session, step: TrialPapers, client: Papers, **options):
    return run_step(
        same_session(session), step, client, now=lambda: NOW, attempt_limit=3, **options
    )


def stored(session: Session) -> list[tuple[str, str]]:
    return [
        (number, pubmed_id)
        for number, pubmed_id in session.execute(
            select(RegistryTrial.external_id, TrialPaper.pubmed_id)
            .join(TrialPaper, TrialPaper.registry_trial_id == RegistryTrial.id)
            .order_by(RegistryTrial.external_id, TrialPaper.pubmed_id)
        )
    ]


def test_a_paper_is_given_only_to_the_trials_its_own_record_names(session: Session):
    """Scenarios: A paper that gives one trial's number; Fifty trials in one request"""
    trials(session, "NCT00000001", "NCT00000002", "NCT00000003")
    client = Papers([paper("11", "NCT00000001"), paper("12", "NCT00000001", "NCT00000002")])

    report = work(session, TrialPapers(trials_per_request=50), client)

    assert (report.done, report.nothing_found, report.failed) == (2, 1, 0)
    assert client.asked == [["NCT00000001", "NCT00000002", "NCT00000003"]]
    assert stored(session) == [
        ("NCT00000001", "11"),
        ("NCT00000001", "12"),
        ("NCT00000002", "12"),
    ]
    kept = session.scalars(select(TrialPaper).where(TrialPaper.pubmed_id == "11")).one()
    assert (kept.source_name, kept.fetched_at) == ("pubmed", NOW)
    assert kept.raw_payload == {"pmid": "11", "title": "Paper 11"}


def test_a_review_that_lists_twelve_trials_is_attached_to_none(session: Session):
    """Scenario: A review that lists twelve trials"""
    trials(session, "NCT00000001")
    review = paper("20", *(f"NCT000000{number:02d}" for number in range(1, 13)))

    report = work(session, TrialPapers(), Papers([review, paper("21", "NCT00000001")]))

    assert (report.done, report.nothing_found) == (1, 0)
    assert stored(session) == [("NCT00000001", "21")]


def test_nothing_found_is_an_answer_and_a_trial_asked_is_not_asked_again(session: Session):
    """Scenario: Asked last week, nothing found"""
    trials(session, "NCT00000001", "NCT00000002")
    step, client = TrialPapers(), Papers([paper("11", "NCT00000001")])
    work(session, step, client)

    again = work(session, step, client)

    assert client.requests_made == 1
    assert (again.done, again.nothing_found, again.remaining_due) == (0, 0, 0)
    counts = count(session, step, 3)
    assert (counts.done, counts.nothing_found, counts.due) == (1, 1, 0)


def test_a_run_goes_on_from_where_the_last_one_stopped(session: Session):
    trials(session, *(f"NCT0000000{number}" for number in range(1, 6)))
    step, client = TrialPapers(trials_per_request=2), Papers([])

    first = work(session, step, client, limit=2)
    second = work(session, step, client)

    assert (first.nothing_found, first.remaining_due) == (2, 3)
    assert (second.nothing_found, second.remaining_due) == (3, 0)
    assert sorted(number for batch in client.asked for number in batch) == [
        f"NCT0000000{number}" for number in range(1, 6)
    ]


def test_a_run_stopped_by_the_source_leaves_its_trials_due(session: Session):
    """Scenario: The allowance runs out"""
    trials(session, "NCT00000001", "NCT00000002")

    class Paused(Papers):
        def papers_carrying(self, numbers):
            raise SourcePaused("pubmed said it was asked too often.")

    step = TrialPapers()
    report = work(session, step, Paused([]))

    assert report.stopped == "pubmed said it was asked too often."
    assert (report.processed, report.remaining_due) == (0, 2)
    assert stored(session) == []


def test_only_trials_of_the_named_sets_are_asked_for_and_the_completed_set_first(
    session: Session,
):
    trials(session, "NCT00000001")  # active
    trials(
        session,
        "NCT00000002",
        overall_status="COMPLETED",
        completion_date="2025-06",
        completion_date_type="ACTUAL",
        has_results=True,
    )
    trials(session, "NCT00000003", phases=["PHASE1"])  # in neither set
    trials(session, "ISRCTN12345678", registry_name="isrctn")  # another registry
    client = Papers([])

    work(session, TrialPapers(trials_per_request=1), client)

    assert client.asked == [["NCT00000002"], ["NCT00000001"]]


def test_the_step_makes_papers_of_trials_and_nothing_else(session: Session):
    """Scenario: A route finishes"""
    from thenwhat.db.models import Claim, EntityMatch, EvidenceEvent, PaperRecord

    trials(session, "NCT00000001")

    work(session, TrialPapers(), Papers([paper("11", "NCT00000001")]))

    for model in (Claim, EntityMatch, EvidenceEvent, PaperRecord):
        assert session.scalars(select(model)).first() is None
