"""Commands for clinical categories: reading the MeSH tree they need, and the reports
that compare them with how claims are filed. Behavior: openspec clinical-classification."""

from typing import Annotated

import typer
from sqlalchemy.orm import Session

from thenwhat.claims.entry import EntryError, claim_by_slug, unarchived_claims
from thenwhat.claims.verticals import VERTICALS
from thenwhat.cli.console import out
from thenwhat.cli.entry import entry_session
from thenwhat.cli.session import settings_or_exit
from thenwhat.clinical.service import (
    MeshSource,
    clinical_of,
    compare,
    coverage,
    read_tree,
    stored_vocabulary,
)
from thenwhat.clinical.topics import configuration_problems
from thenwhat.clinical.vocabulary import Vocabulary
from thenwhat.export.records import PostgresRecords
from thenwhat.sources.mesh import Mesh

clinical_app = typer.Typer(
    help="Clinical categories (MeSH) of claims, and how they compare with their verticals.",
    no_args_is_help=True,
)

TREE_FIRST = "Run `thenwhat clinical tree` first."


def make_mesh(session: Session) -> MeshSource:
    return Mesh(session, contact_email=settings_or_exit().contact_email)


def _count(number: int, noun: str) -> str:
    return f"{number:,} {noun}" if number == 1 else f"{number:,} {noun}s"


def _categories(number: int) -> str:
    return "1 clinical category" if number == 1 else f"{number:,} clinical categories"


def _mapped_vocabulary(session: Session) -> Vocabulary:
    """The stored vocabulary, refused while it lacks a descriptor the topic mapping names."""
    vocabulary = stored_vocabulary(PostgresRecords(session))
    problems = configuration_problems(vocabulary)
    if problems:
        raise EntryError("\n".join([*problems, TREE_FIRST]))
    return vocabulary


@clinical_app.command("tree")
def tree_command(
    slugs: Annotated[
        list[str] | None, typer.Argument(help="Slugs of the claims. Every claim if none.")
    ] = None,
) -> None:
    """Read the MeSH records that claims' clinical categories need.

    For each category a claim's approved trials and papers give it, each descriptor the
    topic mapping names, and every descriptor broader than those, the record is read
    from NLM's MeSH service and stored. A record already stored is not asked for again
    within the year's vocabulary; in a new year each one in use is read again, and one
    the year no longer holds keeps its last record and says the year it was read from.
    """
    with entry_session() as session:
        claims = (
            [claim_by_slug(session, slug) for slug in slugs]
            if slugs
            else unarchived_claims(session)
        )
        run = read_tree(session, make_mesh(session), claims)
        vocabulary = stored_vocabulary(PostgresRecords(session))
        years = ", ".join(vocabulary.years()) or "none"
        out.print(
            f"Read {_count(run.read, 'MeSH record')} for {_count(len(claims), 'claim')}."
            f" {_count(len(vocabulary), 'descriptor')} stored, of MeSH {years}.",
            markup=False,
        )
        if run.unknown_headings:
            out.print(
                f"{_count(len(run.unknown_headings), 'paper heading')} no descriptor is labelled"
                " as, so never a category:",
                markup=False,
            )
            for heading in run.unknown_headings:
                out.print(f"  {heading}", markup=False)
        if run.retired:
            listed = ", ".join(
                f"{one} (last read from MeSH {run.retired_years[one]})"
                if one in run.retired_years
                else one
                for one in run.retired
            )
            out.print(
                f"{_count(len(run.retired), 'descriptor')} the vocabulary no longer holds:"
                f" {listed}",
                markup=False,
            )
        for problem in configuration_problems(vocabulary):
            out.print(problem, markup=False)


