"""The JSON export the site is built from. Behavior: openspec site-publishing.

Only approved, unarchived claims are exported, with their approved events, their
approved matches, a few candidates still awaiting review, their background cards,
their approved reported statements, the organisations they name and their trials'
record readings.
The file is the single interface between pipeline and site; its schema is checked in at
site/export.schema.json.

The export is assembled here once, from a `Records` (`records.py`): the pipeline's own
database, or a SQLite file that has the truth store's schema. Nothing below asks a
database for anything.
"""

import base64
import json
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from thenwhat.claims.approach_rule import approach_from_registry
from thenwhat.claims.entities import intervention_components
from thenwhat.claims.entry import name_key
from thenwhat.claims.status import evidence_of, flags_of, keep_status
from thenwhat.claims.verticals import GROUPS, RETIRED_VERTICALS, VERTICAL_GROUPS, VERTICALS
from thenwhat.clinical.categories import Category, CheckedTerm, ClaimRecords
from thenwhat.clinical.categories import derive as derive_categories
from thenwhat.clinical.vocabulary import Vocabulary
from thenwhat.db.models import (
    Claim,
    ClaimTerm,
    Entity,
    EvidenceEvent,
    PaperRecord,
    Reading,
    TermRecord,
)
from thenwhat.domain import (
    TRIAL_EVENT_TYPES,
    ClaimStatus,
    Decider,
    EntityType,
    EventType,
    EvidenceStage,
    FollowUpUnit,
    MeasureCode,
    ReadingField,
    ReadingKind,
    RegulatoryOutcome,
    ReviewState,
    StatementBasis,
    StatementFirmness,
    StatementKind,
    StatementSpeaker,
    TermFit,
    TermRole,
    TrialPhase,
    TrialState,
)
from thenwhat.events.paper_facts import (
    PaperKind,
    StudiedIn,
    doi_of,
    pubmed_id_of,
    read_paper,
    record_page,
)
from thenwhat.events.paper_records import PUBMED_PREFIX, paper_reference
from thenwhat.events.trial_facts import (
    AgeGroup,
    Allocation,
    ArmKind,
    ClaimArm,
    Comparator,
    HowListed,
    Masking,
    MeasureKind,
    ParticipantBasis,
    SponsorKind,
    StudyKind,
    TestKind,
    TrialStateCode,
    claim_arm,
    read_trial,
    reported_state,
)
from thenwhat.events.trial_records import newest_registry_record
from thenwhat.export.organisations import ExportedOrganisation, organisations_of, publisher_of
from thenwhat.export.records import PostgresRecords, Records
from thenwhat.outlets.icons import is_blank_icon, outlet_domain
from thenwhat.readings.rules import Outcome
from thenwhat.readings.service import readings_that_stand
from thenwhat.sources import opentargets
from thenwhat.sources.base import SourceRecord, record_url
from thenwhat.sources.clinicaltrials import ClinicalTrials
from thenwhat.sources.mesh import Mesh
from thenwhat.sources.openalex import OpenAlex
from thenwhat.sources.ror import Ror
from thenwhat.sources.terms import SOURCES as LISTED_SOURCES
from thenwhat.status.rules import derive, history
from thenwhat.terms.candidates import REASON_CODES
from thenwhat.terms.drugs import DRUG_REASON_CODES, DRUG_RECORD_NAMES_TARGET
from thenwhat.terms.genes import TARGET_REASON_CODES
from thenwhat.terms.kinds import KIND_REASON_CODES, registry_types
from thenwhat.terms.records import read_record

# 2: claims awaiting audit are left out (ADR 0007). The site reads only this version, so
# an export written by code that does not know the hold is refused, not published.
SCHEMA_VERSION = 2
# Registries the clients read. Always listed, as their terms ask for attribution.
SOURCES = [
    ("ClinicalTrials.gov", "https://clinicaltrials.gov/"),
    ("Europe PMC", "https://europepmc.org/"),
    ("Crossref", "https://www.crossref.org/"),
    # Read for a brand's ingredient, which is only searched for. NLM asks an application
    # that uses its data to carry a statement, which the site shows beside this list.
    ("RxNorm", LISTED_SOURCES["rxnorm"].home_url),
]
# Registries with no client yet, listed only when an exported event came from one.
OTHER_REGISTRIES = {"jRCT": "https://jrct.mhlw.go.jp/"}
# The organisation registry, listed only when an exported organisation is identified.
ORGANISATION_REGISTRY = ("Research Organization Registry (ROR)", "https://ror.org/")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExportedSource(Strict):
    name: str
    url: str


class ExportedGroup(Strict):
    slug: str
    title: str


class ExportedVertical(Strict):
    slug: str
    title: str
    # The broader area the vertical is filed under, when it has one.
    group: ExportedGroup | None = None


class ExportedRetiredVertical(Strict):
    """A vertical slug renamed or retired after launch, and the vertical that replaces it."""

    slug: str
    successor: str


class ExportedOutlet(Strict):
    """An outlet's own icon, stored by the pipeline so that no page fetches it."""

    # An article's host without a leading www, as the site shows it.
    domain: str
    # The image itself as a data URI; the site never receives an address to fetch.
    icon: str = Field(pattern=r"^data:image/(png|x-icon|gif|jpeg|webp);base64,[A-Za-z0-9+/]+=*$")
    fetched_at: datetime


class ExportedIntervention(Strict):
    name: str
    synonyms: list[str]


class ExportedStatusChange(Strict):
    """The day the status became `code`, by the rules run on what was dated up to then."""

    on: date
    code: ClaimStatus


class ExportedStatus(Strict):
    code: ClaimStatus
    overlay_years: int | None
    updated_at: datetime | None
    explained_by: list[int]
    # Oldest first; the last entry's code is `code`. Absent from exports made before
    # the history was added, so the site treats a missing history as none.
    history: list[ExportedStatusChange] = []


class ExportedArticle(Strict):
    url: str
    outlet: str
    title: str
    published_date: date
    archive_url: str | None
    # The registry record address (an `organisations` entry's `record.url`) of the
    # identified organisation of the claim on whose website the article is. None for an
    # article on any other site (openspec organisations).
    published_by: str | None = None


class ExportedPromise(Strict):
    description: str
    parsed_date: date | None
    article_url: str


class ExportedStatement(Strict):
    """A reported statement (openspec reported-statements): what an article said, in the
    pipeline's own words and never a quotation. Not a record and not a finding: the site
    words every code and frames the text as its report's statement."""

    text: str
    kind: StatementKind
    firmness: StatementFirmness
    # A role, never a name.
    speaker: StatementSpeaker
    # What the article said the statement rests on.
    basis: StatementBasis
    # The statement check's probability that the article says it.
    confidence: float
    article_url: str
    # When the article was read for it: the statement is of the article as read then.
    read_on: date


