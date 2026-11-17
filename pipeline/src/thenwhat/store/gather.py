"""Every record Postgres holds that the store keeps, in natural-key form.

What is left out, and why, is `store-tables.md`'s: link leads on unlisted outlets and
leads never scored, read, labelled or tied to a claim; the link steps' ledger entries;
the `lead_triage` decisions. One more is this mapping's: what a merged claim keeps for
itself (its intervention, matches, terms and events) is not gathered, because the
store names that claim's slug as the claim it was merged into (`claim_key`), so a second
push would give those records to the claim that stayed (the pull request lists this).
Nor is a rename: see below.

Two rows that come to one natural key give one record: the first, by row id. Each row
left out that way, and each ledger entry or lead link naming a kind the store does not
name records by, is counted, so a caller can show what a snapshot did not carry.
"""

from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

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
    TrialPaper,
    TrialRead,
    WorkEntry,
)
from thenwhat.domain import OutletKind, ScreenOutcome
from thenwhat.sources.people import payload_without_people
from thenwhat.store import records as r
from thenwhat.store.form import (
    Payload,
    Record,
    key_of,
    payload_of,
    payload_record_of,
    url_key,
    when,
)

# Decisions that stay on the device: the lead already holds its score and version.
LOCAL_DECISION_STEPS = frozenset({"lead_triage"})


@dataclass
class Gathered:
    """A snapshot's records, and what it left out by kind: `repeated`, rows whose natural
    key an earlier row already gave; `unnamed`, ledger entries and lead links naming a
    record the store does not name by key."""

    records: list[Record]
    repeated: Counter[str] = field(default_factory=Counter)
    unnamed: Counter[str] = field(default_factory=Counter)


def distinct(records: Iterable[Record], repeated: Counter[str] | None = None) -> list[Record]:
    """One record per kind and key, the first given: a run may stage each key once. Each
    later record with a key already given is counted in `repeated`, by kind."""
    seen: dict[tuple[str, str], Record] = {}
    for record in records:
        if (record.kind, record.key) in seen:
            if repeated is not None:
                repeated[record.kind] += 1
            continue
        seen[(record.kind, record.key)] = record
    return list(seen.values())


def _all[T](session: Session, model: type[T]) -> list[T]:
    """Every row of a table with an id, in id order."""
    return list(session.scalars(select(model).order_by(text("id"))))


# Rows read a page at a time from the database's cursor, so a large table is never held.
PAGE = 2_000


def gather(
    session: Session,
    *,
    keep_payload: Callable[[Payload], None] | None = None,
    hot_only: bool = False,
) -> Gathered:
    """Every record the store keeps of what Postgres holds now, parents before children,
    each natural key once, with counts of what was left out. `keep_payload` is given each
    raw payload as it is read, for a caller that keeps the large ones as objects. For a
    whole database use `stream`, which holds no more than a page of rows."""
    gathered = Gathered(records=[])
    gathered.records = list(stream(session, gathered, keep_payload=keep_payload, hot_only=hot_only))
    return gathered


def stream(
    session: Session,
    counts: Gathered,
    *,
    keep_payload: Callable[[Payload], None] | None = None,
    hot_only: bool = False,
) -> Iterator[Record]:
    """`gather`'s records one at a time, in the same order, each natural key once; what
    is left out is counted into `counts`. With `hot_only`, only the hot tier's records,
    and no bulk table is read but the leads' addresses and claims (tiers.py)."""
    # Each key once, by its hash: two keys that are not one share a 64-bit hash about
    # once in 10^12 pairs, and the set stays small for millions of records.
    seen: set[int] = set()
    for record in _gather(
        session, counts.unnamed, keep_payload or (lambda _: None), hot_only=hot_only
    ):
        held = hash((record.kind, record.key))
        if held in seen:
            counts.repeated[record.kind] += 1
            continue
        seen.add(held)
        yield record


def _pages(session: Session, statement: Any) -> Iterator[Any]:
    return iter(session.scalars(statement.execution_options(yield_per=PAGE)))


