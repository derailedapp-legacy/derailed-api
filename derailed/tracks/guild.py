# The Derailed API
#
# Copyright 2022 Derailed Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from derailed.database import Member, Track, User, get_track_dict
from derailed.depends import get_user
from derailed.exceptions import NoAuthorizationError

router = APIRouter()


@router.get('/guilds/{guild_id}/tracks')
async def get_guild_tracks(
    guild_id: str, user: User | None = Depends(get_user)
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
async def get_guild_track(
    guild_id: str, track_id: str, user: User | None = Depends(get_user)
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