class ExportedEvent(Strict):
    id: int
    type: EventType
    event_date: date
    date_basis: str | None
    summary: str
    source_name: str
    source_url: str
    trial_id: str | None
    trial_phases: list[TrialPhase]
    trial_state: TrialState | None
    regulatory_outcome: RegulatoryOutcome | None
    # How sure the pipeline is that the event is evidence for the claim, 0 to 1. Always
    # set; optional only so that an export made before it was added is still valid.
    confidence: float | None = None


class ExportedFailureFlag(Strict):
    trial_id: str
    source_url: str


class ExportedParticipants(Strict):
    count: int
    basis: ParticipantBasis


class ExportedMatchRecord(Strict):
    # A matched trial's registry record field by field (openspec registry-record-rows).
    # Title and names as the registry wrote them; phases and state as codes the site words.
    title: str | None
    conditions: list[str]
    interventions: list[str]
    phases: list[TrialPhase]
    state: TrialStateCode
    # How many people the record says took part or are planned. None when it says not.
    participants: ExportedParticipants | None = None


class ExportedMatch(Strict):
    # A registry record matched to the claim, with how sure the pipeline is. The site owns
    # the words: it turns `score` into "High match · 92%" and `reading` into a reason.
    source_name: str
    external_id: str
    url: str | None
    # The probability, 0 to 1, that the record is evidence for the claim.
    score: float
    # "approved" counts toward the status; "candidate" is shown apart and does not.
    state: str
    # How the record was read: "match", "other_indication", "not_what_is_tested",
    # "not_a_match", or None.
    reading: str | None
    # Who approved it: "human", "rule", "seed" or "assistant". None for a candidate.
    decided_by: str | None
    # What the record says, in one line: title, conditions, phase, state.
    summary: str | None
    # The same, field by field, for a trial. None for a match whose record has not been
    # read into fields yet (`thenwhat entity record-facts`).
    record: ExportedMatchRecord | None = None


# Trial facts (openspec trial-facts): what a registry record says of its trial, read by
# rule. Codes only; the site owns the words. Registry numbers stay strings as written.


class ExportedSponsor(Strict):
    # None when the sponsor is a person.
    name: str | None
    kind: SponsorKind | None


class ExportedPlannedOutcome(Strict):
    measure: str
    time_frame: str | None


class ExportedResultGroup(Strict):
    title: str
    analysed: str | None
    value: str | None
    spread: str | None
    lower: str | None
    upper: str | None


class ExportedComparison(Strict):
    # The titles of the groups compared.
    groups: list[str]
    p_value: str | None
    method: str | None
    test: TestKind | None


class ExportedResultOutcome(Strict):
    title: str
    time_frame: str | None
    unit: str | None
    measure: MeasureKind | None
    # The registry's own words, such as "Standard Deviation".
    spread_kind: str | None
    # How many rows the outcome is reported in. Groups and comparisons are carried only
    # for an outcome reported in one row.
    rows: int
    groups: list[ExportedResultGroup]
    comparisons: list[ExportedComparison]


class ExportedResults(Strict):
    # At most three posted primary outcomes, and how many the record posts.
    outcomes: list[ExportedResultOutcome]
    outcomes_total: int


class ExportedArm(Strict):
    # The record's words for the arm and its interventions, unaltered but for the
    # registry's "Drug: " style prefix.
    label: str | None
    kind: ArmKind
    interventions: list[str]


class ExportedTrialFacts(Strict):
    study_kind: StudyKind | None
    participants: ExportedParticipants | None
    allocation: Allocation | None
    masking: Masking | None
    comparators: list[Comparator]
    healthy_volunteers: bool | None
    age_groups: list[AgeGroup]
    sponsor: ExportedSponsor | None
    # At most three planned primary outcomes, and how many the record plans.
    primary_outcomes: list[ExportedPlannedOutcome]
    primary_outcomes_total: int
    why_stopped: str | None
    results: ExportedResults | None
    # The record's arms in its order; empty for a registry that lists none.
    arms: list[ExportedArm] = []


class ExportedReading(Strict):
    """A record reading (openspec record-readings): what a model read from one field of
    one of the trial's planned primary outcomes, as a code or a number with a unit, with
    the words it read. A rule checked it against the stored record. Codes only; the site
    owns the wording."""

    kind: ReadingKind
    # The place of the outcome in the trial's `facts.primary_outcomes`, counted from 0.
    outcome: int
    # The field of that outcome the words are in, character for character.
    field: ReadingField
    words: str
    # A follow-up's number and unit; None for a measure.
    number: int | None
    unit: FollowUpUnit | None
    # A measure's kind; None for a follow-up.
    code: MeasureCode | None
    # How sure the model said it was of the reading.
    confidence: float = Field(ge=0, le=1)
    # When the record that was read was fetched: the trial's `facts_as_of`.
    read_on: datetime


class ExportedTrial(Strict):
    """One trial behind the claim's approved events. Its match, if any, is the entry in
    `matches` with the same identifier."""

    trial_id: str
    source_name: str
    # The source link of the trial's newest approved event.
    url: str
    # The registry's brief title; None when no registry record is held.
    title: str | None
    phases: list[TrialPhase]
    state: TrialStateCode
    # When the record the facts were read from was fetched.
    facts_as_of: datetime | None
    # None when no registry record is held, as for a trial entered by hand.
    facts: ExportedTrialFacts | None
    # The identifiers of the papers the trial's registry record names for it, each an
    # entry in the claim's `papers`. Empty for a trial with no registry record.
    papers: list[str] = []
    # Stored readings of the record the facts were read from. Empty when it has not
    # been read, or no reading passed the rules.
    readings: list[ExportedReading] = []
    # Whether the claim's intervention is in the trial's experimental arm or only in its
    # comparator arms, by an exact match of its name or a synonym; None when that
    # cannot be told from the record.
    claim_arm: ClaimArm | None = None


# Papers (openspec paper-facts): each paper a claim page lists, once, with the roles it
# plays for the claim and what its index record states. Codes only; the site owns the
# words. Never an abstract, an author or an affiliation.

PaperRole = Literal["origin", "trial_result", "follow_up", "related"]
# The order a paper's roles are listed in, and papers by their first role.
PAPER_ROLES: tuple[PaperRole, ...] = ("origin", "trial_result", "follow_up", "related")


class ExportedPaperRole(Strict):
    role: PaperRole
    # For "trial_result": the trial whose registry record names the paper, and whether
    # the sponsor listed it as reporting results or the registry linked it from PubMed.
    trial_id: str | None = None
    listed: HowListed | None = None
    # For "follow_up": the evidence event the paper is behind.
    event_id: int | None = None
    # For "related" (openspec related-research): the probability, 0 to 1, that the paper
    # is about the claim's intervention and indication, the reasons found by rule as
    # codes, who approved it, and what the search source says of it in one line.
    score: float | None = None
    reasons: list[str] = []
    decided_by: str | None = None
    summary: str | None = None


class ExportedPaperFacts(Strict):
    title: str | None
    journal: str | None
    year: int | None
    # Every kind the record gives, most specific first.
    kinds: list[PaperKind]
    open_access: bool | None
    retracted: bool
    # What the record's subject headings say the study was in; empty when they say
    # neither or the record has none.
    studied_in: list[StudiedIn]


