"""Commands that draft claims from news articles."""

import sys
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated

import typer
from sqlalchemy.orm import Session

from thenwhat.claims.entry import EntryError
from thenwhat.cli.console import out
from thenwhat.cli.entry import DATE_FORMATS, entry_session
from thenwhat.cli.session import settings_or_exit
from thenwhat.domain import ReviewState
from thenwhat.extract.retrieve import ArticleRetriever, PasteNeeded, Retrieved

if TYPE_CHECKING:
    from thenwhat.llm.client import Llm

extract_app = typer.Typer(help="Draft claims from news articles.", no_args_is_help=True)

PASTE_HELP = "Read the article text from standard input instead of fetching it."


def make_llm(session: Session) -> "Llm":
    # Imported here: the model library is slow to load and most commands never need it.
    from thenwhat.llm.client import Llm, LlmSettings

    settings = settings_or_exit()
    return Llm(
        session,
        LlmSettings(
            model=settings.llm_model,
            monthly_budget_usd=settings.llm_monthly_budget_usd,
            input_usd_per_mtok=settings.llm_input_usd_per_mtok,
            output_usd_per_mtok=settings.llm_output_usd_per_mtok,
        ),
    )


def make_retriever() -> ArticleRetriever:
    return ArticleRetriever(contact_email=settings_or_exit().contact_email)


def _article_text(url: str, paste: bool) -> Retrieved:
    """The article's text for this run only. It is never stored."""
    if paste:
        text = sys.stdin.read().strip()
        if not text:
            raise EntryError("No article text arrived on standard input.")
        return Retrieved(text)
    try:
        return make_retriever().retrieve(url)
    except PasteNeeded as needed:
        raise EntryError(
            f"{needed} Run the command again with --paste and pipe the text in."
        ) from None


@extract_app.command("new")
def extract_new(
    url: Annotated[str, typer.Argument(help="Address of the news article.")],
    slug: Annotated[str, typer.Option(help="Short, guessable page address for the claim.")],
    vertical: Annotated[str, typer.Option(help="Topic area, for example mouth-and-teeth.")],
    outlet: Annotated[str, typer.Option(help="Publication that ran the article.")],
    title: Annotated[str, typer.Option(help="Article title.")],
    published: Annotated[
        datetime, typer.Option(formats=DATE_FORMATS, help="Publication date, YYYY-MM-DD.")
    ],
    paste: Annotated[bool, typer.Option("--paste", help=PASTE_HELP)] = False,
) -> None:
    """Draft a new claim from an article. The draft stays pending until you approve it."""
    from thenwhat.extract.service import draft_claim_from_article

    by_rule = settings_or_exit().approve_drafts_by_rule
    with entry_session() as session:
        article = _article_text(url, paste)
        claim = draft_claim_from_article(
            session,
            make_llm(session),
            text=article.text,
            archive_url=article.archive_url,
            slug=slug,
            vertical=vertical,
            url=url,
            outlet=outlet,
            title=title,
            published_date=published.date(),
            decide_by_rule_at=datetime.now(UTC) if by_rule else None,
        )
        out.print(f"Drafted claim {claim.slug}: {claim.headline}", markup=False)
        if claim.review_state is ReviewState.APPROVED:
            out.print("Approved by rule: it is published with the next export.")
        elif claim.review_state is ReviewState.REJECTED:
            out.print(
                "Rejected by rule: the intervention it names is not a name. Correct it with"
                " `claim edit`, then approve it in review."
            )
        else:
            out.print("It is pending. Correct it with `claim edit`, then approve it in review.")


@extract_app.command("article")
def extract_article(
    claim_slug: Annotated[str, typer.Argument(help="Slug of a claim that is still pending.")],
    article_url: Annotated[str, typer.Option(help="One of the claim's articles.")],
    paste: Annotated[bool, typer.Option("--paste", help=PASTE_HELP)] = False,
) -> None:
    """Add what one of a claim's articles says: entities, the paper, promises."""
    from thenwhat.extract.service import extract_into_claim

    with entry_session() as session:
        article = _article_text(article_url, paste)
        claim = extract_into_claim(
            session,
            make_llm(session),
            claim_slug=claim_slug,
            article_url=article_url,
            text=article.text,
            archive_url=article.archive_url,
        )
        out.print(f"Added details from the article to {claim.slug}.", markup=False)
