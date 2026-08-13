from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def async_database_url(self) -> str:
        import re
        # Handles: postgres://, postgresql://, postgresql+psycopg2://, etc.
        return re.sub(r'^postgres(ql)?(\+\w+)?://', 'postgresql+asyncpg://', self.DATABASE_URL)


settings = Settings()  # type: ignore[call-arg]
