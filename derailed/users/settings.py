# The Derailed API
#
# Copyright 2022 Derailed Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
from typing import Literal

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from derailed.database import Event, Presence, Settings, User, produce
from derailed.depends import get_user
from derailed.exceptions import NoAuthorizationError

router = APIRouter()


class EditSettings(BaseModel):
    status: Literal['online', 'dnd', 'afk', 'invisible'] | None
    theme: Literal['dark', 'light'] | None


@router.get('/users/@me/settings')
async def get_settings(request: Request, response: Response, user: User | None = Depends(get_user)) -> dict:
    if user is None:
        raise NoAuthorizationError()

    settings = await Settings.find_one(Settings.id == user.id)
    return settings.dict(exclude={'id'})


@router.patch('/users/@me/settings')
async def patch_settings(
    model: EditSettings, request: Request, response: Response, user: User | None = Depends(get_user)
) -> dict:
    if user is None:
        raise NoAuthorizationError()

    settings = await Settings.find_one(Settings.id == user.id)

    if model.status and model.theme is None:
        return settings.dict(exclude={'id'})

    if model.status:
        settings.status = model.status

        presence = await Presence.find_one(Presence.id == settings.id)
        if presence.timestamp:
            await presence.update(
                status=model.status if model.status != 'invisible' else 'offline'
            )

    if model.theme:
        settings.theme = model.theme

    await settings.save()
    settings_data = settings.dict(exclude={'id'})

    await produce('user', Event('SETTINGS_UPDATE', settings_data, user_id=user.id))

    return settings_data
