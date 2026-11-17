"""A fake trial registry written as lists of records: what a test's fake returns for a
term is what the registry is said to report and to have taken."""

from thenwhat.sources.base import SourceRecord
from thenwhat.sources.clinicaltrials import NotSent, Searched

REGISTRY = "clinicaltrials.gov"


class ListedSearch:
    """Gives a fake's `search_trials` and `search_phrase` lists the shape the resolver
    asks for. A phrase with no condition is not sent, as the registry's client does."""

    def search_trials(self, intervention: str, condition: str | None = None) -> list[SourceRecord]:
        return []

    def search_phrase(self, phrase: str, condition: str | None) -> list[SourceRecord]:
        return []

    def name_search(self, intervention: str, condition: str | None = None) -> Searched:
        found = self.search_trials(intervention, condition)
        return Searched(REGISTRY, intervention, found, reported=len(found))

    def phrase_search(self, phrase: str, condition: str | None) -> Searched | NotSent:
        if not condition:
            return NotSent(REGISTRY, phrase, "no condition")
        found = self.search_phrase(phrase, condition)
        return Searched(REGISTRY, phrase, found, reported=len(found), condition=condition)
