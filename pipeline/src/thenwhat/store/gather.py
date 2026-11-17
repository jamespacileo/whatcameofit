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
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field

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
    TrialRead,
    WorkEntry,
)
from thenwhat.store import records as r
from thenwhat.store.form import Record, key_of, payload_record, url_key

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


def gather(session: Session) -> Gathered:
    """Every record the store keeps of what Postgres holds now, parents before children,
    each natural key once, with counts of what was left out."""
    gathered = Gathered(records=[])
    gathered.records = distinct(_gather(session, gathered.unnamed), gathered.repeated)
    return gathered


def _gather(session: Session, unnamed: Counter[str]) -> Iterator[Record]:
    claims = {claim.id: claim for claim in _all(session, Claim)}
    slugs = {claim_id: claim.slug for claim_id, claim in claims.items()}
    merged = {claim_id for claim_id, claim in claims.items() if claim.merged_into_id}
    articles = {article.id: article for article in _all(session, SourceArticle)}
    keys = {article.id: url_key(article.url) for article in articles.values()}
    entities = {entity.id: entity for entity in _all(session, Entity)}
    matches = {match.id: match for match in _all(session, EntityMatch)}
    trials = {trial.id: trial for trial in _all(session, RegistryTrial)}
    leads = {lead.id: lead for lead in _all(session, LinkLead)}
    labelled = set(session.scalars(select(LinkLeadLabel.link_lead_id)))
    kept_leads = {
        lead_id: lead
        for lead_id, lead in leads.items()
        if r.stored_lead(lead)
        and (
            lead.triage_score is not None
            or lead.read_outcome is not None
            or lead.claim_id is not None
            or lead_id in labelled
        )
    }
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
        leads={i: lead.url_key for i, lead in leads.items()},
    )
    changes: dict[int, list[ClaimChange]] = defaultdict(list)
    for change in _all(session, ClaimChange):
        changes[change.claim_id].append(change)
    tied_to_lead = {lead.claim_id for lead in leads.values() if lead.claim_id is not None}

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
    for substance in session.scalars(select(EntitySubstance).order_by(EntitySubstance.entity_id)):
        entity = entities[substance.entity_id]
        if own(entity):
            yield payload_record(substance.payload)
            yield r.substance_source_record(substance)
            yield r.entity_substance_record(substance, entity=entity, slug=slugs[entity.claim_id])

    events = {event.id: event for event in _all(session, EvidenceEvent)}
    for event in events.values():
        if event.claim_id in merged:
            continue
        match = None
        if event.entity_match_id is not None:
            entity_match = matches[event.entity_match_id]
            match = (entities[entity_match.entity_id], entity_match)
        yield payload_record(event.raw_payload)
        yield r.evidence_event_record(event, slug=slugs[event.claim_id], match=match)
    for failure in _all(session, FailureFlag):
        if failure.claim_id not in merged:
            yield r.failure_flag_record(
                failure,
                slug=slugs[failure.claim_id],
                dedupe_key=events[failure.evidence_event_id].dedupe_key,
            )
    readings: dict[int, list[Reading]] = defaultdict(list)
    for reading in _all(session, Reading):
        readings[reading.trial_read_id].append(reading)
    for read in _all(session, TrialRead):
        yield r.trial_read_record(read, readings=readings[read.id])

    for trial in trials.values():
        yield payload_record(trial.raw_payload)
        yield r.registry_trial_record(trial)
    for load in session.scalars(
        select(RegistryLoad).order_by(RegistryLoad.registry_name, RegistryLoad.condition)
    ):
        yield r.registry_load_record(load)
    for lead in _all(session, ArticleLead):
        yield r.article_lead_record(
            lead, trial=trials[lead.registry_trial_id], url_key=url_key(lead.url)
        )

    for lead in kept_leads.values():
        yield r.link_lead_record(
            lead, claim_slug=slugs.get(lead.claim_id) if lead.claim_id else None
        )
    for share in _all(session, LinkShare):
        if share.link_lead_id in kept_leads:
            yield r.link_share_record(share, lead_url_key=kept_leads[share.link_lead_id].url_key)

    def record_key(kind: str, record_id: int) -> str | None:
        if kind == "claim":
            return slugs.get(record_id)
        if kind == "registry_trial" and record_id in trials:
            return key_of(trials[record_id].registry_name, trials[record_id].external_id)
        return None

    for link in _all(session, LinkLeadLink):
        if link.link_lead_id not in kept_leads:
            continue
        named = record_key(link.record_kind, link.record_id)
        if named is None:
            unnamed["link_lead_link"] += 1
        else:
            yield r.link_lead_link_record(
                link, lead_url_key=kept_leads[link.link_lead_id].url_key, record_key=named
            )
    for label in _all(session, LinkLeadLabel):
        if label.link_lead_id in kept_leads:
            yield r.link_lead_label_record(
                label, lead_url_key=kept_leads[label.link_lead_id].url_key
            )

    for decision in _all(session, DecisionLog):
        if decision.step not in LOCAL_DECISION_STEPS:
            yield r.decision_record(decision, names=names)
    for usage in _all(session, LlmUsage):
        yield r.usage_record(usage)
    for measure in _all(session, MeasureDaily):
        yield r.measure_daily_record(measure)
    for measured in _all(session, MeasureClaim):
        if measured.claim_id not in merged:
            yield r.measure_claim_record(measured, slug=slugs[measured.claim_id])
    for entry in _all(session, WorkEntry):
        if entry.record_kind == "link_lead":
            continue  # The link steps' ledger stays on the device (store-tables.md).
        named = record_key(entry.record_kind, entry.record_id)
        if named is None:
            unnamed["work_entry"] += 1
        else:
            yield r.work_entry_record(entry, record_key=named)
    for icon in session.scalars(select(OutletIcon).order_by(OutletIcon.domain)):
        yield r.outlet_icon_record(icon)
