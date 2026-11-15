"""Proposing, scoring and deciding subject terms for a claim, and keeping each term's
record. Behavior: openspec knowledge-cards.

A link between a claim and a term never rests on a lookup or on the registry's filing
alone: every candidate is put to the term check, and rules decide on its score. Nothing
here is an input to a claim's status.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entities import entities_of, intervention_components, whole_intervention_names
from thenwhat.claims.entry import name_key
from thenwhat.claims.mesh_areas import approved_trial_payloads
from thenwhat.db.models import Claim, ClaimTerm, TermRecord
from thenwhat.decide.core import Backend
from thenwhat.decide.steps import (
    ACTS_ON,
    BROADER,
    NONE_OF_THESE,
    SAME,
    check_targets,
    check_terms,
    choose_intervention_kind,
    has_kind_answer,
)
from thenwhat.domain import Decider, EntityType, ReviewState, TermFit, TermRole
from thenwhat.review.decisions import record_decision
from thenwhat.sources import mesh, opentargets
from thenwhat.sources.base import SourceRecord
from thenwhat.terms.candidates import LabelMatch, gather_candidates
from thenwhat.terms.drugs import DRUG_NAME_EQUALS_NAME
from thenwhat.terms.genes import WORD_EQUALS_SYMBOL, WORD_EQUALS_SYNONYM, gene_like_words
from thenwhat.terms.kinds import KIND_CHOSEN, KINDS, Kind, registry_types
from thenwhat.terms.records import read_record

# A stored term record older than this is fetched again.
RECORD_MAX_AGE = timedelta(days=90)
FITS = {SAME: TermFit.EXACT, BROADER: TermFit.BROADER}
# The roles a vocabulary term is proposed for. A named gene is not a vocabulary term.
TERM_ROLES = (TermRole.CONDITION, TermRole.INTERVENTION)


class Vocabulary(Protocol):
    name: str

    def term(self, identifier: str, *, force: bool = False) -> SourceRecord | None: ...

    def terms_labelled(self, name: str) -> list[mesh.LabelledTerm]: ...

    def unresolved_entry_terms(self, name: str) -> list[str]: ...


class Genes(Protocol):
    name: str

    def targets_named(self, word: str) -> list[opentargets.NamedTarget]: ...

    def target(self, identifier: str, *, force: bool = False) -> SourceRecord | None: ...


class Drugs(Protocol):
    name: str

    def drugs_named(self, name: str) -> list[SourceRecord]: ...

    def drug(self, identifier: str, *, force: bool = False) -> SourceRecord | None: ...


class KindTermMissing(Exception):
    """The vocabulary holds no record for the term a kind is tied to. Nothing is used
    in its place: the list of kinds is corrected."""

    def __init__(self, kind: Kind, source_name: str) -> None:
        super().__init__(
            f"The kind '{kind.code}' is tied to {source_name} {kind.identifier}"
            f" ({kind.label}), and {source_name} returned no record for it. No other term"
            " was used. Correct the list of kinds in terms/kinds.py, then run this again."
        )
        self.kind = kind


@dataclass(frozen=True, slots=True)
class TermsRun:
    """What one run did for a claim."""

    # Every candidate gathered by rule, new or not.
    gathered: int
    # The candidates this run stored for the first time.
    added: list[ClaimTerm]
    # The candidates this run got an answer for, with the rule's decision applied.
    scored: list[ClaimTerm]
    # The candidates the backend gave no usable answer for. They stay without a score.
    unscored: list[ClaimTerm]
    # The claim's names that equal an entry term whose record the vocabulary did not
    # give. They made no candidate.
    unresolved: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class KindRun:
    """What one run did about the claim's intervention kind."""

    # Whether the kind was asked for in this run.
    asked: bool
    # The code chosen, "none_of_these", or None when not asked or not answered.
    chosen: str | None = None
    # The kind link this run stored, with the rule's decision applied.
    link: ClaimTerm | None = None
    # The backend gave no usable answer. The claim is asked again on the next run.
    failed: bool = False