class ExportedPaper(Strict):
    # The DOI in lower case, else "pmid:<number>", else the source's own identifier.
    identifier: str
    # Where a reader can open the paper.
    url: str
    # The index record the facts were read from, when the index holds the paper.
    record_url: str | None
    roles: list[ExportedPaperRole]
    # When the index record was fetched. None, with no facts, for a paper the index
    # does not hold or was not asked for.
    facts_as_of: datetime | None
    facts: ExportedPaperFacts | None


# Background cards (openspec knowledge-cards): what an open vocabulary says of a term
# tied to the claim. Never an input to the status.


# The reasons a card can carry: those of a vocabulary term and those of a kind link.
CARD_REASON_CODES = (
    *REASON_CODES,
    *KIND_REASON_CODES,
    *TARGET_REASON_CODES,
    *DRUG_REASON_CODES,
)
# Whose facts a drug's kind of molecule and mechanisms are: the source in the list of
# sources that the drug source draws them from (docs/sources.md, docs/adr/0002).
DRUG_FACTS_FROM = "chembl"
# Whose words a target's function description is: the source in the list of sources
# that the target source draws it from (docs/sources.md).
TARGET_DESCRIPTIONS_FROM = "uniprot"


class ExportedCardReason(Strict):
    """Why the term was a candidate, found by rule. The site owns the wording."""

    # "filed_by_registry", "label_equals_name", "entry_term_equals_name", "kind_chosen",
    # "registry_lists_type", "word_equals_symbol", "word_equals_synonym",
    # "drug_name_equals_name" or "drug_record_names_target".
    code: str
    # For "filed_by_registry": how many of the claim's approved trials carry the term,
    # and how many trials there were. For "registry_lists_type": how many of them list
    # the intervention under that type.
    trials: int | None = None
    of: int | None = None
    # For "label_equals_name", "entry_term_equals_name" and "drug_name_equals_name": the
    # claim's name that was equal. For "drug_record_names_target": the drug's name as
    # its source writes it.
    name: str | None = None
    # For "entry_term_equals_name": the vocabulary's entry term the name equals.
    entry_term: str | None = None
    # For "kind_chosen": the code of the kind chosen from the project's list.
    kind: str | None = None
    # For "registry_lists_type": the registry's own code for the intervention's type,
    # such as "DEVICE".
    type: str | None = None
    # For "word_equals_symbol" and "word_equals_synonym": the word of the
    # intervention's name that equals the gene's symbol or a listed synonym of it.
    word: str | None = None
    # For "word_equals_synonym": each source the target source says gives the synonym.
    sources: list[str] | None = None


class ExportedMechanism(Strict):
    """One thing a drug's record says the drug does. The site words the action."""

    # What the drug does to the target, as a code: "agonist", "binding_agent".
    action: str
    # The target's name as the source writes it.
    target: str


class ExportedCard(Strict):
    # What the term is to the claim: its condition, its intervention, a drug source's
    # record of the intervention, or a target. A target is the one protein a drug's
    # record names, or else a gene named in the intervention's name; the second states
    # no mechanism.
    kind: TermRole
    # "exact" when the term is the claim's own condition or intervention, "broader"
    # when it names a wider group that includes it, "kind" when it is the term of the
    # kind of intervention this is and not the intervention itself.
    fit: TermFit
    label: str
    # For a target: the gene's approved name, which names its protein. None otherwise.
    name: str | None = None
    # The vocabulary publisher's own words, never reworded. None when it gives none.
    # For a target, the first function description its source gives, exactly as given.
    definition: str | None
    # The name in `card_sources` of the source the definition's words come from, when
    # that is not the card's own source. None otherwise.
    definition_source: str | None = None
    # The term's record at its source.
    url: str
    # The source's name in `card_sources`.
    source: str
    external_id: str
    # The version of the vocabulary the record was read from, such as a year.
    version: str | None
    # The probability, 0 to 1, of the answer the term check chose for this term or,
    # for a kind, of the kind chosen. None for a card made by a rule a reader can check:
    # a drug found by its exact name, and the target that drug's record names.
    score: float | None
    # For a drug: the kind of molecule, as a code such as "small_molecule". The site
    # words it. None when the source gives none, and on every other card.
    molecule_kind: str | None = None
    # For a drug: what its record says it does, each an action and a target's name.
    mechanisms: list[ExportedMechanism] = []
    # The name in `card_sources` of the source the card's facts are drawn from, when
    # they are under another licence than the card's own source: a drug's kind of
    # molecule and mechanisms, and that a drug's record names this target.
    facts_source: str | None = None
    reasons: list[ExportedCardReason]
    # Who approved the link: "rule", "human" or "assistant".
    decided_by: str
    # When the term's record was read.
    read_at: datetime


class ExportedCardSource(Strict):
    """A source a published card comes from, with what its terms ask for."""

    name: str
    title: str
    # How the source asks to be credited.
    credit: str
    licence: str
    url: str
    terms_url: str
    # Whether its cards may be offered in the open data file under that file's licence.
    in_data_file: bool


class ExportedStageShare(Strict):
    stage: EvidenceStage
    # The probability, 0 to 1, the reading gave this stage.
    score: float


class ExportedStageReading(Strict):
    # How the first report was read when the reading was not sure enough to confirm the
    # stage by rule (openspec review, ADR 0004). The site shows it apart, marked low
    # confidence. Never an input to the status: `evidence_stage` stays empty beside it.
    stage: EvidenceStage
    # The probability, 0 to 1, the reading gave the stage it chose.
    score: float
    # The other stages the reading gave weight to, likeliest first: why it is unsure.
    also: list[ExportedStageShare]


class ExportedCategorySource(Strict):
    """A record that gave a claim one of its clinical categories."""

    kind: Literal["trial", "paper", "term"]
    # The trial's registry identifier, or the paper's identifier as in `papers`. For a
    # term: the descriptor itself, read as the claim's own condition by the terms step.
    identifier: str
    # The score of that reading, shown with it. None for a trial or a paper.
    score: float | None = None


class ExportedClinicalCategory(Strict):
    """A MeSH descriptor the claim's approved trials list for their conditions, or its
    approved papers are indexed under as a major topic (openspec clinical-classification).
    Its name and place in the tree are in the export's `clinical.nodes`."""

    identifier: str
    sources: list[ExportedCategorySource]


class ExportedMeshNode(Strict):
    """A MeSH descriptor a claim has as a category, or one broader than such a one."""

    identifier: str
    # NLM's own label. The site shows it as it is.
    label: str
    tree_numbers: list[str]
    # The descriptors directly broader. Empty at the top of a tree.
    broader: list[str]


class ExportedClinical(Strict):
    # Each MeSH year the nodes were read from, oldest first: NLM asks that it be stated.
    mesh_years: list[str]
    nodes: list[ExportedMeshNode]
    # Published claims whose categories are left out because a MeSH record they need
    # has not been read. `thenwhat clinical tree` reads them.
    claims_not_read: int = 0


