import logging
import os
import time

import requests
from slack_sdk.errors import SlackApiError
from slack_sdk import WebClient

from src.util.common_counter import CommonCounter
from src.util.settings_parser import SettingsParser


class SlackLoadMessages:
    REQUEST_TIME_OUT = 408
    RATE_LIMITED_STATUS_CODE = 429
    CREATED = 201
    OK = 200
    FILE_SIZE_LIMIT = 100000000

    def __init__(self, web_client, config_service, messages_service, pin_service, bookmark_service, thread_service,
                 slack_messages_handler):
        settings = SettingsParser()

        self._logger_bot = logging.getLogger("")
        self._channels_list = {}
        self._users_list = {}
        self._web_client = WebClient(settings.slack_bot_token)
        self._slack_token = settings.slack_bot_token
        self._config_service = config_service
        self._messages_service = messages_service
        self._pin_service = pin_service
        self._bookmark_service = bookmark_service
        self._thread_service = thread_service
        self._slack_messages_handler = slack_messages_handler
        self._initial_user_id = ""
        self._messages_per_page = 10
        self._channel_filter = []
        self._user_mails_list = []

    def load_channel_messages(self, channel_type=None):

        if channel_type is None:
            channel_type = ["direct", "public", "private"]

        self.load_users()
        if "direct" in channel_type:
            self.load_direct_channels()
        else:
            self.load_channels()
            self._set_channel_type_filter(channel_type)
        self._logger_bot.info(self._channels_list)

        self._messages_service.set_users_list(self._users_list)
        self._messages_service.set_channels_list(self._channels_list)
        self._pin_service.set_slack_channels_list(self._channels_list)
        self._bookmark_service.set_slack_channels_list(self._channels_list)
        self._thread_service.set_slack_channels_list(self._channels_list)

        self._logger_bot.info(f'Loading messages from {channel_type} channels')
        for channel_id, channel_item in self._channels_list.items():

            if (self._is_selected_channel(channel_item["name"]) and self._config_service.is_allowed_channel(
                    channel_item["name"]) and channel_item["type"] in channel_type) or (channel_type == "direct"):
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
                        CommonCounter.increment_error()
                        break

                self._logger_bot.info("Selected %d messages from Slack channel %s", len(messages),
                                      channel_item["name"])

                messages_count = len(messages)
                replies_count = 0
                for message in messages:
                    message["is_thread"] = False
                    if "reply_users" in message:
                        message["reply"] = self.load_threads(channel_id=channel_item["id"], oldest_date=oldest_date,
                                                             ts_of_parent_message=message["ts"])
                        replies_count += len(message["reply"])
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

                text_msg = (f'channel {channel_item["name"]} transfer statistics:\n'
                            f'{CommonCounter.get_str_custom_statistic()}')
                CommonCounter.init_custom_counter()
                self._logger_bot.info(text_msg)
                self._slack_messages_handler.send_message(self._initial_user_id, text_msg)

    def load_threads(self, channel_id, ts_of_parent_message, oldest_date) -> list:
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
            CommonCounter.increment_error()
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
            CommonCounter.increment_error()
            return
        users = {}
        for user in user_list:
            user_id = user.get("id")
            user_name = user.get("name")
            user_title = user.get("title")
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
            users[user["id"]] = {"id": user_id, "name": user_name, "title": user_title, "email": user_email,
                                 "is_bot": user_is_bot,
                                 "is_deleted": user_is_deleted, "first_name": user_first_name,
                                 "last_name": user_last_name, "display_name": user_display_name}

        self._logger_bot.info("Slack users loaded (%d)", len(users))
        self.set_users_list(users)

    def load_channels(self):

        try:

            max_retries = 3
            retry_count = 0
            channels_list = []
            self._logger_bot.info("Starting request to Slack (channels)")
            while retry_count < max_retries:
                response = self._web_client.conversations_list(types="public_channel,private_channel",
                                                               limit=self._messages_per_page)
                response_code = response.status_code
                if response_code == self.OK:

                    channels_list = response["channels"]
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
                    response = self._web_client.conversations_list(types="public_channel,private_channel",
                                                                   limit=self._messages_per_page, cursor=next_cursor)
                    response_code = response.status_code
                    if response_code == self.OK:

                        channels_list.extend(response["channels"])
                        next_cursor = response["response_metadata"]["next_cursor"]

                        break
                    else:
                        retry_count += 1
                        time.sleep(5)

                    if retry_count == max_retries:
                        raise SlackApiError(message=f'Timeout after {retry_count} retries',
                                            response={"error": f' Timeout error, {self.REQUEST_TIME_OUT}'})
            self._logger_bot.info("Slack channels loaded - %d", len(channels_list))
        except SlackApiError as e:
            self._logger_bot.error(f"SlackAPIError (conversations_list types=public_channel,private_channel): "
                                   f"{e.response['error']}")
            CommonCounter.increment_error()
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

        self.set_channels_list(channels)

        for channel in channels:
            if self._is_selected_channel(self._get_channel(channel)["name"]) \
                    and self._config_service.is_allowed_channel(self._get_channel(channel)["name"]):
                members = self._load_channel_members(channel)
                self._set_channels_members(channel, members)

    def load_direct_channels(self):

        try:
            max_retries = 3
            retry_count = 0
            channels_users_list = []
            self._logger_bot.info("Starting request to Slack (dm-channels)")
            while retry_count < max_retries:

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

            self._logger_bot.info("Slack direct messages channels loaded - %d", len(channels_users_list))
        except SlackApiError as e:
            self._logger_bot.error(f"SlackAPIError (conversations_list types=im,mpim): {e.response['error']}")
            CommonCounter.increment_error()
            return
        self._logger_bot.info(f'Channels: {channels_users_list}')
        channels = {}
        for channel in channels_users_list:
            if "name" in channel:
                channel_name = channel["name"]
            else:
                channel_name = channel["user"]
            channel_id = channel["id"]
            channel_type = "direct"
            channels[channel["id"]] = {"id": channel_id, "name": channel_name, "type": channel_type}

        self.set_channels_list(channels)
        channels_list = channels.copy()

        for channel in channels_list:
            if self._is_selected_channel(self._get_channel(channel)["name"]) \
                    and self._config_service.is_allowed_channel(self._get_channel(channel)["name"]):
                members = self._load_channel_members(channel)

                exclude_channel = True
                for user in members:

                    self._logger_bot.info(self._users_list.get(user))
                    if not(user == self._initial_user_id) and self._user_mails_list and not self._users_list.get(user)["email"] in self._user_mails_list:
                        continue

                    if user not in self._users_list or self._users_list.get(user)["is_bot"] or user == self._initial_user_id:
                        continue
                    else:
                        exclude_channel = False


                if exclude_channel:
                    del self._channels_list[channel]
                else:

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
            CommonCounter.increment_error()
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
                continue

            if files["size"] > self.FILE_SIZE_LIMIT:
                self._logger_bot.info(f'File {files["name"]} size {files["size"]} is more than {self.FILE_SIZE_LIMIT}')
                continue

            self._logger_bot.info(f'{files["name"]} is downloading')
            response_file = requests.get(files["url_private_download"],
                                         headers={
                                             'Authorization': 'Bearer %s' % self._slack_token})
            if response_file.status_code == 200:
                settings = SettingsParser()
                local_file_path = settings.work_dir + "/" + files["name"]

                local_file_path = self._shorten_filename(local_file_path)

                try:
                    with open(local_file_path, "wb") as local_file:
                        for chunk in response_file.iter_content(chunk_size=8192):
                            local_file.write(chunk)
                    self._logger_bot.info(
                        f'File {files["name"]} is downloaded to {local_file_path}')
                except Exception:
                    self._logger_bot.error("Error in downloading as local file")
                    CommonCounter.increment_error()

                files_dict = {
                    "file_name": files["name"],
                    "link": files["url_private_download"],
                    "user_id": files["user"],
                    "file_path": local_file_path}
                files_list.append(files_dict)
                self._logger_bot.info(f'{files["name"]} is downloaded from Slack')
            else:
                self._logger_bot.error(f'SlackAPIError (files): {response_file.json()}')
                CommonCounter.increment_error()
        return files_list

    def set_channels_list(self, channels: dict):
        self._channels_list = channels

    def set_users_list(self, users: dict):
        self._users_list = users

    def _get_channel(self, channel_id: str) -> dict:
        for key, channel in self._channels_list.items():
            if key == channel_id:
                return channel
        return {}

    def set_initial_user(self, user_id: str):
        self._initial_user_id = user_id

    def get_channels_list(self):
        return self._channels_list

    def get_users_list(self):
        return self._users_list

    def _shorten_filename(self, file_path, max_length=None) -> str:
        if max_length is None:
            max_length = 60
        # Получаем имя файла из полного пути
        file_name = os.path.basename(file_path)

        # Разделяем имя файла и расширение
        base_name, extension = os.path.splitext(file_name)

        # Определяем допустимую длину для базового имени файла (с учетом расширения)
        max_base_length = max_length - len(extension) if max_length > len(extension) else len(extension)

        # Сокращаем имя файла
        shortened_name = base_name[:max_base_length] + "..." + extension if len(
            base_name) > max_base_length else file_name

        return shortened_name

    def set_user_token(self, token: str):
        self._web_client = WebClient(token)
        self._slack_token = token

    def _set_channel_type_filter(self, channel_type: list):
        channels_list = self._channels_list.copy()
        for channel_id, channel_item in channels_list.items():
            if channel_item["type"] not in channel_type:
                del self._channels_list[channel_id]

    def set_direct_channels_filter(self, user_mails: str):
        if user_mails != "all":
            self._user_mails_list = user_mails.split(" ")
