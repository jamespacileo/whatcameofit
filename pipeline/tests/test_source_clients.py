"""The registry, literature and organisation clients, replaying recorded responses
(see tests/fixtures/README.md).

Scenario names are from openspec source-clients.
"""

from datetime import date, timedelta

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.db.models import HttpCache
from thenwhat.sources import openalex, ror
from thenwhat.sources.base import AllowanceUsedUp, MissingKey
from thenwhat.sources.clinicaltrials import ClinicalTrials
from thenwhat.sources.crossref import Crossref, Notice
from thenwhat.sources.europepmc import EuropePmc, describe
from thenwhat.sources.openalex import OpenAlex
from thenwhat.sources.ror import Ror

CONTACT = "ops@thenwhat.test"
NOT_FOUND = httpx.Response(404, text="not found")


class Replay:
    """Serves recorded responses chosen by a routing function and counts requests."""

    def __init__(self, route) -> None:
        self.route = route
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        answer = self.route(request)
        return answer if isinstance(answer, httpx.Response) else httpx.Response(200, json=answer)


# --- ClinicalTrials.gov ----------------------------------------------------------


def trials(session: Session, fake_time, route) -> tuple[ClinicalTrials, Replay]:
    replay = Replay(route)
    source = ClinicalTrials(
        session, contact_email=CONTACT, transport=httpx.MockTransport(replay), time=fake_time
    )
    return source, replay


def test_trial_record_carries_the_common_contract(session: Session, fake_time, fixture_json):
    """Scenario: Trial record"""
    study = fixture_json("clinicaltrials/study_NCT02586935.json")
    source, replay = trials(session, fake_time, lambda request: study)

    record = source.fetch_trial("NCT02586935")

    assert record is not None
    assert record.source_name == "clinicaltrials.gov"
    assert record.external_id == "NCT02586935"
    assert record.url == "https://clinicaltrials.gov/study/NCT02586935"
    assert record.payload == study
    assert record.fetched_at == fake_time.now()
    assert replay.requests[0].url.path == "/api/v2/studies/NCT02586935"


def test_unknown_trial_identifier_is_not_found(session: Session, fake_time):
    """Scenario: Unknown trial identifier"""
    source, _ = trials(session, fake_time, lambda request: NOT_FOUND)

    assert source.fetch_trial("NCT99999999") is None


def test_malformed_trial_identifier_is_not_found_without_a_request(session: Session, fake_time):
    source, replay = trials(session, fake_time, lambda request: NOT_FOUND)

    assert source.fetch_trial("not-a-trial-id") is None
    assert replay.requests == []


def search_pages(fixture_json):
    pages = [fixture_json(f"clinicaltrials/search_tideglusib_page{n}.json") for n in (1, 2, 3)]
    by_token = {
        None: pages[0],
        pages[0]["nextPageToken"]: pages[1],
        pages[1]["nextPageToken"]: pages[2],
    }
    return lambda request: by_token[request.url.params.get("pageToken")]


def test_search_by_intervention_term_returns_matching_trials(
    session: Session, fake_time, fixture_json
):
    """Scenario: Search by intervention term"""
    source, replay = trials(session, fake_time, search_pages(fixture_json))

    records = source.search_trials("tideglusib")

    assert replay.requests[0].url.params["query.intr"] == "tideglusib"
    assert records[0].external_id == "NCT02586935"
    assert records[0].url == "https://clinicaltrials.gov/study/NCT02586935"
    assert all(record.source_name == "clinicaltrials.gov" for record in records)


def test_search_with_many_results_follows_every_page(session: Session, fake_time, fixture_json):
    """Scenario: Search with many results"""
    source, replay = trials(session, fake_time, search_pages(fixture_json))

    records = source.search_trials("tideglusib")

    assert len({record.external_id for record in records}) == 10
    assert len(replay.requests) == 3


