import logging
import re
from datetime import datetime


class MessagesService:
    def __init__(self, config_service, mattermost_upload_messages):
        self._logger_bot = logging.getLogger("")
        self._users_list = {}
        self._channels_list = {}
        self._config_service = config_service
        self.mm_upload_msg = mattermost_upload_messages

    def save_messages_to_dict(self, message: dict):
        user_id = message["user"]
        if not self._config_service.is_allowed_user(self._find_user_name_by_key(user_id)):
            return

        users_mentions = self._extract_users_from_message(message["text"])

        message["text"] = self.replace_mentions(message["text"])

        message_dict = {"text": message["text"],
                        "user": {
                            "user_id": message["user"],
                            "user_name": self._users_list.get(message["user"], {}).get("name"),
                            "user_email": self._users_list.get(message["user"], {}).get("email"),
                            "user_is_bot": self._users_list.get(message["user"], {}).get("is_bot"),
                            "user_first_name": self._users_list.get(message["user"], {}).get("first_name"),
                            "user_last_name": self._users_list.get(message["user"], {}).get("last_name"),
                            "user_is_deleted": self._users_list.get(message["user"], {}).get("is_deleted"),
                            "user_display_name": self._users_list.get(message["user"], {}).get("display_name")},


                        "channel":
                            {"channel_id": message["channel"],
                             "channel_name": self._channels_list.get(message["channel"], {}).get("name"),
                             "channel_type": self._channels_list.get(message["channel"], {}).get("type"),
                             "channel_members": self._channels_list.get(message["channel"], {}).get("members")},

                        "ts": message["ts"], "is_attached": message["is_attached"],
                        "is_thread": message["is_thread"]}

        if "attachments" in message:
            if len(message_dict["text"]) > 0:
                message_dict["text"] = message_dict["text"] + '\n'

            attachments = message["attachments"]
            users_mentions = []
            for attachment in attachments:
                users_mentions.extend(self._extract_users_from_message(message["text"]))
                if "author_id" in attachment:

                    message_dict["text"] = message_dict["text"] + \
                                           f'>>> <@{attachment["author_id"]}> ' \
                                           f'{attachment["text"]} \n'
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
                users_mentions.extend(self._extract_users_from_message(reply_message["text"]))
                reply_dict = {"text": self.replace_mentions(reply_message["text"]), "user_id": reply_message["user"],
                              "user":
                                  {
                                      "user_id": reply_message["user"],
                                      "user_name": self._users_list.get(reply_message["user"], {}).get("name"),
                                      "user_email": self._users_list.get(reply_message["user"], {}).get("email"),
                                      "user_is_bot": self._users_list.get(reply_message["user"], {}).get("is_bot"),
                                      "user_first_name": self._users_list.get(reply_message["user"], {}).get(
                                          "first_name"),
                                      "user_last_name": self._users_list.get(reply_message["user"], {}).get(
                                          "last_name"),
                                      "user_is_deleted": self._users_list.get(reply_message["user"], {}).get(
                                          "is_deleted"),
                                      "user_display_name": self._users_list.get(reply_message["user"], {}).get(
                                          "display_name")},
                              "channel":
                                  {"channel_id": message["channel"],
                                   "channel_name": self._channels_list.get(message["channel"], {}).get("name"),
                                   "channel_type": self._channels_list.get(message["channel"], {}).get("type")},
                              "ts": reply_message["ts"], "is_attached": False,
                              "is_thread": True
                              }
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
                "user_is_bot": self._users_list.get(mention, {}).get("is_bot"),
                "user_first_name": self._users_list.get(mention, {}).get("first_name"),
                "user_last_name": self._users_list.get(mention, {}).get("last_name"),
                "user_is_deleted": self._users_list.get(mention, {}).get("is_deleted"),
                "user_display_name": self._users_list.get(mention, {}).get("display_name")}

            users_mentions_list.append(users_mentions_dict)

        message_dict["users_in_mentions"] = users_mentions_list

        self.mm_upload_msg.upload_messages(message_dict)

    def _find_user_name_by_key(self, key) -> str:
        return self._users_list.get(key)["name"]

    def _get_user_item(self, user_id: str) -> dict:
        user_dict = self._users_list.get(user_id)
        return user_dict

    def get_users_list(self) -> dict:
        return self._users_list

    def set_users_list(self, users_list):
        self._users_list = users_list

    def get_channels_list(self) -> dict:
        return self._channels_list

    def set_channels_list(self, channels_list):
        self._channels_list = channels_list

    def replace_user_function(self, match):
        matched_text = match.group(0)
        matched_text = matched_text[2:len(matched_text) - 1]
        user_data = self._users_list.get(matched_text)
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
