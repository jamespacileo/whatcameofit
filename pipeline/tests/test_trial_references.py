"""What a stored registry record itself lists: papers by kind, and links. Rows are built
in the test database; nothing is asked of any source.
Scenario names are from openspec trial-coverage."""

from datetime import date
from typing import Any

import pytest
from sqlalchemy.orm import Session

from backfill_support import NOW
from thenwhat.backfill.trial_references import (
    UnknownSet,
    count_references,
    references_in,
    references_of,
)
from thenwhat.db.models import RegistryTrial
from thenwhat.events.trial_facts import read_trial

ACTIVE = "active-since-2025"
COMPLETED = "completed-with-results-since-2025"


def record(references: list[dict[str, Any]], links: list[dict[str, Any]] | None = None):
    module: dict[str, Any] = {"references": references}
    if links is not None:
        module["seeAlsoLinks"] = links
    return {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000001", "briefTitle": "A study"},
            "referencesModule": module,
        }
    }


def trial(session: Session, external_id: str, payload: dict[str, Any], **fields: Any):
    defaults: dict[str, Any] = {
        "registry_name": "demo-registry",
        "external_id": external_id,
        "title": f"Trial {external_id}",
        "conditions": ["condition"],
        "interventions": [],
        "phases": ["PHASE3"],
        "overall_status": "RECRUITING",
        "last_update_posted": date(2025, 6, 1),
        "has_results": False,
        "raw_payload": payload,
        "fetched_at": NOW,
    }
    session.add(RegistryTrial(**(defaults | fields)))
    session.flush()


def test_a_record_with_one_results_paper_and_four_background_papers():
    """Scenario: A record with one results paper and four background papers"""
    listed = references_of(
        record(
            [{"pmid": "111", "type": "RESULT"}]
            + [{"pmid": str(number), "type": "BACKGROUND"} for number in range(200, 204)]
        )
    )

    assert listed.listed_by_sponsor == ("111",)
    assert listed.linked_by_registry == ()
    assert listed.background == 4


def test_a_paper_the_registry_linked_is_kept_apart_from_one_the_sponsor_listed():
    listed = references_of(
        record(
            [
                {"pmid": "111", "type": "DERIVED"},
                {"pmid": "222", "type": "RESULT"},
                # Listed twice: the sponsor's listing is the one kept.
                {"pmid": "333", "type": "DERIVED"},
                {"pmid": "333", "type": "RESULT"},
                # Not a PubMed number, and a kind the registry does not have.
                {"pmid": "PMC44", "type": "RESULT"},
                {"pmid": "555", "type": "OTHER"},
                {"type": "RESULT", "citation": "A citation with no number."},
            ]
        )
    )

    assert listed.listed_by_sponsor == ("222", "333")
    assert listed.linked_by_registry == ("111",)


def test_the_papers_are_those_the_claim_path_reads_from_the_same_record():
    """A stored trial's papers and a cited trial's are named by one rule, so the one
    store of paper records holds each paper once whichever asks."""
    study = record(
        [
            {"pmid": "111", "type": "DERIVED"},
            {"pmid": "222", "type": "RESULT"},
            {"pmid": "333", "type": "BACKGROUND"},
        ]
    )

    assert references_of(study).papers == read_trial(study).results_papers


def test_a_link_is_named_by_its_domain_and_whether_that_is_a_listed_outlet():
    """Scenarios: A record that links a press release; A record that links the sponsor's
    site"""
    listed = references_of(
        record(
            [],
            [
                {"label": "Release", "url": "https://www.prnewswire.com/news/a-release.html"},
                {"label": "Sponsor", "url": "https://trials.sponsor.example/study"},
                {"label": "Again", "url": "https://trials.sponsor.example/study"},
                {"label": "Not an address", "url": "see the sponsor"},
                {"label": "Nothing"},
            ],
        )
    )

    assert [(link.domain, link.listed) for link in listed.links] == [
        ("prnewswire.com", True),
        ("trials.sponsor.example", False),
    ]


def test_a_record_with_no_references_lists_nothing():
    assert references_of({"protocolSection": {}}).papers == ()
    assert references_of({}).links == ()
    assert references_of({"protocolSection": {"referencesModule": {}}}).background == 0


def test_a_set_is_counted_from_stored_records(session: Session):
    trial(session, "A1", record([{"pmid": "1", "type": "RESULT"}]))
    trial(
        session,
        "A2",
        record(
            [{"pmid": "1", "type": "DERIVED"}, {"pmid": "2", "type": "DERIVED"}],
            [{"url": "https://www.statnews.com/a"}, {"url": "https://sponsor.example/b"}],
        ),
    )
    trial(session, "A3", record([{"pmid": "9", "type": "BACKGROUND"}]))
    trial(session, "A4", {"protocolSection": {}})
    # In the other set, so not counted here.
    trial(
        session,
        "C1",
        record([{"pmid": "7", "type": "RESULT"}]),
        overall_status="COMPLETED",
        completion_date="2025-06",
        completion_date_type="ACTUAL",
        has_results=True,
    )

    counted = count_references(session, ACTIVE)

    assert counted.trials == 4
    assert (counted.with_sponsor_paper, counted.with_registry_paper) == (1, 1)
    assert (counted.with_either, counted.with_background_only) == (2, 1)
    # Paper 1 is the sponsor's once; paper 2 is the only other.
    assert (counted.sponsor_papers, counted.registry_papers) == (1, 1)
    assert (counted.with_link, counted.links) == (1, 2)
    assert (counted.with_listed_link, counted.listed_links) == (1, 1)
    assert counted.domains == {"statnews.com": 1, "sponsor.example": 1}
    assert [name for name, _ in references_in(session, COMPLETED)] == ["C1"]


def test_a_set_the_command_does_not_know_is_refused_with_the_list(session: Session):
    """Scenario: A set the command does not know"""
    with pytest.raises(UnknownSet, match=f"{ACTIVE}, {COMPLETED}"):
        count_references(session, "successful")
