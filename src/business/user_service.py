from datetime import datetime
import logging
import os
from typing import List
import re

from src.entity.user_entity import UserEntity


class UserService:
    _users_list_slack: List[UserEntity] = []
    _users_list_mattermost: List[UserEntity] = []
    _team_id: str = ""

    def __init__(self, slack_users_handler, mattermost_users_handler):
        self._logger_bot = logging.getLogger("")
        self._slack_users_handler = slack_users_handler
        self._mattermost_users_handler = mattermost_users_handler
        self._transfer_profile_image = False
        self._users_filter = ""
        self._last_time_mm_update = 0
        self._last_time_slack_update = 0

    def sync_process(self, session_id: str):
        self.load_mattermost(session_id)
        self.load_slack(session_id)
        self.load_team(session_id)
        for user_slack in self._users_list_slack:
            if user_slack.email and (not self._users_filter or user_slack.email.lower() in self._users_filter):
                mm_user_id = self.get_user_id_mattermost_by_email(user_slack.email)
                if mm_user_id:
                    user_mm = self._get_user_entity_mattermost(mm_user_id)
                    if (user_mm.title != user_slack.title
                            or user_mm.first_name != user_slack.first_name
                            or user_mm.last_name != user_slack.last_name
                            or user_mm.display_name != user_slack.display_name):
                        self._logger_bot.info("Started updating user %s", user_slack.name)
                        self._logger_bot.info("User data: %s", user_slack)
                        user_mm.title = user_slack.title
                        user_mm.first_name = user_slack.first_name
                        user_mm.last_name = user_slack.last_name
                        user_mm.display_name = user_slack.display_name
                        self._update_user_mattermost(user_mm, session_id)
                        self._logger_bot.info("Finished updating user %s", user_slack.name)

                    if self._transfer_profile_image and user_slack.image_original is not None:
                        image_local_path = self._get_path_users_image_slack(user_slack, session_id)
                        if image_local_path:
                            self._upload_users_image_mattermost(local_path=image_local_path, mm_user_id=mm_user_id,
                                                                session_id=session_id)
                            self._delete_image(image_local_path)

                elif not user_slack.is_bot and user_slack.email is not None:
                    self._logger_bot.info("Started creating user %s", user_slack.name)

                    user_dict_mm = self.create_user_mattermost(user_slack, session_id)
                    user_list_mm = [user_dict_mm]
                    self.load_mattermost(session_id=session_id, users_list=user_list_mm)
                    mm_user_id = self.get_user_id_mattermost_by_email(user_slack.email)
                    image_local_path = self._get_path_users_image_slack(user_slack, session_id)
                    if image_local_path:
                        self._upload_users_image_mattermost(local_path=image_local_path, mm_user_id=mm_user_id,
                                                            session_id=session_id)
                        self._delete_image(image_local_path)
                    self._logger_bot.info("Finished creating user %s", user_slack.name)

    def load_slack(self, session_id: str, users_list=None):
        if self._users_list_slack and (datetime.now().timestamp() - self._last_time_slack_update < 3600) and users_list is None:
            return

        self._users_list_slack = []
        if users_list is None:
            user_list_json = self._slack_users_handler.load(session_id)
        else:
            user_list_json = users_list

        for user in user_list_json:
            user_entity = UserEntity(id=user.get("id"),
                                     name=user.get("name"),
                                     display_name=user["profile"].get("display_name") if "profile" in user and user[
                                         "profile"] is not None else user.get("real_name"),
                                     title=user["profile"].get("title"),
                                     first_name=user["profile"].get("first_name"),
                                     last_name=user["profile"].get("last_name"),
                                     email=user["profile"].get("email") if "profile" in user and user[
                                         "profile"] is not None else None,
                                     is_bot=user.get("is_bot"),
                                     is_deleted=user.get("deleted"),
                                     is_app_user=user.get("is_app_user"),
                                     image_original=user["profile"].get("image_original")
                                     )

            self._users_list_slack.append(user_entity)
        self._last_time_slack_update = datetime.now().timestamp()

    def load_mattermost(self, session_id: str, users_list=None):
        if self._users_list_mattermost and users_list is None and (datetime.now().timestamp() - self._last_time_mm_update < 3600):
            return
        if users_list is None:
            user_list_json = self._mattermost_users_handler.load(session_id)
        else:
            user_list_json = users_list
        for user in user_list_json:
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

            self._users_list_mattermost.append(user_entity)
        self._last_time_mm_update = datetime.now().timestamp()

    def get_users_slack(self) -> List[UserEntity]:
        return self._users_list_slack

    def get_users_slack_as_list(self) -> list:
        users_list = []
        for user in self._users_list_slack:
            users_list.append(user.as_dict())

        return users_list

    def get_users_slack_as_dict(self) -> dict:
        users_dict = {}
        for user in self._users_list_slack:
            users_dict[user.id] = user.as_dict()

        return users_dict

    def get_users_mattermost(self) -> List[UserEntity]:
        return self._users_list_mattermost

    def get_users_mattermost_as_list(self) -> list:
        users_list = []
        for user in self._users_list_mattermost:
            users_list.append(user.as_dict())

        return users_list

    def get_user_id_mattermost_by_email(self, email: str) -> str:
        user_id = None
        for user in self._users_list_mattermost:
            if email and email.lower() == user.email.lower():
                user_id = user.id
                break
        return user_id

    def get_user_id_mattermost_by_user_id_slack(self, slack_user_id: str) -> str:
        mm_user_id = ""
        user_entity_slack = self.get_user_entity_slack(slack_user_id)
        if user_entity_slack and user_entity_slack.email:
            for user in self._users_list_mattermost:
                if user.email and user.email.lower() == user_entity_slack.email.lower():
                    mm_user_id = user.id
                    break
        return mm_user_id

    def _get_user_entity_mattermost(self, user_id: str) -> UserEntity:
        user_entity = UserEntity
        for user in self._users_list_mattermost:
            if user.id == user_id:
                user_entity = user
                break
        return user_entity

    def get_user_entity_slack(self, user_id: str) -> UserEntity:
        user_entity = UserEntity
        for user in self._users_list_slack:
            if user.id == user_id:
                user_entity = user
                break
        return user_entity

    def load_team(self, session_id: str):
        self._team_id = self._mattermost_users_handler.load_team(session_id)

    def create_user_mattermost(self, user_data: UserEntity, session_id: str) -> dict:

        data = {
            "team_id": self._team_id,
            "username": user_data.name,
            "nickname": user_data.display_name,
            "position": user_data.title,
            "email": user_data.email,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "password": "password1+"
        }
        user_dict_mm = self._mattermost_users_handler.create(data, session_id)
        return user_dict_mm

    def _update_user_mattermost(self, mm_user_entity: UserEntity, session_id: str):

        data = {
            "team_id": self._team_id,
            "username": mm_user_entity.name,
            "nickname": mm_user_entity.display_name,
            "position": mm_user_entity.title,
            "first_name": mm_user_entity.first_name,
            "last_name": mm_user_entity.last_name
        }
        self._mattermost_users_handler.update(mm_user_entity.id, data, session_id)

    def _is_users_image_mattermost_exist(self, mm_user_entity: UserEntity, session_id: str) -> bool:
        image_exists = False
        if self._mattermost_users_handler.get_profile_image(mm_user_entity.id, session_id):
            image_exists = True
        return image_exists

    def _get_path_users_image_slack(self, slack_user: UserEntity, session_id: str) -> str:
        local_path = self._slack_users_handler.load_profile_image(image_link=slack_user.image_original,
                                                                  user_id=slack_user.id,
                                                                  session_id=session_id)
        return local_path

    def _upload_users_image_mattermost(self, mm_user_id: str, local_path: str, session_id: str):
        self._mattermost_users_handler.upload_profile_image(mm_user_id=mm_user_id, local_path=local_path,
                                                            session_id=session_id)

    def _delete_image(self, local_path):

        if os.path.exists(local_path):
            os.remove(local_path)
            self._logger_bot.info("Deleted file %s", local_path)

    def set_params(self, params: str):
        filter_params = params
        self._transfer_profile_image = False
        pattern = r'-i'
        regex = re.compile(pattern)
        match = re.search(regex, filter_params)
        if match:
            filter_params = re.sub(pattern, "", filter_params).strip()
            self._transfer_profile_image = True

        if filter_params:
            self._users_filter = filter_params.lower().split(" ")
