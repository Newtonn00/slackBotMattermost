import logging
import os
import re
from datetime import datetime


class MessagesService:
    def __init__(self, config_service):
        self._logger_bot = logging.getLogger("")
        self._users_list = {}
        self._channels_list = {}
        self._config_service = config_service
        self._mm_upload_msg = None

    def save_reply_to_mattermost(self, message: dict):
        username = ""
        if "user" not in message:
            self._logger_bot.info(message)
            user_id = message["bot_id"]
            if "username" in message:
                username = message["username"]
        else:
            user_id = message["user"]
        if not self._config_service.is_allowed_user(self._find_user_name_by_key(user_id)):
            return
        user_dict = self._get_user_item(user_id)
        if username:
            user_dict["name"] = username
            user_dict["display_name"] = username
        users_mentions = self._extract_users_from_message(message["text"])

        message["text"] = self.replace_mentions(message["text"])

        message_dict = {"text": message["text"],
                        "user": {
                            "user_id": user_id,
                            "user_name": user_dict.get("name"),
                            "user_title": user_dict.get("title"),
                            "user_email": user_dict.get("email"),
                            "user_is_bot": user_dict.get("is_bot"),
                            "user_first_name": user_dict.get("first_name"),
                            "user_last_name": user_dict.get("last_name"),
                            "user_is_deleted": user_dict.get("is_deleted"),
                            "user_display_name": user_dict.get("display_name")},


                        "channel":
                            {"channel_id": message["channel"],
                             "channel_name": self._channels_list.get(message["channel"], {}).get("name"),
                             "channel_type": self._channels_list.get(message["channel"], {}).get("type"),
                             "channel_members": self._channels_list.get(message["channel"], {}).get("members")},

                        "mm_post_id": message["post_id"],
                        "ts": message["ts"], "is_attached": message["is_attached"],
                        "is_thread": False}

        if message_dict["is_attached"]:
            message_dict["files"] = message["files"]

        message_dict["text"] = self._add_timestamp_to_text(message_dict["text"], message_dict["ts"])
        users_mentions_list = []
        for mention in users_mentions:
            users_mentions_dict = {
                "user_id": mention,
                "user_name": self._users_list.get(mention, {}).get("name"),
                "user_email": self._users_list.get(mention, {}).get("email"),
                "user_title": self._users_list.get(message["user"], {}).get("title"),
                "user_is_bot": self._users_list.get(mention, {}).get("is_bot"),
                "user_first_name": self._users_list.get(mention, {}).get("first_name"),
                "user_last_name": self._users_list.get(mention, {}).get("last_name"),
                "user_is_deleted": self._users_list.get(mention, {}).get("is_deleted"),
                "user_display_name": self._users_list.get(mention, {}).get("display_name")}

            users_mentions_list.append(users_mentions_dict)

        message_dict["users_in_mentions"] = users_mentions_list

        self._mm_upload_msg.upload_messages(message_dict)
        if message_dict["is_attached"]:
            self._delete_file(message_dict["files"])

    def save_messages_to_dict(self, message: dict):
        username = ""
        if "user" not in message:
            self._logger_bot.info(message)
            user_id = message["bot_id"]
            if "username" in message:
                username = message["username"]
        else:
            user_id = message["user"]
        if not self._config_service.is_allowed_user(self._find_user_name_by_key(user_id)):
            return
        user_dict = self._get_user_item(user_id)
        if username:
            user_dict["name"] = username
            user_dict["display_name"] = username
        users_mentions = self._extract_users_from_message(message["text"])

        message["text"] = self.replace_mentions(message["text"])

        message_dict = {"text": message["text"],
                        "user": {
                            "user_id": user_id,
                            "user_name": user_dict.get("name"),
                            "user_email": user_dict.get("email"),
                            "user_title": user_dict.get("title"),
                            "user_is_bot": user_dict.get("is_bot"),
                            "user_first_name": user_dict.get("first_name"),
                            "user_last_name": user_dict.get("last_name"),
                            "user_is_deleted": user_dict.get("is_deleted"),
                            "user_display_name": user_dict.get("display_name")},


                        "channel":
                            {"channel_id": message["channel"],
                             "channel_name": self._channels_list.get(message["channel"], {}).get("name"),
                             "channel_type": self._channels_list.get(message["channel"], {}).get("type"),
                             "channel_members": self._channels_list.get(message["channel"], {}).get("members")},
                        "mm_post_id": "",
                        "ts": message["ts"], "is_attached": message["is_attached"],
                        "is_thread": message["is_thread"]}

        if "attachments" in message:
            if len(message_dict["text"]) > 0:
                message_dict["text"] = message_dict["text"] + '\n'

            attachments = message["attachments"]
            users_mentions = []
            for attachment in attachments:
                users_mentions.extend(self._extract_users_from_message(message["text"]))
                attachment_text = ""
                if "text" in attachment:
                    attachment_text = attachment["text"]
                if "author_id" in attachment:

                    message_dict["text"] = message_dict["text"] + \
                                           f'>>> <@{attachment["author_id"]}> ' \
                                           f'{attachment_text} \n'
                    message_dict["text"] = self.replace_mentions(message_dict["text"])
                else:
                    self._logger_bot.info("Message without author_id: %s", attachment)
                    message_dict["text"] = message_dict["text"] + f'>>> {attachment["fallback"]} '
                    message_dict["text"] = self.replace_mentions(message_dict["text"])

        if message_dict["is_attached"]:
            message_dict["files"] = message["files"]

        if message_dict["is_thread"]:
            reply_list = []
            for reply_message in message["reply"]:
                reply_username = ""
                if "user" not in reply_message:
                    self._logger_bot.info(reply_message)
                    reply_user_id = reply_message["bot_id"]
                    if "username" in reply_message:
                        reply_username = reply_message["username"]
                else:
                    reply_user_id = reply_message["user"]
                reply_user_dict = self._get_user_item(reply_user_id)
                if reply_username:
                    reply_user_dict["name"] = reply_username
                    reply_user_dict["display_name"] = reply_username

                users_mentions.extend(self._extract_users_from_message(reply_message["text"]))
                reply_dict = {"text": self.replace_mentions(reply_message["text"]),
                              "user_id": reply_user_id,
                              "user":
                                  {
                                      "user_id": reply_user_id,
                                      "user_name": reply_user_dict.get("name"),
                                      "user_email": reply_user_dict.get("email"),
                                      "user_title": reply_user_dict.get("title"),
                                      "user_is_bot": reply_user_dict.get("is_bot"),
                                      "user_first_name": reply_user_dict.get("first_name"),
                                      "user_last_name": reply_user_dict.get("last_name"),
                                      "user_is_deleted": reply_user_dict.get("is_deleted"),
                                      "user_display_name": reply_user_dict.get("display_name")},
                              "channel":
                                  {"channel_id": message["channel"],
                                   "channel_name": self._channels_list.get(message["channel"], {}).get("name"),
                                   "channel_type": self._channels_list.get(message["channel"], {}).get("type")},
                              "mm_post_id": "",
                              "ts": reply_message["ts"], "is_attached": False,
                              "is_thread": True
                              }

                reply_dict["text"] = self._add_timestamp_to_text(reply_dict["text"], reply_dict["ts"])
                if "files" in reply_message:
                    reply_dict["files"] = reply_message["files"]
                reply_list.append(reply_dict)
            message_dict["reply"] = reply_list
        message_dict["text"] = self._add_timestamp_to_text(message_dict["text"], message_dict["ts"])
        users_mentions_list = []
        for mention in users_mentions:
            users_mentions_dict = {
                "user_id": mention,
                "user_name": self._users_list.get(mention, {}).get("name"),
                "user_email": self._users_list.get(mention, {}).get("email"),
                "user_title": self._users_list.get(mention, {}).get("title"),
                "user_is_bot": self._users_list.get(mention, {}).get("is_bot"),
                "user_first_name": self._users_list.get(mention, {}).get("first_name"),
                "user_last_name": self._users_list.get(mention, {}).get("last_name"),
                "user_is_deleted": self._users_list.get(mention, {}).get("is_deleted"),
                "user_display_name": self._users_list.get(mention, {}).get("display_name")}

            users_mentions_list.append(users_mentions_dict)

        message_dict["users_in_mentions"] = users_mentions_list

        self._mm_upload_msg.upload_messages(message_dict)

    def _find_user_name_by_key(self, key) -> str:
        user_name = key

        if self._users_list.get(key):
            user_name = self._users_list[key]["name"]

        return user_name

    def _get_user_item(self, user_id: str) -> dict:
        user_dict = self._users_list.get(user_id)
        if not user_dict:
            user_dict = {"id": user_id, "name": user_id, "title": "", "email": "",
                         "is_bot": True,
                         "is_deleted": False, "first_name": user_id,
                         "last_name": user_id, "display_name": user_id}
        return user_dict

    def get_users_list(self) -> dict:
        return self._users_list

    def set_users_list(self, users_list: dict):
        self._users_list = users_list

    def get_channels_list(self) -> dict:
        return self._channels_list

    def set_channels_list(self, channels_list):
        self._channels_list = channels_list

    def replace_user_function(self, match):
        user_name = ""
        matched_text = match.group(0)
        matched_text = matched_text[2:len(matched_text) - 1]
        self._logger_bot.info(f'Matched text - {matched_text}')
        user_data = self._users_list.get(matched_text)
        if user_data:
            user_name = user_data["name"]
        if user_name == '' or user_name is None:
            user_name = match.group(0)
        else:
            user_name = "@" + user_data["name"]
        return user_name

    def replace_channel_function(self, match) -> str:
        matched_text = match.group(0)
        matched_text = matched_text[2:matched_text.find('|')]
        channel_name = ''
        channel_data = self._channels_list.get(matched_text)
        if channel_data:
            channel_name = channel_data["name"]
        if channel_name == '' or channel_name is None:
            channel_name = match.group(0)
        else:
            channel_name = "~" + channel_name
        return channel_name

    def replace_link_function(self, match) -> str:
        replaced_text: str = ""
        matched_text = match.group(0)
        link = matched_text[2:matched_text.find('|')]
        link_description =  matched_text[matched_text.find('|')+1:matched_text.find('>')]
        if not link or not link_description:
            replaced_text = match.group(0)
        replaced_text = f'[{link_description}]({link})'
        return replaced_text

    def replace_mentions(self, msg_text: str) -> str:

        replaced_message = msg_text
        pattern = r'<@[\w\d]+>'
        regex = re.compile(pattern)
        match = re.search(regex, replaced_message)
        if match:
            replaced_message = re.sub(pattern, self.replace_user_function, replaced_message)

        pattern = r'<#([\w\d]+)\|(.*?)>'
        regex = re.compile(pattern)
        match = re.search(regex, replaced_message)
        if match:
            replaced_message = re.sub(pattern, self.replace_channel_function, replaced_message)

        pattern = r'<!here>'
        regex = re.compile(pattern)
        match = re.search(regex, replaced_message)
        if match:
            replaced_message = re.sub(pattern, "@here", replaced_message)

        pattern = r'<!channel>'
        regex = re.compile(pattern)
        match = re.search(regex, replaced_message)
        if match:
            replaced_message = re.sub(pattern, "@channel", replaced_message)

        pattern = r'<([\w\S\d]+)(\|)([\w\S\d]+)>'
        regex = re.compile(pattern)
        match = re.search(regex, replaced_message)
        if match:
            replaced_message = re.sub(pattern, self.replace_link_function, replaced_message)

        return replaced_message

    def _add_timestamp_to_text(self, msg_text: str, timestamp: float) -> str:
        msg_with_ts = msg_text
        if msg_with_ts != "" and msg_with_ts is not None:
            msg_with_ts = msg_with_ts + f'\n\n slack_ts: ' \
                                        f'{datetime.fromtimestamp(float(timestamp)).strftime("%Y-%m-%d %H:%M:%S")}'
        else:
            msg_with_ts = " slack_ts:" + datetime.fromtimestamp(float(timestamp)).strftime("%Y-%m-%d %H:%M:%S")
        return msg_with_ts

    def _extract_users_from_message(self, msg_txt) -> list:
        users_mentions = []
        pattern = r'<@[\w\d]+>'
        regex = re.compile(pattern)
        matches = regex.findall(msg_txt)

        for match in matches:
            users_mentions.append(match[2:len(match) - 1])

        return users_mentions

    def _delete_file(self, files: list):
        for file in files:
            if os.path.exists(file["file_path"]):
                os.remove(file["file_path"])
                self._logger_bot.info("Deleted file %s from %s", file["file_name"],
                                      file["file_path"])

    def set_mm_upload_messages_instance(self, mm_upload_msg):
        self._mm_upload_msg = mm_upload_msg

    def get_mm_upload_messages_instance(self):
        return self._mm_upload_msg

