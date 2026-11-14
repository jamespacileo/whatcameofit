"""Settings read from the environment. Nothing here has a secret default."""

from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    # Decide new drafts by rule: approved, and published, when the intervention is a
    # name; rejected and kept otherwise. On by default: approval needs no person
    # (openspec auto-publish).
    approve_drafts_by_rule: bool = True
    no_signal_years: int = 3
    # A stored paper record older than this is asked for again at fetch; a younger one
    # causes no request (openspec paper-facts).
    paper_record_max_age_days: int = 30


def load_settings() -> Settings:
    return Settings()
