from datetime import datetime
from threading import Lock

from src.entity.config_entity import ConfigEntity


class ConfigService:
    def __init__(self, config_repo):
        self._config_repo = config_repo
        self._lock = Lock()

    def get_config(self) -> ConfigEntity:
        return self._config_repo.read_config()

    def add_channels(self, channels: str) -> ConfigEntity:
        channels_list = channels.split(" ")
        config_entity = self._config_repo.read_config()
        channel: str
        for channel in channels_list:
            if channel[0] == "+":
                if config_entity.excluded_channels.count(channel[1:]) == 0:
                    config_entity.excluded_channels.insert(0, channel[1:])
            elif channel[0] == "-":
                config_entity.excluded_channels.remove(channel[1:])
        self._config_repo.save_config(config_entity)
        return self._config_repo.read_config()

    def add_users(self, users: str) -> ConfigEntity:
        users_list = users.split(" ")
        config_entity = self._config_repo.read_config()
        user: str
        any_changes = False
        for user in users_list:
            if user[0] == "+":
                if config_entity.excluded_users.count(user[1:]) == 0:
                    config_entity.excluded_users.insert(0, user[1:])
                    any_changes = True
            elif user[0] == "-":
                config_entity.excluded_users.remove(user[1:])
                any_changes = True
        if any_changes:
            self._config_repo.save_config(config_entity)
        return self._config_repo.read_config()

    def set_last_synchronize_date_unix(self, timestmp: float, channel_name="all") -> ConfigEntity:
        with self._lock:
            last_datetime_synchronize = datetime.fromtimestamp(timestmp).strftime("%Y-%m-%d %H:%M:%S")
            config_entity: ConfigEntity = self._config_repo.read_config()

            config_entity.last_datetime_synchronize[channel_name] = last_datetime_synchronize


            self._config_repo.save_config(config_entity)
        return self._config_repo.read_config()

    def is_allowed_channel(self, channel_name: str) -> bool:
        is_allowed = False
        config_entity = self._config_repo.read_config()
        if config_entity.excluded_channels.count(channel_name) == 0:
            is_allowed = True
        return is_allowed

    def is_allowed_user(self, user_name: str) -> bool:
        is_allowed = False
        config_entity = self._config_repo.read_config()
        if config_entity.excluded_users.count(user_name) == 0:
            is_allowed = True
        return is_allowed

    def get_last_synchronize_date_unix(self, channel_name: str) -> float:
        config_entity: ConfigEntity = self._config_repo.read_config()

        oldest_datetime = datetime.strptime(config_entity.last_datetime_synchronize.get(channel_name, config_entity.last_datetime_synchronize.get("all", "1970-01-01 00:00:00")), "%Y-%m-%d %H:%M:%S")

        return oldest_datetime.timestamp()

    def get_all_last_synchronize_date_unix(self) -> list:
        config_entity: ConfigEntity = self._config_repo.read_config()

        return config_entity.last_datetime_synchronize



