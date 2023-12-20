from slack_sdk import WebClient

from src.util.settings_parser import SettingsParser


class SlackWebClient:
    def __init__(self):
        settings = SettingsParser()

        self.slack_bot_token = settings.slack_bot_token
        self.slack_web_client = WebClient(self.slack_bot_token)

