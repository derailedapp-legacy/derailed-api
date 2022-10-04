# The Derailed API
#
# Copyright 2022 Derailed Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.

from typing import Any

import pymongo
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from derailed.database import (
    Event,
    Guild,
    Message,
    Track,
    User,
    get_date,
    get_member_permissions,
    produce,
)
from derailed.database.utils import track_has_bit
from derailed.depends import get_user
from derailed.exceptions import NoAuthorizationError
from derailed.identifier import make_snowflake
from derailed.permissions import RolePermissionEnum
from derailed.rate_limit import track_limit

router = APIRouter()


class MessageAction(BaseModel):
    content: str = Field(min_length=1, max_length=1000)


@router.get('/tracks/{track_id}/messages')
@track_limit
async def get_track_messages(
    track_id: str,
    request: Request,
    response: Response,
    limit: int = Query(50, gt=0, lt=200),
    user: User | None = Depends(get_user),
) -> dict[str, Any]:
    if user is None:
        raise NoAuthorizationError()

    track = await Track.find_one(Track.id == track_id)

    if not track:
        raise HTTPException(404, 'Track not found')

    permissions = await get_member_permissions(user_id=user.id, guild_id=track.guild_id)

    guild = await Guild.find_one(Guild.id == track.guild_id)

    is_owner = user.id == guild.owner_id

    if (
        not track_has_bit(permissions, RolePermissionEnum.VIEW_MESSAGE_HISTORY.value)
        and not is_owner
    ):
        raise HTTPException(403, 'Invalid permissions')

    messages = []

    async for message in Message.find(
        Message.track_id == track_id,
        limit=limit,
        sort=[(Message.id, pymongo.DESCENDING)],
    ):
        messages.append(message.dict())

    return messages


@router.get('/tracks/{track_id}/messages/{message_id}')
@track_limit
async def get_track_message(
    track_id: str,
    message_id: str,
    request: Request,
    response: Response,
    user: User | None = Depends(get_user),
) -> dict[str, Any]:
    if user is None:
        raise NoAuthorizationError()

    track = await Track.find_one(Track.id == track_id)

    if not track:
        raise HTTPException(404, 'Track not found')

    permissions = await get_member_permissions(user_id=user.id, guild_id=track.guild_id)

    guild = await Guild.find_one(Guild.id == track.guild_id)

    is_owner = user.id == guild.owner_id

    if (
        not track_has_bit(permissions, RolePermissionEnum.VIEW_MESSAGE_HISTORY.value)
        and not is_owner
    ):
        raise HTTPException(403, 'Invalid permissions')

    message = await Message.find_one(Message.id == message_id)

    if message is None:
        raise HTTPException(404, 'Message not found')

    return message.dict()


@router.post('/tracks/{track_id}/messages')
@track_limit
async def create_message(
    track_id: str,
    request: Request,
    response: Response,
    model: MessageAction,
    user: User | None = Depends(get_user),
) -> dict[str, Any]:
    if user is None:
        raise NoAuthorizationError()

    track = await Track.find_one(Track.id == track_id)

    if not track:
        raise HTTPException(404, 'Track not found')

    if track.guild_id:
        permissions = await get_member_permissions(user_id=user.id, guild_id=track.guild_id)

        guild = await Guild.find_one(Guild.id == track.guild_id)

        is_owner = user.id == guild.owner_id

        if (
            not track_has_bit(permissions, RolePermissionEnum.CREATE_MESSAGE.value)
            and not is_owner
        ):
            raise HTTPException(403, 'Invalid permissions')

    message = Message(
        id=make_snowflake(),
        author_id=user.id,
        track_id=track_id,
        timestamp=get_date(),
        edited_timestamp=None,
        mention_everyone=False,
        type=0,
        content=model.content.strip(),
    )
    await message.insert()

    m = message.dict()

    await produce('messages', Event('MESSAGE_CREATE', m, guild_id=guild.id))

    return m


@router.patch('/tracks/{track_id}/messages/{message_id}')
@track_limit
async def modify_message(
    track_id: str,
    message_id: str,
    request: Request,
    response: Response,
    model: MessageAction,
    user: User | None = Depends(get_user),
) -> dict[str, Any]:
    if user is None:
        raise NoAuthorizationError()

    track = await Track.find_one(Track.id == track_id)

    if not track:
        raise HTTPException(404, 'Track not found')

    message = await Message.find_one(
        Message.track_id == track_id, Message.id == message_id
    )

    if message.author_id != user.id:
        raise HTTPException(403, 'You are not the creator of this message')

    await message.update(content=model.content.strip())

    m = message.dict()

    await produce('messages', Event('MESSAGE_MODIFY', m, guild_id=track.guild_id))

    return m


@router.delete('/tracks/{track_id}/messages/{message_id}')
@track_limit
async def delete_message(
    track_id: str,
    message_id: str,
    request: Request,
    response: Response,
    user: User | None = Depends(get_user),
) -> str:
    if user is None:
        raise NoAuthorizationError()

    track = await Track.find_one(Track.id == track_id)

    if not track:
        raise HTTPException(404, 'Track not found')

    if track.guild_id:
        permissions = await get_member_permissions(user_id=user.id, guild_id=track.guild_id)

        guild = await Guild.find_one(Guild.id == track.guild_id)

        is_owner = user.id == guild.owner_id

    message = await Message.find_one(
        Message.track_id == track_id, Message.id == message_id
    )

    if (
        not track_has_bit(permissions, RolePermissionEnum.DELETE_MESSAGES.value)
        and not is_owner
        and message.author_id != user.id
    ):
        raise HTTPException(403, 'Invalid permissions')

    await message.delete()

    await produce(
        'messages',
        Event(
            'MESSAGE_DELETE',
            {
                'message_id': message.id,
                'track_id': message.track_id,
                'guild_id': guild.id,
            },
            guild_id=guild.id,
        ),
    )

    return ''
