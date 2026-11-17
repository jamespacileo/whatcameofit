"""Where the export's records come from. Behavior: openspec truth-store, "The export is
assembled once, from either store".

`build.py` assembles the export from a `Records`: it asks for a claim's events, its
matches, a term's record, and never for a table. Two readers answer, with the same
record classes (`db/models.py`): `PostgresRecords` here, over a session, and
`StoreRecords` (`store_records.py`), over a SQLite file that has the truth store's
schema. What a claim's entry contains, how its lists are ordered and how its status is
derived are the assembly's alone, so the two exports can differ only in what a reader
hands over.

A reader keeps to these rules so that the assembly need not know which one it has:

- a list is returned in the order its method states, ties broken by the row's own id;
- a row's `id` is whatever the reader's store calls it. The assembly uses ids only to
  tie one record of a claim to another (an event to the flag raised from it);
- a record that is absent is `None` or an empty list, never an error.
"""

from collections.abc import Iterable
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.corrections import moved_addresses
from thenwhat.claims.entities import entities_of
from thenwhat.claims.entry import articles_of, promises_of
from thenwhat.db.models import (
    Claim,
    ClaimTerm,
    Entity,
    EntityArticle,
    EntityMatch,
    EvidenceEvent,
    FailureFlag,
    OrganisationRecord,
    OutletIcon,
    PaperRecord,
    Promise,
    Reading,
    ReportedStatement,
    SourceArticle,
    TermRecord,
)
from thenwhat.decide.core import Decision
from thenwhat.decide.steps import latest_scoring, latest_stage_suggestion
from thenwhat.domain import Decider, ReviewState
from thenwhat.events.paper_records import stored_paper
from thenwhat.readings.service import readings_of, stored_read
from thenwhat.sources.mesh import Mesh


class Records(Protocol):
    """What the export's assembly asks of a store."""

    def published_claims(self) -> Iterable[Claim]:
        """Each approved claim that is neither archived nor awaiting audit, by slug."""
        ...

    def taken_down(self) -> Iterable[Claim]:
        """Each archived claim that was once published."""
        ...

    def moved(self) -> list[tuple[str, Claim]]:
        """Each published address with no page of its own any more, and the claim it
        leads to: a merged claim's slug, and a slug a rename replaced. By slug."""
        ...

    def decided_by_assistant(self, claim: Claim) -> bool:
        """Whether an assistant's decision stands on the claim, one of its matches, its
        events or its reported statements."""
        ...

    def events(self, claim: Claim) -> list[EvidenceEvent]:
        """The claim's approved events, by date."""
        ...

    def failure_flags(self, claim: Claim) -> list[FailureFlag]:
        """The claim's failure flags, by id."""
        ...

    def articles(self, claim: Claim) -> list[SourceArticle]:
        """The claim's source articles, by the date they were published."""
        ...

    def promises(self, claim: Claim) -> list[Promise]:
        """The claim's promises, by the date their articles were published."""
        ...

    def statements(self, claim: Claim) -> list[tuple[ReportedStatement, SourceArticle]]:
        """The claim's approved reported statements with their articles, by the date
        the article was published and then by article."""
        ...

    def entities(self, claim: Claim) -> list[Entity]:
        """The claim's entities, by id."""
        ...

    def approved_matches(self, entity: Entity) -> list[EntityMatch]:
        """The entity's approved matches from every source, highest score first."""
        ...

    def shown_matches(self, claim: Claim, *, but_from: tuple[str, ...]) -> list[EntityMatch]:
        """The approved and pending matches of the claim's entities, highest score
        first, except those from the sources named."""
        ...

    def match_reading(self, match: EntityMatch) -> str | None:
        """The answer the latest scoring of the match chose, when one is on record."""
        ...

    def named_in(self, entity: Entity) -> list[int]:
        """The ids of the source articles recorded as naming the entity."""
        ...

    def stage_reading(self, claim: Claim) -> Decision | None:
        """The latest reading of the claim's evidence stage that gave an answer."""
        ...

    def terms(self, claim: Claim) -> list[ClaimTerm]:
        """The claim's approved terms, by id."""
        ...

    def term_record(self, source_name: str, external_id: str) -> TermRecord | None: ...

    def mesh_records(self) -> list[TermRecord]:
        """Every stored MeSH term record, by identifier: the vocabulary a claim's clinical
        categories are placed in (openspec clinical-classification)."""
        ...

    def organisation_record(
        self, source_name: str, external_id: str
    ) -> OrganisationRecord | None: ...

    def paper(
        self, *, doi: str | None, pubmed_id: str | None, identifier: str | None
    ) -> PaperRecord | None:
        """The stored record of a paper known by any of these, tried in that order."""
        ...

    def trial_read(self, source_name: str, trial_id: str) -> tuple[str, list[Reading]] | None:
        """The stored read of a trial's record: the checksum of the outcomes it was read
        from, and its readings by outcome and kind."""
        ...

    def outlet_icons(self, domains: set[str]) -> list[OutletIcon]:
        """The stored icon rows of these domains, by domain."""
        ...

    def done(self) -> None:
        """The assembly has read everything, and has put on each claim it published the
        status it derived and, when it had none, a published time."""
        ...


