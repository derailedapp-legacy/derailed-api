# The Derailed API
#
# Copyright 2022 Derailed Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from valve.database import Guild, Member, Role, User, get_date
from valve.depends import get_user
from valve.exceptions import NoAuthorizationError
from valve.identifier import make_snowflake

router = APIRouter(prefix='/guilds')


class CreateGuild(BaseModel):
    name: str = Field(max_length=100)
    description: str | None = Field(None, max_length=1300)
    nsfw: bool = False


class ModifyGuild(CreateGuild):
    pass


@router.post('', status_code=201)
async def create_guild(
    model: CreateGuild, user: User | None = Depends(get_user)
) -> dict:
    if user is None:
        raise NoAuthorizationError()

    guild = Guild(
        id=make_snowflake(),
        name=model.name,
        owner_id=user.id,
        description=model.description,
        nsfw=model.nsfw,
    )
    role = Role(id=guild.id, name='everyone', permissions=0, position=1)
    member = Member(
        user_id=user.id,
        guild_id=guild.id,
        nick=None,
        joined_at=get_date(),
        role_ids=[role.id],
    )
    await guild.insert()
    await member.insert()
    await role.insert()

    return guild.dict()


@router.get('/{guild_id}', status_code=200)
async def get_guild(guild_id: str, user: User | None = Depends(get_user)) -> dict:
    if user is None:
        raise NoAuthorizationError()

    is_member = await Member.find_one(
        Member.user_id == user.id, Member.guild_id == guild_id
    ).exists()

    if is_member is False:
        raise HTTPException(403, 'You are not a member of this guild')

    guild = await Guild.find_one(Guild.id == guild_id)
    return guild.dict()


@router.get('/{guild_id}/preview', status_code=200)
async def get_guild_preview(
    guild_id: str, user: User | None = Depends(get_user)
) -> dict:
    if user is None:
        raise NoAuthorizationError()

    is_member = await Member.find_one(
        Member.user_id == user.id, Member.guild_id == guild_id
    ).exists()

    if is_member is False:
        raise HTTPException(403, 'You are not a member of this guild')

    guild = await Guild.find_one(Guild.id == guild_id)
    guildd = guild.dict()

    guildd['member_count'] = await Member.find(Member.guild_id == guild_id).count()
    # TODO: Actually find a way to count this
    guildd['online_count'] = 0

    return guild.dict()


@router.patch('/{guild_id}', status_code=200)
async def modify_guild(
    guild_id: str, model: ModifyGuild, user: User | None = Depends(get_user)
) -> dict:
    if user is None:
        raise NoAuthorizationError()

    guild = await Guild.find_one(Guild.id == guild_id)

    if guild is None:
        raise HTTPException(404, 'Guild does not exist')

    if guild.owner_id != user.id:
        raise HTTPException(403, 'You are not the guild owner')

    await guild.update(**model.dict())

    return guild.dict()


@router.delete('/{guild_id}', status_code=204)
async def delete_guild(guild_id: str, user: User | None = Depends(get_user)) -> str:
    if user is None:
        raise NoAuthorizationError()

    guild = await Guild.find_one(Guild.id == guild_id)

    if guild is None:
        raise HTTPException(404, 'Guild does not exist')

    if guild.owner_id != user.id:
        raise HTTPException(403, 'You are not the guild owner')

    member_count = await Member.find(Member.guild_id == guild.id).count()

    if member_count > 1000:
        raise HTTPException(400, 'This guild has more then 1000 members')

    members = Member.find(Member.guild_id == guild_id)

    async for member in members:
        await member.delete()

    await guild.delete()

    return ''
