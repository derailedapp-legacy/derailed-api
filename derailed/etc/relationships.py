# The Derailed API
#
# Copyright 2022 Derailed Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from derailed.database import Event, Relationship, User, produce
from derailed.depends import get_user
from derailed.exceptions import NoAuthorizationError

router = APIRouter()


class CreateRelationship(BaseModel):
    type: Literal[1, 2]


@router.get('/relationships/relatable')
async def user_is_relatable(
    username: str,
    discriminator: str,
    request: Request,
    response: Response,
    user: User | None = Depends(get_user),
) -> dict:
    if user is None:
        raise NoAuthorizationError()

    relationships = await Relationship.find(Relationship.user_id == user.id).count()

    if relationships > 4000:
        raise HTTPException(400, 'Max relationships reached')

    if len(discriminator) != 4:
        raise HTTPException(400, 'Discriminator length is too low')

    target_user = await User.find_one(
        User.username == username, User.discriminator == discriminator
    )

    if target_user is None:
        raise HTTPException(404, 'User not found')

    relationship = await Relationship.find_one(
        user_id=target_user.id, target_id=user.id
    )

    relatable = relationship is None or relationship.type != 2

    return {'user_id': target_user.id, 'relatable': relatable}


@router.put('/relationships/{user_id}', status_code=204)
async def create_relationship(
    user_id: str,
    model: CreateRelationship,
    request: Request,
    response: Response,
    user: User | None = Depends(get_user),
) -> str:
    if user is None:
        raise NoAuthorizationError()

    relationships = await Relationship.find(Relationship.user_id == user.id).count()

    if relationships > 4000:
        raise HTTPException(400, 'Max relationships reached')

    target_user = await User.find_one(User.id == user_id)

    if target_user is None:
        raise HTTPException(404, 'User not found')

    current_relationship = await Relationship.find_one(
        Relationship.user_id == user.id, Relationship.target_id == user_id
    )
    target_relationship = await Relationship.find_one(
        Relationship.user_id == user_id, Relationship.target_id == user.id
    )

    if model.type == 1:
        if current_relationship is not None:
            if current_relationship.type == 2:
                raise HTTPException(400, 'You have this user blocked')
            if current_relationship.type == 1:
                raise HTTPException(
                    400, 'You cannot send another friend request to this user'
                )

        if target_relationship is not None:
            if target_relationship.type == 0:
                raise HTTPException(400, 'You are already friends with this user')
            if target_relationship.type == 1:
                await target_relationship.update(type=0)

                if current_relationship is None:
                    current_relationship = Relationship(
                        user_id=user.id, target_id=user_id, type=0
                    )
                    await current_relationship.insert()

                await produce(
                    'relationships',
                    Event('RELATIONSHIP_ACCEPT', {'user_id': user_id}, user_id=user.id),
                )
                await produce(
                    'relationships',
                    Event('RELATIONSHIP_ACCEPT', {'user_id': user.id}, user_id=user_id),
                )

            elif current_relationship.type == 2:
                raise HTTPException(400, 'This user has blocked you.')

    elif model.type == 2:
        if current_relationship is not None:
            if current_relationship.type == 1:
                await current_relationship.update(type=2)
                await target_relationship.delete()

            elif current_relationship.type == 2:
                raise HTTPException(400, 'Cannot block a user twice')

        current_relationship = Relationship(user_id=user.id, target_id=user_id, type=2)
        await current_relationship.insert()

        await produce(
            'relationships',
            Event(
                'RELATIONSHIP_CREATE', {'user_id': user_id, 'type': 2}, user_id=user.id
            ),
        )

    return ''


@router.delete('/relationships/{user_id}', status_code=204)
async def delete_relationship(
    user_id: str, request: Request, response: Response, user: User | None = Depends(get_user)
) -> str:
    if user is None:
        raise NoAuthorizationError()

    target_user = await User.find_one(User.id == user_id)

    if target_user is None:
        raise HTTPException(404, 'User not found')

    current_relationship = await Relationship.find_one(
        Relationship.user_id == user.id, Relationship.target_id == user_id
    )

    if current_relationship.type in (0, 1):
        target_relationship = await Relationship.find_one(
            Relationship.user_id == current_relationship.target_id,
            Relationship.target_id == user.id,
        )

        await target_relationship.delete()

    await current_relationship.delete()

    await produce(
        'relationships',
        Event('RELATIONSHIP_DELETE', {'user_id': user_id}, user_id=user.id),
    )

    return ''
