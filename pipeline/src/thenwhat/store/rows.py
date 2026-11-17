"""From a store record back to what finds or creates its row in Postgres: one function a
kind. Pure: a parent is still named by its natural key (a `*Ref` below), and `place.py`
turns those into row ids against a session.

What the store does not keep cannot come back, and is filled the one way Postgres
allows: an article lead's raw result is empty, a merge brought back has no record of the
rows it moved (so `claim unmerge` cannot undo it), a claim's registry search is not due.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from thenwhat.db.models import (
    ArticleLead,
    Base,
    Claim,
    ClaimChange,
    ClaimTerm,
    DecisionLog,
    Entity,
    EntityArticle,
    EntityMatch,
    EntitySubstance,
    EvidenceEvent,
    FailureFlag,
    LinkLead,
    LinkLeadLabel,
    LinkLeadLink,
    LinkShare,
    LlmUsage,
    MeasureClaim,
    MeasureDaily,
    OrganisationRecord,
    OutletIcon,
    PaperRecord,
    Promise,
    Reading,
    RegistryLoad,
    RegistryTrial,
    ReportedStatement,
    SourceArticle,
    TermRecord,
    TrialRead,
    WorkEntry,
)
from thenwhat.store.form import KEY_JOIN, Record, amount, date_of, moment

# --- natural references, resolved to ids by place.py -----------------------------------


@dataclass(frozen=True, slots=True)
class ClaimRef:
    slug: str


@dataclass(frozen=True, slots=True)
class ArticleRef:
    slug: str
    url_key: str
    # A lead's article is found if it is there; a promise's must be.
    required: bool = True


@dataclass(frozen=True, slots=True)
class EntityRef:
    slug: str
    type: str
    name: str


@dataclass(frozen=True, slots=True)
class MatchRef:
    entity: EntityRef
    source_name: str
    external_id: str


@dataclass(frozen=True, slots=True)
class EventRef:
    slug: str
    dedupe_key: str


@dataclass(frozen=True, slots=True)
class LeadRef:
    url_key: str


@dataclass(frozen=True, slots=True)
class TrialRef:
    registry_name: str
    external_id: str


@dataclass(frozen=True, slots=True)
class ReadRef:
    source_name: str
    trial_id: str


@dataclass(frozen=True, slots=True)
class DecisionRef:
    """A decision log reference in natural-key form (`records.natural_ref`)."""

    text: str


Ref = (
    ClaimRef | ArticleRef | EntityRef | MatchRef | EventRef | LeadRef | TrialRef | ReadRef
) | DecisionRef


@dataclass(frozen=True, slots=True)
class Row:
    """A Postgres row named by what finds it (`key`) and what it holds besides
    (`values`). Either may hold a `Ref` in place of a row id. A key with `url_key` finds
    the article or article lead of its parent whose address has that key. `create`
    false: the row must already be there (an action changes a claim, never adds one)."""

    model: type[Base]
    key: dict[str, Any]
    values: dict[str, Any] = field(default_factory=dict)
    create: bool = True


def trial_ref(record_key: str) -> TrialRef:
    registry, _, number = record_key.partition(KEY_JOIN)
    return TrialRef(registry, number)


def record_ref(kind: str, record_key: str) -> ClaimRef | TrialRef:
    """A record named by kind and natural key, as the ledger and screening name one."""
    if kind == "claim":
        return ClaimRef(record_key)
    if kind == "registry_trial":
        return trial_ref(record_key)
    raise ValueError(f"No record of kind {kind!r} is named by natural key.")


def _entity(b: Mapping[str, Any], prefix: str = "entity_") -> EntityRef:
    return EntityRef(b["slug"], b[f"{prefix}type"], b[f"{prefix}name"])


def _reviewed(b: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "review_state": b.get("review_state", "pending"),
        "reviewed_at": moment(b.get("reviewed_at")),
        "reviewed_by": b.get("reviewed_by"),
    }


# --- claims and what was said of them ------------------------------------------------


def claim_row(record: Record) -> Row:
    """A claim's own fields. Its origin is not a Postgres column."""
    b = record.body
    return Row(
        Claim,
        {"slug": b["slug"]},
        {
            "headline": b["headline"],
            "summary": b["summary"],
            "vertical": b["vertical"],
            "approach": b.get("approach"),
            "indication": b["indication"],
            "first_reported_date": date_of(b.get("first_reported_date")),
            "evidence_stage": b.get("evidence_stage"),
            "current_status": b.get("current_status", "no_trial_found"),
            "overlay_years": b.get("overlay_years"),
            "status_updated_at": moment(b.get("status_updated_at")),
            **_reviewed(b),
            "awaiting_audit_at": moment(b.get("awaiting_audit_at")),
            "created_at": moment(b["created_at"]),
        },
    )


