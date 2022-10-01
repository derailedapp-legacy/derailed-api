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
    Guild,
    Message,
    Track,
    User,
    get_date,
    get_member_permissions,
)
from derailed.depends import get_user
from derailed.exceptions import NoAuthorizationError
from derailed.identifier import make_snowflake
from derailed.permissions import RolePermissionEnum, has_bit
from derailed.rate_limit import track_limit

router = APIRouter()


class MessageAction(BaseModel):
    content: str = Field(min_length=1, max_length=1000)


@router.get('/tracks/{track_id}/messages')
@track_limit()
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
        not has_bit(permissions, RolePermissionEnum.VIEW_MESSAGE_HISTORY.value)
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
@track_limit()
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
        not has_bit(permissions, RolePermissionEnum.VIEW_MESSAGE_HISTORY.value)
        and not is_owner
    ):
        raise HTTPException(403, 'Invalid permissions')

    message = await Message.find_one(Message.id == message_id)

    if message is None:
        raise HTTPException(404, 'Message not found')

    return message.dict()


@router.post('/tracks/{track_id}/messages')
@track_limit()
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

    permissions = await get_member_permissions(user_id=user.id, guild_id=track.guild_id)

    guild = await Guild.find_one(Guild.id == track.guild_id)

    is_owner = user.id == guild.owner_id

    if (
        not has_bit(permissions, RolePermissionEnum.CREATE_MESSAGE.value)
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

    return message.dict()


@router.patch('/tracks/{track_id}/messages/{message_id}')
@track_limit()
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

    if not await Track.find_one(Track.id == track_id).exists():
        raise HTTPException(404, 'Track not found')

    message = await Message.find_one(
        Message.track_id == track_id, Message.id == message_id
    )

    if message.author_id != user.id:
        raise HTTPException(403, 'You are not the creator of this message')

    await message.update(content=model.content.strip())

    return message


@router.delete('/tracks/{track_id}/messages/{message_id}')
@track_limit()
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

    permissions = await get_member_permissions(user_id=user.id, guild_id=track.guild_id)

    guild = await Guild.find_one(Guild.id == track.guild_id)

    is_owner = user.id == guild.owner_id

    if (
        not has_bit(permissions, RolePermissionEnum.DELETE_MESSAGES.value)
        and not is_owner
    ):
        raise HTTPException(403, 'Invalid permissions')

    message = await Message.find_one(
        Message.track_id == track_id, Message.id == message_id
    )

    await message.delete()

    return ''
