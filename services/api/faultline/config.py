from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    app_env: Literal['development', 'test', 'production'] = 'development'
    database_url: str = Field(default='sqlite:///./faultline.db', repr=False)
    jwt_secret: str = Field(min_length=32, repr=False)
    jwt_issuer: str = 'faultline-api'
    jwt_audience: str = 'faultline-mobile'
    access_minutes: int = Field(default=10, ge=1, le=60)
    refresh_days: int = Field(default=30, ge=1, le=90)
    allowed_origins: list[str] = ['http://localhost:8081', 'http://127.0.0.1:8081']
    auth_rate_limit: int = Field(default=20, ge=1)
    auth_rate_window_seconds: int = Field(default=300, ge=1)
    redis_url: str | None = None

    @model_validator(mode='after')
    def production(self):
        if self.app_env == 'production':
            if not self.database_url.startswith('postgresql+psycopg://'):
                raise ValueError('Production requires PostgreSQL')
            if any(not origin.startswith('https://') for origin in self.allowed_origins):
                raise ValueError('Production origins must use HTTPS')
        return self


@lru_cache
def get_settings():
    return Settings()
