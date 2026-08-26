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

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