def action_rows(record: Record) -> list[Row]:
    """An action as the change it makes to its claim in Postgres. A merge or a rename is
    also a `claim_change`, found again by its claim, kind and time."""
    b = record.body
    action, at = b["action"], moment(b.get("at"))
    claim = {"slug": b["slug"]}
    if action == "publish":
        return [Row(Claim, claim, {"published_at": at}, create=False)]
    if action == "archive":
        return [Row(Claim, claim, {"archived_at": at, "archive_reason": b["reason"]}, create=False)]
    if action == "merge":
        into = ClaimRef(b["into_slug"])
        return [
            # As the store's merge does: an archive already stated stands.
            Row(
                Claim,
                claim,
                {
                    "merged_into_id": into,
                    "archived_at": ("keep", at),
                    "archive_reason": ("keep", f"merged into {b['into_slug']}"),
                },
                create=False,
            ),
            Row(
                ClaimChange,
                {"claim_id": ClaimRef(b["slug"]), "kind": "merge", "decided_at": at},
                {
                    "into_claim_id": into,
                    "decided_by": b["decided_by"],
                    "record": {"names_gained": list(b.get("gains", []))},
                },
            ),
        ]
    if action == "rename":
        return [
            Row(
                ClaimChange,
                {
                    "claim_id": ClaimRef(b.get("new_slug", b["slug"])),
                    "kind": "rename",
                    "decided_at": at,
                },
                {
                    "old_name": b.get("old_name"),
                    "new_name": b.get("new_name"),
                    "former_slug": b["slug"] if "new_slug" in b else None,
                    "decided_by": b["decided_by"],
                },
            )
        ]
    raise ValueError(f"Postgres keeps no {action!r} action: the store alone holds it.")


def source_article_row(record: Record) -> Row:
    b = record.body
    return Row(
        SourceArticle,
        {"claim_id": ClaimRef(b["slug"]), "url_key": b["url_key"]},
        {
            "url": b["url"],
            "outlet": b["outlet"],
            "title": b["title"],
            "published_date": date_of(b["published_date"]),
            "content_hash": b.get("content_hash"),
            "archive_url": b.get("archive_url"),
        },
    )


def promise_row(record: Record) -> Row:
    b = record.body
    article = ArticleRef(b["slug"], b["url_key"])
    return Row(
        Promise,
        {"source_article_id": article, "description": b["description"]},
        {"claim_id": ClaimRef(b["slug"]), "parsed_date": date_of(b.get("parsed_date"))},
    )


def reported_statement_row(record: Record) -> Row:
    b = record.body
    return Row(
        ReportedStatement,
        {"source_article_id": ArticleRef(b["slug"], b["url_key"]), "text_key": b["text_key"]},
        {
            "claim_id": ClaimRef(b["slug"]),
            "text": b["text"],
            "kind": b["kind"],
            "firmness": b["firmness"],
            "speaker": b["speaker"],
            "basis": b["basis"],
            "confidence": b["confidence"],
            "decision_ref": DecisionRef(b["decision_ref"]),
            "article_read_at": moment(b["article_read_at"]),
            **_reviewed(b),
            "created_at": moment(b["created_at"]),
        },
    )


# --- entities, matches and terms --------------------------------------------------------


def entity_row(record: Record) -> Row:
    b = record.body
    return Row(
        Entity,
        {"claim_id": ClaimRef(b["slug"]), "type": b["type"], "name": b["name"]},
        {
            "synonyms": list(b.get("synonyms", [])),
            "search_phrases": list(b.get("search_phrases", [])),
            "is_origin_paper": bool(b.get("is_origin_paper", 0)),
            "doi": b.get("doi"),
            "named_by": list(b.get("named_by", ["article"])),
        },
    )


def entity_article_row(record: Record) -> Row:
    b = record.body
    return Row(
        EntityArticle,
        {"entity_id": _entity(b), "source_article_id": ArticleRef(b["slug"], b["url_key"])},
    )


def entity_match_row(record: Record) -> Row:
    b = record.body
    return Row(
        EntityMatch,
        {
            "entity_id": _entity(b),
            "source_name": b["source_name"],
            "external_id": b["external_id"],
        },
        {
            "score": b["score"],
            "record_summary": b.get("record_summary"),
            "record_facts": b.get("record_facts"),
            "reasons": list(b.get("reasons", [])),
            **_reviewed(b),
            "created_at": moment(b["created_at"]),
        },
    )


