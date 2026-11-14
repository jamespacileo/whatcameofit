"""What one Europe PMC record says of its paper. Pure. Behavior: openspec paper-facts.

Each fact is one field of the index record read by a fixed rule, so a reader who opens
the record finds it there. A field the record does not hold, or holds in an unexpected
shape, gives an absent fact and never an error; nothing is inferred.

The paper itself is never read: no abstract, no full text. Nor are authors,
affiliations or citation counts. `reduced` removes the abstract and every name from a
record before it is stored for its facts.
"""

from dataclasses import dataclass
from typing import Any, Literal

PaperKind = Literal[
    "randomised_trial",
    "clinical_trial",
    "meta_analysis",
    "systematic_review",
    "review",
    "observational_study",
    "case_report",
    "preprint",
    "comment",
    "correction",
    "retraction_notice",
    "article",
]
StudiedIn = Literal["people", "animals"]

# The twelve kinds, from most to least specific. Facts carry them in this order.
KIND_ORDER: tuple[PaperKind, ...] = (
    "randomised_trial",
    "clinical_trial",
    "meta_analysis",
    "systematic_review",
    "review",
    "observational_study",
    "case_report",
    "preprint",
    "comment",
    "correction",
    "retraction_notice",
    "article",
)
# The index's publication types, in lower case, and the kind each one is. A type that
# is not here adds no kind: the site never meets a code it has no wording for.
KINDS: dict[str, PaperKind] = {
    "randomized controlled trial": "randomised_trial",
    "clinical trial": "clinical_trial",
    "clinical trial, phase i": "clinical_trial",
    "clinical trial, phase ii": "clinical_trial",
    "clinical trial, phase iii": "clinical_trial",
    "clinical trial, phase iv": "clinical_trial",
    "controlled clinical trial": "clinical_trial",
    "adaptive clinical trial": "clinical_trial",
    "pragmatic clinical trial": "clinical_trial",
    "equivalence trial": "clinical_trial",
    "clinical study": "clinical_trial",
    "meta-analysis": "meta_analysis",
    "network meta-analysis": "meta_analysis",
    "systematic review": "systematic_review",
    "review": "review",
    "review-article": "review",
    "scoping review": "review",
    "observational study": "observational_study",
    "case reports": "case_report",
    "case-report": "case_report",
    "preprint": "preprint",
    "editorial": "comment",
    "letter": "comment",
    "comment": "comment",
    "news": "comment",
    "published erratum": "correction",
    "correction": "correction",
    "retraction of publication": "retraction_notice",
    "retraction": "retraction_notice",
    "journal article": "article",
    "research-article": "article",
}
# The publication type the index gives a paper that has been retracted.
RETRACTED = "retracted publication"
# The two check tags an indexer applies. No other subject heading is read.
HEADINGS: dict[str, StudiedIn] = {"Humans": "people", "Animals": "animals"}

# Removed from a record before it is stored for its facts: the abstract is copyright,
# the names are personal data, and paper facts need neither.
NOT_STORED = (
    "abstractText",
    "authorList",
    "authorString",
    "authorIdList",
    "affiliation",
    "investigatorList",
    "fullTextUrlList",
    "fullTextIdList",
)


@dataclass(frozen=True, slots=True)
class PaperFacts:
    title: str | None
    journal: str | None
    year: int | None
    # Every kind the record gives, most specific first.
    kinds: tuple[PaperKind, ...]
    open_access: bool | None
    retracted: bool
    # What the record's subject headings say the study was in. Empty when the record
    # has no headings or names neither.
    studied_in: tuple[StudiedIn, ...]


def read_paper(record: dict[str, Any]) -> PaperFacts:
    types = {kind.casefold() for kind in _strings(record.get("pubTypeList"), "pubType")}
    found = {KINDS[kind] for kind in types if kind in KINDS}
    headings = {
        heading.get("descriptorName")
        for heading in _objects(record.get("meshHeadingList"), "meshHeading")
    }
    journal = record.get("journalInfo")
    journal = journal.get("journal") if isinstance(journal, dict) else None
    open_access = record.get("isOpenAccess")
    return PaperFacts(
        title=_text(record, "title"),
        journal=_text(journal, "title") if isinstance(journal, dict) else None,
        year=_year(record),
        kinds=tuple(kind for kind in KIND_ORDER if kind in found),
        open_access={"Y": True, "N": False}.get(open_access)
        if isinstance(open_access, str)
        else None,
        retracted=RETRACTED in types,
        studied_in=tuple(code for name, code in HEADINGS.items() if name in headings),
    )


def reduced(record: dict[str, Any]) -> dict[str, Any]:
    """The record without its abstract, its authors, their identifiers and
    affiliations, and its full-text links."""
    return {key: value for key, value in record.items() if key not in NOT_STORED}


def doi_of(record: dict[str, Any]) -> str | None:
    doi = record.get("doi")
    return doi.lower() if isinstance(doi, str) and doi.startswith("10.") else None


def pubmed_id_of(record: dict[str, Any]) -> str | None:
    pubmed_id = record.get("pmid")
    return pubmed_id if isinstance(pubmed_id, str) and pubmed_id.isdigit() else None


def record_page(record: dict[str, Any]) -> str | None:
    """Where a reader can open the index record itself."""
    source, number = record.get("source"), record.get("id")
    if not (isinstance(source, str) and isinstance(number, str) and source and number):
        return None
    return f"https://europepmc.org/article/{source}/{number}"


def _year(record: dict[str, Any]) -> int | None:
    for text in (record.get("pubYear"), str(record.get("firstPublicationDate") or "")[:4]):
        if isinstance(text, str) and len(text) == 4 and text.isdigit():
            return int(text)
    return None


def _text(value: dict[str, Any], key: str) -> str | None:
    text = value.get(key)
    return text if isinstance(text, str) and text.strip() else None


def _strings(value: Any, key: str) -> list[str]:
    items = value.get(key) if isinstance(value, dict) else None
    return [item for item in items if isinstance(item, str)] if isinstance(items, list) else []


def _objects(value: Any, key: str) -> list[dict[str, Any]]:
    items = value.get(key) if isinstance(value, dict) else None
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []
