# The Vincent.chat API
#
# Copyright 2022 Vincent.chat Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from vincentchatapi.database import (
    Guild,
    Member,
    Message,
    Role,
    User,
    get_date,
    get_member_permissions,
    produce,
)
from vincentchatapi.depends import get_user
from vincentchatapi.exceptions import NoAuthorizationError
from vincentchatapi.identifier import make_snowflake
from vincentchatapi.permissions import RolePermissionEnum, has_bit

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
    role = Role(
        id=guild.id, name='everyone', permissions=0, position=1, guild_id=guild.id
    )
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

    dmember = member.dict(exclude={'user_id', 'id'})
    dmember['user'] = user.dict(exclude={'email', 'password', 'verification'})

    await produce('guild', Message('GUILD_CREATE', guild.dict(), user_id=user.id))
    await produce(
        'guild', Message('GUILD_JOIN', dmember, user_id=user.id, guild_id=guild.id)
    )

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

    permissions = await get_member_permissions(user_id=user.id, guild_id=guild_id)

    guild = await Guild.find_one(Guild.id == guild_id)

    is_owner = user.id == guild.owner_id

    if not has_bit(permissions, RolePermissionEnum.MODIFY_GUILD.value) and not is_owner:
        raise HTTPException(403, 'Invalid permissions')

    await guild.update(**model.dict())

    data = guild.dict()
    await produce('guild', Message('GUILD_EDIT', data, guild_id=guild_id))
    return data


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
        # TODO: only have one event to delete this guild from all gateway caches
        await produce(
            'guild',
            Message(
                'GUILD_LEAVE',
                {'guild_id': guild.id},
                user_id=member.user_id,
                guild_id=guild.id,
            ),
        )

    await guild.delete()

    return ''
