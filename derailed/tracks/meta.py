# The Derailed API
#
# Copyright 2022 Derailed Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
import itertools
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from derailed.database import (
    Guild,
    Member,
    Message,
    Overwrite,
    Pin,
    Role,
    Track,
    User,
    get_member_permissions,
    get_track_dict,
    produce,
    track_has_bit,
)
from derailed.database.event import Event
from derailed.depends import get_user
from derailed.exceptions import NoAuthorizationError
from derailed.permissions import RolePermissionEnum, has_bit
from derailed.rate_limit import track_limit

router = APIRouter()


class AddOverwrite(BaseModel):
    object_id: str
    type: Literal[0, 1]
    allow: int
    deny: int


class ModifyTrack(BaseModel):
    name: str | None | bool = Field(default=False)
    topic: str | None = Field(None, max_length=1000, min_length=1)
    add_overwrites: list[AddOverwrite] | None = Field(None)
    remove_overwrites: list[str] | None = Field(None)


@router.patch('/tracks/{track_id}')
@track_limit
async def modify_track(
    track_id: str,
    model: ModifyTrack,
    request: Request,
    response: Response,
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
        member = await Member.find_one(Member.user_id == user.id, Member.guild_id == track.guild_id)

        if (
            not track_has_bit(permissions, RolePermissionEnum.MODIFY_TRACK.value, track, member)
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

    if model.add_overwrites or model.remove_overwrites:
        updates['overwrites'] = track.overwrites

    # remove comes first to make overwriting incredibly more simple
    if model.remove_overwrites:
        if not track.guild_id:
            raise HTTPException(
                400, 'You cannot remove or add overwrites on a non-guild track'
            )

        for overwrite_id, overwrite in itertools.product(
            model.remove_overwrites, track.overwrites
        ):
            if overwrite.object_id == overwrite_id:
                updates['overwrites'].remove(overwrite)

    if model.add_overwrites:
        if not track.guild_id:
            raise HTTPException(
                400, 'You cannot remove or add overwrites on a non-guild track'
            )

        overwrite_object_ids = [
            (overwrite.object_id, overwrite) for overwrite in track.overwrites
        ]

        for overwrite in model.add_overwrites:
            if overwrite.object_id in overwrite_object_ids:
                raise HTTPException(400, 'This overwrite already exists')

            if (
                overwrite.type == 0
                and not await Member.find_one(
                    Member.user_id == overwrite.object_id,
                    Member.guild_id == track.guild_id,
                ).exists()
            ):
                raise HTTPException(
                    400,
                    f'Overwrite for {overwrite.object_id} failed due to the member not being found',
                )
            elif (
                overwrite.type == 1
                and not await Role.find_one(
                    Role.id == overwrite.object_id, Role.guild_id == track.guild_id
                ).exists()
            ):
                raise HTTPException(
                    400,
                    f'Overwrite for {overwrite.object_id} failed due to the role not being found',
                )

            updates['overwrites'].append(
                Overwrite(
                    object_id=overwrite.object_id,
                    type=overwrite.type,
                    allow=overwrite.allow,
                    deny=overwrite.deny,
                )
            )

    await track.update(updates)

    track_data = get_track_dict(track=track)

    if track.guild_id:
        await produce(
            'track',
            Event('TRACK_MODIFY', track_data, guild_id=track.guild_id),
        )

    return track_data


@router.delete('/tracks/{track_id}', status_code=204)
@track_limit
async def delete_track(
    track_id: str,
    request: Request,
    response: Response,
    user: User | None = Depends(get_user),
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

    await produce(
        'track',
        Event(
            'TRACK_DELETE',
            {'track_id': track.id, 'guild_id': track.guild_id},
            guild_id=guild.id if track.guild_id else None,
            user_id=user.id if track.type in (2, 3) else None,
        ),
    )

    return ''
