"""The reading step: a passed link lead's article is read once and becomes a source
article of the claim it reports, or a new claim. Behavior: openspec lead-reading.

Everything that can be settled without the model is settled first: an article that has
become tracked, a claim that has enough articles, an outlet with no name, a page the
page reader does not give, a page with no date or headline. The article's text is held
only while the model reads it. What the read makes is an ordinary source article or an
ordinary claim.

Several outlets report one story, each in its own words, so an article is joined to a
claim that exists whenever a decision says it reports that claim; only otherwise is a new
claim drafted. Reads that run side by side take turns at that point, so two articles on
one story cannot both draft a claim. A new claim with a name is not approved here: it
awaits `thenwhat prepare`, which searches the registries and then decides it by the rule
for drafts, so that no claim is published with a status no search stands behind.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, and_, exists, func, or_, select
from sqlalchemy.orm import Session

from thenwhat.backfill.address import article_key, without_tracking
from thenwhat.backfill.allowance import Allowances
from thenwhat.backfill.errors import BackfillError, SpendCeilingReached
from thenwhat.backfill.link_evaluation import reading_refusal
from thenwhat.backfill.link_screen import CLAIM, REGISTRY_TRIAL, TITLE_NAMES_CLAIM
from thenwhat.backfill.link_triage import is_passed
from thenwhat.backfill.outlet_kinds import name_of
from thenwhat.backfill.steps import TEXT_DOOR, Deferred, Failed, ModelSpend
from thenwhat.backfill.topics import names_one, other_names_of, title_names
from thenwhat.claims.entry import (
    MAX_NAMED_CLAIMS,
    EntryError,
    claim_by_slug,
    claims_sharing_a_name,
    find_article,
    free_slug_for,
    named_claims,
    slug_of_claim_covering,
)
from thenwhat.db.models import Claim, LinkLead, LinkLeadLink, LinkShare, SourceArticle
from thenwhat.decide.core import Backend, DecisionFailed
from thenwhat.decide.steps import (
    ESTABLISHED_TREATMENT,
    choose_same_claim,
    choose_vertical,
    kind_of_treatment_report,
    lead_ref,
)
from thenwhat.domain import Decider, ReadOutcome, ReviewState, ScreenOutcome, WorkOutcome
from thenwhat.extract.names import is_a_class, is_a_name
from thenwhat.extract.page import Page, published_day
from thenwhat.extract.retrieve import (
    READER,
    ArticleRetriever,
    NotAllowed,
    NotNow,
    NotServed,
    ThinPage,
)
from thenwhat.extract.schema import Draft
from thenwhat.extract.service import article_from_draft, claim_from_draft, read_article
from thenwhat.llm.client import Llm
from thenwhat.llm.errors import BudgetExceeded, LlmError
from thenwhat.resolve.named import candidates_named_in_article
from thenwhat.review.decisions import record_decision
from thenwhat.sources.base import SourceError, SystemTime, Time
from thenwhat.statements.service import StatementChecker

NO_NAME = "its outlet has no display name"
NO_DATE = "the page gives no publication date"
NO_HEADLINE = "the page gives no headline"
NOT_ALLOWED = "the page reader does not allow the address"
NO_PAGE = "the page could not be retrieved"
# The name a lead's read is recorded under in the usage ledger, apart from articles an
# operator has read, so the funnel can say what reading leads has cost.
LEAD_READING = "extraction:link_lead"
# Held, until its transaction ends, by the one read that is settling which claim its
# article belongs to. A claim another read has just drafted is then there to be found.
CLAIM_IDENTITY_LOCK = 7_468_656_001
# An article joins a candidate claim only when the same-claim decision gives that claim
# more than every other answer together.
SAME_CLAIM_MAJORITY = 0.5


class NotMeasured(BackfillError):
    """No lead may be read yet: triage has not been measured, or a threshold is unset."""


@dataclass(slots=True)
class ReadClient:
    """What the reading step asks through: the page reader for the page, and the model for
    the read. The model's doors are made for the session at hand, because they record
    each call and its cost there."""

    retriever: ArticleRetriever
    allowances: Allowances
    make_llm: Callable[[Session], Llm]
    make_checker: Callable[[Session], StatementChecker]
    make_backend: Callable[[Session], Backend]
    # The registry and the literature source, read by identifier for the trials and
    # papers a page names. None leaves what a page names unrecorded.
    make_research: Callable[[Session], Any] | None = None
    requests_made: int = 0


class LinkRead:
    name = "link_read"
    version = 1
    record_kind = "link_lead"
    model = LinkLead
    # Every page is asked of the page reader, under its one allowance.
    source = READER
    requests_per_record = 1
    # An estimate for the plan: an article's text and the instructions in, a draft out.
    model_spend = ModelSpend(input_tokens=3000, output_tokens=700, door=TEXT_DOOR)
    # Reading publishes, so a run always says how many leads it may read.
    needs_limit = True

    def __init__(
        self,
        *,
        pass_above: float | None,
        reject_below: float | None,
        triage_version: int,
        min_labels: int,
        reads_per_claim: int,
        vertical_accept_above: float,
        approve_drafts_by_rule: bool,
        same_claim_accept_above: float = 0.6,
        treatment_accept_above: float = 0.5,
        topic_terms: Sequence[str] = (),
        match_reject_below: float = 0.0,
        match_accept_above: float = 0.0,
        time: Time | None = None,
    ) -> None:
        self.pass_above = pass_above
        self.reject_below = reject_below
        self.triage_version = triage_version
        self.min_labels = min_labels
        self.reads_per_claim = reads_per_claim
        self.vertical_accept_above = vertical_accept_above
        self.same_claim_accept_above = same_claim_accept_above
        self.treatment_accept_above = treatment_accept_above
        # The words of the operator's topics. A lead whose title names one is read first,
        # and is read when triage held it as well as when triage passed it.
        self._names_a_topic = title_names(topic_terms)
        self._topic_terms = tuple(topic_terms)
        self.approve_drafts_by_rule = approve_drafts_by_rule
        # The rules `thenwhat resolve` decides candidates by, for those a page names.
        self.match_reject_below = match_reject_below
        self.match_accept_above = match_accept_above
        self._time = time or SystemTime()

    # --- which leads, and in what order ---------------------------------------------

    def scope(self) -> ColumnElement[bool]:
        """Leads that screening left in scope and triage passed at the two thresholds,
        and leads whose title names one of the operator's topics that triage held: the
        topic is to be covered in full, and the check after the read says what each
        article turned out to be. A lead triage rejected is never read. While either
        threshold is unset, none."""
        readable = is_passed(self.pass_above, self.reject_below)
        if (
            self._names_a_topic is not None
            and self.pass_above is not None
            and self.reject_below is not None
        ):
            held_on_a_topic = and_(
                self._names_a_topic,
                LinkLead.triage_score.is_not(None),
                LinkLead.triage_score >= self.reject_below,
            )
            readable = or_(readable, held_on_a_topic)
        return and_(LinkLead.screen_outcome == ScreenOutcome.IN_SCOPE, readable)

    def inputs(self, record: LinkLead) -> dict[str, Any]:
        return {"key": record.url_key}

    def order(self) -> list[ColumnElement[Any]]:
        """First the leads whose title names one of the operator's topics, then those
        linked to a registry trial, then the most shared."""
        linked = exists().where(
            LinkLeadLink.link_lead_id == LinkLead.id,
            LinkLeadLink.record_kind == REGISTRY_TRIAL,
        )
        shared = (
            select(func.coalesce(func.sum(LinkShare.score), 0))
            .where(LinkShare.link_lead_id == LinkLead.id)
            .scalar_subquery()
        )
        topical = [] if self._names_a_topic is None else [self._names_a_topic.desc()]
        return [*topical, linked.desc(), shared.desc()]

    def check_ready(self, session: Session) -> None:
        """Refuse to read anything until triage has been measured (openspec
        lead-evaluation): enough leads carry a person's label at the current version of
        triage, and both thresholds are set."""
        refusal = reading_refusal(
            session,
            version=self.triage_version,
            min_labels=self.min_labels,
            pass_above=self.pass_above,
            reject_below=self.reject_below,
        )
        if refusal is not None:
            raise NotMeasured(refusal)

    # --- one lead ---------------------------------------------------------------------

    def _finish(
        self, record: LinkLead, outcome: ReadOutcome, detail: str | None = None
    ) -> WorkOutcome:
        record.read_outcome = outcome
        record.read_detail = detail
        made = outcome in (ReadOutcome.ADDED_TO_CLAIM, ReadOutcome.NEW_CLAIM)
        return WorkOutcome.DONE if made else WorkOutcome.NOTHING_FOUND

    def _tracked_claim(self, session: Session, record: LinkLead) -> int | None:
        """The claim that has this address as a source article, looked for again now:
        screening's answer may be old."""
        for claim_id, url in session.execute(select(SourceArticle.claim_id, SourceArticle.url)):
            if article_key(url) == record.url_key:
                return claim_id
        return None

    def _has_enough(self, session: Session, record: LinkLead) -> str | None:
        """Why the lead is held, when every claim its title names already has enough
        articles and the lead was shared no earlier than the claim was first reported."""
        claim_ids = list(
            session.scalars(
                select(LinkLeadLink.record_id).where(
                    LinkLeadLink.link_lead_id == record.id,
                    LinkLeadLink.record_kind == CLAIM,
                    LinkLeadLink.reason == TITLE_NAMES_CLAIM,
                )
            )
        )
        if not claim_ids:
            return None
        shared = record.first_shared_at.date()
        held: list[str] = []
        for claim_id in claim_ids:
            claim = session.get(Claim, claim_id)
            if claim is None:
                return None
            articles = session.scalar(
                select(func.count())
                .select_from(SourceArticle)
                .where(SourceArticle.claim_id == claim_id)
            )
            earlier = claim.first_reported_date is None or shared < claim.first_reported_date
            if (articles or 0) < self.reads_per_claim or earlier:
                return None
            held.append(claim.slug)
        return f"the claim it names has enough articles: {', '.join(held)}"

    def _named_on_the_page(
        self, session: Session, claim: Claim, page: Page | None, client: ReadClient, now: datetime
    ) -> str | None:
        """Record the trials and papers the article's page names as candidates of the
        claim, read by their identifiers and decided by the resolver's own rules. Being
        named approves nothing. Returns why they were not recorded, when they were not:
        the claim and its article stand either way."""
        if page is None or client.make_research is None:
            return None
        if not (page.registry_numbers or page.dois):
            return None
        research = client.make_research(session)
        try:
            candidates_named_in_article(
                session,
                claim,
                registry_numbers=page.registry_numbers,
                # With no literature source configured, papers are left unrecorded.
                dois=page.dois if research.papers is not None else (),
                registry=research.registry,
                papers=research.papers,
                backend=client.make_backend(session),
                now=now,
                reject_below=self.match_reject_below,
                accept_trial_above=self.match_accept_above,
                accept_paper_above=self.match_accept_above,
            )
        except (DecisionFailed, SourceError) as failure:
            session.flush()
            return f"the records its page names were not recorded: {failure}"
        return None

    def _claim_it_reports(
        self, session: Session, record: LinkLead, draft: Draft, client: ReadClient, now: datetime
    ) -> tuple[str | None, str | None]:
        """Choose among named candidates using their summaries as well as their names.

        Even equal names are candidates only: a generic category can hide different
        products. The single bounded decision is logged either way.
        """
        names = [draft.intervention, *draft.intervention_synonyms]
        # A topic's list knows a drug's brand and generic names; a claim under any of
        # them is a candidate, though the names share no word.
        candidates = claims_sharing_a_name(
            session, [*names, *other_names_of(names)], indication=draft.indication
        )
        linked_by_title = named_claims(
            session,
            list(
                session.scalars(
                    select(LinkLeadLink.record_id).where(
                        LinkLeadLink.link_lead_id == record.id,
                        LinkLeadLink.record_kind == CLAIM,
                        LinkLeadLink.reason == TITLE_NAMES_CLAIM,
                    )
                )
            ),
        )
        offered = {claim.slug for claim in candidates}
        candidates += [claim for claim in linked_by_title if claim.slug not in offered]
        candidates = candidates[:MAX_NAMED_CLAIMS]
        if not candidates:
            return None, None
        answer = choose_same_claim(
            session,
            client.make_backend(session),
            ref=lead_ref(record.id),
            intervention=draft.intervention,
            indication=draft.indication,
            summary=draft.summary,
            candidates=candidates,
            now=now,
        )
        # Two tests, both measured on the first reads (openspec lead-reading). That the
        # article reports one of the candidates must be likely enough: the decision
        # gives "none of these" 0.99 when the condition is another one and 0.40 or less
        # when it is the same story, whatever it gives each candidate. And one candidate
        # must be likelier than all other answers together, so that two claims for two
        # conditions of one drug are never settled by a near tie.
        one_of_them = 1 - answer.none_probability
        if (
            answer.likeliest is None
            or one_of_them < self.same_claim_accept_above
            or answer.likeliest_probability < SAME_CLAIM_MAJORITY
        ):
            return None, None
        return answer.likeliest, (
            f"read as {draft.intervention} for {draft.indication}; the same claim by "
            f"decision at {answer.likeliest_probability:.2f}, none of the candidates at "
            f"{answer.none_probability:.2f}"
        )

    def run(
        self, session: Session, record: LinkLead, client: ReadClient
    ) -> WorkOutcome | Failed | Deferred:
        now = self._time.now()
        claim_id = self._tracked_claim(session, record)
        if claim_id is not None:
            # No longer a lead to read: it leaves the step's scope as already tracked.
            record.screen_outcome = ScreenOutcome.ALREADY_TRACKED
            record.claim_id = claim_id
            return WorkOutcome.NOTHING_FOUND
        enough = self._has_enough(session, record)
        if enough is not None:
            return self._finish(record, ReadOutcome.ENOUGH_ARTICLES, enough)
        outlet = name_of(record.outlet)
        if outlet is None:
            return self._finish(record, ReadOutcome.CANNOT_BE_READ, NO_NAME)

        # The page reader is asked for the page. Whether the outlet may be asked, and how
        # often, is the reader's to decide; the pipeline acts on its answer.
        client.allowances.claim(READER)
        client.requests_made += 1
        try:
            retrieved = client.retriever.retrieve(record.url)
        except NotNow as later:
            # The site has not refused: it cannot be asked just now. The lead stays due
            # with no attempt counted, and the run goes on with other leads.
            return Deferred(str(later))
        except NotAllowed as refused:
            return self._finish(
                record, ReadOutcome.CANNOT_BE_READ, f"{NOT_ALLOWED}: {refused.reason}"
            )
        except NotServed as missing:
            return self._finish(
                record,
                ReadOutcome.CANNOT_BE_READ,
                f"{NO_PAGE} (the site answered {missing.status})",
            )
        except ThinPage:
            return self._finish(record, ReadOutcome.CANNOT_BE_READ, "too little article text")
        page = retrieved.page
        day = published_day(page.published if page else None)
        if day is None:
            return self._finish(record, ReadOutcome.CANNOT_BE_READ, NO_DATE)
        headline = (page.headline or "").strip() if page else ""
        if not headline:
            return self._finish(record, ReadOutcome.CANNOT_BE_READ, NO_HEADLINE)

        # The one model read. From here a failure is returned, not raised, so that the
        # call's cost and any logged decision stay recorded.
        checker = client.make_checker(session)
        try:
            draft = read_article(
                client.make_llm(session), checker, retrieved.text, purpose=LEAD_READING
            )
        except BudgetExceeded as ceiling:
            raise SpendCeilingReached(str(ceiling)) from None
        except LlmError as failure:
            return Failed(str(failure))
        # A class of treatments is every member of it, not one: "GLP-1 receptor agonists".
        # The name the read gave says so by rule, so no decision is paid for.
        if is_a_class(draft.intervention):
            return self._finish(
                record,
                ReadOutcome.NOT_ONE_TREATMENT,
                f"{draft.intervention} for {draft.indication}; a class of treatments, not one",
            )
        # A claim is one treatment for one condition. Triage sees only a headline, so what
        # the article turned out to be is asked here, of the read's own headline and
        # summary, before anything is joined or drafted. A treatment long in use is
        # wanted as much as a new one: its trials and approval are what came of it.
        try:
            report = kind_of_treatment_report(
                session,
                client.make_backend(session),
                ref=lead_ref(record.id),
                headline=draft.headline,
                summary=draft.summary,
                intervention=draft.intervention,
                indication=draft.indication,
                now=now,
            )
        except DecisionFailed as refused:
            session.flush()
            return Failed(str(refused))
        if report.one_treatment_probability < self.treatment_accept_above:
            return self._finish(
                record,
                ReadOutcome.NOT_ONE_TREATMENT,
                f"{draft.intervention} for {draft.indication}; about one treatment for "
                f"one condition at {report.one_treatment_probability:.2f}",
            )
        # Business news is about one treatment, but not about what it does: its price,
        # supply, sales, a lawsuit. Two rules, both the operator's (2026-11-15). It never
        # starts a claim: a claim rests on something reported of the treatment. And a
        # topic is covered by evidence, safety, new uses and approvals only, so on a
        # topic it does not join a claim either. The lead is on a topic when its title
        # or the treatment the read names holds one of the topic's words: a link is
        # often shared under a title that names nothing.
        business = report.evidence_probability < self.treatment_accept_above
        on_a_topic = any(
            names_one(text, self._topic_terms)
            for text in (record.title, draft.intervention, *draft.intervention_synonyms)
        )
        if business and on_a_topic:
            return self._finish(
                record,
                ReadOutcome.BUSINESS_NEWS,
                f"{draft.intervention} for {draft.indication}; on a topic, and about what "
                f"the treatment does at {report.evidence_probability:.2f}",
            )
        if business:
            established = "business news about a treatment"
        elif report.kind == ESTABLISHED_TREATMENT:
            established = "an established treatment in the news"
        else:
            established = None
        address = without_tracking(record.url)
        # One read at a time from here to the end of its transaction: whichever claim
        # another read has just made for this story is found, not made again.
        session.execute(select(func.pg_advisory_xact_lock(CLAIM_IDENTITY_LOCK)))
        try:
            existing, how = self._claim_it_reports(session, record, draft, client, now)
            if existing is not None:
                claim = claim_by_slug(session, existing)
                article, _ = article_from_draft(
                    session,
                    checker,
                    claim,
                    draft,
                    text=retrieved.text,
                    url=address,
                    outlet=outlet,
                    title=headline,
                    published_date=day,
                    archive_url=retrieved.archive_url,
                    now=now,
                )
                record.claim_id, record.source_article_id = claim.id, article.id
                note = self._named_on_the_page(session, claim, page, client, now)
                detail = "; ".join(part for part in (established, how, note) if part) or None
                return self._finish(record, ReadOutcome.ADDED_TO_CLAIM, detail)

            collision = slug_of_claim_covering(session, draft.intervention, draft.indication)
            if collision is not None:
                # The names are already taken, but identity was not established. Neither
                # force the article onto that claim nor pay to retry an unchanged read.
                return self._finish(
                    record,
                    ReadOutcome.IDENTITY_UNRESOLVED,
                    f"{draft.intervention} for {draft.indication}; names overlap {collision}, "
                    "but the same treatment and condition were not established",
                )
            if business:
                return self._finish(
                    record,
                    ReadOutcome.BUSINESS_NEWS,
                    f"{draft.intervention} for {draft.indication}; no claim to join, and "
                    f"about what the treatment does at {report.evidence_probability:.2f}",
                )
            slug = free_slug_for(session, draft.intervention, draft.indication)
            vertical, probability = choose_vertical(
                session,
                client.make_backend(session),
                ref=lead_ref(record.id),
                intervention=draft.intervention,
                indication=draft.indication,
                summary=draft.summary,
                now=now,
            )
            if probability < self.vertical_accept_above:
                return self._finish(
                    record,
                    ReadOutcome.NEEDS_VERTICAL,
                    f"{draft.intervention} for {draft.indication}; the nearest vertical was "
                    f"{vertical} at {probability:.2f}",
                )
            extracted = claim_from_draft(
                session,
                checker,
                draft,
                text=retrieved.text,
                slug=slug,
                vertical=vertical,
                url=address,
                outlet=outlet,
                title=headline,
                published_date=day,
                archive_url=retrieved.archive_url,
                now=now,
            )
            if self.approve_drafts_by_rule and not is_a_name(draft.intervention):
                # A description in place of a name is rejected now, as for any draft: no
                # registry search would change that. A named claim stays pending until
                # `thenwhat prepare` has searched the registries and decides it.
                record_decision(extracted.claim, ReviewState.REJECTED, by=Decider.RULE, now=now)
        except (EntryError, DecisionFailed) as refused:
            session.flush()
            return Failed(str(refused))
        article = find_article(session, extracted.claim, address)
        record.claim_id = extracted.claim.id
        record.source_article_id = article.id if article else None
        note = self._named_on_the_page(session, extracted.claim, page, client, now)
        detail = "; ".join(part for part in (established, note) if part) or None
        return self._finish(record, ReadOutcome.NEW_CLAIM, detail)
