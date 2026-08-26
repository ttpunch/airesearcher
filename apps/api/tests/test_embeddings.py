import json

import httpx
import pytest

from app.core.config import settings
from app.core.embeddings import LocalHashEmbeddingProvider, VoyageEmbeddingProvider


def voyage_mock_handler(request: httpx.Request) -> httpx.Response:
    assert request.url.path == "/v1/embeddings"
    assert request.headers["authorization"] == "Bearer test-key"
    payload = json.loads(request.content)
    texts = payload["input"]
    assert payload["model"] == "voyage-3"

    # Return them out of index order to prove the client sorts, not trusts
    # response ordering.
    data = [
        {"index": i, "embedding": [float(i)] * 4}
        for i in reversed(range(len(texts)))
    ]
    return httpx.Response(200, json={"data": data, "model": "voyage-3"})


@pytest.fixture
def voyage_client():
    return httpx.AsyncClient(
        transport=httpx.MockTransport(voyage_mock_handler), base_url="https://api.voyageai.com/v1"
    )


async def test_voyage_provider_embeds_and_orders_by_index(voyage_client):
    provider = VoyageEmbeddingProvider(api_key="test-key", model="voyage-3", client=voyage_client)
    async with voyage_client:
        result = await provider.embed(["first text", "second text", "third text"])

    assert result == [[0.0] * 4, [1.0] * 4, [2.0] * 4]


async def test_voyage_provider_empty_input_makes_no_request():
    def fail_handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("should not be called for empty input")

    client = httpx.AsyncClient(transport=httpx.MockTransport(fail_handler), base_url="https://api.voyageai.com/v1")
    provider = VoyageEmbeddingProvider(api_key="test-key", client=client)
    async with client:
        result = await provider.embed([])
    assert result == []


async def test_voyage_provider_raises_on_http_error():
    def error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid api key"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(error_handler), base_url="https://api.voyageai.com/v1")
    provider = VoyageEmbeddingProvider(api_key="bad-key", client=client)
    async with client:
        with pytest.raises(httpx.HTTPStatusError):
            await provider.embed(["some text"])


async def test_local_provider_is_deterministic():
    provider = LocalHashEmbeddingProvider(dim=64)
    a = await provider.embed(["BHEL manufactures turbines"])
    b = await provider.embed(["BHEL manufactures turbines"])
    assert a == b


async def test_local_provider_different_texts_differ():
    provider = LocalHashEmbeddingProvider(dim=64)
    result = await provider.embed(["BHEL turbines", "completely different sentence"])
    assert result[0] != result[1]


async def test_local_provider_respects_dimension_and_is_unit_normalized():
    provider = LocalHashEmbeddingProvider(dim=32)
    [vector] = await provider.embed(["test text"])
    assert len(vector) == 32
    norm = sum(v * v for v in vector) ** 0.5
    assert abs(norm - 1.0) < 1e-6


async def test_local_provider_default_dimension_matches_settings():
    provider = LocalHashEmbeddingProvider()
    [vector] = await provider.embed(["test"])
    assert len(vector) == settings.embedding_dim
