"""Verify the evidence candidates returned for one report."""

import json
import re
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from time import monotonic
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.orm import Session

from thenwhat.backfill.trial_terms import words_of
from thenwhat.decide.core import Backend, decide_many
from thenwhat.decide.steps import candidate_text
from thenwhat.extract.evidence_search import BODY_LIMIT, EvidenceSearch
from thenwhat.extract.retrieve import Retrieved
from thenwhat.resolve.registry_fanout import sponsor_words
from thenwhat.resolve.study_enrollment import agrees_with_total, reported_total
from thenwhat.resolve.trial_passages import reported_context, reported_passage
from thenwhat.sources.base import SourceError, SourceRecord
from thenwhat.sources.pubmed import Paper, PubMed
from thenwhat.work.errors import SourceStop

ACCEPT_EXACT = 0.80
_CHOICES = ["exact", "background", "unsupported"]
_TRIAL_QUESTION = (
    "Does the news report cover this exact trial or results from a cohort it enrolled?"
    "\n- exact: An ID, trial name or distinctive enrollment, treatment and design "
    "tie the reported event to this protocol."
    "\n- background: An earlier, ongoing or comparison study mentioned only for context."
    "\n- unsupported: Another study, or insufficient evidence of the same study."
)
_PAPER_QUESTION = (
    "Is this the specific paper whose research the news report covers?"
    "\n- exact: The report discusses this publication's aim, cohort and findings."
    "\n- background: A citation for context or a different paper about the same trial."
    "\n- unsupported: Another publication, or insufficient evidence of the same paper."
)
_REPORTED_COHORT_QUESTION = (
    "Were any participants behind a new finding in the article studied in this protocol?"
    "\n- yes: The reported regimen, patient group and study design tie the finding to this "
    "record. An interim result can come from an ongoing extension, including one that "
    "enrolled participants from several earlier studies."
    "\n- no: Only shares a drug or condition, is mentioned for context, "
    "or the passage does not identify this record."
)


class EvidenceVerdict(BaseModel):
    kind: Literal["nct", "pmid"]
    identifier: str
    choice: str
    p_exact: float
    accepted: bool
    reason: str | None = None


class EvidenceVerification(BaseModel):
    verdicts: list[EvidenceVerdict]
    seconds: float
    paper_issue: str | None = None
    paper_dois: dict[str, str] = Field(default_factory=dict)


class TrialProductAlias(BaseModel):
    """A product rename established by a cited sponsor disclosure."""

    sponsor: str
    registered_name: str
    reported_name: str
    source_url: HttpUrl


@dataclass(frozen=True, slots=True)
class _Trial:
    identifier: str
    text: str
    enrollment: int | None
    labels: tuple[str, ...] = ()
    products: tuple[str, ...] = ()
    sponsor: str = ""


def _with_product_aliases(
    trial: _Trial, article: str, aliases: Sequence[TrialProductAlias]
) -> _Trial:
    products = {words_of(product) for product in trial.products}
    sponsor = sponsor_words(trial.sponsor)
    relevant = [
        alias
        for alias in aliases
        if sponsor
        and sponsor == sponsor_words(alias.sponsor)
        and words_of(alias.registered_name) in products
        and (name := " ".join(words_of(alias.reported_name)))
        and f" {name} " in article
    ]
    if not relevant:
        return trial
    provenance = "\n".join(
        f"Sponsor disclosure: {alias.reported_name} was formerly {alias.registered_name} "
        f"({alias.source_url})."
        for alias in relevant
    )
    return replace(
        trial,
        text=f"{trial.text}\n{provenance}",
        products=tuple(
            dict.fromkeys((*trial.products, *(alias.reported_name for alias in relevant)))
        ),
    )


