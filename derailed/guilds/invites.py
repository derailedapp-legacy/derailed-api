# The Derailed API
#
# Copyright 2022 Derailed Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.

from time import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from derailed.database import (
    Event,
    Guild,
    Invite,
    Member,
    Track,
    User,
    get_date,
    get_member_permissions,
    produce,
)
from derailed.depends import get_user
from derailed.exceptions import NoAuthorizationError
from derailed.permissions import RolePermissionEnum, has_bit
from derailed.rate_limit import rate_limiter

router = APIRouter()


@router.get('/invites/{invite_code}')
@rate_limiter.limit('10/second')
async def get_invite(
    invite_code: str, request: Request, response: Response
) -> dict[str, Any]:
    invite = await Invite.find_one(Invite.id == invite_code)

    if invite is None:
        raise HTTPException(404, 'Invite not found')

    if invite.expires_at and invite.expires_at < int(time()):
        # NOTE: This is a really convoluted way of deleting invites
        # any better way?
        await invite.delete()
        raise HTTPException(400, 'This invite has expired')

    guild = await Guild.find_one(Guild.id == invite.guild_id)
    track = await Track.find_one(Track.id == invite.track_id)
    inviter = await User.find_one(User.id == invite.inviter_id)

    ret = invite.dict()

    ret['guild'] = guild.dict()
    ret['track'] = track.dict(include={'id', 'name', 'type'})
    ret['inviter'] = inviter.dict(exclude={'email', 'password', 'verification'})

    return ret


@router.post('/invites/{invite_code}')
@rate_limiter.limit('3/second')
async def accept_invite(
    invite_code: str,
    request: Request,
    response: Response,
    user: User | None = Depends(get_user),
) -> str:
    if not user:
        raise NoAuthorizationError()

    invite = await Invite.find_one(Invite.id == invite_code)

    if invite is None:
        raise HTTPException(404, 'Invite not found')

    if invite.expires_at and invite.expires_at < int(time()):
        # NOTE: This is a really convoluted way of deleting invites
        # any better way?
        await invite.delete()
        raise HTTPException(400, 'This invite has expired')

    if await Member.find_one(
        Member.user_id == user.id, Member.guild_id == invite.guild_id
    ).exists():
        raise HTTPException(400, 'You\'re already a member of this guild')

    member_count = Member.find(Member.guild_id == invite.guild_id).count()

    if member_count == 1000:
        raise HTTPException(403, 'This guild has reached its max member count')

    member = Member(
        user_id=user.id,
        guild_id=invite.guild_id,
        nick=None,
        joined_at=get_date(),
        role_ids=[invite.guild_id],
    )
    await member.insert()
    await produce(
        'guild', Event('GUILD_JOIN', data=member.dict(), guild_id=invite.guild_id)
    )

    return ''


@router.delete('/invites/{invite_code}')
async def delete_invite(
    invite_code: str,
    request: Request,
    response: Response,
    user: User | None = Depends(get_user),
) -> str:
    if not user:
        raise NoAuthorizationError()

    invite = await Invite.find_one(Invite.id == invite_code)

    if invite is None:
        raise HTTPException(404, 'Invite not found')

    if invite.expires_at is None or invite.expires_at < int(time()):
        # NOTE: This is a really convoluted way of deleting invites
        # any better way?
        await invite.delete()
        raise HTTPException(400, 'This invite has expired')

    guild = await Guild.find_one(Guild.id == invite.guild_id)

    is_owner = user.id == guild.owner_id

    permissions = await get_member_permissions(
        user_id=user.id, guild_id=invite.guild_id
    )

    if (
        not has_bit(permissions, RolePermissionEnum.DELETE_INVITES.value)
        and not is_owner
    ):
        raise HTTPException(403, 'Invalid permissions')

    await invite.delete()

    return ''
