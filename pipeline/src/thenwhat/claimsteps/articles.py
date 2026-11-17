"""What a claim's articles give it: what each unread article says, read into a claim still
awaiting review, and the registry records and papers its articles' pages name. Behavior:
openspec claim-extraction and lead-reading, "Records a page names are looked up apart
from the join"."""

from datetime import timedelta
from typing import Any

from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session

from thenwhat.backfill.link_reasons import SITE_BUSY, reason_for_status
from thenwhat.backfill.outlet_hold import OutletHeld, retrieve_unless_held
from thenwhat.claimsteps.inputs import Inputs, names_a_record
from thenwhat.claimsteps.reasons import (
    ARTICLE_UNREADABLE,
    OUTLET_HELD,
    PAPERS_OFF,
    SOURCE_FAILED,
    SOURCE_RETRY,
    SourceNotSetUp,
    attempt,
    model_failed,
    put_off,
)
from thenwhat.claimsteps.step import Answer, ClaimSources, ClaimStep
from thenwhat.db.models import Claim, SourceArticle
from thenwhat.decide.core import DecisionFailed
from thenwhat.domain import ReviewState, WorkOutcome
from thenwhat.extract.retrieve import NotNow, NotServed, PasteNeeded
from thenwhat.llm.errors import LlmError
from thenwhat.resolve.named import candidates_named_in_article
from thenwhat.sources.base import SourceError
from thenwhat.work.outcome import Later, NeedsFix
from thenwhat.work.steps import Failed

# What becomes of a claim's articles when not all could be read, the first that applies:
# one that failed is tried again soonest, one put off comes back by itself, and one the
# reader could not read waits for its text.
Unread = Failed | Later | NeedsFix


class ClaimArticles(ClaimStep):
    """Read each unread article of a claim still awaiting review into the claim: its
    entities, the paper, promises and reported statements. An outlet the page reader has
    said cannot be asked yet is not asked: the article is left for later, and the others
    are read. The article's text is used for the read only and never stored."""

    name = "claim_articles"
    version = 2
    reasons = (OUTLET_HELD, ARTICLE_UNREADABLE, SITE_BUSY, SOURCE_FAILED)

    def __init__(self, *, site_retry_wait: timedelta, **step: Any) -> None:
        super().__init__(**step)
        self.site_retry_wait = site_retry_wait

    def condition(self) -> ColumnElement[bool]:
        # A decided claim is never redrafted.
        return Claim.review_state == ReviewState.PENDING

    def read(self, inputs: Inputs, claim_id: int) -> dict[str, Any]:
        return {"unread": inputs.unread.get(claim_id, [])}

    def work(self, session: Session, claim: Claim, sources: ClaimSources) -> Answer:
        # Imported here: the model libraries are slow to load and most commands never
        # need them.
        from thenwhat.extract.service import extract_into_claim

        now = self.now()
        unread = list(
            session.scalars(
                select(SourceArticle)
                .where(SourceArticle.claim_id == claim.id, SourceArticle.content_hash.is_(None))
                .order_by(SourceArticle.published_date, SourceArticle.id)
            )
        )
        if not unread:
            return WorkOutcome.DONE
        if sources.retriever is None or sources.open_session is None:
            raise SourceNotSetUp(
                "The page reader is not configured (FIRECRAWL_API_URL and FIRECRAWL_API_KEY),"
                " so no article can be read."
            )
        retriever, open_session = sources.retriever, sources.open_session
        left: list[Unread] = []
        for article in unread:
            try:
                retrieved = retrieve_unless_held(open_session, retriever, article.url, now)
            except OutletHeld as held:
                left.append(Later(OUTLET_HELD, held.until, {"outlet": article.outlet}))
                continue
            except NotNow as busy:
                wait = timedelta(seconds=busy.retry_after_seconds or SOURCE_RETRY.total_seconds())
                left.append(Later(OUTLET_HELD, now + wait, {"outlet": article.outlet}))
                continue
            except PasteNeeded as needed:
                if isinstance(needed, NotServed) and reason_for_status(needed.status) == SITE_BUSY:
                    left.append(
                        Later(SITE_BUSY, now + self.site_retry_wait, {"status": needed.status})
                    )
                else:
                    left.append(NeedsFix(ARTICLE_UNREADABLE, {"said": str(needed)}))
                continue
            read = attempt(
                session,
                lambda article=article, retrieved=retrieved: extract_into_claim(
                    session,
                    sources.make_llm(session),
                    sources.make_checker(session),
                    claim_slug=claim.slug,
                    article_url=article.url,
                    text=retrieved.text,
                    archive_url=retrieved.archive_url,
                    now=now,
                ),
            )
            if isinstance(read, SourceError):
                left.append(put_off(read, now))
            elif isinstance(read, DecisionFailed | LlmError):
                left.append(model_failed(read))
        return _first_left(left)


