# The Derailed API
#
# Copyright 2022 Derailed Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
from typing import Any

from msgspec import Struct


class Message(Struct):
    name: str
    data: dict[str, Any]
    user_id: str | None = None
    guild_id: str | None = None
