# The Telescope API
#
# Copyright 2022 Telescope Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
from fastapi import HTTPException


class NoAuthorizationError(HTTPException):
    def __init__(self) -> None:
        super().__init__(401, 'No Authorization')
