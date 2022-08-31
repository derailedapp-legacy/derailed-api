# The Felladex API
#
# Copyright 2022 Felladex Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from felladex.database import Track
from felladex.depends import get_user

router = APIRouter()


class ModifyTrack(BaseModel):
    name: str | None | bool = Field(default=False)
    topic: str | None = Field(None, max_length=1000, min_length=1)


# TODO: Implement Routes
