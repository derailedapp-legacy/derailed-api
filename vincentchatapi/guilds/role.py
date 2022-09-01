# The Vincent.chat API
#
# Copyright 2022 Vincent.chat Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from vincentchatapi.database import (
    Guild,
    Member,
    Message,
    Role,
    User,
    get_highest_role,
    get_member_permissions,
    produce,
)
from vincentchatapi.depends import get_user
from vincentchatapi.exceptions import NoAuthorizationError
from vincentchatapi.identifier import make_snowflake
from vincentchatapi.permissions import RolePermissionEnum, has_bit

router = APIRouter()


class CreateRole(BaseModel):
    name: str = Field(max_length=128)
    hoist: bool = False
    permissions: int


class ModifyRole(BaseModel):
    name: str | None = Field(None, max_length=128)
    hoist: bool | None = Field(None)
    position: int | None = Field(None)


@router.get('/guilds/{guild_id}/roles', status_code=200)
async def get_guild_roles(
    guild_id: str, user: User | None = Depends(get_user)
) -> list[Role]:
    if user is None:
        raise NoAuthorizationError()

    is_member = await Member.find_one(
        Member.guild_id == guild_id, Member.user_id == user.id
    ).exists()

    if not is_member:
        raise HTTPException(403, 'You are not a member of this guild')

    roles = await Role.find(Role.guild_id == guild_id).to_list()

    return roles


@router.get('/guilds/{guild_id}/roles/{role_id}', status_code=200)
async def get_guild_role(
    guild_id: str, role_id: str, user: User | None = Depends(get_user)
) -> list[Role]:
    if user is None:
        raise NoAuthorizationError()

    is_member = await Member.find_one(
        Member.guild_id == guild_id, Member.user_id == user.id
    ).exists()

    if not is_member:
        raise HTTPException(403, 'You are not a member of this guild')

    role = await Role.find_one(Role.guild_id == guild_id, Role.id == role_id)

    if TYPE_CHECKING:
        assert role

    return role


@router.post('/guilds/{guild_id}/roles', status_code=201)
async def create_role(
    guild_id: str, model: CreateRole, user: User | None = Depends(get_user)
) -> dict:
    if user is None:
        raise NoAuthorizationError()

    is_member = await Member.find_one(
        Member.guild_id == guild_id, Member.user_id == user.id
    ).exists()

    if not is_member:
        raise HTTPException(403, 'You are not a member of this guild')

    # TODO: don't let users set the roles permission higher than their own
    permissions = await get_member_permissions(user_id=user.id, guild_id=guild_id)

    if not has_bit(permissions, RolePermissionEnum.MANAGE_ROLES.value):
        raise HTTPException(403, 'Invalid permissions')

    if await Role.find_one(
        Role.guild_id == guild_id, Role.position == model.position
    ).exists():
        raise HTTPException(400, 'Role position already taken')

    highest = await get_highest_role(guild_id=guild_id)

    role = Role(
        id=make_snowflake(),
        guild_id=guild_id,
        name=model.name,
        hoist=model.hoist,
        permissions=model.permissions,
        position=highest.position + 1,
    )
    await role.insert()

    data = role.dict()

    await produce('guild', Message('ROLE_CREATE', data, guild_id=guild_id))
    return data


async def get_position(guild_id: str, role: Role, position: int) -> None:
    if position in {0, 1}:
        raise HTTPException(400, 'Cannot designate role position')

    highest = await get_highest_role(guild_id=guild_id)

    if position > highest.position and position != highest + 1:
        raise HTTPException(400, 'Position value is too big')

    if position == highest.position + 1:
        await role.update(position=highest.position + 1)
        return

    roles = Role.find(Role.guild_id == guild_id)

    async for grole in roles:
        if grole.position > position:
            await grole.update(position=grole.position + 1)
        elif grole.position == position:
            await grole.update(position=grole.position + 1)
            break
        else:
            await grole.update(position=grole.position - 1)

    await role.update(position=position)


@router.patch('/guilds/{guild_id}/roles/{role_id}', status_code=200)
async def modify_role(
    guild_id: str,
    role_id: str,
    model: ModifyRole,
    user: User | None = Depends(get_user),
) -> dict:
    if user is None:
        raise NoAuthorizationError()

    is_member = await Member.find_one(
        Member.guild_id == guild_id, Member.user_id == user.id
    ).exists()

    if not is_member:
        raise HTTPException(403, 'You are not a member of this guild')

    permissions, max_pos = await get_member_permissions(
        user_id=user.id, guild_id=guild_id, get_highest_role_position=True
    )

    guild = await Guild.find_one(Guild.id == guild_id)

    is_owner = user.id == guild.owner_id

    if not has_bit(permissions, RolePermissionEnum.MANAGE_ROLES.value) and not is_owner:
        raise HTTPException(403, 'Invalid permissions')

    role = await Role.find_one(Role.guild_id == guild_id, Role.id == role_id)

    if role is None:
        raise HTTPException(404, 'Role does not exist')

    updates: dict[str, Any] = {}

    if model.name:
        updates['name'] = model.name

    if model.hoist is not None:
        updates['hoist'] = model.hoist

    if model.position is not None:
        if role.position > max_pos and not is_owner:
            raise HTTPException(400, 'Role position is over your own role permission.')

        await get_position(guild_id=guild_id, role=role, position=model.position)

    await role.update(**updates)

    data = role.dict()

    await produce('guild', Message('ROLE_EDIT', data, guild_id=guild_id))
    return data


@router.delete('/guilds/{guild_id}/roles/{role_id}', status_code=204)
async def delete_guild_role(
    guild_id: str, role_id: str, user: User | None = Depends(get_user)
) -> str:
    if user is None:
        raise NoAuthorizationError()

    is_member = await Member.find_one(
        Member.guild_id == guild_id, Member.user_id == user.id
    ).exists()

    if not is_member:
        raise HTTPException(403, 'You are not a member of this guild')

    permissions, max_pos = await get_member_permissions(
        user_id=user.id, guild_id=guild_id, get_highest_role_position=True
    )

    guild = await Guild.find_one(Guild.id == guild_id)

    is_owner = user.id == guild.owner_id

    if not has_bit(permissions, RolePermissionEnum.MANAGE_ROLES.value) and not is_owner:
        raise HTTPException(403, 'Invalid permissions')

    role = await Role.find_one(Role.guild_id == guild_id, Role.id == role_id)

    if role is None:
        raise HTTPException(404, 'Role does not exist')

    if max_pos < role.position or max_pos == role.position:
        raise HTTPException(400, 'Role position is higher than your own')

    members = Member.find(Member.guild_id == guild_id)

    async for member in members:
        if role.id in member.role_ids:
            member.role_ids.remove(role.id)

        await member.save()

    await role.delete()

    await produce('guild', Message('ROLE_DELETE', {'id': role.id}, guild_id=guild_id))

    return ''
