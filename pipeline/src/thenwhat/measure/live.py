"""What the runs are doing now, read from the day's files by another process.
Behavior: openspec processing-metrics, "A run can be watched while it works" and "The
live view shows rate, cost and where work is held".

`view_of` is pure: from the lines read so far and the time, it gives what the view
shows. `kept` is pure too: it drops what no later view needs, so a view left open all
day holds minutes of lines, not the day's. `watch` is the loop: it reads the files from
where it last read, asks the database for the paused sources and the month's spend, and
draws. Nothing here writes, and no source is asked.

A record is in hand from its start line until its measurement is written. A process
that holds a record writes a line at least every `BEAT_SECONDS`, so a record whose
process has written nothing for `ALIVE_SECONDS` is no longer counted in hand: a run that
crashed leaves nothing in hand for longer than that. Such records are counted apart, as
left in hand by a process that stopped.
"""

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.db.models import SourceAllowanceUse
from thenwhat.measure.events import RUN_ENDED, RUN_STARTED
from thenwhat.measure.files import BEAT, BEAT_SECONDS, NOT_WRITTEN, Follower, last_event
from thenwhat.measure.report import NotWritten, not_written_of
from thenwhat.measure.spans import STARTED, Event, Span

# The windows, in minutes, each step's figures are given for.
WINDOWS = (1, 5, 15)
WIDEST = timedelta(minutes=max(WINDOWS))
# How often the view is drawn again. A measurement is written within a second of its
# record finishing, so the view counts it within five seconds.
REDRAW_SECONDS = 4.0
# How long a process may write nothing before the records it holds are no longer
# counted in hand.
ALIVE_SECONDS = BEAT_SECONDS * 2.5

Line = Span | Event


@dataclass(frozen=True, slots=True)
class StepWindow:
    """What one step did in one window."""

    step: str
    minutes: int
    records: int
    # Records finished a minute, by outcome.
    finished_a_minute: dict[str, float]
    # Shares of the step's time: running, and waiting by cause, largest first.
    running_share: float
    waiting_shares: list[tuple[str, float]]
    cost_a_minute: Decimal
    cost_a_record: Decimal | None

    @property
    def largest_wait(self) -> str | None:
        """The cause most time was spent waiting on."""
        return self.waiting_shares[0][0] if self.waiting_shares else None


@dataclass(frozen=True, slots=True)
class InHand:
    step: str
    records: int
    oldest_seconds: float
    # What the oldest is: an article's address key, or none for a batch.
    oldest_trace: str | None


@dataclass(frozen=True, slots=True)
class Running:
    """A run started and not ended, whose process is alive."""

    step: str
    started_at: datetime
    limit: int | None
    workers: int


@dataclass(frozen=True, slots=True)
class Ended:
    step: str
    at: datetime
    why: str
    counts: dict[str, int]
    not_written: int
    error_kind: str | None


@dataclass(frozen=True, slots=True)
class LiveView:
    now: datetime
    newest_line_at: datetime | None
    writers: list[str]
    windows: list[StepWindow]
    in_hand: list[InHand]
    # Records whose process stopped without finishing them, in the last fifteen minutes.
    left_in_hand: int
    running: list[Running]
    last_ended: Ended | None
    paused: list[tuple[str, datetime]]
    spent_usd: Decimal
    ceiling_usd: Decimal
    not_written: list[NotWritten] = field(default_factory=list)
    unreadable: int = 0

    @property
    def idle(self) -> bool:
        """Nothing has been recorded in the widest window."""
        return self.newest_line_at is None or self.newest_line_at < self.now - WIDEST

    @property
    def oldest_in_hand(self) -> InHand | None:
        return max(self.in_hand, key=lambda held: held.oldest_seconds, default=None)


def _at(line: Line) -> datetime:
    return line.ended if isinstance(line, Span) else line.at


def _process_of(line: Line) -> str | None:
    """The process that wrote a line, where the line says."""
    if isinstance(line, Span):
        return line.id.rsplit("-", 1)[0] if line.id else None
    process = line.values.get("process")
    return str(process) if process else None


