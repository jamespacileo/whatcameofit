"""Settings read from the environment. Nothing here has a secret default."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str
    # Sent in the User-Agent of every registry request. No request is sent without it.
    contact_email: str | None = None


def load_settings() -> Settings:
    return Settings()
