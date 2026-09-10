from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


Priority = Literal["low", "medium", "high"]


class TodoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    due_date: datetime | None = None
    priority: Priority = "medium"
    tag: str | None = Field(default=None, min_length=1, max_length=100)

    model_config = ConfigDict(str_strip_whitespace=True)


class TodoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    due_date: datetime | None = None
    priority: Priority | None = None
    tag: str | None = Field(default=None, min_length=1, max_length=100)
    completed: bool | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="after")
    def require_update_field(self) -> "TodoUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("Title cannot be null")
        if "priority" in self.model_fields_set and self.priority is None:
            raise ValueError("Priority cannot be null")
        if "completed" in self.model_fields_set and self.completed is None:
            raise ValueError("Completed cannot be null")
        return self


class TodoResponse(BaseModel):
    id: int
    title: str
    description: str | None
    due_date: datetime | None
    priority: Priority
    tag: str | None
    completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)