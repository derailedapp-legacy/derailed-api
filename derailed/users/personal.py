# The Derailed API
#
# Copyright 2022 Derailed Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
from random import randint
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from derailed.database import (
    Event,
    Guild,
    Member,
    Presence,
    Profile,
    Settings,
    User,
    create_token,
    produce,
)
from derailed.depends import get_user
from derailed.exceptions import NoAuthorizationError
from derailed.identifier import make_snowflake

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


class Login(DeleteUser):
    email: EmailStr


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
async def register(model: Register, request: Request) -> dict:
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
    profile = Profile(id=user.id, bio=None)
    await user.insert()
    await settings.insert()
    await presence.insert()
    await profile.insert()

    formatted_user = user.dict(exclude={'password'})
    formatted_user['token'] = create_token(user_id=user_id, user_password=user.password)
    return formatted_user


@router.post('/login', status_code=200)
async def login(model: Login, request: Request) -> dict:
    user = await User.find_one(User.email == model.email)

    if user is None:
        raise HTTPException(400, 'Invalid email entered')

    try:
        ph.verify(user.password, model.password)
    except VerificationError:
        raise HTTPException(403, 'Incorrect password entered')

    return {'token': create_token(user_id=user.id, user_password=user.password)}


@router.get('/users/@me', status_code=200)
async def get_current_user(
    request: Request, user: User | None = Depends(get_user)
) -> dict:
    if user is None:
        raise NoAuthorizationError()

    return user.dict(exclude={'password'})


@router.patch('/users/@me', status_code=200)
async def patch_current_user(
    model: PatchUser, request: Request, user: User | None = Depends(get_user)
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

        await produce('security', Event('USER_DISCONNECT', {}, user_id=user.id))

    await user.save()

    user_data = user.dict(exclude={'password'})

    # TODO: Send this event to the users guilds
    await produce('user', Event('USER_UPDATE', user_data, user_id=user.id))

    return user_data


@router.post('/users/@me/delete', status_code=200)
async def delete_current_user(
    request: Request, model: DeleteUser, user: User | None = Depends(get_user)
):
    if user is None:
        raise NoAuthorizationError()

    try:
        ph.verify(user.password, model.password)
    except VerificationError:
        raise HTTPException(403, 'Incorrect password entered')

    guilds = Member.find(Member.user_id == user.id)

    async for guild_member in guilds:
        guild = await Guild.find_one(Guild.id == guild_member.guild_id)

        if guild.owner_id == user.id:
            raise HTTPException(403, 'You are still an owner of a guild')

    await guilds.delete()

    [
        await produce(
            'guild', Event('MEMBER_LEAVE', {'user_id': user.id, 'guild_id': guild.id})
        )
        async for guild in guilds
    ]

    settings = await User.find_one(Settings.user_id == user.id)

    await produce('security', Event('USER_DISCONNECT', {}, user_id=user.id))

    user.delete()
    settings.delete()

    return ''


@router.post('/genshin-impact', status_code=204)
async def science(
    model: Analytic, request: Request, unused_user: User | None = Depends(get_user)
):
    if unused_user is None:
        raise NoAuthorizationError()

    return ''


@router.post('/profiles/@me', status_code=200)
async def get_current_profile(request: Request, user: User | None = Depends(get_user)):
    if user is None:
        raise NoAuthorizationError()

    profile = await Profile.find_one(Profile.id == user.id)
    return profile.dict(exclude={'id'})


@router.post('/profiles/{user_id}', status_code=200)
async def get_user_profile(
    request: Request, user_id: str, user: User | None = Depends(get_user)
):
    if user is None:
        raise NoAuthorizationError()

    profile = await Profile.find_one(Profile.id == user_id)

    if profile is None:
        raise HTTPException(404, 'User does not exist')

    return profile.dict(exclude={'id'})
