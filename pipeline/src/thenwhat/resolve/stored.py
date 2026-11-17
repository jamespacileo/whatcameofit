"""The stored registry trials as a second way to find a claim's trials, and as a source
of the names a registry files an intervention under. Behavior: openspec
entity-resolution (change live-lookup), "Stored trials that list the intervention are
candidates" and "A name the stored trials file under one other name is searched under
it".

The registry's own search finds a trial by the words of its intervention entries and by
the registry's dictionary of synonyms. It misses a trial filed under a development code
its dictionary does not tie to the name (zanzalintinib, filed as XL092), and a
combination whose parts are filed under other names. The stored trials are read here
with no network and no model: names are compared exactly, letter case, spacing and
trade marks aside.

What is found here is a candidate and nothing more. It is scored and decided like any
candidate the registry's search returns.
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import Text, cast, func, or_, select
from sqlalchemy.orm import Session

from thenwhat.backfill.trial_names import BRACKETS, JOINS, KINDS_OF_PRODUCT, NAMED_KINDS, name_alone
from thenwhat.claims.entry import name_key
from thenwhat.db.models import RegistryTrial
from thenwhat.sources.base import SourceRecord
from thenwhat.sources.clinicaltrials import BROAD_NAME, GENERIC_CONDITION_WORDS, ClinicalTrials

# A shorter name is a word or an abbreviation that many entries hold by chance.
MIN_NAME_LENGTH = 3
# A name looked for in titles and study identifiers is at least this long.
MIN_TITLE_NAME_LENGTH = 5
# The most stored trials read for one claim. A name in more entries than this is a
# class or a common substance; the registry's own search, which ranks, is left to it.
MAX_ROWS_READ = 20000
# How many stored trials must file a name under another before that other name is used
# to find candidates. One sponsor's entry can list anything among its other names.
MIN_TRIALS_FILING = 2

_MARKS = re.compile(r"[®™©]")
_BRACKETED = re.compile(r"\(([^)]*)\)|\[([^\]]*)\]")
_LISTED_APART = re.compile(r"\s*[;,]\s*")
# What joins the treatments of a combination in a claim's name, commas included:
# "Braftovi, cetuximab and standard chemotherapy".
_PARTS = re.compile(
    r"\s+(?:plus|with|and|in combination with|combined with)\s+|\s*[+/,]\s*", re.IGNORECASE
)
# Words around a part that say it is a combination, not what is in it.
_COMBINATION_WORDS = re.compile(
    r"^(?:combination of|the)\s+|\s+(?:combination\s+)?(?:regimen|therapy|treatment)$"
    r"|\s+combination$",
    re.IGNORECASE,
)
# A part that names a kind of care, not a product: no entry is required for it.
_CARE_WORDS = frozenset(["standard", "care", "of", "best", "supportive", "usual", "background"])


def keys_written(written: str) -> set[str]:
    """Every name one registry entry writes, in the compared form. An entry can pack
    several: "Braftovi, PF-07263896, LGX818", "Zidesamtinib (NVL-520)", "Tecentriq®".
    Each name between commas or semicolons and each bracketed name is one name; nothing
    is cut out of a name."""
    text = _MARKS.sub("", written)
    inside = [first or second for first, second in _BRACKETED.findall(text)]
    keys = {name_key(text)}
    for piece in (_BRACKETED.sub(" ", text), *inside):
        keys.update(name_key(part) for part in _LISTED_APART.split(piece))
    return {key for key in keys if len(key) >= MIN_NAME_LENGTH}


def claim_key(name: str) -> str:
    return name_key(_MARKS.sub("", name))


def parts_of(name: str) -> list[str]:
    """The treatments a combination's name joins, each as a name alone, or one name
    when it names one treatment."""
    parts = []
    for part in _PARTS.split(name):
        part = part.strip(" ;")
        while part and (cut := _COMBINATION_WORDS.sub("", part)) != part:
            part = cut.strip()
        if part:
            parts.append(part)
    return parts


def _is_a_kind_of_care(part: str) -> bool:
    words = claim_key(part).split()
    return all(word in KINDS_OF_PRODUCT or word in _CARE_WORDS for word in words)


@dataclass(frozen=True, slots=True)
class StoredTrial:
    """What is read of a stored trial to compare names."""

    external_id: str
    title: str
    conditions: list[str]
    interventions: list[dict[str, Any]]

    def lists(self, keys: Iterable[str]) -> bool:
        """True when an intervention entry names one of the keys, as its name or among
        its other names."""
        wanted = set(keys)
        return any(wanted & _entry_keys(entry) for entry in self.interventions)


def _entry_keys(entry: dict[str, Any]) -> set[str]:
    keys = keys_written(entry.get("name") or "")
    for other in entry.get("otherNames") or []:
        keys |= keys_written(other)
    return keys


@dataclass(frozen=True, slots=True)
class Stored:
    """What the stored trials give for one intervention."""

    # The trials found, as stored: fewer fields than the registry's search returns.
    records: list[SourceRecord] = field(default_factory=list)
    # Names the stored trials file the intervention's names under, each for one name:
    # {"zanzalintinib": "XL092"}.
    filed_under: dict[str, str] = field(default_factory=dict)

    @property
    def other_names(self) -> list[str]:
        return list(dict.fromkeys(self.filed_under.values()))


def _like(key: str) -> str:
    """A pattern for the loose first pass. A space stands for any run of characters, as
    an entry may write several where the compared form has one."""
    escaped = key.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped.replace(' ', '%')}%"


def _mentioning(session: Session, keys: Sequence[str]) -> list[StoredTrial]:
    """The stored trials whose intervention entries hold one of the keys anywhere in
    their text. A first, loose pass: the caller compares names exactly."""
    keys = [key for key in dict.fromkeys(keys) if len(key) >= MIN_NAME_LENGTH]
    if not keys:
        return []
    written = func.lower(cast(RegistryTrial.interventions, Text))
    rows = session.execute(
        select(
            RegistryTrial.external_id,
            RegistryTrial.title,
            RegistryTrial.conditions,
            RegistryTrial.interventions,
        )
        .where(
            RegistryTrial.registry_name == ClinicalTrials.name,
            or_(*(written.like(_like(key), escape="\\") for key in keys)),
        )
        .order_by(RegistryTrial.external_id)
        .limit(MAX_ROWS_READ)
    )
    return [StoredTrial(*row) for row in rows]


def _titled(session: Session, keys: Sequence[str]) -> list[StoredTrial]:
    """The stored trials that carry one of the keys as a whole word in their title,
    official title or acronym, or whose sponsor's study identifier starts with it:
    "BNT211-01"."""
    keys = [key for key in dict.fromkeys(keys) if len(key) >= MIN_TITLE_NAME_LENGTH]
    if not keys:
        return []
    names = "|".join(re.escape(key) for key in keys)
    whole_word = rf"(^|[^a-z0-9])({names})([^a-z0-9]|$)"
    identification = RegistryTrial.raw_payload["protocolSection"]["identificationModule"]
    rows = session.execute(
        select(
            RegistryTrial.external_id,
            RegistryTrial.title,
            RegistryTrial.conditions,
            RegistryTrial.interventions,
        )
        .where(
            RegistryTrial.registry_name == ClinicalTrials.name,
            or_(
                func.lower(RegistryTrial.title).op("~")(whole_word),
                func.lower(func.coalesce(RegistryTrial.acronym, "")).op("~")(whole_word),
                func.lower(func.coalesce(identification["officialTitle"].astext, "")).op("~")(
                    whole_word
                ),
                func.lower(func.coalesce(identification["orgStudyIdInfo"]["id"].astext, "")).op(
                    "~"
                )(rf"^({names})([^a-z0-9]|$)"),
            ),
        )
        .order_by(RegistryTrial.external_id)
        .limit(BROAD_NAME + 1)
    )
    return [StoredTrial(*row) for row in rows]


def filed_names(trials: Sequence[StoredTrial], key: str) -> dict[str, tuple[str, int]]:
    """Each name the stored trials file this name under, with how many trials do: an
    entry that lists the name among its other names is filed under the entry's own
    name, a dose, form or route aside. An entry that joins several products, or whose
    own name is a description, says nothing."""
    found: dict[str, tuple[str, set[str]]] = {}
    for trial in trials:
        for entry in trial.interventions:
            if entry.get("type") not in NAMED_KINDS:
                continue
            written = _MARKS.sub("", entry.get("name") or "")
            if key in keys_written(written):
                continue
            if not any(key in keys_written(other) for other in entry.get("otherNames") or []):
                continue
            if JOINS.search(BRACKETS.sub(" ", written)):
                continue
            alone = name_alone(written)
            if alone is not None:
                found.setdefault(name_key(alone), (alone, set()))[1].add(trial.external_id)
    return {filed: (name, len(ids)) for filed, (name, ids) in found.items()}


def filed_under(trials: Sequence[StoredTrial], key: str) -> str | None:
    """The one name the stored trials file this name under, or None.

    Sasanlimab is filed under PF-06801591 and zanzalintinib under XL092. The name is
    taken only when every entry that lists it agrees on one name, or on one name and
    its forms. A name sponsors file under two names gives none, as the registry of
    substances gives no code for a name it lists under two substances.
    """
    found = filed_names(trials, key)
    for base, (name, _) in found.items():
        if all(other == base or other.startswith((f"{base} ", f"{base}-")) for other in found):
            return name
    return None


def _telling(indication: str | None) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z0-9][a-z0-9'-]*", (indication or "").lower())
        if len(word) >= 3 and word not in GENERIC_CONDITION_WORDS
    }


def _within(trials: list[StoredTrial], indication: str | None) -> list[StoredTrial]:
    """At most BROAD_NAME trials: all of them, or those whose conditions or title share
    a telling word with the indication, or none when the name is broad even there."""
    if len(trials) <= BROAD_NAME:
        return trials
    telling = _telling(indication)
    narrowed = [
        trial for trial in trials if telling & _telling(" ".join([*trial.conditions, trial.title]))
    ]
    return narrowed if len(narrowed) <= BROAD_NAME else []


def stored_trials(
    session: Session,
    names: Sequence[str],
    indication: str | None,
    *,
    codes: Sequence[str] = (),
    substance: str | None = None,
) -> Stored:
    """The stored trials that list the intervention, and the names they file it under.

    A name of one treatment finds the trials with an entry that names it, as the
    entry's name or among its other names; so do a development code and the substance's
    name. A name the entries list nowhere is looked for in titles, acronyms and the
    sponsor's study identifier. A name that joins several treatments finds the trials
    with an entry for every part; a part that names a kind of care ("standard
    chemotherapy") needs no entry. A name is also found under each name that two or
    more stored trials file it under.

    More than BROAD_NAME trials are narrowed to the claim's indication, and given up
    when still as many: the registry's own search handles a broad name.
    """
    whole: list[str] = []
    combined: list[list[str]] = []
    for name in names:
        named = [part for part in parts_of(name) if not _is_a_kind_of_care(part)]
        if len(named) > 1:
            combined.append([claim_key(part) for part in named])
        elif named:
            whole.append(claim_key(named[0]))
    whole += [claim_key(term) for term in (*codes, substance) if term]
    whole = [key for key in dict.fromkeys(whole) if len(key) >= MIN_NAME_LENGTH]
    asked = list(dict.fromkeys([*whole, *(part for parts in combined for part in parts)]))
    mentioning = _mentioning(session, asked)

    # The one name a name is filed under is told to whoever scores and is searched for
    # at the registry. To find candidates here, every name two or more trials file it
    # under is used: a wrong one costs a candidate that is then scored, nothing more.
    filed: dict[str, str] = {}
    also: dict[str, list[str]] = {}
    for key in asked:
        listing = [trial for trial in mentioning if trial.lists([key])]
        names_filed = filed_names(listing, key)
        also[key] = [
            other for other, (_, trials) in names_filed.items() if trials >= MIN_TRIALS_FILING
        ]
        one = filed_under(listing, key)
        if one is not None:
            also[key].append(claim_key(one))
            if claim_key(one) not in asked:
                filed[key] = one
    others = [other for key in asked for other in also[key] if other not in asked]
    if others:
        known = {trial.external_id for trial in mentioning}
        mentioning += [
            trial for trial in _mentioning(session, others) if trial.external_id not in known
        ]

    def keys_of(key: str) -> list[str]:
        return [key, *also[key]]

    found: dict[str, StoredTrial] = {}
    for key in whole:
        listing = [trial for trial in mentioning if trial.lists(keys_of(key))]
        for trial in _within(listing, indication):
            found.setdefault(trial.external_id, trial)
    for parts in combined:
        listing = [
            trial for trial in mentioning if all(trial.lists(keys_of(part)) for part in parts)
        ]
        for trial in _within(listing, indication):
            found.setdefault(trial.external_id, trial)
    unlisted = [key for key in whole if not any(trial.lists([key]) for trial in mentioning)]
    for trial in _within(_titled(session, unlisted), indication):
        found.setdefault(trial.external_id, trial)

    wanted = sorted(found)
    payloads = session.execute(
        select(RegistryTrial.external_id, RegistryTrial.raw_payload, RegistryTrial.fetched_at)
        .where(
            RegistryTrial.registry_name == ClinicalTrials.name,
            RegistryTrial.external_id.in_(wanted),
        )
        .order_by(RegistryTrial.external_id)
    )
    records = [
        SourceRecord(
            source_name=ClinicalTrials.name,
            external_id=external_id,
            url=f"https://clinicaltrials.gov/study/{external_id}",
            payload=payload,
            fetched_at=fetched_at,
        )
        for external_id, payload, fetched_at in payloads
    ]
    return Stored(records, filed)
