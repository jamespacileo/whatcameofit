"""The steps that use decisions, and what each is shown."""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from thenwhat.claims.entities import development_codes, whole_intervention_names
from thenwhat.claims.entry import NamedClaim
from thenwhat.claims.verticals import VERTICALS
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
        " in the same trials, just one component of the claim's combination regimen,"
        " or something that is not the claim's intervention. A component is neither"
        " the complete regimen nor a broader class containing that regimen."
    ),
}

INTERVENTION_KIND = "intervention_kind"
NONE_OF_THESE = "none_of_these"

TARGET_MATCH = "target_match"
ACTS_ON = "acts_on_or_made_from"
# What is asked about a gene named in the claim's intervention (openspec knowledge-cards).
TARGET_OPTIONS = [ACTS_ON, SOMETHING_ELSE]
TARGET_QUESTION = (
    "A word of the intervention's name equals this human gene's symbol, or a listed"
    " synonym of it. Is that what the word means here?\n"
    f"- {ACTS_ON}: the word names this gene or its product, and the intervention acts"
    " on that product or is made from it.\n"
    f"- {SOMETHING_ELSE}: the word means something else here, such as an abbreviation"
    " of a procedure or a product code, or the intervention has nothing to do with"
    " this gene."
)


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
    return f"{_intervention_text(session, claim)}\nIndication: {claim.indication}."


def _intervention_text(session: Session, claim: Claim) -> str:
    """The claim as a kind or a named gene is judged against: its headline, summary
    and intervention names, without its indication."""
    intervention = session.scalars(
        select(Entity).where(Entity.claim_id == claim.id, Entity.type == EntityType.INTERVENTION)
    ).first()
    names = ""
    if intervention is not None:
        aliases = whole_intervention_names([intervention.name, *intervention.synonyms])[1:]
        also = f" (also known as: {', '.join(aliases)})" if aliases else ""
        codes = development_codes(session, intervention)
        coded = f" (development codes: {', '.join(codes)})" if codes else ""
        names = f"\nIntervention: {intervention.name}{also}{coded}."
    summary = f"\n{claim.summary}" if claim.summary else ""
    return f"Claim: {claim.headline}{summary}{names}"


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


def kind_options(kinds: Sequence[tuple[str, str]]) -> list[str]:
    """What the kind step offers for a list of kinds, given as (code, label)."""
    return [*(code for code, _ in kinds), NONE_OF_THESE]


def has_kind_answer(session: Session, claim: Claim, kinds: Sequence[tuple[str, str]]) -> bool:
    """Whether the claim's kind was already chosen from exactly this list of kinds."""
    asked = session.scalars(
        select(DecisionLog)
        .where(
            DecisionLog.step == INTERVENTION_KIND,
            DecisionLog.input_ref == f"claim:{claim.id}",
            DecisionLog.error.is_(None),
        )
        .order_by(DecisionLog.id.desc())
    ).first()
    return asked is not None and asked.options == kind_options(kinds)


def choose_intervention_kind(
    session: Session,
    backend: Backend,
    claim: Claim,
    *,
    kinds: Sequence[tuple[str, str]],
    now: datetime,
) -> Decision | None:
    """Ask which kind of intervention the claim's is, from the kinds given as (code,
    the vocabulary's label for it), or none of them. Decides nothing.

    One log record, referring to the claim, holds every kind's probability. A backend
    failure is in that record and comes back as None: there is no answer.
    """
    listed = "\n".join(f"- {code}: {label}" for code, label in kinds)
    try:
        return decide(
            session,
            backend,
            step=INTERVENTION_KIND,
            state=(
                f"{_intervention_text(session, claim)}\n\n"
                "What kind of intervention is the claim's? Each kind is given with the"
                f" medical vocabulary's name for it:\n{listed}\n"
                f"- {NONE_OF_THESE}: it is none of these kinds, it is several of them"
                " equally, or you cannot tell.\n\n"
                "Choose the kind the intervention itself is, not what it is made with,"
                " how it is given or what it is compared with."
            ),
            options=kind_options(kinds),
            input_ref=f"claim:{claim.id}",
            now=now,
        )
    except DecisionFailed:
        return None


