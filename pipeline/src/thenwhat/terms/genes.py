"""The words of an intervention's names that could be a gene's symbol. Pure: no
database, network, clock or model. Behavior: openspec knowledge-cards, "A gene or
protein named in the intervention is a candidate target".

A word is only a candidate to look up. Whether a gene's symbol or synonym equals it is
the target source's answer, and whether the word means that gene is the target check's.
"""

import re
from collections.abc import Sequence

# The word of the intervention's name equals the gene's approved symbol.
WORD_EQUALS_SYMBOL = "word_equals_symbol"
# The word equals a synonym the source lists for the gene's symbol, not the symbol.
WORD_EQUALS_SYNONYM = "word_equals_synonym"
TARGET_REASON_CODES = (WORD_EQUALS_SYMBOL, WORD_EQUALS_SYNONYM)

_SPLIT = re.compile(r"[\s()\[\]{}]+")
_LEADING = re.compile(r"^anti-", re.IGNORECASE)
_TRAILING = re.compile(r"-(?:derived|mediated|targeting|based|to-.*)$", re.IGNORECASE)
# A letter followed by two to nine letters, digits or hyphens.
_SHAPE = re.compile(r"^[A-Za-z][A-Za-z0-9-]{2,9}$")


def gene_like_words(names: Sequence[str]) -> list[str]:
    """The words of the names that have the shape of a gene symbol, each once, in the
    order they appear.

    A name is split on spaces and brackets. A leading "anti-" and a trailing "-derived",
    "-mediated", "-targeting", "-based" or "-to-…" are removed. What is left is kept
    when it is a letter followed by two to nine letters, digits or hyphens with a
    capital or a digit among them, so that "Aspirin" and "peptide" are not words to
    look up and "CXCR3", "GLP-1" and "Mar1" are.
    """
    found: dict[str, str] = {}
    for name in names:
        for part in _SPLIT.split(name):
            word = _TRAILING.sub("", _LEADING.sub("", part.strip(",;:.")))
            if not _SHAPE.match(word):
                continue
            if not any(letter.isupper() or letter.isdigit() for letter in word[1:]):
                continue
            found.setdefault(word.casefold(), word)
    return list(found.values())
