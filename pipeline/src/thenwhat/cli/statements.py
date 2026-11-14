"""The statements command: reported statements for claims already decided."""

import sys
from datetime import UTC, datetime
from typing import Annotated

import typer

from thenwhat.claims.entry import EntryError, claim_by_slug
from thenwhat.cli import extract
from thenwhat.cli.console import err, out
from thenwhat.cli.entry import entry_session
from thenwhat.db.models import SourceArticle
from thenwhat.extract.retrieve import PasteNeeded
from thenwhat.llm.errors import BudgetExceeded, LlmError, LlmNotConfigured
from thenwhat.statements.service import (
    articles_to_read,
    claims_missing_statements,
    read_again,
)


def statements_command(
    slugs: Annotated[list[str] | None, typer.Argument(help="Slugs of the claims.")] = None,
    missing: Annotated[
        bool,
        typer.Option(
            "--missing", help="Every published claim with an article that has no statement."
        ),
    ] = False,
    again: Annotated[
        bool,
        typer.Option(
            "--again",
            help="Read articles that already have statements again. Pending ones are"
            " replaced; approved and rejected ones stay.",
        ),
    ] = False,
    article_url: Annotated[
        str | None, typer.Option(help="Only this one of the claim's articles.")
    ] = None,
    paste: Annotated[
        bool,
        typer.Option(
            "--paste", help="Read the article's text from standard input instead of fetching it."
        ),
    ] = False,
) -> None:
    """Read the articles of decided claims again, for reported statements only.

    Each article is read under the same robots, archived-copy and pasted-text rules as a
    first read, and its text is kept nowhere. Statements are refused by rule when they
    copy the article, quote or name someone, then checked against the article: one
    checked with a high probability is approved by rule and published, the rest wait in
    review. Nothing else about the claim changes, and an article that already has
    statements is skipped unless --again is given.
    """
    if not slugs and not missing:
        err.print("Name the claims, or use --missing for every claim without statements.")
        raise typer.Exit(code=1)
    if again and not slugs:
        err.print("--again reads the named claims' articles again. Name the claims.")
        raise typer.Exit(code=1)
    if paste and (not slugs or len(slugs) != 1):
        err.print("--paste gives the text of one article. Name exactly one claim.")
        raise typer.Exit(code=1)

    problems = 0
    with entry_session() as session:
        claims = [claim_by_slug(session, slug) for slug in slugs] if slugs else []
        if missing:
            claims += [c for c in claims_missing_statements(session) if c not in claims]
        articles = articles_to_read(session, claims, again=again)
        if article_url is not None:
            articles = [a for a in articles if a.url == article_url]
        if paste and len(articles) > 1:
            raise EntryError("The claim has several articles. Name one with --article-url.")
        if not articles:
            out.print(
                "Every article named already has reported statements."
                " Use --again to read one again."
            )
            return
        slug_of = {claim.id: claim.slug for claim in claims}
        llm = extract.make_llm(session)
        checker = extract.make_checker(session)
        retriever = None if paste else extract.make_retriever()
        for article in articles:
            slug = slug_of[article.claim_id]
            out.print(f"{slug}  {article.outlet}  {article.published_date}", markup=False)
            if retriever is None:
                text = sys.stdin.read().strip()
                if not text:
                    raise EntryError("No article text arrived on standard input.")
            else:
                try:
                    text = retriever.retrieve(article.url).text
                except PasteNeeded as needed:
                    problems += 1
                    err.print(f"  {_paste_needed(slug, article, str(needed))}", markup=False)
                    continue
            try:
                reread = read_again(
                    session, llm, checker, article=article, text=text, now=datetime.now(UTC)
                )
            except LlmError as error:
                problems += 1
                err.print(f"  No reported statement was proposed: {error}", markup=False)
                if isinstance(error, (BudgetExceeded, LlmNotConfigured)):
                    break
                continue
            for line in extract.statement_lines(reread.run):
                out.print(f"  {line}", markup=False)
            if reread.changed:
                out.print(
                    "  The text read now does not match the text first read, by its stored"
                    " hash: the article has changed since it was first read. The statements"
                    " are of the article as read today.",
                    markup=False,
                )
            unchecked = extract.unchecked_line(reread.run, slug)
            if unchecked:
                problems += 1
                err.print(f"  {unchecked}", markup=False)
    if problems:
        # Raised once the session has committed what was stored and logged.
        raise typer.Exit(code=1)


def _paste_needed(slug: str, article: SourceArticle, reason: str) -> str:
    return (
        f"{reason} Pasted text is needed: run `thenwhat statements {slug} --article-url"
        f" {article.url} --paste` with the article's text on standard input."
    )
