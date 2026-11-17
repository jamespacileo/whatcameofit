"""What a record looks like on its way to the truth store, and the few rules every kind
shares: how a time, a date and a JSON value are written, how a payload is named by its
checksum, how an article's address key and an event's content checksum are worked out.

Behavior: openspec change `cloudflare-source-of-truth`, `store/README.md` ("Kinds and the
keys their bodies carry") and `store/schema.sql`. Nothing here reads a database.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from thenwhat.backfill.address import article_key

# A payload larger than this, in bytes of its JSON text, is an R2 object; a smaller one is
# kept in the store's `payload` table (design.md decision 16, point 1).
INLINE_PAYLOAD_LIMIT = 16384
R2_PREFIX = "payload/"
# What joins the parts of a natural key into the staged record's one `key` string.
KEY_JOIN = "|"


@dataclass(frozen=True, slots=True)
class Record:
    """One staged record: its kind, its natural key as one string, and its body, which
    names every parent by natural key and never by a row id."""

    kind: str
    key: str
    body: dict[str, Any]

    def staged(self) -> dict[str, Any]:
        """The record as the ingest service stages it (`store/ingest.sql`, `stage`)."""
        return {"kind": self.kind, "key": self.key, "body": self.body}


KEY_ESCAPE = "\\"


def key_of(*parts: object) -> str:
    """Parts joined into one key. A `|` or `\\` inside a part is escaped with `\\`, so
    that two different sets of parts never give one key; parts without either (every
    slug, every address key seen so far) are joined as they are, as `schema.sql` joins
    them."""
    return KEY_JOIN.join(
        str(part).replace(KEY_ESCAPE, KEY_ESCAPE * 2).replace(KEY_JOIN, KEY_ESCAPE + KEY_JOIN)
        for part in parts
    )


def key_parts(key: str) -> list[str]:
    """`key_of` read the other way: a key back to its parts."""
    parts, part, chars = [], [], iter(key)
    for char in chars:
        if char == KEY_ESCAPE:
            part.append(next(chars, KEY_ESCAPE))
        elif char == KEY_JOIN:
            parts.append("".join(part))
            part = []
        else:
            part.append(char)
    parts.append("".join(part))
    return parts


def body(**fields: Any) -> dict[str, Any]:
    """A record's body without its empty fields.

    The merge reads a JSON column with `->`, which gives the text `null` for a JSON null
    and SQL NULL for a field that is absent; the schema means SQL NULL ("asked, not
    held", no facts yet). Leaving an empty field out gives SQL NULL under `->` and `->>`
    alike, so it is left out everywhere and a reader treats absent as empty."""
    return {name: value for name, value in fields.items() if value is not None}


# --- times, dates, numbers ---------------------------------------------------------------


def when(moment: datetime | None) -> str | None:
    """A time as the store keeps it: ISO-8601 in UTC to the microsecond, always the same
    width, so that the merge's text comparisons (`>`, `min`) order times correctly."""
    if moment is None:
        return None
    if moment.tzinfo is None:
        raise ValueError(f"A time without a time zone cannot be stored: {moment!r}")
    return moment.astimezone(UTC).isoformat(timespec="microseconds")


def moment(text: str | None) -> datetime | None:
    return None if text is None else datetime.fromisoformat(text)


def day(value: date | None) -> str | None:
    return None if value is None else value.isoformat()


def date_of(text: str | None) -> date | None:
    return None if text is None else date.fromisoformat(text)


def money(amount: Decimal | None) -> float | None:
    return None if amount is None else float(amount)


def amount(value: float | None) -> Decimal | None:
    """Back to the six places Postgres keeps money in."""
    return None if value is None else Decimal(repr(value)).quantize(Decimal("0.000001"))


def flag(value: bool | None) -> int | None:
    return None if value is None else int(value)


# --- JSON and payloads -------------------------------------------------------------------


def canonical_json(value: Any) -> str:
    """The one text of a JSON value: keys sorted, no spaces, characters as they are.

    Postgres keeps a payload as JSONB, which does not keep the order of keys or the
    spacing it was given, so the text the source sent cannot be had again. This text is
    what a payload's checksum is of, what `bytes` counts, and what an inline payload's
    `body` holds; the ingest service checks an R2 object's checksum over the same bytes."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True, slots=True)
class Payload:
    sha256: str
    text: str

    @property
    def bytes(self) -> int:
        return len(self.text.encode())

    @property
    def inline(self) -> bool:
        return self.bytes <= INLINE_PAYLOAD_LIMIT

    @property
    def r2_key(self) -> str:
        return R2_PREFIX + self.sha256


def payload_of(value: Any) -> Payload:
    text = canonical_json(value)
    return Payload(sha256=hashlib.sha256(text.encode()).hexdigest(), text=text)


def payload_record(value: Any) -> Record:
    """A raw payload, named by its checksum. One of 16 KB or less travels in the record;
    a larger one is put in R2 under `payload/<sha256>` first and the record carries only
    the object's key."""
    return payload_record_of(payload_of(value))


def payload_record_of(payload: "Payload") -> Record:
    """`payload_record` of a payload already worked out."""
    return Record(
        kind="payload",
        key=payload.sha256,
        body=body(
            sha256=payload.sha256,
            bytes=payload.bytes,
            body=payload.text if payload.inline else None,
            r2_key=None if payload.inline else payload.r2_key,
        ),
    )


def payload_value(record: Record, r2_object: str | None = None) -> Any:
    """The payload a record names, from its own body or, for one kept in R2, from the
    object's text. The text must have the checksum the record names."""
    text = record.body.get("body", r2_object)
    if text is None:
        raise ValueError(f"Payload {record.key} is in R2 and its object was not given.")
    if hashlib.sha256(text.encode()).hexdigest() != record.body["sha256"]:
        raise ValueError(f"Payload {record.key} does not have the checksum it is named by.")
    return json.loads(text)


# --- the two values the proof's export stood in for -------------------------------------


def url_key(url: str) -> str:
    """A source article's or an article lead's address in the form addresses are
    compared in (`backfill/address.py`, the site's `article-key.mjs`). An address that
    has no key cannot be a web page; the store has nowhere to keep it."""
    key = article_key(url)
    if key is None:
        raise ValueError(f"The address {url!r} has no address key, so the store cannot hold it.")
    if KEY_JOIN in key or KEY_ESCAPE in key:
        # `schema.sql` joins a slug and an address key with a bare `|` (`staged_of_article`).
        raise ValueError(f"The address key {key!r} holds a `|` or `\\`; the store joins on them.")
    return key


# The fields of an evidence event its claim's status is derived from (design.md decision
# 16, point 2). Two fetches that agree on these are the same event.
CONTENT_FIELDS = (
    "type",
    "event_date",
    "trial_state",
    "trial_phases",
    "regulatory_outcome",
    "external_id",
)


def content_sha256(
    *,
    type: str,
    event_date: str,
    trial_state: str | None,
    trial_phases: list[str] | None,
    regulatory_outcome: str | None,
    external_id: str,
) -> str:
    """The checksum of what an evidence event says, as the store compares events. Phases
    are compared as a set: a registry that lists them in another order says the same."""
    content = {
        "type": type,
        "event_date": event_date,
        "trial_state": trial_state,
        "trial_phases": None if trial_phases is None else sorted(trial_phases),
        "regulatory_outcome": regulatory_outcome,
        "external_id": external_id,
    }
    return hashlib.sha256(canonical_json(content).encode()).hexdigest()