@dataclass(slots=True)
class _Read:
    """The lines sorted by what they say."""

    spans: list[Span] = field(default_factory=list)
    starts: dict[str, Event] = field(default_factory=dict)
    finished: set[str] = field(default_factory=set)
    signs: dict[str, datetime] = field(default_factory=dict)
    started_runs: dict[str, Event] = field(default_factory=dict)
    ended_runs: dict[str, Event] = field(default_factory=dict)
    notices: list[Event] = field(default_factory=list)

    def alive(self, process: object, now: datetime) -> bool:
        sign = self.signs.get(str(process))
        return sign is not None and sign >= now - timedelta(seconds=ALIVE_SECONDS)

    def in_hand(self, start: Event, now: datetime) -> bool:
        return (
            str(start.values.get("id")) not in self.finished
            and start.values.get("run") not in self.ended_runs
            and self.alive(start.values.get("process"), now)
        )


def _read(lines: Iterable[Line]) -> _Read:
    read = _Read()
    for line in lines:
        process = _process_of(line)
        if process is not None:
            moment = _at(line)
            if moment > read.signs.get(process, datetime.min.replace(tzinfo=UTC)):
                read.signs[process] = moment
        if isinstance(line, Span):
            read.spans.append(line)
            if line.id is not None:
                read.finished.add(line.id)
        elif line.kind == STARTED:
            read.starts[str(line.values.get("id"))] = line
        elif line.kind == RUN_STARTED:
            read.started_runs[str(line.values.get("run"))] = line
        elif line.kind == RUN_ENDED:
            read.ended_runs[str(line.values.get("run"))] = line
        elif line.kind == NOT_WRITTEN:
            read.notices.append(line)
    return read


def _window(step: str, minutes: int, spans: Sequence[Span]) -> StepWindow:
    by_outcome: dict[str, int] = {}
    waited: dict[str, float] = {}
    ran = 0.0
    cost = Decimal(0)
    for span in spans:
        for outcome, records in span.records_by_outcome().items():
            by_outcome[outcome] = by_outcome.get(outcome, 0) + records
        for cause, seconds in span.waited.items():
            waited[cause] = waited.get(cause, 0.0) + seconds
        ran += span.ran_seconds
        # What the whole step cost for its records, what was measured inside it with it.
        cost += span.cost_usd + span.inner_cost_usd
    records = sum(by_outcome.values())
    total = ran + sum(waited.values())
    return StepWindow(
        step=step,
        minutes=minutes,
        records=records,
        finished_a_minute={outcome: n / minutes for outcome, n in sorted(by_outcome.items())},
        running_share=ran / total if total else 0.0,
        waiting_shares=sorted(
            ((cause, seconds / total) for cause, seconds in waited.items() if total),
            key=lambda share: share[1],
            reverse=True,
        ),
        cost_a_minute=cost / minutes,
        cost_a_record=cost / records if records else None,
    )


def view_of(
    lines: Iterable[Line],
    now: datetime,
    *,
    paused: Mapping[str, datetime],
    spent_usd: Decimal,
    ceiling_usd: Decimal,
    unreadable: int = 0,
) -> LiveView:
    """What the view shows at `now`, from the lines read so far."""
    held = list(lines)
    read = _read(held)
    recent = [span for span in read.spans if now - WIDEST < span.ended <= now]
    windows = [
        _window(
            step,
            minutes,
            [
                span
                for span in recent
                if span.step == step and span.ended > now - timedelta(minutes=minutes)
            ],
        )
        for step in sorted({span.step for span in recent})
        for minutes in WINDOWS
    ]
    held_by_step: dict[str, list[Event]] = {}
    left = 0
    for start in read.starts.values():
        if read.in_hand(start, now):
            held_by_step.setdefault(str(start.values.get("step")), []).append(start)
        elif str(start.values.get("id")) not in read.finished and start.at > now - WIDEST:
            left += int(start.values.get("batch") or 1)
    in_hand = []
    for step, starts in sorted(held_by_step.items()):
        oldest = min(starts, key=lambda start: start.at)
        trace = oldest.values.get("trace")
        in_hand.append(
            InHand(
                step=step,
                records=sum(int(start.values.get("batch") or 1) for start in starts),
                oldest_seconds=max((now - oldest.at).total_seconds(), 0.0),
                oldest_trace=str(trace) if trace else None,
            )
        )
    running = [
        Running(
            step=str(started.values.get("step")),
            started_at=started.at,
            limit=started.values.get("limit"),
            workers=int(started.values.get("workers") or 1),
        )
        for run, started in read.started_runs.items()
        if run not in read.ended_runs and read.alive(started.values.get("process"), now)
    ]
    last = max(read.ended_runs.values(), key=lambda event: event.at, default=None)
    times = [_at(line) for line in held if _at(line) <= now]
    return LiveView(
        now=now,
        newest_line_at=max(times, default=None),
        writers=sorted({line.writer for line in held}),
        windows=windows,
        in_hand=in_hand,
        left_in_hand=left,
        running=sorted(running, key=lambda run: run.started_at),
        last_ended=_ended(last) if last is not None else None,
        paused=sorted(paused.items(), key=lambda pause: pause[1]),
        spent_usd=spent_usd,
        ceiling_usd=ceiling_usd,
        not_written=[
            not_written_of(notice) for notice in read.notices if notice.at.date() == now.date()
        ],
        unreadable=unreadable,
    )