class ExportedApproachBasis(Strict):
    """What the registry lists the claim's intervention as, when that is the claim's
    approach: the registry's own type code and how many of the claim's trials list it
    (openspec site-publishing). Said whoever set the approach. The site owns the wording."""

    type: str
    trials: int


class ExportedClaim(Strict):
    slug: str
    headline: str
    summary: str
    vertical: str
    # The kind of intervention, as a configured approach code. The site owns its wording.
    approach: str | None
    # Absent from an export written before it was added, which the site still reads.
    approach_basis: ExportedApproachBasis | None = None
    # The claim's clinical categories. Empty when its records give none. None when they
    # give some and a MeSH record needed to place them has not been read yet, and in an
    # export written before the field was added: the site then shows none.
    clinical_categories: list[ExportedClinicalCategory] | None = None
    intervention: ExportedIntervention
    indication: str
    first_reported_date: date | None
    evidence_stage: EvidenceStage | None
    # Present only while `evidence_stage` is empty and a reading of it is on record.
    evidence_stage_reading: ExportedStageReading | None = None
    # True only when a person approved the claim and no assistant decision stands on
    # it, its matches or its events.
    checked_by_person: bool
    status: ExportedStatus
    articles: list[ExportedArticle]
    promises: list[ExportedPromise]
    events: list[ExportedEvent]
    failure_flags: list[ExportedFailureFlag]
    # Approved matches first, then up to five candidates, each with its confidence.
    matches: list[ExportedMatch] = []
    # One per registry identifier among the approved trial events, ordered by identifier.
    trials: list[ExportedTrial] = []
    # Each paper the page lists, once: the origin paper, results papers of the trials
    # above, papers behind approved follow-up events, and approved related papers.
    papers: list[ExportedPaper] = []
    # At most one card for the condition, then one for the intervention.
    background: list[ExportedCard] = []
    # Each organisation the claim names, once, ordered by role and then by name
    # (openspec organisations). Never an input to the status.
    organisations: list[ExportedOrganisation] = []
    # Approved reported statements, article by article in date order.
    reported_statements: list[ExportedStatement] = []


class ExportedArchived(Strict):
    # A claim the operator took down. Its address answers 410; the reason stays private.
    slug: str
    on: date


class ExportedMoved(Strict):
    # An address that was a claim's page and now leads to another claim's: the claim was
    # merged into that one, or renamed. The reason stays private.
    slug: str
    to: str


class Export(Strict):
    schema_version: int
    generated_at: datetime
    last_checked_at: datetime | None
    # Always false since openspec auto-publish: every approved claim is published, and
    # `checked_by_person` on each claim says whether a person checked it. Kept so a site
    # built from an older export still reads it.
    preview: bool = False
    sources: list[ExportedSource]
    verticals: list[ExportedVertical]
    # Topic addresses that must keep working: each redirects to its successor's.
    retired_verticals: list[ExportedRetiredVertical] = []
    # Icons of the outlets whose articles are exported. An outlet without one is absent.
    outlets: list[ExportedOutlet]
    claims: list[ExportedClaim]
    archived: list[ExportedArchived] = []
    # Addresses that lead to a published claim's page. Never also in `archived`.
    moved: list[ExportedMoved] = []
    # The sources of the cards in `background`, each once.
    card_sources: list[ExportedCardSource] = []
    # The score at or above which a registry match is approved by rule, so the site can
    # say what a possible record lacks (openspec registry-record-rows). None when the
    # rule is off and only a person approves a match.
    match_accept_above: float | None = None
    # The part of the MeSH tree the claims' clinical categories sit in. None in an export
    # written before it was added.
    clinical: ExportedClinical | None = None


def _group_of(vertical: str) -> ExportedGroup | None:
    slug = VERTICAL_GROUPS.get(vertical)
    return None if slug is None else ExportedGroup(slug=slug, title=GROUPS[slug])


def export_json_schema() -> dict[str, Any]:
    return Export.model_json_schema(mode="serialization")


def _statements(records: Records, claim: Claim) -> list[ExportedStatement]:
    """The claim's approved reported statements. Pending and rejected ones are left out."""
    return [
        ExportedStatement(
            text=statement.text,
            kind=statement.kind,
            firmness=statement.firmness,
            speaker=statement.speaker,
            basis=statement.basis,
            confidence=round(statement.confidence, 4),
            article_url=article.url,
            read_on=statement.article_read_at.date(),
        )
        for statement, article in records.statements(claim)
    ]


CANDIDATES_SHOWN = 5


def _matches(records: Records, claim: Claim) -> list[ExportedMatch]:
    """The claim's approved matches, then its best pending candidates. Rejected ones are
    never exported. Openspec auto-publish: "Confidence is shown with every match"."""
    # Papers found by search and organisations are not registry matches of the claim.
    # An approved paper is exported in `papers`, with the role "related" (openspec
    # related-research); organisations are not exported.
    found = records.shown_matches(claim, but_from=(OpenAlex.name, Ror.name))
    approved = [m for m in found if m.review_state is ReviewState.APPROVED]
    pending = [m for m in found if m.review_state is ReviewState.PENDING][:CANDIDATES_SHOWN]
    return [
        ExportedMatch(
            source_name=match.source_name,
            external_id=match.external_id,
            url=record_url(match.source_name, match.external_id),
            score=round(match.score, 4),
            state="approved" if match.review_state is ReviewState.APPROVED else "candidate",
            reading=records.match_reading(match),
            decided_by=(
                match.reviewed_by.value
                if match.review_state is ReviewState.APPROVED and match.reviewed_by
                else None
            ),
            summary=match.record_summary,
            record=(
                ExportedMatchRecord.model_validate(match.record_facts)
                if match.record_facts is not None
                else None
            ),
        )
        for match in [*approved, *pending]
    ]


class _Papers:
    """The claim's papers as they are found, one per identifier. A paper referred to by
    its DOI in one place and by its PubMed number in another is one paper once its
    index record is stored, because the record gives both."""

    def __init__(self, records: Records) -> None:
        self.records = records
        self.found: dict[str, ExportedPaper] = {}
        # Each found paper's stored index record, where the index holds it.
        self.payloads: dict[str, dict[str, Any]] = {}

    def add(
        self,
        role: ExportedPaperRole,
        *,
        doi: str | None = None,
        pubmed_id: str | None = None,
        identifier: str | None = None,
        url: str | None = None,
    ) -> str | None:
        """Give the paper this role and return its identifier, or None when nothing
        identifies it."""
        row = self.records.paper(doi=doi, pubmed_id=pubmed_id, identifier=identifier)
        key = _paper_identifier(row, doi=doi, pubmed_id=pubmed_id, identifier=identifier)
        if key is None:
            return None
        if key not in self.found:
            held = row is not None and row.payload is not None
            if row is not None and row.payload is not None:
                self.payloads[key] = row.payload
            self.found[key] = ExportedPaper(
                identifier=key,
                url=_paper_url(key, url),
                record_url=record_page(row.payload) if row and row.payload else None,
                roles=[],
                facts_as_of=row.fetched_at if row and held else None,
                facts=ExportedPaperFacts.model_validate(asdict(read_paper(row.payload)))
                if row and row.payload
                else None,
            )
        self.found[key].roles.append(role)
        return key

    def listed(self) -> list[ExportedPaper]:
        """Each paper with its roles in their fixed order, and the papers by their
        first role, otherwise as found."""
        for paper in self.found.values():
            paper.roles.sort(key=lambda role: PAPER_ROLES.index(role.role))
        return sorted(self.found.values(), key=lambda p: PAPER_ROLES.index(p.roles[0].role))


