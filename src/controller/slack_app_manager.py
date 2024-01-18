import sys

import requests
from slack_bolt import App
from flask import Flask, request, jsonify
from slack_bolt.adapter.flask import SlackRequestHandler

from src.controller.config_dto_schema import ConfigDTOSchema
import logging
from src.util.settings_parser import SettingsParser
from src.util.common_counter import CommonCounter
from datetime import datetime


class SlackAppManager:

    def __init__(self, config_service, slack_load_messages, mattermost_upload_messages, pin_service,
                 bookmark_service, thread_service, user_service):
        self.logger_bot = logging.getLogger("")

        self._mattermost_upload_messages_id = None
        self._mattermost_upload_messages_state = None
        self._settings = SettingsParser()
        bot_token = self._settings.slack_bot_token
        app_token = self._settings.slack_app_token
        signing_secret = self._settings.slack_signing_secret
        self._client_id = self._settings.slack_client_id
        self._client_secret = self._settings.slack_client_secret
        self.app = App(token=bot_token, signing_secret=signing_secret)
        self.app.client.apps_connections_open(app_token=app_token)
        self.flask_app = Flask(__name__)
        self.handler = SlackRequestHandler(self.app)

        self._config_service = config_service
        self._load_messages = slack_load_messages
        self._get_config_command = self._settings.get_config_command
        self._set_excluded_channels_command = self._settings.set_excluded_channels_command
        self._set_excluded_users_command = self._settings.set_excluded_users_command
        self._set_date_sync_command = self._settings.set_date_sync_command
        self._start_integration_command = self._settings.start_integration_command
        self._start_dm_integration_command = self._settings.start_dm_integration_command
        self._thread_update = "/thread_update"
        self._sync_users_command = self._settings.sync_users_command
        self._mattermost_upload_messages = mattermost_upload_messages
        self._pin_service = pin_service
        self._user_service = user_service
        self._bookmark_service = bookmark_service
        self._thread_service = thread_service
        self.register_commands()

        @self.flask_app.route("/slack/events", methods=["POST"])
        def slack_events():
            return self.handler.handle(request)

        @self.flask_app.route("/auth/redirect", methods=["GET"])
        def auth_redirect():
            # Получаем код из параметра запроса
            print(request.args)
            code = request.args.get('code')
            # Обмениваем код на токен доступа
            user_data = {}
            user_data = self.exchange_code_for_token(code)
            self.start_integration_dm(user_data)
            return CommonCounter.get_str_statistic()


    def register_commands(self):
        self.app.command(self._get_config_command)(self.get_config)
        self.app.command(self._set_excluded_channels_command)(self.set_excluded_channels)
        self.app.command(self._set_excluded_users_command)(self.set_excluded_users)
        self.app.command(self._set_date_sync_command)(self.set_date_integration)
        self.app.command(self._start_integration_command)(self.start_integration)
        self.app.command(self._sync_users_command)(self.sync_users)
        self.app.command(self._start_dm_integration_command)(self.start_dm_integration)
        self.app.command(self._thread_update)(self.thread_update)

    def thread_update(self, ack, respond, command):
        ack()
        respond("Updating threads started")
        self.logger_bot.info("Updating threads started")
        command_params = command['text']
        user_id = command["user_id"]
        if len(command_params) != 0:
            self.logger_bot.info("Got command option - %s", command_params)
        else:
            self.logger_bot.info("Updating threads is canceled: no params")
            respond("Updating thread is canceled: no params")
            return
        CommonCounter.init_counter()

        self._load_messages.set_initial_user(user_id)
        self._load_messages.set_channel_filter(command_params)
        self._load_messages.load_channels()
        self._load_messages.load_users()
        self._mattermost_upload_messages.set_channel_filter(command_params)
        self._thread_service.set_channel_filter(command_params)
        self._thread_service.set_slack_channels_list(self._load_messages.get_channels_list())
        self._thread_service.set_slack_users_list(self._load_messages.get_users_list())

        self._mattermost_upload_messages.load_users()
        self._mattermost_upload_messages.load_channels()
        self._mattermost_upload_messages.load_team_id()
        self._thread_service.process()
        self.logger_bot.info(CommonCounter.get_str_statistic())

        self.logger_bot.info("Updating threads finished")

        respond("Updating threads finished")

    def exchange_code_for_token(self, code) -> dict:
        user_data = {}
        url = 'https://slack.com/api/oauth.v2.access'
        data = {
            'client_id': self._client_id,
            'client_secret': self._client_secret,
            'code': code
        }
        response = requests.post(url, data=data)
        self.logger_bot.info(f'Response: {response.json()}')
        user_data["access_token"] = response.json().get("authed_user").get("access_token")
        user_data["id"] = response.json().get("authed_user").get("id")
        self.logger_bot.info(f'User data: {user_data}')
        return user_data

    def start_dm_integration(self, ack, respond, command):
        ack()

        command_params = command['text']
        self.logger_bot.info("Transfer direct messages started")
        if len(command_params) != 0:
            self.logger_bot.info("Got command option - %s", command_params)
            self._load_messages.set_direct_channels_filter(command_params)
        else:
            self.logger_bot.info("Transfer messages is canceled: no params")
            respond("Transfer messages is canceled: no params")
            return

        user_id = command["user_id"]
        # Генерируем ссылку для предоставления разрешения
        authorize_url = (f'https://slack.com/oauth/v2/authorize?client_id={self._client_id}&'
                         f'scope='
                         f'channels:history,'
                         f'links:read,'
                         f'im:history,'
                         f'mpim:history,'
                         f'im:read,'
                         f'mpim:read,'
                         f'users:read,'
                         f'users:read.email,'
                         f'files:read&'
                         f'user_scope='
                         f'channels:history,'
                         f'links:read,'
                         f'im:history,'
                         f'mpim:history,'
                         f'im:read,'
                         f'mpim:read,'
                         f'users:read,'
                         f'users:read.email,'
                         f'groups:read,'
                         f'groups:history,'
                         f'stars:read,'
                         f'files:read&' 
                         f'user={user_id}')
        respond(
            f'Вам нужно предоставить разрешение на доступ к вашему приложению.\n {authorize_url}')
        # Отправляем сообщение с ссылкой в канал пользователя

    def sync_users(self, ack, respond, command):
        ack()
        self.logger_bot.info("Sync users started")
        respond("Sync users started")
        command_params = command['text']
        self._user_service.set_params(command_params)
        self._user_service.sync_process()
        self.logger_bot.info("Sync users finished")
        respond("Sync users finished")

    def get_config(self, ack, respond, command):
        ack()
        self.logger_bot.info("Config selection started")
        config_entity = self._config_service.get_config()
        config_schema = ConfigDTOSchema()
        config_json = config_schema.dumps(obj=config_entity)
        self.logger_bot.info("Config selection finished")
        respond(config_json)

    def set_excluded_channels(self, ack, respond, command):
        ack()
        command_params = command['text']
        self.logger_bot.info("Channels setting started")
        if len(command_params) != 0:
            self.logger_bot.info("Got command option - %s", command_params)
        new_config_entity = self._config_service.add_channels(command_params)
        config_schema = ConfigDTOSchema()
        config_json = config_schema.dump(obj=new_config_entity)
        self.logger_bot.info("Channels setting finished")
        respond("Channels setting finished")

    def set_excluded_users(self, ack, respond, command):
        ack()
        command_params = command['text']
        self.logger_bot.info("Users setting started")
        if len(command_params) != 0:
            self.logger_bot.info("Got command option - %s", command_params)
        new_config_entity = self._config_service.add_users(command_params)
        config_schema = ConfigDTOSchema()
        config_json = config_schema.dump(obj=new_config_entity)
        self.logger_bot.info("Users setting finished")
        respond("Users setting finished")

    def set_date_integration(self, ack, respond, command):
        ack()
        command_params = command['text']

        self.logger_bot.info("Date setting started")
        if len(command_params) != 0:
            params = command_params.split("=")
            self.logger_bot.info("Got command option - %s", command_params)
            self._config_service.set_last_synchronize_date_unix(
                timestmp=datetime.strptime(params[1], "%Y-%m-%d %H:%M:%S").timestamp(),
                channel_name=params[0])
        else:
            self.logger_bot.info("Date setting is canceled: no params")
            respond("Date setting is canceled: no params")
            return
        self.logger_bot.info("Date setting finished")
        respond("Date setting finished")

    def start_integration(self, ack, respond, command):
        ack()
        respond("Transfer messages started")
        self.logger_bot.info("Transfer messages started")
        command_params = command['text']
        user_id = command["user_id"]
        if len(command_params) != 0:
            self.logger_bot.info("Got command option - %s", command_params)
        else:
            self.logger_bot.info("Transfer messages is canceled: no params")
            respond("Transfer messages is canceled: no params")
            return
        CommonCounter.init_counter()

        self._load_messages.set_initial_user(user_id)
        self._load_messages.set_channel_filter(command_params)
        self._mattermost_upload_messages.set_channel_filter(command_params)
        self._pin_service.set_channel_filter(command_params)
        self._bookmark_service.set_channel_filter(command_params)

        self._mattermost_upload_messages.load_users()
        self._mattermost_upload_messages.load_channels()
        self._mattermost_upload_messages.load_team_id()

        self._load_messages.load_channel_messages(["public", "private"])
        self._pin_service.pins_process()
        self._bookmark_service.bookmarks_process()

        self.logger_bot.info(CommonCounter.get_str_statistic())

        self.logger_bot.info("Transfer messages finished")

        respond("Transfer messages finished")

    def start_integration_dm(self, user_data: dict):

        user_id = user_data["id"]
        CommonCounter.init_counter()
        self._load_messages.set_user_token(user_data["access_token"])
        self._load_messages.set_initial_user(user_id)

        self._user_service.load_mattermost()
        self._user_service.load_slack()
        self._user_service.load_team()
        self._mattermost_upload_messages.load_team_id()
        self._mattermost_upload_messages.set_main_slack_user_id(user_id)
        self._load_messages.load_channel_messages("direct")
#        self._pin_service.pins_process()
#        self._bookmark_service.bookmarks_process()

        self.logger_bot.info(CommonCounter.get_str_statistic())

        self.logger_bot.info("Transfer direct messages finished")

    def run(self, port=3005):
        self.flask_app.run(port=port, host="0.0.0.0", debug=False)

#        self.app.start(port=port)
