import logging

from requests import HTTPError

from src.entity.user_entity import UserEntity
from src.util.common_counter import CommonCounter


class MattermostUsersHandler:
    _users_list: list

    def __init__(self, mattermost_web_client):
        self._logger_bot = logging.getLogger("")
        self._mm_web_client = mattermost_web_client
        self._messages_per_page = 100

    def _map_dict_to_user_entity(self, user: dict) -> UserEntity:

        user_entity = UserEntity(id=user.get("id"),
                                 name=user.get("username"),
                                 display_name=user.get("nickname") if "profile" in user and user[
                                     "profile"] is not None else user.get("real_name"),
                                 title=user.get("position"),
                                 first_name=user.get("first_name"),
                                 last_name=user.get("last_name"),
                                 email=user.get("email"),
                                 is_bot=user.get("is_bot") if "is_bot" in user else False,
                                 is_deleted=False,
                                 is_app_user=False,
                                 image_original=""
                                 )

        return user_entity

    def load(self, session_id: str) -> list:

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

            self._logger_bot.info(f'Mattermost users loaded ({len(self._users_list)})|Session:{session_id}')

        except HTTPError as err:
            self._logger_bot.error(
                f'Mattermost API Error (users). Status code: {response.status_code} '
                f'Response:{response.text} Error:{err} | Session:{session_id}')
            CommonCounter.increment_error(session_id)

        return self._users_list

    def load_team(self, session_id: str) -> str:
        team_id: str = ""
        response = self._mm_web_client.mattermost_session.get(f'{self._mm_web_client.mattermost_url}/teams')
        if response.status_code == 200:
            response_data = response.json()
            team_id = response_data[0]["id"]
            self._logger_bot.info(f'Mattermost team_id loaded - {team_id} | Session:{session_id}')
            self._logger_bot.info(f'Teams: {response_data} | Session:{session_id}')
        else:
            self._logger_bot.error(
                f'Mattermost API Error (teams). Status code: {response.status_code} '
                f'Response:{response.text} | Session:{session_id}')
            CommonCounter.increment_error(session_id)

        return team_id

    def create(self, user_data, session_id: str) -> dict:
        user_id = ""
        self._logger_bot.info("User %s is creating", user_data["username"])
        user_dict = {}
        self._logger_bot.info("User data is %s", user_data)
        response = self._mm_web_client.mattermost_session.post(
            f'{self._mm_web_client.mattermost_url}/users', json=user_data)

        if response.status_code == 201:
            user_dict = response.json()
            user_id = user_dict["id"]
            if "name" in user_dict:
                self._logger_bot.info(f'User {user_dict["name"]} created | Session:{session_id}')

            self._add_user_to_team(user_id=user_id, team_id=user_data["team_id"], session_id=session_id)

        else:
            self._logger_bot.error(
                f'Mattermost API Error (users). Status code: {response.status_code} '
                f'Response:{response.text} Session:{session_id}')
            CommonCounter.increment_error(session_id)
        return user_dict

    def get_profile_image(self, user_id: str, session_id: str) -> str:
        self._logger_bot.info(f'Users {user_id} image is getting|Session:{session_id}')
        user_dict = {}
        response = self._mm_web_client.mattermost_session.get(
            f'{self._mm_web_client.mattermost_url}/users/{user_id}/image')

        if response.status_code == 201 or response.status_code == 200:
            user_dict = response.json()
            user_id = user_dict["id"]
            self._logger_bot.info(f'Users image was got|Session:{session_id}')

        else:
            self._logger_bot.error(
                f'Mattermost API Error (users/image). Status code: {response.status_code} '
                f'Response:{response.text} Session:{session_id}')
            CommonCounter.increment_error(session_id)
        return user_dict

    def update(self, user_id: str, user_data: dict, session_id: str):
        self._logger_bot.info(f'User {user_data["username"]} is updating|Session:{session_id}')
        user_dict = {}
        self._logger_bot.info(f'User data is {user_data}|Session:{session_id}')
        response = self._mm_web_client.mattermost_session.put(
            f'{self._mm_web_client.mattermost_url}/users/{user_id}/patch', json=user_data)

        if response.status_code == 201 or response.status_code == 200:
            user_dict = response.json()
            self._logger_bot.info(f'User {user_data["username"]} was updated|Session:{session_id}')
        else:
            self._logger_bot.error(
                f'Mattermost API Error (users/patch). Status code: {response.status_code} '
                f'Response:{response.text} Session:{session_id}')
            CommonCounter.increment_error(session_id)

    def _add_user_to_team(self, user_id: str, team_id: str, session_id: str):
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

            self._logger_bot.info(f'User {user_id} added to team {team_id}|Session:{session_id}')
        except Exception as err:
            self._logger_bot.error(
                f'Mattermost API Error (teams/members). Status code: {response.status_code} '
                f'Response:{response.text} Session:{session_id}'
                f'Error:{err}')
            CommonCounter.increment_error(session_id)

    def upload_profile_image(self, local_path: str, mm_user_id: str, session_id: str):

        self._logger_bot.info(f'File {local_path} is uploading to Mattermost|Session:{session_id}')
        files = {"image": open(local_path, "rb")}
        response_file = self._mm_web_client.mattermost_session.post(
            f'{self._mm_web_client.mattermost_url}/users/{mm_user_id}/image', files=files)

        if response_file.status_code == 200:
            response_json = response_file.json()
            self._logger_bot.info(f'File {local_path} uploaded to Mattermost|Session:{session_id}')
        else:
            self._logger_bot.error(
                f'Mattermost API Error (users/image). Status code: {response_file.status_code} '
                f'Response:{response_file.text} Session:{session_id}')
            CommonCounter.increment_error(session_id)

    def get_user_by_email(self, session_id: str, email: str) -> UserEntity:

        response = ''
        user_data = {}
        user_entity = None
        try:
            data = {
                "email": email
            }
            response = self._mm_web_client.mattermost_session.get(
                f'{self._mm_web_client.mattermost_url}/users/email/{email}', data=data)
            response.raise_for_status()
            user_data = response.json()

            self._logger_bot.info(f'Mattermost users info by mail {email} loaded | Session:{session_id}')

        except HTTPError as err:
            self._logger_bot.error(
                f'Mattermost API Error (user info). Status code: {response.status_code} '
                f'Response:{response.text} Error:{err} | Session:{session_id}')
            CommonCounter.increment_error(session_id)

        if user_data:
            user_entity = self._map_dict_to_user_entity(user_data)

        return user_entity
