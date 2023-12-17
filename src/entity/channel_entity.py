from dataclasses import dataclass
from enum import Enum


class ChannelTypeEnum(Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    DIRECT_MESSAGE = "dm"


@dataclass
class ChannelEntity:
    channel_id: str
    channel_name: str
    channel_type: ChannelTypeEnum
