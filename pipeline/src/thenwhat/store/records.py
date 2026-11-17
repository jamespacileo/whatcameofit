"""Today's rows in the store's natural-key form: one function a kind of record.

Each function takes a Postgres row and whatever related rows its key needs, already
loaded, and gives the staged record of `store/README.md` with exactly the fields
`store/merge.sql` reads. No row id crosses: a parent is named by its natural key, a raw
payload by its checksum. Nothing here reads a database; `gather.py` does that.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from thenwhat.backfill.address import KEY_VERSION
from thenwhat.db.models import (
    ArticleLead,
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
from thenwhat.domain import OutletKind, ScreenOutcome
from thenwhat.sources.people import sponsored_by_a_person, without_people
from thenwhat.store.form import (
    Record,
    body,
    content_sha256,
    day,
    flag,
    key_of,
    money,
    payload_of,
    when,
)


def _text(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


# --- references a decision or a statement makes to another record -------------------


@dataclass(frozen=True, slots=True)
class Names:
    """Natural keys of the rows a decision log reference can name by id. A reference to
    a row not given here is left as it is."""

    claims: Mapping[int, str] = field(default_factory=dict)  # id -> slug
    articles: Mapping[int, tuple[str, str]] = field(default_factory=dict)  # slug, url_key
    matches: Mapping[int, tuple[str, str, str, str, str]] = field(default_factory=dict)
    leads: Mapping[int, str] = field(default_factory=dict)  # id -> url_key


def natural_ref(ref: str, names: Names) -> str:
    """A decision log reference with its row id replaced by the row's natural key:

    - `claim:<id>[:<rest>]` -> `claim:<slug>[:<rest>]` (a slug holds no colon)
    - `source_article:<id>:statement:<n>` -> `source_article:<slug>|<url_key>:statement:<n>`
    - `entity_match:<id>` -> `entity_match:<slug>|<type>|<name>|<source>|<external id>`
    - `link_lead:<id>` -> `link_lead:<url_key>`

    Any other reference (a lookup's, a corpus audit's) names no row by id and is kept."""
    kind, _, rest = ref.partition(":")
    number, colon, tail = rest.partition(":")
    if not number.isdigit():
        return ref
    row = int(number)
    if kind == "claim" and row in names.claims:
        return f"claim:{names.claims[row]}{colon}{tail}"
    if kind == "source_article" and row in names.articles:
        return f"source_article:{key_of(*names.articles[row])}{colon}{tail}"
    if kind == "entity_match" and row in names.matches and not colon:
        return f"entity_match:{key_of(*names.matches[row])}"
    if kind == "link_lead" and row in names.leads and not colon:
        return f"link_lead:{names.leads[row]}"
    return ref


# --- claims and what was said of them ------------------------------------------------


def claim_origin(claim: Claim, *, from_link_lead: bool) -> str:
    """Where a claim began. Postgres does not record it: a seeded claim is the seed's,
    one a link lead is tied to came from a backfill's read, any other was entered."""
    if _text(claim.reviewed_by) == "seed":
        return "seed"
    return "backfill" if from_link_lead else "entry"


def claim_record(claim: Claim, *, origin: str) -> Record:
    """A claim's own fields. Its publication, archive and merge are actions
    (`claim_actions`); its search being due again is not kept (store-tables.md).

    A merged claim carries no status time and no audit mark: once the store holds its
    merge, its slug names the claim it went into (`claim_key`), so a second push would
    give that claim the merged one's later status and its hold."""
    merged = claim.merged_into_id is not None
    return Record(
        "claim",
        claim.slug,
        body(
            slug=claim.slug,
            headline=claim.headline,
            summary=claim.summary,
            vertical=claim.vertical,
            approach=claim.approach,
            indication=claim.indication,
            first_reported_date=day(claim.first_reported_date),
            evidence_stage=_text(claim.evidence_stage),
            current_status=_text(claim.current_status),
            overlay_years=claim.overlay_years,
            status_updated_at=None if merged else when(claim.status_updated_at),
            origin=origin,
            review_state=_text(claim.review_state),
            reviewed_at=when(claim.reviewed_at),
            reviewed_by=_text(claim.reviewed_by),
            awaiting_audit_at=None if merged else when(claim.awaiting_audit_at),
            created_at=when(claim.created_at),
        ),
    )


