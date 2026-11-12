"""The seeded example, end to end: from an article URL to a built page.

Every step runs for real except the outside world: registries replay recorded
responses, the model is scripted, and the article text is synthetic. The site is
built by Astro from the export this test writes.
"""

import json
import os
import subprocess
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from sqlalchemy.orm import Session

from thenwhat.claims.entities import add_synonym
from thenwhat.decide.core import BackendAnswer
from thenwhat.domain import (
    ClaimStatus,
    EventType,
    EvidenceStage,
    ReviewState,
    TrialPhase,
    TrialState,
)
from thenwhat.events.fetch import fetch_claim
from thenwhat.events.manual import add_manual_event
from thenwhat.export.build import write_export
from thenwhat.extract.service import draft_claim_from_article
from thenwhat.llm.client import Llm, LlmSettings
from thenwhat.resolve.service import resolve_claim
from thenwhat.review.queue import confirm_stage, decide_item, pending_items
from thenwhat.sources.clinicaltrials import ClinicalTrials
from thenwhat.sources.crossref import Crossref
from thenwhat.sources.europepmc import EuropePmc

NOW = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
REPOSITORY = Path(__file__).resolve().parents[2]
SITE = REPOSITORY / "site"
SEED = json.loads((REPOSITORY / "data" / "seed" / "tooth-regrowth-usag1.json").read_text())
SLUG = "tooth-regrowth-usag1"
DOI = "10.1126/sciadv.abf1798"
CONTACT = "ops@thenwhat.test"

# Written for this test. The real article's text is never stored, here or anywhere.
SYNTHETIC_ARTICLE = (
    "A university says its researchers grew new teeth in mice with one dose of an antibody "
    "against a protein called USAG-1. The paper is in Science Advances "
    "(doi 10.1126/sciadv.abf1798). "
    "The team says tests in other animals such as pigs and dogs come next."
)
DRAFT: dict[str, Any] = {
    "headline": SEED["claim"]["headline"],
    "summary": SEED["claim"]["summary"],
    "intervention": SEED["claim"]["intervention"],
    "intervention_synonyms": ["USAG-1 neutralizing antibody"],
    "indication": SEED["claim"]["indication"],
    "paper_title": SEED["origin_paper"]["title"],
    "paper_doi": DOI,
    "entities": [{"type": "institution", "name": "Kyoto University"}],
    "promises": ["tests in other animals such as pigs and dogs next"],
}


class Scoring:
    name = "fake"

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        rest = 0.1 / (len(options) - 1)
        return BackendAnswer(options[0], {o: 0.9 if o == options[0] else rest for o in options})


def registries(fixture_json) -> httpx.MockTransport:
    """ClinicalTrials.gov, Crossref and Europe PMC, answering from recordings."""
    work = fixture_json("crossref/work_sciadv_abf1798.json")
    paper = fixture_json("europepmc/paper_sciadv_abf1798.json")
    citing = fixture_json("europepmc/citing_sciadv_abf1798_page1.json")
    nothing = {"hitCount": 0, "resultList": {"result": []}}

    def answer(request: httpx.Request) -> httpx.Response:
        if request.url.host == "clinicaltrials.gov":
            # Recorded on 2026-11-11: no trial matches any of the claim's names.
            return httpx.Response(200, json={"studies": []})
        if request.url.host == "api.crossref.org":
            found = request.url.path.lower() == f"/works/{DOI}"
            return httpx.Response(200, json=work) if found else httpx.Response(404)
        query = request.url.params["query"]
        if query.startswith("DOI:"):
            return httpx.Response(200, json=paper if DOI in query else nothing)
        first_page = request.url.params.get("cursorMark") == "*"
        return httpx.Response(200, json=citing if first_page else nothing)

    return httpx.MockTransport(answer)


