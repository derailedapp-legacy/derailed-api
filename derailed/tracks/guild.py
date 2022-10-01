# The Derailed API
#
# Copyright 2022 Derailed Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from derailed.database import (
    Member,
    Track,
    User,
    get_new_track_position,
    get_track_dict,
)
from derailed.depends import get_user
from derailed.exceptions import NoAuthorizationError
from derailed.identifier import make_snowflake
from derailed.rate_limit import track_limit

router = APIRouter()


class CreateTrack(BaseModel):
    name: str = Field(max_length=55, min_length=1)
    topic: str | None = Field(max_length=1000, min_length=1)
    parent_id: str
    type: int


@router.get('/guilds/{guild_id}/tracks')
@track_limit()
async def get_guild_tracks(
    guild_id: str, request: Request, user: User | None = Depends(get_user)
) -> list[dict[str, Any]]:
    if user is None:
        raise NoAuthorizationError()

    if not await Member.find_one(
        Member.user_id == user.id, Member.guild_id == guild_id
    ).exists():
        raise HTTPException(403, 'You are not a member of this guild')

    return [
        get_track_dict(track=track)
        async for track in Track.find(Track.guild_id == guild_id)
    ]


@router.get('/guilds/{guild_id}/tracks/{track_id}')
@track_limit()
async def get_guild_track(
    guild_id: str,
    track_id: str,
    request: Request,
    user: User | None = Depends(get_user),
) -> dict[str, Any]:
    if user is None:
        raise NoAuthorizationError()

    if not await Member.find_one(
        Member.user_id == user.id, Member.guild_id == guild_id
    ).exists():
        raise HTTPException(403, 'You are not a member of this guild')

    return get_track_dict(
        track=await Track.find_one(Track.guild_id == guild_id, Track.id == track_id)
    )


@router.post('/guilds/{guild_id}/tracks')
@track_limit()
async def create_track(
    guild_id: str,
    request: Request,
    model: CreateTrack,
    user: User | None = Depends(get_user),
) -> dict[str, Any]:
    if user is None:
        raise NoAuthorizationError()

    if not await Member.find_one(
        Member.user_id == user.id, Member.guild_id == guild_id
    ).exists():
        raise HTTPException(403, 'You are not a member of this guild')

    if model.parent_id:
        parent = await Track.get(model.parent_id)

        if not parent or parent.guild_id != guild_id:
            raise HTTPException(400, 'Invalid or unaccessible parent channel')
    else:
        parent = None

    position = await get_new_track_position(parent=parent)

    track = Track(
        id=make_snowflake(),
        guild_id=guild_id,
        name=model.name,
        topic=model.topic,
        position=position,
        type=model.type,
        nsfw=False,
        last_message_id=None,
        parent_id=parent.id if parent else None,
        overwrites=[],
    )
    await track.insert()

    return track.dict(exclude={'icon', 'members'})
