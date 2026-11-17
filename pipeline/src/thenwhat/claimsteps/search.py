"""The three parts of a claim's search, each a step that fails apart from the others: its
substance looked up, the trial registry searched, and papers searched for. Behavior:
openspec entity-resolution, "A lookup that failed is not a finished search" and "A
registry search leaves a record".

The substance record is what the rule for twin claims reads; the trial search is what a
status rests on; papers are neither, so a literature index that fails leaves the search
of the registry finished.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from thenwhat.claims.stages import confirm_stage_by_rule
from thenwhat.claimsteps.inputs import Inputs
from thenwhat.claimsteps.reasons import (
    NO_INTERVENTION,
    PAPERS_OFF,
    SOURCE_FAILED,
    attempt,
    model_failed,
    put_off,
)
from thenwhat.claimsteps.step import Answer, ClaimSources, ClaimStep
from thenwhat.db.models import Claim, Entity, EntityMatch, EntitySubstance, RegistrySearch
from thenwhat.decide.core import Backend, Decision, DecisionFailed
from thenwhat.decide.steps import latest_stage_suggestion, suggest_evidence_stage
from thenwhat.domain import WorkOutcome
from thenwhat.llm.errors import LlmError
from thenwhat.resolve.codes import give_development_codes, intervention_of
from thenwhat.resolve.organisations import match_organisations
from thenwhat.resolve.papers import choose_origin, find_papers, rescore_papers, trials_from_papers
from thenwhat.resolve.service import (
    RuleRedo,
    TrialRecords,
    redo_rule_approvals,
    rescore_claim,
    resolve_claim,
)
from thenwhat.sources.base import SourceError, UnsearchableTerm
from thenwhat.sources.clinicaltrials import ClinicalTrials, NotSent, Searched
from thenwhat.sources.openalex import OpenAlex
from thenwhat.sources.rxnorm import not_searched
from thenwhat.work.outcome import NeedsFix, NothingFound

# Why a vaccine's antigen, kept as its substance, is not sent as a name.
ANTIGEN = "the source of brands lists it as a vaccine's antigen, which is kept but not searched"


def _names(inputs: Inputs, claim_id: int) -> dict[str, Any]:
    return inputs.names.get(claim_id, {})


class ClaimSubstance(ClaimStep):
    """Look the claim's intervention up in the registry of substances, and in the source
    of brands when the registry lists none of its names. A registry that answers that it
    has no record for the name has answered: the lookup is finished."""

    name = "claim_substance"
    reasons = (SOURCE_FAILED, NO_INTERVENTION)

    def read(self, inputs: Inputs, claim_id: int) -> dict[str, Any]:
        return _names(inputs, claim_id)

    def work(self, session: Session, claim: Claim, sources: ClaimSources) -> Answer:
        answer = attempt(
            session,
            lambda: give_development_codes(
                session,
                claim,
                substances=sources.make_substances(session),
                brands=sources.make_brands(session),
            ),
        )
        if isinstance(answer, SourceError):
            return put_off(answer, self.now())
        if isinstance(answer, DecisionFailed | LlmError):
            return model_failed(answer)
        if answer is None:
            return NothingFound(NO_INTERVENTION)
        self.results[claim.id] = answer
        return WorkOutcome.DONE


@dataclass(slots=True)
class TrialsFound:
    """What a search of the trial registry found for a claim."""

    added: list[EntityMatch] = field(default_factory=list)
    # Pending candidates scored again, with `rescore`.
    again: list[EntityMatch] = field(default_factory=list)
    # Terms the registry could not search for, with its reason.
    refused: dict[str, str] = field(default_factory=dict)
    redone: RuleRedo | None = None
    # The evidence stage read for a claim with none confirmed, and whether a rule
    # confirmed it. None when the claim has a confirmed stage.
    stage: Decision | None = None
    stage_confirmed: bool = False
    stage_newly_read: bool = False


class ClaimTrials(ClaimStep):
    """Search the trial registry for the claim's intervention, by every name, phrase and
    code, and score each candidate for the claim's indication; then read the claim's
    evidence stage when none is confirmed. Every term searched, cut by a limit or not
    sent leaves a record, replacing the claim's search before, once the search finished."""

    name = "claim_trials"
    reasons = (SOURCE_FAILED,)

    def __init__(
        self,
        *,
        reject_below: float,
        accept_above: float,
        approve_drafts_by_rule: bool,
        stage_threshold: float,
        no_signal_years: int,
        rescore: bool = False,
        redo_rule: bool = False,
        **step: Any,
    ) -> None:
        super().__init__(**step)
        self.reject_below = reject_below
        self.accept_above = accept_above
        self.approve_drafts_by_rule = approve_drafts_by_rule
        self.stage_threshold = stage_threshold
        self.no_signal_years = no_signal_years
        self.rescore = rescore
        self.redo_rule = redo_rule

    def read(self, inputs: Inputs, claim_id: int) -> dict[str, Any]:
        names = _names(inputs, claim_id)
        dois = inputs.paper_dois.get(claim_id)
        return {**names, "paper_dois": dois} if dois else names

    def work(self, session: Session, claim: Claim, sources: ClaimSources) -> Answer:
        now = self.now()
        backend = sources.make_backend(session)
        trials, dois = sources.make_registries(session)
        # A stored trial that becomes a candidate is read from the registry in full.
        records = trials if isinstance(trials, TrialRecords) else None
        found = TrialsFound()
        searches: list[Searched | NotSent] = []

        def unsearchable(refused: UnsearchableTerm) -> None:
            if refused.term not in found.refused:
                found.refused[refused.term] = refused.reason
                searches.append(NotSent(ClinicalTrials.name, refused.term, refused.reason))

        def search() -> None:
            found.added = resolve_claim(
                session,
                claim,
                trials=trials,
                dois=dois,
                backend=backend,
                now=now,
                unsearchable=unsearchable,
                records=records,
                searched=searches.append,
                reject_below=self.reject_below,
                accept_above=self.accept_above,
            )
            if self.rescore:
                found.again = rescore_claim(
                    session,
                    claim,
                    trials=trials,
                    backend=backend,
                    now=now,
                    skip=found.added,
                    unsearchable=unsearchable,
                    records=records,
                    reject_below=self.reject_below,
                    accept_above=self.accept_above,
                )
            if self.redo_rule:
                found.redone = redo_rule_approvals(
                    session,
                    claim,
                    trials=trials,
                    backend=backend,
                    now=now,
                    no_signal_years=self.no_signal_years,
                    unsearchable=unsearchable,
                    records=records,
                    reject_below=self.reject_below,
                    accept_above=self.accept_above,
                )

        searched = attempt(session, search)
        if isinstance(searched, SourceError):
            return put_off(searched, now)
        if isinstance(searched, DecisionFailed | LlmError):
            return model_failed(searched)
        staged = attempt(session, lambda: self._stage(session, claim, backend, now, found))
        if isinstance(staged, SourceError):
            return put_off(staged, now)
        if isinstance(staged, DecisionFailed | LlmError):
            return model_failed(staged)
        keep_search(session, claim, [*searches, *_antigens(session, claim)], now)
        self.results[claim.id] = found
        return WorkOutcome.DONE

    def _stage(
        self, session: Session, claim: Claim, backend: Backend, now: datetime, found: TrialsFound
    ) -> None:
        """Read the claim's evidence stage when none is confirmed, reusing a stored
        reading, and let the rule confirm it when drafts are decided by rule."""
        if claim.evidence_stage is not None:
            return
        stage = latest_stage_suggestion(session, claim)
        found.stage_newly_read = stage is None
        if stage is None:
            stage = suggest_evidence_stage(session, backend, claim, now=now)
        found.stage = stage
        found.stage_confirmed = self.approve_drafts_by_rule and confirm_stage_by_rule(
            session,
            claim,
            stage,
            threshold=self.stage_threshold,
            now=now,
            no_signal_years=self.no_signal_years,
        )


