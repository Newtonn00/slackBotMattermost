import logging
import os
import time

import requests
from slack_sdk.errors import SlackApiError


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

    def load(self) -> list:
        try:

            max_retries = 3
            retry_count = 0
            user_list = []
            while retry_count < max_retries:
                self._logger_bot.info("Starting request to Slack (users). %d times repeated",
                                      retry_count)

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
            self._logger_bot.error(f"SlackAPIError (users_list): {e.response['error']}")
            return []
        self._logger_bot.info("Slack users loaded (%d)", len(user_list))
        return user_list

    def load_profile_image(self, image_link: str, user_id: str) -> str:
        local_file_path = ""
        self._logger_bot.info(f'{image_link} is downloading')
        response_file = requests.get(image_link, stream=True)
        if response_file.status_code == 200:
            local_file_path = os.environ.get('WORKDIR') + "/" + user_id + ".jpg"

            try:
                with open(local_file_path, "wb") as local_file:
                    for chunk in response_file.iter_content(chunk_size=8192):
                        local_file.write(chunk)
                self._logger_bot.info(
                    f'File is downloaded to {local_file_path}')
            except Exception:
                self._logger_bot.error("Error in downloading as local file")
        else:
            self._logger_bot.error(f'SlackAPIError (files): {response_file.json()}')

        return local_file_path

