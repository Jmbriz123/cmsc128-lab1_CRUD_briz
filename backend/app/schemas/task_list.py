from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class TaskListCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    model_config = ConfigDict(str_strip_whitespace=True)


class TaskListResponse(BaseModel):
    id: int
    name: str
    owner_name: str
    is_owner: bool


class MemberAdd(BaseModel):
    email: EmailStr = Field(max_length=254)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class MemberResponse(BaseModel):
    id: int
    email: str
    display_name: str
    is_owner: bool
