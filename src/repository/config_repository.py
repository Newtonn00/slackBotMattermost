import logging

from src.entity.config_entity import ConfigEntity
from src.repository.file_instance import FileInstance
from src.util.common_counter import CommonCounter


class ConfigRepository():
    def __init__(self):
        self._file_instance = FileInstance()
        self._logger_bot = logging.getLogger("")

    def read_config(self)->ConfigEntity:
        config_entity = None
        try:
            config_entity = self._file_instance.read_file()
        except Exception as e:
            self._logger_bot.error("Error during reading config: %s", str(e))
            CommonCounter.increment_error("0000")
        return config_entity

    def save_config(self,config_entity: ConfigEntity):
        try:
            self._file_instance.save_file(config_entity)
        except Exception as e:
            self._logger_bot.error("Error during saving config: %s", str(e))
            CommonCounter.increment_error("0000")
