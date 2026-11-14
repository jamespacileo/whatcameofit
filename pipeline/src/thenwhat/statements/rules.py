"""The rules that refuse a proposed reported statement before it is stored.

Behavior: openspec reported-statements ("Statements are in the site's own words").
Pure: no database, network or clock. The article's text is compared here and kept
nowhere.
"""

import re
from collections.abc import Iterable
from enum import StrEnum

MAX_STATEMENT_CHARACTERS = 200
# Marks that open or close a quotation. A closing single quote is left out: it is also
# the apostrophe ("patients’ pain"). A single quote opening a word is caught below.
QUOTATION_MARKS = frozenset('"“”„‟«»‹›‘')
_OPENING_SINGLE_QUOTE = re.compile(r"(?:^|\s)['’]\w")
_WORD = re.compile(r"\w+")
# Words that come before a name and are not part of it.
_TITLES = frozenset({"dr", "doctor", "prof", "professor", "mr", "mrs", "ms", "miss", "sir", "dame"})


class Refusal(StrEnum):
    """Why a proposed statement is not stored."""

    TOO_LONG = "too_long"
    QUOTATION = "quotation"
    NAMES_A_PERSON = "names_a_person"
    COPIES_THE_ARTICLE = "copies_the_article"


def words(text: str) -> list[str]:
    """The text's words in lower case, punctuation left out."""
    return _WORD.findall(text.casefold())


def statement_key(text: str) -> str:
    """The form statements of one article are compared in: letter case, spacing and
    punctuation do not matter."""
    return " ".join(words(text))


def refusal(
    statement: str,
    *,
    article: str,
    people: Iterable[str],
    copied_run: int,
) -> Refusal | None:
    """Why the statement is refused, or None when it may be stored.

    Refused: over 200 characters, carrying a quotation mark, containing the name of one
    of the given people, or sharing `copied_run` or more consecutive words with the
    article.
    """
    if len(statement) > MAX_STATEMENT_CHARACTERS:
        return Refusal.TOO_LONG
    if QUOTATION_MARKS & set(statement) or _OPENING_SINGLE_QUOTE.search(statement):
        return Refusal.QUOTATION
    if any(names(statement, person) for person in people):
        return Refusal.NAMES_A_PERSON
    if copies(statement, article, copied_run):
        return Refusal.COPIES_THE_ARTICLE
    return None


def names(statement: str, person: str) -> bool:
    """Whether the statement contains the person's name or any part of it, such as their
    family name alone, written as a name: as a whole word with a capital letter."""
    parts = [part for part in re.findall(r"[^\W\d_]+", person) if part.casefold() not in _TITLES]
    return any(
        re.search(rf"(?<!\w){re.escape(part)}(?!\w)", statement)
        for part in parts
        if len(part) > 1 and part[0].isupper()
    )


def copies(statement: str, article: str, run: int) -> bool:
    """Whether the statement shares `run` or more consecutive words with the article,
    compared on lower-cased words."""
    said = words(statement)
    if run < 1 or len(said) < run:
        return False
    source = words(article)
    runs = {tuple(source[start : start + run]) for start in range(len(source) - run + 1)}
    return any(tuple(said[start : start + run]) in runs for start in range(len(said) - run + 1))
