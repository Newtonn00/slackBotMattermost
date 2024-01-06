import logging
import time
from typing import List

from slack_sdk.errors import SlackApiError
from slack_sdk import WebClient

from src.util.common_counter import CommonCounter
from src.util.settings_parser import SettingsParser
from src.entity.bookmark_entity import BookmarkEntity


class SlackLoadBookmarks:
    REQUEST_TIME_OUT = 408
    RATE_LIMITED_STATUS_CODE = 429
    CREATED = 201
    OK = 200

    def __init__(self):
        settings = SettingsParser()
        self._logger_bot = logging.getLogger("")
        self._web_client = WebClient(settings.slack_bot_token)
        self._slack_token = settings.slack_bot_token
        self._messages_per_page = 1004

    def _map_dict_to_bookmark_entity(self, data: dict) -> BookmarkEntity:
        bookmark_entity = BookmarkEntity(bookmark_slack_id=0,
                                         slack_channel_id=data["channel_id"],
                                         mm_channel_id='',
                                         created=data["date_created"],
                                         title=data["title"],
                                         link=data["link"])
        return bookmark_entity

    def load_bookmarks(self, channel_id: str) -> List[BookmarkEntity]:
        bookmarks = []
        try:
            max_retries = 3
            retry_count = 0

            while retry_count < max_retries:
                self._logger_bot.info(
                    "Starting request to Slack (bookmarks). %d times repeated",
                    retry_count)
                response = self._web_client.bookmarks_list(
                    channel_id=channel_id)
                response_code = response.status_code

                if response_code == self.OK:
                    bookmarks = response.data["bookmarks"]
                    break
                else:
                    retry_count += 1
                    time.sleep(2)
            if retry_count == max_retries:
                raise SlackApiError(message=f'Timeout after {retry_count} retries',
                                    response={"error": f' Timeout error, {self.REQUEST_TIME_OUT}'})
        except SlackApiError as e:
            self._logger_bot.error(
                f"SlackAPIError (bookmarks_list): {e.response['error']}")
            CommonCounter.increment_error()

        self._logger_bot.info("Selected %d bookmarks from Slack channel_id %s", len(bookmarks),
                              channel_id)

        bookmarks_entity: List[BookmarkEntity] = []
        for bookmark in bookmarks:
            bookmarks_entity.append(self._map_dict_to_bookmark_entity(bookmark))

        return bookmarks_entity
