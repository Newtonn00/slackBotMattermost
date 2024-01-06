import configparser
import os
from src.util.settings_error import SettingsError


class SettingsParser:
    slack_bot_token: str
    slack_app_token: str
    slack_signing_secret: str
    mattermost_bot_token: str
    mattermost_url: str
    set_excluded_channels_command: str
    get_config_command: str
    set_excluded_users_command: str
    set_date_sync_command: str
    start_integration_command: str
    sync_users_command: str
    config_file: str
    log_file: str
    work_dir: str

    def __init__(self):

        _settings_file_exists = True
        config = configparser.ConfigParser()
        if os.path.exists(os.environ.get('WORKDIR') + '/settings.ini') is False:
            _settings_file_exists = False
        else:
            config.read(os.environ.get('WORKDIR') + '/settings.ini')
            self.work_dir = os.environ.get('WORKDIR')

        if (os.environ.get('SLACK_BOT_TOKEN') == '' or os.environ.get(
                'SLACK_BOT_TOKEN') is None) and _settings_file_exists and config.has_option('slack', 'slack_bot_token'):
            self.slack_bot_token = config['slack']['slack_bot_token']
        else:
            self.slack_bot_token = os.environ.get('SLACK_BOT_TOKEN')

        if (os.environ.get('SLACK_SIGNING_SECRET') == '' or os.environ.get(
                'SLACK_SIGNING_SECRET') is None) and _settings_file_exists and config.has_option('slack',
                                                                                                 'slack_signing_secret'):
            self.slack_signing_secret = config['slack']['slack_signing_secret']
        else:
            self.slack_signing_secret = os.environ.get('SLACK_SIGNING_SECRET')

        if (os.environ.get('SLACK_APP_TOKEN') == '' or os.environ.get(
                'SLACK_APP_TOKEN') is None) and _settings_file_exists and config.has_option('slack', 'slack_app_token'):
            self.slack_app_token = config['slack']['slack_app_token']
        else:
            self.slack_app_token = os.environ.get('SLACK_APP_TOKEN')

        if (os.environ.get('MATTERMOST_BOT_TOKEN') == '' or os.environ.get(
                'MATTERMOST_BOT_TOKEN') is None) and _settings_file_exists and config.has_option('mattermost',
                                                                                                 'mattermost_bot_token'):
            self.mattermost_bot_token = config['mattermost']['mattermost_bot_token']
        else:
            self.mattermost_bot_token = os.environ.get('MATTERMOST_BOT_TOKEN')

        if (os.environ.get('MATTERMOST_URL') == '' or os.environ.get(
                'MATTERMOST_URL') is None) and _settings_file_exists and config.has_option('mattermost',
                                                                                           'mattermost_url'):
            self.mattermost_url = config['mattermost']['mattermost_url']
        else:
            self.mattermost_url = os.environ.get('MATTERMOST_URL')

        if (os.environ.get('CONFIG_FILE') == '' or os.environ.get(
                'CONFIG_FILE') is None) and _settings_file_exists and config.has_option('config', 'config_file'):
            self.config_file = os.environ.get('WORKDIR') + '/' + config['config']['config_file']
        else:
            self.config_file = os.environ.get('WORKDIR') + '/' + os.environ.get('CONFIG_FILE')

        if (os.environ.get('GET_CONFIG_COMMAND') == '' or os.environ.get(
                'GET_CONFIG_COMMAND') is None) and _settings_file_exists and config.has_option('slack',
                                                                                               'get_config_command'):
            self.get_config_command = config['slack']['get_config_command']
        else:
            self.get_config_command = os.environ.get('GET_CONFIG_COMMAND')

        if (os.environ.get('SET_EXCLUDED_CHANNELS_COMMAND') == '' or os.environ.get(
                'SET_EXCLUDED_CHANNELS_COMMAND') is None) and _settings_file_exists \
                and config.has_option('slack', 'set_excluded_channels_command'):
            self.set_excluded_channels_command = config['slack']['set_excluded_channels_command']
        else:
            self.set_excluded_channels_command = os.environ.get('SET_EXCLUDED_CHANNELS_COMMAND')

        if (os.environ.get('SET_EXCLUDED_USERS_COMMAND') == '' or os.environ.get(
                'SET_EXCLUDED_USERS_COMMAND') is None) and _settings_file_exists \
                and config.has_option('slack', 'set_excluded_users_command'):
            self.set_excluded_users_command = config['slack']['set_excluded_users_command']
        else:
            self.set_excluded_users_command = os.environ.get('SET_EXCLUDED_USERS_COMMAND')

        if (os.environ.get('SET_DATE_SYNC_COMMAND') == '' or os.environ.get(
                'SET_DATE_SYNC_COMMAND') is None) and _settings_file_exists \
                and config.has_option('slack', 'set_date_sync_command'):
            self.set_date_sync_command = config['slack']['set_date_sync_command']
        else:
            self.set_date_sync_command = os.environ.get('SET_DATE_SYNC_COMMAND')

        if (os.environ.get('START_INTEGRATION_COMMAND') == '' or os.environ.get(
                'START_INTEGRATION_COMMAND') is None) and _settings_file_exists \
                and config.has_option('slack', 'start_integration_command'):
            self.start_integration_command = config['slack']['start_integration_command']
        else:
            self.start_integration_command = os.environ.get('START_INTEGRATION_COMMAND')

        if (os.environ.get('SYNC_USERS_COMMAND') == '' or os.environ.get(
                'SYNC_USERS_COMMAND') is None) and _settings_file_exists \
                and config.has_option('slack', 'sync_users_command'):
            self.sync_users_command = config['slack']['sync_users_command']
        else:
            self.sync_users_command = os.environ.get('SYNC_USERS_COMMAND')

        if (os.environ.get('LOG_FILE') == '' or os.environ.get(
                'LOG_FILE') is None) and _settings_file_exists and config.has_option('config', 'log_file'):
            self.log_file = os.environ.get('WORKDIR') + '/log/' + config['config']['log_file']
        else:
            self.log_file = os.environ.get('WORKDIR') + '/log/' + os.environ.get('LOG_FILE')

        if ((self.slack_bot_token == '' or self.slack_bot_token is None) or (
                self.slack_app_token == '' or self.slack_app_token is None)
                or (self.mattermost_bot_token == '' or self.mattermost_bot_token is None) or (
                self.mattermost_url == '' or self.mattermost_url is None) or (
                self.config_file == '' or self.config_file is None)
                or (self.slack_signing_secret == '' or self.slack_signing_secret is None)
                or (self.set_date_sync_command == '' or self.set_date_sync_command is None)
                or (self.set_excluded_users_command == '' or self.set_excluded_channels_command is None)
                or (self.set_excluded_users_command == '' or self.set_excluded_users_command is None)
                or (self.get_config_command == '' or self.get_config_command is None)
                or (self.start_integration_command == '' or self.start_integration_command is None)
                or (self.log_file == '' or self.log_file is None)
                or (self.sync_users_command == '' or self.sync_users_command is None)):
            raise SettingsError()
