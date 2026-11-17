"""Proposing a claim's subject terms, its intervention's kind, the genes its names name
and its drug record, as a step of the work ledger. Behavior: openspec subject-terms.

Its parts are paid for one by one. A part that finished stays when a later one cannot
ask its source: the claim is put off, and its paid decisions are kept for when it comes
back, which asks again only for what is still unscored.
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from thenwhat.claimsteps.inputs import Inputs
from thenwhat.claimsteps.reasons import (
    KIND_TERM_MISSING,
    SOURCE_FAILED,
    attempt,
    model_failed,
    put_off,
)
from thenwhat.claimsteps.step import Answer, ClaimSources, ClaimStep
from thenwhat.db.models import Claim
from thenwhat.decide.core import DecisionFailed
from thenwhat.domain import WorkOutcome
from thenwhat.llm.errors import LlmError
from thenwhat.sources.base import SourceError
from thenwhat.terms.service import (
    DrugRun,
    KindRun,
    KindTermMissing,
    TargetsRun,
    TermsRun,
    link_drug,
    link_kind,
    link_targets,
    link_terms,
)
from thenwhat.work.outcome import NeedsFix
from thenwhat.work.steps import Failed


@dataclass(slots=True)
class TermsFound:
    """What proposing a claim's terms gave, part by part. A part not reached is None."""

    terms: TermsRun | None = None
    kind: KindRun | KindTermMissing | None = None
    targets: TargetsRun | None = None
    drug: DrugRun | None = None

    @property
    def unscored(self) -> int:
        """How many candidates the model could not score: they stay without a score."""
        return (
            (len(self.terms.unscored) if self.terms else 0)
            + (len(self.targets.unscored) if self.targets else 0)
            + int(isinstance(self.kind, KindRun) and self.kind.failed)
        )


class ClaimTerms(ClaimStep):
    """Propose the claim's subject terms, the kind of its intervention, the genes its
    names name and its drug record. A rule approves a link scored high and rejects one
    scored near zero; the rest wait for review. Nothing here changes a status."""

    name = "claim_terms"
    reasons = (SOURCE_FAILED, KIND_TERM_MISSING)

    def __init__(
        self,
        *,
        reject_below: float,
        accept_above: float,
        term_limit: int,
        target_limit: int,
        rescore_pending: bool = False,
        **step: Any,
    ) -> None:
        super().__init__(**step)
        self.reject_below = reject_below
        self.accept_above = accept_above
        self.term_limit = term_limit
        self.target_limit = target_limit
        self.rescore_pending = rescore_pending

    def read(self, inputs: Inputs, claim_id: int) -> dict[str, Any]:
        # Candidates are gathered from the claim's names and from the terms its approved
        # trials are filed under.
        return {**inputs.names.get(claim_id, {}), "approved": inputs.approved.get(claim_id, [])}

    def work(self, session: Session, claim: Claim, sources: ClaimSources) -> Answer:
        now = self.now()
        vocabulary = sources.make_vocabulary(session)
        backend = sources.make_backend(session)
        found = TermsFound()
        self.results[claim.id] = found

        def terms() -> None:
            found.terms = link_terms(
                session,
                claim,
                vocabulary=vocabulary,
                backend=backend,
                now=now,
                limit=self.term_limit,
                rescore_pending=self.rescore_pending,
                accept_above=self.accept_above,
                reject_below=self.reject_below,
            )

        def kind() -> None:
            try:
                found.kind = link_kind(
                    session,
                    claim,
                    vocabulary=vocabulary,
                    backend=backend,
                    now=now,
                    accept_above=self.accept_above,
                    reject_below=self.reject_below,
                )
            except KindTermMissing as missing:
                found.kind = missing

        def targets() -> None:
            found.targets = link_targets(
                session,
                claim,
                genes=sources.make_genes(session),
                backend=backend,
                now=now,
                limit=self.target_limit,
                accept_above=self.accept_above,
                reject_below=self.reject_below,
            )

        def drug() -> None:
            found.drug = link_drug(session, claim, drugs=sources.make_drugs(session), now=now)

        for part in (terms, kind, targets, drug):
            answer = attempt(session, part)
            if isinstance(answer, SourceError):
                return put_off(answer, now)
            if isinstance(answer, DecisionFailed | LlmError):
                return model_failed(answer)
        if found.unscored:
            return Failed(f"{found.unscored} could not be scored and stay without a score")
        if isinstance(found.kind, KindTermMissing):
            return NeedsFix(KIND_TERM_MISSING, {"said": str(found.kind)})
        return WorkOutcome.DONE
