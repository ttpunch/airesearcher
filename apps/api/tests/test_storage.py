import hashlib

from app.core import storage


async def test_put_and_get_object_roundtrip(s3_env):
    content = b"hello from a test document"
    stored = await storage.put_object("docs/test.txt", content, "text/plain")

    assert stored.storage_path == "docs/test.txt"
    assert stored.content_hash == hashlib.sha256(content).hexdigest()
    assert stored.size == len(content)

    fetched = await storage.get_object("docs/test.txt")
    assert fetched == content
