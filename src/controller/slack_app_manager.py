from slack_bolt import App
from flask import Flask, request
from slack_bolt.adapter.flask import SlackRequestHandler

from src.controller.config_dto_schema import ConfigDTOSchema
import logging
from src.util.settings_parser import SettingsParser
from datetime import datetime


class SlackAppManager:
    def __init__(self, config_service, slack_load_messages, mattermost_upload_messages, pin_service, bookmark_service):
        self.logger_bot = logging.getLogger("")

        self._mattermost_upload_messages_id = None
        self._mattermost_upload_messages_state = None
        settings = SettingsParser()
        bot_token = settings.slack_bot_token
        app_token = settings.slack_app_token
        signing_secret = settings.slack_signing_secret
        self.app = App(token=bot_token, signing_secret=signing_secret)
        self.app.client.apps_connections_open(app_token=app_token)
        self.flask_app = Flask(__name__)
        self.handler = SlackRequestHandler(self.app)

        self._config_service = config_service
        self._load_messages = slack_load_messages
        self._get_config_command = settings.get_config_command
        self._set_excluded_channels_command = settings.set_excluded_channels_command
        self._set_excluded_users_command = settings.set_excluded_users_command
        self._set_date_sync_command = settings.set_date_sync_command
        self._start_integration_command = settings.start_integration_command
        self._mattermost_upload_messages = mattermost_upload_messages
        self._pin_service = pin_service
        self._bookmark_service = bookmark_service
        self.register_commands()

        @self.flask_app.route("/slack/events", methods=["POST"])
        def slack_events():
            return self.handler.handle(request)

    def register_commands(self):
        self.app.command(self._get_config_command)(self.get_config)
        self.app.command(self._set_excluded_channels_command)(self.set_excluded_channels)
        self.app.command(self._set_excluded_users_command)(self.set_excluded_users)
        self.app.command(self._set_date_sync_command)(self.set_date_integration)
        self.app.command(self._start_integration_command)(self.start_integration)

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
            self.logger_bot.info("Got command option - %s", command_params)
        new_config_entity = self._config_service.set_last_synchronize_date_unix(
            datetime.strptime(command_params, "%Y-%m-%d %H:%M:%S").timestamp())
        config_schema = ConfigDTOSchema()
        config_json = config_schema.dump(obj=new_config_entity)
        self.logger_bot.info("Date setting finished")
        respond("Date setting finished")

    def start_integration(self, ack, respond, command):
        ack()
        command_params = command['text']
        if len(command_params) != 0:
            self.logger_bot.info("Got command option - %s", command_params)
        else:
            self.logger_bot.info("Transfer messages is canceled: no params")
            respond("Transfer messages is canceled: no params")
            return
        respond("Transfer messages started")
        self.logger_bot.info("Transfer messages started")

        self._load_messages.set_channel_filter(command_params)
        self._mattermost_upload_messages.set_channel_filter(command_params)
        self._pin_service.set_channel_filter(command_params)
        self._bookmark_service.set_channel_filter(command_params)

        self._mattermost_upload_messages.load_users()
        self._mattermost_upload_messages.load_channels()
        self._mattermost_upload_messages.load_team_id()

        self._load_messages.load_channel_messages()
        self._pin_service.pins_process()
        self._bookmark_service.bookmarks_process()

        self.logger_bot.info("Transfer messages finished")

        respond("Transfer messages finished")

    def run(self, port=3005):
        self.flask_app.run(port=port, host="0.0.0.0", debug=False)

#        self.app.start(port=port)
