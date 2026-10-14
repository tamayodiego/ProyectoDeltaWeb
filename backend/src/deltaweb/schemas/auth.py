"""Account data that travels as JSON."""

from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field


def _lowercase(email: str) -> str:
    return email.lower()


# Validated email ("a@b" is rejected), stored and compared in lowercase
Email = Annotated[EmailStr, AfterValidator(_lowercase)]


class Credentials(BaseModel):
    email: Email
    # Strength rules are checked in the register endpoint, not here: login must accept any
    # string, or the error would tell an attacker which passwords cannot exist
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    email: str
    email_verified: bool
    created_at: datetime
