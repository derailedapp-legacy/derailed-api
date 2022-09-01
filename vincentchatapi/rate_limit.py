# The Vincent.chat API
#
# Copyright 2022 Vincent.chat Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
import os

from fastapi import Depends, Request
from slowapi import Limiter
from slowapi.util import get_ipaddr

from vincentchatapi.database import User
from vincentchatapi.depends import get_user


async def get_rate_limit_key(
    request: Request, user: User | None = Depends(get_user)
) -> str:
    return get_ipaddr(request=request) if user is None else user.id


def get_limiter() -> Limiter:
    return Limiter(
        key_func=get_rate_limit_key,
        default_limits=['50/second'],
        headers_enabled=True,
        strategy='fixed-window-elastic-expiry',
        storage_uri=os.getenv('STORAGE_URI'),
    )
