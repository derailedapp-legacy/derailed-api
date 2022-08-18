# The Derailed API
#
# Copyright 2022 Derailed. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
from datetime import datetime

from beanie import Document, Indexed


class Member(Document):
    user_id: Indexed(str)
    guild_id: Indexed(str)
    nick: str | None = None
    roles: list[str] = []
    joined_at: datetime
    deaf: bool = False
    mute: bool = False
