import logging

from requests import HTTPError

from src.entity.user_entity import UserEntity
from src.util.common_counter import CommonCounter


class MattermostUploadMessages:

    def __init__(self, mattermost_web_client, mattermost_messages, user_service):
        self._channels_list = []
        self._users_list = []
        self._channel_filter = []
        self._team_id = None
        self._logger_bot = logging.getLogger("")
        self._mm_web_client = mattermost_web_client
        self._messages_per_page = 100
        self._mattermost_messages = mattermost_messages
        self._channels_slack_ts = {}
        self._main_slack_user_id = None
        self._user_service = user_service
        self._session_id = None

    def load_users(self):
        response = ''
        params = {
            "page": 0,
            "per_page": self._messages_per_page
        }
        self._users_list = []
        try:
            while True:
                response = self._mm_web_client.mattermost_session.get(
                    f'{self._mm_web_client.mattermost_url}/users',
                    params=params)
                response.raise_for_status()
                users = response.json()

                if not users:
                    break

                self._users_list.extend(users)
                params["page"] += 1

            self._logger_bot.info(f'Mattermost users loaded ({len(self._users_list)})|Session:{self._session_id}')

        except HTTPError as err:
            self._logger_bot.error(
                f'Mattermost API Error (users). Status code: {response.status_code} '
                f'Response:{response.text} Error:{err} Session:{self._session_id}')
            CommonCounter.increment_error(self._session_id)

    def load_users_channels(self):
        user_id = self._user_service.get_user_id_mattermost_by_user_id_slack(self._main_slack_user_id)
        response = ''
        params = {
            "page": 1,
            "per_page": self._messages_per_page,
            "user_id": user_id,
            "type": 'D'
        }
        channels_list = []
        previous_channels = []
        try:
            while True:
                response = self._mm_web_client.mattermost_session.get(
                    f'{self._mm_web_client.mattermost_url}/users/{user_id}/channels',
                    params=params)
                response.raise_for_status()
                channels = response.json()

                if not channels or channels == previous_channels:
                    break
                previous_channels = channels
                channels_list.extend(channels)
                params["page"] += 1
            self._logger_bot.info(f'Mattermost users channels loaded ({len(channels_list)})|Session:{self._session_id}')
            filtered_channels = []
            for channel in channels_list:
                if channel["type"] == 'D':
                    if self._is_selected_channel(channel["name"]):
                        filtered_channels.append(channel)
                    elif self._is_selected_channel(channel["display_name"]):
                        filtered_channels.append(channel)

            self.set_channels_list(filtered_channels)
            for channel in filtered_channels:
                self._set_channels_members(channel["id"])
        except HTTPError as err:
            self._logger_bot.error(
                f'Mattermost API Error (users channels). Status code: {response.status_code} '
                f'Response:{response.text} Error:{err} Session:{self._session_id}')
            CommonCounter.increment_error(self._session_id)

    def load_channels(self):

        response = ''
        params = {
            "page": 0,
            "per_page": self._messages_per_page
        }
        self._channels_list = []
        channels_list = []
        try:
            while True:
                response = self._mm_web_client.mattermost_session.get(
                    f'{self._mm_web_client.mattermost_url}/channels',
                    params=params)
                response.raise_for_status()
                channels = response.json()

                if not channels:
                    break
                channels_list.extend(channels)
                params["page"] += 1
            self._logger_bot.info(f'Mattermost channels loaded ({len(channels_list)})|Session:{self._session_id}')

            filtered_channels = []
            for channel in channels_list:
                if self._is_selected_channel(channel["name"]):
                    filtered_channels.append(channel)
                elif self._is_selected_channel(channel["display_name"]):
                    filtered_channels.append(channel)

            self.set_channels_list(filtered_channels)
            for channel in filtered_channels:
                self._set_channels_members(channel["id"])
        except HTTPError as err:
            self._logger_bot.error(
                f'Mattermost API Error (channels). Status code: {response.status_code} '
                f'Response:{response.text} Error:{err} Session:{self._session_id}')
            CommonCounter.increment_error(self._session_id)

    def upload_messages(self, message_data):
        self._logger_bot.info(self._mm_web_client.mattermost_session.headers)
        self._user_service.load_mattermost(self._session_id)
        self._user_service.load_team(self._session_id)
        self._team_id = self._user_service.get_team_id()
        if not self._users_list:
            self._users_list = self._user_service.get_users_mattermost_as_list()

        if message_data["channel"]["channel_type"] == "direct":
            channel_id = self._create_channel(message_data["channel"])
        else:
            channel_id = self._get_channel_by_name(message_data["channel"])
        if channel_id not in self._channels_slack_ts:
            self._channels_slack_ts[channel_id] = (
                self._get_set_slack_ts(self._mattermost_messages.load_messages(channel_id, self._session_id)))
        if message_data["ts"] in self._channels_slack_ts[channel_id]:
            self._logger_bot.info(f'Message {message_data["ts"]} has already loaded in Mattermost '
                                  f'| Session: {self._session_id}')
            return
        user_data = message_data["user"]

        user_id = self._user_service.get_user_id_mattermost_by_email(user_data["user_email"])
        self._logger_bot.info(f'user_data: {user_data} | Session: {self._session_id}')
        if not user_id:
            slack_user_entity: UserEntity
            slack_user_entity = self._user_service.get_user_entity_slack(user_data["user_id"])
            if slack_user_entity is not None:
                self._logger_bot.info(f'slack_user_entity: {slack_user_entity.as_dict()} | Session: {self._session_id}')
                if slack_user_entity.is_bot is not True and slack_user_entity.email is not None:

                    user_dict_mm = self._user_service.create_user_mattermost(slack_user_entity,
                                                                             session_id=self._session_id)
                    user_list_mm = [user_dict_mm]
                    if user_list_mm:
                        self._user_service.load_mattermost(users_list=user_list_mm, session_id=self._session_id)
                        self._users_list = self._user_service.get_users_mattermost_as_list()
                        user_id = self._user_service.get_user_id_mattermost_by_email(user_data["user_email"])

        if not self._is_user_in_channel(user_id=user_id, channel_id=channel_id) and \
                not (message_data["channel"]["channel_type"] == "direct") and \
                message_data["user"]["user_id"] in message_data["channel"]["channel_members"]:
            self._add_user_to_channel(user_id=user_id, channel_id=channel_id)

        if channel_id is None:
            self._logger_bot.error(f'Channel {message_data["channel"]["channel_name"]} did`nt find in Mattermost|'
                                   f'Session:{self._session_id}')
            CommonCounter.increment_error(self._session_id)
            return

        for mention in message_data["users_in_mentions"]:

            user_mention_id = self._user_service.get_user_id_mattermost_by_email(mention["user_email"])
            if not user_mention_id:
                slack_user_entity: UserEntity
                slack_user_entity = self._user_service.get_user_entity_slack(mention["user_id"])
                self._logger_bot.info(f'slack_user_entity: {slack_user_entity}')
                if slack_user_entity and not slack_user_entity.is_bot and slack_user_entity.email is not None:
                    user_dict_mm = self._user_service.create_user_mattermost(user_data=slack_user_entity,
                                                                             session_id=self._session_id)
                    user_list_mm = [user_dict_mm]
                    if user_list_mm:
                        self._user_service.load_mattermost(user_list_mm, self._session_id)
                        self._users_list = self._user_service.get_users_mattermost_as_list()
                        user_mention_id = self._user_service.get_user_id_mattermost_by_email(mention["user_email"])

            if not self._is_user_in_channel(user_id=user_mention_id, channel_id=channel_id) and \
                    mention in message_data["channel"]["channel_members"]:
                self._add_user_to_channel(user_id=user_mention_id, channel_id=channel_id)

        files_list = []
        self._logger_bot.info("Message is loading to Mattermost")
        if message_data["is_attached"]:
            files_list = self._upload_files(message_data["files"], channel_id=channel_id)

        data = {
            "channel_id": channel_id,
            "message": message_data["text"],
            "root_id": message_data["mm_post_id"],
            "props": {"from_webhook": "true",
                      "override_username": message_data["user"]["user_display_name"],
                      "username": message_data["user"]["user_display_name"],
                      "slack_user_id": message_data["user"]["user_id"],
                      "slack_user_name": message_data["user"]["user_name"],
                      "slack_channel_id": message_data["channel"]["channel_id"],
                      "slack_channel_name": message_data["channel"]["channel_name"],
                      "slack_ts": message_data["ts"]
                      },
            "file_ids": files_list
        }

        response = self._mm_web_client.mattermost_session.post(f'{self._mm_web_client.mattermost_url}/posts', json=data)
        if response.status_code == 201:
            post_info = response.json()
            self._logger_bot.info(f'Message loaded to Mattermost|Session:{self._session_id}')
            CommonCounter.increment_message(self._session_id)

            if message_data["is_thread"]:
                orig_post_id = post_info["id"]

                for reply_message in message_data["reply"]:
                    self._logger_bot.info("Thread`s message is loading to Mattermost")
                    if reply_message["ts"] in self._channels_slack_ts[channel_id]:
                        self._logger_bot.info(f'Message {reply_message["ts"]} has already loaded in Mattermost')
                        continue
                    files_list = []
                    if "files" in reply_message:
                        files_list = self._upload_files(reply_message["files"], channel_id=channel_id)

                    data = {
                        "channel_id": channel_id,
                        "message": reply_message["text"],
                        "root_id": orig_post_id,
                        "props": {"from_webhook": "true",
                                  "override_username": reply_message["user"]["user_display_name"],
                                  "username": reply_message["user"]["user_display_name"],
                                  "slack_user_id": reply_message["user"]["user_id"],
                                  "slack_user_name": reply_message["user"]["user_name"],
                                  "slack_channel_id": reply_message["channel"]["channel_id"],
                                  "slack_channel_name": reply_message["channel"]["channel_name"],
                                  "slack_ts": reply_message["ts"]
                                  },
                        "file_ids": files_list
                    }
                    response = self._mm_web_client.mattermost_session.post(
                        f'{self._mm_web_client.mattermost_url}/posts', json=data)
                    if response.status_code == 201:
                        self._logger_bot.info(f'Threads`s message loaded to Mattermost|Session:{self._session_id}')
                        CommonCounter.increment_message(self._session_id)
                    else:
                        self._logger_bot.error(
                            f'Mattermost API Error (posts). Status code: {response.status_code} '
                            f'Response:{response.text} Session:{self._session_id}')
                        CommonCounter.increment_error(self._session_id)

        else:
            self._logger_bot.error(
                f'Mattermost API Error (posts). Status code: {response.status_code} '
                f'Response:{response.text} Session:{self._session_id}')
            CommonCounter.increment_error(self._session_id)

    def _upload_files(self, files_from_message: list, channel_id: str) -> list:
        files_list = []
        for file in files_from_message:
            if isinstance(file, list):
                files_list.extend(self._upload_files(file, channel_id))
            else:
                self._logger_bot.info(f'File {file["file_path"]} is loading to Mattermost (first phase)|'
                                      f'Session:{self._session_id}')
                files = {"files": open(file["file_path"], "rb")}
                params = {"channel_id": channel_id}
                self._logger_bot.info(f'File is loading to Mattermost (second phase) - {files} and {params}|'
                                      f'Session:{self._session_id}')
                response_file = self._mm_web_client.mattermost_session.post(
                    f'{self._mm_web_client.mattermost_url}/files', params=params,
                    files=files)

                self._logger_bot.info(f'File is loading to Mattermost (third phase) - {files}|'
                                      f'Session:{self._session_id}')

                if response_file.status_code == 201:
                    response_json = response_file.json()
                    self._logger_bot.info(f'File {file["file_path"]} loaded to Mattermost|Session:{self._session_id}')
                    files_list.append(response_json['file_infos'][0]['id'])
                    CommonCounter.increment_file(self._session_id)
                else:
                    self._logger_bot.error(
                        f'Mattermost API Error (files). Status code: {response_file.status_code} '
                        f'Response:{response_file.text} Session:{self._session_id}')
                    CommonCounter.increment_error(self._session_id)

        return files_list

    def _get_user_by_email(self, user_data: dict) -> str:
        user_id = None
        for user in self._users_list:
            mm_mail = user["email"]
            slack_mail = user_data["user_email"]
            if mm_mail and slack_mail and mm_mail.lower() == slack_mail.lower():
                user_id = user["id"]
                break

        if user_id is None and not user_data["user_is_bot"] and user_data["user_email"]:
            self._logger_bot.info("user_data: %s", user_data)
            #            self._logger_bot.info("users_list: %s", self._users_list)
            user_id = self._create_user(user_data)
        return user_id

    def _get_user(self, user_id: str) -> dict:

        for user in self._users_list:
            if user["id"] == user_id:
                return user
        return {}

    def _get_channel(self, channel_id: str) -> dict:
        for channel in self._channels_list:
            if channel["id"] == channel_id:
                return channel
        return {}

    def _get_channel_by_name(self, channel_data: dict) -> str:
        channel_id = None
        #        self._logger_bot.info(f'channel MM - {channel_data}')
        for channel in self._channels_list:
            if ((channel["name"] == channel_data["channel_name"])
                    or (channel["display_name"] == channel_data["channel_name"])):
                channel_id = channel["id"]
                channel["channel_type"] = channel_data["channel_type"]
                channel["slack_channel_id"] = channel_data["channel_id"]
                break

        if channel_id is None:
            channel_id = self._create_channel(channel_data)

        return channel_id

    def _create_channel(self, channel_data: dict) -> str:
        self._logger_bot.info(self._mm_web_client.mattermost_session.headers)
        self._logger_bot.info(channel_data)
        channel_id = None

        if (channel_data["channel_type"] == "direct") or (channel_data["channel_type"] == "group"):
            dm_users_list = []
            for slack_user_id in channel_data["channel_members"]:
                dm_users_list.append(self._user_service.get_user_id_mattermost_by_user_id_slack(slack_user_id))

            response = self._mm_web_client.mattermost_session.post(
                f'{self._mm_web_client.mattermost_url}/channels/{channel_data["channel_type"]}', json=dm_users_list)
        else:
            self._logger_bot.info("Channel %s is creating", channel_data["channel_name"])

            data = {
                "team_id": self._team_id,
                "name": channel_data["channel_name"],
                "display_name": channel_data["channel_name"],
                "scheme_id": '',
                "type": "O",
            }
            if channel_data["channel_type"] == "private":
                data["type"] = "P"

            self._logger_bot.info(data)
            response = self._mm_web_client.mattermost_session.post(
                f'{self._mm_web_client.mattermost_url}/channels', json=data)

        if response.status_code == 201:
            response_data = response.json()
            channel_id = response_data["id"]
            if not self._get_channel(channel_id):
                response_data["channel_type"] = channel_data["channel_type"]
                response_data["slack_channel_id"] = channel_data["channel_id"]
                self._channels_list.append(response_data)
                self._logger_bot.info(f'Channel {channel_data["channel_name"]} created|Session:{self._session_id}')
                self._set_channels_members(channel_id)
                CommonCounter.increment_channel(self._session_id)
        else:
            self._logger_bot.error(
                f'Mattermost API Error (channels). Status code: {response.status_code} '
                f'Response:{response.text} Session:{self._session_id}')
            CommonCounter.increment_error(self._session_id)

        return channel_id

    def _create_user(self, user_data: dict) -> str:
        self._logger_bot.info("User %s is creating", user_data["user_name"])
        user_id = None

        data = {
            "team_id": self._team_id,
            "username": user_data["user_name"],
            "display_name": user_data["user_display_name"],
            "nickname": user_data["user_display_name"],
            "scheme_id": '',
            "position": user_data["user_title"],
            "email": user_data["user_email"],
            "first_name": user_data["user_first_name"],
            "last_name": user_data["user_last_name"],
            "password": "password1+"
        }
        self._logger_bot.info("User data is %s", user_data)
        response = self._mm_web_client.mattermost_session.post(
            f'{self._mm_web_client.mattermost_url}/users', json=data)

        if response.status_code == 201:
            response_date = response.json()
            self._users_list.append(response_date)
            user_id = response_date["id"]
            self._logger_bot.info(f'User {self._get_user(user_id)} created|Session:{self._session_id}')

            self._add_user_to_team(user_id=user_id, team_id=self._team_id)
            CommonCounter.increment_user(self._session_id)

        else:
            self._logger_bot.error(
                f'Mattermost API Error (users). Status code: {response.status_code} '
                f'Response:{response.text} Session:{self._session_id}')
            CommonCounter.increment_error(self._session_id)

        return user_id

    def load_team_id(self):
        response = self._mm_web_client.mattermost_session.get(f'{self._mm_web_client.mattermost_url}/teams')
        if response.status_code == 200:
            response_data = response.json()
            self._team_id = response_data[0]["id"]
            self._logger_bot.info(f'Mattermost team_id loaded - {self._team_id}|Session:{self._session_id}')
            # self._logger_bot.info(f'Teams: {response_data}|Session:{self._session_id}')
        else:
            self._logger_bot.error(
                f'Mattermost API Error (teams). Status code: {response.status_code} '
                f'Response:{response.text} Session:{self._session_id}')
            CommonCounter.increment_error(self._session_id)

    def _add_user_to_channel(self, user_id: str, channel_id: str):
        response = ''
        if user_id is None or channel_id is None:
            return

        try:
            self._logger_bot.info("Started adding user %s to channel %s", self._get_user(user_id)["name"],
                                  self._get_channel(channel_id)["name"])
            #            self._logger_bot.info("Users data: %s", self._get_user(user_id))
            #            self._logger_bot.info("Channels data: %s", self._get_channel(channel_id))
            payload = {
                "user_id": user_id,
            }

            response = self._mm_web_client.mattermost_session.post(f'{self._mm_web_client.mattermost_url}'
                                                                   f'/channels/{channel_id}/members',
                                                                   json=payload)
            response.raise_for_status()

            channels = self._channels_list
            i = 0
            for channel in channels:
                if channel["id"] == channel_id:
                    self._channels_list[i]["members"].append(user_id)
                    break
                i += 1

            self._logger_bot.info(f'User {self._get_user(user_id)["name"]} '
                                  f'added to channel {self._get_channel(channel_id)["name"]}|'
                                  f'Session:{self._session_id}')
        except Exception as err:
            self._logger_bot.error(
                f'Mattermost API Error (channels/member). Status code: {response.status_code} Response:{response.text} '
                f'Error:{err} Session:{self._session_id}')
            CommonCounter.increment_error(self._session_id)

    def _set_channels_members(self, channel_id: str):
        channels = self._channels_list
        i = 0
        for channel in channels:
            if channel["id"] == channel_id:
                channel_members_list = self._get_channels_members(channel_id)
                member_list = []
                for channel_member in channel_members_list:
                    member_list.append(channel_member["user_id"])
                self._channels_list[i]["members"] = member_list
                break
            i += 1

    def _get_channels_members(self, channel_id: str) -> list:
        response = ''
        channel_members = []
        try:

            response = self._mm_web_client.mattermost_session.get(f'{self._mm_web_client.mattermost_url}'
                                                                  f'/channels/{channel_id}/members')
            response.raise_for_status()
            channel_members = response.json()

 #           self._logger_bot.info(f'Got members of channel {self._get_channel(channel_id)["name"]}|'
 #                                 f'Session:{self._session_id}')
        except Exception as err:
            self._logger_bot.error(
                f'Mattermost API Error (channels/members). '
                f'Status code: {response.status_code} Response:{response.text} '
                f'Error:{err} Session:{self._session_id}')
            CommonCounter.increment_error(self._session_id)
        return channel_members

    def _is_user_in_channel(self, user_id: str, channel_id: str) -> bool:
        is_member = False
        channels = self._get_channel(channel_id)
        if "members" in channels:
            for member in channels["members"]:
                if member == user_id:
                    is_member = True
        return is_member

    def _add_user_to_team(self, user_id: str, team_id: str):
        response = ''
        try:
            payload = {
                "user_id": user_id,
                "team_id": team_id
            }

            response = self._mm_web_client.mattermost_session.post(f'{self._mm_web_client.mattermost_url}'
                                                                   f'/teams/{team_id}/members',
                                                                   json=payload)
            response.raise_for_status()

            self._logger_bot.info(f'User {self._get_user(user_id)["name"]} added to team {team_id}|'
                                  f'Session:{self._session_id}')
        except Exception as err:
            self._logger_bot.error(
                f'Mattermost API Error (teams/members). Status code: {response.status_code} Response:{response.text}'
                f'Error:{err} Session:{self._session_id}')
            CommonCounter.increment_error(self._session_id)

    def set_channel_filter(self, channel_filter):
        if len(channel_filter) != 0 and channel_filter != 'all':
            self._channel_filter = channel_filter.split(" ")

    def set_channels_list(self, channels):
        self._channels_list = channels

    def set_users_list(self, users):
        self._users_list = users

    def _is_selected_channel(self, channel_name) -> bool:
        is_channel_selected = False
        if len(self._channel_filter) == 0:
            is_channel_selected = True
        else:
            if channel_name in self._channel_filter:
                is_channel_selected = True

        return is_channel_selected

    def get_channel_list(self) -> list:
        return self._channels_list

    def _get_set_slack_ts(self, messages_data: dict) -> set:
        slack_ts_set = set()
        for message_id, message in messages_data.items():
            if "props" in message and "slack_ts" in message["props"]:
                slack_ts_set.add(message["props"]["slack_ts"])
        return slack_ts_set

    def set_main_slack_user_id(self, slack_user_id):
        self._main_slack_user_id = slack_user_id

    def set_session_id(self, session_id):
        self._session_id = session_id
