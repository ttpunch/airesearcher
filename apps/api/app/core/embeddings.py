"""Embedding providers.

VoyageEmbeddingProvider is the real one — Voyage AI is Anthropic's
recommended embeddings provider, and this project standardizes on it (see
docs/research/bhel-ai-strategy.html §18). It's a genuine HTTP client, unit
tested against httpx.MockTransport (same technique as app/crawler/) since
this project's dev sandbox cannot reach api.voyageai.com and has no key
configured — not simulated by skipping the real request-building/
response-parsing code.

LocalHashEmbeddingProvider is NOT semantically meaningful — it maps text
to a deterministic vector via hashing, purely so the chunking -> embedding
-> storage -> hybrid-search pipeline is mechanically runnable and testable
end-to-end without a Voyage API key. It exists to keep local dev/CI/this
sandbox unblocked, not as a real search backend — get_embedding_provider()
only falls back to it when VOYAGE_API_KEY is unset, and that should never
be true in a real deployment.
"""

import hashlib
from typing import Protocol

import httpx

from app.core.config import settings


class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class VoyageEmbeddingProvider:
    def __init__(self, api_key: str, model: str | None = None, client: httpx.AsyncClient | None = None):
        self._api_key = api_key
        self._model = model or settings.voyage_model
        self._client = client or httpx.AsyncClient(base_url="https://api.voyageai.com/v1")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = await self._client.post(
            "/embeddings",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"input": texts, "model": self._model},
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
        # Voyage returns `data` sorted by `index`; sort explicitly rather
        # than trusting response order, since callers zip results
        # positionally against their input texts.
        ordered = sorted(payload["data"], key=lambda item: item["index"])
        return [item["embedding"] for item in ordered]


class LocalHashEmbeddingProvider:
    """Deterministic, non-semantic fallback — see module docstring."""

    def __init__(self, dim: int | None = None):
        self._dim = dim or settings.embedding_dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        values: list[float] = []
        counter = 0
        seed = text.encode("utf-8")
        while len(values) < self._dim:
            digest = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
            values.extend(b / 255.0 - 0.5 for b in digest)
            counter += 1
        vector = values[: self._dim]
        norm = sum(v * v for v in vector) ** 0.5 or 1.0
        return [v / norm for v in vector]


def get_embedding_provider() -> EmbeddingProvider:
    if settings.voyage_api_key:
        return VoyageEmbeddingProvider(settings.voyage_api_key)
    return LocalHashEmbeddingProvider()
