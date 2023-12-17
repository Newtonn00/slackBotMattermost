from dataclasses import dataclass


@dataclass
class BookmarkEntity:
    bookmark_slack_id: int
    slack_channel_id: str
    mm_channel_id: str
    created: int
    title: str
    link: str