def broad_search(fixture_json, narrowed_by=lambda condition: True):
    """A name with thousands of trials. With a condition, the registry answers only when
    `narrowed_by` accepts the condition's wording."""
    broad = fixture_json("clinicaltrials/search_broad_count.json")
    narrowed = fixture_json("clinicaltrials/search_broad_with_condition.json")

    def route(request: httpx.Request):
        condition = request.url.params.get("query.cond")
        if condition is None:
            return broad
        return narrowed if narrowed_by(condition) else {"studies": [], "totalCount": 0}

    return route


def test_broad_name_is_searched_within_the_condition(session: Session, fake_time, fixture_json):
    """Scenario: Broad intervention name"""
    source, replay = trials(session, fake_time, broad_search(fixture_json))

    records = source.search_trials("CAR-T cell therapy", condition="Stiff person syndrome")

    assert [record.external_id for record in records] == ["NCT07341828", "NCT06588491"]
    # One request to learn how many trials the name has, one within the condition;
    # the thousands of other trials are never paged through.
    assert [request.url.params.get("query.cond") for request in replay.requests] == [
        None,
        "Stiff person syndrome",
    ]
    assert replay.requests[0].url.params["countTotal"] == "true"


def test_specific_name_is_searched_without_the_condition(session: Session, fake_time, fixture_json):
    source, replay = trials(session, fake_time, search_pages(fixture_json))

    records = source.search_trials("tideglusib", condition="Tooth decay")

    assert len({record.external_id for record in records}) == 10
    assert all("query.cond" not in request.url.params for request in replay.requests)


def test_condition_wording_the_registry_does_not_know_is_tried_by_its_words(
    session: Session, fake_time, fixture_json
):
    route = broad_search(fixture_json, narrowed_by=lambda condition: " OR " in condition)
    source, replay = trials(session, fake_time, route)

    records = source.search_trials(
        "CAR-T cell therapy", condition="Stiff person syndrome, a rare disorder"
    )

    assert len(records) == 2
    # Words every condition shares are left out of the second attempt.
    assert replay.requests[-1].url.params["query.cond"] == "stiff OR person OR rare"


def test_broad_name_with_no_trial_under_the_condition_gives_no_candidates(
    session: Session, fake_time, fixture_json
):
    route = broad_search(fixture_json, narrowed_by=lambda condition: False)
    source, replay = trials(session, fake_time, route)

    records = source.search_trials("CAR-T cell therapy", condition="Stiff person syndrome")

    assert records == []
    assert all("pageToken" not in request.url.params for request in replay.requests)


def test_name_still_broad_within_the_condition_gives_no_candidates(
    session: Session, fake_time, fixture_json
):
    """Scenario: Name that identifies nothing"""
    # A phrase such as "the drug": thousands of trials whatever the condition.
    broad = fixture_json("clinicaltrials/search_broad_count.json")
    source, replay = trials(session, fake_time, lambda request: broad)

    records = source.search_trials("the drug", condition="Muscle loss")

    assert records == []
    assert len(replay.requests) == 2


def test_trials_that_carry_a_trial_name_are_found(session: Session, fake_time, fixture_json):
    """Scenario: Search by a trial's name"""
    named = fixture_json("clinicaltrials/titles_surmount5.json")
    source, replay = trials(session, fake_time, lambda request: named)

    records = source.named_trials('SURMOUNT-5"')

    assert [record.external_id for record in records] == ["NCT05822830"]
    assert replay.requests[0].url.params["query.titles"] == '"SURMOUNT-5"'
    design = records[0].payload["protocolSection"]["designModule"]
    assert design["enrollmentInfo"]["count"] == 751


def test_a_trial_name_that_many_trials_carry_identifies_none(
    session: Session, fake_time, fixture_json
):
    named = fixture_json("clinicaltrials/titles_surmount5.json") | {"totalCount": 4000}
    source, _ = trials(session, fake_time, lambda request: named)

    assert source.named_trials("study") == []


# --- Europe PMC ------------------------------------------------------------------


def literature(session: Session, fake_time, route) -> tuple[EuropePmc, Replay]:
    replay = Replay(route)
    source = EuropePmc(
        session, contact_email=CONTACT, transport=httpx.MockTransport(replay), time=fake_time
    )
    return source, replay


