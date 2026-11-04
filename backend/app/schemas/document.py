from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: int
    project_id: int
    file_name: str
    file_type: str
    size_bytes: int
    status: str
    error: str | None = None
    page_count: int | None = None
    chunk_count: int
    uploaded_at: str
    processed_at: str | None = None


class ChunkOut(BaseModel):
    id: int
    page: int | None = None
    text: str


class DocumentPreviewOut(BaseModel):
    document: DocumentOut
    text: str
    chunks: list[ChunkOut]