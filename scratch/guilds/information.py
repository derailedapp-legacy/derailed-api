# The Itch API
#
# Copyright 2022 Itch. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from scratch.database import Channel, Guild, Member, Settings, User, get_date
from scratch.depends import get_user
from scratch.exceptions import NoAuthorizationError

from ..identifier import make_snowflake

router = APIRouter()


class CreateGuild(BaseModel):
    name: str
    default_message_notification_level: Literal[0, 1] | None


class ModifyGuild(BaseModel):
    name: str
    default_message_notification_level: Literal[0, 1] | None


@router.post('/guilds', status_code=201)
async def create_guild(
    model: CreateGuild, user: User | None = Depends(get_user)
) -> dict:
    if user is None:
        raise NoAuthorizationError()

    # TODO: Create default channels
    guild = Guild(
        id=make_snowflake(),
        name=model.name,
        default_message_notification_level=model.default_message_notification_level
        if model.default_message_notification_level is not None
        else 0,
        owner_id=user.id,
    )
    member = Member(user_id=user.id, guild_id=guild.id, joined_at=get_date())
    await guild.insert()
    await member.insert()

    settings = await Settings.find_one(Settings.id == user.id)
    settings.guild_positions.append(guild.id)

    return guild.dict()


@router.get('/guilds/{guild_id}', status_code=200)
async def get_guild(guild_id: str, user: User | None = Depends(get_user)) -> dict:
    if user is None:
        raise NoAuthorizationError()

    member = await Member.find_one(
        Member.user_id == user.id, Member.guild_id == guild_id
    )

    if member is None:
        raise HTTPException(403, 'You are not a member of this Guild')

    guild = await Guild.find_one(Guild.id == guild_id)
    return guild.dict()


@router.get('/guilds/{guild_id}/preview', status_code=200)
async def get_guild_preview(guild_id: str) -> dict:
    guild = await Guild.find_one(Guild.id == guild_id)

    if guild is None:
        raise HTTPException(404, 'Guild not found')

    return guild.dict(
        exclude=['default_message_notification_level', 'roles', 'features', 'emojis']
    )


@router.delete('/guilds/{guild_id}', status_code=204)
async def delete_guild(guild_id: str, user: User | None = Depends(get_user)) -> dict:
    if user is None:
        raise NoAuthorizationError()

    guild = await Guild.find_one(Guild.id == guild_id)

    if guild is None:
        raise HTTPException(404, 'Unable to find Guild')

    if guild.owner_id != user.id:
        raise HTTPException(403, 'You are not the owner of this Guild')

    member_count = await Member.find(Member.guild_id == guild.id).count()

    if member_count > 2000:
        raise HTTPException(400, 'This Guild has too many members to be deleted')

    await guild.delete()
    await Member.find(Member.guild_id == guild_id).delete()
    await Channel.find(Channel.guild_id == guild_id).delete()

    return ''