EMPTY_SEARCH = {"hitCount": 0, "resultList": {"result": []}}


def test_a_paper_gives_the_registry_number_of_its_trial(session: Session, fake_time, fixture_json):
    """Scenario: Registry number of a paper's trial"""
    paper = fixture_json("europepmc/paper_nejmoa2206038.json")
    source, replay = literature(session, fake_time, lambda request: paper)

    assert source.trial_numbers(doi="10.1056/nejmoa2206038") == ["NCT04184622"]
    assert source.trial_numbers(pubmed_id="35658024") == ["NCT04184622"]
    asked = [request.url.params["query"] for request in replay.requests]
    assert asked == ['DOI:"10.1056/nejmoa2206038"', "EXT_ID:35658024 AND SRC:MED"]


def test_a_paper_that_lists_many_trials_or_is_unknown_identifies_none(
    session: Session, fake_time, fixture_json
):
    review = fixture_json("europepmc/paper_nejmoa2206038.json")
    review["resultList"]["result"][0]["abstractText"] = " ".join(
        f"NCT0000000{n}" for n in range(1, 6)
    )
    answers = {'DOI:"10.1/review"': review}
    source, replay = literature(
        session, fake_time, lambda request: answers.get(request.url.params["query"], EMPTY_SEARCH)
    )

    assert source.trial_numbers(doi="10.1/review") == []
    assert source.trial_numbers(doi="10.1/unknown") == []
    assert source.trial_numbers(pubmed_id="not-a-number") == []
    assert len(replay.requests) == 2


def test_paper_is_found_by_its_doi(session: Session, fake_time, fixture_json):
    paper = fixture_json("europepmc/paper_srep39654.json")
    source, replay = literature(session, fake_time, lambda request: paper)

    record = source.paper("10.1038/srep39654")

    assert record is not None
    assert (record.source_name, record.external_id) == ("europepmc", "10.1038/srep39654")
    assert record.url == "https://europepmc.org/article/MED/28067250"
    assert record.payload == paper["resultList"]["result"][0]
    assert replay.requests[0].url.params["query"] == 'DOI:"10.1038/srep39654"'
    info = describe(record)
    assert info.title == "Promotion of natural tooth repair by small molecule GSK3 antagonists."
    assert info.authors[:2] == ("Neves VC", "Babb R")
    assert (info.published_date, info.doi) == (date(2017, 1, 9), "10.1038/srep39654")
    assert info.abstract


def test_unknown_doi_is_not_found(session: Session, fake_time):
    source, _ = literature(session, fake_time, lambda request: EMPTY_SEARCH)

    assert source.paper("10.9999/does-not-exist") is None


def citing_route(fixture_json):
    paper = fixture_json("europepmc/paper_srep39654.json")
    first_page = fixture_json("europepmc/citing_srep39654_page1.json")

    def route(request: httpx.Request):
        query = request.url.params["query"]
        if query.startswith("DOI:"):
            return paper
        assert query == "CITES:28067250_MED"
        cursor = request.url.params["cursorMark"]
        return first_page if cursor == "*" else EMPTY_SEARCH | {"nextCursorMark": cursor}

    return route


def test_citing_papers_are_listed_with_their_details(session: Session, fake_time, fixture_json):
    """Scenario: Citing papers"""
    source, _ = literature(session, fake_time, citing_route(fixture_json))
    paper = source.paper("10.1038/srep39654")
    assert paper is not None

    citing = source.citing_papers(paper, page_size=3)

    assert [record.external_id for record in citing] == [
        "10.1007/s10735-026-10987-w",
        "10.2147/dddt.s621268",
        "10.3389/fcell.2026.1795445",
    ]
    first = describe(citing[0])
    assert first.title.startswith("Glomerular epithelial protein-1")
    assert first.authors[0].startswith("Pokharel")
    assert (first.published_date, first.doi) == (date(2026, 10, 1), "10.1007/s10735-026-10987-w")


