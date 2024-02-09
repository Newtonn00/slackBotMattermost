import os
from typing import List

from src.entity.emoji_entity import EmojiEntity


class EmojiService:
    def __init__(self, slack_emoji_handler, mattermost__emoji_handler, user_service):
        self._main_user = None
        self._slack_emoji_handler = slack_emoji_handler
        self._mattermost_emoji_handler = mattermost__emoji_handler
        self._user_service = user_service
        self._emoji_count: int = -1

    def process(self, session_id: str):
        self._slack_emoji_handler.set_main_user(self._main_user)
        self._mattermost_emoji_handler.set_main_user(self._user_service.get_user_id_mattermost_by_user_id_slack_direct(slack_user_id=self._main_user, session_id=session_id))
        emoji_entity_list: List[EmojiEntity]
        emoji_entity_list = self._slack_emoji_handler.load(session_id)
        em_count: int = 1
        res_dict = {}
        for emoji_entity in emoji_entity_list:
            if not emoji_entity.local_file_path:
                continue
            if not (self._emoji_count > -1 and em_count > self._emoji_count):
                res_dict = self._mattermost_emoji_handler.save(session_id=session_id, emoji=emoji_entity)

            if emoji_entity.local_file_path:
                if os.path.exists(emoji_entity.local_file_path):
                    os.remove(emoji_entity.local_file_path)

            if "ok" in res_dict and res_dict["ok"]:
                em_count += 1

    def set_main_user(self, user_id):
        self._main_user = user_id

    def set_emoji_count(self, emoji_count: int):
        self._emoji_count = emoji_count
