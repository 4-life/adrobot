from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Every setting, read from the environment / `.env` (field name upper-cased)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # The tracker adapter (app/tracker/factory.py). "fake": in-memory sample data, for local
    # testing without Keitaro (app/tracker/fake/adapter.py).
    tracker: Literal["keitaro", "fake"] = "keitaro"

    # Keitaro Admin API: base URL without a path (the client adds /admin_api/v1).
    keitaro_url: str = ""
    keitaro_api_key: str = ""
    keitaro_timeout_seconds: float = 30.0

    # Campaign defaults (docs/DESIGN.md: Creating a Campaign).
    geo_redirect_url: str = "https://google.com"
    default_geo: str = "AU"
    # MVP only (empty in production): the default name of new campaigns (prefix + N), the
    # campaigns table's default search, and whose streams Fetch streams reads. Empty: no
    # default name, no default search, and Fetch streams reads the campaign list only.
    campaign_name_prefix: str = ""

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