def test_citing_papers_follow_the_cursor_until_a_page_comes_back_empty(
    session: Session, fake_time, fixture_json
):
    source, replay = literature(session, fake_time, citing_route(fixture_json))
    paper = source.paper("10.1038/srep39654")
    assert paper is not None

    source.citing_papers(paper, page_size=3)

    cursors = [r.url.params["cursorMark"] for r in replay.requests if "cursorMark" in r.url.params]
    assert cursors == ["*", "AoIIQHd8aSg1NTc4OTc0NQ=="]


# --- Crossref --------------------------------------------------------------------

RETRACTED_DOI = "10.1016/S0140-6736(97)11096-0"


def registry(session: Session, fake_time, route) -> tuple[Crossref, Replay]:
    replay = Replay(route)
    source = Crossref(
        session, contact_email=CONTACT, transport=httpx.MockTransport(replay), time=fake_time
    )
    return source, replay


def test_work_metadata_is_fetched_by_doi(session: Session, fake_time, fixture_json):
    work = fixture_json("crossref/work_srep39654.json")
    source, replay = registry(session, fake_time, lambda request: work)

    record = source.work("10.1038/srep39654")

    assert record is not None
    assert (record.source_name, record.external_id) == ("crossref", "10.1038/srep39654")
    assert record.url == "https://doi.org/10.1038/srep39654"
    assert record.payload == work["message"]
    assert replay.requests[0].url.path == "/works/10.1038/srep39654"


def test_retracted_paper_lists_its_retraction_notice(session: Session, fake_time, fixture_json):
    """Scenario: Retracted paper"""
    work = fixture_json("crossref/work_retracted_lancet_1998.json")
    source, _ = registry(session, fake_time, lambda request: work)

    notices = source.notices(RETRACTED_DOI)

    assert Notice("retraction", date(2010, 2, 6), "10.1016/s0140-6736(10)60175-4") in notices
    assert Notice("correction", date(2004, 3, 6), "10.1016/s0140-6736(04)15715-2") in notices


def test_paper_with_no_notices_gives_an_empty_list(session: Session, fake_time, fixture_json):
    """Scenario: Paper with no notices"""
    work = fixture_json("crossref/work_srep39654.json")
    source, _ = registry(session, fake_time, lambda request: work)

    assert source.notices("10.1038/srep39654") == []


def test_unknown_doi_has_no_work_and_no_notices(session: Session, fake_time):
    source, _ = registry(session, fake_time, lambda request: NOT_FOUND)

    assert source.work("10.9999/does-not-exist") is None
    assert source.notices("10.9999/does-not-exist") == []


def test_work_and_notices_for_one_doi_cost_one_request(session: Session, fake_time, fixture_json):
    work = fixture_json("crossref/work_retracted_lancet_1998.json")
    source, replay = registry(session, fake_time, lambda request: work)

    source.work(RETRACTED_DOI)
    source.notices(RETRACTED_DOI)

    assert len(replay.requests) == 1


def test_search_phrase_is_searched_only_within_the_condition(
    session: Session, fake_time, fixture_json
):
    source, replay = trials(session, fake_time, broad_search(fixture_json))

    records = source.search_phrase("cell therapy", "Stiff person syndrome")

    assert [record.external_id for record in records] == ["NCT07341828", "NCT06588491"]
    assert [request.url.params.get("query.cond") for request in replay.requests] == [
        "Stiff person syndrome"
    ]


def test_search_phrase_without_a_condition_sends_nothing(session: Session, fake_time, fixture_json):
    source, replay = trials(session, fake_time, broad_search(fixture_json))

    assert source.search_phrase("cell therapy", None) == []
    assert replay.requests == []


def test_search_phrase_that_is_broad_within_the_condition_finds_nothing(
    session: Session, fake_time, fixture_json
):
    """Scenario: Search phrase that identifies nothing"""
    source, _ = trials(
        session, fake_time, lambda request: fixture_json("clinicaltrials/search_broad_count.json")
    )

    assert source.search_phrase("cell therapy", "Cancer") == []