def claim_term_row(record: Record) -> Row:
    b = record.body
    return Row(
        ClaimTerm,
        {
            "claim_id": ClaimRef(b["slug"]),
            "role": b["role"],
            "source_name": b["source_name"],
            "external_id": b["external_id"],
        },
        {
            "label": b["label"],
            "score": b.get("score"),
            "fit": b.get("fit"),
            "reasons": list(b.get("reasons", [])),
            **_reviewed(b),
            "created_at": moment(b["created_at"]),
        },
    )


def source_record_rows(record: Record) -> list[Row]:
    """A term's, an organisation's or a paper's record. A substance's record has no row
    of its own in Postgres: it is part of each `entity_substance` (`entity_substance_row`)."""
    b = record.body
    kind = b["kind"]
    fetched_at = moment(b["fetched_at"])
    if kind == "term":
        key = {"source_name": b["source_name"], "external_id": b["external_id"]}
        values = {"url": b["url"], "payload": b["body"], "fetched_at": fetched_at}
        return [Row(TermRecord, key, values)]
    if kind == "organisation":
        key = {"source_name": b["source_name"], "external_id": b["external_id"]}
        values = {"url": b["url"], "payload": b["body"], "fetched_at": fetched_at}
        return [Row(OrganisationRecord, key, values)]
    if kind == "paper":
        values = {
            "source_name": b["source_name"],
            "pubmed_id": b.get("pubmed_id"),
            "payload": b.get("body"),
            "fetched_at": fetched_at,
        }
        return [Row(PaperRecord, {"identifier": b["external_id"]}, values)]
    if kind == "substance":
        return []
    raise ValueError(f"Unknown kind of source record: {kind!r}")


def entity_substance_row(record: Record, *, substance: Record, payload: Any) -> Row:
    """An intervention's substance, with the substance's own record (address and payload)
    that the store keeps once as a `source_record`."""
    b = record.body
    return Row(
        EntitySubstance,
        {"entity_id": _entity(b)},
        {
            "source_name": b["source_name"],
            "external_id": b["external_id"],
            "codes": list(b.get("codes", [])),
            "fetched_at": moment(b["fetched_at"]),
            "url": substance.body["url"],
            "payload": payload,
        },
    )


# --- evidence ---------------------------------------------------------------------------


def evidence_event_row(record: Record, *, payload: Any) -> Row:
    """An event, with the payload its checksum names. The content checksum is the store's
    and is worked out again from the fields whenever it is needed."""
    b = record.body
    match = None
    if "match_entity_type" in b:
        match = MatchRef(
            _entity(b, "match_entity_"), b["match_source_name"], b["match_external_id"]
        )
    return Row(
        EvidenceEvent,
        {"claim_id": ClaimRef(b["slug"]), "dedupe_key": b["dedupe_key"]},
        {
            "entity_match_id": match,
            "type": b["type"],
            "event_date": date_of(b["event_date"]),
            "date_basis": b.get("date_basis"),
            "source_name": b["source_name"],
            "source_url": b["source_url"],
            "external_id": b["external_id"],
            "trial_phases": b.get("trial_phases"),
            "trial_state": b.get("trial_state"),
            "regulatory_outcome": b.get("regulatory_outcome"),
            "summary": b["summary"],
            "confidence": b["confidence"],
            "raw_payload": payload,
            "fetched_at": moment(b["fetched_at"]),
            **_reviewed(b),
            "created_at": moment(b["created_at"]),
        },
    )


def failure_flag_row(record: Record) -> Row:
    b = record.body
    return Row(
        FailureFlag,
        {"claim_id": ClaimRef(b["slug"]), "trial_external_id": b["trial_external_id"]},
        {
            "evidence_event_id": EventRef(b["slug"], b["dedupe_key"]),
            "source_url": b["source_url"],
            "created_at": moment(b["created_at"]),
        },
    )


def trial_read_rows(record: Record) -> list[Row]:
    """A read and its readings, which Postgres keeps as rows of their own."""
    b = record.body
    read = ReadRef(b["source_name"], b["trial_id"])
    rows = [
        Row(
            TrialRead,
            {"source_name": b["source_name"], "trial_id": b["trial_id"]},
            {
                "input_hash": b["input_hash"],
                "instructions_version": b["instructions_version"],
                "provider": b["provider"],
                "model": b["model"],
                "refusals": list(b.get("refusals", [])),
                "read_at": moment(b["read_at"]),
            },
        )
    ]
    for reading in b.get("readings", []):
        rows.append(
            Row(
                Reading,
                {"trial_read_id": read, "outcome": reading["outcome"], "kind": reading["kind"]},
                {
                    "field": reading["field"],
                    "words": reading["words"],
                    "number": reading.get("number"),
                    "unit": reading.get("unit"),
                    "code": reading.get("code"),
                    "confidence": reading["confidence"],
                    "decided_by": reading["decided_by"],
                },
            )
        )
    return rows


