import json
import logging

import requests
from requests import HTTPError

from src.controller.token_storage import TokenStorage
from src.entity.emoji_entity import EmojiEntity
from src.util.common_counter import CommonCounter


class MattermostEmojiHandler:
    def __init__(self, mattermost_web_client):
        self._main_user = None
        self._logger_bot = logging.getLogger("")
        self._web_client = mattermost_web_client
        self._mattermost_session = None

    def save(self, emoji: EmojiEntity, session_id: str) -> dict:
        result_dict = {"ok": True}
        response = ''
        if not self._mattermost_session:
            mm_token = TokenStorage.get_mm_token(session_id)
            self._mattermost_session = requests.Session()
            self._mattermost_session.headers.update({'Authorization': 'Bearer ' + mm_token})

        if not emoji.local_file_path:
            return
        try:
            headers = {'Content-Type': 'multipart/form-data'}
            emoji_data = {
                    "name": emoji.emoji_name,
                    "creator_id": self._main_user
            }
            files = {"image": open(emoji.local_file_path, 'rb')}
            data = {'emoji': json.dumps(emoji_data)}
            response = self._mattermost_session.post(
                f'{self._web_client.mattermost_url}/emoji', files=files, data=data)
            response.raise_for_status()
            data = response.json()
            self._logger_bot.info(f'Mattermost saved emoji {emoji.emoji_name} | Session:{session_id}')
            CommonCounter.increment_pin(session_id)

        except HTTPError as err:
            self._logger_bot.error(
                f'Mattermost API Error (emoji). Status code: {response.status_code} '
                f'Response:{response.text} Error:{err} Session:{session_id}')
            CommonCounter.increment_error(session_id)
            result_dict = {"ok": False}
        return result_dict

    def set_main_user(self, user_id):
        self._main_user = user_id