# --- OpenAlex --------------------------------------------------------------------

OPENALEX_KEY = "test-key-not-a-real-one"
TERMS = ["median nerve stimulation"]
CONDITION = "Tourette syndrome"


def allowance(remaining: str = "0.994", prepaid: str = "0", reset: str = "3600") -> dict[str, str]:
    """The headers OpenAlex sends with every answer to a search."""
    return {
        "X-RateLimit-Cost-USD": "0.001",
        "X-RateLimit-Remaining-USD": remaining,
        "X-RateLimit-Prepaid-Remaining-USD": prepaid,
        "X-RateLimit-Reset": reset,
    }


def papers(
    session: Session, fake_time, route, *, api_key: str | None = OPENALEX_KEY
) -> tuple[OpenAlex, Replay]:
    replay = Replay(route)
    source = OpenAlex(
        session,
        contact_email=CONTACT,
        api_key=api_key,
        transport=httpx.MockTransport(replay),
        time=fake_time,
    )
    return source, replay


def found_with(fixture_json, **stated: str) -> httpx.Response:
    return httpx.Response(
        200,
        json=fixture_json("openalex/search_median_nerve_tourette.json"),
        headers=allowance(**stated),
    )


def searches(replay: Replay) -> list[str]:
    return [r.url.params["search"] for r in replay.requests if r.url.path == "/works"]


def test_literature_search_returns_papers_most_relevant_first(
    session: Session, fake_time, fixture_json
):
    """Scenario: Search with results"""
    source, replay = papers(session, fake_time, lambda request: found_with(fixture_json))

    records = source.search_papers(TERMS, CONDITION)

    assert [record.external_id for record in records] == [
        "10.5281/zenodo.19046790",
        "10.3390/jcm12072514",
        "10.1016/j.cub.2020.04.044",
    ]
    assert records[0].url == "https://doi.org/10.5281/zenodo.19046790"
    trial = openalex.describe(records[1])
    assert trial.title.startswith("Median Nerve Stimulation for Treatment of Tics: Randomized")
    assert (trial.kind, trial.year) == ("article", 2023)
    assert trial.published_date == date(2023, 3, 27)
    assert trial.journal == "Journal of Clinical Medicine"
    assert trial.pubmed_id == "37048598"
    assert trial.abstract == "Abstract replaced in this fixture."
    assert len(trial.authors) == 8
    assert trial.authors[0].institutions == (("Washington University in St. Louis", "01yc7t268"),)
    assert searches(replay) == ['("median nerve stimulation") AND "Tourette syndrome"']


def test_every_name_and_phrase_of_a_claim_goes_into_one_search(
    session: Session, fake_time, fixture_json
):
    source, replay = papers(session, fake_time, lambda request: found_with(fixture_json))

    source.search_papers(
        ['Wrist-worn "device" (new)', "median nerve stimulation", "median nerve stimulation"],
        CONDITION,
    )

    assert searches(replay) == [
        '("Wrist-worn device new" OR "median nerve stimulation") AND "Tourette syndrome"'
    ]
    assert source.usage.searches_sent == 1


def test_literature_search_asks_for_no_page_beyond_the_limit(
    session: Session, fake_time, fixture_json
):
    """Scenario: Search with more results than the limit"""
    found = fixture_json("openalex/search_median_nerve_tourette.json")
    source, replay = papers(session, fake_time, lambda request: found_with(fixture_json))

    records = source.search_papers(TERMS, CONDITION, limit=2)

    assert found["meta"]["count"] > 20
    assert len(records) == 2
    assert [request.url.params["per_page"] for request in replay.requests] == ["2"]


def test_search_that_finds_nothing_as_phrases_is_tried_once_more_by_its_words(
    session: Session, fake_time, fixture_json
):
    nothing = httpx.Response(
        200, json=fixture_json("openalex/search_nothing.json"), headers=allowance()
    )
    source, replay = papers(session, fake_time, lambda request: nothing)

    assert source.search_papers(["Wrist-worn stimulation device", "a phrase"], CONDITION) == []
    assert searches(replay) == [
        '("Wrist-worn stimulation device" OR "a phrase") AND "Tourette syndrome"',
        "Wrist-worn stimulation device Tourette syndrome",
    ]


