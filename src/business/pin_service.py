from typing import List

from src.entity.pin_entity import PinEntity


class PinService:
    pin_list: List[PinEntity]
    _slack_channels_list: dict
    _mm_channels_list: list
    _slack_load_pins = None

    def __init__(self, slack_load_pins, mattermost_upload_pins, mattermost_upload_messages, mattermost_messages):
        self._slack_load_pins = slack_load_pins
        self._mattermost_pins = mattermost_upload_pins
        self._mattermost_upload_messages = mattermost_upload_messages
        self._mattermost_messages = mattermost_messages
        self._channel_filter = []

    def set_slack_channels_list(self, channels_list):
        self._slack_channels_list = channels_list

    def set_mm_channels_list(self, channels_list):
        self._mm_channels_list = channels_list

    def pins_process(self):
        self.set_mm_channels_list(self._mattermost_upload_messages.get_channel_list())
        self._apply_filter_to_mm_channel()
        self._apply_filter_to_slack_channel()

        for channel_key, channel_item in self._slack_channels_list.items():
            mm_pin_list: List[PinEntity]
            slack_pin_list = self._get_pins(channel_key)
            mm_channel_id = self._get_mm_channel_id_by_name(channel_item["name"])["id"]
            for pin in slack_pin_list:
                pin.mm_channel_id = mm_channel_id

            mm_pin_list = self._mattermost_pins.load(mm_channel_id)
            for mm_pin in mm_pin_list:
                msg_pinned = False
                for slack_pin in slack_pin_list:
                    if mm_pin.message_ts == slack_pin.message_ts:
                        msg_pinned = True
                if not msg_pinned:
                    self._mattermost_pins.unpin(mm_pin.message_mm_id)

            messages_for_pin = []
            for slack_pin in slack_pin_list:
                msg_pinned = False
                for mm_pin in mm_pin_list:
                    if slack_pin.message_ts == mm_pin.message_ts:
                        msg_pinned = True
                if not msg_pinned:
                    messages_for_pin.append(slack_pin)

            if messages_for_pin:
                messages_dict = self._mattermost_messages.load_messages(mm_channel_id)
                for pin in messages_for_pin:

                    post_id = self._mattermost_pins.get_message_id_by_ts(messages_dict, pin.message_ts)

                    if post_id:
                        self._mattermost_pins.pin(post_id)

    def _get_pins(self, channel_id) -> List[PinEntity]:
        pin_list = self._slack_load_pins.load_pins(channel_id=channel_id)
        return pin_list

    def _get_mm_channel_id_by_name(self, channel_name: str) -> dict:
        mm_channel: dict = {}
        for channel in self._mm_channels_list:
            if channel["name"] == channel_name:
                mm_channel = channel
                break
        return mm_channel

    def _get_slack_channel(self, channel_id: str) -> dict:
        slack_channel: dict = {}
        for channel_key, channel_item in self._slack_channels_list.items():
            if channel_key == channel_id:
                slack_channel = channel_item
                break
        return slack_channel

    def set_channel_filter(self, channel_filter: str):
        if len(channel_filter) != 0 and channel_filter != "all":
            self._channel_filter = channel_filter.split(" ")

    def _apply_filter_to_slack_channel(self):
        channels = self._slack_channels_list
        filtered_channels = {}
        for channel_id, channel_item in channels.items():
            if channel_item["name"] in self._channel_filter:
                filtered_channels[channel_id] = channel_item
        self._slack_channels_list = filtered_channels

    def _apply_filter_to_mm_channel(self):
        channels = self._mm_channels_list
        filtered_channels = []
        for channel in channels:
            if channel["name"] in self._channel_filter:
                filtered_channels.append(channel)
        self._mm_channels_list = filtered_channels
