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

    def search_trials(self, intervention: str) -> list[SourceRecord]:
        """Every trial whose interventions match the term, across all result pages."""
        records: list[SourceRecord] = []
        page_token: str | None = None
        while True:
            params = {"query.intr": intervention, "pageSize": "100", "fields": SEARCH_FIELDS}
            if page_token:
                params["pageToken"] = page_token
            fetched = self._get(f"{API}/studies", params)
            if fetched is None:
                break
            records += [
                self._record(study, fetched.fetched_at)
                for study in fetched.payload.get("studies", [])
            ]
            page_token = fetched.payload.get("nextPageToken")
            if not page_token:
                break
        return records

    def _record(self, study: dict[str, Any], fetched_at: datetime) -> SourceRecord:
        nct_id = study["protocolSection"]["identificationModule"]["nctId"]
        return SourceRecord(
            source_name=self.name,
            external_id=nct_id,
            url=f"https://clinicaltrials.gov/study/{nct_id}",
            payload=study,
            fetched_at=fetched_at,
        )