def test_a_search_is_answered_from_the_cache_for_a_week(session: Session, fake_time, fixture_json):
    source, replay = papers(session, fake_time, lambda request: found_with(fixture_json))
    source.search_papers(TERMS, CONDITION)

    fake_time.advance(timedelta(days=6))
    again, _ = papers(session, fake_time, replay)
    assert len(again.search_papers(TERMS, CONDITION)) == 3
    assert (again.usage.searches_sent, again.usage.searches_from_cache) == (0, 1)
    assert again.usage.line() == (
        "OpenAlex: 0 searches sent ($0.000), 1 answered from the week's cache."
    )

    fake_time.advance(timedelta(days=2))
    again.search_papers(TERMS, CONDITION)
    assert len(replay.requests) == 2


def test_one_paper_is_looked_up_by_its_doi(session: Session, fake_time, fixture_json):
    work = fixture_json("openalex/work_704541.json")
    source, replay = papers(session, fake_time, lambda request: work)

    record = source.paper("10.64898/2026.02.07.704541")

    assert record is not None
    assert record.external_id == "10.64898/2026.02.07.704541"
    assert replay.requests[0].url.path == "/works/doi:10.64898/2026.02.07.704541"
    assert source.paper("not an identifier") is None
    assert len(replay.requests) == 1
    assert source.usage.searches_sent == 0


def test_literature_search_without_a_key_sends_nothing_and_names_the_setting(
    session: Session, fake_time
):
    """Scenario: Missing key"""
    source, replay = papers(session, fake_time, lambda request: {}, api_key=None)

    with pytest.raises(MissingKey, match="OPENALEX_API_KEY"):
        source.search_papers(TERMS, CONDITION)
    assert replay.requests == []


def test_the_key_is_sent_in_a_header_and_kept_out_of_the_cache(
    session: Session, fake_time, fixture_json, caplog
):
    source, replay = papers(session, fake_time, lambda request: found_with(fixture_json))

    with caplog.at_level("DEBUG"):
        source.search_papers(TERMS, CONDITION)

    [request] = replay.requests
    assert request.headers["Authorization"] == f"Bearer {OPENALEX_KEY}"
    assert OPENALEX_KEY not in str(request.url)
    cached = session.scalars(select(HttpCache)).all()
    assert cached and all(OPENALEX_KEY not in f"{row.request_key} {row.payload}" for row in cached)
    assert OPENALEX_KEY not in caplog.text
    assert OPENALEX_KEY not in source.usage.line()


def test_a_run_reports_what_it_sent_what_it_cost_and_what_is_left(
    session: Session, fake_time, fixture_json
):
    source, _ = papers(session, fake_time, lambda request: found_with(fixture_json))

    source.search_papers(TERMS, CONDITION)

    assert source.usage.line() == (
        "OpenAlex: 1 search sent ($0.001), $0.994 of the free allowance left today."
    )


def test_used_up_allowance_stops_the_run_without_a_retry(session: Session, fake_time):
    """Scenario: Allowance used up"""
    refused = httpx.Response(429, json={}, headers=allowance(remaining="0"))
    source, replay = papers(session, fake_time, lambda request: refused)

    with pytest.raises(AllowanceUsedUp, match="used up"):
        source.search_papers(["first"], CONDITION)
    with pytest.raises(AllowanceUsedUp):
        source.search_papers(["second"], CONDITION)

    assert len(replay.requests) == 1
    assert fake_time.slept == []
    assert "used up" in source.usage.line()