def claim_actions(
    claim: Claim, changes: Sequence[ClaimChange], slugs: Mapping[int, str]
) -> list[Record]:
    """What the operator and the export did to a claim, as the store's actions: its
    publication, its archive, a merge into another claim that was not undone, and each
    rename. `slugs` names the claim a merge went into.

    A merged claim's publication and archive are left out: its slug comes to name the
    claim it went into, which a second push would publish or archive. The merge archives
    it in the store."""
    merged = claim.merged_into_id is not None
    actions: list[Record] = []
    if claim.published_at is not None and not merged:
        actions.append(
            Record(
                "action",
                key_of("publish", claim.slug),
                body(action="publish", slug=claim.slug, at=when(claim.published_at)),
            )
        )
    if claim.archived_at is not None and not merged:
        # Postgres does not record who archived a claim, and an assistant's audit
        # archives the same way a person does; a decision no one recorded as a person's
        # is never stored as one.
        actions.append(
            Record(
                "action",
                key_of("archive", claim.slug),
                body(
                    action="archive",
                    slug=claim.slug,
                    reason=claim.archive_reason,
                    decided_by="assistant",
                    at=when(claim.archived_at),
                ),
            )
        )
    for change in sorted(changes, key=lambda change: (change.decided_at, change.id)):
        if change.kind == "merge" and change.undone_at is None:
            if claim.merged_into_id is None or change.into_claim_id is None:
                continue
            actions.append(
                Record(
                    "action",
                    key_of("merge", claim.slug),
                    body(
                        action="merge",
                        slug=claim.slug,
                        into_slug=slugs[change.into_claim_id],
                        gains=list((change.record or {}).get("names_gained", [])),
                        decided_by=_text(change.decided_by),
                        at=when(change.decided_at),
                    ),
                )
            )
        elif change.kind == "rename":
            named = change.former_slug or claim.slug
            actions.append(
                Record(
                    "action",
                    key_of("rename", named, when(change.decided_at)),
                    body(
                        action="rename",
                        slug=named,
                        new_slug=claim.slug if change.former_slug else None,
                        old_name=change.old_name,
                        new_name=change.new_name,
                        decided_by=_text(change.decided_by),
                        at=when(change.decided_at),
                    ),
                )
            )
    return actions


def source_article_record(article: SourceArticle, *, slug: str, url_key: str) -> Record:
    return Record(
        "source_article",
        key_of(slug, url_key),
        body(
            slug=slug,
            url_key=url_key,
            url=article.url,
            outlet=article.outlet,
            title=article.title,
            published_date=day(article.published_date),
            content_hash=article.content_hash,
            archive_url=article.archive_url,
        ),
    )


def promise_record(promise: Promise, *, slug: str, url_key: str) -> Record:
    return Record(
        "promise",
        key_of(slug, url_key, promise.description),
        body(
            slug=slug,
            url_key=url_key,
            description=promise.description,
            parsed_date=day(promise.parsed_date),
        ),
    )


def reported_statement_record(
    statement: ReportedStatement, *, slug: str, url_key: str, names: Names
) -> Record:
    return Record(
        "reported_statement",
        key_of(slug, url_key, statement.text_key),
        body(
            slug=slug,
            url_key=url_key,
            text=statement.text,
            text_key=statement.text_key,
            kind=_text(statement.kind),
            firmness=_text(statement.firmness),
            speaker=_text(statement.speaker),
            basis=_text(statement.basis),
            confidence=statement.confidence,
            decision_ref=natural_ref(statement.decision_ref, names),
            article_read_at=when(statement.article_read_at),
            review_state=_text(statement.review_state),
            reviewed_at=when(statement.reviewed_at),
            reviewed_by=_text(statement.reviewed_by),
            created_at=when(statement.created_at),
        ),
    )


# --- entities, matches and terms --------------------------------------------------------


def entity_record(entity: Entity, *, slug: str) -> Record:
    entity_type = _text(entity.type)
    return Record(
        "entity",
        key_of(slug, entity_type, entity.name),
        body(
            slug=slug,
            type=entity_type,
            name=entity.name,
            synonyms=list(entity.synonyms),
            search_phrases=list(entity.search_phrases),
            is_origin_paper=flag(entity.is_origin_paper),
            doi=entity.doi,
            # The store's CHECK knows three spellings: one name, or both in this order.
            named_by=sorted(set(entity.named_by)),
        ),
    )


