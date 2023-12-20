import logging
import time
from typing import List

from slack_sdk.errors import SlackApiError
from slack_sdk import WebClient
from src.util.settings_parser import SettingsParser
from src.entity.pin_entity import PinEntity


class SlackLoadPins:
    REQUEST_TIME_OUT = 408
    RATE_LIMITED_STATUS_CODE = 429
    CREATED = 201
    OK = 200

    def __init__(self):
        settings = SettingsParser()
        self._logger_bot = logging.getLogger("")
        self._web_client = WebClient(settings.slack_bot_token)
        self._slack_token = settings.slack_bot_token
        self._messages_per_page = 100

    def _map_dict_to_pin_entity(self, data: dict) -> PinEntity:
        pin_entity = PinEntity(pin_id=0,
                               slack_channel_id=data["channel"],
                               mm_channel_id='',
                               created=data["created"],
                               message_mm_id='',
                               message_ts=data["message"]["ts"])
        return pin_entity

    def load_pins(self, channel_id: str) -> List[PinEntity]:
        pinned_messages = []
        try:
            max_retries = 3
            retry_count = 0

            while retry_count < max_retries:
                self._logger_bot.info(
                    "Starting request to Slack (pins). %d times repeated",
                    retry_count)
                response = self._web_client.pins_list(
                    channel=channel_id
                )
                response_code = response.status_code

                if response_code == self.OK:
                    pinned_messages = response.data
                    break
                else:
                    retry_count += 1
                    time.sleep(2)
            if retry_count == max_retries:
                raise SlackApiError(message=f'Timeout after {retry_count} retries',
                                    response={"error": f' Timeout error, {self.REQUEST_TIME_OUT}'})
        except SlackApiError as e:
            self._logger_bot.error(
                f"SlackAPIError (conversations_history): {e.response['error']}")

        self._logger_bot.info("Selected %d pinned messages from Slack channel_id %s", len(pinned_messages),
                              channel_id)

        pin_entity: List[PinEntity] = []
        if "items" in pinned_messages:
            for message in pinned_messages["items"]:
                pin_entity.append(self._map_dict_to_pin_entity(message))

        return pin_entity
