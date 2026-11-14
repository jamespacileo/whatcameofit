"""The steps that use decisions, and what each is shown."""

import json
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from thenwhat.db.models import Claim, ClaimTerm, DecisionLog, Entity, EntityMatch
from thenwhat.decide.core import Backend, Decision, DecisionFailed, decide, decide_many
from thenwhat.domain import EntityType, EvidenceStage, TermRole
from thenwhat.sources import openalex
from thenwhat.sources.base import SourceRecord

EVIDENCE_STAGE = "evidence_stage"
ENTITY_MATCH = "entity_match"
MATCH = "match"
NOT_A_MATCH = "not_a_match"
# The record is about the claim's intervention, but for a different condition.
OTHER_INDICATION = "other_indication"
MAX_CANDIDATE_CHARACTERS = 1500

# What is asked about a trial record: a claim is one intervention for one indication,
# so the same intervention in another condition is its own answer.
TRIAL_OPTIONS = [MATCH, OTHER_INDICATION, NOT_A_MATCH]
TRIAL_QUESTION = (
    "Is this record a trial of the claim's intervention for the claim's indication?\n"
    f"- {MATCH}: it tests this intervention in the claim's indication, in a form of"
    " that condition, or in patients who have it.\n"
    f"- {OTHER_INDICATION}: it tests this intervention for a different condition,"
    " or only in healthy volunteers.\n"
    f"- {NOT_A_MATCH}: it is not a trial of this intervention."
)

PAPER_MATCH = "paper_match"
REVIEW_OR_COMMENTARY = "review_or_commentary"
UNRELATED = "unrelated"
MAX_PAPER_CHARACTERS = 3000
# What is asked about a paper a literature search found. The first two options are the
# ones asked about a trial, so a paper's score and its another-indication label are read
# the way a trial's are.
PAPER_OPTIONS = [MATCH, OTHER_INDICATION, REVIEW_OR_COMMENTARY, UNRELATED]
PAPER_QUESTION = (
    "What is this paper to the claim?\n"
    f"- {MATCH}: it reports a study of the claim's intervention for the claim's"
    " indication.\n"
    f"- {OTHER_INDICATION}: it reports a study of this intervention for a different"
    " condition.\n"
    f"- {REVIEW_OR_COMMENTARY}: it is a review, an editorial or a commentary, not a"
    " report of one study.\n"
    f"- {UNRELATED}: it is not about this intervention."
)

ORIGIN_PAPER = "origin_paper"
NO_PAPER = "none"

TERM_MATCH = "term_match"
SAME = "same"
BROADER = "broader"
SOMETHING_ELSE = "something_else"
# What is asked about a candidate subject term (openspec knowledge-cards).
TERM_OPTIONS = [SAME, BROADER, SOMETHING_ELSE]
TERM_QUESTIONS = {
    TermRole.CONDITION: (
        "What is this vocabulary term to the claim's indication?\n"
        f"- {SAME}: it names the condition the claim is about, or is another name for it.\n"
        f"- {BROADER}: it names a wider group of conditions that includes the claim's"
        " indication.\n"
        f"- {SOMETHING_ELSE}: it names a different condition, only one form of the"
        " claim's indication, or something that is not a condition."
    ),
    TermRole.INTERVENTION: (
        "What is this vocabulary term to the claim's intervention?\n"
        f"- {SAME}: it names the claim's intervention, or is another name for it.\n"
        f"- {BROADER}: it names a class or kind of treatment that includes the claim's"
        " intervention.\n"
        f"- {SOMETHING_ELSE}: it names a different treatment, such as another drug given"
        " in the same trials, or something that is not the claim's intervention."
    ),
}


STATEMENT_CHECK = "statement_check"
SAYS_THIS = "says_this"
SAYS_SOMETHING_WEAKER = "says_something_weaker"
DOES_NOT_SAY = "does_not_say"
# What is asked about a reported statement (openspec reported-statements). The middle
# option is there for a statement worded more firmly than its article, so that it lowers
# the probability of the first instead of being split between yes and no.
STATEMENT_OPTIONS = [SAYS_THIS, SAYS_SOMETHING_WEAKER, DOES_NOT_SAY]
STATEMENT_QUESTION = (
    "Does the article say this, as it is put here: as firmly, said by the same kind of"
    " person, and resting on what the article says it rests on?\n"
    f"- {SAYS_THIS}: the article says this, no more firmly or widely than it is put here.\n"
    f"- {SAYS_SOMETHING_WEAKER}: the article says something like this, but less firmly,"
    " more narrowly, with less behind it, or said by someone else.\n"
    f"- {DOES_NOT_SAY}: the article does not say this."
)


