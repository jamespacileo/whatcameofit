"""Candidates an article's own page gives: the registry numbers and paper DOIs it names.
Behavior: openspec lead-reading, "Registry numbers and papers the page gives".

Nothing is searched for. Each number or DOI is read from its source by that identifier,
stored as a candidate on the claim's intervention with the reason that the article names
it, and then scored and decided by the same rules as a candidate a search found. Being
named approves nothing: an article can name a trial of another treatment, or of the same
treatment for another condition.
"""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entities import entities_of
from thenwhat.db.models import Claim, Entity, EntityMatch
from thenwhat.decide.core import Backend, DecisionFailed
from thenwhat.decide.steps import score_matches, score_papers
from thenwhat.domain import Decider, EntityType, ReviewState
from thenwhat.resolve.papers import PAPER_SOURCE, PaperSearch, TrialRegistry, paper_line
from thenwhat.resolve.papers import _reasons as paper_reasons_of
from thenwhat.resolve.reasons import NAMED_IN_ARTICLE
from thenwhat.resolve.service import approve_confident, facts_of, reject_near_zero, what_it_says
from thenwhat.review.decisions import record_decision
from thenwhat.sources.base import SourceRecord
from thenwhat.sources.clinicaltrials import ClinicalTrials


def candidates_named_in_article(
    session: Session,
    claim: Claim,
    *,
    registry_numbers: Sequence[str],
    dois: Sequence[str],
    registry: TrialRegistry,
    papers: PaperSearch | None,
    backend: Backend,
    now: datetime,
    reject_below: float = 0.0,
    accept_trial_above: float = 0.0,
    accept_paper_above: float = 0.0,
    unasked_dois: list[str] | None = None,
) -> list[EntityMatch]:
    """Store the trials and papers an article's page names as candidates of the claim,
    scored for the claim's indication. Returns the candidates this call added.

    `registry_numbers` and `dois` are what the page gave (`extract.page.Page`). A number
    or DOI its source does not have adds nothing. A candidate the claim already has
    keeps its score and its state, whatever they are, and gains the reason. Each new one
    is decided by rule exactly as a searched one: rejected under `reject_below`; a trial
    approved at or above `accept_trial_above` only when it was scored for the claim's
    indication; a paper approved at or above `accept_paper_above`. 0 turns an approval
    off. If a candidate cannot be scored, none of this call's candidates are kept.

    A paper the page gives only by its PubMed number is not recorded: the literature
    source is asked by DOI. With no literature source, no paper is recorded.
    """
    intervention = next(
        (e for e in entities_of(session, claim) if e.type is EntityType.INTERVENTION), None
    )
    if intervention is None:
        return []
    have = {
        (match.source_name, match.external_id.lower()): match
        for match in session.scalars(
            select(EntityMatch).where(EntityMatch.entity_id == intervention.id)
        )
    }

    def known(source_name: str, external_id: str) -> bool:
        """True when the claim has the candidate already; it then gains the reason."""
        match = have.get((source_name, external_id.lower()))
        if match is None:
            return False
        if NAMED_IN_ARTICLE not in match.reasons:
            match.reasons = [*match.reasons, NAMED_IN_ARTICLE]
        return True

    trials: list[tuple[Entity, EntityMatch, SourceRecord]] = []
    for number in dict.fromkeys(number.upper() for number in registry_numbers):
        if known(ClinicalTrials.name, number):
            continue
        record = registry.fetch_trial(number)
        # The registry may answer an old number with the record under its current one.
        if record is None or known(record.source_name, record.external_id):
            continue
        match = EntityMatch(
            entity_id=intervention.id,
            source_name=record.source_name,
            external_id=record.external_id,
            score=0.0,
            record_summary=what_it_says(record),
            record_facts=facts_of(record),
            reasons=[NAMED_IN_ARTICLE],
        )
        have[(match.source_name, match.external_id.lower())] = match
        trials.append((intervention, match, record))

    found: list[tuple[EntityMatch, SourceRecord]] = []
    for doi in dict.fromkeys(doi.lower() for doi in dois):
        if known(PAPER_SOURCE, doi):
            continue
        if papers is None:
            if unasked_dois is not None:
                unasked_dois.append(doi)
            continue
        record = papers.paper(doi)
        if record is None or known(PAPER_SOURCE, record.external_id):
            continue
        match = EntityMatch(
            entity_id=intervention.id,
            source_name=PAPER_SOURCE,
            external_id=record.external_id,
            score=0.0,
            record_summary=paper_line(record),
            reasons=[*paper_reasons_of(session, claim, intervention, record), NAMED_IN_ARTICLE],
        )
        have[(match.source_name, match.external_id.lower())] = match
        found.append((match, record))

    trial_matches = [match for _, match, _ in trials]
    paper_matches = [match for match, _ in found]
    added = [*trial_matches, *paper_matches]
    session.add_all(added)
    session.flush()
    try:
        score_matches(session, backend, claim=claim, candidates=trials, now=now)
        score_papers(session, backend, claim=claim, candidates=found, now=now)
    except DecisionFailed:
        # The decision log keeps the failure; the unscored candidates are withdrawn.
        for match in added:
            session.delete(match)
        session.flush()
        raise
    reject_near_zero(added, reject_below, now)
    approve_confident(session, trial_matches, accept_trial_above, now)
    if accept_paper_above > 0:
        for match in paper_matches:
            if match.review_state is ReviewState.PENDING and match.score >= accept_paper_above:
                record_decision(match, ReviewState.APPROVED, by=Decider.RULE, now=now)
    session.flush()
    return added