def _of_entity(entity: Entity, slug: str) -> dict[str, Any]:
    return {"slug": slug, "entity_type": _text(entity.type), "entity_name": entity.name}


def entity_article_record(
    link: EntityArticle, *, entity: Entity, slug: str, url_key: str
) -> Record:
    del link  # the link is its two parents and nothing more
    return Record(
        "entity_article",
        key_of(slug, _text(entity.type), entity.name, url_key),
        body(**_of_entity(entity, slug), url_key=url_key),
    )


def entity_match_record(match: EntityMatch, *, entity: Entity, slug: str) -> Record:
    return Record(
        "entity_match",
        key_of(slug, _text(entity.type), entity.name, match.source_name, match.external_id),
        body(
            **_of_entity(entity, slug),
            source_name=match.source_name,
            external_id=match.external_id,
            score=match.score,
            record_summary=match.record_summary,
            record_facts=match.record_facts,
            reasons=list(match.reasons),
            review_state=_text(match.review_state),
            reviewed_at=when(match.reviewed_at),
            reviewed_by=_text(match.reviewed_by),
            created_at=when(match.created_at),
        ),
    )


def claim_term_record(term: ClaimTerm, *, slug: str) -> Record:
    role = _text(term.role)
    return Record(
        "claim_term",
        key_of(slug, role, term.source_name, term.external_id),
        body(
            slug=slug,
            role=role,
            source_name=term.source_name,
            external_id=term.external_id,
            label=term.label,
            score=term.score,
            fit=_text(term.fit),
            reasons=list(term.reasons),
            review_state=_text(term.review_state),
            reviewed_at=when(term.reviewed_at),
            reviewed_by=_text(term.reviewed_by),
            created_at=when(term.created_at),
        ),
    )


def _source_record(kind: str, source_name: str, external_id: str, **fields: Any) -> Record:
    return Record(
        "source_record",
        key_of(kind, source_name, external_id),
        body(kind=kind, source_name=source_name, external_id=external_id, **fields),
    )


def term_source_record(term: TermRecord) -> Record:
    return _source_record(
        "term",
        term.source_name,
        term.external_id,
        url=term.url,
        body=term.payload,
        fetched_at=when(term.fetched_at),
    )


def organisation_source_record(organisation: OrganisationRecord) -> Record:
    return _source_record(
        "organisation",
        organisation.source_name,
        organisation.external_id,
        url=organisation.url,
        body=organisation.payload,
        fetched_at=when(organisation.fetched_at),
    )


def paper_source_record(paper: PaperRecord) -> Record:
    """A paper's reduced record. One the index does not hold has no body."""
    return _source_record(
        "paper",
        paper.source_name,
        paper.identifier,
        pubmed_id=paper.pubmed_id,
        body=paper.payload,
        fetched_at=when(paper.fetched_at),
    )


def substance_source_record(substance: EntitySubstance) -> Record:
    """A substance's record is large: the store keeps it as a payload, by checksum."""
    return _source_record(
        "substance",
        substance.source_name,
        substance.external_id,
        url=substance.url,
        payload_sha256=payload_of(substance.payload).sha256,
        fetched_at=when(substance.fetched_at),
    )


def entity_substance_record(substance: EntitySubstance, *, entity: Entity, slug: str) -> Record:
    return Record(
        "entity_substance",
        key_of(slug, _text(entity.type), entity.name),
        body(
            **_of_entity(entity, slug),
            source_name=substance.source_name,
            external_id=substance.external_id,
            codes=list(substance.codes),
            fetched_at=when(substance.fetched_at),
        ),
    )


# --- evidence ---------------------------------------------------------------------------