def _first_left(left: list[Unread]) -> Any:
    for kind in (Failed, Later, NeedsFix):
        for answer in left:
            if isinstance(answer, kind):
                return answer
    return WorkOutcome.DONE


class ClaimNamedRecords(ClaimStep):
    """Record the trials and papers the claim's articles' pages name, and those matched
    exactly to its articles, as candidates of the claim, read by their identifiers and
    decided by the resolver's own rules. Being named or matched approves nothing.
    A registry or literature error leaves the claim due again for this step."""

    name = "claim_named_records"
    reasons = (SOURCE_FAILED, PAPERS_OFF)

    def __init__(
        self, *, reject_below: float, accept_above: float, papers_enabled: bool, **step: Any
    ) -> None:
        super().__init__(**step)
        self.reject_below = reject_below
        self.accept_above = accept_above
        self.papers_enabled = papers_enabled

    def condition(self) -> ColumnElement[bool]:
        return names_a_record()

    def read(self, inputs: Inputs, claim_id: int) -> dict[str, Any]:
        read: dict[str, Any] = {
            "named": inputs.named.get(claim_id, []),
            "papers_enabled": self.papers_enabled,
        }
        # Only a claim with matches reads them, so the input of one without is as before.
        matched = inputs.matched.get(claim_id)
        if matched:
            read["matched"] = matched
        return read

    def work(self, session: Session, claim: Claim, sources: ClaimSources) -> Answer:
        now = self.now()
        numbers: list[str] = []
        dois: list[str] = []
        matched_numbers: list[str] = []
        matched_dois: list[str] = []
        matched_pmids: list[str] = []
        for article in session.scalars(
            select(SourceArticle)
            .where(SourceArticle.claim_id == claim.id)
            .order_by(SourceArticle.published_date, SourceArticle.id)
        ):
            numbers += article.named_registry_numbers
            dois += article.named_dois
            matched_numbers += article.matched_registry_numbers
            matched_dois += article.matched_dois
            matched_pmids += article.matched_pubmed_ids
        research = sources.make_research(session)
        backend = sources.make_backend(session)
        unasked: list[str] = []
        unasked_pmids: list[str] = []
        added = attempt(
            session,
            lambda: candidates_named_in_article(
                session,
                claim,
                registry_numbers=numbers,
                dois=dois,
                verified_registry_numbers=matched_numbers,
                verified_dois=matched_dois,
                verified_pmids=matched_pmids,
                unasked_dois=unasked,
                unasked_pmids=unasked_pmids,
                registry=research.registry,
                papers=research.papers,
                backend=backend,
                now=now,
                reject_below=self.reject_below,
                accept_trial_above=self.accept_above,
                accept_paper_above=self.accept_above,
            ),
        )
        if isinstance(added, SourceError):
            return put_off(added, now)
        if isinstance(added, DecisionFailed | LlmError):
            return model_failed(added)
        self.results[claim.id] = added
        if unasked or unasked_pmids:
            values = {"dois": unasked}
            if unasked_pmids:
                values["pmids"] = unasked_pmids
            return NeedsFix(PAPERS_OFF, values)
        return WorkOutcome.DONE
