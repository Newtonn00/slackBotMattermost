import logging
import re


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
                             "channel_type": self._channels_list.get(message["channel"], {}).get("type")},

                        "ts": message["ts"], "is_attached": message["is_attached"],
                        "is_thread": message["is_thread"]}

        if "attachments" in message:
            #            if message["attachments"][0]["author_id"] != user_id:
            if len(message_dict["text"]) > 0:
                message_dict["text"] = message_dict["text"] + '\n'

            attachments = message["attachments"]

            for attachment in attachments:
                if "author_id" in attachment:
                    message_dict["text"] = message_dict["text"] + \
                                           f'>>> <@{attachment["author_id"]}> ' \
                                           f'{attachment["text"]} \n'
                    message_dict["text"] = self.replace_mentions(message_dict["text"])
                else:
                    self._logger_bot.info("Message without author_id: %s", attachment)
                    message_dict["text"] = message_dict["text"] + \
                                           f'>>> {attachment["fallback"]} '
                    message_dict["text"] = self.replace_mentions(message_dict["text"])

        if message_dict["is_attached"]:
            message_dict["files"] = message["files"]

        #            if "attachments" not in message:
        #                if message["files"][0]["user_id"] != user_id:
        #                    if len(message_dict["text"]) > 0:
        #                        message_dict["text"] = message_dict["text"] + '\n'
        #                    attachments = message["files"]
        #                    for attachment in attachments:
        #                        message_dict["text"] = message_dict["text"] + \
        #                                               f'>>> <@{attachment["user_id"]}> \n'
        #                        message_dict["text"] = self.replace_mentions(message_dict["text"])

        if message_dict["is_thread"]:
            reply_list = []
            for reply_message in message["reply"]:
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
                              "is_thread": True}
                if "files" in reply_message:
                    reply_dict["files"] = reply_message["files"]
                reply_list.append(reply_dict)
            message_dict["reply"] = reply_list

        self.mm_upload_msg.upload_messages(message_dict)

    def _find_user_name_by_key(self, key) -> str:
        return self._users_list.get(key)

    def get_users_list(self) -> dict:
        return self._users_list

    def set_users_list(self, users_list):
        self._users_list = users_list

    def get_channels_list(self) -> dict:
        return self._channels_list

    def set_channels_list(self, channels_list):
        self._channels_list = channels_list

    def replace_function(self, match):
        matched_text = match.group(0)
        matched_text = matched_text[2:len(matched_text) - 1]
        user_data = self._users_list.get(matched_text)
        user_name = user_data["name"]
        if user_name == '' or user_name is None:
            user_name = match.group(0)
        else:
            user_name = "@" + user_data["name"]
        return user_name

    def replace_mentions(self, msg_text: str) -> str:
        pattern = r'<@[\w\d]+>'
        regex = re.compile(pattern)
        match = re.search(regex, msg_text)
        if match is None:
            return msg_text
        else:
            return re.sub(pattern, self.replace_function, msg_text)
