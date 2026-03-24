from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env", override=False)


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


def _default_provider() -> str:
    explicit_provider = os.getenv("MODEL_PROVIDER")
    if explicit_provider in {"gemini", "openai"}:
        return explicit_provider
    if os.getenv("GOOGLE_API_KEY"):
        return "gemini"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    return "gemini"


@dataclass(frozen=True)
class Settings:
    root_dir: Path
    project_name: str
    active_plugin: str
    model_provider: str
    openai_api_key: str | None
    openai_base_url: str | None
    openai_chat_model: str
    openai_embedding_model: str
    google_api_key: str | None
    gemini_chat_model: str
    gemini_embedding_model: str
    timezone: str
    max_recent_sessions: int
    retrieval_k: int
    data_dir: Path
    docs_dir: Path
    notes_dir: Path
    memory_dir: Path
    vector_store_dir: Path

    @property
    def notes_file(self) -> Path:
        return self.notes_dir / "notes.md"

    @property
    def memory_file(self) -> Path:
        return self.memory_dir / "conversations.json"

    @property
    def vector_manifest_file(self) -> Path:
        return self.vector_store_dir / "manifest.json"

    @property
    def active_chat_model(self) -> str:
        if self.model_provider == "gemini":
            return self.gemini_chat_model
        return self.openai_chat_model

    @property
    def active_embedding_model(self) -> str:
        if self.model_provider == "gemini":
            return self.gemini_embedding_model
        return self.openai_embedding_model

    @property
    def has_model_credentials(self) -> bool:
        if self.model_provider == "gemini":
            return bool(self.google_api_key)
        return bool(self.openai_api_key)


def ensure_directories(settings: Settings) -> None:
    for path in (
        settings.data_dir,
        settings.docs_dir,
        settings.notes_dir,
        settings.memory_dir,
        settings.vector_store_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings(
        root_dir=ROOT_DIR,
        project_name="Pluggable Executive Assistant",
        active_plugin=os.getenv("ACTIVE_PLUGIN", "personal"),
        model_provider=_default_provider(),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_base_url=os.getenv("OPENAI_BASE_URL"),
        openai_chat_model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4.1-mini"),
        openai_embedding_model=os.getenv(
            "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
        ),
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        gemini_chat_model=os.getenv("GEMINI_CHAT_MODEL", "gemini-2.5-flash"),
        gemini_embedding_model=os.getenv(
            "GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"
        ),
        timezone=os.getenv("APP_TIMEZONE", "America/Toronto"),
        max_recent_sessions=_env_int("MAX_RECENT_SESSIONS", 3),
        retrieval_k=_env_int("RETRIEVAL_K", 4),
        data_dir=ROOT_DIR / "data",
        docs_dir=ROOT_DIR / "data" / "docs",
        notes_dir=ROOT_DIR / "data" / "notes",
        memory_dir=ROOT_DIR / "data" / "memory",
        vector_store_dir=ROOT_DIR / "data" / "vector_store",
    )
    ensure_directories(settings)
    return settings