@dataclass(frozen=True, slots=True)
class DrugRun:
    """What one run did about the drug source's record of the claim's intervention."""

    # The claim's drug link, new or kept. None when no drug, or more than one, was found.
    link: ClaimTerm | None = None
    # Whether this run stored the link.
    added: bool = False
    # The names of the drugs found when the claim's names equal more than one drug's.
    # They make no link: a claim is about one intervention.
    several: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TargetsRun:
    """What one run did about the genes named in the claim's intervention."""

    gathered: int
    added: list[ClaimTerm]
    scored: list[ClaimTerm]
    unscored: list[ClaimTerm]


def terms_of(session: Session, claim: Claim) -> list[ClaimTerm]:
    return list(
        session.scalars(
            select(ClaimTerm).where(ClaimTerm.claim_id == claim.id).order_by(ClaimTerm.id)
        )
    )


def stored_record(
    session: Session, vocabulary: Vocabulary, identifier: str, *, now: datetime
) -> TermRecord | None:
    """The term's own record, fetched when none is stored or the stored one is older
    than ninety days. A term the vocabulary does not hold has no record; a refresh that
    finds nothing leaves the stored record as it is."""
    return _kept_record(session, vocabulary.name, vocabulary.term, identifier, now=now)


def _kept_record(
    session: Session,
    source_name: str,
    fetch: Callable[..., SourceRecord | None],
    identifier: str,
    *,
    now: datetime,
) -> TermRecord | None:
    kept = session.get(TermRecord, (source_name, identifier))
    if kept is not None and now - kept.fetched_at <= RECORD_MAX_AGE:
        return kept
    record = fetch(identifier, force=kept is not None)
    if record is None:
        return kept
    if kept is None:
        kept = TermRecord(source_name=record.source_name, external_id=record.external_id)
        session.add(kept)
    kept.url = record.url
    kept.payload = record.payload
    kept.fetched_at = record.fetched_at
    session.flush()
    return kept


def _definition(record: TermRecord | None) -> str | None:
    return read_record(record).definition if record is not None else None


def intervention_names(session: Session, claim: Claim) -> list[str]:
    """The claim's intervention's name and its other names. Search phrases are not
    names: they were written for searching the registry."""
    return whole_intervention_names(
        [
            name
            for entity in entities_of(session, claim)
            if entity.type is EntityType.INTERVENTION
            for name in [entity.name, *entity.synonyms]
            if name.strip()
        ]
    )


def _label_matches(
    session: Session, claim: Claim, vocabulary: Vocabulary
) -> tuple[list[LabelMatch], list[str]]:
    """Vocabulary terms whose label or entry term equals the claim's indication, its
    intervention's name or one of the intervention's other names; and the names that
    equal an entry term whose record the vocabulary did not give."""
    names = [(TermRole.CONDITION, claim.indication)] if claim.indication.strip() else []
    names += [(TermRole.INTERVENTION, name) for name in intervention_names(session, claim)]
    matches = [
        LabelMatch(role, term.identifier, term.label, name, term.entry_term)
        for role, name in names
        for term in vocabulary.terms_labelled(name)
    ]
    unresolved = [name for _, name in names if vocabulary.unresolved_entry_terms(name)]
    return matches, list(dict.fromkeys(unresolved))