def _ended(event: Event) -> Ended:
    values = event.values
    return Ended(
        step=str(values.get("step")),
        at=event.at,
        why=str(values.get("why")),
        counts={str(name): int(n) for name, n in (values.get("counts") or {}).items()},
        not_written=int(values.get("not_written") or 0),
        error_kind=values.get("error_kind"),
    )


def kept(lines: Iterable[Line], now: datetime) -> list[Line]:
    """The lines a view at `now` or later can still need: measurements of the widest
    window, records still in hand or left in it lately, runs not ended and the last that
    ended, each process's last sign, and today's notices of what could not be written."""
    held = list(lines)
    read = _read(held)
    since = now - WIDEST
    last_ended = max(read.ended_runs.values(), key=lambda event: event.at, default=None)
    last_sign: dict[str, Event] = {}
    out: list[Line] = []
    for line in held:
        if isinstance(line, Span):
            if line.ended > since:
                out.append(line)
        elif line.kind == STARTED:
            if str(line.values.get("id")) not in read.finished and (
                line.at > since or read.in_hand(line, now)
            ):
                out.append(line)
        elif line.kind == RUN_STARTED:
            if str(line.values.get("run")) not in read.ended_runs or line.at > since:
                out.append(line)
        elif line.kind == RUN_ENDED:
            if line is last_ended or line.at > since:
                out.append(line)
        elif line.kind == NOT_WRITTEN:
            if line.at.date() == now.date():
                out.append(line)
        elif line.kind == BEAT:
            process = str(line.values.get("process"))
            if process not in last_sign or line.at > last_sign[process].at:
                last_sign[process] = line
        elif line.at > since:
            out.append(line)
    return out + list(last_sign.values())


# --- in words ------------------------------------------------------------------------

OUTCOME_WORDS = {
    "done": "done",
    "nothing_found": "found nothing",
    "later": "put off",
    "needs_fix": "need a fix",
    "failed": "failed",
    "deferred": "could not be asked for now",
}
WHY_WORDS = {
    "nothing_due": "nothing was due",
    "limit": "it reached its limit",
    "cannot_ask": "a provider could not be asked",
    "spend_ceiling": "the month's model spend reached its ceiling",
    "operator": "the operator stopped it",
    "failed": "an error ended it",
}


def _duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    return f"{int(seconds // 3600)}h {int(seconds % 3600 // 60)}m"


def _share(name: str, share: float) -> str:
    return f"{name} {share:.0%}"


