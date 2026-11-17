"""PubMed through NCBI's E-utilities: which papers carry a trial's registry number in
the field their publisher supplied for it. Terms, key and limits: docs/sources.md.

One search carries the numbers of many trials, each tagged for the Secondary Source ID
field (`[si]`), and answers with PubMed numbers only: it does not say which trial a
paper matched. So each paper's own record is read back, and a paper is given to a trial
only when that record lists the trial's number under ClinicalTrials.gov. A paper that
only mentions a number in its text is never found this way.

A paper's record holds its abstract and its authors. Neither leaves this module: what
is kept of a record is its number, title, journal, year, kinds of publication and the
registry numbers it carries.
"""

import re
import xml.etree.ElementTree as ElementTree
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from thenwhat.backfill.allowance import Allowances
from thenwhat.backfill.errors import BackfillError, SourceStop
from thenwhat.sources.base import (
    MissingContact,
    SourceError,
    SourceUnavailable,
    SystemTime,
    Time,
    require_recorded,
)

API = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
DATABASE = "pubmed"
# The name PubMed's records give the registry in their list of databanks.
CLINICALTRIALS = "ClinicalTrials.gov"
REGISTRY_NUMBER = re.compile(r"NCT\d{8}")
# The most PubMed numbers one search may return, and the most asked for in one fetch
# without the History server (docs/sources.md).
SEARCH_MAX = 10_000
FETCH_MAX = 200
# NCBI asks that a series of more than this many requests runs at the weekend or
# between 21:00 and 05:00 Eastern time on a weekday.
SMALL_JOB = 100
EASTERN = ZoneInfo("America/New_York")
OFF_PEAK_FROM, OFF_PEAK_UNTIL = 21, 5


class MissingTool(BackfillError):
    """No tool name is configured, so no request may be sent."""


class PeakHours(SourceStop):
    """A large job reached NCBI's peak hours. The run ends with its records still due."""


class SourceRejectedKey(SourceStop):
    """NCBI did not accept the key. Every record would fail the same way."""


class TooManyPapers(SourceError):
    """A search matched more papers than one answer may hold. Ask for fewer trials."""


@dataclass(frozen=True, slots=True)
class Paper:
    pubmed_id: str
    # The ClinicalTrials.gov numbers the paper's own record carries, in its order.
    trial_numbers: tuple[str, ...]
    # The record as kept: no abstract and no author.
    raw: dict[str, Any]


def is_off_peak(moment: datetime) -> bool:
    """Whether NCBI's servers are in the hours it asks large jobs to keep to."""
    eastern = moment.astimezone(EASTERN)
    weekend = eastern.weekday() >= 5
    return weekend or eastern.hour >= OFF_PEAK_FROM or eastern.hour < OFF_PEAK_UNTIL


def search_term(numbers: Sequence[str]) -> str:
    return " OR ".join(f"{number}[si]" for number in numbers)


def _text(element: ElementTree.Element | None) -> str | None:
    if element is None:
        return None
    text = " ".join("".join(element.itertext()).split())
    return text or None


def read_papers(xml: str) -> list[Paper]:
    """The papers in a fetched set, each reduced to what is kept."""
    papers: list[Paper] = []
    for article in ElementTree.fromstring(xml).iter("PubmedArticle"):
        citation = article.find("MedlineCitation")
        pubmed_id = _text(citation.find("PMID")) if citation is not None else None
        if citation is None or pubmed_id is None:
            continue
        databanks: list[dict[str, Any]] = []
        numbers: list[str] = []
        for bank in citation.iter("DataBank"):
            name = _text(bank.find("DataBankName"))
            accessions = [
                number for accession in bank.iter("AccessionNumber") if (number := _text(accession))
            ]
            databanks.append({"name": name, "accession_numbers": accessions})
            if name == CLINICALTRIALS:
                numbers += [
                    number.upper()
                    for number in accessions
                    if REGISTRY_NUMBER.fullmatch(number.upper())
                ]
        journal = citation.find("Article/Journal")
        raw = {
            "pmid": pubmed_id,
            "title": _text(citation.find("Article/ArticleTitle")),
            "journal": _text(journal.find("Title")) if journal is not None else None,
            "year": (
                _text(journal.find("JournalIssue/PubDate/Year")) if journal is not None else None
            ),
            "publication_types": [
                kind for one in citation.iter("PublicationType") if (kind := _text(one))
            ],
            "databanks": databanks,
        }
        papers.append(Paper(pubmed_id, tuple(dict.fromkeys(numbers)), raw))
    return papers