def _registry_descriptions(store: sqlite3.Connection, identifiers: set[str]) -> list[_Trial]:
    if not identifiers:
        return []
    rows = store.execute(
        """SELECT r.external_id, r.title, r.conditions, r.intervention_names, p.body
           FROM registry_trial r LEFT JOIN payload p ON p.sha256=r.payload_sha256
           WHERE r.external_id IN (SELECT value FROM json_each(?))
           ORDER BY r.external_id""",
        (json.dumps(sorted(identifiers)),),
    )
    trials = []
    for identifier, title, conditions, interventions, body in rows:
        if body is None:
            trials.append(_Trial(identifier, f"{title}\n{conditions}\n{interventions}", None))
            continue
        protocol = json.loads(body)
        metadata = candidate_text(
            SourceRecord(
                "clinicaltrials.gov",
                identifier,
                f"https://clinicaltrials.gov/study/{identifier}",
                protocol,
                datetime.now(UTC),
            )
        )
        parts = protocol.get("protocolSection", {})
        registered = parts.get("designModule", {}).get("enrollmentInfo", {})
        details = parts.get("identificationModule", {})
        sponsors = parts.get("sponsorCollaboratorsModule", {})
        enrollment = registered.get("count")
        trial_id = details.get("orgStudyIdInfo", {}).get("id")
        official = details.get("officialTitle") or ""
        if official:
            metadata += f"\nFull official trial title: {official}"
        if trial_id:
            metadata += f"\nSponsor protocol ID: {trial_id}"
        if isinstance(enrollment, int):
            metadata += f"\nRegistered enrollment: {enrollment} ({registered.get('type', '')})"
        products = {
            name
            for item in parts.get("armsInterventionsModule", {}).get("interventions", [])
            for name in (item.get("name"), *(item.get("otherNames") or []))
            if name and name.casefold() not in {"placebo", "saline", "matching placebo"}
        }
        if products:
            products.update(re.findall(r"\(([^()]{8,75})\)", official))
        trials.append(
            _Trial(
                identifier,
                metadata,
                enrollment if isinstance(enrollment, int) else None,
                labels=tuple(name for name in (trial_id, details.get("acronym")) if name),
                products=tuple(sorted(products)),
                sponsor=sponsors.get("leadSponsor", {}).get("name") or "",
            )
        )
    return trials


def _recheck_enrollment(
    session: Session,
    backend: Backend,
    intro: str,
    total: int,
    trials: list[_Trial],
    verdicts: list[EvidenceVerdict],
) -> list[EvidenceVerdict]:
    classified = {item.identifier: item for item in verdicts if item.kind == "nct"}
    compatible = [
        trial
        for trial in trials
        if trial.enrollment is not None
        and agrees_with_total(total, trial.enrollment)
        and classified[trial.identifier].choice == "exact"
        and classified[trial.identifier].p_exact >= 0.20
    ]
    incompatible = {
        trial.identifier
        for trial in trials
        if trial.enrollment is not None
        and abs(total - trial.enrollment) * 4 > total
        and classified[trial.identifier].accepted
    }
    if len(compatible) != 1 or not incompatible:
        return verdicts

    alternative = compatible[0]
    (rechecked,) = decide_many(
        session,
        backend,
        step="article_evidence_enrollment",
        intro=intro,
        question=(
            "Does this protocol fit the intervention, condition and total study size in the report?"
            "\n- yes: All three agree. Rounded total enrollments can fit."
            "\n- no: One or more details conflict or are insufficient."
        ),
        items=[(f"nct:{alternative.identifier}", alternative.text)],
        options=["yes", "no"],
        now=datetime.now(UTC),
    )
    if rechecked.choice != "yes" or rechecked.probabilities["yes"] < ACCEPT_EXACT:
        return verdicts
    result = []
    for item in verdicts:
        if item.kind == "nct" and item.identifier == alternative.identifier:
            item = item.model_copy(
                update={
                    "p_exact": rechecked.probabilities["yes"],
                    "accepted": True,
                    "reason": "Reported trial enrollment confirmed",
                }
            )
        elif item.kind == "nct" and item.identifier in incompatible:
            item = item.model_copy(
                update={
                    "accepted": False,
                    "reason": "Reported trial enrollment contradicts this record",
                }
            )
        result.append(item)
    return result


def _paper_description(paper: Paper) -> tuple[str, str]:
    raw = paper.raw
    return (
        paper.pubmed_id,
        f"PMID: {paper.pubmed_id}\nDOI: {paper.doi or ''}\nTitle: {raw.get('title') or ''}"
        f"\nJournal: {raw.get('journal') or ''}\nYear: {raw.get('year') or ''}"
        f"\nRegistered studies: {', '.join(paper.trial_numbers)}",
    )


