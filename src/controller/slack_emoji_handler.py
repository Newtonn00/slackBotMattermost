import logging
import time
from typing import List

import requests
from slack_sdk.errors import SlackApiError

from src.controller.token_storage import TokenStorage
from src.entity.emoji_entity import EmojiEntity
from src.util.common_counter import CommonCounter
from src.util.settings_parser import SettingsParser


class SlackEmojiHandler:
    REQUEST_TIME_OUT = 408
    RATE_LIMITED_STATUS_CODE = 429
    CREATED = 201
    OK = 200

    def __init__(self, slack_web_client):
        self._web_client = slack_web_client.get_web_instance()
        self._main_user_id = None
        self._logger_bot = logging.getLogger("")
        self._slack_token = None

    def _map_dict_to_emoji_entity(self, data: dict) -> EmojiEntity:
        emoji_entity = EmojiEntity(emoji_name=list(data.keys())[0],
                                   emoji_image=list(data.values())[0],
                                   local_file_path="")
        return emoji_entity

    def load(self, session_id) -> List[EmojiEntity]:

        self._slack_token = TokenStorage.get_slack_token(session_id)
        response_data = None
        try:
            max_retries = 3
            retry_count = 0
            self._logger_bot.info(
                f"Starting request to Slack (emoji) | Session: {session_id}")
            while retry_count < max_retries:

                response = self._web_client.emoji_list()
                response_code = response.status_code

                if response_code == self.OK:
                    response_data = response.data
                    break
                else:
                    retry_count += 1
                    time.sleep(2)
            if retry_count == max_retries:
                raise SlackApiError(message=f'Timeout after {retry_count} retries',
                                    response={"error": f' Timeout error, {self.REQUEST_TIME_OUT} '
                                                       f'| Session: {session_id}'})
        except SlackApiError as e:
            self._logger_bot.error(
                f"SlackAPIError (pin_list): {e.response['error']} "
                f"Session: {session_id}")
            CommonCounter.increment_error(session_id)

        emoji_entity: List[EmojiEntity] = []
        if "emoji" in response_data:
            for emoji in list(response_data["emoji"].items()):
                em_dict = dict([emoji])
                emoji_entity.append(self._map_dict_to_emoji_entity(dict([emoji])))

        self._logger_bot.info(f'Selected {len(emoji_entity)} emoji from Slack '
                              f'| Session: {session_id}')

        for emoji in emoji_entity:
            emoji.local_file_path = self.download_image(emoji, session_id)

        return emoji_entity

    def set_main_user(self, user_id):
        self._main_user_id = user_id

    def download_image(self, emoji: EmojiEntity, session_id: str) -> str:
        local_file_path = ""
        response_file = None
        try:
            response_file = requests.get(emoji.emoji_image,
                                             headers={
                                             'Authorization': 'Bearer %s' % self._slack_token})
        except Exception as err:
            self._logger_bot.error(f'Error in downloading {emoji.emoji_name} as local file | '
                                   f'Session: {session_id}')
            CommonCounter.increment_error(session_id)
        if response_file and response_file.status_code == 200:
            local_file_path = emoji.emoji_name + ".png"

            #local_file_path = self._shorten_filename(local_file_path)

            try:
                with open(local_file_path, "wb") as local_file:
                    for chunk in response_file.iter_content(chunk_size=8192):
                        local_file.write(chunk)
                self._logger_bot.info(
                    f'File {local_file_path} is downloaded | '
                    f'Session: {session_id}')
            except Exception:
                self._logger_bot.error(f'Error in downloading as local file | '
                                       f'Session: {session_id}')
                CommonCounter.increment_error(session_id)
        return local_file_path
