from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # SQLite by default for zero-setup local dev; set DATABASE_URL to Postgres/Neon in prod.
    database_url: str = "sqlite:///./jobify.db"
    api_cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    remotive_enabled: bool = True
    upload_dir: str = "uploads"
    # Optional keys improve live learning lookups (all work without them via free APIs).
    youtube_api_key: str = ""
    google_books_api_key: str = ""
    github_token: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
