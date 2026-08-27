from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://airesearcher:airesearcher@localhost:5432/airesearcher"
    cors_origins: str = "http://localhost:3000"

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "airesearcher"
    s3_secret_key: str = "airesearcher-dev-secret"
    s3_bucket: str = "airesearcher-documents"

    # Embeddings: Voyage AI (Anthropic's recommended provider) when a key is
    # configured; otherwise app.core.embeddings falls back to a local,
    # non-semantic provider so the pipeline still runs without one — see
    # that module's docstring.
    voyage_api_key: str | None = None
    voyage_model: str = "voyage-3"
    embedding_dim: int = 1024

    # Research agent model provider. "anthropic" (default) runs the Claude
    # Agent SDK path (app/agent/research_agent.py, app/agent/deep_research.py)
    # exactly as before. "openrouter" and "deepseek" run a hand-rolled
    # OpenAI-compatible tool-calling loop instead (app/agent/openai_compatible.py)
    # against the same tools — for OpenRouter's aggregator API or DeepSeek's
    # API directly, e.g. for a user without an ANTHROPIC_API_KEY. See
    # AGENTS.md for why the Claude Agent SDK stays the default.
    llm_provider: str = "anthropic"
    openrouter_api_key: str | None = None
    openrouter_model: str = "deepseek/deepseek-chat"
    deepseek_api_key: str | None = None
    deepseek_model: str = "deepseek-chat"

    # National Power Portal (npp.gov.in) integration — see
    # app/portals/npp/ for the client and app/mcp_servers/npp_server.py
    # for the standalone MCP server built on it. Unlike GeM, NPP's
    # dashboard endpoints are plain unauthenticated JSON GETs (verified
    # live), so this is a real client, not a manual-entry workaround.
    npp_enabled: bool = True
    npp_base_url: str = "https://npp.gov.in"
    npp_timeout_seconds: float = 30.0
    npp_max_retries: int = 2
    npp_cache_ttl_seconds: int = 21600  # 6h — station/project/capacity data
    npp_trend_cache_ttl_seconds: int = 86400  # 24h — annual generation series
    npp_max_tool_results: int = 100

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