def _paper_identifier(
    row: PaperRecord | None, *, doi: str | None, pubmed_id: str | None, identifier: str | None
) -> str | None:
    payload = row.payload if row is not None else None
    number = (pubmed_id_of(payload) if payload else None) or pubmed_id
    return (
        (doi_of(payload) if payload else None)
        or (doi.lower() if doi else None)
        or (f"{PUBMED_PREFIX}{number}" if number else None)
        or identifier
    )


def _paper_url(identifier: str, url: str | None) -> str:
    if identifier.startswith("10."):
        return f"https://doi.org/{identifier}"
    if identifier.startswith(PUBMED_PREFIX):
        return f"https://pubmed.ncbi.nlm.nih.gov/{identifier.removeprefix(PUBMED_PREFIX)}/"
    assert url is not None, "a paper with neither a DOI nor a PubMed number has its own link"
    return url


def _collect_matches(
    records: Records, entities: list[Entity], events: list[EvidenceEvent], papers: _Papers
) -> dict[int, str]:
    """Collect paper roles and return the current approved registry matches by row ID."""
    trial_matches: dict[int, str] = {}
    for entity in entities:
        approved = records.approved_matches(entity)
        trial_matches.update(
            (m.id, m.external_id) for m in approved if m.source_name == ClinicalTrials.name
        )
        if entity.is_origin_paper and approved and approved[0].external_id.startswith("10."):
            papers.add(ExportedPaperRole(role="origin"), doi=approved[0].external_id)
        if entity.type is not EntityType.INTERVENTION:
            continue
        for match in approved:
            if match.source_name != OpenAlex.name:
                continue
            doi, _ = paper_reference(match.external_id)
            papers.add(
                ExportedPaperRole(
                    role="related",
                    score=round(match.score, 4),
                    reasons=list(match.reasons),
                    decided_by=match.reviewed_by.value if match.reviewed_by else None,
                    summary=match.record_summary,
                ),
                doi=doi,
                identifier=None if doi else f"openalex:{match.external_id}",
                url=record_url(match.source_name, match.external_id),
            )
    for event in events:
        if event.type is EventType.FOLLOWUP_PAPER:
            doi, pubmed_id = paper_reference(event.external_id)
            papers.add(
                ExportedPaperRole(role="follow_up", event_id=event.id),
                doi=doi,
                pubmed_id=pubmed_id,
                identifier=event.external_id,
                url=event.source_url,
            )
    return trial_matches


def _trials(
    records: Records,
    events: list[EvidenceEvent],
    papers: _Papers,
    reading_accept_above: float = 0.8,
    intervention_names: list[str] | None = None,
) -> list[ExportedTrial]:
    """One entry per registry identifier among the claim's approved trial events, given
    oldest first. Openspec trial-facts: the facts are read from the most recently fetched
    registry record those events hold; a trial with none is listed without facts.
    Openspec record-readings: the trial's stored readings are carried beside its facts,
    and are no input to them."""
    by_trial: dict[str, list[EvidenceEvent]] = {}
    for event in events:
        if event.type in TRIAL_EVENT_TYPES:
            by_trial.setdefault(event.external_id, []).append(event)
    trials: list[ExportedTrial] = []
    for trial_id, held in sorted(by_trial.items()):
        newest = held[-1]
        record = newest_registry_record(held)
        if record is None:
            changes = [event for event in held if event.type is EventType.TRIAL_STATUS_CHANGE]
            state = reported_state(changes[-1].trial_state if changes else None)
            title, facts, facts_as_of = None, None, None
            arm_of_claim: ClaimArm | None = None
            results: list[str] = []
            readings: list[ExportedReading] = []
        else:
            read = read_trial(record.raw_payload)
            state, title, facts_as_of = read.state, read.title, record.fetched_at
            facts = ExportedTrialFacts.model_validate(asdict(read.facts))
            arm_of_claim = claim_arm(read.facts.arms, intervention_names or [])
            readings = [
                ExportedReading(
                    kind=reading.kind,
                    outcome=reading.outcome,
                    field=reading.field,
                    words=reading.words,
                    number=reading.number,
                    unit=reading.unit,
                    code=reading.code,
                    confidence=round(reading.confidence, 4),
                    read_on=record.fetched_at,
                )
                for reading in _readings(
                    records,
                    record.source_name,
                    trial_id,
                    [Outcome(o.measure, o.time_frame) for o in read.facts.primary_outcomes],
                )
                # A reading below the bar is not published: the page and the data file
                # give the registry's own words for that answer instead (ADR 0003).
                if reading.confidence >= reading_accept_above
            ]
            results = [
                key
                for paper in read.results_papers
                if (
                    key := papers.add(
                        ExportedPaperRole(
                            role="trial_result", trial_id=trial_id, listed=paper.listed
                        ),
                        pubmed_id=paper.pubmed_id,
                    )
                )
            ]
        trials.append(
            ExportedTrial(
                trial_id=trial_id,
                source_name=newest.source_name,
                url=newest.source_url,
                title=title,
                phases=[TrialPhase(phase) for phase in newest.trial_phases or []],
                state=state,
                facts_as_of=facts_as_of,
                facts=facts,
                papers=list(dict.fromkeys(results)),
                readings=readings,
                claim_arm=arm_of_claim,
            )
        )
    return trials


def _readings(
    records: Records, source_name: str, trial_id: str, outcomes: list[Outcome]
) -> list[Reading]:
    """The stored readings of the trial that were read from these outcomes."""
    read = records.trial_read(source_name, trial_id)
    return [] if read is None else readings_that_stand(read[0], read[1], outcomes)


