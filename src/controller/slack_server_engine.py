from slack_bolt import App
import logging
from src.util.settings_parser import SettingsParser


class SlackServerEngine:
    def __init__(self):
        settings = SettingsParser()
        bot_token = settings.slack_bot_token
        app_token = settings.slack_app_token
        signing_secret = settings.slack_signing_secret
        self.app = App(token=bot_token, signing_secret=signing_secret)
        self.app.client.apps_connections_open(app_token=app_token)


