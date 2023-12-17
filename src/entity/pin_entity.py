from dataclasses import dataclass


@dataclass
class PinEntity:
    pin_id: int
    slack_channel_id: str
    mm_channel_id: str
    created: int
    message_mm_id: str
    message_ts: str
