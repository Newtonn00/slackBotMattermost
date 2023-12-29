import logging
import os
import time

import requests
from slack_sdk.errors import SlackApiError


class SlackMessagesHandler:

    REQUEST_TIME_OUT = 408
    RATE_LIMITED_STATUS_CODE = 429
    CREATED = 201
    OK = 200

    def __init__(self, web_client):

        self._logger_bot = logging.getLogger("")
        self._web_client = web_client.slack_web_client
        self._slack_bot_token = web_client.slack_bot_token
        self._messages_per_page = 100

    def load_threads(self, channel_id: str, ts_of_parent_message, oldest_date=0) -> list:
        try:
            response = self._web_client.conversations_replies(
                channel=channel_id,
                ts=ts_of_parent_message,
                oldest=oldest_date + 1
            )

            reply_messages = response["messages"][1:]
            self._logger_bot.info("Thread (%d messages) loaded", len(reply_messages))
        except SlackApiError as e:
            self._logger_bot.error(f"SlackAPIError (conversations_replies): {e.response['error']}")
            return []


        return reply_messages

    def download_files(self, files_attach: list) -> list:
        files_list = []
        for files in files_attach:
            if "url_private_download" not in files:
                break
            self._logger_bot.info(f'{files["name"]} is downloading')
            response_file = requests.get(files["url_private_download"],
                                         headers={
                                             'Authorization': 'Bearer %s' % self._slack_bot_token})
            if response_file.status_code == 200:
                local_file_path = os.environ.get('WORKDIR') + "/" + files["name"]

                try:
                    with open(local_file_path, "wb") as local_file:
                        for chunk in response_file.iter_content(chunk_size=8192):
                            local_file.write(chunk)
                    self._logger_bot.info(
                        f'File {files["name"]} is downloaded to {local_file_path}')
                except Exception:
                    self._logger_bot.error("Error in downloading as local file")

                files_dict = {
                    "file_name": files["name"],
                    "link": files["url_private_download"],
                    "user_id": files["user"],
                    "file_path": local_file_path}
                files_list.append(files_dict)
                self._logger_bot.info(f'{files["name"]} is downloaded from Slack')
            else:
                self._logger_bot.error(f'SlackAPIError (files): {response_file.json()}')
        return files_list
