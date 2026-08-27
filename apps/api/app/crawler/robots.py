"""robots.txt compliance for the crawler — a hard requirement per the
strategy report's Data Architecture section, not optional politeness.
"""

from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

USER_AGENT = "airesearcher-bot/0.1 (+https://github.com/ttpunch/airesearcher)"

_robots_cache: dict[str, RobotFileParser] = {}


async def _get_parser(client: httpx.AsyncClient, origin: str) -> RobotFileParser:
    if origin in _robots_cache:
        return _robots_cache[origin]

    parser = RobotFileParser()
    parser.set_url(f"{origin}/robots.txt")
    try:
        response = await client.get(f"{origin}/robots.txt", timeout=10.0)
        if response.status_code == 200:
            parser.parse(response.text.splitlines())
        else:
            # No robots.txt (or inaccessible) — RobotFileParser treats an
            # empty ruleset as "allow everything", which is the correct
            # default per the robots.txt spec.
            parser.parse([])
    except httpx.HTTPError:
        parser.parse([])

    _robots_cache[origin] = parser
    return parser


async def can_fetch(client: httpx.AsyncClient, url: str) -> bool:
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    parser = await _get_parser(client, origin)
    return parser.can_fetch(USER_AGENT, url)
