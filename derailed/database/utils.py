# The Derailed API
#
# Copyright 2022 Derailed Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.

import asyncio
from typing import TYPE_CHECKING, Any

from derailed.database import Invite, Member, Role, Track
from derailed.identifier import make_invite
from derailed.permissions import (
    PermissionValue,
    combine_role_permission_values,
    has_bit,
)


async def get_member_roles(user_id: str, guild_id: str) -> list[Role]:
    roles: list[Role] = []
    member = await Member.find_one(
        Member.user_id == user_id, Member.guild_id == guild_id
    )

    if TYPE_CHECKING and member is None:
        raise AssertionError

    for role_id in member.role_ids:
        roles.append(await Role.find_one(Role.id == role_id))

    return roles


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


def get_track_dict(track: Track) -> dict[str, Any]:
    if track.type == 0:
        return track.dict(
            exclude={
                'icon',
                'members',
                'last_message_id',
                'parent_id',
            }
        )
    elif track.type == 1:
        return track.dict(
            exclude={
                'icon',
                'members',
            }
        )
    elif track.type in (2, 3):
        return track.dict(
            exclude={
                'position',
                'overwrites',
                'nsfw',
                'parent_id',
            }
        )


async def get_highest_position(guild_id: str, parent: Track | None = None) -> int:
    highest_position = 0

    if parent:
        async for track in Track.find(
            Track.guild_id == guild_id,
            Track.parent_id == parent.id,
        ):
            if track.position > highest_position:
                highest_position = track.position
    else:
        async for track in Track.find(
            Track.guild_id == guild_id,
        ):
            if int(track.position) > int(highest_position) and track.parent_id is None:
                highest_position = track.position

    return highest_position


async def get_new_track_position(guild_id: str, parent: Track | None = None) -> int:
    return (await get_highest_position(parent=parent, guild_id=guild_id)) + 1


async def get_invite_code() -> str:
    code = make_invite()

    if await Invite.find_one(Invite.id == code).exists():
        return await asyncio.create_task(get_invite_code())

    return code


def track_has_bit(value: int, visible: int, track: Track, member: Member) -> bool:
    for overwrite in track.overwrites:
        if (
            overwrite.object_id == member.user_id
            or overwrite.object_id in member.role_ids
        ):
            if has_bit(overwrite.allow, visible):
                return True
            elif has_bit(overwrite.deny, visible):
                return False

    return has_bit(value, visible)