def link_terms(
    session: Session,
    claim: Claim,
    *,
    vocabulary: Vocabulary,
    backend: Backend,
    now: datetime,
    limit: int = 10,
    accept_above: float = 0.0,
    reject_below: float = 0.0,
) -> TermsRun:
    """Gather the claim's candidate subject terms, score those without a score and
    decide them by rule, and keep the record of every approved term.

    A candidate's score is the probability of the answer chosen when the term was read
    as the claim's own condition or intervention, or as broader, and zero otherwise. One
    scored at or above `accept_above` is approved by rule (0 turns that off); one under
    `reject_below` is rejected by rule; the rest wait for review. A candidate that
    already has a score is left exactly as it is, so a link the operator rejected stays
    rejected. A name equal to an entry term whose record the vocabulary did not give
    makes no candidate and is named in the run's result.
    """
    label_matches, unresolved = _label_matches(session, claim, vocabulary)
    candidates = gather_candidates(
        trial_payloads=approved_trial_payloads(session, claim),
        label_matches=label_matches,
        limit=limit,
    )
    names = intervention_names(session, claim)
    components = intervention_components(names[0]) if names else set()
    candidates = [
        candidate
        for candidate in candidates
        if candidate.role is not TermRole.INTERVENTION
        or name_key(candidate.label) not in components
    ]
    known = {(term.role, term.source_name, term.external_id) for term in terms_of(session, claim)}
    added: list[ClaimTerm] = []
    for candidate in candidates:
        key = (candidate.role, candidate.source_name, candidate.identifier)
        if key in known:
            continue
        known.add(key)
        term = ClaimTerm(
            claim_id=claim.id,
            role=candidate.role,
            source_name=candidate.source_name,
            external_id=candidate.identifier,
            label=candidate.label,
            reasons=list(candidate.reasons),
        )
        session.add(term)
        added.append(term)
    session.flush()

    waiting = [
        term
        for term in terms_of(session, claim)
        if term.score is None
        and term.review_state is ReviewState.PENDING
        and term.source_name == vocabulary.name
        and (term.role is not TermRole.INTERVENTION or name_key(term.label) not in components)
    ]
    scored: list[ClaimTerm] = []
    unscored: list[ClaimTerm] = []
    for role in TERM_ROLES:
        asked = [
            (term, _definition(stored_record(session, vocabulary, term.external_id, now=now)))
            for term in waiting
            if term.role is role
        ]
        if not asked:
            continue
        decisions = check_terms(session, backend, claim=claim, role=role, candidates=asked, now=now)
        for (term, _), decision in zip(asked, decisions, strict=True):
            if decision is None:
                unscored.append(term)
                continue
            term.fit = FITS.get(decision.choice)
            term.score = decision.probabilities[decision.choice] if term.fit else 0.0
            _decide_by_rule(term, now=now, accept_above=accept_above, reject_below=reject_below)
            scored.append(term)

    for term in terms_of(session, claim):
        if term.review_state is ReviewState.APPROVED and term.source_name == vocabulary.name:
            stored_record(session, vocabulary, term.external_id, now=now)
    session.flush()
    return TermsRun(len(candidates), added, scored, unscored, unresolved)


def _decide_by_rule(
    term: ClaimTerm, *, now: datetime, accept_above: float, reject_below: float
) -> None:
    """Approve a link scored at or above `accept_above` (0 turns that off), reject one
    under `reject_below`, and leave the rest pending."""
    assert term.score is not None
    if accept_above > 0 and term.score >= accept_above:
        record_decision(term, ReviewState.APPROVED, by=Decider.RULE, now=now)
    elif term.score < reject_below:
        record_decision(term, ReviewState.REJECTED, by=Decider.RULE, now=now)