def _background(
    records: Records, terms: list[ClaimTerm], intervention: Entity
) -> list[ExportedCard]:
    """At most one card for the claim's condition and one for its intervention: the
    approved exact link with the highest score or, with none, the approved broader one
    or, for the intervention with neither, the approved kind link. Then at most one
    target card, from the approved named-gene link with the highest score.

    A link whose source is not accepted in the list of sources gives no card, nor does
    one whose term has no stored record, since a card states when its record was read.
    """
    components = intervention_components([intervention.name, *intervention.synonyms])
    # Highest score first; `terms` is by id, and the sort keeps that order among equals.
    approved = sorted(
        (term for term in terms if term.fit is not None and term.score is not None),
        key=lambda term: -(term.score or 0.0),
    )
    cards: list[ExportedCard] = []
    drug, drugs_target = _drug_cards(records, terms, components)
    # The drug source's own target comes before a gene named in the intervention.
    for role in (TermRole.CONDITION, TermRole.INTERVENTION, TermRole.DRUG, TermRole.TARGET):
        if role is TermRole.DRUG:
            cards += [drug] if drug is not None else []
            continue
        if role is TermRole.TARGET and drugs_target is not None:
            cards.append(drugs_target)
            continue
        for fit in TermFit:  # exact before broader before kind
            card = next(
                (
                    made
                    for term in approved
                    if term.role is role and term.fit is fit
                    if role is not TermRole.INTERVENTION or name_key(term.label) not in components
                    if (made := _card(records, term)) is not None
                    if role is not TermRole.INTERVENTION or name_key(made.label) not in components
                ),
                None,
            )
            if card is not None:
                cards.append(card)
                break
    return cards


def _card(records: Records, term: ClaimTerm) -> ExportedCard | None:
    listed = LISTED_SOURCES.get(term.source_name)
    record = records.term_record(term.source_name, term.external_id)
    if listed is None or not listed.accepted or record is None:
        return None
    assert term.fit is not None and term.score is not None and term.reviewed_by is not None
    read = read_record(record)
    name, definition, definition_source = None, read.definition, None
    if term.role is TermRole.TARGET:
        name = opentargets.describe(_source_record(record)).name or None
        # The description is UniProt's, carried by the target source. It is exported
        # only while UniProt is accepted, and then names UniProt as where it is from.
        described = LISTED_SOURCES.get(TARGET_DESCRIPTIONS_FROM)
        if definition is not None and (described is None or not described.accepted):
            definition = None
        if definition is not None:
            definition_source = TARGET_DESCRIPTIONS_FROM
    return ExportedCard(
        kind=term.role,
        fit=term.fit,
        label=read.label or term.label,
        name=name,
        definition=definition,
        definition_source=definition_source,
        url=record.url,
        source=term.source_name,
        external_id=term.external_id,
        version=read.version,
        score=round(term.score, 4),
        reasons=[
            ExportedCardReason.model_validate(reason)
            for reason in term.reasons
            if reason.get("code") in CARD_REASON_CODES
        ],
        decided_by=term.reviewed_by.value,
        read_at=record.fetched_at,
    )


def _drug_cards(
    records: Records, terms: list[ClaimTerm], components: set[str]
) -> tuple[ExportedCard | None, ExportedCard | None]:
    """The claim's drug card and, when the drug's record names exactly one single
    protein as its target, that target's card. Neither is scored: the drug was found by
    its exact name.

    Both rest on facts the drug source draws from another source under a share-alike
    licence, so both are made only while that source is accepted, and each names it.
    A drug whose record gives no kind of molecule and no mechanism makes no card.
    """
    listed, facts = (
        LISTED_SOURCES.get(opentargets.OpenTargets.name),
        LISTED_SOURCES.get(DRUG_FACTS_FROM),
    )
    if listed is None or not listed.accepted or facts is None or not facts.accepted:
        return None, None
    for link in (term for term in terms if term.role is TermRole.DRUG):
        if name_key(link.label) in components or link.source_name != listed.name:
            continue
        record = records.term_record(link.source_name, link.external_id)
        if record is None:
            continue
        drug = opentargets.describe_drug(_source_record(record))
        if name_key(drug.name) in components:
            continue
        if drug.molecule_kind is not None or drug.mechanisms:
            break
    else:
        return None, None
    assert link.fit is not None and link.reviewed_by is not None
    drug_card = ExportedCard(
        kind=TermRole.DRUG,
        fit=link.fit,
        label=drug.name or link.label,
        definition=None,
        url=record.url,
        source=link.source_name,
        external_id=link.external_id,
        version=None,
        score=None,
        molecule_kind=drug.molecule_kind,
        mechanisms=[
            ExportedMechanism(action=mechanism.action, target=mechanism.target_name)
            for mechanism in drug.mechanisms
        ],
        facts_source=DRUG_FACTS_FROM,
        reasons=[
            ExportedCardReason.model_validate(reason)
            for reason in link.reasons
            if reason.get("code") in CARD_REASON_CODES
        ],
        decided_by=link.reviewed_by.value,
        read_at=record.fetched_at,
    )
    target = opentargets.single_protein_target(drug)
    if target is None:
        return drug_card, None
    described = LISTED_SOURCES.get(TARGET_DESCRIPTIONS_FROM)
    definition = target.definition if described is not None and described.accepted else None
    target_card = ExportedCard(
        kind=TermRole.TARGET,
        fit=TermFit.EXACT,
        label=target.symbol,
        name=target.name or None,
        definition=definition,
        definition_source=TARGET_DESCRIPTIONS_FROM if definition is not None else None,
        url=record_url(link.source_name, target.identifier) or record.url,
        source=link.source_name,
        external_id=target.identifier,
        version=None,
        score=None,
        facts_source=DRUG_FACTS_FROM,
        reasons=[ExportedCardReason(code=DRUG_RECORD_NAMES_TARGET, name=drug_card.label)],
        decided_by=link.reviewed_by.value,
        read_at=record.fetched_at,
    )
    return drug_card, target_card


def _source_record(record: TermRecord) -> SourceRecord:
    return SourceRecord(
        record.source_name, record.external_id, record.url, record.payload, record.fetched_at
    )


def _card_sources(claims: list[ExportedClaim]) -> list[ExportedCardSource]:
    used = {
        name
        for claim in claims
        for card in claim.background
        for name in (card.source, card.definition_source, card.facts_source)
        if name
    }
    return [
        ExportedCardSource(
            name=listed.name,
            title=listed.title,
            credit=listed.credit,
            licence=listed.licence,
            url=listed.home_url,
            terms_url=listed.terms_url,
            in_data_file=listed.in_data_file,
        )
        for listed in LISTED_SOURCES.values()
        if listed.name in used
    ]


def _outlets(records: Records, claims: list[ExportedClaim]) -> list[ExportedOutlet]:
    domains = {outlet_domain(article.url) for claim in claims for article in claim.articles}
    return [
        ExportedOutlet(
            domain=icon.domain,
            icon=f"data:{icon.media_type};base64,{base64.b64encode(icon.content).decode()}",
            fetched_at=icon.fetched_at,
        )
        for icon in sorted(records.outlet_icons(domains), key=lambda icon: icon.domain)
        if icon.content is not None and not is_blank_icon(icon.content)
    ]


# A stage the reading gave less weight than this is left out of `also`.
STAGE_SHARE_FLOOR = 0.05


