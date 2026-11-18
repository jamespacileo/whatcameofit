"""Preview and apply stored registry-claim drafts."""

import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any

import typer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from thenwhat.backfill.registry_draft import (
    DraftBatchPlan,
    VerifiedLinks,
    applied_batch,
    apply_draft_plan,
    lock_drafting,
    prepare_draft_plan,
)
from thenwhat.backfill.registry_scope_review import load_protocol_evidence, load_scope_reviews
from thenwhat.backfill.trial_sets import REGISTRY_CLAIMS_2026, require_wider_record
from thenwhat.cli.backfill import make_allowances, refusals
from thenwhat.cli.entry import entry_session
from thenwhat.cli.session import settings_or_exit
from thenwhat.clinical.mesh_xml import mesh_xml_vocabulary
from thenwhat.config import Settings
from thenwhat.db.models import LlmUsage
from thenwhat.decide.core import BATCH_SIZE
from thenwhat.decide.steps import ENTITY_MATCH
from thenwhat.llm.decisions import MAX_QUESTIONS
from thenwhat.sources.clinicaltrials import ClinicalTrials
from thenwhat.work.errors import BackfillError
from thenwhat.work.spend import OPENAI_DECISIONS, left_this_month


def _preparation_estimate(
    session: Session, settings: Settings, plan: DraftBatchPlan, now: datetime
) -> dict[str, Any]:
    candidates: dict[str, set[str]] = defaultdict(set)
    for action in plan.actions:
        candidates[action.slug].update(action.trial_ids)
    allowance = make_allowances(settings).status(session, ClinicalTrials.name)
    decisions = settings.decision_backend == OPENAI_DECISIONS
    model = settings.llm_model
    if decisions:
        provider, _, name = (model or "").partition(":")
        model = settings.decisions_model or (name if provider.startswith("openai") else None)
    sample_count, average = session.execute(
        select(func.count(), func.avg(LlmUsage.cost_usd)).where(
            LlmUsage.purpose == f"decision:{ENTITY_MATCH}",
            LlmUsage.model == model,
            LlmUsage.created_at >= now - timedelta(days=30),
        )
    ).one()
    width = MAX_QUESTIONS if decisions else BATCH_SIZE
    match_calls = sum((len(trials) + width - 1) // width for trials in candidates.values())
    return {
        "drafting_network_requests": 0,
        "clinicaltrials_gov": {
            "claims_to_search": len(candidates),
            "named_trial_id_fallbacks_up_to": sum(map(len, candidates.values())),
            "allowance_requests_left": allowance.left,
            "paused_until": allowance.paused_until.isoformat() if allowance.paused_until else None,
        },
        "known_candidate_match_calls_before_cache": match_calls,
        "known_candidate_match_cost_usd": str(average * match_calls)
        if average is not None
        else None,
        "observed_match_calls_for_model": sample_count,
        "monthly_model_allowance_left_usd": str(left_this_month(session, settings, now)),
        "basis": (
            "Recent per-call mean for the configured match model applied to the known trial IDs. "
            "Preparation also searches registry names and aliases and can fetch additional "
            "records and run configured literature steps."
        ),
    }


def draft_from_registry_command(
    trial_set: Annotated[str, typer.Argument(help="The named set of eligible registry trials.")],
    batch: Annotated[str, typer.Option(help="Stable name for this drafting and audit batch.")],
    limit: Annotated[int | None, typer.Option(min=1, help="Maximum actionable groups.")] = None,
    reviewed_scopes: Annotated[
        Path | None, typer.Option(exists=True, dir_okay=False, help="Registry scope receipts.")
    ] = None,
    mesh_descriptors: Annotated[
        Path | None, typer.Option(exists=True, dir_okay=False, help="Annual NLM MeSH descriptors.")
    ] = None,
    verified_links: Annotated[
        Path | None,
        typer.Option(exists=True, dir_okay=False, help="Reviewed existing-claim links."),
    ] = None,
    apply_plan: Annotated[
        str | None, typer.Option(help="Apply the exact SHA-256 printed by a reviewed preview.")
    ] = None,
    arm_evidence: Annotated[
        Path | None,
        typer.Option(exists=True, dir_okay=False, help="Version-matched detailed protocol cache."),
    ] = None,
    existing_only: Annotated[
        bool, typer.Option(help="Nominate verified trials to existing claims without drafting.")
    ] = False,
) -> None:
    """Preview a batch from stored records, or apply a reviewed preview to the writer."""
    with refusals(), entry_session() as session:
        if trial_set != REGISTRY_CLAIMS_2026:
            raise BackfillError(
                f"Unknown registry drafting set '{trial_set}'. Use {REGISTRY_CLAIMS_2026}."
            )
        settings = settings_or_exit()
        if apply_plan is not None:
            lock_drafting(session)
        replay = applied_batch(session, batch, apply_plan)
        if replay is not None:
            report = replay
        else:
            try:
                reviews = (
                    load_scope_reviews(reviewed_scopes) if reviewed_scopes is not None else None
                )
                evidence = (
                    load_protocol_evidence(arm_evidence) if arm_evidence is not None else None
                )
                vocabulary = mesh_xml_vocabulary(mesh_descriptors) if mesh_descriptors else None
                links = (
                    VerifiedLinks.model_validate_json(verified_links.read_bytes()).links
                    if verified_links
                    else ()
                )
            except (OSError, ValueError, SyntaxError) as error:
                raise BackfillError(
                    f"Could not read registry drafting evidence: {error}"
                ) from error
            require_wider_record(session)
            plan = prepare_draft_plan(
                session,
                batch,
                limit=limit,
                scope_reviews=reviews,
                arm_evidence=evidence,
                vocabulary=vocabulary,
                links=links,
                existing_only=existing_only,
            )
            if apply_plan is None:
                report = {
                    "outcome": "preview",
                    **plan.report,
                    "preparation_estimate": _preparation_estimate(
                        session, settings, plan, datetime.now(UTC)
                    ),
                }
            else:
                report = {"batch": batch, **apply_draft_plan(session, plan, apply_plan)}
    typer.echo(json.dumps(report, ensure_ascii=False))
