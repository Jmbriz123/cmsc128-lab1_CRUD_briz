from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    session_cookie_name: str = "daymark_session"
    session_ttl_days: int = Field(default=30, ge=1, le=365)
    session_cookie_secure: bool = False
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000"
    auth_rate_window_seconds: int = Field(default=60, ge=1)
    login_rate_limit: int = Field(default=10, ge=1)
    recovery_rate_limit: int = Field(default=3, ge=1)

    @property
    def trusted_origins(self) -> set[str]:
        return {origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()}

    @model_validator(mode="after")
    def validate_origins(self):
        if not self.trusted_origins:
            raise ValueError("At least one allowed origin is required")
        for origin in self.trusted_origins:
            parsed = urlsplit(origin)
            if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                    or parsed.path or parsed.query or parsed.fragment or parsed.username
                    or parsed.password or "*" in origin):
                raise ValueError("Allowed origins must be exact HTTP(S) origins without paths")
            if not self.session_cookie_secure and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError("Non-local deployments require secure session cookies")
            if self.session_cookie_secure and parsed.scheme != "https":
                raise ValueError("Secure session cookies require HTTPS origins")
        return self


settings = Settings()
