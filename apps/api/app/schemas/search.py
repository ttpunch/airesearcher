from pydantic import BaseModel


class CitationRead(BaseModel):
    source_id: int
    source_name: str
    source_url: str
    source_tier: str
    document_id: int
    document_url: str | None


class SearchResultRead(BaseModel):
    chunk_id: int
    chunk_index: int
    content: str
    vector_score: float
    text_score: float
    hybrid_score: float
    citation: CitationRead
