"""Settings read from the environment. Nothing here has a secret default."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str


def load_settings() -> Settings:
    return Settings()
