from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_prefix="READMASTER_",
        extra="ignore",
    )

    app_name: str = "ReadMaster API"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    data_dir: Path = PROJECT_ROOT / "data"
    database_url: str | None = None
    frontend_origin: str = "http://localhost:5173"

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite+pysqlite:///{(self.data_dir / 'readmaster.db').as_posix()}"

    @property
    def dictionary_database_path(self) -> Path:
        return self.data_dir / "dictionaries" / "ecdict.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
