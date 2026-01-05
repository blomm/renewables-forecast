"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://renewables:renewables_dev@localhost:5433/renewables_forecast"

    # OpenAI
    openai_api_key: str = ""

    # Environment
    environment: str = "development"
    debug: bool = True

    # API Settings
    api_v1_prefix: str = "/api/v1"
    project_name: str = "Renewables Forecast API"

    # CORS
    allowed_origins: str = "http://localhost:3000,http://localhost:3001"

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse allowed origins into a list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    # External APIs
    postcodes_io_base_url: str = "https://api.postcodes.io"
    nasa_power_base_url: str = "https://power.larc.nasa.gov/api"

    # Caching (in seconds)
    cache_ttl_climate_data: int = 2592000  # 30 days
    cache_ttl_postcode: int = 7776000  # 90 days


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
