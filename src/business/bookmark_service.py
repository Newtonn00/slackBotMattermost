import logging
from typing import List

from src.entity.bookmark_entity import BookmarkEntity
from src.util.common_counter import CommonCounter


class BookmarkService:
    _slack_channels_list: dict
    _mm_channels_list: list
    _slack_load_pins = None

    def __init__(self, slack_load_bookmarks, mattermost_bookmarks):
        self._slack_load_bookmarks = slack_load_bookmarks
        self._mattermost_bookmarks = mattermost_bookmarks
        self._channel_filter = []
        self._logger_bot = logging.getLogger("")
        self._session_id = None

    def bookmarks_process(self):
        self._apply_filter_to_mm_channel()
        self._apply_filter_to_slack_channel()
        for channel_key, channel_item in self._slack_channels_list.items():
            slack_bookmark_list = self._get_slack_bookmarks(channel_key)

            mm_channel_item = self._get_mm_channel_id_by_name(channel_item["name"])
            if mm_channel_item:
                mm_channel_id = mm_channel_item.get("id")
            else:
                self._logger_bot.info(f'Channel {channel_item["name"]} not found in Mattermost')
                CommonCounter.increment_error()
                break

            for bookmark in slack_bookmark_list:
                bookmark.mm_channel_id = mm_channel_id

            if slack_bookmark_list:
                bookmark_data = self._collect_bookmarks_data(slack_bookmark_list)
                self._mattermost_bookmarks.update_channel_header(bookmark_data, mm_channel_id, self._session_id)

    def _collect_bookmarks_data(self, bookmark_list: List[BookmarkEntity]) -> str:
        bookmark_data: str = ""
        for bookmark in bookmark_list:
            bookmark_data = bookmark_data + f'***{bookmark.title}***\n{bookmark.link}\n'
        return bookmark_data

    def _get_slack_bookmarks(self, channel_key) -> list[BookmarkEntity]:
        bookmark_entity: List[BookmarkEntity]
        bookmark_entity = self._slack_load_bookmarks.load_bookmarks(channel_key, self._session_id)
        return bookmark_entity

    def set_slack_channels_list(self, channels_list):
        self._slack_channels_list = channels_list

    def set_mm_channels_list(self, channels_list):
        self._mm_channels_list = channels_list

    def _get_mm_channel_id_by_name(self, channel_name: str) -> dict:
        mm_channel: dict = {}
        for channel in self._mm_channels_list:
            if channel["name"] == channel_name or (channel["display_name"] == channel_name):
                mm_channel = channel
                break
        return mm_channel

    def _get_slack_channel(self, channel_id: str) -> dict:
        slack_channel: dict = {}
        for channel_key, channel_item in self._slack_channels_list.items():
            if channel_key == channel_id:
                slack_channel = channel_item
                break
        return slack_channel

    def set_channel_filter(self, channel_filter: str):
        if len(channel_filter) != 0 and channel_filter != "all":
            self._channel_filter = channel_filter.split(" ")

    def _apply_filter_to_slack_channel(self):
        channels = self._slack_channels_list
        filtered_channels = {}
        for channel_id, channel_item in channels.items():
            if channel_item["name"] in self._channel_filter:
                filtered_channels[channel_id] = channel_item
        self._slack_channels_list = filtered_channels

    def _apply_filter_to_mm_channel(self):
        channels = self._mm_channels_list
        filtered_channels = []
        for channel in channels:
            if channel["name"] in self._channel_filter:
                filtered_channels.append(channel)
        self._mm_channels_list = filtered_channels

    def set_session_id(self, session_id):
        self._session_id = session_id
