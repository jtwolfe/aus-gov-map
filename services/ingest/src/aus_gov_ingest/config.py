from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "data" / "fixtures" / "seed.json").exists():
            return parent
        if (parent / "docker-compose.yml").exists():
            return parent
    return Path.cwd()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_repo_root() / ".env", Path.cwd() / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str | None = None
    neo4j_uri: str | None = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "ausgovmap"

    embedding_provider: str = "hash"
    embedding_dim: int = 384
    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    st_embedding_model: str = "all-MiniLM-L6-v2"

    aus_gov_fixture_path: str | None = None
    ingest_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    )
    ingest_timeout_seconds: float = 45
    ingest_rate_limit_seconds: float = 0.6
    ingest_max_retries: int = 3
    ingest_include_transcripts: bool = True
    ingest_fallback_fixture: bool = True

    def fixture_path(self) -> Path:
        if self.aus_gov_fixture_path:
            return Path(self.aus_gov_fixture_path)
        bundled = Path(__file__).resolve().parents[2] / "fixtures" / "seed.json"
        repo = _repo_root() / "data" / "fixtures" / "seed.json"
        for candidate in (repo, bundled):
            if candidate.exists():
                return candidate
        return repo


settings = Settings()
