"""Find and verify research on the publisher body already held by a link read."""

import sqlite3
from collections.abc import Callable, Sequence
from contextlib import closing
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from pydantic import TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from thenwhat.decide.core import Backend
from thenwhat.extract.evidence_search import find_evidence
from thenwhat.extract.evidence_verification import TrialProductAlias, verify_evidence
from thenwhat.extract.retrieve import Retrieved
from thenwhat.llm.client import Llm
from thenwhat.sources.base import SourceError
from thenwhat.sources.pubmed import PubMed
from thenwhat.work.errors import BackfillError, CannotAsk


@dataclass(frozen=True, slots=True)
class ArticleMatches:
    """Identifiers established by the article-to-record verifier."""

    registry_numbers: tuple[str, ...]
    dois: tuple[str, ...]
    pubmed_ids: tuple[str, ...]


class ArticleEvidence:
    """The normal Luna and Decisions matcher, with its local trial and PubMed sources."""

    def __init__(
        self,
        store: Path,
        pubmed: PubMed | None,
        make_llm: Callable[[Session], Llm],
        make_backend: Callable[[Session], Backend],
        product_aliases: Sequence[TrialProductAlias] = (),
    ) -> None:
        self._uri = store.resolve().as_uri() + "?mode=ro"
        self._pubmed = pubmed
        self._make_llm = make_llm
        self._make_backend = make_backend
        self._aliases = product_aliases

    def check_ready(self) -> None:
        if self._pubmed is not None:
            self._pubmed.check_ready()
        try:
            with closing(sqlite3.connect(self._uri, uri=True)) as trials:
                trials.execute("SELECT 1 FROM registry_trial LIMIT 1")
        except sqlite3.Error as error:
            raise BackfillError(f"The local trial snapshot cannot be opened: {error}") from None

    def __call__(
        self,
        session: Session,
        article: Retrieved,
        headline: str,
        outlet: str,
        published: date,
    ) -> ArticleMatches:
        try:
            with closing(sqlite3.connect(self._uri, uri=True)) as trials:
                candidates = find_evidence(
                    self._make_llm(session),
                    article,
                    headline=headline,
                    outlet=outlet,
                    published=published,
                    trial_store=trials,
                    pubmed=self._pubmed,
                    require_papers=self._pubmed is not None,
                )
                verified = verify_evidence(
                    session,
                    self._make_backend(session),
                    article,
                    candidates,
                    trial_store=trials,
                    pubmed=self._pubmed,
                    headline=headline,
                    product_aliases=self._aliases,
                    require_papers=self._pubmed is not None,
                )
        except (SourceError, sqlite3.Error) as error:
            raise CannotAsk(f"Article evidence search could not finish: {error}") from None
        return ArticleMatches(
            tuple(
                sorted({v.identifier for v in verified.verdicts if v.kind == "nct" and v.accepted})
            ),
            tuple(sorted(set(verified.paper_dois.values()))),
            tuple(
                sorted({v.identifier for v in verified.verdicts if v.kind == "pmid" and v.accepted})
            ),
        )


def product_aliases_of(path: Path | None) -> list[TrialProductAlias]:
    if path is None:
        return []
    try:
        return TypeAdapter(list[TrialProductAlias]).validate_json(path.read_bytes())
    except (OSError, ValidationError) as error:
        raise BackfillError(f"Cannot load the cited sponsor aliases: {error}") from None
