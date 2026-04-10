from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR.parent / ".env"


class Settings(BaseSettings):
    APP_NAME: str = "ONRE Incident Triage Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/db/onre.db"
    openai_api_key: str
    openai_model: str = "gpt-4.1-mini"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    RETRIEVAL_TOP_K: int = 3
    taxonomy_path: Path = BASE_DIR / "taxonomy" / "taxonomy.yaml"
    INCIDENTS_PATH: Path = BASE_DIR / "db" / "incidents.json"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def normalize_debug(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"debug", "dev", "development"}:
                return True
            if normalized in {"release", "prod", "production"}:
                return False
        return value

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",  # or "forbid" if you want strictness later
    )


settings = Settings()
