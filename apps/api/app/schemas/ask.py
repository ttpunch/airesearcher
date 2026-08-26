from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str


class CitationOut(BaseModel):
    chunk_id: int
    content: str
    source_name: str
    source_url: str
    source_tier: str
    document_id: int


class AskResponseOut(BaseModel):
    answer: str
    citations: list[CitationOut]
    unverifiable_citation_count: int
    verified: bool = Field(
        description=(
            "True only when every citation in the answer was successfully grounded "
            "(unverifiable_citation_count == 0 and at least one citation exists). An "
            "answer with zero citations — e.g. 'I cannot verify this from public "
            "sources' — is not verified, it's honestly uncertain, not confirmed false."
        )
    )
