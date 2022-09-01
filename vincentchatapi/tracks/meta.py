# The Vincent.chat API
#
# Copyright 2022 Vincent.chat Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from vincentchatapi.database import Track
from vincentchatapi.depends import get_user

router = APIRouter()


class ModifyTrack(BaseModel):
    name: str | None | bool = Field(default=False)
    topic: str | None = Field(None, max_length=1000, min_length=1)


# TODO: Implement Routes
