import logging
import os

import requests
from slack_sdk.errors import SlackApiError
from slack_sdk import WebClient

from src.util.settings_parser import SettingsParser


class SlackLoadMessages:
    def __init__(self, web_client, config_service, messages_service, mattermost_upload_messages):
        settings = SettingsParser()
        self._logger_bot = logging.getLogger("")

        self._web_client = WebClient(settings.slack_bot_token)
        self._slack_token = settings.slack_bot_token
        self._config_service = config_service
        self._messages_service = messages_service
        self._mattermost_upload_messages = mattermost_upload_messages
        self._messages_per_page = 200
        self._channels_filter = []

    def load_channel_messages(self):
        channels = self.load_channels()
        self._messages_service.set_users_list(self.load_users())
        self._messages_service.set_channels_list(channels)
        self._logger_bot.info("Loading messages from public and private channels")
        for key, channel_info in channels.items():
            oldest_date = self._config_service.get_last_synchronize_date_unix(channel_name=channel_info["name"])
            new_start_date = oldest_date
            if self._config_service.is_allowed_channel(channel_info["name"]) and self._is_selected_channel(
                    channel_info["name"]):
                self._logger_bot.info("Start loading messages from channel %s, from date - %d", channel_info["name"],
                                      oldest_date)
                cursor = None
                while True:
                    try:
                        self._logger_bot.info("Starting request to Slack")
                        response = self._web_client.conversations_history(
                            channel=key,
                            limit=self._messages_per_page,
                            oldest=oldest_date + 1,
                            cursor=cursor
                        )
                    #                    self._logger_bot.info("Response: %s %s", response.status_code, response.data)

                    except SlackApiError as e:
                        self._logger_bot.error(
                            f"SlackAPIError (conversations_history): {e.response['error']}")
                        break

                    messages = response["messages"]
                    self._logger_bot.info("Selected %d messages from Slack channel %s", len(messages),
                                          channel_info["name"])
                    if not messages:
                        break
                    messages = reversed(messages)
                    for message in messages:
                        message["is_thread"] = False
                        if "reply_users" in message:
                            message["reply"] = self._load_threads(channel_id=key, oldest_date=oldest_date,
                                                                  ts_of_parent_message=message["ts"])
                            message["is_thread"] = True
                        message["channel"] = key
                        if new_start_date < float(message["ts"]):
                            new_start_date = float(message["ts"])

                        files_list = []
                        message["is_attached"] = False
                        if "files" in message:
                            files_list = self._download_files(message["files"])
                            message["is_attached"] = True
                            message["files"] = files_list
                        if "attachments" in message:
                            attachments = message["attachments"]
                            for attachment in attachments:
                                if "files" in attachment:
                                    files_list = self._download_files(attachment["files"])
                                    message["is_attached"] = True
                                    if "files" in message:
                                        message["files"].append(files_list)
                                    else:
                                        message["files"] = files_list

                        self._messages_service.save_messages_to_dict(message)
                        if message["is_thread"]:
                            for reply_message in message["reply"]:
                                if "files" in reply_message and reply_message["files"]:
                                    files_list.extend(reply_message["files"])

                        if files_list:
                            for files in files_list:
                                if os.path.exists(files["file_path"]):
                                    os.remove(files["file_path"])
                                    self._logger_bot.info("Deleted file %s from %s", files["file_name"],
                                                          files["file_path"])
                    if response["has_more"]:
                        cursor = response["response_metadata"]["next_cursor"]
                    else:
                        break

                self._config_service.set_last_synchronize_date_unix(new_start_date, channel_name=channel_info["name"])

    def load_direct_messages(self):
        channels = self.load_users_channels()
        self._logger_bot.info("Loading direct messages")
        for key, channel_info in channels.items():
            oldest_date = self._config_service.get_last_synchronize_date_unix(channel_name=channel_info["name"])
            new_start_date = oldest_date
            if self._is_selected_channel(channel_info["name"]):
                cursor = None
                while True:
                    try:
                        response = self._web_client.conversations_history(
                            channel=key,
                            limit=self._messages_per_page,
                            oldest=oldest_date + 1,
                            cursor=cursor
                        )
                    except SlackApiError as e:
                        self._logger_bot.error(
                            f"SlackAPIError (conversations_history): {e.response['error']}")
                        break
                    messages = response["messages"]
                    self._logger_bot.info("Selected %d messages by user %s", len(messages), channel_info["name"])

                    if not messages:
                        break

                    messages = reversed(messages)

                    for message in messages:
                        message["is_thread"] = False
                        if "reply_users" in message:
                            message["reply"] = self._load_threads(channel_id=key, oldest_date=oldest_date,
                                                                  ts_of_parent_message=message["ts"])
                            message["is_thread"] = True
                        message["channel"] = key
                        if new_start_date < float(message["ts"]):
                            new_start_date = float(message["ts"])

                        files_list = []
                        message["is_attached"] = False

                        if "files" in message:
                            files_list = self._download_files(message["files"])
                            message["is_attached"] = True
                            message["files"] = files_list
                        self._messages_service.save_messages_to_dict(message)
                        if files_list:
                            for files in files_list:
                                if os.path.exists(files["file_path"]):
                                    os.remove(files["file_path"])
                    if response["has_more"]:
                        cursor = response["response_metadata"]["next_cursor"]
                    else:
                        break

                self._config_service.set_last_synchronize_date_unix(new_start_date, channel_name=channel_info["name"])

    def _load_threads(self, channel_id, ts_of_parent_message, oldest_date) -> list:
        reply_messages = []
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
        thread_messages = []
        for reply in reply_messages:
            if "files" in reply:
                files_list = self._download_files(reply["files"])
                reply["files"] = files_list
            thread_messages.append(reply)

        return thread_messages

    def load_users(self) -> dict:
        try:
            user_list = self._web_client.users_list()["members"]
        except SlackApiError as e:
            self._logger_bot.error(f"SlackAPIError (users_list): {e.response['error']}")
            return {}

        users = {}
        for user in user_list:
            user_id = user.get("id")
            user_name = user.get("name")
            user_display_name = user["profile"].get("display_name")
            if user_display_name == "" or user_display_name is None:
                user_display_name = user.get("real_name")
            user_email = user["profile"].get("email") if "profile" in user and user["profile"] is not None else None
            user_is_bot = user.get("is_bot")
            user_first_name = user.get("first_name")
            user_last_name = user.get("last_name")
            user_is_deleted = user.get("is_deleted")
            users[user["id"]] = {"id": user_id, "name": user_name, "email": user_email, "is_bot": user_is_bot,
                                 "is_deleted": user_is_deleted, "first_name": user_first_name,
                                 "last_name": user_last_name, "display_name": user_display_name}

        self._logger_bot.info("Slack users loaded (%d)", len(users))
        return users

    def load_channels(self) -> dict:

        try:
            response = self._web_client.conversations_list(types="public_channel,private_channel",
                                                           limit=self._messages_per_page)
            channels_list = response["channels"]
            next_cursor = response["response_metadata"]["next_cursor"]

            while next_cursor:
                response = self._web_client.conversations_list(types="public_channel,private_channel",
                                                               limit=self._messages_per_page, cursor=next_cursor)
                channels_list.extend(response["channels"])
                next_cursor = response["response_metadata"]["next_cursor"]

        except SlackApiError as e:
            self._logger_bot.error(f"SlackAPIError (conversations_list types=public_channel,private_channel): "
                                   f"{e.response['error']}")
            return {}

        channels = {}
        for channel in channels_list:
            channel_id = channel["id"]
            channel_name = channel["name"]
            if channel["is_private"]:
                channel_type = "private"
            else:
                channel_type = "public"
            channels[channel["id"]] = {"id": channel_id, "name": channel_name, "type": channel_type}

        self._logger_bot.info("Slack channels loaded (%d)", len(channels))
        return channels

    def load_users_channels(self) -> dict:
        try:
            response = self._web_client.conversations_list(limit=self._messages_per_page, types="im,mpim")
            channels_list = response["channels"]
            next_cursor = response["response_metadata"]["next_cursor"]

            while next_cursor:
                response = self._web_client.conversations_list(types="im,mpim",
                                                               limit=self._messages_per_page, cursor=next_cursor)
                channels_list.extend(response["channels"])
                next_cursor = response["response_metadata"]["next_cursor"]
        except SlackApiError as e:
            self._logger_bot.error(f"SlackAPIError (conversations_list types=im,mpim): {e.response['error']}")
            return {}

        channels = {}
        for channel in channels_list:
            channel_id = channel["id"]
            if "name" in channel:
                channel_name = channel["name"]
            else:
                channel_name = channel["user"]

            channels[channel["id"]] = {"id": channel_id, "name": channel_name}
        self._logger_bot.info("Slack direct message channels loaded (%d)", len(channels))

        return channels

    def set_channels_filter(self, channel_filter: str):
        if len(channel_filter) != 0:
            self._channels_filter = channel_filter.split(" ")

    def _is_selected_channel(self, channel_name) -> bool:
        is_channel_selected = False
        if len(self._channels_filter) == 0:
            is_channel_selected = True
        else:
            for channel in self._channels_filter:
                if channel == channel_name:
                    is_channel_selected = True
                    break
        return is_channel_selected

    def _download_files(self, files_attach: list) -> list:
        files_list = []
        for files in files_attach:
            if files["timestamp"] == 0:
                break
            self._logger_bot.info(f'{files["name"]} is downloading')
            self._logger_bot.info("Files: %s", files)
            response_file = requests.get(files["url_private_download"],
                                         headers={
                                             'Authorization': 'Bearer %s' % self._slack_token})
            if response_file.status_code == 200:
                local_file_path = os.environ.get('WORKDIR') + "/" + files["name"]

                try:
                    with open(local_file_path, "wb") as local_file:
                        for chunk in response_file.iter_content(chunk_size=8192):
                            local_file.write(chunk)
                    self._logger_bot.info(
                        f'File {files["name"]} is downloaded to {local_file_path}')
                except Exception as e:
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
