import logging
import os
import time

import requests
from slack_sdk.errors import SlackApiError
from slack_sdk import WebClient

from src.util.settings_parser import SettingsParser


class SlackLoadMessages:
    REQUEST_TIME_OUT = 408
    RATE_LIMITED_STATUS_CODE = 429
    CREATED = 201
    OK = 200

    def __init__(self, web_client, config_service, messages_service, pin_service, bookmark_service):
        settings = SettingsParser()

        self._logger_bot = logging.getLogger("")
        self._channels_list = {}
        self._users_list = []
        self._web_client = WebClient(settings.slack_bot_token)
        self._slack_token = settings.slack_bot_token
        self._config_service = config_service
        self._messages_service = messages_service
        self._pin_service = pin_service
        self._bookmark_service = bookmark_service

        self._messages_per_page = 100
        self._channel_filter = []

    def load_channel_messages(self):

        self.load_channels()
        self.load_users()
        self._messages_service.set_users_list(self._users_list)
        self._messages_service.set_channels_list(self._channels_list)
        self._pin_service.set_slack_channels_list(self._channels_list)
        self._bookmark_service.set_slack_channels_list(self._channels_list)

        self._logger_bot.info("Loading messages from public and private channels")
        for channel_id, channel_item in self._channels_list.items():
            if self._is_selected_channel(channel_item["name"]) and self._config_service.is_allowed_channel(
                    channel_item["name"]):
                oldest_date = self._config_service.get_last_synchronize_date_unix(channel_name=channel_item["name"])
                new_start_date = oldest_date
                self._logger_bot.info("Start loading messages from channel %s, from date - %d", channel_item["name"],
                                      oldest_date)
                cursor = None

                messages = []
                while True:
                    try:
                        max_retries = 3
                        retry_count = 0

                        while retry_count < max_retries:
                            self._logger_bot.info(
                                "Starting request to Slack (conversations_history). %d times repeated",
                                retry_count)
                            response = self._web_client.conversations_history(
                                channel=channel_item["id"],
                                limit=self._messages_per_page,
                                oldest=oldest_date + 1,
                                cursor=cursor
                            )
                            response_code = response.status_code

                            if response_code == self.OK:
                                message_for_sort = response["messages"]
                                message_for_sort = reversed(message_for_sort)
                                messages.extend(message_for_sort)
                                break
                            else:
                                retry_count += 1
                                time.sleep(2)
                        if retry_count == max_retries:
                            raise SlackApiError(message=f'Timeout after {retry_count} retries',
                                                response={"error": f' Timeout error, {self.REQUEST_TIME_OUT}'})
                        if response["has_more"]:
                            cursor = response["response_metadata"]["next_cursor"]
                        else:
                            break
                    except SlackApiError as e:
                        self._logger_bot.error(
                            f"SlackAPIError (conversations_history): {e.response['error']}")
                        break

                self._logger_bot.info("Selected %d messages from Slack channel %s", len(messages),
                                      channel_item["name"])

                for message in messages:
                    message["is_thread"] = False
                    if "reply_users" in message:
                        message["reply"] = self._load_threads(channel_id=channel_item["id"], oldest_date=oldest_date,
                                                              ts_of_parent_message=message["ts"])
                        message["is_thread"] = True
                    message["channel"] = channel_item["id"]
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

                    self._config_service.set_last_synchronize_date_unix(new_start_date,
                                                                        channel_name=channel_item["name"])

    def _load_threads(self, channel_id, ts_of_parent_message, oldest_date) -> list:
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

    def load_users(self):
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
            return
        users = {}
        for user in user_list:
            user_id = user.get("id")
            user_name = user.get("name")
            user_display_name = user["profile"].get("display_name")
            if user_display_name == "" or user_display_name is None:
                user_display_name = user.get("real_name")
            if user_display_name == "" or user_display_name is None:
                user_display_name = user_name
            user_email = user["profile"].get("email") if "profile" in user and user["profile"] is not None else None
            user_is_bot = user.get("is_bot")
            user_first_name = user["profile"].get("first_name")
            user_last_name = user["profile"].get("last_name")
            user_is_deleted = user.get("deleted")
            users[user["id"]] = {"id": user_id, "name": user_name, "email": user_email, "is_bot": user_is_bot,
                                 "is_deleted": user_is_deleted, "first_name": user_first_name,
                                 "last_name": user_last_name, "display_name": user_display_name}

        self._logger_bot.info("Slack users loaded (%d)", len(users))
        self.set_users_list(users)

    def load_channels(self):

        try:

            max_retries = 3
            retry_count = 0
            channels_list = []
            while retry_count < max_retries:
                self._logger_bot.info("Starting request to Slack (channels). %d times repeated",
                                      retry_count)

                response = self._web_client.conversations_list(types="public_channel,private_channel",
                                                               limit=self._messages_per_page)
                response_code = response.status_code
                if response_code == self.OK:

                    channels_list = response["channels"]
                    self._logger_bot.info("Loaded %s channels", len(response["channels"]))
                    break
                else:
                    retry_count += 1
                    time.sleep(5)

            if retry_count == max_retries:
                raise SlackApiError(message=f'Timeout after {retry_count} retries',
                                    response={"error": f' Timeout error, {self.REQUEST_TIME_OUT}'})

            next_cursor = response["response_metadata"]["next_cursor"]

            while next_cursor:
                max_retries = 3
                retry_count = 0
                while retry_count < max_retries:
                    self._logger_bot.info("Starting request to Slack (channels). %d times repeated",
                                          retry_count)
                    response = self._web_client.conversations_list(types="public_channel,private_channel",
                                                                   limit=self._messages_per_page, cursor=next_cursor)
                    response_code = response.status_code
                    if response_code == self.OK:

                        channels_list.extend(response["channels"])
                        self._logger_bot.info("Loaded %s channels", len(response["channels"]))
                        next_cursor = response["response_metadata"]["next_cursor"]
                        self._logger_bot.info("Slack channels loaded (%d)", len(channels_list))
                        break
                    else:
                        retry_count += 1
                        time.sleep(5)

                    if retry_count == max_retries:
                        raise SlackApiError(message=f'Timeout after {retry_count} retries',
                                            response={"error": f' Timeout error, {self.REQUEST_TIME_OUT}'})

        except SlackApiError as e:
            self._logger_bot.error(f"SlackAPIError (conversations_list types=public_channel,private_channel): "
                                   f"{e.response['error']}")
            return

        try:

            max_retries = 3
            retry_count = 0
            channels_users_list = []
            while retry_count < max_retries:
                self._logger_bot.info("Starting request to Slack (dm-channels). %d times repeated",
                                      retry_count)

                response = self._web_client.conversations_list(limit=self._messages_per_page, types="im,mpim")
                response_code = response.status_code
                if response_code == self.OK:
                    channels_users_list = response["channels"]
                    next_cursor = response["response_metadata"]["next_cursor"]
                    break
                else:
                    retry_count += 1
                    time.sleep(5)

            if retry_count == max_retries:
                raise SlackApiError(message=f'Timeout after {retry_count} retries',
                                    response={"error": f' Timeout error, {self.REQUEST_TIME_OUT}'})

            while next_cursor:
                max_retries = 3
                retry_count = 0
                channels_users_list = []
                while retry_count < max_retries:
                    self._logger_bot.info("Starting request to Slack (dm-channels). %d times repeated",
                                          retry_count)

                    response_code = response.status_code
                    if response_code == self.OK:

                        response = self._web_client.conversations_list(types="im,mpim",
                                                                       limit=self._messages_per_page,
                                                                       cursor=next_cursor)
                        channels_users_list.extend(response["channels"])
                        next_cursor = response["response_metadata"]["next_cursor"]
                        break
                    else:
                        retry_count += 1
                        time.sleep(5)

                if retry_count == max_retries:
                    raise SlackApiError(message=f'Timeout after {retry_count} retries',
                                        response={"error": f' Timeout error, {self.REQUEST_TIME_OUT}'})

            self._logger_bot.info("Slack direct messages channels loaded (%d)", len(channels_users_list))
        except SlackApiError as e:
            self._logger_bot.error(f"SlackAPIError (conversations_list types=im,mpim): {e.response['error']}")
            return

        channels = {}
        for channel in channels_list:
            channel_id = channel["id"]
            channel_name = channel["name"]
            if channel["is_private"]:
                channel_type = "private"
            else:
                channel_type = "public"
            channels[channel["id"]] = {"id": channel_id, "name": channel_name, "type": channel_type}

        for channel in channels_users_list:
            if "name" in channel:
                channel_name = channel["name"]
            else:
                channel_name = channel["user"]
            channel_id = channel["id"]
            channel_type = "direct"
            channels[channel["id"]] = {"id": channel_id, "name": channel_name, "type": channel_type}

        self.set_channels_list(channels)

        for channel in channels:
            if self._is_selected_channel(self._get_channel(channel)["name"]) \
                    and self._config_service.is_allowed_channel(self._get_channel(channel)["name"]):
                members = self._load_channel_members(channel)
                self._set_channels_members(channel, members)

    def _load_channel_members(self, channel_id: str) -> list:

        try:

            max_retries = 3
            retry_count = 0
            members_list = []
            while retry_count < max_retries:
                self._logger_bot.info("Starting request to Slack (channels/members). %d times repeated",
                                      retry_count)

                response = self._web_client.conversations_members(channel=channel_id,
                                                                  limit=self._messages_per_page)
                response_code = response.status_code
                if response_code == self.OK:

                    members_list = response["members"]
                    self._logger_bot.info("Loaded %s members for channel %s", len(response["members"]),
                                          self._get_channel(channel_id)["name"])
                    break
                else:
                    retry_count += 1
                    time.sleep(5)

            if retry_count == max_retries:
                raise SlackApiError(message=f'Timeout after {retry_count} retries',
                                    response={"error": f' Timeout error, {self.REQUEST_TIME_OUT}'})

            next_cursor = response["response_metadata"]["next_cursor"]

            while next_cursor:
                max_retries = 3
                retry_count = 0
                while retry_count < max_retries:
                    self._logger_bot.info("Starting request to Slack (channels|members). "
                                          "%d times repeated",
                                          retry_count)
                    response = self._web_client.conversations_members(channel=channel_id,
                                                                      limit=self._messages_per_page, cursor=next_cursor)
                    response_code = response.status_code
                    if response_code == self.OK:

                        members_list.extend(response["members"])
                        self._logger_bot.info("Loaded %s members for channel %s", len(response["members"]),
                                              self._get_channel(channel_id)["name"])
                        next_cursor = response["response_metadata"]["next_cursor"]
                        break
                    else:
                        retry_count += 1
                        time.sleep(5)

                    if retry_count == max_retries:
                        raise SlackApiError(message=f'Timeout after {retry_count} retries',
                                            response={"error": f' Timeout error, {self.REQUEST_TIME_OUT}'})

        except SlackApiError as e:
            self._logger_bot.error(f"SlackAPIError (conversations_members): "
                                   f"{e.response['error']}")
            return []
        return members_list

    def _set_channels_members(self, channel_id: str, members: list):
        channels = self._channels_list
        i = 0
        for key, channel in channels.items():
            if channel["id"] == channel_id:
                self._channels_list[key]["members"] = members
                break
            i += 1

    def set_channel_filter(self, channel_filter: str):
        if len(channel_filter) != 0 and channel_filter != "all":
            self._channel_filter = channel_filter.split(" ")

    def _is_selected_channel(self, channel_name) -> bool:
        is_channel_selected = False
        if len(self._channel_filter) == 0:
            is_channel_selected = True
        else:
            if channel_name in self._channel_filter:
                is_channel_selected = True

        return is_channel_selected

    def _download_files(self, files_attach: list) -> list:
        files_list = []
        for files in files_attach:
            if "url_private_download" not in files:
                break
            self._logger_bot.info(f'{files["name"]} is downloading')
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

    def set_channels_list(self, channels: dict):
        self._channels_list = channels

    def set_users_list(self, users: dict):
        self._users_list = users

    def _get_channel(self, channel_id: str) -> dict:
        for key, channel in self._channels_list.items():
            if channel["id"] == channel_id:
                return channel
        return {}