def lines_of(view: LiveView, folder: Path) -> list[str]:
    """The view in words, as the operator reads it."""
    newest = (
        "nothing read yet"
        if view.newest_line_at is None
        else f"newest line {_duration((view.now - view.newest_line_at).total_seconds())} old"
    )
    writers = ", ".join(view.writers) or "none"
    lines = [
        f"Live, {view.now:%Y-%m-%d %H:%M:%S} UTC, from {folder} (writers: {writers}; {newest})"
    ]
    if view.idle:
        lines.append("Nothing has been recorded in the last fifteen minutes.")
    for run in view.running:
        limit = f"limit {run.limit:,}" if run.limit is not None else "no limit"
        lines.append(
            f"Running: {run.step} since {run.started_at:%H:%M:%S} UTC"
            f" ({limit}, {run.workers} workers)"
        )
    if view.last_ended is not None and (view.idle or not view.running):
        ended = view.last_ended
        counts = ", ".join(
            f"{n:,} {OUTCOME_WORDS.get(name, name)}"
            for name, n in ended.counts.items()
            if name != "still_due" and n
        )
        due = ended.counts.get("still_due")
        lines.append(
            f"The last run, of {ended.step}, ended at {ended.at:%Y-%m-%d %H:%M:%S} UTC:"
            f" {WHY_WORDS.get(ended.why, ended.why)}"
            + (f" ({ended.error_kind})" if ended.error_kind else "")
            + f". {counts or 'No records'}"
            + (f"; {due:,} still due" if due is not None else "")
            + "."
        )
        if ended.not_written:
            lines.append(f"  {ended.not_written:,} of its measurements could not be written.")
    if view.windows:
        lines += ["", "By step, in the last 1, 5 and 15 minutes:"]
    for window in view.windows:
        if window.minutes == WINDOWS[0]:
            lines.append(f"  {window.step}")
        rates = ", ".join(
            f"{rate:.1f} {OUTCOME_WORDS.get(outcome, outcome)}"
            for outcome, rate in window.finished_a_minute.items()
        )
        waiting = ", ".join(_share(cause, share) for cause, share in window.waiting_shares)
        a_record = f"${window.cost_a_record:.4f}" if window.cost_a_record is not None else "-"
        lines.append(
            f"    {window.minutes:>2} min: {window.records / window.minutes:.1f} records a minute"
            + (f" ({rates})" if rates else "")
            + f"; running {window.running_share:.0%}"
            + (f", waiting {waiting}" if waiting else "")
            + (f"; waited most on {window.largest_wait}" if window.largest_wait else "")
            + f"; ${window.cost_a_minute:.4f} a minute, {a_record} a record"
        )
    lines.append("")
    if view.in_hand:
        lines.append("In hand:")
        for held in view.in_hand:
            what = f", {held.oldest_trace}" if held.oldest_trace else ""
            lines.append(
                f"  {held.step}: {held.records:,} records, the oldest for"
                f" {_duration(held.oldest_seconds)}{what}"
            )
        oldest = view.oldest_in_hand
        assert oldest is not None
        lines.append(f"  Oldest in hand: {oldest.step}, for {_duration(oldest.oldest_seconds)}.")
    else:
        lines.append("In hand: none.")
    if view.left_in_hand:
        lines.append(
            f"  Left in hand by a process that stopped without finishing them:"
            f" {view.left_in_hand:,} records."
        )
    if view.paused:
        lines.append("Paused:")
        lines += [f"  {source} until {until:%Y-%m-%d %H:%M} UTC" for source, until in view.paused]
    else:
        lines.append("Paused: none.")
    lines.append(f"Model spend this month: ${view.spent_usd:.2f} of ${view.ceiling_usd:.2f}.")
    for gap in view.not_written:
        lines.append(
            f"{gap.measurements:,} measurements could not be written from"
            f" {gap.since:%H:%M} to {gap.until:%H:%M} UTC."
        )
    if view.unreadable:
        lines.append(f"{view.unreadable:,} lines of the files could not be read.")
    return lines


# --- the loop ------------------------------------------------------------------------


def paused_sources(session: Session, now: datetime) -> dict[str, datetime]:
    """Every source and outlet not to be asked before a time still to come."""
    rows = session.execute(
        select(SourceAllowanceUse.source_name, SourceAllowanceUse.paused_until).where(
            SourceAllowanceUse.paused_until > now
        )
    )
    return {name: until for name, until in rows if until is not None}


@dataclass(frozen=True, slots=True)
class Stored:
    """What the view asks the database for each time it draws."""

    paused: dict[str, datetime]
    spent_usd: Decimal


def _days(moment: datetime) -> list[date]:
    # Yesterday too, so the widest window reaches back across midnight.
    return [moment.date() - timedelta(days=1), moment.date()]


def watch(
    folder: Path,
    *,
    stored: Callable[[datetime], Stored],
    ceiling_usd: Decimal,
    draw: Callable[[LiveView], None],
    now: Callable[[], datetime],
    sleep: Callable[[float], None],
    once: bool,
) -> None:
    """Read the day's files from where it last read, and draw the view every
    `REDRAW_SECONDS`, or once."""
    follower = Follower(folder)
    first = now()
    held: list[Line] = follower.read(_days(first))
    if not any(isinstance(line, Event) and line.kind == RUN_ENDED for line in held):
        # The last run may have ended days ago: its ending is still shown.
        earlier = last_event(folder, RUN_ENDED, before=_days(first)[0])
        if earlier is not None:
            held.append(earlier)
    while True:
        moment = now()
        held = kept([*held, *follower.read(_days(moment))], moment)
        asked = stored(moment)
        draw(
            view_of(
                held,
                moment,
                paused=asked.paused,
                spent_usd=asked.spent_usd,
                ceiling_usd=ceiling_usd,
                unreadable=follower.unreadable,
            )
        )
        if once:
            return
        sleep(REDRAW_SECONDS)
