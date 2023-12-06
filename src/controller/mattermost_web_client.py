import requests

from src.util.settings_parser import SettingsParser


class MattermostWebClient:
    def __init__(self):
        settings = SettingsParser()
        self.mattermost_url = settings.mattermost_url
        self.mattermost_session = requests.Session()
        self.mattermost_session.headers.update({'Authorization': 'Bearer ' + settings.mattermost_bot_token})