class PostgresRecords:
    """The pipeline's own database, through a session. A status the assembly derives and
    a first published time are stored with the session's next commit."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def published_claims(self) -> Iterable[Claim]:
        return self.session.scalars(
            select(Claim)
            .where(
                Claim.review_state == ReviewState.APPROVED,
                Claim.archived_at.is_(None),
                Claim.awaiting_audit_at.is_(None),
            )
            .order_by(Claim.slug)
        )

    def taken_down(self) -> Iterable[Claim]:
        return self.session.scalars(
            select(Claim).where(Claim.archived_at.is_not(None), Claim.published_at.is_not(None))
        )

    def moved(self) -> list[tuple[str, Claim]]:
        return moved_addresses(self.session)

    def decided_by_assistant(self, claim: Claim) -> bool:
        if claim.reviewed_by is Decider.ASSISTANT:
            return True
        session = self.session
        match_ids = select(EntityMatch.id).join(Entity).where(Entity.claim_id == claim.id)
        return bool(
            session.scalar(
                select(EntityMatch.id).where(
                    EntityMatch.id.in_(match_ids), EntityMatch.reviewed_by == Decider.ASSISTANT
                )
            )
            or session.scalar(
                select(EvidenceEvent.id).where(
                    EvidenceEvent.claim_id == claim.id,
                    EvidenceEvent.reviewed_by == Decider.ASSISTANT,
                )
            )
            or session.scalar(
                select(ReportedStatement.id).where(
                    ReportedStatement.claim_id == claim.id,
                    ReportedStatement.reviewed_by == Decider.ASSISTANT,
                )
            )
        )

    def events(self, claim: Claim) -> list[EvidenceEvent]:
        return list(
            self.session.scalars(
                select(EvidenceEvent)
                .where(
                    EvidenceEvent.claim_id == claim.id,
                    EvidenceEvent.review_state == ReviewState.APPROVED,
                )
                .order_by(EvidenceEvent.event_date, EvidenceEvent.id)
            )
        )

    def failure_flags(self, claim: Claim) -> list[FailureFlag]:
        return list(
            self.session.scalars(
                select(FailureFlag).where(FailureFlag.claim_id == claim.id).order_by(FailureFlag.id)
            )
        )

    def articles(self, claim: Claim) -> list[SourceArticle]:
        return articles_of(self.session, claim)

    def promises(self, claim: Claim) -> list[Promise]:
        return promises_of(self.session, claim)

    def statements(self, claim: Claim) -> list[tuple[ReportedStatement, SourceArticle]]:
        return [
            (statement, article)
            for statement, article in self.session.execute(
                select(ReportedStatement, SourceArticle)
                .join(SourceArticle, SourceArticle.id == ReportedStatement.source_article_id)
                .where(
                    ReportedStatement.claim_id == claim.id,
                    ReportedStatement.review_state == ReviewState.APPROVED,
                )
                .order_by(SourceArticle.published_date, SourceArticle.id, ReportedStatement.id)
            )
        ]

    def entities(self, claim: Claim) -> list[Entity]:
        return entities_of(self.session, claim)

    def approved_matches(self, entity: Entity) -> list[EntityMatch]:
        return list(
            self.session.scalars(
                select(EntityMatch)
                .where(
                    EntityMatch.entity_id == entity.id,
                    EntityMatch.review_state == ReviewState.APPROVED,
                )
                .order_by(EntityMatch.score.desc(), EntityMatch.id)
            )
        )

    def shown_matches(self, claim: Claim, *, but_from: tuple[str, ...]) -> list[EntityMatch]:
        return list(
            self.session.scalars(
                select(EntityMatch)
                .join(Entity)
                .where(
                    Entity.claim_id == claim.id,
                    EntityMatch.review_state.in_([ReviewState.APPROVED, ReviewState.PENDING]),
                    EntityMatch.source_name.not_in(but_from),
                )
                .order_by(EntityMatch.score.desc(), EntityMatch.id)
            )
        )

    def match_reading(self, match: EntityMatch) -> str | None:
        scored = latest_scoring(self.session, match)
        if scored is None or scored.output is None:
            return None
        choice = scored.output.get("choice")
        return choice if isinstance(choice, str) else None

    def named_in(self, entity: Entity) -> list[int]:
        return list(
            self.session.scalars(
                select(EntityArticle.source_article_id).where(EntityArticle.entity_id == entity.id)
            )
        )

    def stage_reading(self, claim: Claim) -> Decision | None:
        return latest_stage_suggestion(self.session, claim)

    def terms(self, claim: Claim) -> list[ClaimTerm]:
        return list(
            self.session.scalars(
                select(ClaimTerm)
                .where(
                    ClaimTerm.claim_id == claim.id,
                    ClaimTerm.review_state == ReviewState.APPROVED,
                )
                .order_by(ClaimTerm.id)
            )
        )

    def term_record(self, source_name: str, external_id: str) -> TermRecord | None:
        return self.session.get(TermRecord, (source_name, external_id))

    def mesh_records(self) -> list[TermRecord]:
        return list(
            self.session.scalars(
                select(TermRecord)
                .where(TermRecord.source_name == Mesh.name)
                .order_by(TermRecord.external_id)
            )
        )

    def organisation_record(self, source_name: str, external_id: str) -> OrganisationRecord | None:
        return self.session.get(OrganisationRecord, (source_name, external_id))

    def paper(
        self, *, doi: str | None, pubmed_id: str | None, identifier: str | None
    ) -> PaperRecord | None:
        return stored_paper(self.session, doi=doi, pubmed_id=pubmed_id, identifier=identifier)

    def trial_read(self, source_name: str, trial_id: str) -> tuple[str, list[Reading]] | None:
        read = stored_read(self.session, source_name, trial_id)
        return None if read is None else (read.input_hash, readings_of(self.session, read))

    def outlet_icons(self, domains: set[str]) -> list[OutletIcon]:
        return list(
            self.session.scalars(
                select(OutletIcon).where(OutletIcon.domain.in_(domains)).order_by(OutletIcon.domain)
            )
        )

    def done(self) -> None:
        self.session.flush()
