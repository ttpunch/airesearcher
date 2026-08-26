"""Tests for app/agent/openai_compatible.py — the hand-rolled OpenAI-
compatible tool-calling loop used for the "openrouter"/"deepseek"
app.core.config.settings.llm_provider options.

The tool-calling loop is tested against httpx.MockTransport (same
technique as app/core/embeddings.py's VoyageEmbeddingProvider and
app/crawler/) — a real request/response cycle through httpx, not a
request-patching mock — since this sandbox cannot reach openrouter.ai or
api.deepseek.com and has no key configured for either.
"""

import json

import httpx
import pytest
from claude_agent_sdk import tool

from app.agent.openai_compatible import (
    DEEPSEEK_BASE_URL,
    OPENROUTER_BASE_URL,
    OpenAICompatibleConfig,
    _tool_to_openai_schema,
    get_openai_compatible_config,
    run_tool_calling_loop,
)
from app.core.config import settings


@tool("echo_tool", "Echoes back the given text.", {"text": str, "limit": int})
async def _echo_tool(args: dict) -> dict:
    return {"content": [{"type": "text", "text": f"echoed: {args['text']} (limit={args.get('limit')})"}]}


def test_tool_to_openai_schema_converts_python_types_to_json_schema():
    schema = _tool_to_openai_schema(_echo_tool)

    assert schema["type"] == "function"
    assert schema["function"]["name"] == "echo_tool"
    assert schema["function"]["description"] == "Echoes back the given text."
    properties = schema["function"]["parameters"]["properties"]
    assert properties == {"text": {"type": "string"}, "limit": {"type": "integer"}}
    assert set(schema["function"]["parameters"]["required"]) == {"text", "limit"}


class _ProviderSettingsGuard:
    """Restores settings.llm_provider/keys after a test mutates them —
    settings is a module-level singleton shared across the whole suite.
    """

    def __init__(self):
        self._original = {
            "llm_provider": settings.llm_provider,
            "openrouter_api_key": settings.openrouter_api_key,
            "openrouter_model": settings.openrouter_model,
            "deepseek_api_key": settings.deepseek_api_key,
            "deepseek_model": settings.deepseek_model,
        }

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        for key, value in self._original.items():
            setattr(settings, key, value)


def test_get_openai_compatible_config_for_openrouter():
    with _ProviderSettingsGuard():
        settings.llm_provider = "openrouter"
        settings.openrouter_api_key = "test-key"
        settings.openrouter_model = "deepseek/deepseek-chat"

        config = get_openai_compatible_config()

        assert config.base_url == OPENROUTER_BASE_URL
        assert config.api_key == "test-key"
        assert config.model == "deepseek/deepseek-chat"


def test_get_openai_compatible_config_for_deepseek():
    with _ProviderSettingsGuard():
        settings.llm_provider = "deepseek"
        settings.deepseek_api_key = "test-key-2"
        settings.deepseek_model = "deepseek-chat"

        config = get_openai_compatible_config()

        assert config.base_url == DEEPSEEK_BASE_URL
        assert config.api_key == "test-key-2"
        assert config.model == "deepseek-chat"


def test_get_openai_compatible_config_raises_for_anthropic():
    with _ProviderSettingsGuard():
        settings.llm_provider = "anthropic"
        with pytest.raises(ValueError, match="Not an OpenAI-compatible provider"):
            get_openai_compatible_config()


def _chat_completion_response(*, content: str | None = None, tool_calls: list[dict] | None = None) -> dict:
    message: dict = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {"choices": [{"message": message}]}


async def test_run_tool_calling_loop_calls_tool_and_returns_final_answer():
    call_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        body = json.loads(request.content)
        assert body["model"] == "test-model"
        assert body["messages"][0]["role"] == "system"

        if call_count["n"] == 1:
            return httpx.Response(
                200,
                json=_chat_completion_response(
                    tool_calls=[
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "echo_tool", "arguments": json.dumps({"text": "hi", "limit": 3})},
                        }
                    ]
                ),
            )
        # Second call must include the tool result in the message history.
        tool_messages = [m for m in body["messages"] if m["role"] == "tool"]
        assert len(tool_messages) == 1
        assert "echoed: hi" in tool_messages[0]["content"]
        return httpx.Response(200, json=_chat_completion_response(content="Final answer using [chunk:1]."))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://example.test")
    config = OpenAICompatibleConfig(base_url="https://example.test", api_key="test-key", model="test-model")

    result = await run_tool_calling_loop(config, "system prompt", "user question", tools=[_echo_tool], client=client)

    assert result == "Final answer using [chunk:1]."
    assert call_count["n"] == 2


async def test_run_tool_calling_loop_returns_immediately_with_no_tool_calls():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_chat_completion_response(content="No tools needed."))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://example.test")
    config = OpenAICompatibleConfig(base_url="https://example.test", api_key="test-key", model="test-model")

    result = await run_tool_calling_loop(config, "system prompt", "user question", tools=[_echo_tool], client=client)

    assert result == "No tools needed."


async def test_run_tool_calling_loop_unknown_tool_name_does_not_crash():
    call_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return httpx.Response(
                200,
                json=_chat_completion_response(
                    tool_calls=[
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "nonexistent_tool", "arguments": "{}"},
                        }
                    ]
                ),
            )
        return httpx.Response(200, json=_chat_completion_response(content="Handled the unknown-tool case."))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://example.test")
    config = OpenAICompatibleConfig(base_url="https://example.test", api_key="test-key", model="test-model")

    result = await run_tool_calling_loop(config, "system prompt", "user question", tools=[_echo_tool], client=client)

    assert result == "Handled the unknown-tool case."


async def test_run_tool_calling_loop_gives_up_after_max_turns():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_chat_completion_response(
                tool_calls=[
                    {"id": "call_x", "type": "function", "function": {"name": "echo_tool", "arguments": '{"text": "x", "limit": 1}'}}
                ]
            ),
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://example.test")
    config = OpenAICompatibleConfig(base_url="https://example.test", api_key="test-key", model="test-model")

    result = await run_tool_calling_loop(
        config, "system prompt", "user question", tools=[_echo_tool], client=client, max_turns=2
    )

    assert "maximum number of tool-use turns" in result
