"""ClinicalTrials.gov API v2. Terms and limits: docs/sources.md."""

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import httpx

from thenwhat.sources.base import (
    MissingContact,
    Source,
    SourceError,
    SourceRecord,
    UnsearchableTerm,
)

API = "https://clinicaltrials.gov/api/v2"
NCT_ID = re.compile(r"NCT\d{8}")
# A search only has to show enough to judge a match; the full record is fetched by identifier.
# The acronym, the enrolment and the collaborators let a lookup tell which of a treatment's
# trials an article reports. An intervention's other names say what else the sponsor calls
# it: a trial filed under a development code lists the generic name there.
SEARCH_FIELDS = (
    "NCTId,BriefTitle,OfficialTitle,InterventionName,LeadSponsorName,Phase,OverallStatus,Condition"
    ",Acronym,EnrollmentCount,CollaboratorName,StudyType"
    ",InterventionOtherName,InterventionDescription,InterventionArmGroupLabel"
    ",ArmGroupLabel,ArmGroupType,ArmGroupDescription,ArmGroupInterventionName"
)
# What a bulk load keeps of each trial: what identifies it, its activity and results
# dates, its sponsor, size, treatment arms, condition descriptors, references and planned primary
# outcome. Never its
# descriptions, eligibility, locations, contacts, results sections or reference
# citations. Each date is asked with its type, so that actual and anticipated dates are
# told apart.
LIST_FIELDS = (
    "NCTId,BriefTitle,Condition,InterventionType,InterventionName,InterventionOtherName"
    ",Phase,OverallStatus,StartDate,StartDateType,LeadSponsorClass"
    ",LastUpdatePostDate,StudyFirstPostDate"
    ",PrimaryCompletionDate,PrimaryCompletionDateType,CompletionDate,CompletionDateType"
    ",ResultsFirstPostDate,HasResults,WhyStopped"
    ",Acronym,OfficialTitle,OrgStudyId,SecondaryId,SecondaryIdType"
    ",LeadSponsorName,CollaboratorName,CollaboratorClass,EnrollmentCount,EnrollmentType"
    ",ReferencePMID,ReferenceType,SeeAlsoLinkURL,SeeAlsoLinkLabel"
    ",PrimaryOutcomeMeasure,PrimaryOutcomeTimeFrame"
    ",StudyType,DesignPrimaryPurpose,DesignAllocation,DesignInterventionModel"
    ",ArmGroupLabel,ArmGroupType"
    ",ArmGroupInterventionName,InterventionArmGroupLabel"
    ",ConditionBrowseModule"
    # Only the type: it says when the lead sponsor is a sponsor-investigator, a person
    # whose name is then not kept. The investigator's name, title and affiliation in the
    # same module are never asked for.
    ",ResponsiblePartyType"
)
# The most trials the registry returns in one page.
LIST_PAGE_SIZE = 1000


@dataclass(frozen=True, slots=True)
class Searched:
    """One search of the registry for a term: what it reported holding, and what was
    taken. Behavior: openspec entity-resolution, "A registry search leaves a record"."""

    source_name: str
    term: str
    records: list[SourceRecord]
    # How many trials the registry said it holds for the search whose records were taken.
    reported: int
    # The wording of the condition the search was narrowed by, if it was.
    condition: str | None = None
    # A limit left some of the reported trials out.
    cut: bool = False

    @property
    def kept(self) -> int:
        return len(self.records)


@dataclass(frozen=True, slots=True)
class NotSent:
    """A term that was not searched for, and why."""

    source_name: str
    term: str
    reason: str


# Why a search phrase with no condition is not sent.
PHRASE_ALONE = "a search phrase is searched within a condition only, and none was given"


@dataclass(frozen=True, slots=True)
class TrialPage:
    """One page of the registry's list: the trials as returned, and where the next page starts."""

    studies: list[dict[str, Any]]
    next_token: str | None
    fetched_at: datetime


# A trial's name that this many trials carry does not identify one.
MAX_NAMED_TRIALS = 20
# A name with more trials than this is a class or a common substance, not one product.
# Such a name is searched within the claim's condition.
BROAD_NAME = 100
# Words nearly every condition shares. They are left out when a condition is tried word by word.
GENERIC_CONDITION_WORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "the",
        "of",
        "in",
        "for",
        "with",
        "from",
        "to",
        "or",
        "by",
        "after",
        "during",
        "due",
        "caused",
        "that",
        "which",
        "disease",
        "diseases",
        "disorder",
        "disorders",
        "syndrome",
        "syndromes",
        "condition",
        "conditions",
        "chronic",
        "acute",
        "severe",
        "mild",
        "moderate",
        "advanced",
        "early",
        "late",
        "stage",
        "type",
        "high",
        "low",
        "risk",
        "loss",
        "pain",
        "cancer",
        "blood",
        "patients",
        "patient",
        "adults",
        "adult",
        "children",
        "people",
    ]
)


