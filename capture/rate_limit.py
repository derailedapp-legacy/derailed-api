# The Telescope API
#
# Copyright 2022 Telescope Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
import base64
import binascii
import os

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_ipaddr

from capture.database import User


def get_rate_limit_key(request: Request) -> str:
    try:
        token = request.headers['Authorization']
    except:
        return get_ipaddr(request=request)

    fragmented = token.split('.')
    encoded_user_id = fragmented[0]

    try:
        user_id = base64.b64decode(encoded_user_id.encode()).decode()
    except (ValueError, binascii.Error):
        return get_ipaddr(request=request)

    User

    return user_id


def get_limiter() -> Limiter:
    return Limiter(
        key_func=get_rate_limit_key,
        default_limits=['50/second'],
        headers_enabled=True,
        strategy='fixed-window-elastic-expiry',
        storage_uri=os.getenv('STORAGE_URI'),
    )
