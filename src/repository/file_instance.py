import json
from dataclasses import asdict

from src.util.settings_parser import SettingsParser
from src.entity.config_entity import ConfigEntity


class FileInstance:
    def __init__(self):
        setting_parser = SettingsParser()
        self._config_file = setting_parser.config_file

    def read_file(self) -> ConfigEntity:
        with open(self._config_file) as f:
            config_data = json.load(f)

        config_entity = ConfigEntity.from_dict(config_data)

        return config_entity

    def save_file(self, config_entity: ConfigEntity):

        config_dict = asdict(config_entity)
        with open(self._config_file, 'w') as f:
            f.write(json.dumps(config_dict, default=str))
