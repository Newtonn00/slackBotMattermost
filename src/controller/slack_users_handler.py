import logging
import os
import time

import requests
from slack_sdk.errors import SlackApiError

from src.util.common_counter import CommonCounter


class SlackUsersHandler:
    REQUEST_TIME_OUT = 408
    RATE_LIMITED_STATUS_CODE = 429
    CREATED = 201
    OK = 200

    def __init__(self, web_client):

        self._logger_bot = logging.getLogger("")
        self._web_client = web_client.slack_web_client
        self._slack_bot_token = web_client.slack_bot_token
        self._messages_per_page = 100

    def load(self, session_id: str) -> list:
        try:

            max_retries = 3
            retry_count = 0
            user_list = []
            while retry_count < max_retries:
                self._logger_bot.info(f"Starting request to Slack (users). {retry_count} times repeated | "
                                      f"Session: {session_id}")

                response = self._web_client.users_list()

                response_code = response.status_code

                if response_code == self.OK:
                    user_list = response["members"]
                    break
                else:
                    retry_count += 1
                    time.sleep(5)
            if retry_count == max_retries:
                raise SlackApiError(message=f'Timeout after {retry_count} retries',
                                    response={"error": f' Timeout error, {self.REQUEST_TIME_OUT}'})

        except SlackApiError as e:
            self._logger_bot.error(f"SlackAPIError (users_list): {e.response['error']}"
                                   f" Session: {session_id}")
            CommonCounter.increment_error(session_id)
            return []
        self._logger_bot.info(f"Slack users loaded ({len(user_list)}) | Session: {session_id}")
        return user_list

    def load_profile_image(self, image_link: str, user_id: str, session_id: str) -> str:
        local_file_path = ""
        self._logger_bot.info(f'{image_link} is downloading'
                              f' | Session: {session_id}')
        response_file = requests.get(image_link, stream=True)
        if response_file.status_code == 200:
            local_file_path = os.environ.get('WORKDIR') + "/" + user_id + ".jpg"

            try:
                with open(local_file_path, "wb") as local_file:
                    for chunk in response_file.iter_content(chunk_size=8192):
                        local_file.write(chunk)
                self._logger_bot.info(
                    f'File is downloaded to {local_file_path}'
                    f' | Session: {session_id}')
            except Exception:
                self._logger_bot.error(f"Error in downloading as local file | Session: {session_id}")
                CommonCounter.increment_error(session_id)
        else:
            self._logger_bot.error(f'SlackAPIError (files): {response_file.json()}'
                                   f' Session: {session_id}')
            CommonCounter.increment_error(session_id)

        return local_file_path
