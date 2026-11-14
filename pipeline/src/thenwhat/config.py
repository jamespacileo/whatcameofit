"""Settings read from the environment. Nothing here has a secret default."""

from decimal import Decimal

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class SourceAllowance(BaseModel):
    """How many requests a source may receive in a period, and how far apart."""

    requests: int
    period_hours: float
    interval_seconds: float
    # How long to stop asking after the source says "too many requests" without
    # saying for how long.
    pause_minutes: float = 60


# At or below what each source publishes (docs/sources.md). SOURCE_ALLOWANCES in the
# environment replaces or adds entries by source name.
DEFAULT_ALLOWANCES = {
    "clinicaltrials.gov": SourceAllowance(requests=5000, period_hours=24, interval_seconds=0.5),
    "mediacloud": SourceAllowance(requests=4000, period_hours=168, interval_seconds=30),
}


class Settings(BaseSettings):
    # Empty variables, as in a freshly copied .env, count as not set.
    model_config = SettingsConfigDict(extra="ignore", env_ignore_empty=True)

    database_url: str
    # Sent in the User-Agent of every registry request. No request is sent without it.
    contact_email: str | None = None

    # OpenAlex's free key, for the literature search. Empty turns paper search off and
    # leaves the rest of resolution as it is.
    openalex_api_key: str | None = None

    # Language model: provider and model as "provider:model". No default on purpose.
    llm_model: str | None = None
    llm_monthly_budget_usd: Decimal = Decimal("13")
    llm_input_usd_per_mtok: Decimal | None = None
    llm_output_usd_per_mtok: Decimal | None = None

    # Which backend answers bounded decisions: "llm" or "openai-decisions".
    decision_backend: str = "llm"
    # For "openai-decisions": the model by the provider's own name (when empty, the
    # model of LLM_MODEL if that is an OpenAI one) and its price per million input tokens.
    decisions_model: str | None = None
    decisions_input_usd_per_mtok: Decimal | None = None

    review_confidence_threshold: float = 0.95
    # A new candidate match scored under this is rejected by rule instead of waiting
    # for review. It is kept and can be listed and approved. 0 turns the rule off.
    match_reject_below: float = 0.05
    # A new trial candidate scored for the claim's indication at or above this is
    # approved by rule and published. The default is where the site's "High match" band
    # starts. 0 turns the rule off (openspec auto-publish).
    # A related paper scored at or above it is approved by rule too (openspec
    # related-research), and one scored under `match_reject_below` is rejected.
    match_accept_above: float = 0.8
    # How many candidate subject terms are kept for a claim (openspec knowledge-cards).
    term_candidates_max: int = 10
    # How many genes named in a claim's intervention are kept as candidate targets.
    target_candidates_max: int = 3
    # Reported statements (openspec reported-statements). A statement the statement check
    # gives this probability or more that its article says it is approved by rule and
    # published; one below it waits, unpublished. 0 turns the rule off.
    statement_accept_above: float = 0.8
    # The most reported statements kept for one article.
    statements_per_article: int = 6
    # A proposed statement sharing this many consecutive words with its article is
    # refused as copied.
    statement_copied_run: int = 8
    # Decide new drafts by rule: approved, and published, when the intervention is a
    # name; rejected and kept otherwise. On by default: approval needs no person
    # (openspec auto-publish).
    approve_drafts_by_rule: bool = True
    no_signal_years: int = 3
    # A stored paper record older than this is asked for again at fetch; a younger one
    # causes no request (openspec paper-facts).
    paper_record_max_age_days: int = 30

    # Backfill (openspec work-ledger, source-allowances, article-leads).
    # JSON by source name, for example
    # {"mediacloud": {"requests": 4000, "period_hours": 168, "interval_seconds": 30}}.
    source_allowances: dict[str, SourceAllowance] = {}
    # A record that failed this many times is skipped and reported.
    backfill_attempt_limit: int = 3
    # Media Cloud key, and the collections and single outlets to search, as
    # comma-separated ids from its directory. The news search refuses to run while the
    # key is empty or while neither list names anything.
    mediacloud_api_key: str | None = None
    mediacloud_collection_ids: str = ""
    mediacloud_source_ids: str = ""
    # At most this many article leads are kept for one trial.
    leads_per_trial: int = 20

    # Link leads (openspec link-leads). The Reddit communities whose submissions are
    # loaded, separated by commas, without "r/". A Reddit load refuses while it is empty.
    link_lead_subreddits: str = ""

    # At most this many stored claims and registry trials are linked to one link lead
    # by screening (openspec lead-screening).
    lead_links_max: int = 10

    # Triage (openspec lead-triage): a link lead scored at or above the first is passed
    # and may be read; one scored below the second is rejected and kept; between them it
    # is held. No default on purpose: the operator sets both from the evaluation report,
    # and until then nothing is passed.
    lead_pass_above: float | None = None
    lead_reject_below: float | None = None

    def chosen_subreddits(self) -> frozenset[str]:
        return frozenset(
            name.strip().removeprefix("r/")
            for name in self.link_lead_subreddits.split(",")
            if name.strip()
        )

    def allowances(self) -> dict[str, SourceAllowance]:
        return {**DEFAULT_ALLOWANCES, **self.source_allowances}


def load_settings() -> Settings:
    return Settings()
