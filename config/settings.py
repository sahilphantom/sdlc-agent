from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM
    ollama_host: str = "http://localhost:11434"
    sdlc_code_model: str = "qwen2.5-coder:3b"
    sdlc_reason_model: str = "llama3.2:3b"
    sdlc_embed_model: str = "nomic-embed-text"

    # LangSmith
    langchain_tracing_v2: bool = True
    langchain_api_key: str = ""
    langchain_project: str = "sdlc-agent"
    tracing_backend: str = "langsmith"

    # Databases
    database_url: str = "postgresql://sdlc:sdlc_pass@localhost:5432/sdlc_agent"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"

    # GitHub
    github_token: str = ""
    github_username: str = ""

    # Pipeline
    sdlc_max_retries: int = 3
    sdlc_confidence_threshold: float = 0.75

    # FastAPI
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_secret_key: str = "change_me"

    # General
    environment: str = "development"
    log_level: str = "INFO"


# Singleton — import this everywhere in the project
settings = Settings()