def test_seeded_example_round_trips_from_article_url_to_built_page(
    session: Session, fixture_json, fake_time, tmp_path: Path
):
    web = registries(fixture_json)
    trials = ClinicalTrials(session, contact_email=CONTACT, transport=web, time=fake_time)
    crossref = Crossref(session, contact_email=CONTACT, transport=web, time=fake_time)
    literature = EuropePmc(session, contact_email=CONTACT, transport=web, time=fake_time)

    # 1. Article URL to a pending draft.
    def respond(messages, info) -> ModelResponse:
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, DRAFT)])

    llm = Llm(
        session,
        LlmSettings("test:scripted", Decimal("10"), Decimal("3"), Decimal("15")),
        model=FunctionModel(respond),
        now=lambda: NOW,
    )
    article = SEED["articles"][0]
    claim = draft_claim_from_article(
        session,
        llm,
        text=SYNTHETIC_ARTICLE,
        slug=SLUG,
        vertical="dental-regeneration",
        url=article["url"],
        outlet=article["outlet"],
        title=article["title"],
        published_date=date.fromisoformat(article["published_date"]),
    )
    assert claim.review_state is ReviewState.PENDING

    # 2. The operator approves the draft and adds the names the compound goes by.
    decide_item(session, "claim", claim.id, ReviewState.APPROVED, now=NOW)
    for synonym in ("TRG035", "USAG-1"):
        add_synonym(session, SLUG, SEED["claim"]["intervention"], synonym)
    confirm_stage(session, SLUG, EvidenceStage.ANIMAL, now=NOW)

    # 3. Resolve: no trial on ClinicalTrials.gov, and the paper's DOI is found.
    candidates = resolve_claim(
        session, claim, trials=trials, dois=crossref, backend=Scoring(), now=NOW
    )
    assert [(c.source_name, c.external_id) for c in candidates] == [("crossref", DOI)]
    for item in pending_items(session, claim_slug=SLUG, kind="match"):
        decide_item(session, "match", item.id, ReviewState.APPROVED, now=NOW)

    # 4. The trial is in a registry with no client, so its events are entered by hand.
    for entry in SEED["events"]:
        add_manual_event(
            session,
            SLUG,
            type=EventType(entry["type"]),
            event_date=date.fromisoformat(entry["event_date"]),
            source_url=entry["source_url"],
            source_name=entry["source_name"],
            external_id=entry["external_id"],
            trial_phases=[TrialPhase(phase) for phase in entry["trial_phases"]],
            trial_state=TrialState(entry["trial_state"]) if entry["trial_state"] else None,
            summary=entry["summary"],
            now=NOW,
        )

    # 5. Fetch: citing papers that name the intervention become pending follow-ups.
    created = fetch_claim(
        session,
        claim,
        trials=trials,
        literature=literature,
        notices=crossref,
        threshold=0.95,
        now=NOW,
    )
    follow_ups = [event for event in created if event.type is EventType.FOLLOWUP_PAPER]
    assert [event.external_id for event in follow_ups] == ["10.1002/cre2.70301"]

    # 6. The operator reviews everything that is pending.
    for item in pending_items(session, claim_slug=SLUG, kind="event"):
        decide_item(session, "event", item.id, ReviewState.APPROVED, now=NOW)
    assert pending_items(session, claim_slug=SLUG) == []
    assert claim.current_status is ClaimStatus.PHASE_1

    # 7. Export, then build the site from that file alone.
    export_file = tmp_path / "export.json"
    export = write_export(session, export_file, now=NOW)
    [exported] = export.claims
    assert len(exported.events) == 3

    dist = tmp_path / "dist"
    build = subprocess.run(
        ["npx", "astro", "build", "--outDir", str(dist)],
        cwd=SITE,
        env=os.environ | {"EXPORT_FILE": str(export_file), "ASTRO_TELEMETRY_DISABLED": "1"},
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert build.returncode == 0, build.stdout[-2000:] + build.stderr[-2000:]

    # 8. The published page shows the status and links every event to its source.
    page = (dist / SLUG / "index.html").read_text()
    assert SEED["claim"]["headline"] in page
    assert "Phase 1 trial" in page
    assert "basis of status" in page
    for event in exported.events:
        assert event.source_url.replace("&", "&amp;") in page, event.source_url
    assert article["url"] in page
    assert SYNTHETIC_ARTICLE[:40] not in page
    assert (dist / "og" / f"{SLUG}.png").stat().st_size > 10_000
