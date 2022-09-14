# The Derailed API
#
# Copyright 2022 Derailed Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from derailed.database import (
    Guild,
    Message,
    Pin,
    Track,
    User,
    get_member_permissions,
    get_track_dict,
    produce,
)
from derailed.database.event import Event
from derailed.depends import get_user
from derailed.exceptions import NoAuthorizationError
from derailed.permissions import RolePermissionEnum, has_bit

router = APIRouter()


class ModifyTrack(BaseModel):
    name: str | None | bool = Field(default=False)
    topic: str | None = Field(None, max_length=1000, min_length=1)


@router.patch('/tracks/{track_id}')
async def modify_track(
    track_id: str,
    model: ModifyTrack,
    request: Request,
    user: User | None = Depends(get_user),
) -> dict:
    if user is None:
        raise NoAuthorizationError()

    track = await Track.find_one(Track.id == track_id)

    if track is None:
        raise HTTPException(404, 'Track not found')

    if track.guild_id:
        permissions = await get_member_permissions(
            user_id=user.id, guild_id=track.guild_id
        )

        guild = await Guild.find_one(Guild.id == track.guild_id)

        is_owner = user.id == guild.owner_id

        if (
            not has_bit(permissions, RolePermissionEnum.MODIFY_TRACK.value)
            and not is_owner
        ):
            raise HTTPException(403, 'Invalid permissions')
    elif user.id not in track.members:
        raise HTTPException(403, 'You are not a member of this track')

    updates: dict[str, Any] = {}

    if model.name:
        updates['name'] = model.name

    if model.topic:
        updates['topic'] = model.topic

    await track.update(**updates)

    track_data = get_track_dict(track=track)

    if track.guild_id:
        await produce(
            'track',
            Event('TRACK_MODIFY', track_data, guild_id=track.guild_id),
        )

    return track_data


@router.delete('/tracks/{track_id}', status_code=204)
async def delete_track(
    track_id: str, request: Request, user: User | None = Depends(get_user)
) -> str:
    if user is None:
        raise NoAuthorizationError()

    track = await Track.find_one(Track.id == track_id)

    if track is None:
        raise HTTPException(404, 'Track not found')

    if track.guild_id:
        permissions = await get_member_permissions(
            user_id=user.id, guild_id=track.guild_id
        )

        guild = await Guild.find_one(Guild.id == track.guild_id)

        is_owner = user.id == guild.owner_id

        if (
            not has_bit(permissions, RolePermissionEnum.DELETE_TRACKS.value)
            and not is_owner
        ):
            raise HTTPException(403, 'Invalid permissions')

    if track.type in (2, 3):
        track.members.remove(user.id)

        if track.members == []:
            await track.delete()

            messages = Message.find(Message.track_id == track.id)
            pins = Pin.find(Pin.origin == track.id)

            await messages.delete()
            await pins.delete()
        else:
            await track.update()
    else:
        await track.delete()

        messages = Message.find(Message.track_id == track.id)
        pins = Pin.find(Pin.origin == track.id)

        await messages.delete()
        await pins.delete()

    return ''
