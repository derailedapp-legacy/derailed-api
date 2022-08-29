# The Derailed API
#
# Copyright 2022 Derailed Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
import os
from random import randint
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from valve.database import Message, Presence, Settings, User, create_token, produce
from valve.depends import get_user
from valve.exceptions import NoAuthorizationError
from valve.identifier import make_snowflake

ph = PasswordHasher()

router = APIRouter(tags=['User'])


class Register(BaseModel):
    email: EmailStr
    username: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=128)


class PatchUser(BaseModel):
    email: EmailStr
    username: str | None = Field(min_length=1, max_length=200)
    password: str | None = Field(min_length=1, max_length=128)


class DeleteUser(BaseModel):
    password: str | None = Field(min_length=1, max_length=128)


class Analytic(BaseModel):
    type: str
    data: dict[str, Any] | list[dict[str, Any] | str | int] | str | int


def generate_discriminator_number() -> str:
    discrim_number = randint(1, 9999)
    return '%04d' % discrim_number


async def find_discriminator(username: str) -> str:
    for _ in range(10):
        number = generate_discriminator_number()

        exists = await User.find_one(
            User.username == username, User.discriminator == number
        )

        if exists is None:
            return number

    raise HTTPException(400, 'Unable to find discriminator for this username')


@router.post('/register', status_code=201)
async def register(model: Register) -> dict:
    usage = await User.find(User.username == model.username).count()

    if usage == 9000:
        raise HTTPException(400, 'Too many people have used this username')

    user_id = make_snowflake()

    user = User(
        id=user_id,
        email=model.email,
        username=model.username,
        password=ph.hash(model.password),
        discriminator=await find_discriminator(username=model.username),
    )
    settings = Settings(id=user_id)
    presence = Presence(id=user.id, status='offline', content=None, timestamp=None)
    await user.insert()
    await settings.insert()
    await presence.insert()

    formatted_user = user.dict(exclude={'password'})
    formatted_user['token'] = create_token(user_id=user_id, user_password=user.password)
    return formatted_user


@router.get('/users/@me', status_code=200)
async def get_current_user(user: User | None = Depends(get_user)) -> dict:
    if user is None:
        raise NoAuthorizationError()

    return user.dict(exclude={'password'})


@router.patch('/users/@me', status_code=200)
async def patch_current_user(
    model: PatchUser, user: User | None = Depends(get_user)
) -> dict:
    if user is None:
        raise NoAuthorizationError()

    if model.email:
        user.email = model.email

    if model.username:
        user.username = model.username
        exists = await User.find_one(
            User.username == model.username,
            User.discriminator == user.discriminator,
        )

        if exists:
            user.discriminator = await find_discriminator(model.username)

    if model.password:
        user.password = ph.hash(model.password)

        await produce('security', Message('USER_DISCONNECT', {}, user_id=user.id))

    await user.save()

    user_data = user.dict(exclude={'password'})

    # TODO: Send this event to the users guilds
    await produce('user', Message('USER_UPDATE', user_data, user_id=user.id))

    return user_data


@router.post('/users/@me/delete', status_code=200)
async def delete_current_user(model: DeleteUser, user: User | None = Depends(get_user)):
    if user is None:
        raise NoAuthorizationError()

    try:
        ph.verify(user.password, model.password)
    except VerificationError:
        raise HTTPException(403, 'Incorrect password entered')

    settings = await User.find_one(Settings.user_id == user.id)

    await produce('security', Message('USER_DISCONNECT', {}, user_id=user.id))

    user.delete()
    settings.delete()

    return ''


@router.post('/genshin-impact', status_code=204)
async def science(model: Analytic, user: User | None = Depends(get_user)):
    return ''
