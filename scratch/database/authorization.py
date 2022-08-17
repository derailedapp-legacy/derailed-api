# The Itch API
#
# Copyright 2022 Itch. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
import base64
import binascii

import itsdangerous
from fastapi import HTTPException

from .models import User


def create_token(user_id: str, user_password: str) -> str:
    signer = itsdangerous.TimestampSigner(user_password)
    user_id = base64.b64encode(user_id.encode())

    return signer.sign(user_id).decode()


async def verify_token(token: str) -> User:
    fragmented = token.split('.')
    encoded_user_id = fragmented[0]

    try:
        user_id = base64.b64decode(encoded_user_id.encode()).decode()
    except (ValueError, binascii.Error):
        raise HTTPException(401, 'Unauthorized')

    user = await User.find_one(User.id == user_id)

    if user is None:
        raise HTTPException(401, 'Unauthorized')

    signer = itsdangerous.TimestampSigner(user.password)

    try:
        signer.unsign(token)

        return user
    except (itsdangerous.BadSignature):
        raise HTTPException(401, 'Unauthorized')