class PubMed:
    name = "pubmed"

    def __init__(
        self,
        *,
        contact_email: str | None,
        tool: str | None,
        api_key: str | None,
        allowances: Allowances,
        transport: httpx.BaseTransport | None = None,
        time: Time | None = None,
    ) -> None:
        self._contact = (contact_email or "").strip()
        self._tool = (tool or "").strip()
        self._key = (api_key or "").strip()
        self._allowances = allowances
        self._time = time or SystemTime()
        self._client = httpx.Client(transport=transport, timeout=60.0)
        self.requests_made = 0

    def check_ready(self) -> None:
        """Refuse before any record is touched when a request could not be sent as
        NCBI's usage policy asks: every request names the software and gives its
        developer's address."""
        require_recorded(self.name)
        if not self._contact:
            raise MissingContact(
                "CONTACT_EMAIL is not set, so no request was sent. NCBI asks every "
                "E-utilities request to give the developer's address (docs/sources.md)."
            )
        if not self._tool or " " in self._tool:
            raise MissingTool(
                "PUBMED_TOOL is not set to a name with no spaces, so no request was sent. "
                "NCBI asks every E-utilities request to name its software (docs/sources.md)."
            )

    def papers_carrying(self, numbers: Sequence[str]) -> tuple[list[Paper], datetime]:
        """The papers whose records PubMed returns for these trials' numbers in the
        Secondary Source ID field, each with the numbers its own record carries, and
        when they were fetched. One search, then one fetch for each 200 papers."""
        if not numbers:
            return [], self._time.now()
        found = self._post(
            "esearch.fcgi",
            {"term": search_term(numbers), "retmax": str(SEARCH_MAX), "retmode": "json"},
        ).json()["esearchresult"]
        ids = [str(one) for one in found.get("idlist", [])]
        if int(found.get("count", len(ids))) > len(ids):
            raise TooManyPapers(
                f"{self.name} holds {found['count']} papers for {len(numbers)} trials, more "
                "than one answer returns. Ask for fewer trials in a request."
            )
        papers: list[Paper] = []
        for start in range(0, len(ids), FETCH_MAX):
            fetched = self._post(
                "efetch.fcgi", {"id": ",".join(ids[start : start + FETCH_MAX]), "retmode": "xml"}
            )
            papers += read_papers(fetched.text)
        return papers, self._time.now()

    def _post(self, utility: str, fields: dict[str, str]) -> httpx.Response:
        """One request, by POST so a long list of numbers is never an address, counted
        against the shared allowance."""
        self.check_ready()
        if self.requests_made >= SMALL_JOB and not is_off_peak(self._time.now()):
            raise PeakHours(
                f"{self.name}: NCBI asks that more than {SMALL_JOB} requests run at the "
                "weekend or between 21:00 and 05:00 Eastern time. Run the step again then."
            )
        self._allowances.claim(self.name)
        self.requests_made += 1
        data = {"db": DATABASE, "tool": self._tool, "email": self._contact, **fields}
        if self._key:
            data["api_key"] = self._key
        try:
            response = self._client.post(f"{API}/{utility}", data=data)
        except httpx.TransportError as error:
            raise SourceUnavailable(f"{self.name} could not be reached: {error}") from None
        if response.status_code == 429:
            raise self._allowances.refused(self.name, _retry_after(response))
        if response.status_code in (401, 403) or (
            response.status_code == 400 and "api-key" in response.text.lower()
        ):
            raise SourceRejectedKey(
                f"{self.name} did not accept the request (status {response.status_code}). "
                "Check PUBMED_API_KEY."
            )
        if response.status_code >= 500:
            raise SourceUnavailable(f"{self.name} answered with status {response.status_code}.")
        if not response.is_success:
            raise SourceError(
                f"{self.name} refused the request with status {response.status_code}."
            )
        return response


def _retry_after(response: httpx.Response) -> float | None:
    try:
        return float(response.headers["Retry-After"])
    except (KeyError, ValueError):
        return None
