"""Why a paper is a candidate, as codes found by rule. Pure: no database, network,
clock or model. Behavior: openspec related-research. The site owns the wording."""

from datetime import date

from thenwhat.sources.openalex import PaperRecord

NAMED_IN_TITLE = "named_in_title"
INDICATION_NAMED = "indication_named"
NAMED_INSTITUTION = "named_institution"
PUBLISHED_BEFORE_REPORT = "published_before_report"
# Every code, in the order they are given.
REASON_CODES = (NAMED_IN_TITLE, INDICATION_NAMED, NAMED_INSTITUTION, PUBLISHED_BEFORE_REPORT)


def _key(text: str) -> str:
    return " ".join(text.split()).casefold()


def paper_reasons(
    paper: PaperRecord,
    *,
    terms: list[str],
    indication: str,
    institutions: list[str],
    institution_ids: frozenset[str] = frozenset(),
    first_reported: date | None,
) -> list[str]:
    """The signs a reader can check for themselves, none of which a model found.

    `terms` are the intervention's name, other names and search phrases. `institutions`
    are the names the article gave, and `institution_ids` the ROR identifiers matched to
    them. A paper published on the day of the first report counts as before it: reports
    are written to a journal's release time.
    """
    title = _key(paper.title)
    text = f"{title} {_key(paper.abstract)}"
    named = {_key(name) for name in institutions if name.strip()}
    reasons: list[str] = []
    if any(_key(term) in title for term in terms if term.strip()):
        reasons.append(NAMED_IN_TITLE)
    if indication.strip() and _key(indication) in text:
        reasons.append(INDICATION_NAMED)
    if any(
        _key(name) in named or (identifier is not None and identifier in institution_ids)
        for author in paper.authors
        for name, identifier in author.institutions
    ):
        reasons.append(NAMED_INSTITUTION)
    if (
        first_reported is not None
        and paper.published_date is not None
        and paper.published_date <= first_reported
    ):
        reasons.append(PUBLISHED_BEFORE_REPORT)
    return reasons
