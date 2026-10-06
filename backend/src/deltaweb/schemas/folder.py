"""Folder data that travels as JSON."""

from datetime import datetime
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

# Surrounding spaces are stripped first, so "   " is empty and rejected
FolderName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class FolderCreate(BaseModel):
    name: FolderName
    parent_id: int | None = None  # None = root folder


class FolderUpdate(BaseModel):
    """Only the fields that are sent change. ``"parent_id": null`` moves to the root."""

    name: FolderName | None = None
    parent_id: int | None = None

    @model_validator(mode="after")
    def name_cannot_be_null(self) -> Self:
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null")
        return self


class FolderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    parent_id: int | None
    created_at: datetime
