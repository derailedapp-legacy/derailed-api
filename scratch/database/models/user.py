# The Derailed API
#
# Copyright 2022 Derailed. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
from typing import Literal

from beanie import Document
from pydantic import BaseModel, Field


class User(Document):
    id: str
    username: str = Field(min_length=1, max_length=200)
    discriminator: str = Field(regex=r'^[0-9]{4}$')
    email: str
    password: str
    avatar: str | None = None
    verified: bool = False


class GuildFolder(BaseModel):
    folder_id: str
    name: str
    guild_ids: list[str]


class Settings(Document):
    id: str
    status: str = 'online'
    theme: Literal['dark', 'light'] = 'dark'
    client_status: Literal['desktop', 'mobile', 'web', 'tui'] = None
    guild_folders: list[GuildFolder] = []
    guild_positions: list[str] = []
