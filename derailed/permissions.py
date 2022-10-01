# The Derailed API
#
# Copyright 2022 Derailed Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
import itertools

# NOTE: enums in the standard python implementation aren't really the fastest.
# is there a better way to do this?
from enum import IntFlag
from typing import TypedDict


def has_bit(value: int, visible: int) -> bool:
    return True if value & 1 << 9 else bool(value & visible)


class PermissionValue(TypedDict):
    position: int
    value: int


class RolePermissionEnum(IntFlag):
    MODIFY_GUILD = 1 << 0
    KICK_USERS = 1 << 1
    MODIFY_MEMBERS = 1 << 2
    MODIFY_MEMBER_NICKNAMES = 1 << 3
    BAN_MEMBERS = 1 << 4
    CREATE_TRACK = 1 << 5
    MODIFY_TRACK = 1 << 6
    DELETE_TRACKS = 1 << 7
    MANAGE_ROLES = 1 << 8
    ADMINISTRATOR = 1 << 9
    CREATE_MESSAGE = 1 << 10
    DELETE_MESSAGES = 1 << 11
    VIEW_MESSAGE_HISTORY = 1 << 12


def combine_role_permission_values(*permission_values: PermissionValue):
    modified_value = 0
    _internal = []

    for value in permission_values:
        _internal.insert(value['position'], value['value'])

    for value, permission_value in itertools.product(_internal, RolePermissionEnum):
        if has_bit(modified_value, permission_value.value) and not has_bit(
            value, permission_value.value
        ):
            modified_value -= permission_value.value
        elif not has_bit(modified_value, permission_value.value) and has_bit(
            value, permission_value.value
        ):
            modified_value |= permission_value.value
        else:
            continue

    return modified_value
