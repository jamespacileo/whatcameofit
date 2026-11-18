"""Fetch and resume the version-checked protocol cache for scope review."""

import fcntl
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from thenwhat.backfill.registry_scope_review import (
    confirm_protocol_evidence,
    load_protocol_evidence,
)
from thenwhat.sources.base import SourceError
from thenwhat.sources.clinicaltrials import SCOPE_PAGE_SIZE, ClinicalTrials
from thenwhat.sources.people import without_email_text, without_people
from thenwhat.work.errors import BackfillError

type Record = dict[str, Any]
type StoredTrial = tuple[Record, date | None]

_MODULES = {
    "identificationModule",
    "statusModule",
    "conditionsModule",
    "armsInterventionsModule",
    "eligibilityModule",
    "designModule",
    "outcomesModule",
}
_CONTACT_LINE = re.compile(
    r"https?://|\b(?:e-mail|email|phone|telephone|fax)\b|\bcontact\s*:", re.I
)


@dataclass(slots=True)
class ScopeEvidenceReport:
    cached: int = 0
    fetched: int = 0
    pages_read: int = 0
    pending_ids: list[str] = field(default_factory=list)
    issues: dict[str, str] = field(default_factory=dict)
    stopped: str | None = None


def _strip_scope_record(study: Record) -> Record:
    protocol = without_people(study)["protocolSection"]
    kept = without_email_text({name: value for name, value in protocol.items() if name in _MODULES})
    arms = kept.get("armsInterventionsModule") or {}
    prose = [*arms.get("armGroups", []), *arms.get("interventions", [])]
    prose.append(kept.get("eligibilityModule") or {})
    for section in prose:
        for key in ("description", "eligibilityCriteria", "studyPopulation"):
            if isinstance(text := section.get(key), str):
                section[key] = "".join(
                    line
                    for line in text.splitlines(keepends=True)
                    if not _CONTACT_LINE.search(line)
                )
    return {"protocolSection": kept}


def _confirm(identifier: str, stored: StoredTrial, detailed: Record) -> None:
    record, updated = stored
    confirm_protocol_evidence(
        identifier, record, detailed, stored_update=updated.isoformat() if updated else None
    )


def _write_cache(destination: Path, evidence: Mapping[str, Record]) -> None:
    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix=f".{destination.name}.",
        dir=destination.parent,
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        try:
            json.dump(evidence, handle, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            handle.write("\n")
            handle.close()
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)


def _index_page(studies: list[Record], expected: tuple[str, ...]) -> dict[str, Record]:
    records: dict[str, Record] = {}
    for study in studies:
        try:
            identifier = study["protocolSection"]["identificationModule"]["nctId"]
            if (
                not isinstance(identifier, str)
                or identifier not in expected
                or identifier in records
            ):
                raise ValueError
            records[identifier] = _strip_scope_record(study)
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            raise SourceError(
                "Registry scope response had malformed or unexpected trials."
            ) from error
    return records


def cache_scope_evidence(
    registry: ClinicalTrials,
    stored: Mapping[str, StoredTrial],
    destination: Path,
) -> ScopeEvidenceReport:
    """Keep checked records in a private file and resume from those matching this snapshot."""
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.with_name(f".{destination.name}.lock").open("a", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise BackfillError("Another run is writing this registry scope cache.") from error
        return _fill_cache(registry, stored, destination)


def _fill_cache(
    registry: ClinicalTrials,
    stored: Mapping[str, StoredTrial],
    destination: Path,
) -> ScopeEvidenceReport:
    exists = destination.exists()
    evidence = load_protocol_evidence(destination) if exists else {}
    report = ScopeEvidenceReport()
    needed = []
    for identifier, trial in stored.items():
        try:
            _confirm(identifier, trial, evidence[identifier])
        except (KeyError, ValueError):
            needed.append(identifier)
        else:
            report.cached += 1

    saved = set()
    for start in range(0, len(needed), SCOPE_PAGE_SIZE):
        page_ids = tuple(needed[start : start + SCOPE_PAGE_SIZE])
        try:
            page = registry.scope_page(page_ids)
            report.pages_read += 1
            records = _index_page(page.studies, page_ids)
        except SourceError as error:
            report.stopped = str(error)
            break
        for identifier in page_ids:
            detailed = records.get(identifier)
            if detailed is None:
                report.issues[identifier] = "The registry did not return this trial."
                continue
            try:
                _confirm(identifier, stored[identifier], detailed)
            except ValueError as error:
                report.issues[identifier] = str(error)
                continue
            evidence[identifier] = detailed
            saved.add(identifier)
    report.fetched = len(saved)
    report.pending_ids = [identifier for identifier in needed if identifier not in saved]
    if report.fetched or not exists:
        _write_cache(destination, evidence)
    return report