def test_the_last_search_of_the_allowance_stops_every_client_until_it_resets(
    session: Session, fake_time, fixture_json
):
    last = found_with(fixture_json, remaining="0", reset="3600")
    source, replay = papers(session, fake_time, lambda request: last)

    assert len(source.search_papers(["first"], CONDITION)) == 3
    # Another process, or a later run of the day, reads the same stop from the database.
    other, _ = papers(session, fake_time, replay)
    with pytest.raises(AllowanceUsedUp, match="used up"):
        other.search_papers(["second"], CONDITION)
    # What was already answered is still served, and one paper is still looked up.
    assert len(other.search_papers(["first"], CONDITION)) == 3
    assert len(replay.requests) == 1

    fake_time.advance(timedelta(seconds=3601))
    assert len(other.search_papers(["second"], CONDITION)) == 3


def test_prepaid_credit_on_the_account_stops_searches_so_none_is_spent(
    session: Session, fake_time, fixture_json
):
    source, replay = papers(
        session, fake_time, lambda request: found_with(fixture_json, prepaid="5")
    )

    assert len(source.search_papers(["first"], CONDITION)) == 3
    with pytest.raises(AllowanceUsedUp, match="prepaid credit"):
        source.search_papers(["second"], CONDITION)

    assert len(replay.requests) == 1
    assert "prepaid credit" in source.usage.line()


def test_an_allowance_the_source_does_not_state_stops_further_searches(
    session: Session, fake_time, fixture_json
):
    unstated = httpx.Response(200, json=fixture_json("openalex/search_median_nerve_tourette.json"))
    source, replay = papers(session, fake_time, lambda request: unstated)

    assert len(source.search_papers(["first"], CONDITION)) == 3
    with pytest.raises(AllowanceUsedUp, match="did not say"):
        source.search_papers(["second"], CONDITION)
    assert len(replay.requests) == 1


def test_one_paper_is_still_looked_up_once_the_searches_are_spent(
    session: Session, fake_time, fixture_json
):
    answers = [
        found_with(fixture_json, remaining="0"),
        httpx.Response(200, json=fixture_json("openalex/work_704541.json")),
    ]
    source, _ = papers(session, fake_time, lambda request: answers.pop(0))
    source.search_papers(["first"], CONDITION)

    assert source.paper("10.64898/2026.02.07.704541") is not None


def test_a_brief_rate_limit_with_allowance_left_is_retried(
    session: Session, fake_time, fixture_json
):
    answers = [httpx.Response(429, json={}, headers=allowance()), found_with(fixture_json)]
    source, replay = papers(session, fake_time, lambda request: answers.pop(0))

    assert len(source.search_papers(TERMS, CONDITION)) == 3
    assert len(replay.requests) == 2
    assert source.usage.searches_sent == 1


# --- ROR -------------------------------------------------------------------------


def organisations(session: Session, fake_time, route) -> tuple[Ror, Replay]:
    replay = Replay(route)
    source = Ror(
        session, contact_email=CONTACT, transport=httpx.MockTransport(replay), time=fake_time
    )
    return source, replay


def test_known_organisation_is_returned_with_its_identifier_and_match_measure(
    session: Session, fake_time, fixture_json
):
    """Scenario: Known organisation"""
    found = fixture_json("ror/affiliation_university_of_nottingham.json")
    source, replay = organisations(session, fake_time, lambda request: found)

    [record] = source.organisations("University of Nottingham")

    assert (record.source_name, record.external_id) == ("ror", "01ee9ar58")
    assert record.url == "https://ror.org/01ee9ar58"
    assert ror.describe(record) == ror.Organisation(
        name="University of Nottingham",
        country="United Kingdom",
        website="https://www.nottingham.ac.uk/",
        name_match=1.0,
    )
    assert replay.requests[0].url.params["affiliation"] == "University of Nottingham"


def test_unknown_organisation_gives_an_empty_result(session: Session, fake_time, fixture_json):
    """Scenario: Unknown organisation"""
    near_misses = fixture_json("ror/affiliation_unknown.json")
    source, _ = organisations(session, fake_time, lambda request: near_misses)

    assert near_misses["items"]
    assert source.organisations("Zzqxv Institute of Nowhere Qqxzj") == []