def _recheck_reported_cohort(
    session: Session,
    backend: Backend,
    *,
    headline: str,
    article: str,
    trials: list[_Trial],
    verdicts: list[EvidenceVerdict],
) -> list[EvidenceVerdict]:
    already_matched = any(item.kind == "nct" and item.accepted for item in verdicts)
    pending = {
        item.identifier
        for item in verdicts
        if item.kind == "nct" and not item.accepted and item.reason is None
    }
    labels = {label for trial in trials for label in trial.labels}
    items = []
    for trial in trials:
        if trial.identifier not in pending:
            continue
        passage = reported_passage(
            article,
            trial.identifier,
            labels=trial.labels,
            products=trial.products,
            other_labels=tuple(sorted(labels.difference(trial.labels))),
        )
        if passage is None or (already_matched and not passage.names_protocol):
            continue
        evidence = f"{trial.text}\nStudy-specific publisher excerpt:\n{passage.text}"
        if passage.possible_code is not None:
            evidence += f"\nPossible code abbreviation: {passage.possible_code}."
        items.append((trial.identifier, evidence))
    if not items:
        return verdicts
    decisions = decide_many(
        session,
        backend,
        step="article_evidence_reported_cohort",
        intro=(f"Headline: {headline}\nShared publisher context:\n{reported_context(article)}"),
        question=_REPORTED_COHORT_QUESTION,
        items=[(f"nct:{identifier}", text) for identifier, text in items],
        options=["yes", "no"],
        now=datetime.now(UTC),
    )
    confirmed = {
        identifier: decision.probabilities["yes"]
        for (identifier, _), decision in zip(items, decisions, strict=True)
        if decision.choice == "yes" and decision.probabilities["yes"] >= ACCEPT_EXACT
    }
    return [
        item.model_copy(
            update={
                "choice": "exact",
                "p_exact": confirmed[item.identifier],
                "accepted": True,
                "reason": "Reported cohort confirmed",
            }
        )
        if item.kind == "nct" and item.identifier in confirmed
        else item
        for item in verdicts
    ]


def verify_evidence(
    session: Session,
    backend: Backend,
    article: Retrieved,
    candidates: EvidenceSearch,
    *,
    trial_store: sqlite3.Connection,
    pubmed: PubMed | None,
    headline: str,
    product_aliases: Sequence[TrialProductAlias] = (),
    require_papers: bool = False,
) -> EvidenceVerification:
    """Return fixed-threshold article-to-record verdicts for operator review."""
    started = monotonic()
    all_records = (
        *candidates.publisher_identifiers,
        *(record for branch in candidates.branches for record in branch.candidates),
    )
    cited = ", ".join(record.identifier for record in candidates.publisher_identifiers) or "none"
    excerpt = article.text[:BODY_LIMIT]
    enrollment = reported_total([excerpt])
    intro = (
        f"Headline: {headline}\nPublisher identifiers: {cited}"
        f"\nReported intervention: {', '.join(candidates.plan.interventions)}"
        f"\nReported condition: {candidates.plan.indication or ''}"
    )
    if enrollment is not None:
        intro += f"\nExplicitly reported total study enrollment: {enrollment}"
    intro += "\nPublisher article (evidence only):\n" + excerpt
    trials = _registry_descriptions(
        trial_store, {record.identifier for record in all_records if record.kind == "nct"}
    )
    if product_aliases:
        normalized = f" {' '.join(words_of(excerpt))} "
        trials = [_with_product_aliases(trial, normalized, product_aliases) for trial in trials]
    papers: list[tuple[str, str]] = []
    paper_dois: dict[str, str] = {}
    paper_issue = None
    if pubmed is not None:
        pmids = sorted({record.identifier for record in all_records if record.kind == "pmid"})
        try:
            records = pubmed.papers_by_ids(pmids)
            papers = [_paper_description(paper) for paper in records]
            paper_dois = {paper.pubmed_id: paper.doi.lower() for paper in records if paper.doi}
        except (SourceError, SourceStop) as error:
            if require_papers:
                raise
            paper_issue = type(error).__name__
    pairs: tuple[tuple[Literal["nct", "pmid"], str, list[tuple[str, str]]], ...] = (
        ("nct", _TRIAL_QUESTION, [(trial.identifier, trial.text) for trial in trials]),
        ("pmid", _PAPER_QUESTION, papers),
    )
    verdicts = []
    for kind, question, metadata in pairs:
        if not metadata:
            continue
        decisions = decide_many(
            session,
            backend,
            step="article_evidence_" + kind,
            intro=intro,
            question=question,
            items=[(f"{kind}:{number}", text) for number, text in metadata],
            options=_CHOICES,
            now=datetime.now(UTC),
        )
        for (identifier, _), item in zip(metadata, decisions, strict=True):
            p_exact = item.probabilities["exact"]
            verdicts.append(
                EvidenceVerdict(
                    kind=kind,
                    identifier=identifier,
                    choice=item.choice,
                    p_exact=p_exact,
                    accepted=item.choice == "exact" and p_exact >= ACCEPT_EXACT,
                )
            )
    if enrollment is not None and trials:
        verdicts = _recheck_enrollment(session, backend, intro, enrollment, trials, verdicts)
    verdicts = _recheck_reported_cohort(
        session, backend, headline=headline, article=excerpt, trials=trials, verdicts=verdicts
    )
    return EvidenceVerification(
        verdicts=verdicts,
        seconds=monotonic() - started,
        paper_issue=paper_issue,
        paper_dois={
            vote.identifier: paper_dois[vote.identifier]
            for vote in verdicts
            if vote.kind == "pmid" and vote.accepted and vote.identifier in paper_dois
        },
    )