@clinical_app.command("categories")
def categories_command(
    slug: Annotated[
        str | None, typer.Argument(help="A claim, to list its categories and their sources.")
    ] = None,
) -> None:
    """Say how many claims have a clinical category and from what, or list one claim's.

    Categories are derived from the claim's approved trial records and its papers' index
    records each time; nothing is stored, and nothing is changed here.
    """
    with entry_session() as session:
        records = PostgresRecords(session)
        vocabulary = stored_vocabulary(records)
        if slug is not None:
            claim = claim_by_slug(session, slug)
            placed = clinical_of(records, claim, vocabulary)
            if not placed.read:
                out.print(
                    f"{claim.slug}: not yet read. {TREE_FIRST}"
                    f" Missing: {', '.join([*placed.missing, *placed.derived.unread_headings])}",
                    markup=False,
                )
                return
            out.print(f"{claim.slug}: {_categories(len(placed.categories))}", markup=False)
            for category in placed.categories:
                sources = ", ".join(
                    f"its own condition, read at {s.score:.2f}"
                    if s.kind == "term" and s.score is not None
                    else "its own condition"
                    if s.kind == "term"
                    else f"{s.kind} {s.identifier}"
                    for s in category.sources
                )
                out.print(f"  {category.label} ({category.identifier}): {sources}", markup=False)
            return
        claims = unarchived_claims(session)
        counted = coverage(records, claims, vocabulary)
        out.print(
            f"{_count(len(claims), 'claim')}: {counted.from_trials:,} with a category from a"
            f" trial, {counted.from_papers_only:,} from papers only,"
            f" {counted.from_term_only:,} only from the reading of their own condition,"
            f" {counted.none:,} with none, {counted.not_read:,} not yet read.",
            markup=False,
        )
        if counted.not_read:
            out.print(TREE_FIRST, markup=False)


@clinical_app.command("compare")
def compare_command(
    disagreeing: Annotated[
        bool, typer.Option("--disagreeing", help="List each claim whose topics disagree.")
    ] = False,
    tsv: Annotated[
        bool, typer.Option("--tsv", help="Only the disagreeing claims, as tab-separated rows.")
    ] = False,
    show_uncovered: Annotated[
        bool, typer.Option("--uncovered", help="List the categories no topic covers.")
    ] = False,
) -> None:
    """Compare the topics derived from claims' clinical categories with their verticals.

    A claim agrees when one of its derived topics is in the group of the vertical it is
    filed under. Nothing is changed: a vertical is only ever changed by the operator.
    """
    with entry_session() as session:
        vocabulary = _mapped_vocabulary(session)
        result = compare(session, unarchived_claims(session), vocabulary)
        rows = sorted(result.disagreeing, key=lambda row: row.slug)
        if tsv:
            for row in rows:
                # Not through the console, which would turn the tabs into spaces.
                typer.echo(
                    "\t".join(
                        [
                            row.slug,
                            row.intervention,
                            row.indication,
                            row.vertical,
                            "; ".join(topic.topic for topic in row.topics),
                            "; ".join(f"{c.label} ({c.identifier})" for c in row.categories),
                        ]
                    )
                )
            return
        out.print(
            f"{_count(result.claims, 'claim')}: {result.agrees:,} filed under a group their"
            f" categories derive, {len(rows):,} under another group."
            f" Nothing to compare: {result.no_category:,} with no category,"
            f" {result.no_topic:,} whose categories no topic covers,"
            f" {result.not_read:,} not yet read.",
            markup=False,
        )
        out.print(
            f"{result.several_topics:,} fall under more than one topic."
            f" {result.agrees_by_term_only:,} of those that agree rest only on the reading"
            " of the claim's own condition.",
            markup=False,
        )
        for topic, title in VERTICALS.items():
            if topic in result.per_topic:
                out.print(f"  {title}: {result.per_topic[topic]:,}", markup=False)
        if rows and not disagreeing:
            out.print("--disagreeing lists them; --tsv gives rows for the fault tab.", markup=False)
        if not rows:
            out.print("No claim is filed under a group its categories do not derive.", markup=False)
        if disagreeing:
            for row in rows:
                topics = "; ".join(
                    f"{VERTICALS[topic.topic]} (MeSH: {_label(vocabulary, topic.category)})"
                    for topic in row.topics
                )
                out.print(
                    f"  {row.slug}: filed under {VERTICALS.get(row.vertical, row.vertical)};"
                    f" its categories derive {topics}",
                    markup=False,
                )
        if show_uncovered:
            listed = sorted(result.uncovered.items(), key=lambda item: (-item[1], item[0]))
            out.print(f"{_categories(len(listed))} no topic covers:", markup=False)
            for (label, identifier), claims in listed:
                out.print(f"  {label} ({identifier}): {_count(claims, 'claim')}", markup=False)


def _label(vocabulary: Vocabulary, identifier: str) -> str:
    held = vocabulary.get(identifier)
    return held.label if held and held.label else identifier
