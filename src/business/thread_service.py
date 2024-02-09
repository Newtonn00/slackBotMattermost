import logging
from datetime import datetime, timedelta

from src.controller.channel_lock import ChannelLock


class ThreadService:
    _slack_channels_list: dict
    _mm_channels_list: list
    _slack_load_pins = None
    _slack_users_list: list

    def __init__(self, config_service, messages_service, mattermost_messages,
                 slack_messages_handler, user_service):
        self._mattermost_messages = mattermost_messages
        self._slack_messages_handler = slack_messages_handler
        self._last_sync_date = config_service.get_all_last_synchronize_date_unix()
        self._message_service = messages_service
        self._channel_filter = []
        self._user_service = user_service
        self._session_id = None
        self._logger_bot = logging.getLogger("")

    def process(self):
        self._user_service.load_slack(self._session_id)
        self.set_slack_users_list(self._user_service.get_users_slack_as_list())
        self._apply_filter_to_mm_channel()
        self._apply_filter_to_slack_channel()
        self._message_service.set_users_list(self._slack_users_list)
        self._message_service.set_channels_list(self._slack_channels_list)
        for channel_key, channel_item in self._slack_channels_list.items():

            locked_channel = ChannelLock.lock_channel(channel_id=channel_key, session_id=self._session_id)
            if not locked_channel["ok"]:
                self._logger_bot.info(f'{locked_channel["message"]} | Session: {self._session_id}')
                continue

            mm_channel_id = self._get_mm_channel_id_by_name(channel_item["name"])["id"]
            date_for_selection_messages = int((datetime.now() - timedelta(days=90)).timestamp())
            mm_messages_dict = self._mattermost_messages.load_messages(mm_channel_id, self._session_id)
            slack_ts_set = self._get_set_slack_ts(mm_messages_dict)
            slack_thread_timestamps = {}
            last_date_sync_unix = datetime.strptime(self._last_sync_date.get(channel_item["name"],
                                                                             {self._last_sync_date.get("all",
                                                                                                       "1970-01-01 00:00:00")}),
                                                    "%Y-%m-%d %H:%M:%S").timestamp()
            new_last_date_sync_unix = last_date_sync_unix
            if mm_messages_dict:
                slack_thread_timestamps = self._get_slack_thread_timestamps(mm_messages_dict,
                                                                            int(last_date_sync_unix))

            for mm_post_id, slack_message_ts in slack_thread_timestamps.items():
                reply_messages = self._slack_load_thread_replies(channel_key, ts=slack_message_ts)

                for message in reply_messages:

                    if message["ts"] not in slack_ts_set:

                        slack_ts_set.add(message["ts"])
                        if "files" in message:
                            files_list = self._slack_messages_handler.download_files(message["files"],
                                                                                     session_id=self._session_id)
                            message["files"] = files_list

                        message["post_id"] = mm_post_id
                        message["channel"] = channel_key
                        if "files" in message:
                            message["is_attached"] = True
                        else:
                            message["is_attached"] = False
                        self._upload_message_to_mattermost(message)
            ChannelLock.release_channel(channel_id=channel_key, session_id=self._session_id)

    def _upload_message_to_mattermost(self, message: dict):
        self._message_service.save_reply_to_mattermost(message)

    def _slack_load_thread_replies(self, channel_id: str, ts: str, last_date_sync_unix = 0) -> list:
        reply_messages = self._slack_messages_handler.load_threads(channel_id, ts, last_date_sync_unix,
                                                                   session_id=self._session_id)
        return reply_messages

    def _get_slack_thread_timestamps(self, messages_dict: dict, last_date_sync_unix: int) -> dict:
        thread_messages = dict()
        for message_id, message in messages_dict.items():
            if message["root_id"]:
                message_root = messages_dict.get(message["root_id"])
                if message_root and "slack_ts" in message_root["props"]:
                    ts = message_root["props"]["slack_ts"]
                    if int(float(ts)) < last_date_sync_unix:
                        thread_messages.update({message["root_id"]: ts})
        return thread_messages

    def set_slack_users_list(self, users_list):
        self._slack_users_list = users_list

    def set_slack_channels_list(self, channels_list):
        self._slack_channels_list = channels_list

    def set_mm_channels_list(self, channels_list):
        self._mm_channels_list = channels_list

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

    def _get_set_slack_ts(self, messages_data:dict) -> set:
        slack_ts_set = set()
        for message_id, message in messages_data.items():
            if "props" in message and "slack_ts" in message["props"]:
                slack_ts_set.add(message["props"]["slack_ts"])
        return slack_ts_set

    def set_session_id(self, session_id):
        self._session_id = session_id

