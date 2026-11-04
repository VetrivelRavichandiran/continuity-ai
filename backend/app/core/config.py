"""Application configuration (pydantic-settings)."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Storage
    DATA_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent / "data"

    # Upload limits
    MAX_FILE_MB: int = 15
    MAX_FILES_PER_UPLOAD: int = 20
    ALLOWED_EXTENSIONS: tuple[str, ...] = (".pdf", ".docx", ".txt", ".md")

    # Retrieval
    ASK_TOP_CHUNKS: int = 6
    ASK_TOP_KNOWLEDGE: int = 4
    ASK_MIN_SCORE: float = 0.05

    @property
    def files_dir(self) -> Path:
        return self.DATA_DIR / "files"

    @property
    def db_path(self) -> Path:
        return self.DATA_DIR / "continuity.db"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.DATA_DIR.mkdir(parents=True, exist_ok=True)
    s.files_dir.mkdir(parents=True, exist_ok=True)
    return s