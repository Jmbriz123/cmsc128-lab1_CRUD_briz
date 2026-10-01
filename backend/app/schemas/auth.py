from typing import Annotated

from pydantic import BaseModel, BeforeValidator, EmailStr, Field, SecretStr, field_validator, model_validator

from app.schemas.user import Password


def normalize_email(value):
    return value.strip().lower() if isinstance(value, str) else value


Email = Annotated[EmailStr, BeforeValidator(normalize_email), Field(max_length=254)]
CurrentPassword = Annotated[SecretStr, Field(min_length=1, max_length=128)]


class LoginRequest(BaseModel):
    email: Email
    password: CurrentPassword


class ProfileUpdate(BaseModel):
    email: Email | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    current_password: CurrentPassword | None = None

    @field_validator("display_name", mode="before")
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def require_changes(self):
        changes = self.model_fields_set & {"email", "display_name"}
        if not changes or any(getattr(self, key) is None for key in changes):
            raise ValueError("Provide a nonempty email or display name")
        return self


class PasswordChange(BaseModel):
    current_password: CurrentPassword
    new_password: Password


class Message(BaseModel):
    detail: str


class ForgotPasswordRequest(BaseModel):
    email: Email


class ResetPasswordRequest(BaseModel):
    token: SecretStr = Field(min_length=43, max_length=43)
    new_password: Password
