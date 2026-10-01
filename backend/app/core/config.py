from urllib.parse import urlsplit
from typing import Literal

from pydantic import EmailStr, Field, SecretStr, field_validator, model_validator
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

    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from: EmailStr | None = None
    smtp_tls_mode: Literal["starttls", "ssl"] = "starttls"
    smtp_timeout_seconds: float = Field(default=10, gt=0, le=60)
    public_frontend_url: str = "http://localhost:5173"
    reset_token_ttl_minutes: int = Field(default=30, ge=1, le=60)

    @field_validator("smtp_from", mode="before")
    @classmethod
    def empty_sender(cls, value):
        return value or None

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_from)

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
        if self.smtp_host and (not self.smtp_from or self.public_frontend_url not in self.trusted_origins):
            raise ValueError("SMTP requires a sender and a public frontend URL matching an allowed origin")
        if bool(self.smtp_username) != bool(self.smtp_password.get_secret_value()):
            raise ValueError("SMTP username and password must be configured together")
        return self


settings = Settings()
