import time

import requests
from slack_bolt import App
from flask import Flask, request, has_request_context, current_app
from slack_bolt.adapter.flask import SlackRequestHandler
from concurrent.futures import ThreadPoolExecutor

from src.controller.channel_lock import ChannelLock
from src.controller.config_dto_schema import ConfigDTOSchema
import logging

from src.controller.token_storage import TokenStorage
from src.util.settings_parser import SettingsParser
from src.util.common_counter import CommonCounter
from datetime import datetime
import secrets


class SlackAppManager:
    container = None

    @classmethod
    def set_container_instance(cls, container_instance):
        cls.container = container_instance

    def __init__(self, config_service, user_service):
        self.emoji_service = None
        self.logger_bot = logging.getLogger("")
        self._mattermost_upload_messages_id = None
        self._mattermost_upload_messages_state = None
        self.executor = ThreadPoolExecutor(max_workers=10)
        self._settings = SettingsParser()
        bot_token = self._settings.slack_bot_token
        self.app_token = self._settings.slack_app_token
        signing_secret = self._settings.slack_signing_secret
        self._client_id = self._settings.slack_client_id
        self._client_secret = self._settings.slack_client_secret
        self.app = App(token=bot_token, signing_secret=signing_secret)
        self.app.client.apps_connections_open(app_token=self.app_token)
        self.flask_app = Flask(__name__)
        self.handler = SlackRequestHandler(self.app)

        self._config_service = config_service
        self._get_config_command = self._settings.get_config_command
        self._set_excluded_channels_command = self._settings.set_excluded_channels_command
        self._set_excluded_users_command = self._settings.set_excluded_users_command
        self._set_date_sync_command = self._settings.set_date_sync_command
        self._start_integration_command = self._settings.start_integration_command
        self._start_dm_integration_command = self._settings.start_dm_integration_command
        self._thread_update = "/thread_update"
        self._start_group_integration_command = "/start_group_integration"
        self._emoji_integration_command = "/emoji_transfer"

        self._sync_users_command = self._settings.sync_users_command
        self._user_service = user_service
        self.register_commands()

        #        self.aiohttp_app.router.add_post("/slack/events", self.slack_events)
        #        self.aiohttp_app.router.add_get("/auth/redirect", self.auth_redirect)
        self.user_session = {}

        @self.flask_app.route("/slack/events", methods=["POST"])
        def slack_events():
            self.executor.submit(self.handler.handle(request))
            return "Request processing started"

        @self.flask_app.route("/auth/redirect", methods=["GET"])
        def auth_redirect():
            code = request.args.get('code')
            session_id = request.args.get('state')
            future = self.executor.submit(self.handle_auth_redirect, code, session_id)
            result = future.result()
            return result

    def handle_auth_redirect(self, code, session_id):
        # Получаем код из параметра запроса

        #            code = request_txt.args.get('code')
        # Обмениваем код на токен доступа
        user_data = self.exchange_code_for_token(code, session_id)
        if session_id in self.user_session:
            self.user_session[session_id]["access_token"] = user_data["access_token"]
            self.user_session[session_id]["token_date_unix"] = datetime.now().timestamp()
            self.start_integration_dm(self.user_session[session_id])
            return CommonCounter.get_str_statistic(session_id)
        else:
            self.logger_bot.info(f'Did`nt find session {session_id}')
            return f'Did`nt find session {session_id}\n Repeat, please'

    def register_commands(self):
        self.app.command(self._get_config_command)(self.get_config)
        self.app.command(self._set_excluded_channels_command)(self.set_excluded_channels)
        self.app.command(self._set_excluded_users_command)(self.set_excluded_users)
        self.app.command(self._set_date_sync_command)(self.set_date_integration)
        self.app.command(self._start_integration_command)(self.start_integration)
        self.app.command(self._sync_users_command)(self.sync_users)
        self.app.command(self._start_dm_integration_command)(self.start_dm_integration)
        self.app.command(self._thread_update)(self.thread_update)
        self.app.command(self._start_group_integration_command)(self.start_group_integration)
        self.app.command(self._emoji_integration_command)(self.emoji_integration)

    def emoji_integration(self, ack, respond, command):
        ack()
        session_id = secrets.token_urlsafe(16)
        TokenStorage.set_slack_token(session_id=session_id, slack_token=self._settings.slack_bot_token)
        CommonCounter.init_counter(session_id)
        user_id = command["user_id"]
        self.emoji_service = self.container.emoji_service()
        command_params = command['text']
        command_list = []
        if len(command_params) > 0:
            command_list = command_params.split(" ")
        if len(command_list) > 1:
            TokenStorage.set_mm_token(session_id=session_id, mm_token=command_list[0])
            self.emoji_service.set_emoji_count(int(command_list[1]))
        elif len(command_list) == 1:
            TokenStorage.set_mm_token(session_id=session_id, mm_token=command_list[0])
        else:
            self.logger_bot.info(f'Emoji transfer is canceled - no params | Session: {session_id}')
            respond("Emoji transfer is canceled - no params")
            TokenStorage.delete_session(session_id)
            return
        respond("Emoji transfer started")
        self.logger_bot.info(f'Emoji transfer started | Session: {session_id}')
        self.emoji_service.set_main_user(user_id)
        self.emoji_service.process(session_id)
        self.logger_bot.info(CommonCounter.get_str_statistic(session_id))
        self.logger_bot.info(f'Emoji transfer finished | Session: {session_id}')
        TokenStorage.delete_session(session_id)
        respond("Emoji transfer finished")

    def thread_update(self, ack, respond, command):
        ack()
        session_id = secrets.token_urlsafe(16)
        respond("Updating threads started")
        self.logger_bot.info(f'Updating threads started | Session: {session_id}')
        command_params = command['text']
        user_id = command["user_id"]
        if len(command_params) != 0:
            self.logger_bot.info(f'Got command option - {command_params} | Session: {session_id}')
        else:
            self.logger_bot.info(f'Updating threads is canceled: no params | Session: {session_id}')
            respond("Updating thread is canceled: no params")
            return

        CommonCounter.init_counter(session_id)
        slack_load_messages_instance = self.container.slack_load_messages()
        mm_upload_messages_instance = self.container.mattermost_upload_messages()
        thread_service_instance = self.container.thread_service()

        slack_load_messages_instance.set_session_id(session_id)
        mm_upload_messages_instance.set_session_id(session_id)
        thread_service_instance.set_session_id(session_id)

        slack_load_messages_instance.set_mm_upload_msg_instance(mm_upload_messages_instance)
        slack_load_messages_instance.set_initial_user(user_id)
        slack_load_messages_instance.set_channel_filter(command_params)
        slack_load_messages_instance.load_channels()

        mm_upload_messages_instance.set_channel_filter(command_params)
        thread_service_instance.set_slack_users_list(slack_load_messages_instance.get_channels_list())
        thread_service_instance.set_channel_filter(command_params)
        thread_service_instance.set_slack_channels_list(slack_load_messages_instance.get_channels_list())
        thread_service_instance.set_slack_users_list(slack_load_messages_instance.get_users_list())
        mm_upload_messages_instance.load_channels()

        thread_service_instance.set_mm_channels_list(mm_upload_messages_instance.get_channel_list())
        thread_service_instance.process()
        self.logger_bot.info(CommonCounter.get_str_statistic(session_id))

        self.logger_bot.info(f'Updating threads finished | Session:{session_id}')

        respond("Updating threads finished")

    def exchange_code_for_token(self, code, session_id) -> dict:
        user_data = {}
        url = 'https://slack.com/api/oauth.v2.access'
        data = {
            'client_id': self._client_id,
            'client_secret': self._client_secret,
            'code': code
        }

        response = requests.post(url, data=data)
        response_json = response.json()
        self.logger_bot.info(f'Response: {response_json} | Session: {session_id}')
        if not response_json["ok"]:
            self.logger_bot.info(f'Exchange code {code} error: {response_json["error"]} | Session: {session_id}')
        else:
            user_data["access_token"] = response_json.get("authed_user").get("access_token")
            user_data["id"] = response_json.get("authed_user").get("id")
            # self.logger_bot.info(f'User data: {user_data}')
        return user_data

    def start_group_integration(self, ack, respond, command):
        ack()

        command_params = command['text']
        session_id = secrets.token_urlsafe(16)
        self.logger_bot.info(f'Session ID is created - {session_id}')
        if len(command_params) != 0:
            self.logger_bot.info(f'Command option got - {command_params} | Session:{session_id}')
        else:
            self.logger_bot.info(f'Transfer group messages is canceled: no params | Session:{session_id}')
            respond("Transfer group messages is canceled: no params")
            return

        user_id = command["user_id"]
        user_sessions = []

        for session_key, session_data in self.user_session.items():
            if session_data.get("user_id") == user_id:
                user_sessions.append(session_data)

        for user_session_data in user_sessions:
            if user_session_data["access_token"] and datetime.now().timestamp() - user_session_data[
                "token_date_unix"] < 3600:
                self.user_session[session_id] = {

                    "user_id": user_id,
                    "command_params": command_params,
                    "session_id": session_id,
                    "access_token": user_session_data["access_token"],
                    "token_date_unix": datetime.now().timestamp(),
                    "request_type": "group",
                    "status": "open"

                }

                break
        if self.user_session.get(session_id):
            respond("Transfer group messages started")
            self.logger_bot.info(f'Transfer group messages started | Session: {session_id}')
            self.start_integration_dm(self.user_session[session_id])
            respond("Transfer group messages finished")

        else:

            # Генерируем ссылку для предоставления разрешения
            authorize_url = self.get_authorize_url(session_id, user_id)

            self.user_session[session_id] = {

                "user_id": user_id,
                "command_params": command_params,
                "session_id": session_id,
                "status": "open",
                "access_token": "",
                "token_date_unix": 0,
                "request_type": "group"
            }

            respond(
                f'Вам нужно предоставить разрешение на доступ к вашему приложению.\n {authorize_url}')
        # Отправляем сообщение с ссылкой в канал пользователя

    def start_dm_integration(self, ack, respond, command):
        ack()

        command_params = command['text']
        session_id = secrets.token_urlsafe(16)
        user_id = command["user_id"]
        self.logger_bot.info(f'Session ID is created - {session_id} | User: {user_id}')
        if len(command_params) != 0:
            self.logger_bot.info(f'Command option got - {command_params} | User: {user_id} | Session:{session_id}')
        else:
            self.logger_bot.info \
                (f'Transfer direct messages is canceled: no params | User: {user_id} | Session:{session_id}')
            respond("Transfer direct messages is canceled: no params")
            return

        user_sessions = []

        for session_key, session_data in self.user_session.items():
            if session_data.get("user_id") == user_id and session_data["access_token"]:
                user_sessions.append(session_data)

        for user_session_data in user_sessions:
            if user_session_data["access_token"] and datetime.now().timestamp() - user_session_data[
                "token_date_unix"] < 3600:
                self.user_session[session_id] = {

                    "user_id": user_id,
                    "command_params": command_params,
                    "session_id": session_id,
                    "access_token": user_session_data["access_token"],
                    "token_date_unix": datetime.now().timestamp(),
                    "request_type": "direct",
                    "status": "open"

                }

                break
        if self.user_session.get(session_id):
            respond("Transfer direct messages started")
            self.logger_bot.info(f'Transfer direct messages started | User: {user_id} | Session: {session_id}')
            self.start_integration_dm(self.user_session[session_id])
            respond("Transfer messages finished")

        else:

            # Генерируем ссылку для предоставления разрешения
            authorize_url = self.get_authorize_url(session_id, user_id)

            self.user_session[session_id] = {
                "user_id": user_id,
                "command_params": command_params,
                "session_id": session_id,
                "status": "open",
                "access_token": "",
                "token_date_unix": 0,
                "request_type": "direct"
            }

            respond(
                f'Вам нужно предоставить разрешение на доступ к вашему приложению.\n {authorize_url}')
        # Отправляем сообщение с ссылкой в канал пользователя

    def sync_users(self, ack, respond, command):
        ack()
        session_id = secrets.token_urlsafe(16)
        self.logger_bot.info(f'Sync users started | Session: {session_id}')
        respond("Sync users started")
        command_params = command['text']
        self._user_service.set_params(command_params)
        self._user_service.sync_process(session_id)
        self.logger_bot.info(f'Sync users finished | Session: {session_id}')
        respond("Sync users finished")

    def get_config(self, ack, respond, command):
        ack()
        session_id = secrets.token_urlsafe(16)
        self.logger_bot.info(f'Config selection started | Session: {session_id}')
        config_entity = self._config_service.get_config()
        config_schema = ConfigDTOSchema()
        config_json = config_schema.dumps(obj=config_entity)
        self.logger_bot.info(f'Config selection finished | Session: {session_id}')
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
        session_id = secrets.token_urlsafe(16)
        user_id = command["user_id"]
        respond("Transfer messages started")
        self.logger_bot.info(f'Transfer messages started | User: {user_id} | Session: {session_id}')
        command_params = command['text']
        TokenStorage.set_slack_token(session_id=session_id, slack_token=self._settings.slack_bot_token)

        if len(command_params) != 0:
            self.logger_bot.info(f'Command option was got - {command_params} | Session: {session_id}')
        else:
            self.logger_bot.info(f'Transfer messages is canceled: no params | Session: {session_id}')
            respond("Transfer messages is canceled: no params")
            return
        CommonCounter.init_counter(session_id)

        slack_load_messages_instance = self.container.slack_load_messages()
        mm_upload_messages_instance = self.container.mattermost_upload_messages()
        pin_service_instance = self.container.pin_service()
        bookmark_service_instance = self.container.bookmark_service()

        slack_load_messages_instance.set_mm_upload_msg_instance(mm_upload_messages_instance)
        slack_load_messages_instance.set_container_instance(self.container)
        slack_load_messages_instance.set_session_id(session_id)
        mm_upload_messages_instance.set_session_id(session_id)
        pin_service_instance.set_session_id(session_id)
        bookmark_service_instance.set_session_id(session_id)

        slack_load_messages_instance.set_initial_user(user_id)
        slack_load_messages_instance.set_channels_filter(command_params)
        pin_service_instance.set_channel_filter(command_params)
        bookmark_service_instance.set_channel_filter(command_params)

        #        mm_upload_messages_instance.load_users()

        mm_upload_messages_instance.load_channels()

        slack_load_messages_instance.load_channel_messages(["public", "private"])
        pin_service_instance.set_mm_channels_list(mm_upload_messages_instance.get_channel_list())
        pin_service_instance.set_slack_channels_list(slack_load_messages_instance.get_channels_list())
        pin_service_instance.pins_process()
        bookmark_service_instance.set_mm_channels_list(mm_upload_messages_instance.get_channel_list())
        bookmark_service_instance.set_slack_channels_list(slack_load_messages_instance.get_channels_list())
        bookmark_service_instance.bookmarks_process()

        self.logger_bot.info(CommonCounter.get_str_statistic(session_id))

        self.logger_bot.info(f'Transfer messages finished | Session: {session_id}')

        respond("Transfer messages finished")

    def start_integration_dm(self, user_session_data: dict):

        user_id = user_session_data["user_id"]
        session_id = user_session_data["session_id"]
        request_type = user_session_data["request_type"]

        TokenStorage.set_slack_token(session_id=session_id, slack_token=user_session_data["access_token"])

        slack_load_messages_instance = self.container.slack_load_messages()
        mm_upload_messages_instance = self.container.mattermost_upload_messages()
        pin_service_instance = self.container.pin_service()
        bookmark_service_instance = self.container.bookmark_service()

        slack_load_messages_instance.set_mm_upload_msg_instance(mm_upload_messages_instance)
        slack_load_messages_instance.set_container_instance(self.container)

        slack_load_messages_instance.set_session_id(session_id)
        mm_upload_messages_instance.set_session_id(session_id)

        slack_load_messages_instance.set_user_token(user_session_data["access_token"])
        slack_load_messages_instance.set_initial_user(user_id)
        slack_load_messages_instance.set_channels_filter(user_session_data["command_params"])

        pin_service_instance.set_channel_filter(user_session_data["command_params"])
        bookmark_service_instance.set_channel_filter(user_session_data["command_params"])

        self._user_service.load_mattermost(session_id)
        self._user_service.load_slack(session_id)
        self._user_service.load_team(session_id)

        pin_service_instance.set_session_id(session_id)
        bookmark_service_instance.set_session_id(session_id)

        mm_upload_messages_instance.set_main_slack_user_id(user_id)
        slack_load_messages_instance.load_channel_messages(request_type)

        pin_service_instance.set_mm_channels_list(mm_upload_messages_instance.get_channel_list())
        pin_service_instance.set_slack_channels_list(slack_load_messages_instance.get_channels_list())
        pin_service_instance.pins_process()
        bookmark_service_instance.set_mm_channels_list(mm_upload_messages_instance.get_channel_list())
        bookmark_service_instance.set_slack_channels_list(slack_load_messages_instance.get_channels_list())
        bookmark_service_instance.bookmarks_process()

        self.logger_bot.info(CommonCounter.get_str_statistic(session_id))

        self.logger_bot.info(f'Transfer {request_type} messages finished | Session: {session_id}')

    def get_authorize_url(self, session_id: str, user_id: str) -> str:
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
                         f'im:write,'
                         f'chat:write,'
                         f'bookmarks:read,'
                         f'pins:read,'
                         f'files:read&'
                         f'state={session_id}&'
                         f'user={user_id}')
        return authorize_url

    def cleanup_process(self):
        while True:
            ChannelLock.clean_locked_channels()
            # Логика очистки данных, например, удаление устаревших записей из словарей
            time.sleep(300)

    def run(self, port=3005):
        self.logger_bot.info("Slack bot version 2.1 started")
        self.executor.submit(self.cleanup_process)
        self.flask_app.run(port=port, host="0.0.0.0", debug=False)
