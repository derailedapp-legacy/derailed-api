# The Derailed API
#
# Copyright 2022 Derailed. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
import os
from datetime import datetime, timezone

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from .models import Profile, Settings, User

DOCUMENT_MODELS = [
    User,
    Settings,
    Profile,
]


async def connect() -> None:
    motor = AsyncIOMotorClient(os.getenv('MONGO_URI'))
    await init_beanie(
        database=motor.db_name,
        document_models=DOCUMENT_MODELS,
        allow_index_dropping=True,
    )


def get_date() -> datetime:
    return datetime.now(timezone.utc)