# --- the registry corpus ------------------------------------------------------------------


def registry_trial_row(record: Record, *, payload: Any) -> Row:
    """A trial with the payload its checksum names. The search's joined names are the
    store's own; every other column comes back as the store holds it."""
    b = record.body
    has_results = b.get("has_results")
    return Row(
        RegistryTrial,
        {"registry_name": b["registry_name"], "external_id": b["external_id"]},
        {
            "title": b["title"],
            "conditions": list(b.get("conditions", [])),
            "interventions": list(b.get("interventions", [])),
            "phases": list(b.get("phases", [])),
            "overall_status": b.get("overall_status"),
            "start_date": b.get("start_date"),
            "sponsor_class": b.get("sponsor_class"),
            "search_name": b.get("search_name"),
            "search_indication": b.get("search_indication"),
            "start_date_type": b.get("start_date_type"),
            "last_update_posted": date_of(b.get("last_update_posted")),
            "study_first_posted": date_of(b.get("study_first_posted")),
            "primary_completion_date": b.get("primary_completion_date"),
            "primary_completion_date_type": b.get("primary_completion_date_type"),
            "completion_date": b.get("completion_date"),
            "completion_date_type": b.get("completion_date_type"),
            "results_first_posted": date_of(b.get("results_first_posted")),
            "has_results": None if has_results is None else bool(has_results),
            "acronym": b.get("acronym"),
            "lead_sponsor_name": b.get("lead_sponsor_name"),
            "raw_payload": payload,
            "fetched_at": moment(b["fetched_at"]),
        },
    )


def registry_load_row(record: Record) -> Row:
    b = record.body
    return Row(
        RegistryLoad,
        {"registry_name": b["registry_name"], "condition": b["condition"]},
        {"loaded_from": moment(b["loaded_from"]), "completed_at": moment(b["completed_at"])},
    )


def article_lead_row(record: Record) -> Row:
    b = record.body
    return Row(
        ArticleLead,
        {"registry_trial_id": TrialRef(b["registry_name"], b["trial_id"]), "url_key": b["url_key"]},
        {
            "url": b["url"],
            "outlet": b["outlet"],
            "title": b["title"],
            "published_date": date_of(b.get("published_date")),
            "outlet_kind": b["outlet_kind"],
            "source_name": b["source_name"],
            "search_query": b["search_query"],
            "raw_result": {},
            "fetched_at": moment(b["fetched_at"]),
        },
    )


# --- link leads ----------------------------------------------------------------------------


def link_lead_row(record: Record) -> Row:
    b = record.body
    slug = b.get("claim_slug")
    return Row(
        LinkLead,
        {"url_key": b["url_key"]},
        {
            "url_key_version": b["url_key_version"],
            "url": b["url"],
            "outlet": b["outlet"],
            "outlet_kind": b["outlet_kind"],
            "title": b["title"],
            "first_shared_at": moment(b["first_shared_at"]),
            "screen_outcome": b.get("screen_outcome"),
            "triage_score": b.get("triage_score"),
            "triage_version": b.get("triage_version"),
            "read_outcome": b.get("read_outcome"),
            "read_detail": b.get("read_detail"),
            "claim_id": None if slug is None else ClaimRef(slug),
            # As the store's merge ties it: the claim's article at the lead's own address.
            "source_article_id": (
                None if slug is None else ArticleRef(slug, b["url_key"], required=False)
            ),
        },
    )


def link_share_row(record: Record) -> Row:
    b = record.body
    return Row(
        LinkShare,
        {
            "link_lead_id": LeadRef(b["lead_url_key"]),
            "platform": b["platform"],
            "community": b["community"],
            "shared_at": moment(b["shared_at"]),
        },
        {"score": b.get("score", 0), "item_number": b.get("item_number")},
    )


def link_lead_link_row(record: Record) -> Row:
    b = record.body
    return Row(
        LinkLeadLink,
        {
            "link_lead_id": LeadRef(b["lead_url_key"]),
            "record_kind": b["record_kind"],
            "record_id": record_ref(b["record_kind"], b["record_key"]),
            "reason": b["reason"],
        },
    )


def link_lead_label_row(record: Record) -> Row:
    b = record.body
    return Row(
        LinkLeadLabel,
        {"link_lead_id": LeadRef(b["lead_url_key"]), "labelled_by": b["labelled_by"]},
        {"label": b["label"], "labelled_at": moment(b["labelled_at"])},
    )


