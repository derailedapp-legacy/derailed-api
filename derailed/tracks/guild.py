# The Derailed API
#
# Copyright 2022 Derailed Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.

from time import time
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from derailed.database import (
    Event,
    Invite,
    Member,
    Track,
    User,
    get_invite_code,
    get_member_permissions,
    get_new_track_position,
    get_track_dict,
    produce,
)
from derailed.depends import get_user
from derailed.exceptions import NoAuthorizationError
from derailed.identifier import make_snowflake
from derailed.permissions import RolePermissionEnum, has_bit
from derailed.rate_limit import track_limit

router = APIRouter()


class CreateTrack(BaseModel):
    name: str = Field(max_length=55, min_length=1)
    topic: str | None = Field(max_length=1000, min_length=1)
    parent_id: str | None = None
    type: Literal[0, 1] | None = 1


class CreateInvite(BaseModel):
    expires_at: int | None = None


@router.get('/guilds/{guild_id}/tracks')
@track_limit
async def get_guild_tracks(
    guild_id: str,
    request: Request,
    response: Response,
    user: User | None = Depends(get_user),
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
@track_limit
async def get_guild_track(
    guild_id: str,
    track_id: str,
    request: Request,
    response: Response,
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
@track_limit
async def create_track(
    guild_id: str,
    request: Request,
    response: Response,
    model: CreateTrack,
    user: User | None = Depends(get_user),
) -> dict[str, Any]:
    if user is None:
        raise NoAuthorizationError()

    if not await Member.find_one(
        Member.user_id == user.id, Member.guild_id == guild_id
    ).exists():
        raise HTTPException(403, 'You are not a member of this guild')

    if model.parent_id and model.type == 0:
        raise HTTPException(400, 'Category tracks cannot have parents')

    if model.parent_id:
        parent = await Track.get(model.parent_id)

        if not parent or parent.guild_id != guild_id:
            raise HTTPException(400, 'Invalid or unaccessible parent track')
    else:
        parent = None

    position = await get_new_track_position(parent=parent, guild_id=guild_id)

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

    t = get_track_dict(track=track)

    await produce('track', Event('TRACK_CREATE', t, guild_id=guild_id))

    return t


@router.post('/guilds/{guild_id}/tracks/{track_id}/invites')
async def create_invite(
    guild_id: str,
    track_id: str,
    request: Request,
    response: Response,
    model: CreateInvite,
    user: User | None = Depends(get_user),
) -> dict[str, Any]:
    if user is None:
        raise NoAuthorizationError()

    if not await Track.find_one(
        Track.id == track_id, Track.guild_id == guild_id
    ).exists():
        raise HTTPException(404, 'Track or Guild not found')

    permissions = await get_member_permissions(user_id=user.id, guild_id=guild_id)

    if not has_bit(permissions, RolePermissionEnum.CREATE_INVITES.value):
        raise HTTPException(403, 'Invalid permissions')

    current_second = int(time())

    if (current_second + 10000) > model.expires_at or len(str(model.expires_at)) > 11:
        raise HTTPException(400, 'Expiry date is invalid')

    invite = Invite(
        id=get_invite_code(),
        guild_id=guild_id,
        track_id=track_id,
        inviter_id=user.id,
        expires_at=model.expires_at,
    )
    await invite.insert()

    return invite.dict()
