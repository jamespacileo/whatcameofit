"""Whether two exports say the same. Behavior: openspec truth-store, "The two exports are
compared".

The cut-over rule is that the export taken from the truth store equals the one taken
from the pipeline's database, night after night. Two exports of the same records still
differ in three ways that say nothing of the records, and `canonical` removes exactly
those before the two are compared byte for byte:

- **The time the export was made.** Left out.
- **Row ids.** An event's `id` is its row's id in the store it was read from. Each
  claim's events are numbered again from 1 in an order made only of what they say, and
  what refers to an event (`status.explained_by`, a paper's `event_id`) follows.
- **Order among equals.** Where the export orders a list by a date or a score, two
  entries equal in that are in row-id order. Each such list is ordered again by the same
  date or score and then by what the entry says. An order that is the export's own
  (a trial's arms, a paper's roles, a status's history) is left as it is.

Nothing else is altered: a field that differs, a missing entry and an entry out of its
date or score order all still show.
"""

import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from thenwhat.backfill.address import article_key
from thenwhat.export.build import PAPER_ROLES
from thenwhat.export.organisations import ORGANISATION_ROLES

# How many places a report names for one claim before it says how many more there are.
PLACES_SHOWN = 12


def _said(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _claim(claim: dict[str, Any]) -> dict[str, Any]:
    claim = json.loads(json.dumps(claim))
    article_day = {article["url"]: article["published_date"] for article in claim["articles"]}

    def by_article(entry: dict[str, Any]) -> tuple[str, str]:
        return article_day.get(entry["article_url"], ""), _said(entry)

    events = sorted(
        claim["events"],
        key=lambda event: (event["event_date"], _said({**event, "id": None})),
    )
    number = {event["id"]: place for place, event in enumerate(events, start=1)}
    for event in events:
        event["id"] = number[event["id"]]
    claim["events"] = events
    claim["status"]["explained_by"] = sorted(
        number.get(event_id, event_id) for event_id in claim["status"]["explained_by"]
    )
    for paper in claim.get("papers", []):
        for role in paper["roles"]:
            if role.get("event_id") is not None:
                role["event_id"] = number.get(role["event_id"], role["event_id"])
    claim["articles"].sort(key=lambda article: (article["published_date"], _said(article)))
    claim["promises"].sort(key=by_article)
    claim.get("reported_statements", []).sort(key=by_article)
    claim["failure_flags"].sort(key=_said)
    claim.get("matches", []).sort(
        key=lambda match: (match["state"] != "approved", -match["score"], _said(match))
    )
    claim.get("papers", []).sort(
        key=lambda paper: (PAPER_ROLES.index(paper["roles"][0]["role"]), paper["identifier"])
    )
    for organisation in claim.get("organisations", []):
        for role in organisation["roles"]:
            role.get("article_urls", []).sort(key=lambda url: (article_day.get(url, ""), url))
    claim.get("organisations", []).sort(
        key=lambda organisation: (
            ORGANISATION_ROLES.index(organisation["roles"][0]["role"]),
            organisation["name"].casefold(),
            _said(organisation),
        )
    )
    return claim


def canonical(export: dict[str, Any]) -> dict[str, Any]:
    """The export with what says nothing of the records removed (see the module)."""
    return {
        **{key: value for key, value in export.items() if key != "generated_at"},
        "claims": sorted((_claim(claim) for claim in export["claims"]), key=lambda c: c["slug"]),
        "outlets": sorted(export.get("outlets", []), key=lambda outlet: outlet["domain"]),
        "archived": sorted(export.get("archived", []), key=lambda claim: claim["slug"]),
        "moved": sorted(export.get("moved", []), key=lambda claim: claim["slug"]),
    }


def canonical_bytes(export: dict[str, Any]) -> bytes:
    """The canonical export as the bytes two exports are compared by."""
    return (json.dumps(canonical(export), sort_keys=True, ensure_ascii=False) + "\n").encode()


def _places(ours: Any, theirs: Any, at: str) -> list[str]:
    """Where two values differ, each place once, as a path into the export."""
    if ours == theirs:
        return []
    if isinstance(ours, dict) and isinstance(theirs, dict):
        found: list[str] = []
        for key in sorted({*ours, *theirs}):
            if key not in ours or key not in theirs:
                found.append(f"{at}.{key}: only in {'the first' if key in ours else 'the second'}")
            else:
                found += _places(ours[key], theirs[key], f"{at}.{key}")
        return found
    if isinstance(ours, list) and isinstance(theirs, list):
        if len(ours) != len(theirs):
            return [f"{at}: {len(ours)} entries in the first, {len(theirs)} in the second"]
        found = []
        for place, (one, other) in enumerate(zip(ours, theirs, strict=True)):
            found += _places(one, other, f"{at}[{place}]")
        return found
    return [f"{at}: {_short(ours)} in the first, {_short(theirs)} in the second"]


def _short(value: Any) -> str:
    said = _said(value)
    return said if len(said) <= 80 else said[:77] + "..."


@dataclass(frozen=True)
class Difference:
    """One part of the export that differs: a claim, or a part outside the claims."""

    # A claim's slug, or the export's own key such as `archived`.
    part: str
    # Whether `part` is a claim.
    claim: bool
    places: list[str]
    # Why it differs, when the comparison can say: what is at fault and how. None when
    # it cannot, which is the case that needs a person.
    cause: str | None = None


@dataclass(frozen=True)
class Comparison:
    claims_first: int
    claims_second: int
    differences: list[Difference]

    @property
    def same(self) -> bool:
        return not self.differences

    @property
    def unexplained(self) -> list[Difference]:
        """The differences no cause is named for."""
        return [difference for difference in self.differences if difference.cause is None]

    def lines(self) -> list[str]:
        """The comparison in words: one line when the two are the same, else each part
        that differs with the places it differs at."""
        if self.same:
            return [f"The two exports are the same: {self.claims_first} claims, byte for byte."]
        claims = sum(1 for difference in self.differences if difference.claim)
        lines = [
            f"The two exports differ: {claims} of {self.claims_first} claims"
            f" ({self.claims_second} in the second),"
            f" and {len(self.differences) - claims} other parts."
            f" {len(self.differences) - len(self.unexplained)} have a named cause,"
            f" {len(self.unexplained)} do not."
        ]
        for difference in self.differences:
            lines.append(f"{difference.part}:")
            if difference.cause is not None:
                lines.append(f"  cause: {difference.cause}")
            lines += [f"  {place}" for place in difference.places[:PLACES_SHOWN]]
            if len(difference.places) > PLACES_SHOWN:
                lines.append(f"  and {len(difference.places) - PLACES_SHOWN} more places")
        return lines


SYNONYM_ORDER = (
    "the store's merge (store/merge.sql): the intervention holds the same names in"
    " another order. A merge rewrites the names of the claim that stays as a set."
)


def _only_synonym_order(ours: dict[str, Any], theirs: dict[str, Any]) -> bool:
    """Whether two entries of one claim differ in nothing but the order of the
    intervention's other names."""
    one, other = ours.get("intervention"), theirs.get("intervention")
    if not isinstance(one, dict) or not isinstance(other, dict):
        return False
    if "synonyms" not in one or "synonyms" not in other:
        return False
    if sorted(one["synonyms"]) != sorted(other["synonyms"]):
        return False
    return {**ours, "intervention": {**one, "synonyms": []}} == {
        **theirs,
        "intervention": {**other, "synonyms": []},
    }


def _fold_articles(
    ours: dict[str, Any], theirs: dict[str, Any], duplicates: dict[str, str]
) -> dict[str, Any] | None:
    """Apply just the known article merges to the first export, retaining all other data."""
    source = {article["url"] for article in ours["articles"]}
    stored = {article["url"] for article in theirs["articles"]}
    for removed, kept in duplicates.items():
        if (
            removed not in source
            or kept not in source
            or removed in stored
            or kept not in stored
            or not article_key(kept)
            or article_key(removed) != article_key(kept)
        ):
            return None
    folded = deepcopy(ours)
    folded["articles"] = [
        article for article in folded["articles"] if article["url"] not in duplicates
    ]
    for field in ("promises", "reported_statements"):
        if field not in folded:
            continue
        children = []
        origins: dict[str, set[str]] = {}
        for row in folded[field]:
            url = row["article_url"]
            row["article_url"] = duplicates.get(url, url)
            if row["article_url"] in duplicates.values():
                # Equal children from different articles become one store record. If
                # rows of the same article already collide, the cause is ambiguous.
                urls = origins.setdefault(_said(row), set())
                if url in urls:
                    return None
                urls.add(url)
                if len(urls) > 1:
                    continue
            children.append(row)
        folded[field] = children
    for organisation in folded.get("organisations", []):
        for role in organisation["roles"]:
            if "article_urls" in role:
                if len(set(role["article_urls"])) != len(role["article_urls"]):
                    return None
                role["article_urls"] = list(
                    dict.fromkeys(duplicates.get(url, url) for url in role["article_urls"])
                )
    return _claim(folded)


def _cause(
    one: dict[str, Any],
    other: dict[str, Any],
    aliases: dict[str, str] | str | None,
    places: list[str],
) -> str | None:
    if _only_synonym_order(one, other):
        return SYNONYM_ORDER
    if not isinstance(aliases, dict) or not aliases:
        return None
    folded = _fold_articles(one, other, aliases)
    if folded is None:
        return None
    kept = ", ".join(sorted(set(aliases.values())))
    cause = (
        "the database holds two source articles of this claim at one"
        f" address key. The store keeps the first ({kept})."
    )
    if folded == other:
        return cause
    if _only_synonym_order(folded, other):
        return f"{cause} {SYNONYM_ORDER}"
    # A length difference hides a change to a retained row in the original report.
    # Show what still differs after folding.
    places.extend(p for p in _places(folded, other, "claim") if p not in places)
    return None


def compare(
    first: dict[str, Any],
    second: dict[str, Any],
    *,
    known: Mapping[str, dict[str, str] | str] | None = None,
) -> Comparison:
    """Compare two exports, each as parsed JSON. They are the same exactly when their
    canonical bytes are.

    `known` gives, by slug, each duplicate article URL and the URL the store keeps.
    A legacy text explanation alone is insufficient to attribute a difference."""
    known = known or {}
    ours, theirs = canonical(first), canonical(second)
    differences: list[Difference] = []
    for key in sorted({*ours, *theirs} - {"claims"}):
        places = _places(ours.get(key), theirs.get(key), key)
        if places:
            differences.append(Difference(key, False, places))
    our_claims = {claim["slug"]: claim for claim in ours["claims"]}
    their_claims = {claim["slug"]: claim for claim in theirs["claims"]}
    for slug in sorted({*our_claims, *their_claims}):
        if slug not in our_claims or slug not in their_claims:
            where = "the first" if slug in our_claims else "the second"
            differences.append(Difference(slug, True, [f"only in {where}"]))
            continue
        one, other = our_claims[slug], their_claims[slug]
        places = _places(one, other, "claim")
        if places:
            cause = _cause(one, other, known.get(slug), places)
            differences.append(Difference(slug, True, places, cause))
    assert bool(differences) == (canonical_bytes(first) != canonical_bytes(second))
    return Comparison(len(our_claims), len(their_claims), differences)