def evidence_event_record(
    event: EvidenceEvent,
    *,
    slug: str,
    match: tuple[Entity, EntityMatch] | None,
    payload_sha256: str | None = None,
) -> Record:
    """An event, its payload named by checksum, and the match it came from named by its
    entity's type and name and the record's source and identifier."""
    phases = None if event.trial_phases is None else list(event.trial_phases)
    fields: dict[str, Any] = {
        "type": _text(event.type),
        "event_date": day(event.event_date),
        "trial_state": _text(event.trial_state),
        "trial_phases": phases,
        "regulatory_outcome": _text(event.regulatory_outcome),
        "external_id": event.external_id,
    }
    matched: dict[str, Any] = {}
    if match is not None:
        entity, entity_match = match
        matched = {
            "match_entity_type": _text(entity.type),
            "match_entity_name": entity.name,
            "match_source_name": entity_match.source_name,
            "match_external_id": entity_match.external_id,
        }
    return Record(
        "evidence_event",
        key_of(slug, event.dedupe_key),
        body(
            slug=slug,
            dedupe_key=event.dedupe_key,
            **matched,
            **fields,
            date_basis=event.date_basis,
            source_name=event.source_name,
            source_url=event.source_url,
            summary=event.summary,
            confidence=event.confidence,
            content_sha256=content_sha256(**fields),
            payload_sha256=payload_sha256 or payload_of(event.raw_payload).sha256,
            fetched_at=when(event.fetched_at),
            review_state=_text(event.review_state),
            reviewed_at=when(event.reviewed_at),
            reviewed_by=_text(event.reviewed_by),
            created_at=when(event.created_at),
        ),
    )


def failure_flag_record(failure: FailureFlag, *, slug: str, dedupe_key: str) -> Record:
    return Record(
        "failure_flag",
        key_of(slug, failure.trial_external_id),
        body(
            slug=slug,
            trial_external_id=failure.trial_external_id,
            dedupe_key=dedupe_key,
            source_url=failure.source_url,
            created_at=when(failure.created_at),
        ),
    )


def _reading(reading: Reading) -> dict[str, Any]:
    return body(
        outcome=reading.outcome,
        kind=_text(reading.kind),
        field=_text(reading.field),
        words=reading.words,
        number=reading.number,
        unit=_text(reading.unit),
        code=_text(reading.code),
        confidence=reading.confidence,
        decided_by=_text(reading.decided_by),
    )


def trial_read_record(read: TrialRead, *, readings: Sequence[Reading]) -> Record:
    """A trial's read, with its readings in it: nothing asks for one reading alone."""
    return Record(
        "trial_read",
        key_of(read.source_name, read.trial_id),
        body(
            source_name=read.source_name,
            trial_id=read.trial_id,
            input_hash=read.input_hash,
            instructions_version=read.instructions_version,
            provider=read.provider,
            model=read.model,
            refusals=list(read.refusals),
            readings=[
                _reading(reading)
                for reading in sorted(readings, key=lambda r: (r.outcome, _text(r.kind)))
            ],
            read_at=when(read.read_at),
        ),
    )


# --- the registry corpus ------------------------------------------------------------------


def intervention_names(interventions: Sequence[Mapping[str, Any]]) -> str:
    """Every name of every intervention, the registry's own and its other names, for the
    trial search's index. Postgres keeps other names under `otherNames`."""
    names: list[str] = []
    for intervention in interventions:
        if intervention.get("name"):
            names.append(str(intervention["name"]))
        others = intervention.get("otherNames")
        if isinstance(others, list):
            names.extend(str(name) for name in others if name)
    return "; ".join(names)


def registry_payload(trial: RegistryTrial) -> Any:
    """A trial's payload as the store keeps it: without a person's name, as the corpus
    load keeps one since 2026-11-17 (`sources.people.without_people`). Rows
    loaded before then still hold such names in Postgres."""
    if not isinstance(trial.raw_payload, dict):
        return trial.raw_payload
    return without_people(trial.raw_payload)