# --- decisions, spend, measurements, ledger, icons ------------------------------------------


def decision_row(record: Record) -> Row:
    """A decision is found again by its place in the run, which the migration takes from
    its Postgres id."""
    b = record.body
    return Row(
        DecisionLog,
        {"id": b["seq"]},
        {
            "step": b["step"],
            "input_ref": DecisionRef(b["input_ref"]),
            "backend": b["backend"],
            "model": b.get("model"),
            "options": b.get("options", []),
            "output": b.get("output"),
            "confidence": b.get("confidence"),
            "error": b.get("error"),
            "human_label": b.get("human_label"),
            "created_at": moment(b["created_at"]),
        },
    )


def usage_row(record: Record) -> Row:
    b = record.body
    return Row(
        LlmUsage,
        {"id": b["seq"]},
        {
            "purpose": b["purpose"],
            "model": b["model"],
            "input_tokens": b["input_tokens"],
            "output_tokens": b["output_tokens"],
            "cost_usd": amount(b["cost_usd"]),
            "created_at": moment(b["created_at"]),
        },
    )


def measure_daily_row(record: Record) -> Row:
    b = record.body
    return Row(
        MeasureDaily,
        {
            "day": date_of(b["day"]),
            "step": b["step"],
            "step_version": b["step_version"],
            "writer": b["writer"],
            "outcome": b["outcome"],
        },
        {
            "spans": b["spans"],
            "records": b["records"],
            "reused": b["reused"],
            "ran_seconds": b["ran_seconds"],
            "waited_seconds": b["waited_seconds"],
            "waited_by_cause": b.get("waited_by_cause", {}),
            "requests_by_source": b.get("requests_by_source", {}),
            "tokens_in": b["tokens_in"],
            "tokens_out": b["tokens_out"],
            "cost_usd": amount(b["cost_usd"]),
            "inner_cost_usd": amount(b["inner_cost_usd"]),
            "rows_written": b["rows_written"],
        },
    )


def measure_claim_row(record: Record) -> Row:
    b = record.body
    return Row(
        MeasureClaim,
        {"claim_id": ClaimRef(b["slug"])},
        {
            "first_seen_at": moment(b["first_seen_at"]),
            "last_step_at": moment(b["last_step_at"]),
            "spans": b["spans"],
            "ran_seconds": b["ran_seconds"],
            "waited_seconds": b["waited_seconds"],
            "cost_usd": amount(b["cost_usd"]),
        },
    )


def work_entry_row(record: Record) -> Row:
    b = record.body
    return Row(
        WorkEntry,
        {
            "record_kind": b["record_kind"],
            "record_id": record_ref(b["record_kind"], b["record_key"]),
            "step": b["step"],
            "step_version": b["step_version"],
        },
        {
            "outcome": b["outcome"],
            "attempts": b["attempts"],
            "requests_used": b["requests_used"],
            "fingerprint": b["fingerprint"],
            "stale": bool(b.get("stale", 0)),
            "error": b.get("error"),
            "last_attempt_at": moment(b["last_attempt_at"]),
        },
    )


def outlet_icon_row(record: Record) -> Row:
    b = record.body
    content = b.get("content_hex")
    return Row(
        OutletIcon,
        {"domain": b["domain"]},
        {
            "icon_url": b.get("icon_url"),
            "media_type": b.get("media_type"),
            "content": None if content is None else bytes.fromhex(content),
            "fetched_at": moment(b["fetched_at"]),
        },
    )


# Kinds whose row needs nothing but the record. A payload is not a row: the record that
# names it carries it back. The store's own kinds (a lead's reading, a work slice, an
# unlisted domain's count) have no Postgres table.
SIMPLE: Mapping[str, Callable[[Record], Row]] = {
    "claim": claim_row,
    "source_article": source_article_row,
    "promise": promise_row,
    "reported_statement": reported_statement_row,
    "entity": entity_row,
    "entity_article": entity_article_row,
    "entity_match": entity_match_row,
    "claim_term": claim_term_row,
    "failure_flag": failure_flag_row,
    "registry_load": registry_load_row,
    "article_lead": article_lead_row,
    "link_lead": link_lead_row,
    "link_share": link_share_row,
    "link_lead_link": link_lead_link_row,
    "link_lead_label": link_lead_label_row,
    "decision": decision_row,
    "usage": usage_row,
    "measure_daily": measure_daily_row,
    "measure_claim": measure_claim_row,
    "work_entry": work_entry_row,
    "outlet_icon": outlet_icon_row,
}
