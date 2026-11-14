"""Which stored registry record a trial's facts are read from. Behavior: openspec
trial-facts."""

from collections.abc import Iterable

from thenwhat.db.models import EvidenceEvent
from thenwhat.events.trial_facts import is_registry_record


def newest_registry_record(held: Iterable[EvidenceEvent]) -> EvidenceEvent | None:
    """Of one trial's events, the one holding the most recently fetched registry record,
    or None when none holds one, as for a trial entered by hand."""
    return max(
        (event for event in held if is_registry_record(event.raw_payload)),
        key=lambda event: (event.fetched_at, event.id),
        default=None,
    )
