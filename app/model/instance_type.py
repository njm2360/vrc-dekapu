from enum import StrEnum


class InstanceType(StrEnum):
    PUBLIC = "public"
    HIDDEN = "hidden"
    FRIENDS = "friends"
    PRIVATE = "private"
    GROUP = "group"
