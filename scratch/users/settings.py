# The Derailed API
#
# Copyright 2022 Derailed. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from scratch.database import Message, Settings, User, produce
from scratch.depends import get_user
from scratch.exceptions import NoAuthorizationError

router = APIRouter()


class EditSettings(BaseModel):
    status: Literal['online', 'dnd', 'afk', 'invisible'] | None
    theme: Literal['dark', 'light'] | None


@router.get('/users/@me/settings')
async def get_settings(user: User | None = Depends(get_user)) -> dict:
    if user is None:
        raise NoAuthorizationError()

    settings = await Settings.find_one(Settings.id == user.id)
    return settings.dict(exclude={'id'})


@router.patch('/users/@me/settings')
async def patch_settings(
    model: EditSettings, user: User | None = Depends(get_user)
) -> dict:
    if user is None:
        raise NoAuthorizationError()

    settings = await Settings.find_one(Settings.id == user.id)

    if model.status and model.theme is None:
        return settings.dict(exclude={'id'})

    if model.status:
        settings.status = model.status

    if model.theme:
        settings.theme = model.theme

    await settings.save()
    settings_data = settings.dict(exclude={'id'})

    await produce('user', Message('SETTINGS_UPDATE', settings_data, user_id=user.id))

    return settings_data
