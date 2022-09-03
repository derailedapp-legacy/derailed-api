# The Derailed API
#
# Copyright 2022 Derailed Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from derailed.database import Relationship, Track, User, produce
from derailed.database.event import Message
from derailed.depends import get_user
from derailed.exceptions import NoAuthorizationError
from derailed.identifier import make_snowflake

router = APIRouter()


class CreateGroupDM(BaseModel):
    name: str | None = Field(None, max_length=20, min_length=1)
    topic: str | None = Field(None, max_length=1000, min_length=1)
    user_ids: list[str] = Field(min_items=2, max_items=20)


@router.post('/users/@me/group-dms', status_code=201)
async def create_group_dm(
    model: CreateGroupDM, user: User | None = Depends(get_user)
) -> dict:
    if user is None:
        raise NoAuthorizationError()

    for user_id in model.user_ids:
        relation = await Relationship.find_one(
            Relationship.user_id == user_id, Relationship.target_id == user.id
        )

        if relation is None or relation.type != 0:
            raise HTTPException(403, f'You are not friends with user {user_id}')

    model.user_ids.append(user.id)

    track = Track(
        id=make_snowflake(),
        name=model.name,
        topic=model.topic,
        members=model.user_ids,
        position=None,
        type=3,
        nsfw=None,
        last_message_id=None,
        parent_id=None,
        overwrites=None,
    )
    await track.insert()

    track_data = track.dict(exclude={'position', 'nsfw', 'parent_id', 'overwrites'})

    await produce('track', Message('GROUP_TRACK_CREATE', track_data, user_id=user.id))

    for user_id in track.members:
        await produce(
            'track', Message('GROUP_TRACK_CREATE', track_data, user_id=user_id)
        )

    return track_data
