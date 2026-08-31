from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-5"
    max_rows: int = 100
    sql_timeout_seconds: int = 10

    model_config = SettingsConfigDict(
        env_file='.env', 
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra="forbid"
    )

try:
    settings = Settings()
except Exception as e:
    raise RuntimeError(f"Failed to load settings: {e}")