def match_ref(match_id: int) -> str:
    """The decision log's reference to a candidate match."""
    return f"{ENTITY_MATCH}:{match_id}"


def latest_scoring(session: Session, match: EntityMatch) -> DecisionLog | None:
    """The latest decision that scored the candidate without an error, if any."""
    return session.scalars(
        select(DecisionLog)
        .where(
            DecisionLog.step.in_([ENTITY_MATCH, PAPER_MATCH]),
            DecisionLog.input_ref == match_ref(match.id),
            DecisionLog.error.is_(None),
        )
        .order_by(DecisionLog.id.desc())
    ).first()


def candidate_text(record: SourceRecord) -> str:
    """A registry record as it is shown to the backend."""
    return (
        f"Candidate record from {record.source_name} ({record.external_id}):\n{_describe(record)}"
    )


def _claim_text(session: Session, claim: Claim) -> str:
    intervention = session.scalars(
        select(Entity).where(Entity.claim_id == claim.id, Entity.type == EntityType.INTERVENTION)
    ).first()
    names = ""
    if intervention is not None:
        also = (
            f" (also known as: {', '.join(intervention.synonyms)})" if intervention.synonyms else ""
        )
        names = f"Intervention: {intervention.name}{also}.\n"
    summary = f"{claim.summary}\n" if claim.summary else ""
    return f"Claim: {claim.headline}\n{summary}{names}Indication: {claim.indication}."


def has_stage_suggestion(session: Session, claim: Claim) -> bool:
    return (
        session.scalars(
            select(DecisionLog.id).where(
                DecisionLog.step == EVIDENCE_STAGE,
                DecisionLog.input_ref == f"claim:{claim.id}",
                DecisionLog.error.is_(None),
            )
        ).first()
        is not None
    )


def suggest_evidence_stage(
    session: Session, backend: Backend, claim: Claim, *, now: datetime
) -> Decision:
    """Suggest the stage of evidence at announcement. The claim's stage is not set here:
    it stays empty until an operator confirms it."""
    return decide(
        session,
        backend,
        step=EVIDENCE_STAGE,
        state=_claim_text(session, claim)
        + "\n\nHow far had the evidence come when this was announced?",
        options=[stage.value for stage in EvidenceStage],
        input_ref=f"claim:{claim.id}",
        now=now,
    )


def score_matches(
    session: Session,
    backend: Backend,
    *,
    claim: Claim,
    candidates: list[tuple[Entity, EntityMatch, SourceRecord]],
    now: datetime,
) -> None:
    """Set each candidate's score: the probability that its registry record is evidence
    for the claim. Scores order the review queue, and the resolver's rules approve or
    reject on them; this function decides nothing.

    A claim is one intervention for one indication, so a trial is a match only when it
    tests that intervention for that indication. The same intervention in another
    condition is its own answer, so the reviewer can be told which it was. A paper is
    only asked whether it is the same paper. An entity's candidates are scored together,
    several to a backend call.
    """
    by_entity: dict[int, list[tuple[Entity, EntityMatch, SourceRecord]]] = {}
    for candidate in candidates:
        by_entity.setdefault(candidate[0].id, []).append(candidate)
    for group in by_entity.values():
        entity = group[0][0]
        if entity.type is EntityType.INTERVENTION:
            options = TRIAL_OPTIONS
            question = TRIAL_QUESTION
        else:
            options = [MATCH, NOT_A_MATCH]
            question = "Is this record about the same entity as the claim?"
        decisions = decide_many(
            session,
            backend,
            step=ENTITY_MATCH,
            intro=(
                f"{_claim_text(session, claim)}\n\nEntity to match ({entity.type}): {entity.name}"
            ),
            question=question,
            items=[(match_ref(match.id), candidate_text(record)) for _, match, record in group],
            options=options,
            now=now,
        )
        for (_, match, _), decision in zip(group, decisions, strict=True):
            match.score = decision.probabilities[MATCH]


