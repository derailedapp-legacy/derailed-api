# The Telescope API
#
# Copyright 2022 Telescope Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
from random import randint
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, EmailStr, Field

from capture.database import Settings, User, create_token, verify_token
from capture.identifier import make_snowflake

ph = PasswordHasher()


router = APIRouter(tags=['User'])


class Register(BaseModel):
    email: EmailStr = Field(min_length=5, max_length=128)
    username: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=128)


class PatchUser(BaseModel):
    email: EmailStr | None = Field(min_length=5, max_length=128)
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
        user_id=user_id,
        email=model.email,
        username=model.username,
        password=ph.hash(model.password),
    )
    settings = Settings(user_id=user_id)
    await user.insert()
    await settings.insert()

    formatted_user = user.dict(exclude=['password'])
    formatted_user['token'] = create_token(user_id=user_id, user_password=user.password)
    return formatted_user


@router.get('/users/@me', status_code=200)
async def get_current_user(authorization: str | None = Header(None)) -> dict:
    user = await verify_token(authorization)

    return user.dict(exclude=['password'])


@router.patch('/users/@me', status_code=200)
async def patch_current_user(
    model: PatchUser, authorization: str | None = Header(None)
) -> dict:
    user = await verify_token(authorization)

    if model.email:
        user.email = model.email

    if model.password:
        user.password = ph.hash(model.password)

    if model.username:
        user.username = model.username
        exists = await User.find_one(
            User.username == model.username,
            User.discriminator == user.discriminator,
        )

        if exists:
            user.discriminator = await find_discriminator(model.username)

    await user.save()

    return user.dict(exclude=['password'])


@router.post('/users/@me/delete', status_code=200)
async def delete_current_user(
    model: DeleteUser, authorization: str | None = Header(None)
):
    user = await verify_token(authorization)

    try:
        ph.verify(user.password, model.password)
    except VerificationError:
        raise HTTPException(403, 'Incorrect password entered')

    settings = await User.find_one(Settings.user_id == user.id)

    user.delete()
    settings.delete()


@router.post('/genshin-impact', status_code=204)
async def science(model: Analytic, authorization: str | None = Header(None)):
    return ''
