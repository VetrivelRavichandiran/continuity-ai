"""API key handling. The key is read only from the environment (or .env via
pydantic-settings, which itself reads env vars first)."""
from app.core.config import get_settings


def get_api_key() -> str | None:
    return get_settings().GEMINI_API_KEY or None


def is_ai_configured() -> bool:
    return bool(get_settings().GEMINI_API_KEY)