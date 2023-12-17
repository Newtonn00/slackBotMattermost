import logging
from typing import List

from requests import HTTPError

from src.entity.pin_entity import PinEntity


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

    def load(self, channel_id) -> List[PinEntity]:
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

            self._logger_bot.info("Mattermost pins loaded (%d)", len(pin_dict))

        except HTTPError as err:
            self._logger_bot.error(
                f'Mattermost API Error (channels/pinned). Status code: {response.status_code} '
                f'Response:{response.text} Error: {err}')

        for key, pin in pin_dict.items():
            pin_entity_list.append(self._map_dict_to_pin_entity(pin))
        return pin_entity_list

    def unpin(self, post_id):

        response = ''
        try:
            response = self._mm_web_client.mattermost_session.post(
                f'{self._mm_web_client.mattermost_url}/posts/{post_id}/unpin')
            response.raise_for_status()
            data = response.json()
            self._logger_bot.info("Mattermost post %s unpinned", post_id)

        except HTTPError:
            self._logger_bot.error(
                f'Mattermost API Error (posts/unpin). Status code: {response.status_code} Response:{response.text}')

    def pin(self, post_id: str):
        response = ''
        try:
            response = self._mm_web_client.mattermost_session.post(
                f'{self._mm_web_client.mattermost_url}/posts/{post_id}/pin')
            response.raise_for_status()
            data = response.json()
            self._logger_bot.info("Mattermost post %s pinned", post_id)

        except HTTPError:
            self._logger_bot.error(
                f'Mattermost API Error (posts/pin). Status code: {response.status_code} Response:{response.text}')

    def load_messages(self, channel_id) -> dict:
        messages_dict = {}
        response = ''
        params = {
            "page": 0,
            "per_page": self._messages_per_page
        }
        try:
            while True:
                response = self._mm_web_client.mattermost_session.get(
                    f'{self._mm_web_client.mattermost_url}/channels/{channel_id}/posts',
                    params=params)
                response.raise_for_status()
                messages = response.json()["posts"]

                if not messages:
                    break

                messages_dict.update(messages)
                params["page"] += 1

            self._logger_bot.info("Mattermost messages loaded (%d)", len(messages_dict))

        except HTTPError as err:
            self._logger_bot.error(
                f'Mattermost API Error (channels/posts). Status code: {response.status_code} '
                f'Response:{response.text} Error:{err}')
        return messages_dict

    def get_message_id_by_ts(self, messages_dict: dict, ts: str) -> str:
        post_id = ''
        for message_id, message in messages_dict.items():
            if "slack_ts" in message["props"] and message["props"]["slack_ts"] == ts:
                post_id = message_id
                break
        return post_id
