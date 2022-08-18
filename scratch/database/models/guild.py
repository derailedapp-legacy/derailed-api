# The Derailed API
#
# Copyright 2022 Derailed. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
from typing import Literal

from beanie import Document
from pydantic import BaseModel


class Role(BaseModel):
    id: str
    name: str
    color: int
    hoist: bool
    position: int
    permissions: str
    mentionable: bool


class Emoji(BaseModel):
    id: str
    name: str
    asset: str


class Guild(Document):
    id: str
    name: str
    owner_id: str
    icon: str = None
    default_message_notification_level: Literal[0, 1]
    roles: list[Role] = []
    emojis: list[Emoji] = []
    features: list[str] = []