def _gather(
    session: Session,
    unnamed: Counter[str],
    keep_payload: Callable[[Payload], None],
    *,
    hot_only: bool = False,
) -> Iterator[Record]:
    def payload_record(value: Any) -> tuple[Record, str]:
        payload = payload_of(value)
        keep_payload(payload)
        return payload_record_of(payload), payload.sha256

    claims = {claim.id: claim for claim in _all(session, Claim)}
    slugs = {claim_id: claim.slug for claim_id, claim in claims.items()}
    merged = {claim_id for claim_id, claim in claims.items() if claim.merged_into_id}
    articles = {article.id: article for article in _all(session, SourceArticle)}
    keys = {article.id: url_key(article.url) for article in articles.values()}
    entities = {entity.id: entity for entity in _all(session, Entity)}
    matches = {match.id: match for match in _all(session, EntityMatch)}
    trials: dict[int, tuple[str, str]] = (
        {}
        if hot_only
        else {
            trial_id: (registry, external)
            for trial_id, registry, external in session.execute(
                select(RegistryTrial.id, RegistryTrial.registry_name, RegistryTrial.external_id)
            )
        }
    )
    labelled = set() if hot_only else set(session.scalars(select(LinkLeadLabel.link_lead_id)))
    lead_keys: dict[int, str] = {}
    kept_leads: set[int] = set()
    tied_to_lead: set[int] = set()
    if hot_only:
        # A decision names a lead by its address, and a claim tied to a lead began in a
        # backfill: two narrow reads of the leads, and nothing else of the bulk tables.
        lead_keys = {i: key for i, key in session.execute(select(LinkLead.id, LinkLead.url_key))}
        tied_to_lead = {
            claim_id
            for claim_id in session.scalars(
                select(LinkLead.claim_id).where(LinkLead.claim_id.is_not(None)).distinct()
            )
            if claim_id is not None
        }
    for lead_id, key, claim_id, kind, screen, score, read in (
        []
        if hot_only
        else session.execute(
            select(
                LinkLead.id,
                LinkLead.url_key,
                LinkLead.claim_id,
                LinkLead.outlet_kind,
                LinkLead.screen_outcome,
                LinkLead.triage_score,
                LinkLead.read_outcome,
            ).execution_options(yield_per=20_000)
        )
    ):
        lead_keys[lead_id] = key
        if claim_id is not None:
            tied_to_lead.add(claim_id)
        listed = kind is not OutletKind.UNKNOWN and screen is not ScreenOutcome.UNLISTED_OUTLET
        if listed and (
            score is not None or read is not None or claim_id is not None or lead_id in labelled
        ):
            kept_leads.add(lead_id)
    names = r.Names(
        claims=slugs,
        articles={i: (slugs[a.claim_id], keys[i]) for i, a in articles.items()},
        matches={
            i: (
                slugs[entities[m.entity_id].claim_id],
                str(entities[m.entity_id].type.value),
                entities[m.entity_id].name,
                m.source_name,
                m.external_id,
            )
            for i, m in matches.items()
        },
        leads=lead_keys,
    )
    changes: dict[int, list[ClaimChange]] = defaultdict(list)
    for change in _all(session, ClaimChange):
        changes[change.claim_id].append(change)

    # Claims first, then what hangs from them.
    for claim in claims.values():
        yield r.claim_record(
            claim, origin=r.claim_origin(claim, from_link_lead=claim.id in tied_to_lead)
        )
    for claim in claims.values():
        # A merged claim's publication and archive are left out (`claim_actions`).
        actions = r.claim_actions(claim, changes[claim.id], slugs)
        # A rename names the claim by the slug it had, which a store that learns the
        # claim from this snapshot never holds: the run's counts would not reconcile and
        # the whole run would be refused. A rename reaches the store when it is made.
        yield from (a for a in actions if a.body["action"] != "rename")
    for article_id, article in articles.items():
        yield r.source_article_record(
            article, slug=slugs[article.claim_id], url_key=keys[article_id]
        )
    for promise in _all(session, Promise):
        yield r.promise_record(
            promise, slug=slugs[promise.claim_id], url_key=keys[promise.source_article_id]
        )
    for statement in _all(session, ReportedStatement):
        yield r.reported_statement_record(
            statement,
            slug=slugs[statement.claim_id],
            url_key=keys[statement.source_article_id],
            names=names,
        )

    def own(entity: Entity) -> bool:
        return entity.claim_id not in merged

    for entity in entities.values():
        if own(entity):
            yield r.entity_record(entity, slug=slugs[entity.claim_id])
    for link in session.scalars(
        select(EntityArticle).order_by(EntityArticle.entity_id, EntityArticle.source_article_id)
    ):
        entity = entities[link.entity_id]
        if own(entity):
            yield r.entity_article_record(
                link,
                entity=entity,
                slug=slugs[entity.claim_id],
                url_key=keys[link.source_article_id],
            )
    for match in matches.values():
        entity = entities[match.entity_id]
        if own(entity):
            yield r.entity_match_record(match, entity=entity, slug=slugs[entity.claim_id])
    for term in _all(session, ClaimTerm):
        if term.claim_id not in merged:
            yield r.claim_term_record(term, slug=slugs[term.claim_id])
    for record in session.scalars(
        select(TermRecord).order_by(TermRecord.source_name, TermRecord.external_id)
    ):
        yield r.term_source_record(record)
    for record in session.scalars(
        select(OrganisationRecord).order_by(
            OrganisationRecord.source_name, OrganisationRecord.external_id
        )
    ):
        yield r.organisation_source_record(record)
    for paper in _all(session, PaperRecord):
        yield r.paper_source_record(paper)
    for substance in _pages(session, select(EntitySubstance).order_by(EntitySubstance.entity_id)):
        entity = entities[substance.entity_id]
        if own(entity):
            yield payload_record(substance.payload)[0]
            yield r.substance_source_record(substance)
            yield r.entity_substance_record(substance, entity=entity, slug=slugs[entity.claim_id])

    dedupe_keys: dict[int, str] = {}
    for event in _pages(session, select(EvidenceEvent).order_by(EvidenceEvent.id)):
        dedupe_keys[event.id] = event.dedupe_key
        if event.claim_id in merged:
            continue
        match = None
        if event.entity_match_id is not None:
            entity_match = matches[event.entity_match_id]
            match = (entities[entity_match.entity_id], entity_match)
        # A second guard: an event stored before people were removed at the source, a
        # registry study, or anything carrying a registry person's keys; a paper's byline stays.
        record, sha256 = payload_record(payload_without_people(event.raw_payload))
        yield record
        yield r.evidence_event_record(
            event, slug=slugs[event.claim_id], match=match, payload_sha256=sha256
        )
    for failure in _all(session, FailureFlag):
        if failure.claim_id not in merged:
            yield r.failure_flag_record(
                failure,
                slug=slugs[failure.claim_id],
                dedupe_key=dedupe_keys[failure.evidence_event_id],
            )
    readings: dict[int, list[Reading]] = defaultdict(list)
    for reading in _all(session, Reading):
        readings[reading.trial_read_id].append(reading)
    for read in _all(session, TrialRead):
        yield r.trial_read_record(read, readings=readings[read.id])

    for decision in _pages(
        session,
        select(DecisionLog)
        .where(DecisionLog.step.not_in(LOCAL_DECISION_STEPS))
        .order_by(DecisionLog.id),
    ):
        yield r.decision_record(decision, names=names)
    for icon in session.scalars(select(OutletIcon).order_by(OutletIcon.domain)):
        yield r.outlet_icon_record(icon)
    if hot_only:
        return

    for trial in _pages(session, select(RegistryTrial).order_by(RegistryTrial.id)):
        record, sha256 = payload_record(r.registry_payload(trial))
        yield record
        yield r.registry_trial_record(trial, payload_sha256=sha256)
    # A trial's papers found by its number, without their abstracts or any email (ADR 0011).
    for paper in _pages(session, select(TrialPaper).order_by(TrialPaper.id)):
        if paper.registry_trial_id not in trials:
            continue
        registry, external = trials[paper.registry_trial_id]
        record, sha256 = payload_record(payload_without_people(paper.raw_payload))
        yield record
        yield Record(
            "trial_paper",
            key_of(registry, external, paper.source_name, paper.pubmed_id),
            {
                "registry_name": registry,
                "trial_id": external,
                "source_name": paper.source_name,
                "pubmed_id": paper.pubmed_id,
                "payload_sha256": sha256,
                "fetched_at": when(paper.fetched_at),
            },
        )
    for load in session.scalars(
        select(RegistryLoad).order_by(RegistryLoad.registry_name, RegistryLoad.condition)
    ):
        yield r.registry_load_record(load)
    for lead in _pages(session, select(ArticleLead).order_by(ArticleLead.id)):
        registry, external = trials[lead.registry_trial_id]
        yield r.article_lead_record(
            lead, trial=_Trial(registry, external), url_key=url_key(lead.url)
        )

    for lead in _pages(session, select(LinkLead).order_by(LinkLead.id)):
        if lead.id in kept_leads:
            yield r.link_lead_record(
                lead, claim_slug=slugs.get(lead.claim_id) if lead.claim_id else None
            )
    for share in _pages(session, select(LinkShare).order_by(LinkShare.id)):
        if share.link_lead_id in kept_leads:
            yield r.link_share_record(share, lead_url_key=lead_keys[share.link_lead_id])

    def record_key(kind: str, record_id: int) -> str | None:
        if kind == "claim":
            return slugs.get(record_id)
        if kind == "registry_trial" and record_id in trials:
            return key_of(*trials[record_id])
        return None

    for link in _pages(session, select(LinkLeadLink).order_by(LinkLeadLink.id)):
        if link.link_lead_id not in kept_leads:
            continue
        named = record_key(link.record_kind, link.record_id)
        if named is None:
            unnamed["link_lead_link"] += 1
        else:
            yield r.link_lead_link_record(
                link, lead_url_key=lead_keys[link.link_lead_id], record_key=named
            )
    for label in _all(session, LinkLeadLabel):
        if label.link_lead_id in kept_leads:
            yield r.link_lead_label_record(label, lead_url_key=lead_keys[label.link_lead_id])

    for usage in _pages(session, select(LlmUsage).order_by(LlmUsage.id)):
        yield r.usage_record(usage)
    for measure in _all(session, MeasureDaily):
        yield r.measure_daily_record(measure)
    for measured in _all(session, MeasureClaim):
        if measured.claim_id not in merged:
            yield r.measure_claim_record(measured, slug=slugs[measured.claim_id])
    # The link steps' ledger stays on the device (store-tables.md).
    for entry in _pages(
        session,
        select(WorkEntry).where(WorkEntry.record_kind != "link_lead").order_by(WorkEntry.id),
    ):
        named = record_key(entry.record_kind, entry.record_id)
        if named is None:
            unnamed["work_entry"] += 1
        else:
            yield r.work_entry_record(entry, record_key=named)


@dataclass
class _Trial:
    """What an article lead names its trial by."""

    registry_name: str
    external_id: str
