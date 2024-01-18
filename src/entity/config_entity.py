from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List


@dataclass
class Channels:
    channel: str


@dataclass
class DateSynchroniseUtc:
    channel_name: str
    last_datetime_synchronize_utc: datetime


@dataclass
class ConfigEntity:
    slack_id: int
    last_datetime_synchronize: List[DateSynchroniseUtc]
    excluded_channels: list[Channels]
    excluded_users: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, data):
        return cls(
            slack_id=data.get('config_id'),
            last_datetime_synchronize=data.get("last_datetime_synchronize"),
            excluded_channels=data.get('excluded_channels'),
            excluded_users=data.get('excluded_users')
        )

    def as_dict(self) -> dict:
        return asdict(self)
