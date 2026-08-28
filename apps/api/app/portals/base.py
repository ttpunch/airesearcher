"""Shared building blocks for portal clients and portal tools.

See app/portals/__init__.py for the boundary rule (no app.core.db /
app.models / app.routers imports here) and app/portals/npp/ for the first
concrete portal built on top of this.
"""

import asyncio
import inspect
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from app.crawler.robots import USER_AGENT, can_fetch
from app.portals.cache import TTLCache

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class PortalError(Exception):
    """Base class for all portal-integration errors. Every message should
    be actionable — what happened and what the caller can do about it —
    per this project's MCP tool-design convention, not a bare exception
    dump.
    """


class PortalUnavailable(PortalError):
    """The portal didn't respond successfully after retries."""


class PortalDisallowed(PortalError):
    """robots.txt disallows fetching this path."""


class PortalSchemaDrift(PortalError):
    """The response no longer looks like what this client expects."""


class PortalToolError(PortalError):
    """A tool call failed on the caller's input (e.g. an unknown id) rather
    than on the upstream portal (PortalUnavailable) or its schema
    (PortalSchemaDrift). Deliberately not an MCP-specific exception type —
    app/portals/npp/tools.py stays transport-agnostic; each adapter (e.g.
    app/mcp_servers/npp_server.py) is responsible for translating this into
    whatever "anticipated failure, not a crash" mechanism its own transport
    uses.
    """


@dataclass(frozen=True)
class Fetched:
    """A single fetch's raw payload plus the provenance every downstream
    record needs to satisfy this project's "traceable to a source"
    principle for a live, changing API — see app/portals/npp/models.py.
    """

    payload: Any
    url: str
    retrieved_at: datetime


class PortalClient:
    """Base HTTP client for a government/public data portal: robots-txt
    compliance (reusing the crawler's own check), timeout, bounded retry
    with backoff, and a shared TTL + single-flight cache.

    Subclasses (e.g. app.portals.npp.client.NppClient) add endpoint methods
    and response parsing; they should not need to touch retry/cache logic.
    """

    def __init__(
        self,
        base_url: str,
        *,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
        user_agent: str = USER_AGENT,
        cache: TTLCache[Fetched] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(base_url=self._base_url)
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._user_agent = user_agent
        self._cache = cache or TTLCache[Fetched]()

    async def get_json(self, path: str, *, ttl_seconds: float) -> Fetched:
        url = f"{self._base_url}{path}" if path.startswith("/") else f"{self._base_url}/{path}"

        async def fetch() -> Fetched:
            if not await can_fetch(self._client, url):
                raise PortalDisallowed(
                    f"robots.txt at {self._base_url} disallows fetching {url} — this client will not "
                    "override that. If the site's robots.txt has since changed, retry."
                )
            return await self._get_with_retry(url)

        return await self._cache.get_or_fetch(url, ttl_seconds, fetch)

    async def _get_with_retry(self, url: str) -> Fetched:
        last_error: Exception | None = None
        base_backoffs = [0.5, 1.5, 3.0, 5.0]
        backoffs = [base_backoffs[i] if i < len(base_backoffs) else 5.0 for i in range(self._max_retries)]
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.get(
                    url, headers={"User-Agent": self._user_agent}, timeout=self._timeout_seconds
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
            else:
                if response.status_code == 200:
                    try:
                        payload = response.json()
                    except ValueError as exc:
                        raise PortalSchemaDrift(
                            f"{url} returned a 200 response that isn't valid JSON — the portal may have "
                            "changed its response format. Inspect the raw response before retrying."
                        ) from exc
                    return Fetched(payload=payload, url=url, retrieved_at=datetime.now(UTC))

                if response.status_code not in RETRYABLE_STATUS_CODES:
                    raise PortalUnavailable(
                        f"{url} returned HTTP {response.status_code}, which this client does not retry. "
                        "Check the URL and the portal's current API shape before retrying."
                    )
                last_error = PortalUnavailable(f"{url} returned HTTP {response.status_code}")
                retry_after = response.headers.get("Retry-After")
                if retry_after is not None:
                    try:
                        await asyncio.sleep(float(retry_after))
                        continue
                    except ValueError:
                        pass  # not a numeric Retry-After — fall through to the default backoff

            if attempt < self._max_retries:
                await asyncio.sleep(backoffs[attempt])

        raise PortalUnavailable(
            f"{url} did not respond successfully after {self._max_retries + 1} attempts "
            f"(last error: {last_error}). The portal may be intermittently slow or down — retry later, "
            "or fall back to any previously ingested snapshot of this data."
        ) from last_error


_SIMPLE_SCHEMA_TYPES = {str: str, int: int, float: float, bool: bool}


def derive_simple_schema(fn: Callable[..., Any]) -> dict[str, type]:
    """Derive a {param_name: python_type} schema from a function's typed
    signature — the same shape make_search_tool's manual {"query": str,
    "limit": int} dicts already use for claude_agent_sdk's @tool decorator.
    One source of truth (the signature) instead of a hand-written schema
    that can drift from the actual parameters.
    """
    schema: dict[str, type] = {}
    for name, param in inspect.signature(fn).parameters.items():
        annotation = param.annotation
        # Treat `X | None` the same as `X` for schema purposes — optionality
        # is expressed by having a default, not by the declared type.
        origin_args = getattr(annotation, "__args__", None)
        if origin_args:
            annotation = next((a for a in origin_args if a is not type(None)), annotation)
        schema[name] = _SIMPLE_SCHEMA_TYPES.get(annotation, str)
    return schema


@dataclass(frozen=True)
class PortalTool:
    """A single transport-agnostic tool: adapters in app/portals/adapters/
    turn this into a claude_agent_sdk SdkMcpTool or an mcp.server.MCPServer
    tool registration.
    """

    name: str
    description: str
    fn: Callable[..., Awaitable[Any]]
    read_only: bool = True

    @property
    def simple_input_schema(self) -> dict[str, type]:
        return derive_simple_schema(self.fn)


def now_utc() -> datetime:
    return datetime.now(UTC)


def dedupe_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered
