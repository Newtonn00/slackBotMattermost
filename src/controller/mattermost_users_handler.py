import logging

from requests import HTTPError

from src.util.common_counter import CommonCounter


class MattermostUsersHandler:
    _users_list: list

    def __init__(self, mattermost_web_client):
        self._logger_bot = logging.getLogger("")
        self._mm_web_client = mattermost_web_client
        self._messages_per_page = 100

    def load(self) -> list:

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

            self._logger_bot.info("Mattermost users loaded (%d)", len(self._users_list))

        except HTTPError:
            self._logger_bot.error(
                f'Mattermost API Error (users). Status code: {response.status_code} Response:{response.text}')
            CommonCounter.increment_error()

        return self._users_list

    def load_team(self) -> str:
        team_id: str = ""
        response = self._mm_web_client.mattermost_session.get(f'{self._mm_web_client.mattermost_url}/teams')
        if response.status_code == 200:
            response_data = response.json()
            team_id = response_data[0]["id"]
            self._logger_bot.info("Mattermost team_id loaded - %s", team_id)
            self._logger_bot.info("Teams: %s", response_data)
        else:
            self._logger_bot.error(
                f'Mattermost API Error (teams). Status code: {response.status_code} Response:{response.text}')
            CommonCounter.increment_error()

        return team_id

    def create(self, user_data) -> dict:
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
                self._logger_bot.info("User %s created", user_dict["name"])

            self._add_user_to_team(user_id=user_id, team_id=user_data["team_id"])

        else:
            self._logger_bot.error(
                f'Mattermost API Error (users). Status code: {response.status_code} Response:{response.text}')
            CommonCounter.increment_error()
        return user_dict

    def get_profile_image(self, user_id: str) -> str:
        self._logger_bot.info("Users %s image is getting", user_id)
        user_dict = {}
        response = self._mm_web_client.mattermost_session.get(
            f'{self._mm_web_client.mattermost_url}/users/{user_id}/image')

        if response.status_code == 201 or response.status_code == 200:
            user_dict = response.json()
            user_id = user_dict["id"]
            self._logger_bot.info("Users image was got")

        else:
            self._logger_bot.error(
                f'Mattermost API Error (users/image). Status code: {response.status_code} Response:{response.text}')
            CommonCounter.increment_error()
        return user_dict

    def update(self, user_id: str, user_data: dict):
        self._logger_bot.info("User %s is updating", user_data["username"])
        user_dict = {}
        self._logger_bot.info("User data is %s", user_data)
        response = self._mm_web_client.mattermost_session.put(
            f'{self._mm_web_client.mattermost_url}/users/{user_id}/patch', json=user_data)

        if response.status_code == 201 or response.status_code == 200:
            user_dict = response.json()
            self._logger_bot.info("User %s was updated", user_data["username"])


        else:
            self._logger_bot.error(
                f'Mattermost API Error (users/patch). Status code: {response.status_code} Response:{response.text}')
            CommonCounter.increment_error()

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

            self._logger_bot.info("User %s added to team %s", user_id, team_id)
        except Exception as err:
            self._logger_bot.error(
                f'Mattermost API Error (teams/members). Status code: {response.status_code} Response:{response.text}'
                f'Error:{err}')
            CommonCounter.increment_error()

    def upload_profile_image(self, local_path: str, mm_user_id: str):

        self._logger_bot.info("File %s is uploading to Mattermost", local_path)
        files = {"image": open(local_path, "rb")}
        response_file = self._mm_web_client.mattermost_session.post(
            f'{self._mm_web_client.mattermost_url}/users/{mm_user_id}/image', files=files)

        if response_file.status_code == 200 :
            response_json = response_file.json()
            self._logger_bot.info("File %s uploaded to Mattermost", local_path)
        else:
            self._logger_bot.error(
                f'Mattermost API Error (users/image). Status code: {response_file.status_code} '
                f'Response:{response_file.text}')
            CommonCounter.increment_error()
