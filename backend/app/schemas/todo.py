from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TodoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class TodoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    completed: bool | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="after")
    def require_update_field(self) -> "TodoUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("Title cannot be null")
        if "completed" in self.model_fields_set and self.completed is None:
            raise ValueError("Completed cannot be null")
        return self


class TodoResponse(BaseModel):
    id: int
    title: str
    description: str | None
    completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)