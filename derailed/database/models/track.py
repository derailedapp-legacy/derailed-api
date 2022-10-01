# The Derailed API
#
# Copyright 2022 Derailed Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.

from datetime import datetime
from typing import Literal

from beanie import Document
from pydantic import BaseModel


class Overwrite(BaseModel):
    track_id: str
    object_id: str
    type: int
    allow: int
    deny: int


class Track(Document):
    id: str
    guild_id: str | None = None
    icon: str | None = None
    name: str | None
    topic: str | None
    position: str | None
    type: Literal[0, 1, 2, 3]
    members: list[str] | None
    nsfw: bool | None
    last_message_id: str | None
    parent_id: str | None
    overwrites: list[Overwrite] | None


class Message(Document):
    id: str
    author_id: str
    track_id: str
    timestamp: datetime
    edited_timestamp: datetime | None
    mention_everyone: bool
    pinned: bool = False
    type: int
    content: str


class Pin(Document):
    id: str
    origin: str