def paper_text(record: SourceRecord) -> str:
    """A paper as it is shown to the backend: title, year, kind, journal and abstract.
    The abstract goes no further than the question; the decision log keeps none of it."""
    paper = openalex.describe(record)
    lines = [
        f"Candidate paper ({record.external_id}):",
        f"Title: {paper.title}",
        f"Year: {paper.year or 'not given'}",
        f"Kind: {paper.kind or 'not given'}",
        f"Journal: {paper.journal or 'not given'}",
        f"Abstract: {paper.abstract or 'not given'}",
    ]
    return "\n".join(lines)[:MAX_PAPER_CHARACTERS]


def score_papers(
    session: Session,
    backend: Backend,
    *,
    claim: Claim,
    candidates: list[tuple[EntityMatch, SourceRecord]],
    now: datetime,
) -> None:
    """Set each paper candidate's score: the probability that it reports a study of the
    claim's intervention for the claim's indication. This function decides nothing."""
    decisions = decide_many(
        session,
        backend,
        step=PAPER_MATCH,
        intro=_claim_text(session, claim),
        question=PAPER_QUESTION,
        items=[(match_ref(match.id), paper_text(record)) for match, record in candidates],
        options=PAPER_OPTIONS,
        now=now,
    )
    for (match, _), decision in zip(candidates, decisions, strict=True):
        match.score = decision.probabilities[MATCH]


def term_ref(term: ClaimTerm) -> str:
    """The decision log's reference to a candidate subject term: the claim and the term."""
    return f"claim:{term.claim_id}:{term.role.value}:{term.source_name}:{term.external_id}"


def term_text(term: ClaimTerm, definition: str | None) -> str:
    """A subject term as it is shown to the backend: its label and its definition."""
    return (
        f"Candidate term ({term.source_name} {term.external_id}): {term.label}\n"
        f"Definition: {definition or 'none given'}"
    )


def check_terms(
    session: Session,
    backend: Backend,
    *,
    claim: Claim,
    role: TermRole,
    candidates: list[tuple[ClaimTerm, str | None]],
    now: datetime,
) -> list[Decision | None]:
    """Ask, for each candidate term given with its definition, whether it is the claim's
    condition (or intervention), a broader term, or something else. Decides nothing.

    Every candidate gets its own log record. A candidate the backend gave no usable
    answer for comes back as None: the failure is in its log record and it has no answer.
    """
    refs = [term_ref(term) for term, _ in candidates]
    return _each_answered(
        session,
        backend,
        step=TERM_MATCH,
        intro=_claim_text(session, claim),
        question=TERM_QUESTIONS[role],
        items=[
            (ref, term_text(term, definition))
            for ref, (term, definition) in zip(refs, candidates, strict=True)
        ],
        options=TERM_OPTIONS,
        now=now,
    )


def statement_ref(article_id: int, place: int) -> str:
    """The decision log's reference to a proposed statement: its article and its place
    among the statements proposed for that article, counted from one. The statement row
    keeps the same string, so a later human label can be joined to the record."""
    return f"source_article:{article_id}:statement:{place}"


def last_statement_place(session: Session, article_id: int) -> int:
    """The highest place a statement of the article was checked at, or 0. A later read
    counts on from it, so that every check of the article has its own reference."""
    prefix = statement_ref(article_id, 0).removesuffix("0")
    refs = session.scalars(
        select(DecisionLog.input_ref).where(
            DecisionLog.step == STATEMENT_CHECK, DecisionLog.input_ref.startswith(prefix)
        )
    )
    return max((int(ref.removeprefix(prefix)) for ref in refs), default=0)


def check_statements(
    session: Session,
    backend: Backend,
    *,
    article_text: str,
    statements: list[tuple[str, str]],
    now: datetime,
) -> list[Decision | None]:
    """Ask, for each proposed statement given as (reference, how it is put), whether the
    article says it, says something weaker, or does not say it. Decides nothing.

    The article's text is shown to the backend and goes no further: the log records hold
    the reference and the answer, neither the article nor the statement. A statement the
    backend gave no usable answer for comes back as None, with the failure in its record.
    """
    if not statements:
        return []
    return _each_answered(
        session,
        backend,
        step=STATEMENT_CHECK,
        intro=f"A news article follows.\n\nArticle:\n{article_text}",
        question=STATEMENT_QUESTION,
        items=statements,
        options=STATEMENT_OPTIONS,
        now=now,
    )