def _antigens(session: Session, claim: Claim) -> list[NotSent]:
    """The substance kept for the claim's intervention that is not searched as a name: a
    vaccine's antigen."""
    intervention = intervention_of(session, claim)
    kept = session.get(EntitySubstance, intervention.id) if intervention else None
    if kept is None or not not_searched(kept.source_name, kept.payload):
        return []
    name = (kept.payload.get("substance") or {}).get("_name") if kept.payload else None
    return [NotSent(ClinicalTrials.name, str(name or kept.external_id), ANTIGEN)]


def keep_search(
    session: Session, claim: Claim, searches: list[Searched | NotSent], now: datetime
) -> None:
    """Replace the record of the claim's search of each registry with this one's."""
    for source in {search.source_name for search in searches} | {ClinicalTrials.name}:
        session.execute(
            delete(RegistrySearch).where(
                RegistrySearch.claim_id == claim.id, RegistrySearch.source_name == source
            )
        )
    for search in searches:
        if isinstance(search, NotSent):
            session.add(
                RegistrySearch(
                    claim_id=claim.id,
                    source_name=search.source_name,
                    term=search.term,
                    ran_at=now,
                    not_sent_reason=search.reason,
                )
            )
        else:
            session.add(
                RegistrySearch(
                    claim_id=claim.id,
                    source_name=search.source_name,
                    term=search.term,
                    condition=search.condition,
                    ran_at=now,
                    reported=search.reported,
                    kept=search.kept,
                    cut=search.cut,
                )
            )
    session.flush()


