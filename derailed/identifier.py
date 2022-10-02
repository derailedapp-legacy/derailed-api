# The Derailed API
#
# Copyright 2022 Derailed Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
import os
import secrets
import threading
import time
from random import randint

INCREMENTATION: int = 0
EPOCH: int = 1641042000000


def make_snowflake() -> str:
    global INCREMENTATION

    current_ms = int(time.time() * 1000)
    epoch = current_ms - EPOCH << 22

    curthread = threading.current_thread().ident
    if curthread is None:
        raise AssertionError

    epoch |= (curthread % 32) << 17
    epoch |= (os.getpid() % 32) << 12

    epoch |= INCREMENTATION % 4096

    if INCREMENTATION == 9000000000:
        INCREMENTATION = 0

    INCREMENTATION += 1

    return str(epoch)


def make_invite() -> str:
    return secrets.token_urlsafe(randint(4, 7))


if __name__ == '__main__':
    while True:
        import sys

        print(make_snowflake(), file=sys.stderr)
