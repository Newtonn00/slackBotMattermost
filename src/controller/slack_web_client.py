from slack_sdk import WebClient

from src.util.settings_parser import SettingsParser


class SlackWebClient:
    def __init__(self):
        settings = SettingsParser()

        self.slack_web_client = WebClient(settings.slack_bot_token)
