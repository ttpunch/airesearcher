"""OpenAI-compatible tool-calling loop for non-Anthropic model providers.

OpenRouter and DeepSeek both expose an OpenAI-compatible `/chat/completions`
API, so one loop implementation serves both — only base_url/api_key/model
differ. This is a hand-rolled agentic loop (the Claude Agent SDK only talks
to Claude), but it reuses the *exact same* SdkMcpTool objects the Claude
Agent SDK path uses (make_search_tool, make_search_tenders_tool,
make_search_entities_tool) by calling `.handler(args)` directly — same
tools, same evidence-discipline system prompts, different model backend.
No new dependency: built on httpx (already used for Voyage/the crawler),
not the `openai` package.

Real HTTP client, unit tested against httpx.MockTransport — same technique
as app/core/embeddings.py's VoyageEmbeddingProvider and app/crawler/ — since
this project's dev sandbox cannot reach openrouter.ai or api.deepseek.com
and has no key configured for either.
"""

import json
from dataclasses import dataclass

import httpx
from claude_agent_sdk import SdkMcpTool

from app.core.config import settings

_PYTHON_TYPE_TO_JSON_SCHEMA_TYPE = {str: "string", int: "integer", float: "number", bool: "boolean"}

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"


@dataclass
class OpenAICompatibleConfig:
    base_url: str
    api_key: str
    model: str


def get_openai_compatible_config() -> OpenAICompatibleConfig:
    """Raises ValueError if the configured provider isn't one of these two
    — callers are expected to check settings.llm_provider first (the
    Claude Agent SDK path handles "anthropic", the default).
    """
    if settings.llm_provider == "openrouter":
        return OpenAICompatibleConfig(
            base_url=OPENROUTER_BASE_URL,
            api_key=settings.openrouter_api_key or "",
            model=settings.openrouter_model,
        )
    if settings.llm_provider == "deepseek":
        return OpenAICompatibleConfig(
            base_url=DEEPSEEK_BASE_URL,
            api_key=settings.deepseek_api_key or "",
            model=settings.deepseek_model,
        )
    raise ValueError(f"Not an OpenAI-compatible provider: {settings.llm_provider!r}")


def _tool_to_openai_schema(tool: SdkMcpTool) -> dict:
    properties: dict[str, dict] = {}
    for param_name, param_type in tool.input_schema.items():
        json_type = _PYTHON_TYPE_TO_JSON_SCHEMA_TYPE.get(param_type, "string")
        properties[param_name] = {"type": json_type}
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": {"type": "object", "properties": properties, "required": list(properties)},
        },
    }


async def run_tool_calling_loop(
    config: OpenAICompatibleConfig,
    system_prompt: str,
    user_prompt: str,
    tools: list[SdkMcpTool],
    client: httpx.AsyncClient | None = None,
    max_turns: int = 10,
) -> str:
    """Runs the request/tool-call/tool-result loop until the model returns
    a final message with no tool calls, or max_turns is exhausted. Returns
    the final text content (never raises for "no final answer" — returns
    an explanatory string instead, so callers' citation-extraction logic
    still runs over *something* rather than crashing).
    """
    owns_client = client is None
    client = client or httpx.AsyncClient(base_url=config.base_url)
    tools_by_name = {t.name: t for t in tools}
    openai_tools = [_tool_to_openai_schema(t) for t in tools]

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        for _ in range(max_turns):
            response = await client.post(
                "/chat/completions",
                headers={"Authorization": f"Bearer {config.api_key}"},
                json={"model": config.model, "messages": messages, "tools": openai_tools, "tool_choice": "auto"},
                timeout=60.0,
            )
            response.raise_for_status()
            message = response.json()["choices"][0]["message"]
            tool_calls = message.get("tool_calls") or []

            if not tool_calls:
                return message.get("content") or ""

            messages.append(
                {
                    "role": "assistant",
                    "content": message.get("content"),
                    "tool_calls": tool_calls,
                }
            )

            for tool_call in tool_calls:
                function = tool_call["function"]
                tool_obj = tools_by_name.get(function["name"])
                if tool_obj is None:
                    result_text = f"Unknown tool: {function['name']}"
                else:
                    args = json.loads(function.get("arguments") or "{}")
                    result = await tool_obj.handler(args)
                    result_text = result["content"][0]["text"]
                messages.append({"role": "tool", "tool_call_id": tool_call["id"], "content": result_text})

        return "Reached the maximum number of tool-use turns without a final answer."
    finally:
        if owns_client:
            await client.aclose()
