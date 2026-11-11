"""Settings read from the environment. Nothing here has a secret default."""

from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Empty variables, as in a freshly copied .env, count as not set.
    model_config = SettingsConfigDict(extra="ignore", env_ignore_empty=True)

    database_url: str
    # Sent in the User-Agent of every registry request. No request is sent without it.
    contact_email: str | None = None

    # Language model: provider and model as "provider:model". No default on purpose.
    llm_model: str | None = None
    llm_monthly_budget_usd: Decimal = Decimal("13")
    llm_input_usd_per_mtok: Decimal | None = None
    llm_output_usd_per_mtok: Decimal | None = None

    review_confidence_threshold: float = 0.95
    no_signal_years: int = 3


def load_settings() -> Settings:
    return Settings()