def registry_trial_record(trial: RegistryTrial, *, payload_sha256: str | None = None) -> Record:
    """A trial with every column Postgres holds, its payload named by checksum. When the
    registry was last found to say the same (`checked_at`) is the store's to know. A
    sponsor who is a person is not named."""
    payload = registry_payload(trial) if payload_sha256 is None else trial.raw_payload
    sponsors = (
        payload.get("protocolSection", {}).get("sponsorCollaboratorsModule", {})
        if isinstance(payload, dict)
        else {}
    )
    return Record(
        "registry_trial",
        key_of(trial.registry_name, trial.external_id),
        body(
            registry_name=trial.registry_name,
            external_id=trial.external_id,
            title=trial.title,
            conditions=list(trial.conditions),
            interventions=list(trial.interventions),
            intervention_names=intervention_names(trial.interventions),
            phases=list(trial.phases),
            overall_status=trial.overall_status,
            start_date=trial.start_date,
            sponsor_class=trial.sponsor_class,
            search_name=trial.search_name,
            search_indication=trial.search_indication,
            start_date_type=trial.start_date_type,
            last_update_posted=day(trial.last_update_posted),
            study_first_posted=day(trial.study_first_posted),
            primary_completion_date=trial.primary_completion_date,
            primary_completion_date_type=trial.primary_completion_date_type,
            completion_date=trial.completion_date,
            completion_date_type=trial.completion_date_type,
            results_first_posted=day(trial.results_first_posted),
            has_results=flag(trial.has_results),
            acronym=trial.acronym,
            lead_sponsor_name=(
                None if sponsored_by_a_person(sponsors) else trial.lead_sponsor_name
            ),
            payload_sha256=payload_sha256 or payload_of(payload).sha256,
            fetched_at=when(trial.fetched_at),
        ),
    )


def registry_load_record(load: RegistryLoad) -> Record:
    return Record(
        "registry_load",
        key_of(load.registry_name, load.condition),
        body(
            registry_name=load.registry_name,
            condition=load.condition,
            loaded_from=when(load.loaded_from),
            completed_at=when(load.completed_at),
        ),
    )


class TrialNamed(Protocol):
    """What names a trial: its registry and its identifier there."""

    registry_name: str
    external_id: str


def article_lead_record(lead: ArticleLead, *, trial: TrialNamed, url_key: str) -> Record:
    """A news article found for a trial. The search service's raw result is not kept: its
    fields are already the record's."""
    return Record(
        "article_lead",
        key_of(trial.registry_name, trial.external_id, url_key),
        body(
            registry_name=trial.registry_name,
            trial_id=trial.external_id,
            url_key=url_key,
            url=lead.url,
            outlet=lead.outlet,
            title=lead.title,
            published_date=day(lead.published_date),
            outlet_kind=_text(lead.outlet_kind),
            source_name=lead.source_name,
            search_query=lead.search_query,
            fetched_at=when(lead.fetched_at),
        ),
    )


# --- link leads ----------------------------------------------------------------------------


def stored_lead(lead: LinkLead) -> bool:
    """Whether the store holds a lead at all: only one on a listed outlet."""
    return lead.outlet_kind is not OutletKind.UNKNOWN and (
        lead.screen_outcome is not ScreenOutcome.UNLISTED_OUTLET
    )


def link_lead_record(lead: LinkLead, *, claim_slug: str | None) -> Record:
    """A lead on a listed outlet. Every lead in Postgres came from a run file; whether its
    title names a topic word is the store's index to find, and starts as no."""
    if not stored_lead(lead):
        raise ValueError(f"A lead on an unlisted outlet is never stored: {lead.url_key}")
    if lead.url_key_version != KEY_VERSION:
        raise ValueError(
            f"The lead {lead.url_key} has an address key of version {lead.url_key_version}, "
            f"not {KEY_VERSION}: run `thenwhat backfill rekey-links` first."
        )
    return Record(
        "link_lead",
        lead.url_key,
        body(
            url_key=lead.url_key,
            url_key_version=lead.url_key_version,
            url=lead.url,
            outlet=lead.outlet,
            outlet_kind=_text(lead.outlet_kind),
            title=lead.title,
            first_shared_at=when(lead.first_shared_at),
            origin="file",
            screen_outcome=_text(lead.screen_outcome),
            triage_score=lead.triage_score,
            triage_version=lead.triage_version,
            read_outcome=_text(lead.read_outcome),
            read_detail=lead.read_detail,
            claim_slug=claim_slug,
        ),
    )


def link_share_record(share: LinkShare, *, lead_url_key: str) -> Record:
    shared_at = when(share.shared_at)
    return Record(
        "link_share",
        key_of(lead_url_key, share.platform, share.community, shared_at),
        body(
            lead_url_key=lead_url_key,
            platform=share.platform,
            community=share.community,
            shared_at=shared_at,
            score=share.score,
            item_number=share.item_number,
        ),
    )


