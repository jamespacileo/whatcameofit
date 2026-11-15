"""Finding the registry trials behind a news article or a post. Behavior: openspec live-lookup.

A lookup is an answer for one reader, made on the spot. It stores no claim, no match and
no article: the text is shown to the model and dropped, as in extraction. What it returns
is a ranked list of candidates, not a reviewed status.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entry import name_key
from thenwhat.db.models import Claim, Entity
from thenwhat.decide.core import Backend, decide_many
from thenwhat.decide.steps import MATCH, TRIAL_OPTIONS, TRIAL_QUESTION, candidate_text
from thenwhat.domain import EntityType
from thenwhat.extract.names import is_a_name
from thenwhat.extract.page import Page
from thenwhat.extract.schema import MAX_SEARCH_PHRASES, ShortText
from thenwhat.llm.client import Llm
from thenwhat.lookup.details import PAPER, STATED, Details, agreeing
from thenwhat.resolve.codes import Substances, codes_for
from thenwhat.resolve.service import what_it_says
from thenwhat.sources.base import SourceError, SourceRecord

STEP = "lookup_match"
REGISTRY_NUMBER = re.compile(r"\bNCT\d{8}\b", re.IGNORECASE)
COMBINED = re.compile(r"\s+(?:and|plus)\s+|\s*\+\s*", re.IGNORECASE)
# The most records one lookup will ask the backend about.
MAX_CANDIDATES = 60
# From this score a record reads as a trial of the treatment for the condition.
LIKELY_FROM = 0.5
# The most linked papers one lookup asks about.
MAX_PAPERS = 3


INSTRUCTIONS = """\
You read one news article or social media post and identify a specific medical
treatment claim it reports.
Report only what the text says. Do not add facts, and do not judge the claim.
The one exception is the field for names you know: there, and only there, use your own knowledge.
If the text is not about a specific treatment for a specific condition, say so and leave
the other fields empty.
A condition or intended benefit may use everyday words: studying a topical for hair
growth or a drug to regrow missing teeth is specific enough without a formal
diagnosis. Keep that stated target; do not invent a diagnosis from a drug name alone.
First distinguish a treatment report from incidental mentions of medicines. A report
describes a therapeutic claim, medical research, a trial starting or its results
(including negative results), preclinical work, or observational treatment evidence.
Earnings, sales forecasts, prices, supply shortages, litigation and company profiles
are not treatment reports merely because they name a medicine and its usual use.
For those stories, return about_a_treatment false and empty identification fields
unless the story actually reports a specific therapeutic research finding or claim
as its subject. Do not convert a side-effect lawsuit into an efficacy claim.
Classify the purpose of the whole article or post before choosing a medicine.
A company history listing its founding, offices and products remains a company
profile even if one product's indication, mechanism or past regulatory approval is
stated. Those catalogue facts are not the post's own therapeutic research claim.
Do not select a product from that history or turn its hashtags into a new finding.
An unnamed but described treatment can be a valid claim: keep its descriptive name
and uncertainty instead of inventing a product. Trial permission is not approval of
a treatment, and animal or laboratory findings are not evidence of human efficacy.
Identify one intervention-condition pair. A real combination regimen is one
intervention, but unrelated treatments listed in a round-up are not a combination.
Different arms of one trial are not unrelated roundup items. A report comparing
monotherapy with a combination still reports a treatment study: identify the main
experimental treatment or regimen and use its comparators as study context.
Choose a single pair only when it is clearly the main subject. Otherwise return
about_a_treatment false with empty identification fields and explain in the gist
that the text contains several separate claims, rather than merging their names.
"""


class Reading(BaseModel):
    """What the model must return for one piece of text."""

    about_a_treatment: bool = Field(
        description="Whether the text reports a specific treatment for a specific condition."
    )
    gist: str = Field(
        default="",
        max_length=300,
        description="What was reported, in one neutral line of your own words.",
    )
    intervention: ShortText | None = Field(
        default=None,
        description="The drug, device or method, by its name alone: no maker or mechanism.",
    )
    other_names: list[ShortText] = Field(
        default_factory=list,
        description=(
            "Other names the text gives it: a brand name, a code such as ABC-123, or a generic"
            " name. For a combination, only whole-regimen aliases, never individual components."
            " Never a description such as 'the drug'. Empty if there is none."
        ),
    )
    known_names: list[ShortText] = Field(
        default_factory=list,
        max_length=5,
        description=(
            "From your own knowledge, not the text: other names this exact treatment goes by"
            " that the text does not give, such as a development code, a generic name or a"
            " brand name. For a combination, also the name of each part. Only names you are"
            " sure of. Empty if you know none."
        ),
    )
    search_phrases: list[ShortText] = Field(
        default_factory=list,
        max_length=MAX_SEARCH_PHRASES,
        description=(
            "Up to three short phrases a clinical trial registry would use for this treatment"
            " when it has no product name, most specific first, for example 'median nerve"
            " stimulation'. Empty when the names above are enough."
        ),
    )
    indication: ShortText | None = Field(
        default=None, description="The condition it is reported to treat, in medical words."
    )
    trial_name: ShortText | None = Field(
        default=None,
        description=(
            "The name the text gives the trial itself, such as SURMOUNT-5 or RECOVERY."
            " Not the treatment's name. Null if the text gives none."
        ),
    )
    participants: int | None = Field(
        default=None,
        ge=1,
        description=(
            "How many people took part in the trial the text reports, as the text says."
            " Null if it does not say."
        ),
    )
    sponsor: ShortText | None = Field(
        default=None,
        description=(
            "The company, university or hospital the text says ran or paid for the trial,"
            " by its name alone. Null if the text names none."
        ),
    )


class Trials(Protocol):
    def search_trials(
        self, intervention: str, condition: str | None = None
    ) -> list[SourceRecord]: ...

    def fetch_trial(self, nct_id: str) -> SourceRecord | None: ...

    def named_trials(self, name: str) -> list[SourceRecord]: ...


class Papers(Protocol):
    def trial_numbers(
        self, *, doi: str | None = None, pubmed_id: str | None = None
    ) -> list[str]: ...


@dataclass(frozen=True, slots=True)
class Candidate:
    external_id: str
    url: str
    # The backend's probability that the record is a trial of this treatment for this condition.
    score: float
    answer: str
    summary: str
    # Why it is ranked where it is, beyond the score: codes from thenwhat.lookup.details.
    agrees: list[str] = field(default_factory=list)

    @property
    def likely(self) -> bool:
        """Whether the record reads as a trial of the treatment for the condition, or the
        text itself names it."""
        return self.score >= LIKELY_FROM or STATED in self.agrees


@dataclass(frozen=True, slots=True)
class Lookup:
    gist: str
    intervention: str | None
    indication: str | None
    # Names the text gives.
    names: list[str] = field(default_factory=list)
    # Names the model knows the treatment by. They widen the search; they are not from the text.
    known_names: list[str] = field(default_factory=list)
    # Development codes a registry of substances lists for the treatment, or for a part
    # of a combination. They widen the search; they are not from the text or a model.
    codes: list[str] = field(default_factory=list)
    # Why the registry of substances could not be asked, when it could not.
    codes_not_looked_up: str | None = None
    registry_numbers: list[str] = field(default_factory=list)
    # Registry numbers given by a paper the page links to.
    paper_numbers: list[str] = field(default_factory=list)
    # What the text says about the trial itself.
    details: Details = field(default_factory=Details)
    # Slugs of claims for the complete intervention and the same indication.
    tracked: list[str] = field(default_factory=list)
    candidates: list[Candidate] = field(default_factory=list)


def look_up(
    session: Session,
    llm: Llm,
    backend: Backend,
    trials: Trials,
    *,
    text: str,
    now: datetime,
    page: Page | None = None,
    papers: Papers | None = None,
    substances: Substances | None = None,
) -> Lookup:
    """Read the text, search the registry for what it reports, and rank what is found.

    Registry numbers stated in the text, or in a link on the page, are looked up directly;
    so are the numbers given by a paper the page links to. Each name the text gives, each
    name the model knows the treatment by, and each search phrase is searched within the
    reported condition, and so is each development code a registry of substances lists
    for the treatment under a name the text gives. A trial the text names is searched
    for by that name. Every
    record found is scored by the backend with the question used for a claim's candidates.
    Among the records that read as trials of the treatment, those that agree with what the
    text says of the trial (its name, its size, who ran it) come first. Nothing is stored.
    """
    stated = [number.upper() for number in REGISTRY_NUMBER.findall(text)]
    numbers = list(dict.fromkeys([*stated, *(page.registry_numbers if page else ())]))
    reading = llm.run("lookup", instructions=INSTRUCTIONS, prompt=text, output_type=Reading)
    if not reading.about_a_treatment or not reading.intervention:
        return Lookup(reading.gist, None, None, registry_numbers=numbers)

    # A registry number is looked up as a record, never searched for as a name.
    other = [
        name
        for name in reading.other_names
        if is_a_name(name) and not REGISTRY_NUMBER.fullmatch(name.strip())
    ]
    names = list(dict.fromkeys([reading.intervention, *other]))
    known = [
        name
        for name in dict.fromkeys(reading.known_names)
        if is_a_name(name) and not REGISTRY_NUMBER.fullmatch(name.strip()) and name not in names
    ]
    details = Details(reading.trial_name, reading.participants, reading.sponsor)
    from_papers = [number for number in _paper_numbers(page, papers) if number not in numbers]
    # What is known by number or by the trial's name comes first, so it is never cut off.
    records: dict[str, SourceRecord] = {}
    for number in [*numbers, *from_papers]:
        given = trials.fetch_trial(number)
        if given is not None:
            records.setdefault(given.external_id, given)
    if details.trial_name:
        for record in trials.named_trials(details.trial_name):
            records.setdefault(record.external_id, record)
    # A combination is registered under its parts as often as under the pair.
    parts = [part for name in names for part in _parts(name)]
    codes, codes_not_looked_up = _codes(substances, names, parts)
    for term in dict.fromkeys([*names, *parts, *known, *codes, *reading.search_phrases]):
        for record in trials.search_trials(term, reading.indication):
            records.setdefault(record.external_id, record)
    found = list(records.values())[:MAX_CANDIDATES]

    others = [*names[1:], *known, *codes]
    also = f" (also known as: {', '.join(others)})" if others else ""
    decisions = decide_many(
        session,
        backend,
        step=STEP,
        intro=(
            f"Claim: {reading.gist}\nIntervention: {names[0]}{also}.\n"
            f"Indication: {reading.indication}.\n\nEntity to match (intervention): {names[0]}"
        ),
        question=TRIAL_QUESTION,
        items=[(f"lookup:{record.external_id}", candidate_text(record)) for record in found],
        options=TRIAL_OPTIONS,
        now=now,
    )
    candidates = sorted(
        (
            Candidate(
                record.external_id,
                record.url,
                decision.probabilities[MATCH],
                decision.choice,
                what_it_says(record) or "",
                [
                    *([STATED] if record.external_id in numbers else []),
                    *([PAPER] if record.external_id in from_papers else []),
                    *agreeing(record.payload, details),
                ],
            )
            for record, decision in zip(found, decisions, strict=True)
        ),
        # A record the article itself names is first whatever its score. Then the records
        # that read as trials of the treatment, those agreeing with more details first.
        key=lambda candidate: (
            STATED not in candidate.agrees,
            candidate.score < LIKELY_FROM,
            -len(candidate.agrees),
            -candidate.score,
            candidate.external_id,
        ),
    )
    return Lookup(
        reading.gist,
        names[0],
        reading.indication,
        names=names,
        known_names=known,
        codes=codes,
        codes_not_looked_up=codes_not_looked_up,
        registry_numbers=numbers,
        paper_numbers=from_papers,
        details=details,
        # Model-known names include individual components; use them only for search.
        tracked=_tracked(session, names, reading.indication),
        candidates=candidates,
    )


def _codes(
    substances: Substances | None, names: list[str], parts: list[str]
) -> tuple[list[str], str | None]:
    """The development codes the registry of substances lists for the treatment, and for
    each part of a combination, with the reason when it could not be asked.

    The names the text gives must lead to one substance; each part is its own. A name
    the registry does not list gives no code, and no name from the model is asked about.
    """
    if substances is None:
        return [], None
    taken = {name_key(name) for name in [*names, *parts]}
    codes: list[str] = []
    try:
        for asked in [names, *([part] for part in parts)]:
            for code in codes_for(substances, asked).codes:
                if name_key(code) not in taken:
                    taken.add(name_key(code))
                    codes.append(code)
    except SourceError as failed:
        return [], str(failed)
    return codes, None


def _paper_numbers(page: Page | None, papers: Papers | None) -> list[str]:
    """The registry numbers given by the papers the page links to. A paper that cannot
    be looked up is passed over: the lookup goes on without it."""
    if page is None or papers is None:
        return []
    linked: list[dict[str, str]] = [
        *({"doi": doi} for doi in page.dois),
        *({"pubmed_id": pubmed_id} for pubmed_id in page.pubmed_ids),
    ]
    found: list[str] = []
    for paper in linked[:MAX_PAPERS]:
        try:
            found += papers.trial_numbers(**paper)
        except SourceError:
            continue
    return list(dict.fromkeys(found))


def _parts(name: str) -> list[str]:
    """The treatments joined in a name such as 'A and B' or 'A plus B'; none for one treatment."""
    pieces = [piece.strip() for piece in COMBINED.split(name)]
    return [piece for piece in pieces if piece] if len(pieces) > 1 else []


def _regimen_names(names: list[str]) -> set[tuple[str, ...]]:
    """Whole-regimen aliases, excluding single components of a combination."""
    parts = _regimen_parts(names)
    components = {part for one in parts if len(one) > 1 for part in one}
    if parts and len(parts[0]) == 1 and parts[0][0] in components:
        return set()
    return {one for one in parts if len(one) > 1 or len(one) == 1 and one[0] not in components}


def _regimen_parts(names: list[str]) -> list[tuple[str, ...]]:
    return [
        tuple(
            sorted(
                name_key(part)
                for part in re.split(r"\s+(?:and|plus)\s+|\s*[+/]\s*", name, flags=re.I)
                if name_key(part)
            )
        )
        for name in names
    ]


def _tracked(session: Session, names: list[str], indication: str | None) -> list[str]:
    """Claims for the complete intervention and the same explicit condition."""
    if not indication or not name_key(indication):
        return []
    wanted = _regimen_names(names)
    cards = [
        (slug, [name, *synonyms], _regimen_names([name, *synonyms]))
        for slug, condition, name, synonyms in session.execute(
            select(Claim.slug, Claim.indication, Entity.name, Entity.synonyms)
            .join(Entity, Entity.claim_id == Claim.id)
            .where(Entity.type == EntityType.INTERVENTION)
            .order_by(Claim.slug)
        )
        if name_key(condition) == name_key(indication)
    ]
    primary = _regimen_names(names[:1])
    direct = [slug for slug, _, keys in cards if primary & keys]
    if direct:
        # Published whole aliases establish equivalence; inferred aliases must
        # not add a component card to an exact primary match.
        return list(dict.fromkeys(direct))
    named_aliases = [name for _, aliases, keys in cards if primary & keys for name in aliases]
    primary_parts = {one for one in _regimen_parts(names[:1]) if len(one) > 1}
    named_parts = {one for one in _regimen_parts(named_aliases) if len(one) > 1}
    full_regimens = (
        primary_parts or named_parts or {one for one in _regimen_parts(names) if len(one) > 1}
    )
    if len(full_regimens) > 1:
        return []
    whole_names = [*names, *named_aliases]
    components = {(part,) for one in _regimen_parts(whole_names) if len(one) > 1 for part in one}
    slugs = [
        slug
        for slug, aliases, keys in cards
        if wanted & keys
        and not components & keys
        and (
            not full_regimens
            or all(one in full_regimens for one in _regimen_parts(aliases) if len(one) > 1)
        )
    ]
    return list(dict.fromkeys(slugs))
