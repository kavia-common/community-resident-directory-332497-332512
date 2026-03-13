from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Typed application settings loaded from environment variables.

    Environment variables expected (request orchestrator to set in .env):
    - POSTGRES_URL: SQLAlchemy/asyncpg compatible URL, e.g. postgresql+asyncpg://user:pass@host:port/db
      (DB container provides POSTGRES_URL, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT;
       prefer POSTGRES_URL to avoid guessing composition.)
    - JWT_SECRET: secret used to sign JWT tokens
    - JWT_ALGORITHM: defaults to HS256
    - ACCESS_TOKEN_EXPIRE_MINUTES: defaults to 60
    - CORS_ALLOW_ORIGINS: comma-separated list or '*' (default '*')
    """

    postgres_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_allow_origins: str = "*"

    @staticmethod
    def _must_get(name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise RuntimeError(
                f"Missing required environment variable: {name}. "
                "Ask the orchestrator to set it in the container .env."
            )
        return value

    @classmethod
    def load(cls) -> "Settings":
        """Load settings from environment (single normalization point)."""
        return cls(
            postgres_url=cls._must_get("POSTGRES_URL"),
            jwt_secret=cls._must_get("JWT_SECRET"),
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")),
            cors_allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*"),
        )


settings = Settings.load()