def _unconfirmed_stage_reading(
    records: Records, claim: Claim, *, show_above: float
) -> ExportedStageReading | None:
    """The latest reading of a claim's evidence stage, when the stage is not confirmed
    and the reading chose its stage with at least `show_above`. Shown, never used."""
    if claim.evidence_stage is not None:
        return None
    reading = records.stage_reading(claim)
    stages = {stage.value for stage in EvidenceStage}
    if reading is None or reading.choice not in stages:
        return None
    score = reading.probabilities.get(reading.choice, 0.0)
    if score < show_above:
        return None
    others = sorted(
        (
            (probability, stage)
            for stage, probability in reading.probabilities.items()
            if stage in stages and stage != reading.choice and probability >= STAGE_SHARE_FLOOR
        ),
        reverse=True,
    )
    return ExportedStageReading(
        stage=EvidenceStage(reading.choice),
        score=score,
        also=[
            ExportedStageShare(stage=EvidenceStage(stage), score=probability)
            for probability, stage in others
        ],
    )


def _clinical_records(
    events: list[EvidenceEvent],
    papers: _Papers,
    terms: list[ClaimTerm],
    trial_matches: dict[int, str],
) -> ClaimRecords:
    """What the claim's clinical categories are derived from: its approved trial
    records, its papers' index records, and the approved readings of a MeSH descriptor as
    its own condition."""
    by_trial: dict[str, list[EvidenceEvent]] = {}
    for event in events:
        if (
            event.source_name == ClinicalTrials.name
            and event.type in TRIAL_EVENT_TYPES
            and event.entity_match_id is not None
            and trial_matches.get(event.entity_match_id) == event.external_id
        ):
            by_trial.setdefault(event.external_id, []).append(event)
    return ClaimRecords(
        trials=tuple(
            (number, record.raw_payload)
            for number, snapshots in sorted(by_trial.items())
            if (record := newest_registry_record(snapshots)) is not None
        ),
        papers=tuple(
            (key, payload)
            for key, payload in papers.payloads.items()
            if any(
                role.role != "trial_result" or role.trial_id in by_trial
                for role in papers.found[key].roles
            )
        ),
        terms=tuple(
            CheckedTerm(term.external_id, term.label, term.score)
            for term in terms
            if term.role is TermRole.CONDITION
            and term.source_name == Mesh.name
            and term.fit is TermFit.EXACT
        ),
    )


def _clinical_categories(given: ClaimRecords, vocabulary: Vocabulary) -> list[Category] | None:
    """The claim's clinical categories, or None while a MeSH record needed to place them
    is not read: a paper heading whose descriptor is not stored, or a descriptor above a
    category."""
    derived = derive_categories(given.trials, given.papers, vocabulary, given.terms)
    needed = [category.identifier for category in derived.categories]
    if derived.unread_headings or vocabulary.missing(needed):
        return None
    return list(derived.categories)


def claim_clinical_records(records: Records, claim: Claim) -> ClaimRecords:
    """What the claim's clinical categories are derived from, as the export gathers it,
    for the reports."""
    events = records.events(claim)
    entities = records.entities(claim)
    papers = _Papers(records)
    trial_matches = _collect_matches(records, entities, events, papers)
    intervention = next((e for e in entities if e.type is EntityType.INTERVENTION), None)
    names = [intervention.name, *intervention.synonyms] if intervention else []
    # Results papers are found as each trial is read.
    _trials(records, events, papers, intervention_names=names)
    return _clinical_records(events, papers, records.terms(claim), trial_matches)


def _clinical(used: set[str], vocabulary: Vocabulary, not_read: int) -> ExportedClinical:
    """The tree the exported categories sit in: each with every descriptor above it."""
    parents, _ = vocabulary.hierarchy(used)
    nodes = sorted(parents)
    held = [node for node in (vocabulary.get(one) for one in nodes) if node is not None]
    return ExportedClinical(
        mesh_years=sorted({node.year for node in held if node.year}),
        nodes=[
            ExportedMeshNode(
                identifier=node.identifier,
                label=node.label,
                tree_numbers=list(node.tree_numbers),
                broader=sorted(parents[node.identifier]),
            )
            for node in held
        ],
        claims_not_read=not_read,
    )


def _approach_basis(
    claim: Claim, events: list[EvidenceEvent], names: list[str]
) -> ExportedApproachBasis | None:
    """The registry's one type for the claim's intervention, when it maps to the claim's
    approach. Derived from the claim's approved trial records, so it is the same from
    either store and says nothing of who set the approach."""
    if claim.approach is None:
        return None
    answer = approach_from_registry(
        registry_types(
            [event.raw_payload for event in events if event.source_name == ClinicalTrials.name],
            names,
        )
    )
    if answer.basis is None or answer.approach != claim.approach:
        return None
    return ExportedApproachBasis(type=answer.basis["type"], trials=answer.basis["trials"])


def _from(source: Session | Records) -> Records:
    return PostgresRecords(source) if isinstance(source, Session) else source


