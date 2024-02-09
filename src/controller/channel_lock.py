from datetime import datetime
from threading import Lock


class ChannelLock:
    _slack_channel_in_use = {}
    _lock = Lock()

    @classmethod
    def lock_channel(cls, session_id, channel_id):
        with cls._lock:
            if channel_id in cls._slack_channel_in_use and cls._slack_channel_in_use[channel_id]["session_id"] != session_id:
                # Канал уже заблокирован, возвращаем ошибку
                return {"ok": False, "message": f'Channel {channel_id} already locked'}

            cls._slack_channel_in_use[channel_id] = {
                "channel_id": channel_id,
                "session_id": session_id,
                "time_stamp": datetime.now().timestamp()
            }

            # Успешно заблокирован
            return {"ok": True}

    @classmethod
    def clean_locked_channels(cls):
        with cls._lock:
            for channel_key, channel_item in list(cls._slack_channel_in_use.items()):
                if datetime.now().timestamp() - channel_item["time_stamp"] > 1800:
                    del cls._slack_channel_in_use[channel_key]

    @classmethod
    def release_channel(cls, channel_id, session_id):
        with cls._lock:
            if channel_id in cls._slack_channel_in_use and cls._slack_channel_in_use[channel_id]["session_id"] == session_id:
                del cls._slack_channel_in_use[channel_id]
