# The Derailed API
#
# Copyright 2022 Derailed Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
import os

from fastapi import Depends, Request
from slowapi import Limiter
from slowapi.util import get_ipaddr

from derailed.database import User
from derailed.depends import get_user


def get_rate_limit_key(request: Request, user: User | None = Depends(get_user)) -> str:
    return get_ipaddr(request=request) if user is None else user.id


def get_limiter() -> Limiter:
    return Limiter(
        key_func=get_rate_limit_key,
        default_limits=['50/second'],
        headers_enabled=True,
        strategy='fixed-window-elastic-expiry',
        storage_uri=os.getenv('STORAGE_URI'),
    )


rate_limiter = get_limiter()

track_limit = rate_limiter.shared_limit('20/second', 'track_id')
