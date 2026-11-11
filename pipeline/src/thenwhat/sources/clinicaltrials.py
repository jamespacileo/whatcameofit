"""ClinicalTrials.gov API v2. Terms and limits: docs/sources.md."""

import re
from datetime import datetime
from typing import Any

from thenwhat.sources.base import Source, SourceRecord

API = "https://clinicaltrials.gov/api/v2"
NCT_ID = re.compile(r"NCT\d{8}")
# A search only has to show enough to judge a match; the full record is fetched by identifier.
SEARCH_FIELDS = (
    "NCTId,BriefTitle,OfficialTitle,InterventionName,LeadSponsorName,Phase,OverallStatus,Condition"
)
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
        """The trials whose interventions match the term.

        A specific name returns every trial it has, across all result pages. A broad name
        (more than BROAD_NAME trials) is searched within the condition instead: first by the
        condition as worded, then by its telling words. If the registry files nothing under
        either, the first page of the broad search is returned, so the reviewer still sees
        that trials of the intervention exist.
        """
        first, total, next_token = self._page(intervention, None, None)
        if condition and total > BROAD_NAME:
            for wording in (condition, _telling_words(condition)):
                if wording:
                    narrowed = self._all_pages(intervention, wording)
                    if narrowed:
                        return narrowed
            return first
        records = first
        while next_token:
            more, _, next_token = self._page(intervention, None, next_token)
            records += more
        return records

    def _all_pages(self, intervention: str, condition: str) -> list[SourceRecord]:
        records, _, next_token = self._page(intervention, condition, None)
        while next_token:
            more, _, next_token = self._page(intervention, condition, next_token)
            records += more
        return records

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
        fetched = self._get(f"{API}/studies", params)
        if fetched is None:
            return [], 0, None
        studies = fetched.payload.get("studies", [])
        records = [self._record(study, fetched.fetched_at) for study in studies]
        total = fetched.payload.get("totalCount", len(studies))
        return records, total, fetched.payload.get("nextPageToken")

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