def target_text(term: ClaimTerm, word: str, name: str | None) -> str:
    """A candidate gene as it is shown to the backend: the word of the intervention's
    name that was equal, the gene's symbol and its name."""
    return (
        f"Word in the intervention's name: {word}\n"
        f"Candidate gene ({term.source_name} {term.external_id}): {term.label}\n"
        f"Gene name: {name or 'not given'}"
    )


def check_targets(
    session: Session,
    backend: Backend,
    *,
    claim: Claim,
    candidates: list[tuple[ClaimTerm, str, str | None]],
    now: datetime,
) -> list[Decision | None]:
    """Ask, for each candidate gene given with the word that equals it and the gene's
    name, whether the intervention acts on the gene's product or is made from it, or
    the word means something else. Decides nothing.

    Every candidate gets its own log record, referring to the claim and the gene. A
    candidate the backend gave no usable answer for comes back as None.
    """
    if not candidates:
        return []
    return _each_answered(
        session,
        backend,
        step=TARGET_MATCH,
        intro=_intervention_text(session, claim),
        question=TARGET_QUESTION,
        items=[(term_ref(term), target_text(term, word, name)) for term, word, name in candidates],
        options=TARGET_OPTIONS,
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


# --- link lead triage (openspec lead-triage) -----------------------------------------

LEAD_TRIAGE = "lead_triage"
TREATMENT_REPORT = "treatment_report"
HEALTH_OTHER = "health_other"
NOT_HEALTH = "not_health"
TRIAGE_OPTIONS = [TREATMENT_REPORT, HEALTH_OTHER, NOT_HEALTH]
TRIAGE_INTRO = (
    "Each item is the headline of a news article, with the outlet that published it and "
    "the year it was shared. Judge from the headline alone. Nothing else is known about "
    "the article."
)
TRIAGE_QUESTION = (
    "What does this headline report?\n"
    f"- {TREATMENT_REPORT}: a result, finding or development about one specific treatment "
    "(a drug, vaccine, device, procedure or therapy, named or described) for one specific "
    "disease or condition\n"
    f"- {HEALTH_OTHER}: health or medicine, but not that: policy, an outbreak, a risk "
    "factor, advice on diet or lifestyle, a company's business, or science with no "
    "treatment for a condition\n"
    f"- {NOT_HEALTH}: not about health or medicine"
)


def lead_ref(lead_id: int) -> str:
    """The decision log's reference to a link lead."""
    return f"link_lead:{lead_id}"


def headline_text(title: str, outlet: str, year: int) -> str:
    """All that triage is shown of a link lead: its title, its outlet and the year."""
    return f"Headline: {title}\nOutlet: {outlet}\nYear shared: {year}"


def triage_headlines(
    session: Session,
    backend: Backend,
    *,
    headlines: Sequence[tuple[int, str]],
    now: datetime,
) -> list[float]:
    """For each link lead, given as (id, text), the probability that its headline reports
    a specific treatment for a specific condition. This function decides nothing."""
    decisions = decide_many(
        session,
        backend,
        step=LEAD_TRIAGE,
        intro=TRIAGE_INTRO,
        question=TRIAGE_QUESTION,
        items=[(lead_ref(lead_id), text) for lead_id, text in headlines],
        options=TRIAGE_OPTIONS,
        now=now,
    )
    return [decision.probabilities[TREATMENT_REPORT] for decision in decisions]


# --- the vertical of a claim drafted from a link lead (openspec lead-reading) ---------

VERTICAL_CHOICE = "vertical_choice"
VERTICAL_QUESTION = (
    "Which health area is this treatment filed under? Choose the area of the condition "
    "it is reported to treat, not of the kind of treatment."
)


def vertical_state(intervention: str, indication: str, summary: str) -> str:
    """What the vertical decision is shown: what was read from the article, the question,
    and every configured vertical with its title."""
    areas = "\n".join(f"- {slug}: {title}" for slug, title in VERTICALS.items())
    return (
        f"Intervention: {intervention}\nIndication: {indication}\nSummary: {summary}\n\n"
        f"{VERTICAL_QUESTION}\n{areas}"
    )


def choose_vertical(
    session: Session,
    backend: Backend,
    *,
    ref: str,
    intervention: str,
    indication: str,
    summary: str,
    now: datetime,
) -> tuple[str, float]:
    """The vertical the backend chooses among the configured ones, and the probability
    it gives that choice. A retired vertical is never offered. This function decides
    nothing: the caller accepts the choice only at or above its own setting."""
    decision = decide(
        session,
        backend,
        step=VERTICAL_CHOICE,
        state=vertical_state(intervention, indication, summary),
        options=list(VERTICALS),
        input_ref=ref,
        now=now,
    )
    return decision.choice, decision.probabilities[decision.choice]


SAME_CLAIM = "same_claim"
# The answer when the article reports none of the claims it is shown.
NO_SUCH_CLAIM = "none-of-these"
SAME_CLAIM_QUESTION = (
    "An article has been read. Does it report the same treatment for the same condition "
    "as one of the claims below? Choose a claim only when its treatment is the article's "
    "treatment and its condition is the article's condition: worded differently, more "
    "narrowly or more generally, it is still the same condition. A different condition, "
    f"or a different treatment that shares a word of the name, is {NO_SUCH_CLAIM}."
)


def same_claim_state(intervention: str, indication: str, candidates: Sequence[NamedClaim]) -> str:
    """What the same-claim decision is shown: the treatment and condition read from the
    article, the question, and each candidate claim's treatment and condition. Never a
    word of the article."""
    listed = "\n".join(
        f"- {claim.slug}: {claim.intervention} for {claim.indication}" for claim in candidates
    )
    return (
        f"Article's treatment: {intervention}\nArticle's condition: {indication}\n\n"
        f"{SAME_CLAIM_QUESTION}\n{listed}\n- {NO_SUCH_CLAIM}"
    )


@dataclass(frozen=True, slots=True)
class SameClaim:
    """What the same-claim decision answered."""

    # The candidate it chose, or None when it chose "none of these".
    slug: str | None
    # The probability it gave the candidate it thinks most likely, chosen or not.
    likeliest: str | None
    likeliest_probability: float
    # The probability it gave to the article reporting none of the candidates.
    none_probability: float


def choose_same_claim(
    session: Session,
    backend: Backend,
    *,
    ref: str,
    intervention: str,
    indication: str,
    candidates: Sequence[NamedClaim],
    now: datetime,
) -> SameClaim:
    """Which claim, among the candidates, the backend says the article reports, with the
    probability it gives its likeliest candidate and the probability it gives to none of
    them. This function decides nothing: the caller joins the article to a claim by its
    own rule."""
    decision = decide(
        session,
        backend,
        step=SAME_CLAIM,
        state=same_claim_state(intervention, indication, candidates),
        options=[*(claim.slug for claim in candidates), NO_SUCH_CLAIM],
        input_ref=ref,
        now=now,
    )
    chances = decision.probabilities
    likeliest = max(
        (claim.slug for claim in candidates), key=lambda slug: chances.get(slug, 0.0), default=None
    )
    return SameClaim(
        slug=None if decision.choice == NO_SUCH_CLAIM else decision.choice,
        likeliest=likeliest,
        likeliest_probability=chances.get(likeliest, 0.0) if likeliest else 0.0,
        none_probability=chances.get(NO_SUCH_CLAIM, 0.0),
    )


# The decision made after a read. Its own name: "treatment_report" is one of triage's
# answers, and the decision log must not hold the two under one word.
TREATMENT_KIND = "treatment_kind"
NEW_TREATMENT = "new_treatment"
ESTABLISHED_TREATMENT = "established_treatment"
# About one treatment for one condition, but not about what the treatment does.
BUSINESS_NEWS = "business_news"
NOT_ONE_TREATMENT = "not_one_treatment"
TREATMENT_KIND_OPTIONS = [NEW_TREATMENT, ESTABLISHED_TREATMENT, BUSINESS_NEWS, NOT_ONE_TREATMENT]
TREATMENT_KIND_QUESTION = (
    "An article has been read and is summarised above in our own words. Which is it?\n"
    f"- {NEW_TREATMENT}: about one treatment for one condition, where the treatment is "
    "new, experimental or being tested for that condition. A study or trial result, good "
    "or bad; a trial starting or being halted; a first use in people; an approval or its "
    "refusal. A drug long used for something else and now tested for this condition "
    "belongs here.\n"
    f"- {ESTABLISHED_TREATMENT}: about one treatment for one condition, where the "
    "treatment is already in established use for that condition, and the article is "
    "about what the treatment does: new evidence about how well it works or about its "
    "safety, a new use of it, or a change to its approval.\n"
    f"- {BUSINESS_NEWS}: about one treatment for one condition, but not about what the "
    "treatment does: its price, sales, supply or shortage, a lawsuit, insurance cover, "
    "marketing, or who is taking it.\n"
    f"- {NOT_ONE_TREATMENT}: anything else. No one treatment (a class or an approach for "
    "many conditions, a research direction); not a treatment (a predictor, a risk factor, "
    "a test, a discovery about a disease); or advice with no condition treated."
)


@dataclass(frozen=True, slots=True)
class TreatmentKind:
    """What the treatment-kind decision answered."""

    # Whichever it thinks likeliest of a new treatment, an established treatment and
    # business news about a treatment.
    kind: str
    # The probability it gave to the article being about one treatment for one
    # condition, of any of those three kinds: one minus what it gave to none.
    one_treatment_probability: float
    # The probability it gave to the article being about what the treatment does, new
    # or established: evidence, safety, a new use, an approval.
    evidence_probability: float


def treatment_kind_state(headline: str, summary: str, intervention: str, indication: str) -> str:
    """What the treatment-kind decision is shown: what was read from the article, in
    the tracker's own words, and the question. Never a word of the article."""
    return (
        f"Headline: {headline}\nSummary: {summary}\n"
        f"Treatment: {intervention}\nCondition: {indication}\n\n{TREATMENT_KIND_QUESTION}"
    )


def kind_of_treatment_report(
    session: Session,
    backend: Backend,
    *,
    ref: str,
    headline: str,
    summary: str,
    intervention: str,
    indication: str,
    now: datetime,
) -> TreatmentKind:
    """Whether the backend says the article is about one treatment for one condition,
    which is what a claim is; whether that treatment is new or established; and whether
    the article is about what the treatment does or about its business. This function
    decides nothing: the caller drafts or joins a claim only by its own rule. An
    established treatment is wanted as much as a new one: its registry record is what
    came of it."""
    decision = decide(
        session,
        backend,
        step=TREATMENT_KIND,
        state=treatment_kind_state(headline, summary, intervention, indication),
        options=TREATMENT_KIND_OPTIONS,
        input_ref=ref,
        now=now,
    )
    chances = decision.probabilities
    kinds = (NEW_TREATMENT, ESTABLISHED_TREATMENT, BUSINESS_NEWS)
    return TreatmentKind(
        kind=max(kinds, key=lambda kind: chances.get(kind, 0.0)),
        one_treatment_probability=1 - chances.get(NOT_ONE_TREATMENT, 0.0),
        evidence_probability=chances.get(NEW_TREATMENT, 0.0)
        + chances.get(ESTABLISHED_TREATMENT, 0.0),
    )
