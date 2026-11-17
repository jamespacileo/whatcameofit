"""Proposing a claim's subject terms, its intervention's kind, the genes its names name
and its drug record, as a step of the work ledger. Behavior: openspec subject-terms.

Its parts are paid for one by one. A part that finished stays when a later one cannot
ask its source: the claim is put off, and its paid decisions are kept for when it comes
back, which asks again only for what is still unscored.
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claimsteps.inputs import Inputs
from thenwhat.claimsteps.reasons import (
    KIND_TERM_MISSING,
    MESH_UNRESOLVED,
    SOURCE_FAILED,
    SOURCE_RETRY,
    run_parts,
)
from thenwhat.claimsteps.step import Answer, ClaimSources, ClaimStep
from thenwhat.clinical.service import read_tree, stored_vocabulary
from thenwhat.db.models import Claim, ClaimTerm
from thenwhat.domain import ReviewState, TermFit, TermRole, WorkOutcome
from thenwhat.export.records import PostgresRecords
from thenwhat.sources.base import MissingContact, SourceError
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
from thenwhat.work.outcome import Later, NeedsFix
from thenwhat.work.steps import Failed


@dataclass(slots=True)
class TermsFound:
    """What proposing a claim's terms gave, part by part. A part not reached is None."""

    terms: TermsRun | None = None
    kind: KindRun | KindTermMissing | None = None
    targets: TargetsRun | None = None
    drug: DrugRun | None = None
    tree_error: SourceError | None = None

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
    version = 2
    reasons = (SOURCE_FAILED, KIND_TERM_MISSING, MESH_UNRESOLVED)

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

        def ancestry() -> None:
            approved = list(
                session.scalars(
                    select(ClaimTerm.external_id).where(
                        ClaimTerm.claim_id == claim.id,
                        ClaimTerm.source_name == "mesh",
                        ClaimTerm.review_state == ReviewState.APPROVED,
                        ClaimTerm.role == TermRole.CONDITION,
                        ClaimTerm.fit == TermFit.EXACT,
                    )
                )
            )
            if approved and stored_vocabulary(PostgresRecords(session)).missing(approved):
                try:
                    read_tree(session, sources.make_mesh(session), [claim], mapping={})
                except MissingContact as error:
                    # The optional ancestry lookup has no configured contact. Keep the
                    # completed term decisions and report the pending tree to the operator.
                    found.tree_error = error
                except SourceError as error:
                    found.tree_error = error
                    raise

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

        unfinished = run_parts(session, (terms, kind, targets, drug, ancestry), now)
        if unfinished is not None:
            return unfinished
        if found.unscored:
            return Failed(f"{found.unscored} could not be scored and stay without a score")
        if found.terms and found.terms.unresolved:
            return Later(
                MESH_UNRESOLVED, now + SOURCE_RETRY, {"names": ", ".join(found.terms.unresolved)}
            )
        if isinstance(found.kind, KindTermMissing):
            return NeedsFix(KIND_TERM_MISSING, {"said": str(found.kind)})
        return WorkOutcome.DONE
