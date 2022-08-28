# The Derailed API
#
# Copyright 2022 Derailed Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
import os
from datetime import datetime, timezone

from aiokafka import AIOKafkaProducer
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from msgspec import msgpack

from .event import Message
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


producer: AIOKafkaProducer | None = None


async def produce(topic: str, event: Message) -> None:
    if producer is None:
        global producer

        producer = AIOKafkaProducer(bootstrap_servers=os.getenv('KAFKA_URI'))
        await producer.start()

    await producer.send(topic=topic, value=msgpack.encode(event))
