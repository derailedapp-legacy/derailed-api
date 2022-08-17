# The Telescope API
#
# Copyright 2022 Telescope Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
from beanie import Document
from pydantic import BaseModel


class PermissionOverwrite(BaseModel):
    id: str
    type: int
    allow: str
    deny: str


class Channel(Document):
    id: str
    guild_id: str
    name: str
    position: int
    topic: str
    type: int
    last_message_id: str = None
    permission_overwrites: list[PermissionOverwrite] = []
    bitrate: int
    recipients: list[str]
