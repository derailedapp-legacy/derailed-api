# The Derailed API
#
# Copyright 2022 Derailed Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from derailed.database import Event, Presence, User, produce
from derailed.depends import get_user
from derailed.exceptions import NoAuthorizationError

router = APIRouter()


class PutPresence(BaseModel):
    content: str = Field(max_length=128, min_length=1)


@router.put('/users/@me/presence', status_code=204)
async def put_presence(
    model: PutPresence, request: Request, user: User | None = Depends(get_user)
) -> str:
    if user is None:
        raise NoAuthorizationError()

    presence = await Presence.find_one(Presence.id == user.id)

    await presence.update(content=model.content)

    await produce(
        'presences', Event('PRESENCE_UPDATE', presence.dict(), user_id=user.id)
    )

    return ''