def link_kind(
    session: Session,
    claim: Claim,
    *,
    vocabulary: Vocabulary,
    backend: Backend,
    now: datetime,
    kinds: tuple[Kind, ...] = KINDS,
    accept_above: float = 0.0,
    reject_below: float = 0.0,
) -> KindRun:
    """Give the claim's intervention its kind, when it has no exact term of its own.

    The kind is asked for only when the claim has an intervention, no approved exact
    intervention term, no kind link, and no answer on record for this same list of
    kinds. The chosen kind's term becomes a kind link scored with the probability of
    the choice and decided by the two thresholds, unless that term is already a link
    for the claim's intervention: then nothing is stored and that link stands as it is.
    "None of these" stores nothing. The kind is never taken from the registry's type,
    which is carried as a reason only.
    """
    names = intervention_names(session, claim)
    links = [term for term in terms_of(session, claim) if term.role is TermRole.INTERVENTION]
    offered = [(kind.code, kind.label) for kind in kinds]
    if (
        not names
        or any(link.fit is TermFit.KIND for link in links)
        or any(
            link.fit is TermFit.EXACT and link.review_state is ReviewState.APPROVED
            for link in links
        )
        or has_kind_answer(session, claim, offered)
    ):
        return KindRun(asked=False)

    decision = choose_intervention_kind(session, backend, claim, kinds=offered, now=now)
    if decision is None:
        return KindRun(asked=True, failed=True)
    if decision.choice == NONE_OF_THESE:
        return KindRun(asked=True, chosen=NONE_OF_THESE)
    kind = next(kind for kind in kinds if kind.code == decision.choice)
    record = stored_record(session, vocabulary, kind.identifier, now=now)
    if record is None:
        raise KindTermMissing(kind, vocabulary.name)
    if any(
        link.source_name == vocabulary.name and link.external_id == kind.identifier
        for link in links
    ):
        return KindRun(asked=True, chosen=kind.code)

    link = ClaimTerm(
        claim_id=claim.id,
        role=TermRole.INTERVENTION,
        source_name=vocabulary.name,
        external_id=kind.identifier,
        label=read_record(record).label or kind.label,
        score=decision.probabilities[decision.choice],
        fit=TermFit.KIND,
        reasons=[
            {"code": KIND_CHOSEN, "kind": kind.code},
            *registry_types(approved_trial_payloads(session, claim), names),
        ],
    )
    session.add(link)
    session.flush()
    _decide_by_rule(link, now=now, accept_above=accept_above, reject_below=reject_below)
    session.flush()
    return KindRun(asked=True, chosen=kind.code, link=link)


def _named_gene_reason(word: str, target: opentargets.NamedTarget) -> dict[str, object]:
    if target.equal == opentargets.SYMBOL:
        return {"code": WORD_EQUALS_SYMBOL, "word": word}
    return {"code": WORD_EQUALS_SYNONYM, "word": word, "sources": list(target.synonym_sources)}


def link_targets(
    session: Session,
    claim: Claim,
    *,
    genes: Genes,
    backend: Backend,
    now: datetime,
    limit: int = 3,
    accept_above: float = 0.0,
    reject_below: float = 0.0,
) -> TargetsRun:
    """Gather the genes named in the claim's intervention, score those without a score
    and decide them by rule, and keep the record of every approved one.

    A candidate is a gene whose approved symbol, or a listed synonym of it, equals a
    gene-like word of the intervention's names. At most `limit` are kept, a word equal
    to a symbol before a word equal to a synonym. A candidate's score is the
    probability that the intervention acts on the gene's product or is made from it,
    when that is the answer chosen, and zero otherwise. A candidate that already has a
    score is left as it is, so a link the operator rejected stays rejected.
    """
    found: dict[str, tuple[str, opentargets.NamedTarget]] = {}
    for word in gene_like_words(intervention_names(session, claim)):
        for target in genes.targets_named(word):
            found.setdefault(target.identifier, (word, target))
    candidates = sorted(found.values(), key=lambda pair: pair[1].equal != opentargets.SYMBOL)[
        : max(limit, 0)
    ]

    known = {
        term.external_id
        for term in terms_of(session, claim)
        if term.role is TermRole.TARGET and term.source_name == genes.name
    }
    added: list[ClaimTerm] = []
    for word, target in candidates:
        if target.identifier in known:
            continue
        known.add(target.identifier)
        term = ClaimTerm(
            claim_id=claim.id,
            role=TermRole.TARGET,
            source_name=genes.name,
            external_id=target.identifier,
            label=target.symbol,
            reasons=[_named_gene_reason(word, target)],
        )
        session.add(term)
        added.append(term)
    session.flush()

    waiting = [
        term
        for term in terms_of(session, claim)
        if term.role is TermRole.TARGET
        and term.source_name == genes.name
        and term.score is None
        and term.review_state is ReviewState.PENDING
    ]
    asked: list[tuple[ClaimTerm, str, str | None]] = []
    for term in waiting:
        record = _kept_record(session, genes.name, genes.target, term.external_id, now=now)
        name = opentargets.describe(_as_source_record(record)).name if record else None
        word = next((str(reason["word"]) for reason in term.reasons if reason.get("word")), "")
        asked.append((term, word, name or None))
    scored: list[ClaimTerm] = []
    unscored: list[ClaimTerm] = []
    decisions = check_targets(session, backend, claim=claim, candidates=asked, now=now)
    for (term, _, _), decision in zip(asked, decisions, strict=True):
        if decision is None:
            unscored.append(term)
            continue
        acts_on = decision.choice == ACTS_ON
        term.fit = TermFit.EXACT if acts_on else None
        term.score = decision.probabilities[decision.choice] if acts_on else 0.0
        _decide_by_rule(term, now=now, accept_above=accept_above, reject_below=reject_below)
        scored.append(term)

    for term in terms_of(session, claim):
        if (
            term.role is TermRole.TARGET
            and term.source_name == genes.name
            and term.review_state is ReviewState.APPROVED
        ):
            _kept_record(session, genes.name, genes.target, term.external_id, now=now)
    session.flush()
    return TargetsRun(len(candidates), added, scored, unscored)


