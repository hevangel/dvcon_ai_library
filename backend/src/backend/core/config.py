from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_repo_root() / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "DVCon Proceedings Intelligence Portal"
    api_prefix: str = "/api"
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
    )

    openai_base_url: str | None = None
    openai_api_key: str | None = None
    openai_chat_model: str = "gpt-5-mini"

    grobid_enabled: bool = True
    grobid_url: str = "http://127.0.0.1:8070"
    grobid_timeout_seconds: int = 180

    local_embedding_model: str = "BAAI/bge-m3"
    local_embedding_device: str = "cuda"
    local_embedding_batch_size: int = 16

    chunk_size: int = 1400
    chunk_overlap: int = 200
    max_search_results: int = 50
    data_dir_name: str = Field(default="data", alias="DATA_DIR")

    repo_root: Path = Field(default_factory=_repo_root)

    @property
    def paper_dir(self) -> Path:
        return self.data_dir / "paper"

    @property
    def data_dir(self) -> Path:
        return self.repo_root / self.data_dir_name

    @property
    def markdown_dir(self) -> Path:
        return self.data_dir / "markdown"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def tei_dir(self) -> Path:
        return self.data_dir / "tei"

    @property
    def model_cache_dir(self) -> Path:
        return self.data_dir / "models"

    @property
    def manifest_path(self) -> Path:
        return self.data_dir / "ingest_manifest.json"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "dvcon.db"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path.as_posix()}"

    @property
    def frontend_dist_dir(self) -> Path:
        return self.repo_root / "frontend" / "dist"

    @property
    def chat_is_configured(self) -> bool:
        return bool(self.openai_api_key and self.openai_base_url)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.paper_dir.mkdir(parents=True, exist_ok=True)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.markdown_dir.mkdir(parents=True, exist_ok=True)
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    settings.tei_dir.mkdir(parents=True, exist_ok=True)
    settings.model_cache_dir.mkdir(parents=True, exist_ok=True)
    return settings