def build_export(
    source: Session | Records,
    *,
    now: datetime,
    no_signal_years: int = 3,
    reading_accept_above: float = 0.8,
    stage_show_above: float = 0.5,
    match_accept_above: float = 0.0,
) -> Export:
    """Everything the site may show, as of now.

    `source` is where the records are read from: the pipeline's session, or any other
    `Records`. The export is the same for the same records, whichever holds them.

    Each claim's status is derived again first, because the no-signal overlay depends
    on today's date. A claim exported for the first time gets its published time.

    Every approved, unarchived claim is included, whoever decided it, except one held
    awaiting the audit of its batch; a claim the assistant decided says it was not
    checked by a person.
    """
    records = _from(source)
    claims: list[ExportedClaim] = []
    last_checked: datetime | None = None
    # The stored MeSH descriptors, read once: every claim's categories are placed in it.
    vocabulary = Vocabulary(
        (record.external_id, record.payload) for record in records.mesh_records()
    )
    categories_used: set[str] = set()
    categories_not_read = 0
    # By slug, character by character: the same order whichever store hands them over,
    # where each store's own ordering of text would differ.
    for claim in sorted(records.published_claims(), key=lambda claim: claim.slug):
        # Every approved claim is published, whoever decided it (openspec auto-publish).
        # Whether a person checked it is still said, in `checked_by_person`.
        assistant = records.decided_by_assistant(claim)
        events = records.events(claim)
        flags = records.failure_flags(claim)
        entities = records.entities(claim)
        # The status is derived here by the rules, from what the reader handed over, and
        # put on the claim: its updated-at time changes only when the status does.
        evidence = evidence_of(events)
        origin_paper_ids = frozenset(
            match.external_id
            for entity in entities
            if entity.is_origin_paper
            for match in records.approved_matches(entity)
        )
        derivation = derive(
            evidence,
            flags_of(flags),
            first_reported_date=claim.first_reported_date,
            as_of=now.date(),
            origin_paper_ids=origin_paper_ids,
            no_signal_years=no_signal_years,
            evidence_stage=claim.evidence_stage,
        )
        keep_status(claim, derivation, now=now)
        if claim.published_at is None:
            claim.published_at = now
        for event in events:
            if last_checked is None or event.fetched_at > last_checked:
                last_checked = event.fetched_at
        articles = records.articles(claim)
        article_urls = {article.id: article.url for article in articles}
        intervention = next(
            (entity for entity in entities if entity.type is EntityType.INTERVENTION), None
        )
        assert intervention is not None, "every claim is created with its intervention entity"
        papers = _Papers(records)
        trial_matches = _collect_matches(records, entities, events, papers)
        terms = records.terms(claim)
        trials = _trials(
            records,
            events,
            papers,
            reading_accept_above,
            [intervention.name, *intervention.synonyms],
        )
        categories = _clinical_categories(
            _clinical_records(events, papers, terms, trial_matches), vocabulary
        )
        if categories is None:
            categories_not_read += 1
        else:
            categories_used.update(category.identifier for category in categories)
        organisations = organisations_of(
            records,
            entities,
            articles=articles,
            sponsors={
                trial.trial_id: trial.facts.sponsor.name
                for trial in trials
                if trial.facts and trial.facts.sponsor and trial.facts.sponsor.name
            },
        )
        claims.append(
            ExportedClaim(
                slug=claim.slug,
                headline=claim.headline,
                summary=claim.summary,
                vertical=claim.vertical,
                approach=claim.approach,
                approach_basis=_approach_basis(
                    claim, events, [intervention.name, *intervention.synonyms]
                ),
                clinical_categories=None
                if categories is None
                else [
                    ExportedClinicalCategory(
                        identifier=category.identifier,
                        sources=[
                            ExportedCategorySource(
                                kind=source.kind,
                                identifier=source.identifier,
                                score=None if source.score is None else round(source.score, 4),
                            )
                            for source in category.sources
                        ],
                    )
                    for category in categories
                ],
                intervention=ExportedIntervention(
                    name=intervention.name, synonyms=list(intervention.synonyms)
                ),
                indication=claim.indication,
                first_reported_date=claim.first_reported_date,
                evidence_stage=claim.evidence_stage,
                evidence_stage_reading=_unconfirmed_stage_reading(
                    records, claim, show_above=stage_show_above
                ),
                checked_by_person=claim.reviewed_by is Decider.HUMAN and not assistant,
                status=ExportedStatus(
                    code=derivation.status,
                    overlay_years=derivation.overlay_years,
                    updated_at=claim.status_updated_at,
                    explained_by=list(derivation.explaining_event_ids),
                    history=[
                        ExportedStatusChange(on=change.on, code=change.status)
                        for change in history(
                            evidence,
                            flags_of(flags),
                            first_reported_date=claim.first_reported_date,
                            origin_paper_ids=origin_paper_ids,
                            evidence_stage=claim.evidence_stage,
                        )
                    ],
                ),
                articles=[
                    ExportedArticle(
                        url=article.url,
                        outlet=article.outlet,
                        title=article.title,
                        published_date=article.published_date,
                        archive_url=article.archive_url,
                        published_by=publisher_of(article.url, organisations),
                    )
                    for article in articles
                ],
                promises=[
                    ExportedPromise(
                        description=promise.description,
                        parsed_date=promise.parsed_date,
                        article_url=article_urls[promise.source_article_id],
                    )
                    for promise in records.promises(claim)
                ],
                events=[
                    ExportedEvent(
                        id=event.id,
                        type=event.type,
                        event_date=event.event_date,
                        date_basis=event.date_basis,
                        summary=event.summary,
                        source_name=event.source_name,
                        source_url=event.source_url,
                        trial_id=event.external_id if event.type in TRIAL_EVENT_TYPES else None,
                        trial_phases=[TrialPhase(phase) for phase in event.trial_phases or []],
                        trial_state=event.trial_state,
                        regulatory_outcome=event.regulatory_outcome,
                        confidence=round(event.confidence, 4),
                    )
                    for event in events
                ],
                matches=_matches(records, claim),
                trials=trials,
                papers=papers.listed(),
                background=_background(records, terms, intervention),
                organisations=organisations,
                reported_statements=_statements(records, claim),
                failure_flags=[
                    ExportedFailureFlag(trial_id=flag.trial_external_id, source_url=flag.source_url)
                    for flag in flags
                ],
            )
        )
    records.done()
    card_sources = _card_sources(claims)
    # An address that was a claim's page leads to the claim it was merged into, or to its
    # page under a new slug, when that claim is published here. Otherwise it answers
    # gone, like any claim taken down.
    public = {claim.slug for claim in claims}
    elsewhere = records.moved()
    leads_to = {slug: claim.slug for slug, claim in elsewhere if claim.slug in public}
    gone = {
        claim.slug: claim.archived_at.date()
        for claim in records.taken_down()
        if claim.archived_at is not None and claim.slug not in leads_to
    }
    for slug, claim in elsewhere:
        if slug not in leads_to and claim.archived_at is not None:
            gone.setdefault(slug, claim.archived_at.date())
    return Export(
        schema_version=SCHEMA_VERSION,
        generated_at=now,
        last_checked_at=last_checked,
        match_accept_above=match_accept_above if match_accept_above > 0 else None,
        clinical=_clinical(categories_used, vocabulary, categories_not_read),
        sources=[
            ExportedSource(name=name, url=url)
            for name, url in [
                *SOURCES,
                *(
                    (name, url)
                    for name, url in OTHER_REGISTRIES.items()
                    if any(event.source_name == name for claim in claims for event in claim.events)
                ),
                # A source a published card comes from is credited like the registries.
                *((source.title, source.url) for source in card_sources),
                *(
                    [ORGANISATION_REGISTRY]
                    if any(org.identified for claim in claims for org in claim.organisations)
                    else []
                ),
            ]
        ],
        verticals=[
            ExportedVertical(slug=slug, title=title, group=_group_of(slug))
            for slug, title in VERTICALS.items()
        ],
        retired_verticals=[
            ExportedRetiredVertical(slug=slug, successor=successor)
            for slug, successor in RETIRED_VERTICALS.items()
        ],
        outlets=_outlets(records, claims),
        claims=claims,
        archived=[ExportedArchived(slug=slug, on=on) for slug, on in sorted(gone.items())],
        moved=[ExportedMoved(slug=slug, to=to) for slug, to in leads_to.items()],
        card_sources=card_sources,
    )


def write_export(
    source: Session | Records,
    path: Path,
    *,
    now: datetime,
    no_signal_years: int = 3,
    reading_accept_above: float = 0.8,
    stage_show_above: float = 0.5,
    match_accept_above: float = 0.0,
) -> Export:
    """Write the export to `path`, replacing any earlier file only once it is complete."""
    export = build_export(
        source,
        now=now,
        no_signal_years=no_signal_years,
        reading_accept_above=reading_accept_above,
        stage_show_above=stage_show_above,
        match_accept_above=match_accept_above,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    partial.write_text(export.model_dump_json(indent=2) + "\n")
    partial.replace(path)
    return export


def write_schema(path: Path) -> None:
    path.write_text(json.dumps(export_json_schema(), indent=2) + "\n")
