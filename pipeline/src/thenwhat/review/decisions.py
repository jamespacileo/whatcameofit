"""Recording review decisions. Behavior: openspec review."""

from datetime import datetime

from thenwhat.db.models import Reviewed
from thenwhat.domain import Decider, ReviewState


def record_decision(item: Reviewed, state: ReviewState, *, by: Decider, now: datetime) -> None:
    """Approve or reject an item, noting when the decision was made and who made it."""
    if state is ReviewState.PENDING:
        raise ValueError("A decision is an approval or a rejection, not pending.")
    item.review_state = state
    item.reviewed_at = now
    item.reviewed_by = by
