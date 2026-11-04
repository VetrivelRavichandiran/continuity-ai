from fastapi import APIRouter

from app.core.config import get_settings
from app.core.security import is_ai_configured
from app.schemas.settings import SettingsOut

router = APIRouter(prefix="/api/settings", tags=["settings"])

DATA_DISCLOSURE = (
    "Document text is sent to the configured LLM provider for extraction and "
    "question answering when an API key is configured. With no key, a "
    "deterministic local extractor is used and no text leaves this machine."
)


@router.get("", response_model=SettingsOut)
def get_settings_endpoint():
    s = get_settings()
    return SettingsOut(
        ai_configured=is_ai_configured(),
        ai_provider="gemini",
        ai_model=s.GEMINI_MODEL,
        allowed_extensions=list(s.ALLOWED_EXTENSIONS),
        max_file_mb=s.MAX_FILE_MB,
        max_files_per_upload=s.MAX_FILES_PER_UPLOAD,
        data_disclosure=DATA_DISCLOSURE,
    )