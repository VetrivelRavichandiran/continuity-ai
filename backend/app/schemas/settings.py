from pydantic import BaseModel


class SettingsOut(BaseModel):
    ai_configured: bool
    ai_provider: str
    ai_model: str
    allowed_extensions: list[str]
    max_file_mb: int
    max_files_per_upload: int
    data_disclosure: str