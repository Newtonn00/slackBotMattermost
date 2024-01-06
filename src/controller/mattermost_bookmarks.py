import logging
from typing import List

from requests import HTTPError

from src.entity.bookmark_entity import BookmarkEntity
from src.util.common_counter import CommonCounter


class MattermostBookmarks:

    def __init__(self, mattermost_web_client):
        self._logger_bot = logging.getLogger("")
        self._mm_web_client = mattermost_web_client
        self._messages_per_page = 100

    def update_channel_header(self, bookmark: str, channel_id: str):
        response = ''
        json_data = {

            "id": channel_id,
            "header": bookmark
        }
        try:

            response = self._mm_web_client.mattermost_session.put(
                f'{self._mm_web_client.mattermost_url}/channels/{channel_id}',json=json_data)
            response.raise_for_status()
            data = response.json()
            self._logger_bot.info("Mattermost channels %s header updated", channel_id)

        except HTTPError as err:
            self._logger_bot.error(
                f'Mattermost API Error (channels header). Status code: {response.status_code} Response:{response.text} '
                f'Error: {err}')
            CommonCounter.increment_error()
