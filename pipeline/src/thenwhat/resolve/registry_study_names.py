"""Find registered study names in a reporter's evidence, including trial roundups."""

import json
import re
import sqlite3
from dataclasses import dataclass

from thenwhat.backfill.trial_terms import condition_words, words_of

_WORD = re.compile(r"[a-zA-Z0-9]+")
_NAME_SEPARATOR = re.compile(r"[ \t‐‑–-]+")
_SHORT_PRODUCT = re.compile(r"[A-Z][A-Z0-9]{2,3}")
_PROTOCOL_CUE = re.compile(
    r"\b(?:trial|trials|study|studies|phase|cohort|protocol|pooled|results|findings|data)\b",
    re.IGNORECASE,
)
_NUMBERED_SERIES = re.compile(
    r"\b([A-Za-z][A-Za-z0-9]{3,})[- ]+(1)\s*(?:and|&|/)\s*([2-9])\b", re.IGNORECASE
)
_LIMIT = 16
_CONTEXT_CHARS = 240


@dataclass(frozen=True, slots=True)
class NamedTrial:
    identifier: str
    name: str


def _marked(word: str) -> bool:
    return sum(character.isupper() for character in word) >= 2 or (
        word[0].isupper() and any(character.isdigit() for character in word)
    )


def _name_keys(article: str) -> dict[str, list[str]]:
    """Propose complete labels near a study cue, using the registry to attest them."""
    tokens = list(_WORD.finditer(article))
    mentions: dict[str, list[str]] = {}
    for index, token in enumerate(tokens):
        if len(token[0]) < 2 or token[0].isdecimal():
            continue
        start = token.start()
        if not _PROTOCOL_CUE.search(article[max(0, start - 72) : token.end() + 84]):
            continue
        for width in range(1, min(5, len(tokens) - index + 1)):
            part = tokens[index : index + width]
            if width > 1 and not _NAME_SEPARATOR.fullmatch(
                article[part[-2].end() : part[-1].start()]
            ):
                break
            length = part[-1].end() - start
            if length > 52:
                break
            marked = any(_marked(piece[0]) for piece in part)
            title_case = sum(piece[0][0].isupper() for piece in part) >= 2
            if length < 4 or not (marked or title_case):
                continue
            following = article[part[-1].end() : part[-1].end() + 6]
            if re.match(r"[- ]+[2-9]\b", following):
                continue
            end = start + length
            key = " ".join(piece[0].lower() for piece in part)
            window = article[max(0, start - _CONTEXT_CHARS) : end + _CONTEXT_CHARS]
            mentions.setdefault(key, []).append(window)
    for matched in _NUMBERED_SERIES.finditer(article):
        family, first, second = matched.groups()
        if family.lower() not in mentions:
            continue
        window = article[max(0, matched.start() - _CONTEXT_CHARS) : matched.end() + _CONTEXT_CHARS]
        for ordinal in (first, second):
            mentions.setdefault(f"{family.lower()} {ordinal}", []).append(window)
    return mentions


def cited_study_names(store: sqlite3.Connection, article: str) -> list[NamedTrial]:
    """Retrieve bounded candidates whose registered label and nearby context agree."""
    mentions = _name_keys(article)
    if not mentions:
        return []
    matches = store.execute(
        """SELECT external_id, acronym, conditions, intervention_names
           FROM registry_trial
           WHERE acronym IS NOT NULL
             AND lower(trim(replace(replace(replace(replace(replace(replace(replace(
                 acronym, char(9), ' '), '-', ' '), '–', ' '), '‑', ' '), '‐', ' '),
                 '  ', ' '), '  ', ' ')))
                 IN (SELECT value FROM json_each(?))""",
        (json.dumps(list(mentions)),),
    )
    scored: list[tuple[tuple[int, int, str], NamedTrial]] = []
    for identifier, name, conditions, products in matches:
        label = words_of(name)
        indications = json.loads(conditions or "[]")
        condition = condition_words(indications)
        condition_abbreviations = {
            "".join(word[0] for word in terms).upper()
            for indication in indications
            if 2 <= len(terms := words_of(indication)) <= 6
        }
        product = set(words_of(products or "")) - {"placebo", "control", "other", "drug"}
        product = {word for word in product if len(word) >= 5} - condition
        short_products = {
            entry
            for raw in (products or "").split(";")
            if (entry := raw.strip()) != "PBO" and _SHORT_PRODUCT.fullmatch(entry)
        }
        score = 0
        for window in mentions.get(" ".join(label), ()):
            given = set(words_of(window)) - set(label)
            written = set(_WORD.findall(window)) - {word.upper() for word in label}
            treatment = len(product & given) + len(short_products & written)
            disease = len(condition & given) + len(condition_abbreviations & written)
            score = max(score, 2 * treatment + disease)
        if score:
            scored.append(((-score, -len(label), identifier), NamedTrial(identifier, name)))
    return [trial for _, trial in sorted(scored)[:_LIMIT]]
