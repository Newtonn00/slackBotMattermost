import logging

from requests import HTTPError


class MattermostUploadMessages:
    def __init__(self, mattermost_web_client):
        self._channels_list = []
        self._users_list = []
        self._team_id = None
        self._logger_bot = logging.getLogger("")
        self._mm_web_client = mattermost_web_client
        #        self._team_id = 'iwmq1ygp47rg3jqxtxw1iwfn7e'
        self._messages_per_page = 100

    def load_users(self):
        params = {
            "page": 0,  # Номер страницы (начиная с 0)
            "per_page": self._messages_per_page  # Количество элементов на странице
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
                params["page"] += 1  # Переходим на следующую страницу

            self._logger_bot.info("Mattermost users loaded (%d)", len(self._users_list))


        except HTTPError:
            self._logger_bot.error(
                f'Mattermost API Error (users). Status code: {response.status_code} Response:{response.text}')

    def load_channels(self):
        params = {
            "page": 0,  # Номер страницы (начиная с 0)
            "per_page": self._messages_per_page  # Количество элементов на странице
        }
        self._channels_list = []
        try:
            while True:
                response = self._mm_web_client.mattermost_session.get(
                    f'{self._mm_web_client.mattermost_url}/channels',
                    params=params)
                response.raise_for_status()
                channels = response.json()

                if not channels:
                    break
                self._channels_list.extend(channels)
                params["page"] += 1  # Переходим на следующую страницу
            self._logger_bot.info("Mattermost channels loaded (%d)", len(self._channels_list))
            channels = self._channels_list
            for channel in channels:
                self._set_channels_members(channel["id"])
        except HTTPError:
            self._logger_bot.error(
                f'Mattermost API Error (channels). Status code: {response.status_code} Response:{response.text}')

    def upload_messages(self, message_data):
        channel_id = self._get_channel_by_name(message_data["channel"])
        user_data = message_data["user"]
        user_id = self._get_user_by_email(user_data)
        if channel_id is None:
            self._logger_bot.error("Channel %s did`nt find in Mattermost", message_data["channel_name"])
            return

        if not self._is_user_in_channel(user_id=user_id, channel_id=channel_id):
            self._add_user_to_channel(user_id=user_id, channel_id=channel_id)

        files_list = []
        self._logger_bot.info("Message is loading to Mattermost")
        if message_data["is_attached"]:
            files_list = self._upload_files(message_data["files"], channel_id=channel_id)

        data = {
            "channel_id": channel_id,
            "message": message_data["text"],
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
        post_info = {}
        if response.status_code == 201:
            post_info = response.json()
            self._logger_bot.info("Message loaded to Mattermost")

            if message_data["is_thread"]:
                orig_post_id = post_info["id"]

                for reply_message in message_data["reply"]:
                    self._logger_bot.info("Thread`s message is loading to Mattermost")
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
                        self._logger_bot.info("Threads`s message loaded to Mattermost")
                    else:
                        self._logger_bot.error(
                            f'Mattermost API Error (posts). Status code: {response.status_code} '
                            f'Response:{response.text}')

        else:
            self._logger_bot.error(
                f'Mattermost API Error (posts). Status code: {response.status_code} Response:{response.text}')

    def _upload_files(self, files_from_message: list, channel_id: str) -> list:
        files_list = []
        for file in files_from_message:
            self._logger_bot.info("File %s is loading to Mattermost", file["file_path"])
            files = {"files": open(file["file_path"], "rb")}
            params = {"channel_id": channel_id}

            response_file = self._mm_web_client.mattermost_session.post(
                f'{self._mm_web_client.mattermost_url}/files', params=params,
                files=files)

            if response_file.status_code == 201:
                response_json = response_file.json()
                self._logger_bot.info("File %s loaded to Mattermost", file["file_path"])
                files_list.append(response_json['file_infos'][0]['id'])
            else:
                self._logger_bot.error(
                    f'Mattermost API Error (files). Status code: {response_file.status_code} '
                    f'Response:{response_file.text}')
        return files_list

    def _get_user_by_email(self, user_data: dict) -> str:
        user_id = None
        for user in self._users_list:
            if user["email"] == user_data["user_email"]:
                user_id = user["id"]
                break

        if user_id is None and not user_data["user_is_bot"]:
            self._logger_bot.info("user_data: %s", user_data)
            self._logger_bot.info("users_list: %s", self._users_list)
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
        for channel in self._channels_list:
            if channel["name"] == channel_data["channel_name"]:
                channel_id = channel["id"]
                break

        if channel_id is None:
            channel_id = self._create_channel(channel_data)

        return channel_id

    def _create_channel(self, channel_data: dict) -> str:
        self._logger_bot.info("Channel %s is creating", channel_data["channel_name"])

        channel_id = None
        data = {
            "team_id": self._team_id,
            "name": channel_data["channel_name"],
            "display_name": channel_data["channel_name"],
            "scheme_id": '',
            "type": "O",  # "O" для общедоступного канала, "P" для частного
        }
        if channel_data["channel_type"] == "private":
            data["type"] = "P"
        response = self._mm_web_client.mattermost_session.post(
            f'{self._mm_web_client.mattermost_url}/channels', json=data)

        if response.status_code == 201:
            response_data = response.json()
            channel_id = response_data["id"]
            self._channels_list.append(response_data)
            self._logger_bot.info("Channel %s created", channel_data["channel_name"])
        else:
            self._logger_bot.error(
                f'Mattermost API Error (channels). Status code: {response.status_code} Response:{response.text}')

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
            self._logger_bot.info("User %s created", user_data["user_name"])

            self._add_user_to_team(user_id=user_id, team_id=self._team_id)

        else:
            self._logger_bot.error(
                f'Mattermost API Error (users). Status code: {response.status_code} Response:{response.text}')

        return user_id

    def load_team_id(self):
        response = self._mm_web_client.mattermost_session.get(f'{self._mm_web_client.mattermost_url}/teams')
        if response.status_code == 200:
            response_data = response.json()
            self._team_id = response_data[0]["id"]
            self._logger_bot.info("Mattermost team_id loaded - %s", self._team_id)
            self._logger_bot.info("Teams: %s", response_data)
        else:
            self._logger_bot.error(
                f'Mattermost API Error (teams). Status code: {response.status_code} Response:{response.text}')

    def _add_user_to_channel(self, user_id: str, channel_id: str):
        if user_id is None or channel_id is None:
            return



        try:
            self._logger_bot.info("Started adding user %s to channel %s", user_id, channel_id)
            self._logger_bot.info("Users data: %s", self._get_user(user_id))
            self._logger_bot.info("Channels data: %s", self._get_channel(channel_id))
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

            self._logger_bot.info("User %s added to channel %s", self._get_user(user_id), self._get_channel(channel_id))
        except Exception as err:
            self._logger_bot.error(
                f'Mattermost API Error (channels/member). Status code: {response.status_code} Response:{response.text} '
                f'Error:{err}')

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

        channel_members = []
        try:

            response = self._mm_web_client.mattermost_session.get(f'{self._mm_web_client.mattermost_url}'
                                                                  f'/channels/{channel_id}/members')
            response.raise_for_status()
            channel_members = response.json()

            self._logger_bot.info("Got members of channel %s", self._get_channel(channel_id)["name"])
        except Exception:
            self._logger_bot.error(
                f'Mattermost API Error (channels/members). Status code: {response.status_code} Response:{response.text}')
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
        try:
            payload = {
               "user_id": user_id,
            }

            response = self._mm_web_client.mattermost_session.post(f'{self._mm_web_client.mattermost_url}'
                                                                   f'/teams/{team_id}/members',
                                                                   json=payload)
            response.raise_for_status()

            self._logger_bot.info("User %s added to team %s", self._get_user(user_id), team_id)
        except Exception:
            self._logger_bot.error(
                f'Mattermost API Error (teams/members). Status code: {response.status_code} Response:{response.text}')

