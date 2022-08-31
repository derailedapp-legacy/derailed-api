# The Felladex API
#
# Copyright 2022 Felladex Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
from datetime import datetime
from typing import Literal

from beanie import Document
from pydantic import BaseModel, Field


class Verification(BaseModel):
    email: bool = False
    phone: bool = False


class User(Document):
    id: str
    username: str = Field(min_length=1, max_length=200)
    discriminator: str = Field(regex=r'^[0-9]{4}$')
    email: str
    password: str
    verification: Verification = Verification()


class Profile(Document):
    id: str
    bio: str | None


class Settings(Document):
    id: str
    status: str = 'online'
    theme: Literal['dark', 'light'] = 'dark'
    client_status: Literal['desktop', 'mobile', 'web', 'tui'] = None


class Relationship(Document):
    user_id: str
    target_id: str
    type: int


class Presence(Document):
    id: str
    status: Literal['online', 'offline', 'afk', 'dnd']
    content: str | None = Field(max_length=128, min_length=1)
    timestamp: datetime | None