def link_drug(session: Session, claim: Claim, *, drugs: Drugs, now: datetime) -> DrugRun:
    """Tie the claim's intervention to the drug source's record of it, by exact name.

    A drug is found only when its own name in the source equals the intervention's name
    or one of its other names, whatever the case. The link is made by that rule alone:
    it has no score, it is approved by rule, and the operator can reject it. When the
    claim's names equal the names of several different drugs, as they do when a class
    of drugs lists its members among its other names, no link is made.
    A link that already exists is left as it is, so a rejected one stays rejected.
    """
    found: dict[str, tuple[str, SourceRecord]] = {}
    for name in intervention_names(session, claim):
        for record in drugs.drugs_named(name):
            found.setdefault(record.external_id, (name, record))
    if len(found) != 1:
        labels = sorted(opentargets.describe_drug(record).name for _, record in found.values())
        return DrugRun(several=tuple(labels))
    [(identifier, (name, record))] = found.items()

    link = next(
        (
            term
            for term in terms_of(session, claim)
            if term.role is TermRole.DRUG
            and term.source_name == drugs.name
            and term.external_id == identifier
        ),
        None,
    )
    added = link is None
    if link is None:
        link = ClaimTerm(
            claim_id=claim.id,
            role=TermRole.DRUG,
            source_name=drugs.name,
            external_id=identifier,
            label=opentargets.describe_drug(record).name,
            fit=TermFit.EXACT,
            reasons=[{"code": DRUG_NAME_EQUALS_NAME, "name": name}],
        )
        session.add(link)
        session.flush()
        record_decision(link, ReviewState.APPROVED, by=Decider.RULE, now=now)
    if link.review_state is ReviewState.APPROVED:
        _kept_record(session, drugs.name, drugs.drug, identifier, now=now)
    session.flush()
    return DrugRun(link=link, added=added)


def _as_source_record(record: TermRecord) -> SourceRecord:
    return SourceRecord(
        record.source_name, record.external_id, record.url, record.payload, record.fetched_at
    )


def published_claims(session: Session) -> list[Claim]:
    """Every published claim."""
    return list(
        session.scalars(
            select(Claim)
            .where(Claim.review_state == ReviewState.APPROVED, Claim.archived_at.is_(None))
            .order_by(Claim.slug)
        )
    )


def claims_without_terms(session: Session) -> list[Claim]:
    """Every published claim that has no candidate subject term yet."""
    linked = select(ClaimTerm.claim_id)
    return list(
        session.scalars(
            select(Claim)
            .where(
                Claim.review_state == ReviewState.APPROVED,
                Claim.archived_at.is_(None),
                Claim.id.not_in(linked),
            )
            .order_by(Claim.slug)
        )
    )
