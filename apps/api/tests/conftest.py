import pytest
from moto.server import ThreadedMotoServer

from app.core import storage
from app.core.config import settings


@pytest.fixture
def s3_env():
    """A real S3-API HTTP server (not moto's endpoint-patching mock_aws,
    which doesn't intercept calls to an explicit custom endpoint_url — see
    the storage/crawler modules, which always set one).
    """
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
