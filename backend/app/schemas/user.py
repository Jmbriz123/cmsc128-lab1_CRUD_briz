from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator


def validate_password(value: SecretStr) -> SecretStr:
    if not 15 <= len(value.get_secret_value()) <= 128:
        raise ValueError("Password must contain 15 to 128 characters")
    return value


Password = Annotated[SecretStr, AfterValidator(validate_password)]


class UserCreate(BaseModel):
    email: EmailStr = Field(max_length=254)
    display_name: str = Field(min_length=1, max_length=100)
    password: Password

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("display_name", mode="before")
    @classmethod
    def trim_display_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str
