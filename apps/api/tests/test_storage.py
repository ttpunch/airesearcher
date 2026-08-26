import hashlib

import pytest
from moto.server import ThreadedMotoServer

from app.core import storage
from app.core.config import settings


@pytest.fixture
def s3_env():
    # mock_aws() only intercepts calls to real AWS endpoints; this project's
    # storage client always points at an explicit endpoint_url (MinIO in
    # dev/prod), so tests need moto's actual server, not the patch-based mock.
    server = ThreadedMotoServer(port=0)
    server.start()
    host, port = server.get_host_and_port()
    original_endpoint = settings.s3_endpoint_url
    settings.s3_endpoint_url = f"http://{host}:{port}"
    try:
        storage.ensure_bucket()
        yield
    finally:
        settings.s3_endpoint_url = original_endpoint
        server.stop()


@pytest.mark.asyncio
async def test_put_and_get_object_roundtrip(s3_env):
    content = b"hello from a test document"
    stored = await storage.put_object("docs/test.txt", content, "text/plain")

    assert stored.storage_path == "docs/test.txt"
    assert stored.content_hash == hashlib.sha256(content).hexdigest()
    assert stored.size == len(content)

    fetched = await storage.get_object("docs/test.txt")
    assert fetched == content
