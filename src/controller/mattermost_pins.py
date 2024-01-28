import logging
from typing import List

from requests import HTTPError

from src.entity.pin_entity import PinEntity
from src.util.common_counter import CommonCounter


class MattermostPins:

    def __init__(self, mattermost_web_client):
        self._logger_bot = logging.getLogger("")
        self._mm_web_client = mattermost_web_client
        self._messages_per_page = 100

    def _map_dict_to_pin_entity(self, data: dict) -> PinEntity:
        pin_entity = PinEntity(pin_id=0,
                               slack_channel_id='',
                               mm_channel_id=data["channel_id"],
                               created=data["create_at"],
                               message_mm_id=data["id"],
                               message_ts=data["props"]["slack_ts"])
        return pin_entity

    def load(self, channel_id, session_id: str) -> List[PinEntity]:
        pin_entity_list: List[PinEntity] = []
        response = ''
        pin_dict = {}
        try:

            data = {
                "channel_id": channel_id
            }
            self._logger_bot.info("Started loading pinned messages from Mattermost")
            response = self._mm_web_client.mattermost_session.get(
                f'{self._mm_web_client.mattermost_url}/channels/{channel_id}/pinned', json=data)
            response.raise_for_status()
            pin_dict = response.json()["posts"]

            self._logger_bot.info(f'Mattermost pins loaded ({len(pin_dict)})|Session: {session_id}')

        except HTTPError as err:
            self._logger_bot.error(
                f'Mattermost API Error (channels/pinned). Status code: {response.status_code} '
                f'Response:{response.text} Error: {err} Session:{session_id}')
            CommonCounter.increment_error(session_id)

        for key, pin in pin_dict.items():
            pin_entity_list.append(self._map_dict_to_pin_entity(pin))
        return pin_entity_list

    def unpin(self, post_id, session_id: str):

        response = ''
        try:
            response = self._mm_web_client.mattermost_session.post(
                f'{self._mm_web_client.mattermost_url}/posts/{post_id}/unpin')
            response.raise_for_status()
            data = response.json()
            self._logger_bot.info(f'Mattermost post {post_id} unpinned|Session:{session_id}' )

        except HTTPError as err:
            self._logger_bot.error(
                f'Mattermost API Error (posts/unpin). Status code: {response.status_code} '
                f'Response:{response.text} Error:{err} Session:{session_id}')
            CommonCounter.increment_error(session_id)

    def pin(self, post_id: str, session_id: str):
        response = ''
        try:
            response = self._mm_web_client.mattermost_session.post(
                f'{self._mm_web_client.mattermost_url}/posts/{post_id}/pin')
            response.raise_for_status()
            data = response.json()
            self._logger_bot.info(f'Mattermost post {post_id} pinned|Session:{session_id}')
            CommonCounter.increment_pin(session_id)

        except HTTPError as err:
            self._logger_bot.error(
                f'Mattermost API Error (posts/pin). Status code: {response.status_code} '
                f'Response:{response.text} Error:{err} Session:{session_id}')
            CommonCounter.increment_error(session_id)

    def get_message_id_by_ts(self, messages_dict: dict, ts: str) -> str:
        post_id = ''
        for message_id, message in messages_dict.items():
            if "slack_ts" in message["props"] and message["props"]["slack_ts"] == ts:
                post_id = message_id
                break
        return post_id