def link_lead_link_record(link: LinkLeadLink, *, lead_url_key: str, record_key: str) -> Record:
    """A record screening found, named by a claim's slug or a trial's `registry|number`."""
    return Record(
        "link_lead_link",
        key_of(lead_url_key, link.record_kind, record_key, link.reason),
        body(
            lead_url_key=lead_url_key,
            record_kind=link.record_kind,
            record_key=record_key,
            reason=link.reason,
        ),
    )


def link_lead_label_record(label: LinkLeadLabel, *, lead_url_key: str) -> Record:
    labelled_by = _text(label.labelled_by)
    return Record(
        "link_lead_label",
        key_of(lead_url_key, labelled_by),
        body(
            lead_url_key=lead_url_key,
            labelled_by=labelled_by,
            label=_text(label.label),
            labelled_at=when(label.labelled_at),
        ),
    )


# --- decisions, spend, measurements, ledger, icons ------------------------------------------


def decision_record(decision: DecisionLog, *, names: Names) -> Record:
    """A decision has no natural key: its place in the run is its Postgres id, which the
    migration's run keeps (design.md decision 12)."""
    return Record(
        "decision",
        str(decision.id),
        body(
            seq=decision.id,
            step=decision.step,
            input_ref=natural_ref(decision.input_ref, names),
            backend=decision.backend,
            model=decision.model,
            options=decision.options,
            output=decision.output,
            confidence=decision.confidence,
            error=decision.error,
            human_label=decision.human_label,
            created_at=when(decision.created_at),
        ),
    )


def usage_record(usage: LlmUsage) -> Record:
    return Record(
        "usage",
        str(usage.id),
        body(
            seq=usage.id,
            purpose=usage.purpose,
            model=usage.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cost_usd=money(usage.cost_usd),
            created_at=when(usage.created_at),
        ),
    )


def measure_daily_record(measure: MeasureDaily) -> Record:
    the_day = day(measure.day)
    return Record(
        "measure_daily",
        key_of(the_day, measure.step, measure.step_version, measure.writer, measure.outcome),
        body(
            day=the_day,
            step=measure.step,
            step_version=measure.step_version,
            writer=measure.writer,
            outcome=measure.outcome,
            spans=measure.spans,
            records=measure.records,
            reused=measure.reused,
            ran_seconds=measure.ran_seconds,
            waited_seconds=measure.waited_seconds,
            waited_by_cause=measure.waited_by_cause,
            requests_by_source=measure.requests_by_source,
            tokens_in=measure.tokens_in,
            tokens_out=measure.tokens_out,
            cost_usd=money(measure.cost_usd),
            inner_cost_usd=money(measure.inner_cost_usd),
            rows_written=measure.rows_written,
        ),
    )


def measure_claim_record(measure: MeasureClaim, *, slug: str) -> Record:
    return Record(
        "measure_claim",
        slug,
        body(
            slug=slug,
            first_seen_at=when(measure.first_seen_at),
            last_step_at=when(measure.last_step_at),
            spans=measure.spans,
            ran_seconds=measure.ran_seconds,
            waited_seconds=measure.waited_seconds,
            cost_usd=money(measure.cost_usd),
        ),
    )


def work_entry_record(entry: WorkEntry, *, record_key: str) -> Record:
    """A ledger entry named by its record's natural key: a claim's slug or a trial's
    `registry|number`. A link step's entry is not kept: the lead's own columns say it."""
    if entry.record_kind == "link_lead":
        raise ValueError("A link step's ledger entry is never stored.")
    return Record(
        "work_entry",
        key_of(entry.record_kind, record_key, entry.step, entry.step_version),
        body(
            record_kind=entry.record_kind,
            record_key=record_key,
            step=entry.step,
            step_version=entry.step_version,
            outcome=_text(entry.outcome),
            attempts=entry.attempts,
            requests_used=entry.requests_used,
            fingerprint=entry.fingerprint,
            stale=flag(entry.stale),
            error=entry.error,
            last_attempt_at=when(entry.last_attempt_at),
        ),
    )


def outlet_icon_record(icon: OutletIcon) -> Record:
    return Record(
        "outlet_icon",
        icon.domain,
        body(
            domain=icon.domain,
            icon_url=icon.icon_url,
            media_type=icon.media_type,
            content_hex=None if icon.content is None else icon.content.hex().upper(),
            fetched_at=when(icon.fetched_at),
        ),
    )
