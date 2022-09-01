# The Vincent.chat API
#
# Copyright 2022 Vincent.chat Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.

from typing import TYPE_CHECKING, overload

from vincentchatapi.database import Member, Role
from vincentchatapi.permissions import PermissionValue, combine_role_permission_values


async def get_member_roles(user_id: str, guild_id: str) -> list[Role]:
    roles: list[Role] = []
    member = await Member.find_one(
        Member.user_id == user_id, Member.guild_id == guild_id
    )

    if TYPE_CHECKING:
        assert member is not None

    for role_id in member.role_ids:
        roles.append(await Role.find_one(Role.id == role_id))

    return roles


@overload
async def get_member_permissions(user_id: str, guild_id: str) -> int:
    pass


@overload
async def get_member_permissions(user_id: str, guild_id: str) -> tuple[int, int]:
    pass


async def get_member_permissions(
    user_id: str, guild_id: str, get_highest_role_position: bool = False
) -> int | tuple[int, int]:
    roles = await get_member_roles(user_id=user_id, guild_id=guild_id)
    highest_position: int = 0

    values: list[PermissionValue] = []

    for role in roles:
        values.append(PermissionValue(position=role.position, value=role.permissions))

        if role.position > highest_position:
            highest_position = role.position

    if get_highest_role_position:
        return combine_role_permission_values(*values), highest_position

    return combine_role_permission_values(*values)


async def get_highest_role(guild_id: str) -> Role:
    roles = Role.find(Role.guild_id == guild_id)
    highest_role: Role = None

    async for role in roles:
        if role.position > highest_role.position:
            highest_role = role

    return highest_role
