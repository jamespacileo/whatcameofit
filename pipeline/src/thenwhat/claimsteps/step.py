"""What every claim step shares: which claims it is for, what it reads of a claim, and
the sources it asks through."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import ColumnElement, and_, or_, true
from sqlalchemy.orm import Session, object_session

from thenwhat.claimsteps.inputs import CLAIM, Inputs
from thenwhat.db.models import Claim
from thenwhat.decide.core import Backend
from thenwhat.domain import ReviewState, WorkOutcome
from thenwhat.events.fetch import LiteratureIndex, NoticeRegistry, TrialRegistry
from thenwhat.resolve.codes import Substances
from thenwhat.resolve.organisations import OrganisationRegistry
from thenwhat.resolve.papers import PaperSearch, RegistryNumbers
from thenwhat.resolve.papers import TrialRegistry as TrialsByNumber
from thenwhat.resolve.service import DoiLookup, TrialSearch
from thenwhat.terms.service import Drugs, Genes, Vocabulary
from thenwhat.work.outcome import Later, NeedsFix, NothingFound, Reason
from thenwhat.work.steps import Failed

if TYPE_CHECKING:
    from thenwhat.extract.retrieve import ArticleRetriever
    from thenwhat.llm.client import Llm
    from thenwhat.statements.service import StatementChecker

# What a claim step answers for a claim.
Answer = WorkOutcome | Failed | NothingFound | Later | NeedsFix

# What a claim step names as its source: the registries, literature indexes and models
# a claim's preparation asks, each at its own pace and under no allowance of the ledger.
CLAIM_SOURCES = "claim sources"


def prepared() -> ColumnElement[bool]:
    """The claims whose preparation runs: not merged into another, and awaiting review,
    or approved and not archived."""
    return and_(
        Claim.merged_into_id.is_(None),
        or_(
            Claim.review_state == ReviewState.PENDING,
            and_(Claim.review_state == ReviewState.APPROVED, Claim.archived_at.is_(None)),
        ),
    )


def named(ids: list[int]) -> ColumnElement[bool]:
    """Only these claims, whatever their review, unless merged into another."""
    return and_(Claim.id.in_(ids), Claim.merged_into_id.is_(None))


@dataclass(frozen=True, slots=True)
class Research:
    """The sources behind related papers and organisations."""

    # None while OPENALEX_API_KEY is empty: paper search is then off.
    papers: PaperSearch | None
    numbers: RegistryNumbers
    registry: TrialsByNumber
    organisations: OrganisationRegistry


def _not_given(what: str) -> Callable[[Session], Any]:
    def missing(session: Session) -> Any:
        raise LookupError(f"No {what} was given to the claim steps.")

    return missing


OpenSession = Callable[[], AbstractContextManager[Session]]


@dataclass(slots=True)
class ClaimSources:
    """What the claim steps ask through. Each source is made for the session at hand,
    because it caches its answers and takes its turns there. Requests are not counted
    here: a source paces itself."""

    make_backend: Callable[[Session], Backend] = field(
        default_factory=lambda: _not_given("backend")
    )
    make_substances: Callable[[Session], Substances] = field(
        default_factory=lambda: _not_given("registry of substances")
    )
    make_brands: Callable[[Session], Substances | None] = field(
        default_factory=lambda: _not_given("source of brands")
    )
    make_registries: Callable[[Session], tuple[TrialSearch, DoiLookup]] = field(
        default_factory=lambda: _not_given("trial registry")
    )
    make_research: Callable[[Session], Research] = field(
        default_factory=lambda: _not_given("literature source")
    )
    make_evidence: Callable[[Session], tuple[TrialRegistry, LiteratureIndex, NoticeRegistry]] = (
        field(default_factory=lambda: _not_given("source of evidence"))
    )
    make_llm: Callable[[Session], "Llm"] = field(default_factory=lambda: _not_given("model"))
    make_checker: Callable[[Session], "StatementChecker"] = field(
        default_factory=lambda: _not_given("statement checker")
    )
    make_vocabulary: Callable[[Session], Vocabulary] = field(
        default_factory=lambda: _not_given("vocabulary")
    )
    make_genes: Callable[[Session], Genes] = field(default_factory=lambda: _not_given("genes"))
    make_drugs: Callable[[Session], Drugs] = field(default_factory=lambda: _not_given("drugs"))
    # The page reader, or None when it is not configured; and the sessions an outlet's
    # hold is kept in, apart from the step's own.
    retriever: "ArticleRetriever | None" = None
    open_session: OpenSession | None = None
    requests_made: int = 0


def now_utc() -> datetime:
    return datetime.now(UTC)


class ClaimStep:
    """A step whose record is a claim. Each declares its name, what it reads and the
    reasons it may give; the claims it is for are given when it is made."""

    name: str
    version = 1
    record_kind = CLAIM
    model = Claim
    source = CLAIM_SOURCES
    # A claim's requests vary with its names and its matches; none is estimated.
    requests_per_record = 0
    reasons: tuple[Reason, ...] = ()
    # The steps that must have finished for a claim before this one is due for it.
    after: tuple["ClaimStep", ...] = ()

    def __init__(
        self,
        *,
        claims: ColumnElement[bool] | None = None,
        clock: Callable[[], datetime] = now_utc,
    ) -> None:
        self.claims = prepared() if claims is None else claims
        self.now = clock
        # What the step found for each claim it finished, for a command to say.
        self.results: dict[int, Any] = {}

    def scope(self) -> ColumnElement[bool]:
        return and_(self.claims, self.condition())

    def condition(self) -> ColumnElement[bool]:
        """What else a claim must be for this step."""
        return true()

    def inputs(self, record: Claim) -> dict[str, Any]:
        session = object_session(record)
        assert session is not None
        # The ledger asks while its entry for the claim is not yet complete: what the
        # step wrote is flushed already, and the entry is not to be.
        with session.no_autoflush:
            return self.read(Inputs(session, [record.id]), record.id)

    def read(self, inputs: Inputs, claim_id: int) -> dict[str, Any]:
        """What the step reads of the claim: it is due again when this changes."""
        return {}

    def run(self, session: Session, record: Claim, client: ClaimSources) -> Answer:
        return self.work(session, record, client)

    def work(self, session: Session, claim: Claim, sources: ClaimSources) -> Answer:
        """Do the step for one claim, in the runner's transaction for it."""
        raise NotImplementedError