@dataclass(slots=True)
class PapersFound:
    """What the search for a claim's papers and organisations found."""

    organisations: list[EntityMatch] = field(default_factory=list)
    # None while paper search is off.
    papers: list[EntityMatch] | None = None
    # Pending papers scored again, with `rescore`.
    again: list[EntityMatch] | None = None
    # Whether the claim had any paper candidate after the search.
    has_papers: bool = False
    from_papers: list[EntityMatch] = field(default_factory=list)
    origin: Entity | None = None
    # What the literature source says of its use, if it says.
    usage: str | None = None


class ClaimPapers(ClaimStep):
    """Look the claim's organisations up, search the literature for papers about its
    intervention and indication, read the registry numbers the approved papers state,
    and choose the origin paper. Each part that finished stays when a later one fails."""

    name = "claim_papers"
    reasons = (SOURCE_FAILED, PAPERS_OFF)

    def __init__(
        self, *, reject_below: float, accept_above: float, rescore: bool = False, **step: Any
    ) -> None:
        super().__init__(**step)
        self.reject_below = reject_below
        self.accept_above = accept_above
        self.rescore = rescore

    def read(self, inputs: Inputs, claim_id: int) -> dict[str, Any]:
        return _names(inputs, claim_id)

    def work(self, session: Session, claim: Claim, sources: ClaimSources) -> Answer:
        now = self.now()
        research = sources.make_research(session)
        backend = sources.make_backend(session)
        papers = research.papers
        found = PapersFound()

        def organisations() -> None:
            found.organisations = match_organisations(
                session, claim, registry=research.organisations, now=now
            )

        def search() -> None:
            if papers is None:
                return
            found.papers = find_papers(
                session,
                claim,
                papers=papers,
                backend=backend,
                now=now,
                reject_below=self.reject_below,
                accept_above=self.accept_above,
            )
            found.has_papers = _has_papers(session, claim)
            if self.rescore:
                found.again = rescore_papers(
                    session,
                    claim,
                    papers=papers,
                    backend=backend,
                    now=now,
                    skip=found.papers,
                    reject_below=self.reject_below,
                    accept_above=self.accept_above,
                )

        def numbers() -> None:
            found.from_papers = trials_from_papers(
                session,
                claim,
                numbers=research.numbers,
                registry=research.registry,
                backend=backend,
                now=now,
                papers=papers,
                reject_below=self.reject_below,
                accept_above=self.accept_above,
            )

        def origin() -> None:
            if papers is not None:
                found.origin = choose_origin(
                    session,
                    claim,
                    papers=papers,
                    backend=backend,
                    now=now,
                    accept_above=self.accept_above,
                )

        for part in (organisations, search, numbers, origin):
            answer = attempt(session, part)
            if isinstance(answer, SourceError):
                return put_off(answer, now)
            if isinstance(answer, DecisionFailed | LlmError):
                return model_failed(answer)
        if isinstance(papers, OpenAlex):
            found.usage = papers.usage.line()
        self.results[claim.id] = found
        if papers is None:
            return NeedsFix(PAPERS_OFF)
        return WorkOutcome.DONE


def _has_papers(session: Session, claim: Claim) -> bool:
    """Whether the claim has any paper candidate, in any state."""
    return (
        session.scalars(
            select(EntityMatch.id)
            .join(Entity, Entity.id == EntityMatch.entity_id)
            .where(Entity.claim_id == claim.id, EntityMatch.source_name == OpenAlex.name)
        ).first()
        is not None
    )
