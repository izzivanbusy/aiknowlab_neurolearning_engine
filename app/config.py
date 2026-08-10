from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@property
def async_database_url(self) -> str:
    # Take everything after :// and rebuild with asyncpg
    rest = self.DATABASE_URL.split("://", 1)[1]
    return "postgresql+asyncpg://" + rest


settings = Settings()  # type: ignore[call-arg]