# How the registry begins its answer when it cannot read a search as written, for
# example "Error parsing query in Intervention / treatment: Too complicated query".
UNREADABLE_QUERY = re.compile(r"Error parsing query in (?P<field>[^:]+): (?P<reason>.+)", re.DOTALL)


class _UnreadableQuery(SourceError):
    """The registry could not read one field of a search."""

    def __init__(self, field: str, reason: str) -> None:
        super().__init__(reason)
        self.field = field
        self.reason = reason


class _UnreadableCondition(UnsearchableTerm):
    """Only the condition field was refused; bounded discovery wording may remain."""


class ClinicalTrials(Source):
    name = "clinicaltrials.gov"
    default_rate_per_second = 2.0

    def fetch_trial(self, nct_id: str, *, force: bool = False) -> SourceRecord | None:
        """The full registry record of one trial, or None if the registry has no such trial."""
        nct_id = nct_id.strip().upper()
        if not NCT_ID.fullmatch(nct_id):
            return None
        fetched = self._get(f"{API}/studies/{nct_id}", force=force)
        if fetched is None:
            return None
        return self._record(fetched.payload, fetched.fetched_at)

    def search_trials(self, intervention: str, condition: str | None = None) -> list[SourceRecord]:
        """The trials whose interventions match the term, as `name_search` takes them."""
        return self.name_search(intervention, condition).records

    def name_search(self, intervention: str, condition: str | None = None) -> Searched:
        """The trials whose interventions match the term, with what the registry reported.

        A specific name returns every trial it has, across all result pages. A broad name
        (more than BROAD_NAME trials) is searched within the condition instead: first by the
        condition as worded, then by its telling words. A name that is still broad within
        the condition returns the registry's first page there, its most relevant
        BROAD_NAME trials, each to be scored like any candidate: an established drug such as
        buprenorphine has hundreds of trials for opioid use disorder, and returning none
        made its claim read "no trial found" (batch 2's audit, 2026-11-16). A name with no
        trial under the condition returns nothing.
        """
        first, total, next_token = self._page(intervention, None, None)
        if condition and total > BROAD_NAME:
            return self._condition_trials(intervention, condition, keep_most_relevant=True)
        records = first
        while next_token:
            more, _, next_token = self._page(intervention, None, next_token)
            records += more
        return Searched(self.name, intervention, records, reported=total)

    def phrase_search(self, phrase: str, condition: str | None) -> Searched | NotSent:
        """The trials a search phrase finds within the condition.

        A phrase is the registry's words for a treatment with no product name, so it is
        broader than a name and is never searched alone. It is tried within the condition
        as worded, then by the condition's telling words. A phrase with more than
        BROAD_NAME trials there, or none, identifies nothing and returns nothing.
        """
        if not condition:
            return NotSent(self.name, phrase, PHRASE_ALONE)
        return self._condition_trials(phrase, condition)

    def _condition_trials(
        self, intervention: str, condition: str, *, keep_most_relevant: bool = False
    ) -> Searched:
        """Discover candidates with at most two wordings, never altering scoring scope.
        A search still broad within the condition gives nothing, or, for a name, the
        first page the registry returns there: either way a limit left trials out."""
        wordings = [condition]
        fallback = _telling_words(condition)
        if fallback and fallback != condition:
            wordings.append(fallback)
        for index, wording in enumerate(wordings):
            try:
                narrowed, within, _ = self._page(intervention, wording, None)
            except _UnreadableCondition:
                if index == len(wordings) - 1:
                    raise
                continue
            if within > BROAD_NAME:
                kept = narrowed if keep_most_relevant else []
                return Searched(self.name, intervention, kept, within, wording, cut=True)
            if narrowed or index == len(wordings) - 1:
                return Searched(self.name, intervention, narrowed, within, wording)
        return Searched(self.name, intervention, [], 0, wordings[-1])

    def named_trials(self, name: str, condition: str | None = None) -> list[SourceRecord]:
        """The trials that carry this name in their acronym or title, such as SURMOUNT-5.
        Narrow a broad name once by condition; never paginate ambiguous names."""
        phrase = name.replace('"', " ").strip()
        if not phrase:
            return []
        params = {
            "query.titles": f'"{phrase}"',
            "pageSize": str(MAX_NAMED_TRIALS),
            "fields": SEARCH_FIELDS,
            "countTotal": "true",
        }
        for within in (None, condition) if condition else (None,):
            narrowed = params | ({"query.cond": within} if within else {})
            try:
                fetched = self._get(f"{API}/studies", narrowed)
            except _UnreadableQuery as unreadable:
                raise UnsearchableTerm(name, unreadable.reason, self.name) from None
            if fetched is None:
                return []
            studies = fetched.payload.get("studies", [])
            if fetched.payload.get("totalCount", len(studies)) <= MAX_NAMED_TRIALS:
                return [self._record(study, fetched.fetched_at) for study in studies]
        return []

    def list_page(
        self,
        condition: str,
        *,
        page_token: str | None = None,
        updated_since: date | None = None,
        page_size: int = LIST_PAGE_SIZE,
    ) -> TrialPage:
        """One page of the trials that meet a condition written in the registry's own
        expression language, optionally only those the registry updated since a date.

        For bulk loads: up to a thousand trials per request, not one request per trial.
        The answer is not cached, because a page is large and is stored trial by trial.
        """
        if not self._contact:
            raise MissingContact("CONTACT_EMAIL is not set, so no request was sent.")
        expression = condition
        if updated_since is not None:
            expression = (
                f"({condition}) AND AREA[LastUpdatePostDate]RANGE[{updated_since.isoformat()},MAX]"
            )
        params = {
            "filter.advanced": expression,
            "fields": LIST_FIELDS,
            "pageSize": str(page_size),
        }
        if page_token:
            params["pageToken"] = page_token
        response = self._request(f"{API}/studies", params)
        payload = response.json() if response is not None else {}
        return TrialPage(payload.get("studies", []), payload.get("nextPageToken"), self._time.now())

    def _page(
        self, intervention: str, condition: str | None, page_token: str | None
    ) -> tuple[list[SourceRecord], int, str | None]:
        """One page of a search: its records, the search's total, and the next page's token."""
        params = {
            "query.intr": intervention,
            "pageSize": "100",
            "fields": SEARCH_FIELDS,
            "countTotal": "true",
        }
        if condition:
            params["query.cond"] = condition
        if page_token:
            params["pageToken"] = page_token
        try:
            fetched = self._get(f"{API}/studies", params)
        except _UnreadableQuery as unreadable:
            # The registry names the field it could not read: the treatment or the condition.
            if condition and unreadable.field == "Conditions or disease":
                raise _UnreadableCondition(condition, unreadable.reason, self.name) from None
            at_fault = intervention if unreadable.field.startswith("Intervention") else condition
            raise UnsearchableTerm(at_fault or intervention, unreadable.reason, self.name) from None
        if fetched is None:
            return [], 0, None
        studies = fetched.payload.get("studies", [])
        records = [self._record(study, fetched.fetched_at) for study in studies]
        total = fetched.payload.get("totalCount", len(studies))
        return records, total, fetched.payload.get("nextPageToken")

    def _heed(self, response: httpx.Response) -> None:
        """A search the registry cannot read is its own failure, with the registry's
        reason. Only a condition refusal may use the existing discovery fallback."""
        if response.status_code == 400:
            unreadable = UNREADABLE_QUERY.match(response.text.strip())
            if unreadable:
                raise _UnreadableQuery(unreadable["field"].strip(), unreadable["reason"].strip())

    def _record(self, study: dict[str, Any], fetched_at: datetime) -> SourceRecord:
        nct_id = study["protocolSection"]["identificationModule"]["nctId"]
        return SourceRecord(
            source_name=self.name,
            external_id=nct_id,
            url=f"https://clinicaltrials.gov/study/{nct_id}",
            payload=study,
            fetched_at=fetched_at,
        )


def _telling_words(condition: str) -> str | None:
    """The condition's distinguishing words joined with OR, for a registry that does not
    know the condition as worded. None when no such word is left."""
    words = [
        word
        for word in re.findall(r"[a-z0-9][a-z0-9'-]*", condition.lower())
        if len(word) >= 3 and word not in GENERIC_CONDITION_WORDS
    ]
    unique = list(dict.fromkeys(words))
    return " OR ".join(unique) if unique else None