def _each_answered(
    session: Session,
    backend: Backend,
    *,
    step: str,
    intro: str,
    question: str,
    items: list[tuple[str, str]],
    options: list[str],
    now: datetime,
) -> list[Decision | None]:
    """`decide_many`, with an item that has no usable answer given as None instead of
    failing the rest. Every item keeps its own log record."""
    before = session.scalar(select(func.max(DecisionLog.id))) or 0
    refs = [ref for ref, _ in items]
    try:
        return list(
            decide_many(
                session,
                backend,
                step=step,
                intro=intro,
                question=question,
                items=items,
                options=options,
                now=now,
            )
        )
    except DecisionFailed:
        # Some items of the batch may have been answered before the failure.
        answered = {
            entry.input_ref: entry
            for entry in session.scalars(
                select(DecisionLog)
                .where(
                    DecisionLog.step == step,
                    DecisionLog.id > before,
                    DecisionLog.input_ref.in_(refs),
                    DecisionLog.error.is_(None),
                )
                .order_by(DecisionLog.id)
            )
        }
        return [_logged(answered.get(ref)) for ref in refs]


def _logged(entry: DecisionLog | None) -> Decision | None:
    if entry is None or entry.output is None or entry.confidence is None:
        return None
    return Decision(
        entry.output["choice"], entry.output["probabilities"], entry.confidence, entry.id
    )


def has_origin_choice(session: Session, claim: Claim, offered: list[str]) -> bool:
    """Whether the origin paper was already asked about with exactly these papers."""
    asked = session.scalars(
        select(DecisionLog)
        .where(
            DecisionLog.step == ORIGIN_PAPER,
            DecisionLog.input_ref == f"claim:{claim.id}",
            DecisionLog.error.is_(None),
        )
        .order_by(DecisionLog.id.desc())
    ).first()
    return asked is not None and asked.options == [*offered, NO_PAPER]


def choose_origin_paper(
    session: Session,
    backend: Backend,
    claim: Claim,
    *,
    offered: list[tuple[str, str]],
    now: datetime,
) -> Decision:
    """Ask which of the offered papers, given as (identifier, one line about it), is the
    one the first reports were about, or none of them. The caller applies the rule."""
    listed = "\n".join(f"- {identifier}: {line}" for identifier, line in offered)
    reported = claim.first_reported_date.isoformat() if claim.first_reported_date else "unknown"
    return decide(
        session,
        backend,
        step=ORIGIN_PAPER,
        state=(
            f"{_claim_text(session, claim)}\nFirst reported: {reported}.\n\n"
            f"Papers published by then:\n{listed}\n\n"
            "Which paper is the one those first reports were about? Answer with its"
            f" identifier, or '{NO_PAPER}' if it is none of them or you cannot tell."
        ),
        options=[*(identifier for identifier, _ in offered), NO_PAPER],
        input_ref=f"claim:{claim.id}",
        now=now,
    )


def _describe(candidate: SourceRecord) -> str:
    """What the record says, with a trial's conditions and interventions first so that a
    long record is never cut off before them."""
    section = candidate.payload.get("protocolSection")
    if isinstance(section, dict):
        identification = section.get("identificationModule", {})
        described = {
            "title": identification.get("briefTitle"),
            "official_title": identification.get("officialTitle"),
            "conditions": section.get("conditionsModule", {}).get("conditions", []),
            "interventions": [
                intervention.get("name")
                for intervention in section.get("armsInterventionsModule", {}).get(
                    "interventions", []
                )
            ],
            "phases": section.get("designModule", {}).get("phases", []),
            "status": section.get("statusModule", {}).get("overallStatus"),
            "sponsor": section.get("sponsorCollaboratorsModule", {})
            .get("leadSponsor", {})
            .get("name"),
        }
        text = json.dumps(
            {name: value for name, value in described.items() if value}, ensure_ascii=False
        )
    else:
        text = json.dumps(candidate.payload, ensure_ascii=False, sort_keys=True)
    return text[:MAX_CANDIDATE_CHARACTERS]
